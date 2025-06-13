from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from model import db, User, Schedule, Reservation, ReservationStatusEnum, RoleEnum, Route, ScheduleStatusEnum
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
import logging
from extensions import redis_client
import json
from cache import cache_manager
from constants import RedisKeys

driver_bp = Blueprint('driver', __name__)

def get_cached_schedules(driver_id, date, status=None):
    """获取缓存的班次列表"""
    key = RedisKeys.DRIVER_SCHEDULES.format(driver_id, date)
    if status:
        key = f"{key}:{status}"
    return redis_client.get(key)

def cache_schedules(driver_id, date, data, status=None):
    """缓存班次列表"""
    key = RedisKeys.DRIVER_SCHEDULES.format(driver_id, date)
    if status:
        key = f"{key}:{status}"
    redis_client.setex(key, 300, json.dumps(data))  # 缓存5分钟

def get_cached_schedule_detail(schedule_id):
    """获取缓存的班次详情"""
    key = RedisKeys.SCHEDULE_DETAIL.format(schedule_id)
    return redis_client.get(key)

def cache_schedule_detail(schedule_id, data):
    """缓存班次详情"""
    key = RedisKeys.SCHEDULE_DETAIL.format(schedule_id)
    redis_client.setex(key, 300, json.dumps(data))  # 缓存5分钟

def get_cached_passenger_list(schedule_id, status=None):
    """获取缓存的乘客名单"""
    key = RedisKeys.PASSENGER_LIST.format(schedule_id, status or 'all')
    return redis_client.get(key)

def cache_passenger_list(schedule_id, data, status=None):
    """缓存乘客名单"""
    key = RedisKeys.PASSENGER_LIST.format(schedule_id, status or 'all')
    redis_client.setex(key, 300, json.dumps(data))  # 缓存5分钟

def get_reservation_stats(schedule_id):
    """获取预约统计信息"""
    key = RedisKeys.RESERVATION_STATS.format(schedule_id)
    stats = redis_client.get(key)
    if stats:
        return json.loads(stats)
    
    # 从数据库获取统计信息
    total = Reservation.query.filter_by(
        schedule_id=schedule_id,
        status=ReservationStatusEnum.active
    ).count()
    
    checked_in = Reservation.query.filter_by(
        schedule_id=schedule_id,
        status=ReservationStatusEnum.checked_in
    ).count()
    
    stats = {
        'total': total,
        'checked_in': checked_in
    }
    
    # 缓存统计信息
    redis_client.setex(key, 300, json.dumps(stats))
    return stats

@driver_bp.route('/schedules', methods=['GET'])
@jwt_required()
def list_driver_schedules():
    """
    获取司机负责的班次列表
    查询参数:
        date: 日期（可选，格式：YYYY-MM-DD）
        status: 班次状态（可选，normal/canceled/delayed）
    返回:
        成功:
            schedules: [
                {
                    id: 班次ID
                    route_name: 路线名称
                    start_point: 起点
                    end_point: 终点
                    departure_time: 发车时间
                    departure_datetime: 具体发车日期时间
                    vehicle_plate: 车牌号
                    status: 班次状态
                    total_seats: 总座位数
                    reserved_seats: 已预约座位数
                    checked_in_seats: 已签到座位数
                }
            ]
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证，且用户角色必须为司机
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查权限
        if user.role != RoleEnum.driver:
            return jsonify({'error': '只有司机可以查看班次信息'}), 403

        # 获取查询参数
        date = request.args.get('date')
        status = request.args.get('status')

        # 尝试从缓存获取数据
        if date:
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d').date()
                cached_data = get_cached_schedules(current_user_id, date, status)
                if cached_data:
                    return jsonify(json.loads(cached_data))
            except ValueError:
                return jsonify({'error': '日期格式不正确'}), 400

        # 构建查询
        query = Schedule.query.filter_by(driver_id=current_user_id)
        
        if date:
            query = query.filter(db.func.date(Schedule.departure_datetime) == target_date)
        if status:
            query = query.filter_by(status=status)

        # 获取所有班次
        schedules = query.order_by(Schedule.departure_datetime.desc()).all()

        result = {
            'schedules': [{
                'id': schedule.id,
                'route_name': schedule.route.name.value,
                'start_point': schedule.route.start_point,
                'end_point': schedule.route.end_point,
                'departure_time': schedule.route.departure_time.strftime('%H:%M'),
                'departure_datetime': schedule.departure_datetime.isoformat(),
                'vehicle_plate': schedule.vehicle_plate,
                'status': schedule.status.value,
                'total_seats': schedule.dynamic_capacity,
                'reserved_seats': get_reservation_stats(schedule.id)['total'],
                'checked_in_seats': get_reservation_stats(schedule.id)['checked_in']
            } for schedule in schedules]
        }

        # 缓存结果
        if date:
            cache_schedules(current_user_id, date, result, status)

        return jsonify(result)

    except Exception as e:
        logging.error(f"获取司机班次列表失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

@driver_bp.route('/schedules/<string:schedule_id>', methods=['GET'])
@jwt_required()
def get_schedule_detail(schedule_id):
    """
    获取班次详细信息
    Args:
        schedule_id: 班次ID
    返回:
        成功:
            schedule: {
                id: 班次ID
                route_name: 路线名称
                start_point: 起点
                end_point: 终点
                departure_time: 发车时间
                departure_datetime: 具体发车日期时间
                vehicle_plate: 车牌号
                status: 班次状态
                total_seats: 总座位数
                reserved_seats: 已预约座位数
                checked_in_seats: 已签到座位数
                reservations: [
                    {
                        id: 预约ID
                        user_name: 乘客姓名
                        seat_number: 座位号
                        status: 预约状态
                        checked_in_at: 签到时间
                    }
                ]
            }
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证，且用户角色必须为司机
    业务规则:
        只能查看自己负责的班次
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查权限
        if user.role != RoleEnum.driver:
            return jsonify({'error': '只有司机可以查看班次信息'}), 403

        # 尝试从缓存获取数据
        cached_data = get_cached_schedule_detail(schedule_id)
        if cached_data:
            return jsonify(json.loads(cached_data))

        # 获取班次信息
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'error': '班次不存在'}), 404

        # 检查是否是自己的班次
        if schedule.driver_id != current_user_id:
            return jsonify({'error': '无权查看此班次信息'}), 403

        # 获取预约信息
        reservations = Reservation.query.filter_by(schedule_id=schedule_id).all()
        reservation_list = [{
            'id': r.id,
            'user_name': r.user.name,
            'seat_number': r.seat_number,
            'status': r.status.value,
            'checked_in_at': r.checked_in_at.isoformat() if r.checked_in_at else None
        } for r in reservations]

        result = {
            'schedule': {
                'id': schedule.id,
                'route_name': schedule.route.name.value,
                'start_point': schedule.route.start_point,
                'end_point': schedule.route.end_point,
                'departure_time': schedule.route.departure_time.strftime('%H:%M'),
                'departure_datetime': schedule.departure_datetime.isoformat(),
                'vehicle_plate': schedule.vehicle_plate,
                'status': schedule.status.value,
                'total_seats': schedule.dynamic_capacity,
                'reserved_seats': get_reservation_stats(schedule.id)['total'],
                'checked_in_seats': get_reservation_stats(schedule.id)['checked_in'],
                'reservations': reservation_list
            }
        }

        # 缓存结果
        cache_schedule_detail(schedule_id, result)

        return jsonify(result)

    except Exception as e:
        logging.error(f"获取班次详情失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

@driver_bp.route('/schedules/<string:schedule_id>/passengers', methods=['GET'])
@jwt_required()
def get_passenger_list(schedule_id):
    """
    获取班次乘客名单
    Args:
        schedule_id: 班次ID
    查询参数:
        status: 预约状态筛选（可选，active/checked_in/canceled/absent）
    返回:
        成功:
            passengers: [
                {
                    id: 预约ID
                    user_name: 乘客姓名
                    seat_number: 座位号
                    status: 预约状态
                    checked_in_at: 签到时间
                }
            ]
        失败:
            error: 错误信息
    权限要求:
        需要JWT认证，且用户角色必须为司机
    业务规则:
        1. 只能查看自己负责的班次
        2. 可以按预约状态筛选乘客
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # 检查权限
        if user.role != RoleEnum.driver:
            return jsonify({'error': '只有司机可以查看乘客名单'}), 403

        # 获取查询参数
        status = request.args.get('status')

        # 尝试从缓存获取数据
        cached_data = get_cached_passenger_list(schedule_id, status)
        if cached_data:
            return jsonify(json.loads(cached_data))

        # 获取班次信息
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'error': '班次不存在'}), 404

        # 检查是否是自己的班次
        if schedule.driver_id != current_user_id:
            return jsonify({'error': '无权查看此班次信息'}), 403

        # 构建查询
        query = Reservation.query.filter_by(schedule_id=schedule_id)
        if status:
            query = query.filter_by(status=ReservationStatusEnum[status])

        # 获取所有预约信息
        reservations = query.all()
        passenger_list = [{
            'id': r.id,
            'user_name': r.user.name,
            'seat_number': r.seat_number,
            'status': r.status.value,
            'checked_in_at': r.checked_in_at.isoformat() if r.checked_in_at else None
        } for r in reservations]

        result = {
            'passengers': passenger_list
        }

        # 缓存结果
        cache_passenger_list(schedule_id, result, status)

        return jsonify(result)

    except Exception as e:
        logging.error(f"获取乘客名单失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500


def update_driver_cache(schedule_id):
    """更新司机相关的所有缓存"""
    cache_manager.update_schedule_cache(schedule_id)