"""
天气技能 - WeatherSkill

提供天气查询功能，支持情绪感知和记忆上下文
"""

import asyncio
import re
from typing import Dict, Any
from .agent_skills import AgentSkill


class WeatherSkill(AgentSkill):
    """
    天气查询技能
    """
    
    def __init__(self):
        """
        初始化天气技能
        """
        super().__init__()
        self.name = "WeatherSkill"
        self.description = "查询天气信息"
        self.keywords = ["天气", "温度", "晴", "雨", "雪", "预报", "天气怎么样"]
    
    async def execute(self, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行天气查询
        
        Args:
            query: 用户查询文本
            emotion_state: 当前情绪状态
            memory_context: 记忆上下文
            
        Returns:
            Dict: 技能执行结果
        """
        # 提取城市名称
        city = self._extract_city(query)
        if not city:
            return self.format_response(
                success=False,
                result={},
                emotion_update={"sadness": 0.1},
                memory_update="用户尝试查询天气但未指定城市",
                message="请告诉我你想查询哪个城市的天气"
            )
        
        # 模拟天气查询（实际应用中可以调用真实的天气API）
        weather_data = await self._get_weather(city)
        
        if not weather_data:
            return self.format_response(
                success=False,
                result={},
                emotion_update={"sadness": 0.2},
                memory_update=f"查询{city}天气失败",
                message=f"抱歉，暂时无法查询{city}的天气信息"
            )
        
        # 构建回复消息
        message = self._format_weather_message(city, weather_data)
        
        # 情绪更新：根据天气状况调整情绪
        emotion_update = self._get_emotion_update(weather_data)
        
        # 记忆更新
        memory_update = f"查询了{city}的天气，当前温度{weather_data['temperature']}°C，天气{weather_data['condition']}"
        
        return self.format_response(
            success=True,
            result=weather_data,
            emotion_update=emotion_update,
            memory_update=memory_update,
            message=message
        )
    
    def _extract_city(self, query: str) -> str:
        """
        从查询中提取城市名称
        
        Args:
            query: 用户查询文本
            
        Returns:
            str: 城市名称
        """
        # 简单的城市提取逻辑
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆"]
        for city in cities:
            if city in query:
                return city
        return "北京"  # 默认北京
    
    async def _get_weather(self, city: str) -> Dict[str, Any]:
        """
        获取天气信息
        
        Args:
            city: 城市名称
            
        Returns:
            Dict: 天气数据
        """
        # 模拟天气数据
        await asyncio.sleep(0.5)  # 模拟网络延迟
        
        # 模拟不同城市的天气
        weather_data = {
            "北京": {
                "temperature": 22,
                "condition": "晴",
                "humidity": 45,
                "wind": "微风",
                "forecast": ["晴", "晴", "多云"]
            },
            "上海": {
                "temperature": 25,
                "condition": "多云",
                "humidity": 60,
                "wind": "东风",
                "forecast": ["多云", "阴", "小雨"]
            },
            "广州": {
                "temperature": 28,
                "condition": "晴",
                "humidity": 70,
                "wind": "南风",
                "forecast": ["晴", "晴", "晴"]
            }
        }
        
        return weather_data.get(city, {
            "temperature": 20,
            "condition": "晴",
            "humidity": 50,
            "wind": "微风",
            "forecast": ["晴", "晴", "晴"]
        })
    
    def _format_weather_message(self, city: str, weather_data: Dict[str, Any]) -> str:
        """
        格式化天气消息
        
        Args:
            city: 城市名称
            weather_data: 天气数据
            
        Returns:
            str: 格式化的天气消息
        """
        temp = weather_data.get("temperature", "未知")
        condition = weather_data.get("condition", "未知")
        humidity = weather_data.get("humidity", "未知")
        wind = weather_data.get("wind", "未知")
        forecast = weather_data.get("forecast", [])
        
        message = f"{city}当前天气：{condition}，温度 {temp}°C，湿度 {humidity}%，风力 {wind}。"
        
        if forecast:
            message += f"未来几天预报：{', '.join(forecast)}"
        
        return message
    
    def _get_emotion_update(self, weather_data: Dict[str, Any]) -> Dict[str, float]:
        """
        根据天气状况调整情绪
        
        Args:
            weather_data: 天气数据
            
        Returns:
            Dict: 情绪更新
        """
        condition = weather_data.get("condition", "").lower()
        emotion_update = {}
        
        if "晴" in condition:
            emotion_update["joy"] = 0.2
        elif "雨" in condition:
            emotion_update["sadness"] = 0.1
        elif "雪" in condition:
            emotion_update["joy"] = 0.1
            emotion_update["anticipation"] = 0.1
        
        return emotion_update
