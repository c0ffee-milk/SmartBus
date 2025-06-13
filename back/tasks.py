from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from model import db, Schedule, Reservation, ReservationStatusEnum, Penalty, User
from sqlalchemy import and_
import logging

MAX_ABSENT_TIMES = 5  # 最大缺席次数
PENALTY_DAYS = 7  # 惩罚天数

scheduler = BackgroundScheduler()
app = None  # 全局变量存储应用实例

def get_monday(today=None, number=0) -> str:
    """
    获取Monday的方法, 通过指定number来获得当前之后或者当前后的星期一的日期
    number 为 0 是获取本周的星期一
    number 为 1 是获取上周的星期一
    """
    time_fmt = "%Y-%m-%d"
    today = datetime.strptime(str(today), time_fmt) if today else datetime.today()
    return datetime.strftime(today - timedelta(days=today.weekday()) - timedelta(days=number*7), time_fmt)

def check_absent_reservations():
    """检查未签到的预约并标记为缺席"""
    global app
    if not app:
        logging.error("应用实例未初始化")
        return
        
    with app.app_context():
        try:
            # 获取所有已发车但未签到的预约
            absent_reservations = Reservation.query.join(Schedule).filter(
                and_(
                    Reservation.status == ReservationStatusEnum.active,
                    Schedule.departure_datetime < datetime.utcnow()
                )
            ).all()

            for reservation in absent_reservations:
                # 更新预约状态
                reservation.status = ReservationStatusEnum.absent

                # 检查每周缺席次数(每周可缺席5次)
                absent_count = Reservation.query.filter(
                    and_(
                        Reservation.user_id == reservation.user_id,
                        Reservation.reserved_at > get_monday(),
                        Reservation.status == ReservationStatusEnum.absent
                    )
                ).count()
                
                if absent_count >= MAX_ABSENT_TIMES:
                    # 添加惩罚记录
                    penalty = Penalty(
                        user_id=reservation.user_id,
                        penalty_until=datetime.utcnow() + timedelta(days=PENALTY_DAYS)  # 7天惩罚期
                    )
                    db.session.add(penalty)
                    
                    # 更新用户惩罚状态
                    absent_user = User.query.get(reservation.user_id)
                    absent_user.penalty_until = penalty.penalty_until

            db.session.commit()
            logging.info(f"已标记 {len(absent_reservations)} 个预约为缺席")

        except Exception as e:
            logging.error(f"检查缺席预约失败: {str(e)}")
            db.session.rollback()

def init_scheduler(flask_app):
    """初始化定时任务"""
    global app
    app = flask_app  # 保存应用实例
    
    # 每10分钟检查一次未签到的预约
    scheduler.add_job(
        check_absent_reservations,
        CronTrigger(minute='*/10'),  # 每10分钟执行一次
        id='check_absent_reservations',
        replace_existing=True
    )
    
    scheduler.start()
    logging.info("定时任务已启动") 