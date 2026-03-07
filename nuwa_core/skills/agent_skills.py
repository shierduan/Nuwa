"""
AgentSkills 系统 - 基础技能基类

提供统一的技能接口，支持情绪感知和记忆上下文
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class AgentSkill(ABC):
    """
    技能基类，所有技能都应该继承自此类
    """
    
    def __init__(self):
        """
        初始化技能
        """
        self.name = self.__class__.__name__
        self.description = "基础技能"
        self.keywords = []
        self.enabled = True
    
    @property
    def skill_info(self) -> Dict[str, Any]:
        """
        获取技能信息
        """
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "enabled": self.enabled
        }
    
    def can_handle(self, query: str) -> bool:
        """
        判断技能是否可以处理当前查询
        
        Args:
            query: 用户查询文本
            
        Returns:
            bool: 是否可以处理
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.keywords)
    
    @abstractmethod
    async def execute(self, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            query: 用户查询文本
            emotion_state: 当前情绪状态
            memory_context: 记忆上下文
            
        Returns:
            Dict: 技能执行结果，包含以下字段：
                - success: bool - 执行是否成功
                - result: Dict - 执行结果数据
                - emotion_update: Dict - 情绪更新
                - memory_update: str - 记忆更新内容
                - message: str - 向用户展示的消息
        """
        pass
    
    def format_response(self, success: bool, result: Dict, emotion_update: Dict, memory_update: str, message: str) -> Dict[str, Any]:
        """
        格式化技能执行结果
        
        Args:
            success: 执行是否成功
            result: 执行结果数据
            emotion_update: 情绪更新
            memory_update: 记忆更新内容
            message: 向用户展示的消息
            
        Returns:
            Dict: 格式化后的结果
        """
        return {
            "success": success,
            "result": result,
            "emotion_update": emotion_update,
            "memory_update": memory_update,
            "message": message
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取技能元数据
        
        Returns:
            Dict: 技能元数据
        """
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "enabled": self.enabled
        }
