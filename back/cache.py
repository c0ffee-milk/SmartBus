from model import Schedule, Reservation, ReservationStatusEnum
from extensions import redis_client, db
from constants import RedisKeys

class CacheManager:
    """缓存管理器，统一管理所有缓存更新操作"""
    
    @staticmethod
    def update_available_seats_cache(schedule_id):
        """更新班次可用座位数缓存"""
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return

        available_seats = schedule.dynamic_capacity - Reservation.query.filter_by(
            schedule_id=schedule_id,
            status=ReservationStatusEnum.active
        ).count()
        redis_client.setex(
            RedisKeys.SCHEDULE_AVAILABLE_SEATS.format(schedule_id),
            300,
            str(available_seats)
        )

    @staticmethod
    def update_admin_cache(schedule_id, date_str):
        """更新管理员相关缓存"""
        redis_client.delete(RedisKeys.ADMIN_SCHEDULES.format(date_str))
        redis_client.delete(RedisKeys.ADMIN_STATISTICS.format(date_str))
        
        for status in ['total', 'active', 'checked_in', 'absent', 'canceled']:
            redis_client.delete(RedisKeys.SCHEDULE_RESERVATIONS.format(schedule_id, status))

    @staticmethod
    def update_driver_cache(schedule_id, date_str, driver_id=None):
        """更新司机相关缓存"""
        redis_client.delete(RedisKeys.SCHEDULE_DETAIL.format(schedule_id))
        
        for status in ['all', 'active', 'checked_in', 'canceled', 'absent']:
            redis_client.delete(RedisKeys.PASSENGER_LIST.format(schedule_id, status))
        
        redis_client.delete(RedisKeys.RESERVATION_STATS.format(schedule_id))
        
        if driver_id:
            for status in ['normal', 'canceled', 'delayed']:
                redis_client.delete(RedisKeys.DRIVER_SCHEDULES.format(driver_id, date_str, status))
            redis_client.delete(RedisKeys.DRIVER_SCHEDULES.format(driver_id, date_str))

    @staticmethod
    def update_reservation_cache(schedule_id, date_str, user_id=None):
        """更新预约相关缓存"""
        pattern = RedisKeys.AVAILABLE_SCHEDULES.format(f"{date_str}:*", '*')
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)

        if user_id:
            redis_client.delete(RedisKeys.USER_RESERVATIONS.format(user_id))
        else:
            user_ids = db.session.query(Reservation.user_id).filter_by(
                schedule_id=schedule_id
            ).distinct().all()
            for user_id in user_ids:
                redis_client.delete(RedisKeys.USER_RESERVATIONS.format(user_id[0]))

    @staticmethod
    def update_schedule_cache(schedule_id, user_id=None):
        """统一更新所有与班次相关的缓存"""
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return

        date_str = schedule.departure_datetime.strftime('%Y-%m-%d')
        
        CacheManager.update_available_seats_cache(schedule_id)
        CacheManager.update_admin_cache(schedule_id, date_str)
        CacheManager.update_driver_cache(schedule_id, date_str, schedule.driver_id)
        CacheManager.update_reservation_cache(schedule_id, date_str, user_id)

# 创建缓存管理器实例
cache_manager = CacheManager()