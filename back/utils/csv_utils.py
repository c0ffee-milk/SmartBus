import csv
import os
from typing import Optional, Dict

def verify_user_identity(name: str, school_id: str) -> Optional[Dict]:
    """
    从 CSV 文件中验证用户身份
    
    Args:
        name: 用户姓名
        school_id: 学工号
        
    Returns:
        如果验证成功，返回包含用户信息的字典；否则返回 None
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.csv')
    
    if not os.path.exists(csv_path):
        return None
        
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['name'] == name and row['school_id'] == school_id:
                    return {
                        'name': row['name'],
                        'school_id': row['school_id'],
                        'role': row.get('role', 'student'),  # 如果没有指定角色，默认为学生
                    }
    except Exception as e:
        print(f"读取 CSV 文件时出错: {str(e)}")
        return None
        
    return None 