import os
import json
import logging
from datetime import datetime
from constants import RedisKeys
from extensions import redis_client
from openai import OpenAI

class AIService:
    def __init__(self):
        """初始化OpenAI客户端"""
        try:
            api_key = os.getenv("TONGYI_API_KEY")
            api_url = os.getenv("TONGYI_API_URL")
            
            if not api_key or not api_url:
                logging.warning("未设置DASHSCOPE_API_KEY或DASHSCOPE_API_URL环境变量，AI分析功能将不可用")
                self.client = None
            else:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=api_url
                )
        except Exception as e:
            logging.error(f"初始化AI服务失败: {str(e)}")
            self.client = None

    def get_analysis(self, statistics, start_date_str, end_date_str):
        """
        获取班次调度建议
        
        Args:
            statistics: 统计数据列表
            start_date_str: 开始日期字符串 (YYYY-MM-DD)
            end_date_str: 结束日期字符串 (YYYY-MM-DD)
            
        Returns:
            dict: 包含调度建议的字典
        """
        try:
            # 如果AI服务未初始化，返回默认分析
            if not self.client:
                return self._get_default_analysis(statistics)

            # 尝试从缓存获取
            cache_key = RedisKeys.AI_ANALYSIS.format(start_date_str, end_date_str)
            cached_analysis = redis_client.get(cache_key)
            if cached_analysis:
                return json.loads(cached_analysis)

            # 计算关键指标
            total_schedules = len(statistics)
            total_reservations = sum(s['total_reservations'] for s in statistics)
            total_checked_in = sum(s['checked_in'] for s in statistics)
            total_seats = sum(s['total_seats'] for s in statistics)
            
            # 计算平均上座率
            avg_occupancy_rate = (total_checked_in / total_seats * 100) if total_seats > 0 else 0

            # 构建提示词
            prompt = f"""请根据以下数据提供班次调度建议：
            
                        统计时间范围：{start_date_str} 至 {end_date_str}
                        总班次数：{total_schedules}
                        总预约数：{total_reservations}
                        总签到数：{total_checked_in}
                        总座位数：{total_seats}
                        平均上座率：{avg_occupancy_rate:.1f}%

                        各路线详细数据：
                        {json.dumps(statistics, ensure_ascii=False, indent=2)}

                        请提供以下建议：
                        1. 是否需要增加或减少班次
                        2. 哪些时段的班次需要调整
                        3. 座位容量是否需要调整
                        4. 其他优化建议

                        请用简洁的语言回答，直接给出具体建议。注意分析时间范围内的趋势变化。注意使用纯文本格式，不要使用markdown格式。"""

            # 调用通义千问API
            completion = self.client.chat.completions.create(
                model="qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的班次调度顾问，请根据数据提供具体的调度建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # 获取建议
            suggestions = completion.choices[0].message.content.strip()

            # 构建分析结果
            analysis = {
                'summary': {
                    'total_schedules': total_schedules,
                    'total_reservations': total_reservations,
                    'total_checked_in': total_checked_in,
                    'total_seats': total_seats,
                    'avg_occupancy_rate': f"{avg_occupancy_rate:.1f}%"
                },
                'suggestions': suggestions
            }

            # 缓存结果（永久保存）
            redis_client.set(cache_key, json.dumps(analysis))
            return analysis

        except Exception as e:
            logging.error(f"AI分析失败: {str(e)}")
            return self._get_default_analysis(statistics)

    def _get_default_analysis(self, statistics):
        """获取默认分析结果"""
        total_schedules = len(statistics)
        total_reservations = sum(s['total_reservations'] for s in statistics)
        total_checked_in = sum(s['checked_in'] for s in statistics)
        total_seats = sum(s['total_seats'] for s in statistics)
        avg_occupancy_rate = (total_checked_in / total_seats * 100) if total_seats > 0 else 0

        return {
            'summary': {
                'total_schedules': total_schedules,
                'total_reservations': total_reservations,
                'total_checked_in': total_checked_in,
                'total_seats': total_seats,
                'avg_occupancy_rate': f"{avg_occupancy_rate:.1f}%"
            },
            'suggestions': '暂时无法提供调度建议，请稍后再试。'
        }

# 创建单例实例
llm_service = AIService() 