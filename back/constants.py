class RedisKeys:
    """Redis 键定义"""
    
    # 管理员相关
    ADMIN_SCHEDULES = 'admin:schedules:{}'  # 管理员班次列表
    ADMIN_STATISTICS = 'admin:statistics:{}:{}'  # 管理员统计数据
    ADMIN_EXPORT = 'admin:export:reservations:{}:{}'  # 导出数据缓存
    SCHEDULE_RESERVATIONS = 'schedule:reservations:{}:{}'  # 班次预约统计
    
    # 司机相关
    DRIVER_SCHEDULES = 'driver:schedules:{}:{}'  # driver:schedules:{driver_id}:{date}
    SCHEDULE_DETAIL = 'schedule:detail:{}'  # schedule:detail:{schedule_id}
    PASSENGER_LIST = 'schedule:passengers:{}:{}'  # schedule:passengers:{schedule_id}:{status}
    RESERVATION_STATS = 'schedule:stats:{}'  # schedule:stats:{schedule_id}
    
    # 预约相关
    RESERVATION = 'reservation:{}'  # 预约信息
    USER_RESERVATIONS = 'user:reservations:{}'  # 用户预约列表
    AVAILABLE_SCHEDULES = 'available:schedules:{}:{}'  # 可预约班次列表
    USER_CANCEL_COUNT = 'user:cancel:count:{}:{}'  # 用户每日取消次数
    SCHEDULE_AVAILABLE_SEATS = 'schedule:available_seats:{}' 
    
    # AI相关
    AI_ANALYSIS = 'ai:analysis:{}:{}'