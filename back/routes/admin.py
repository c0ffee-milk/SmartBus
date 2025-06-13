"""
管理员模块
提供班车管理、数据导出和统计功能
"""

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from model import db, User, Schedule, Route, Reservation, RoleEnum, ReservationStatusEnum
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd
import io
import logging
from extensions import redis_client
import json
from config import Config
from cache import cache_manager
from constants import RedisKeys
from services.ai_service import llm_service

# 创建蓝图
admin_bp = Blueprint('admin', __name__)


def admin_required(fn):
    """
    管理员权限检查装饰器
    用于确保只有管理员角色可以访问特定接口
    
    Args:
        fn: 被装饰的函数
        
    Returns:
        wrapper: 包装后的函数
        
    Raises:
        403: 如果用户不是管理员
    """
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != RoleEnum.admin:
            return jsonify({'error': '需要管理员权限'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# 已对接
@admin_bp.route('/schedules', methods=['GET'])
@admin_required
def list_schedules():
    """
    获取所有班次信息
    
    查询参数:
        date: 日期 (YYYY-MM-DD)，默认为今天
        
    返回:
        成功:
            schedules: [
                {
                    id: 班次ID
                    route_name: 路线名称
                    departure_time: 发车时间
                    start_point: 起点
                    end_point: 终点
                    capacity: 座位数
                    vehicle_plate: 车牌号
                    driver_name: 司机姓名
                    status: 班次状态
                    reserved_count: 已预约数量
                }
            ]
        失败:
            error: 错误信息
    """
    try:
        date_str = request.args.get('date')
        if date_str:
            try:
                query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': '日期格式不正确'}), 400
        else:
            query_date = datetime.now().date()

        # 构建缓存键
        cache_key = RedisKeys.ADMIN_SCHEDULES.format(query_date.strftime('%Y-%m-%d'))
        
        # 尝试从缓存获取数据
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))

        # 缓存未命中，从数据库获取
        schedules = Schedule.query.filter(
            func.date(Schedule.departure_datetime) == query_date
        ).all()

        result = {
            'schedules': [{
                'id': schedule.id,
                'route_id': schedule.route_id,
                'route_name': schedule.route.name.value,
                'departure_time': schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                'start_point': schedule.route.start_point,
                'end_point': schedule.route.end_point,
                'capacity': schedule.dynamic_capacity,
                'vehicle_plate': schedule.vehicle_plate,
                'driver_name': schedule.driver.name if schedule.driver else None,
                'status': schedule.status.value,
                'reserved_count': Reservation.query.filter_by(
                    schedule_id=schedule.id,
                    status=ReservationStatusEnum.active
                ).count()
            } for schedule in schedules]
        }
    
        # 存入缓存，设置5分钟过期
        redis_client.setex(cache_key, 300, json.dumps(result))
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"获取班次列表失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500
    

# 已对接
@admin_bp.route('/schedules', methods=['POST'])
@admin_required
def create_schedule():
    """
    创建新班次
    
    请求体:
        direction: 方向（A或B）
        start_point: 始发站
        end_point: 终点站
        departure_datetime: 发车时间 (YYYY-MM-DD HH:MM)
        dynamic_capacity: 座位数
        vehicle_plate: 车牌号（可选）
        driver_id: 司机ID（可选）
        
    返回:
        成功:
            message: 创建成功信息
            schedule: {
                id: 班次ID
                route_name: 路线名称
                departure_time: 发车时间
                capacity: 座位数
            }
        失败:
            error: 错误信息
    """
    try:
        data = request.json
        required_fields = ['direction', 'start_point', 'end_point', 'departure_datetime', 'dynamic_capacity']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '缺少必要字段'}), 400

        # 查找或创建路线
        route = Route.query.filter_by(
            name=data['direction'],
            start_point=data['start_point'],
            end_point=data['end_point'],
            departure_time=datetime.strptime(data['departure_datetime'], '%Y-%m-%d %H:%M').time()
        ).first()

        if not route:
            # 创建新路线
            route = Route(
                name=data['direction'],
                start_point=data['start_point'],
                end_point=data['end_point'],
                departure_time=datetime.strptime(data['departure_datetime'], '%Y-%m-%d %H:%M').time()
            )
            db.session.add(route)
            db.session.flush()  # 获取新创建的route_id

        departure_time=datetime.strptime(data['departure_datetime'], '%Y-%m-%d %H:%M').time()
        is_weekend = departure_time.strftime('%w') in ['0', '6']
        schedule_id = f"{departure_time.strftime('%Y%m%d')}{data['start_point']}-->{data['end_point']}{departure_time.strftime('%H%M')}{is_weekend}"
        existing_schedule = Schedule.query.get(schedule_id)
        if existing_schedule:
            return jsonify({'error': '班次已存在'}), 400
        
        # 创建班次
        schedule = Schedule(
            id = schedule_id,
            route_id=route.id,
            departure_datetime=datetime.strptime(data['departure_datetime'], '%Y-%m-%d %H:%M'),
            dynamic_capacity=data['dynamic_capacity'],
            vehicle_plate=data.get('vehicle_plate'),
            driver_id=data.get('driver_id'),
            status='normal'
        )

        db.session.add(schedule)
        db.session.commit()

        # 更新缓存
        cache_manager.update_schedule_cache(schedule.id)

        return jsonify({
            'message': '班次创建成功',
            'schedule': {
                'id': schedule.id,
                'route_name': schedule.route.name.value,
                'departure_time': schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                'capacity': schedule.dynamic_capacity
            }
        })
    except Exception as e:
        logging.error(f"创建班次失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

# 已对接
@admin_bp.route('/schedules/<string:schedule_id>', methods=['PUT'])
@admin_required
def update_schedule(schedule_id):
    """
    更新班次信息
    
    路径参数:
        schedule_id: 班次ID
        
    请求体:
        departure_datetime: 发车时间 (YYYY-MM-DD HH:MM)（可选）
        dynamic_capacity: 座位数（可选）
        vehicle_plate: 车牌号（可选）
        driver_id: 司机ID（可选）
        status: 班次状态（可选）
        
    返回:
        成功:
            message: 更新成功信息
            schedule: {
                id: 班次ID
                route_name: 路线名称
                departure_time: 发车时间
                capacity: 座位数
                status: 班次状态
            }
        失败:
            error: 错误信息
    """
    try:
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'error': '班次不存在'}), 404

        data = request.json
        if 'departure_datetime' in data:
            schedule.departure_datetime = datetime.strptime(data['departure_datetime'], '%Y-%m-%d %H:%M')
        if 'dynamic_capacity' in data:
            schedule.dynamic_capacity = data['dynamic_capacity']
        if 'vehicle_plate' in data:
            schedule.vehicle_plate = data['vehicle_plate']
        if 'driver_id' in data:
            schedule.driver_id = data['driver_id']
        if 'status' in data:
            schedule.status = data['status']

        db.session.commit()

        # 更新缓存
        cache_manager.update_schedule_cache(schedule_id)

        return jsonify({
            'message': '班次更新成功',
            'schedule': {
                'id': schedule.id,
                'route_name': schedule.route.name.value,
                'departure_time': schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                'capacity': schedule.dynamic_capacity,
                'status': schedule.status.value
            }
        })
    except Exception as e:
        logging.error(f"更新班次失败: {str(e)}")
        db.session.rollback()
        return jsonify({'error': '系统错误'}), 500

# 已对接
@admin_bp.route('/schedules/<string:schedule_id>', methods=['DELETE'])
@admin_required
def delete_schedule(schedule_id):
    """
    删除班次
    
    路径参数:
        schedule_id: 班次ID
        
    返回:
        成功:
            message: 删除成功信息
        失败:
            error: 错误信息
            
    权限要求:
        需要管理员权限
        
    业务规则:
        只能删除没有活跃（active）和已签到（checked_in）预约的班次
    """
    try:
        # 获取班次信息
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'error': '班次不存在'}), 404

        # 检查是否有活跃或已签到的预约
        active_reservations = Reservation.query.filter(
            Reservation.schedule_id == schedule_id,
            Reservation.status.in_([ReservationStatusEnum.active, ReservationStatusEnum.checked_in])
        ).count()
        
        if active_reservations > 0:
            return jsonify({'error': '该班次有活跃或已签到的预约，无法删除'}), 400

        # 获取其他状态的预约（已取消或缺席的预约）
        other_reservations = Reservation.query.filter(
            Reservation.schedule_id == schedule_id,
            Reservation.status.in_([ReservationStatusEnum.canceled, ReservationStatusEnum.absent])
        ).all()

        # 删除其他状态的预约
        if other_reservations:
            for reservation in other_reservations:
                db.session.delete(reservation)
                # 删除相关缓存
                cache_manager.delete_reservation_cache(reservation.id)

        # 更新缓存
        cache_manager.update_schedule_cache(schedule_id)

        # 删除班次
        db.session.delete(schedule)
        db.session.commit()


        return jsonify({'message': '班次删除成功'})

    except Exception as e:
        db.session.rollback()
        logging.error(f"删除班次失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

# 已对接
@admin_bp.route('/export/reservations', methods=['GET'])
@admin_required
def export_reservations():
    """
    导出预约数据
    
    查询参数:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        
    返回:
        成功:
            Excel文件，包含以下字段：
            - 预约ID
            - 用户姓名
            - 学号
            - 班次ID
            - 路线
            - 出发时间
            - 起点
            - 终点
            - 座位号
            - 状态
            - 预约时间
            - 签到时间
            - 取消时间
        失败:
            error: 错误信息
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({'error': '请指定日期范围'}), 400

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': '日期格式不正确'}), 400
        
        # 构建缓存键
        cache_key = RedisKeys.ADMIN_EXPORT.format(start_date, end_date)
        
        # 尝试从缓存获取数据
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return send_file(
                io.BytesIO(cached_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'预约数据_{start_date}_{end_date}.xlsx'
            )

        # 查询预约数据
        reservations = Reservation.query.join(Schedule).filter(
            func.date(Schedule.departure_datetime).between(start_date, end_date)
        ).all()

        # 准备数据
        data = []
        for reservation in reservations:
            data.append({
                '预约ID': reservation.id,
                '用户姓名': reservation.user.name,
                '学号': reservation.user.school_id,
                '班次ID': reservation.schedule_id,
                '路线': reservation.schedule.route.name.value,
                '出发时间': reservation.schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                '起点': reservation.schedule.route.start_point,
                '终点': reservation.schedule.route.end_point,
                '座位号': reservation.seat_number,
                '状态': reservation.status.value,
                '预约时间': reservation.reserved_at.strftime('%Y-%m-%d %H:%M'),
                '签到时间': reservation.checked_in_at.strftime('%Y-%m-%d %H:%M') if reservation.checked_in_at else None,
                '取消时间': reservation.canceled_at.strftime('%Y-%m-%d %H:%M') if reservation.canceled_at else None
            })

        # 创建Excel文件
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='预约数据')

        output.seek(0)
        excel_data = output.getvalue()

        # 存入缓存，设置1小时过期
        redis_client.setex(cache_key, 3600, excel_data)

        return send_file(
            io.BytesIO(excel_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'预约数据_{start_date}_{end_date}.xlsx'
        )

    except Exception as e:
        logging.error(f"导出预约数据失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

# 已对接
@admin_bp.route('/statistics', methods=['GET'])
@admin_required
def get_statistics():
    """
    获取统计数据
    
    查询参数:
        start_date: 开始日期 (YYYY-MM-DD)，默认为今天
        end_date: 结束日期 (YYYY-MM-DD)，默认为开始日期
        
    返回:
        成功:
            start_date: 开始日期
            end_date: 结束日期
            statistics: [
                {
                    schedule_id: 班次ID
                    route_name: 路线名称
                    departure_time: 发车时间
                    start_point: 起点
                    end_point: 终点
                    total_reservations: 总预约数
                    active_reservations: 活跃预约数
                    checked_in: 已签到数
                    absent: 缺席数
                    canceled: 取消数
                    occupancy_rate: 上座率
                    total_seats: 总座位数
                }
            ]
            analysis: {
                summary: {
                    total_schedules: 总班次数
                    total_reservations: 总预约数
                    total_checked_in: 总签到数
                    total_seats: 总座位数
                    avg_occupancy_rate: 平均上座率
                }
                suggestions: 班次调度建议
            }
        失败:
            error: 错误信息
    """
    try:
        # 获取日期参数
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # 处理日期参数
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date = datetime.now().date()
                
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date = start_date
            
            if start_date >= datetime.now().date():
                return jsonify({'error': '起始日期不能早于今天'}), 400

            if end_date < start_date:
                return jsonify({'error': '结束日期不能早于开始日期'}), 400
                
            # 限制查询时间范围不超过14天
            if (end_date - start_date).days > 365:
                return jsonify({'error': '查询时间范围不能超过365天'}), 400
                
        except ValueError:
            return jsonify({'error': '日期格式不正确'}), 400

        # 构建缓存键
        cache_key = RedisKeys.ADMIN_STATISTICS.format(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # 尝试从缓存获取数据
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))

        # 缓存未命中，从数据库获取
        schedules = Schedule.query.filter(
            func.date(Schedule.departure_datetime).between(start_date, end_date)
        ).all()

        statistics = []
        for schedule in schedules:
            # 使用 Redis 管道批量获取预约统计
            pipe = redis_client.pipeline()
            for status in ['total', 'active', 'checked_in', 'absent', 'canceled']:
                pipe.get(RedisKeys.SCHEDULE_RESERVATIONS.format(schedule.id, status))
            results = pipe.execute()

            # 如果缓存中没有数据，从数据库获取并更新缓存
            if not all(results):
                total = Reservation.query.filter_by(schedule_id=schedule.id).count()
                active = Reservation.query.filter_by(
                    schedule_id=schedule.id,
                    status=ReservationStatusEnum.active
                ).count()
                checked_in = Reservation.query.filter_by(
                    schedule_id=schedule.id,
                    status=ReservationStatusEnum.checked_in
                ).count()
                absent = Reservation.query.filter_by(
                    schedule_id=schedule.id,
                    status=ReservationStatusEnum.absent
                ).count()
                canceled = Reservation.query.filter_by(
                    schedule_id=schedule.id,
                    status=ReservationStatusEnum.canceled
                ).count()

                # 更新缓存
                pipe = redis_client.pipeline()
                for status, value in [
                    ('total', total),
                    ('active', active),
                    ('checked_in', checked_in),
                    ('absent', absent),
                    ('canceled', canceled)
                ]:
                    pipe.setex(
                        RedisKeys.SCHEDULE_RESERVATIONS.format(schedule.id, status),
                        300,
                        str(value)
                    )
                pipe.execute()
            else:
                total, active, checked_in, absent, canceled = [int(r) if r else 0 for r in results]

            statistics.append({
                'schedule_id': schedule.id,
                'route_name': schedule.route.name.value,
                'departure_time': schedule.departure_datetime.strftime('%Y-%m-%d %H:%M'),
                'start_point': schedule.route.start_point,
                'end_point': schedule.route.end_point,
                'total_reservations': total,
                'active_reservations': active,
                'checked_in': checked_in,
                'absent': absent,
                'canceled': canceled,
                'occupancy_rate': f"{(checked_in / schedule.dynamic_capacity * 100):.1f}%" if schedule.dynamic_capacity > 0 else "0%",
                'total_seats': schedule.dynamic_capacity
            })

        # 获取AI分析
        analysis = llm_service.get_analysis(
            statistics,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        result = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'statistics': statistics,
            'analysis': analysis
        }

        # 存入缓存，永久
        redis_client.set(cache_key, json.dumps(result))
        return jsonify(result)

    except Exception as e:
        logging.error(f"获取统计数据失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500