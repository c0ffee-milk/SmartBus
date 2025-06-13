from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from model import db, User, Schedule, Reservation, ReservationStatusEnum, RoleEnum, Penalty, Route, RouteNameEnum
from datetime import datetime, timedelta, date
from sqlalchemy import and_, or_, func
import logging
import re
import uuid
import qrcode
import io
import base64
from extensions import redis_client
import json
from cache import cache_manager
from constants import RedisKeys

reservation_bp = Blueprint('reservation', __name__)

# 预约相关配置
MAX_CANCEL_TIMES = 5  # 每天最大取消次数
PENALTY_DAYS = 7  # 惩罚天数
TEACHER_PRIORITY_SEATS = 5  # 教师优先座位数

def generate_qr_code(reservation_id):
    """
    生成预约二维码
    Args:
        reservation_id: 预约ID
    Returns:
        str: Base64编码的二维码图片
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(reservation_id))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# 已实现
@reservation_bp.route('/create', methods=['POST'])
@jwt_required()
def create_reservation():
    """
    创建班车预约
    请求体:
        schedule_id: 班次ID 
    返回:
        成功:
            message: 预约成功
            reservation: {
                id: 预约ID
                schedule_id: 班次ID
                seat_number: 座位号
                status: 预约状态
                qr_code: 预约二维码
                qr_image: 二维码图片(Base64)
            }
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证
    业务规则:
        1. 用户不能在惩罚期内
        2. 每个用户同时只能有一个有效预约
        3. 教师有优先座位权
        4. 预约成功后生成唯一二维码
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查用户是否在惩罚期内
        if hasattr(user, 'penalty_until') and user.penalty_until and user.penalty_until > datetime.utcnow():
            return jsonify({
                'error': '您在惩罚期内，无法预约',
                'penalty_until': user.penalty_until.isoformat()
            }), 403

        schedule_id = request.json.get('schedule_id')
        if not schedule_id:
            return jsonify({'error': '缺少班次ID'}), 400

        # 检查班次是否存在且有效
        schedule = Schedule.query.get(schedule_id)
        if not schedule or schedule.status.value != 'normal':
            return jsonify({'error': '班次不存在或已取消'}), 400

        # 检查是否已经预约过该班次
        existing_reservation = Reservation.query.filter_by(
            user_id=current_user_id,
            schedule_id=schedule_id,
            status=ReservationStatusEnum.active
        ).first()
        
        if existing_reservation:
            return jsonify({'error': '您已经预约过该班次'}), 400

        # 检查用户是否已有其他有效预约
        active_reservation = Reservation.query.filter_by(
            user_id=current_user_id,
            status=ReservationStatusEnum.active
        ).first()
        
        if active_reservation:
            return jsonify({'error': '您已有其他有效预约'}), 400

        # 获取当前预约数量
        current_reservations = Reservation.query.filter_by(
            schedule_id=schedule_id,
            status=ReservationStatusEnum.active
        ).count()

        # 检查是否还有座位
        if current_reservations >= schedule.dynamic_capacity:
            return jsonify({'error': '该班次已满'}), 400

        # 检查教师优先座位
        is_teacher = user.role == RoleEnum.teacher
        if not is_teacher and current_reservations >= (schedule.dynamic_capacity - TEACHER_PRIORITY_SEATS):
            return jsonify({'error': '该班次仅剩教师优先座位'}), 400

        # 生成唯一二维码
        qr_code = str(uuid.uuid4())

        # 创建预约
        reservation = Reservation(
            user_id=current_user_id,
            schedule_id=schedule_id,
            seat_number=current_reservations + 1,
            priority_used=is_teacher,
            qr_code=qr_code
        )

        db.session.add(reservation)
        db.session.commit()

        # 更新缓存
        update_schedule_cache(schedule_id, current_user_id)
        
        # 缓存预约信息
        reservation_data = {
            'id': reservation.id,
            'user_id': current_user_id,
            'schedule_id': reservation.schedule_id,
            'seat_number': reservation.seat_number,
            'status': reservation.status.value,
            'reserved_at': reservation.reserved_at.isoformat(),
            'qr_code': qr_code
        }
        redis_client.setex(
            RedisKeys.RESERVATION.format(reservation.id),
            3600,
            json.dumps(reservation_data)
        )

        return jsonify({
            'message': '预约成功',
            'reservation': reservation_data
        })

    except Exception as e:
        logging.error(f"创建预约失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

@reservation_bp.route('/check-in/<string:qr_code>', methods=['POST'])
@jwt_required()
def check_in(qr_code):
    """
    扫描二维码进行签到
    Args:
        qr_code: 预约二维码
    返回:
        成功:
            message: 签到成功
            reservation: {
                id: 预约ID
                user_name: 用户姓名
                seat_number: 座位号
            }
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证，且用户角色必须为司机
    业务规则:
        1. 只能对有效预约进行签到
        2. 必须在发车前完成签到
        3. 签到后更新预约状态为已签到
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查权限（仅司机可以签到）
        if user.role != RoleEnum.driver:
            return jsonify({'error': '只有司机可以进行签到操作'}), 403

        # 查找预约记录
        reservation = Reservation.query.filter_by(qr_code=qr_code).first()
        if not reservation:
            return jsonify({'error': '无效的二维码'}), 404

        # 检查预约状态
        if reservation.status != ReservationStatusEnum.active:
            return jsonify({'error': '该预约已失效'}), 400

        # 检查班次时间
        schedule = Schedule.query.get(reservation.schedule_id)
        if datetime.utcnow() > schedule.departure_datetime:
            return jsonify({'error': '该班次已发车，无法签到'}), 400
        
        cache_manager.update_reservation_cache(reservation.schedule_id, reservation.user_id)

        # 更新预约状态
        reservation.status = ReservationStatusEnum.checked_in
        reservation.checked_in_at = datetime.utcnow()
        
        db.session.commit()

        return jsonify({
            'message': '签到成功',
            'reservation': {
                'id': reservation.id,
                'user_name': reservation.user.name,
                'seat_number': reservation.seat_number
            }
        })

    except Exception as e:
        logging.error(f"签到失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

@reservation_bp.route('/mark-absent', methods=['POST'])
@jwt_required()
def mark_absent():
    """
    标记班次中所有未签到的预约为缺席
    请求体:
        schedule_id: 班次ID
    返回:
        成功:
            message: 标记成功信息
            absent_count: 标记为缺席的预约数量
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证，且用户角色必须为管理员或司机
    业务规则:
        1. 只能标记已发车班次的未签到预约
        2. 自动为缺席用户添加惩罚记录
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查权限（仅管理员和司机可以标记缺席）
        if user.role not in [RoleEnum.admin, RoleEnum.driver]:
            return jsonify({'error': '无权操作'}), 403

        schedule_id = request.json.get('schedule_id')
        if not schedule_id:
            return jsonify({'error': '缺少班次ID'}), 400

        # 获取班次信息
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'error': '班次不存在'}), 404

        # 获取所有未签到的有效预约
        absent_reservations = Reservation.query.filter(
            and_(
                Reservation.schedule_id == schedule_id,
                Reservation.status == ReservationStatusEnum.active,
                Schedule.departure_datetime < datetime.utcnow()
            )
        ).all()

        # 标记缺席并添加惩罚
        for reservation in absent_reservations:
            reservation.status = ReservationStatusEnum.absent
            
            # 添加惩罚记录
            penalty = Penalty(
                user_id=reservation.user_id,
                penalty_until=datetime.utcnow() + timedelta(days=PENALTY_DAYS)
            )
            db.session.add(penalty)
            
            # 更新用户惩罚状态
            absent_user = User.query.get(reservation.user_id)
            absent_user.penalty_until = penalty.penalty_until

        db.session.commit()

        cache_manager.update_reservation_cache(schedule_id, current_user_id)

        return jsonify({
            'message': f'已标记 {len(absent_reservations)} 个预约为缺席',
            'absent_count': len(absent_reservations)
        })

    except Exception as e:
        logging.error(f"标记缺席失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

# 已实现
@reservation_bp.route('/cancel', methods=['POST'])
@jwt_required()
def cancel_reservation():
    """
    取消预约
    请求体:
        schedule_id: 班次ID
    返回:
        成功:
            message: 取消成功信息
            cancel_count: 今日已取消次数
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证
    业务规则:
        1. 只能取消自己的预约
        2. 每天最多取消5次
        3. 只能取消有效预约
    """
    try:
        current_user_id = get_jwt_identity()
        schedule_id = request.json.get('schedule_id')
        
        # 检查取消次数
        today = date.today().isoformat()
        cancel_count_key = RedisKeys.USER_CANCEL_COUNT.format(current_user_id, today)
        cancel_count = int(redis_client.get(cancel_count_key) or 0)

        if cancel_count >= MAX_CANCEL_TIMES:
            return jsonify({'error': '您已达到最大取消次数'}), 400

        # 查找预约记录
        reservation = Reservation.query.filter_by(
            user_id=current_user_id,
            schedule_id=schedule_id,
            status=ReservationStatusEnum.active
        ).first()
        
        if not reservation:
            return jsonify({'error': '预约记录不存在'}), 404

        # 更新预约状态
        reservation.status = ReservationStatusEnum.canceled
        reservation.canceled_at = datetime.utcnow()
        
        db.session.commit()

        # 更新缓存
        update_schedule_cache(schedule_id, current_user_id)
        
        # 更新取消次数
        redis_client.incr(cancel_count_key)
        redis_client.expire(cancel_count_key, 86400)  # 24小时过期

        return jsonify({
            'message': '取消预约成功',
            'cancel_count': cancel_count + 1
        })

    except Exception as e:
        logging.error(f"取消预约失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

# 已实现
@reservation_bp.route('/list', methods=['GET'])
@jwt_required()
def list_reservations():
    """
    获取用户的预约列表
    查询参数:
        status: 预约状态筛选（可选，null时返回所有状态）
    返回:
        成功:
            reservations: [
                {
                    id: 预约ID
                    schedule_id: 班次ID
                    seat_number: 座位号
                    status: 预约状态
                    reserved_at: 预约时间
                    canceled_at: 取消时间（如果有）
                    priority_used: 是否使用教师优先
                    qr_code: 预约二维码
                }
            ]
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证
    业务规则:
        1. 只能查看自己的预约记录
        2. 支持分页和状态筛选
    """
    try:
        current_user_id = get_jwt_identity()
        
        # 获取查询参数
        status = request.args.get('status')

        # 尝试从缓存获取预约列表
        cache_key = RedisKeys.USER_RESERVATIONS.format(current_user_id)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            reservations = json.loads(cached_data)
            if status and status.lower() != 'null':
                reservations = [r for r in reservations if r['status'] == status]
            return jsonify({'reservations': reservations})

        # 构建查询
        query = Reservation.query.filter_by(user_id=current_user_id)
        
        if status and status.lower() != 'null':  # 只有当status有值且不为'null'时才进行筛选
            query = query.filter_by(status=ReservationStatusEnum[status])

        # 获取所有预约
        reservation_data = query.all()

        reservations = [{
            'id': r.id,
            'schedule_id': r.schedule_id,
            'seat_number': r.seat_number,
            'status': r.status.value,
            'reserved_at': r.reserved_at.isoformat(),
            'canceled_at': r.canceled_at.isoformat() if r.canceled_at else None,
            'priority_used': r.priority_used,
            'qr_code': r.qr_code
        } for r in reservation_data]

        # 缓存预约列表
        redis_client.setex(cache_key, 300, json.dumps(reservations))  # 5分钟过期

        return jsonify({
            'reservations': reservations,
        })

    except Exception as e:
        logging.error(f"获取预约列表失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

# 已实现
@reservation_bp.route('/available-schedules', methods=['GET'])
@jwt_required()
def get_available_schedules():
    """
    获取可预约的班次列表
    查询参数:
        date: 日期 (YYYY-MM-DD)
        start_point: 起点
        end_point: 终点
    返回:
        成功:
            schedules: [
                {
                    id: 班次ID
                    route_name: 路线名称
                    departure_time: 发车时间
                    available_seats: 剩余座位数
                    total_seats: 总座位数
                    vehicle_plate: 车牌号
                    driver_name: 司机姓名
                    is_full: 是否满座
                    is_booked: 是否已预约
                }
            ]
            total: 总记录数
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证
    业务规则:
        1. 只返回未发车的班次
        2. 只返回有剩余座位的班次
        3. 支持按日期、起点、终点筛选
        4. 支持分页
    """
    try:
        current_user_id = get_jwt_identity()
        if not current_user_id:
            return jsonify({
                'code': 4001,
                'error': '未认证', 
                'message': '请前往我的界面验证身份'
            }), 400

        date_str = request.args.get('date')
        start_point = request.args.get('start_point')
        end_point = request.args.get('end_point')

        # 构建缓存键
        cache_key = RedisKeys.AVAILABLE_SCHEDULES.format(
            f"{date_str}:{start_point}:{end_point}",
            current_user_id
        )

        # 尝试从缓存获取数据
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))

        # 验证日期格式
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'error': '日期格式不正确，请使用 YYYY-MM-DD 格式'}), 400

        # 构建基础查询
        query = Schedule.query.join(Route).filter(
            func.date(Schedule.departure_datetime) == query_date,
            Schedule.status == 'normal',
            # 如果是今天，则只显示当前时间之后的班次
            or_(
                query_date > datetime.utcnow().date(),
                func.time(Schedule.departure_datetime) > datetime.utcnow().time()
            )
        )

        # 根据起点和终点筛选
        if start_point and end_point:
            query = query.filter(
                Route.start_point == start_point,
                Route.end_point == end_point
            )

        # 计算每个班次的已预约数量
        subquery = db.session.query(
            Reservation.schedule_id,
            func.count(Reservation.id).label('reserved_count')
        ).filter(
            Reservation.status == ReservationStatusEnum.active
        ).group_by(Reservation.schedule_id).subquery()

        # 获取用户已预约的班次ID列表
        user_booked_schedules = db.session.query(Reservation.schedule_id).filter(
            Reservation.user_id == current_user_id,
            Reservation.status == ReservationStatusEnum.active
        ).all()
        user_booked_schedule_ids = [schedule[0] for schedule in user_booked_schedules]

        # 添加已预约数量信息
        query = query.outerjoin(
            subquery,
            Schedule.id == subquery.c.schedule_id
        ).add_columns(
            func.coalesce(subquery.c.reserved_count, 0).label('reserved_count')
        )


        # 获取所有符合条件的班次
        schedules_data = query.all()

        # 构建返回数据
        schedules = []
        for schedule, reserved_count in schedules_data:
            # 获取缓存的可用座位数
            available_seats_key = RedisKeys.SCHEDULE_AVAILABLE_SEATS.format(schedule.id)
            cached_available_seats = redis_client.get(available_seats_key)
            
            if cached_available_seats is not None:
                available_seats = int(cached_available_seats)
            else:
                available_seats = schedule.dynamic_capacity - reserved_count
                redis_client.setex(available_seats_key, 300, str(available_seats))

            schedules.append({
                'id': schedule.id,
                'route_name': schedule.route.name.value,
                'departure_time': schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                'available_seats': available_seats,
                'total_seats': schedule.dynamic_capacity,
                'vehicle_plate': schedule.vehicle_plate,
                'driver_name': schedule.driver.name if schedule.driver else None,
                'start_point': schedule.route.start_point,
                'end_point': schedule.route.end_point,
                'is_full': available_seats <= 0,
                'is_booked': schedule.id in user_booked_schedule_ids
            })

        # 缓存结果
        result = {'schedules': schedules}
        redis_client.setex(cache_key, 300, json.dumps(result))

        return jsonify(result)

    except Exception as e:
        logging.error(f"获取可预约班次列表失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

def init_routes_and_schedules():
    """
    初始化路线和班次数据
    """
    try:
        # 检查是否已经存在路线数据
        if Route.query.first() is None:
            # 创建基础路线
            routes = [
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部网安院',
                    end_point='新校区新珈楼门口',
                    departure_time=datetime.strptime('07:00', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部网安院',
                    end_point='新校区新珈楼门口',
                    departure_time=datetime.strptime('10:30', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部网安院',
                    end_point='新校区新珈楼门口',
                    departure_time=datetime.strptime('12:30', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部网安院',
                    end_point='新校区新珈楼门口',
                    departure_time=datetime.strptime('16:30', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部当代楼附近校巴站',
                    end_point='新校区一食堂门口',
                    departure_time=datetime.strptime('18:30', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.A,
                    start_point='武大本部当代楼附近校巴站',
                    end_point='新校区一食堂门口',
                    departure_time=datetime.strptime('19:00', '%H:%M').time(),
                    is_weekend=True
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区一食堂门口',
                    end_point='武大本部当代楼',
                    departure_time=datetime.strptime('06:40', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区新珈楼门口',
                    end_point='武大本部网安院',
                    departure_time=datetime.strptime('08:50', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区新珈楼门口',
                    end_point='武大本部网安院',
                    departure_time=datetime.strptime('13:00', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区新珈楼门口',
                    end_point='武大本部网安院',
                    departure_time=datetime.strptime('17:30', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区新珈楼门口',
                    end_point='武大本部网安院',
                    departure_time=datetime.strptime('18:00', '%H:%M').time()
                ),
                Route(
                    name=RouteNameEnum.B,
                    start_point='新校区一食堂门口',
                    end_point='武大本部当代楼附近校巴站',
                    departure_time=datetime.strptime('6:40', '%H:%M').time(),
                    is_weekend=True
                )
            ]
            db.session.add_all(routes)
            db.session.commit()
            logging.info("路线数据初始化成功")

        # 检查是否已经存在班次数据
        if Schedule.query.first() is None:
            # 获取所有路线
            routes = Route.query.all()
            
            # 获取当前日期
            current_date = datetime.now().date()
            # 计算下个月的最后一天
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1)
            last_day = (next_month.replace(day=1) - timedelta(days=1)).day
            
            # 为未来一个月创建班次
            for i in range(last_day):
                target_date = current_date + timedelta(days=i)
                is_weekend = target_date.weekday() >= 5  # 5和6是周六和周日
                
                for route in routes:
                    # 工作日和周末使用不同的班次规则
                    if is_weekend:
                        # 周末班次
                        if route.is_weekend :
                            time = route.departure_time.strftime('%H%M')
                            # 生成班次ID：年月日+路线编号+时间
                            schedule_id = f"{target_date.strftime('%Y%m%d')}{route.name.value}{time}{route.is_weekend}"
                            
                            # 创建班次
                            schedule = Schedule(
                                id=schedule_id,
                                route_id=route.id,
                                departure_datetime=datetime.combine(target_date, route.departure_time),
                                dynamic_capacity=30,  # 默认座位数
                                status='normal'
                            )
                            db.session.add(schedule)
                    else:
                        if is_weekend == False:
                            # 工作日班次
                            time = route.departure_time.strftime('%H%M')
                            schedule_id = f"{target_date.strftime('%Y%m%d')}{route.name.value}{time}{route.is_weekend}"
                            
                            # 创建班次
                            schedule = Schedule(
                                id=schedule_id,
                                route_id=route.id,
                                departure_datetime=datetime.combine(target_date, route.departure_time),
                                dynamic_capacity=30,  # 默认座位数
                                status='normal'
                            )
                            db.session.add(schedule)
            
            db.session.commit()
            logging.info("班次数据初始化成功")

    except Exception as e:
        logging.error(f"初始化数据失败: {str(e)}")
        db.session.rollback()
        raise e

# 在应用启动时调用初始化函数
def init_app(app):
    """
    初始化应用
    Args:
        app: Flask应用实例
    """
    with app.app_context():
        try:
            init_routes_and_schedules()
        except Exception as e:
            logging.error(f"初始化数据失败: {str(e)}")
            raise e

def update_schedule_cache(schedule_id, user_id=None):
    """更新班次相关的所有缓存"""
    cache_manager.update_schedule_cache(schedule_id, user_id)


@reservation_bp.route('/detail', methods=['GET'])
@jwt_required()
def get_reservation_detail():
    """
    获取单条预约详情
    
    查询参数:
        id: 预约ID
        
    返回:
        成功:
            {
                id: 预约ID
                schedule_id: 班次ID
                seat_number: 座位号
                status: 预约状态
                reserved_at: 预约时间
                qr_code: 预约二维码
            }
        失败:
            error: 错误信息
            
    权限要求:
        需要JWT认证
        只能查看自己的预约记录
    """
    try:
        current_user_id = get_jwt_identity()
        reservation_id = request.args.get('id')
        
        if not reservation_id:
            return jsonify({'error': '缺少预约ID参数'}), 400
            
        # 尝试从Redis缓存获取预约详情
        cache_key = RedisKeys.RESERVATION.format(reservation_id)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            reservation_data = json.loads(cached_data)
            # 检查是否是当前用户的预约
            if reservation_data.get('user_id') != current_user_id:
                return jsonify({'error': '无权查看该预约'}), 403
            return jsonify(reservation_data)
            
        # 从数据库获取预约信息
        reservation = Reservation.query.get(reservation_id)
        
        if not reservation:
            return jsonify({'error': '预约不存在'}), 404
            
        # 检查权限
        if reservation.user_id != current_user_id:
            return jsonify({'error': '无权查看该预约'}), 403
            
        # 构建返回数据
        reservation_data = {
            'id': reservation.id,
            'user_id': current_user_id,
            'schedule_id': reservation.schedule_id,
            'seat_number': reservation.seat_number,
            'status': reservation.status.value,
            'reserved_at': reservation.reserved_at.isoformat(),
            'qr_code': reservation.qr_code
        }
        
        # 缓存预约详情（1小时过期）
        redis_client.setex(
            cache_key,
            3600,
            json.dumps(reservation_data)
        )
            
        return jsonify(reservation_data)
        
    except Exception as e:
        logging.error(f"获取预约详情失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500