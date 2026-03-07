"""
配置数据模型

使用Pydantic定义类型安全的配置模型，支持验证和序列化。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class NuwaConfig(BaseModel):
    """女娲系统统一配置模型"""
    
    # LLM配置
    llm_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="LLM服务地址"
    )
    llm_api_key: str = Field(
        default="lm-studio",
        description="LLM API密钥"
    )
    llm_model_name: str = Field(
        default="local-model",
        description="LLM模型名称"
    )
    llm_temperature: float = Field(
        default=0.7,
        description="LLM温度参数",
        ge=0.0,
        le=1.0
    )
    llm_max_tokens: int = Field(
        default=512,
        description="最大token数",
        ge=1
    )
    
    # 生物节律配置
    energy_recovery_rate: float = Field(
        default=0.0003,
        description="精力恢复速率",
        ge=0.0
    )
    energy_consumption_base: float = Field(
        default=0.04,
        description="基础精力消耗",
        ge=0.0
    )
    energy_consumption_system: float = Field(
        default=0.005,
        description="系统精力消耗",
        ge=0.0
    )
    energy_critical_threshold: float = Field(
        default=0.05,
        description="精力临界阈值",
        ge=0.0,
        le=1.0
    )
    
    # 记忆系统配置
    memory_ttl_days: int = Field(
        default=30,
        description="记忆存活天数",
        ge=1
    )
    memory_max_retrieval: int = Field(
        default=5,
        description="最大检索数量",
        ge=1
    )
    memory_emotion_weight: float = Field(
        default=0.3,
        description="情感权重",
        ge=0.0,
        le=1.0
    )
    
    # 缓存配置
    cache_enabled: bool = Field(
        default=True,
        description="是否启用缓存"
    )
    cache_ttl: int = Field(
        default=300,
        description="缓存过期时间(秒)",
        ge=1
    )
    cache_vector_maxsize: int = Field(
        default=5000,
        description="向量缓存最大大小",
        ge=1
    )
    cache_response_maxsize: int = Field(
        default=100,
        description="响应缓存最大大小",
        ge=1
    )
    cache_memory_maxsize: int = Field(
        default=200,
        description="记忆缓存最大大小",
        ge=1
    )
    cache_state_maxsize: int = Field(
        default=50,
        description="状态缓存最大大小",
        ge=1
    )
    
    # 内存优化配置
    memory_history_max: int = Field(
        default=50,
        description="状态历史最大长度",
        ge=1
    )
    memory_warning_mb: float = Field(
        default=500.0,
        description="内存警告阈值(MB)",
        ge=0.0
    )
    memory_critical_mb: float = Field(
        default=1000.0,
        description="内存临界阈值(MB)",
        ge=0.0
    )
    memory_cleanup_interval: float = Field(
        default=60.0,
        description="内存清理间隔(秒)",
        ge=1.0
    )
    
    # 状态管理配置
    state_save_interval: float = Field(
        default=30.0,
        description="状态保存间隔(秒)",
        ge=1.0
    )
    state_file_name: str = Field(
        default="state.json",
        description="状态文件名"
    )
    
    # 梦境系统配置
    dream_interval: float = Field(
        default=900.0,
        description="梦境间隔(秒)",
        ge=1.0
    )
    dream_batch_size: int = Field(
        default=1000,
        description="梦境批次大小",
        ge=1
    )
    
    # 主动对话配置
    active_dialogue_cooldown: float = Field(
        default=30.0,
        description="主动对话冷却时间(秒)",
        ge=0.0
    )
    social_hunger_threshold: float = Field(
        default=0.6,
        description="社交饥渴阈值",
        ge=0.0,
        le=1.0
    )
    active_trigger_probability: float = Field(
        default=0.3,
        description="主动触发概率",
        ge=0.0,
        le=1.0
    )
    
    # 人格演化配置
    evolution_cooldown: float = Field(
        default=21600.0,
        description="进化冷却时间(秒)",
        ge=0.0
    )
    
    # 项目路径配置
    project_name: str = Field(
        default="nuwa",
        description="项目名称"
    )
    data_dir: str = Field(
        default="data",
        description="数据目录"
    )
    model_dir: str = Field(
        default="models",
        description="模型目录"
    )
    
    # 系统配置
    enable_heartbeat: bool = Field(
        default=True,
        description="启用心跳"
    )
    enable_debug_mode: bool = Field(
        default=False,
        description="启用调试模式"
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="日志级别"
    )
    
    @field_validator('llm_temperature')
    @classmethod
    def validate_temperature(cls, v):
        """验证温度参数"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('温度参数必须在0.0到1.0之间')
        return v
    
    @field_validator('llm_base_url')
    @classmethod
    def validate_url(cls, v):
        """验证URL格式"""
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NuwaConfig":
        """从字典创建配置"""
        return cls(**data)
    
    @classmethod
    def get_default_yaml(cls) -> str:
        """获取默认YAML配置"""
        default = cls()
        import yaml
        return yaml.dump(default.to_dict(), allow_unicode=True, default_flow_style=False)


class ConfigUpdate(BaseModel):
    """配置更新请求模型"""
    
    updates: Dict[str, Any] = Field(
        ...,
        description="要更新的配置项"
    )
    user: Optional[str] = Field(
        default="system",
        description="更新用户"
    )
    
    @field_validator('updates')
    @classmethod
    def validate_updates(cls, v):
        """验证更新内容"""
        if not v:
            raise ValueError('更新内容不能为空')
        return v


class ConfigHistory(BaseModel):
    """配置历史记录"""
    
    id: str = Field(..., description="历史记录ID")
    timestamp: datetime = Field(..., description="时间戳")
    user: str = Field(..., description="操作用户")
    status: str = Field(..., description="状态: committed, rolled_back")
    updates: Dict[str, Any] = Field(..., description="更新内容")
    old_values: Dict[str, Any] = Field(..., description="旧值")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user": self.user,
            "status": self.status,
            "updates": self.updates,
            "old_values": self.old_values
        }


class SystemStatus(BaseModel):
    """系统状态模型"""
    
    config_manager: bool = Field(..., description="配置管理器状态")
    websocket_connections: int = Field(..., description="WebSocket连接数")
    hot_reload_running: bool = Field(..., description="热重载运行状态")
    config_file_exists: bool = Field(..., description="配置文件是否存在")
    uptime_seconds: float = Field(..., description="运行时间(秒)")
    memory_mb: float = Field(..., description="内存使用(MB)")
    timestamp: datetime = Field(default_factory=datetime.now, description="查询时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class DebugMessage(BaseModel):
    """调试消息模型"""
    
    type: str = Field(..., description="消息类型")
    message: str = Field(..., description="消息内容")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


__all__ = [
    "LogLevel",
    "NuwaConfig",
    "ConfigUpdate",
    "ConfigHistory",
    "SystemStatus",
    "DebugMessage",
]
