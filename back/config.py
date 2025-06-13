import os
from datetime import timedelta

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY', '114514')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///shuttle_bus.db')  # 使用 SQLite 作为开发数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG  # 在调试模式下打印SQL语句
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', '114514')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)  # token过期时间
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 刷新token过期时间
    
    # 微信小程序配置
    WECHAT_APPID = os.environ.get('WECHAT_APPID', 'your-wechat-appid')
    WECHAT_SECRET = os.environ.get('WECHAT_SECRET', 'your-wechat-secret')
    
    # 缓存配置
    CACHE_TYPE = 'redis'
    CACHE_REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    CACHE_REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    CACHE_REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    CACHE_REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Redis 配置
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # 跨域配置
    CORS_ORIGINS = ['*']  # 在生产环境中应该设置具体的域名
    
    # 系统配置
    SYSTEM_NAME = '校园巴士系统'
    SYSTEM_VERSION = '1.0.0'
    SYSTEM_DESCRIPTION = '校园巴士预约和管理系统'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # 安全配置
    PASSWORD_SALT = os.environ.get('PASSWORD_SALT', 'your-salt-here')
    MAX_LOGIN_ATTEMPTS = 5  # 最大登录尝试次数
    LOGIN_TIMEOUT = 30  # 登录超时时间（分钟）
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大文件大小（16MB）
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

    
    # 系统配置
    SYSTEM_NAME = '校园巴士系统'
    SYSTEM_VERSION = '1.0.0'
    SYSTEM_DESCRIPTION = '校园巴士预约和管理系统'
    
