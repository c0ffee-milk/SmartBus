from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from redis import Redis 
from config import Config

# 初始化扩展
db = SQLAlchemy()
jwt = JWTManager()

# 初始化 Redis
redis_client = Redis(
    host=Config.CACHE_REDIS_HOST,
    port=Config.CACHE_REDIS_PORT,
    db=Config.CACHE_REDIS_DB,
    password=Config.CACHE_REDIS_PASSWORD,
    decode_responses=True
)

def init_extensions(app):
    """初始化所有扩展"""
    db.init_app(app)
    jwt.init_app(app) 