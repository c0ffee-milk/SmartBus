# routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, jwt, redis_client
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from model import User, RoleEnum
import requests
from config import Config
from sqlalchemy.exc import SQLAlchemyError
import logging
import base64
import json
from Cryptodome.Cipher import AES
from utils.csv_utils import verify_user_identity
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

WECHAT_LOGIN_URL = "https://api.weixin.qq.com/sns/jscode2session"

# Redis 键前缀
class RedisKeys:
    USER_CACHE = 'user:{}'  # 用户信息缓存
    LOGIN_ATTEMPTS = 'login_attempts:{}'  # 登录尝试次数
    WECHAT_SESSION = 'wechat:session:{}'  # 微信会话缓存
    REFRESH_TOKEN = 'refresh_token:{}'  # 刷新令牌

# 登录尝试限制配置
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 1800  # 30分钟

def check_login_attempts(school_id):
    """检查登录尝试次数"""
    key = RedisKeys.LOGIN_ATTEMPTS.format(school_id)
    attempts = redis_client.get(key)
    
    if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
        return False
    
    # 增加尝试次数
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, LOGIN_TIMEOUT)
    pipe.execute()
    return True

def clear_login_attempts(school_id):
    """清除登录尝试次数"""
    key = RedisKeys.LOGIN_ATTEMPTS.format(school_id)
    redis_client.delete(key)

def cache_user_info(user):
    """缓存用户信息"""
    key = RedisKeys.USER_CACHE.format(user.id)
    user_data = {
        'id': user.id,
        'role': user.role.value,
        'name': user.name,
        'school_id': user.school_id,
        'wechat_openid': user.wechat_openid
    }
    redis_client.setex(key, 3600, json.dumps(user_data))  # 缓存1小时

def get_cached_user(user_id):
    """获取缓存的用户信息"""
    key = RedisKeys.USER_CACHE.format(user_id)
    data = redis_client.get(key)
    return json.loads(data) if data else None

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        code = request.json.get('code')
        name = request.json.get('name')
        school_id = request.json.get('school_id')
        
        if not all([code, name, school_id]):
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 检查登录尝试次数
        if not check_login_attempts(school_id):
            return jsonify({'error': '登录尝试次数过多，请稍后再试'}), 429
        
        # 验证用户身份
        user_info = verify_user_identity(name, school_id)
        if not user_info:
            return jsonify({'error': '身份验证失败，请确认姓名和学工号是否正确'}), 401

        # 检查微信会话缓存
        session_key = RedisKeys.WECHAT_SESSION.format(code)
        cached_session = redis_client.get(session_key)
        
        if cached_session:
            response = json.loads(cached_session)
        else:
            # 请求微信接口验证 code
            try:
                params = {
                    'appid': Config.WECHAT_APPID,
                    'secret': Config.WECHAT_SECRET,
                    'js_code': code,
                    'grant_type': 'authorization_code'
                }
                response = requests.get(WECHAT_LOGIN_URL, params=params, timeout=5).json()
                
                # 缓存微信会话信息（5分钟）
                if 'errcode' not in response:
                    redis_client.setex(session_key, 300, json.dumps(response))
                    
            except requests.RequestException as e:
                logging.error(f"微信接口请求失败: {str(e)}")
                return jsonify({'error': '微信服务暂时不可用'}), 503

        if 'errcode' in response:
            logging.error(f"微信登录失败: {response['errmsg']}")
            return jsonify({'error': '微信登录失败', 'detail': response['errmsg']}), 400

        openid = response['openid']

        # 查询或创建用户
        user = User.query.filter_by(wechat_openid=openid).first()
        if not user:
            user = User(
                wechat_openid=openid,
                role=user_info['role'],
                name=name,
                school_id=school_id,
            )
            db.session.add(user)
            db.session.commit()

        # 生成令牌
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # 缓存刷新令牌
        redis_client.setex(
            RedisKeys.REFRESH_TOKEN.format(user.id),
            int(timedelta(days=30).total_seconds()),
            refresh_token
        )
        
        # 缓存用户信息
        cache_user_info(user)
        
        # 清除登录尝试次数
        clear_login_attempts(school_id)

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'role': user.role.value,
                'name': user.name,
                'school_id': user.school_id,
            }
        })

    except Exception as e:
        logging.error(f"登录过程发生错误: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新访问令牌"""
    try:
        current_user_id = get_jwt_identity()
        
        # 验证刷新令牌
        stored_token = redis_client.get(RedisKeys.REFRESH_TOKEN.format(current_user_id))
        if not stored_token:
            return jsonify({'error': '刷新令牌无效'}), 401
            
        # 创建新的访问令牌
        access_token = create_access_token(identity=current_user_id)
        
        # 获取缓存的用户信息
        user_data = get_cached_user(current_user_id)
        if not user_data:
            user = User.query.get(current_user_id)
            if user:
                cache_user_info(user)
                user_data = get_cached_user(current_user_id)
        
        return jsonify({
            'access_token': access_token,
            'user': user_data
        })
        
    except Exception as e:
        logging.error(f"刷新令牌失败: {str(e)}")
        return jsonify({'error': '系统错误'}), 500





