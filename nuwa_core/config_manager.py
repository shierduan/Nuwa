"""
配置管理系统 (Configuration Management)

功能：统一配置管理，支持依赖注入和接口化解耦。

核心功能：
- NuwaConfig: 统一配置数据类
- IConfigLoader: 配置加载器接口
- YAML/环境变量/JSON加载器
- 依赖注入容器
"""

import os
import yaml
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, TypeVar, Generic
from pathlib import Path


@dataclass
class NuwaConfig:
    """
    统一配置类
    
    所有系统参数集中管理，支持默认值、环境变量和配置文件覆盖
    """
    
    # LLM 配置
    llm_base_url: str = "http://127.0.0.1:1234/v1"
    llm_api_key: str = "lm-studio"
    llm_model_name: str = "local-model"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 512
    
    # 生物节律配置
    energy_recovery_rate: float = 0.0003
    energy_consumption_base: float = 0.04
    energy_consumption_system: float = 0.005
    energy_critical_threshold: float = 0.05
    
    # 记忆系统配置
    memory_ttl_days: int = 30
    memory_max_retrieval: int = 5
    memory_emotion_weight: float = 0.3
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 300
    cache_vector_maxsize: int = 5000
    cache_response_maxsize: int = 100
    cache_memory_maxsize: int = 200
    cache_state_maxsize: int = 50
    
    # 内存优化配置
    memory_history_max: int = 50
    memory_warning_mb: float = 500.0
    memory_critical_mb: float = 1000.0
    memory_cleanup_interval: float = 60.0
    
    # 状态管理配置
    state_save_interval: float = 30.0
    state_file_name: str = "state.json"
    
    # 梦境系统配置
    dream_interval: float = 900.0  # 15分钟
    dream_batch_size: int = 1000
    
    # 主动对话配置
    active_dialogue_cooldown: float = 30.0
    social_hunger_threshold: float = 0.6
    active_trigger_probability: float = 0.3
    
    # 人格演化配置
    evolution_cooldown: float = 21600.0  # 6小时
    
    # 项目路径配置
    project_name: str = "nuwa"
    data_dir: str = "data"
    model_dir: str = "models"
    
    # 系统配置
    enable_heartbeat: bool = True
    enable_debug_mode: bool = False
    log_level: str = "INFO"
    
    # 监控配置
    metrics_port: int = 8080
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NuwaConfig":
        """从字典创建配置"""
        # 过滤有效字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # 创建配置实例
        config = cls(**filtered_data)
        
        # 保留非标准字段，如channels
        for key, value in data.items():
            if key not in valid_fields:
                setattr(config, key, value)
        
        return config
    
    @classmethod
    def from_file(cls, file_path: str) -> "NuwaConfig":
        """从文件加载配置（支持YAML/JSON）"""
        path = Path(file_path)
        if not path.exists():
            print(f"[WARN] 配置文件不存在: {file_path}，使用默认配置")
            return cls()
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                # 尝试自动检测格式
                content = f.read()
                try:
                    data = yaml.safe_load(content)
                except:
                    try:
                        data = json.loads(content)
                    except:
                        print(f"[WARN] 无法解析配置文件: {file_path}，使用默认配置")
                        return cls()
        
        return cls.from_dict(data or {})
    
    @classmethod
    def from_env(cls, prefix: str = "NUWA_") -> "NuwaConfig":
        """从环境变量加载配置"""
        env_data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # NUWA_LLM_BASE_URL -> llm_base_url
                config_key = key[len(prefix):].lower().replace('_', '-')
                # 转换为下划线格式
                config_key = config_key.replace('-', '_')
                
                # 尝试转换类型
                try:
                    # 尝试解析为数字
                    if value.isdigit():
                        env_data[config_key] = int(value)
                    elif value.replace('.', '').isdigit() and '.' in value:
                        env_data[config_key] = float(value)
                    elif value.lower() in ['true', 'false']:
                        env_data[config_key] = value.lower() == 'true'
                    else:
                        env_data[config_key] = value
                except:
                    env_data[config_key] = value
        
        return cls.from_dict(env_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_yaml(self, file_path: str):
        """保存为YAML文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False)
    
    def to_json(self, file_path: str):
        """保存为JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def update(self, **kwargs):
        """更新配置项"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f"[WARN] 未知配置项: {key}")
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return getattr(self, key, default)


class IConfigLoader(ABC):
    """配置加载器接口"""
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """加载配置"""
        pass


class YAMLConfigLoader(IConfigLoader):
    """YAML配置加载器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {}
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}


class JSONConfigLoader(IConfigLoader):
    """JSON配置加载器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {}
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f) or {}


class EnvConfigLoader(IConfigLoader):
    """环境变量配置加载器"""
    
    def __init__(self, prefix: str = "NUWA_"):
        self.prefix = prefix
    
    def load(self) -> Dict[str, Any]:
        env_data = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix):].lower().replace('_', '-')
                config_key = config_key.replace('-', '_')
                
                # 类型转换
                try:
                    if value.isdigit():
                        env_data[config_key] = int(value)
                    elif value.replace('.', '').isdigit() and '.' in value:
                        env_data[config_key] = float(value)
                    elif value.lower() in ['true', 'false']:
                        env_data[config_key] = value.lower() == 'true'
                    else:
                        env_data[config_key] = value
                except:
                    env_data[config_key] = value
        
        return env_data


class ConfigManager:
    """配置管理器 - 支持多来源配置合并"""
    
    def __init__(self, default_config: Optional[NuwaConfig] = None):
        self.config = default_config or NuwaConfig()
        self.loaders: List[IConfigLoader] = []
    
    def add_loader(self, loader: IConfigLoader):
        """添加配置加载器"""
        self.loaders.append(loader)
    
    def load_from_file(self, file_path: str):
        """从文件加载（自动检测格式）"""
        path = Path(file_path)
        if not path.exists():
            print(f"[WARN] 配置文件不存在: {file_path}")
            return
        
        if path.suffix.lower() in ['.yaml', '.yml']:
            loader = YAMLConfigLoader(file_path)
        elif path.suffix.lower() == '.json':
            loader = JSONConfigLoader(file_path)
        else:
            print(f"[WARN] 不支持的配置文件格式: {path.suffix}")
            return
        
        self.add_loader(loader)
    
    def load_from_env(self, prefix: str = "NUWA_"):
        """从环境变量加载"""
        self.add_loader(EnvConfigLoader(prefix))
    
    def merge(self) -> NuwaConfig:
        """合并所有配置源（后添加的优先级更高）"""
        merged_data = {}
        
        # 先使用当前配置作为基础
        merged_data.update(self.config.to_dict())
        
        # 依次加载并合并
        for loader in self.loaders:
            try:
                loaded = loader.load()
                merged_data.update(loaded)
            except Exception as e:
                print(f"[WARN] 配置加载失败: {e}")
        
        # 更新配置对象
        self.config = NuwaConfig.from_dict(merged_data)
        return self.config
    
    def get_config(self) -> NuwaConfig:
        """获取当前配置"""
        return self.config


# 依赖注入容器
T = TypeVar('T')


class DependencyContainer:
    """依赖注入容器 - 实现接口化解耦"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register(self, name: str, service: Any):
        """注册服务实例"""
        self._services[name] = service
    
    def register_factory(self, name: str, factory: callable):
        """注册服务工厂"""
        self._factories[name] = factory
    
    def register_type(self, name: str, service_type: type, *args, **kwargs):
        """注册类型（延迟实例化）"""
        self._factories[name] = lambda: service_type(*args, **kwargs)
    
    def resolve(self, name: str) -> Any:
        """解析服务"""
        # 优先返回已注册实例
        if name in self._services:
            return self._services[name]
        
        # 使用工厂创建
        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service  # 缓存实例
            return service
        
        raise KeyError(f"服务未注册: {name}")
    
    def resolve_new(self, name: str) -> Any:
        """解析服务（总是创建新实例）"""
        if name in self._factories:
            return self._factories[name]()
        if name in self._services:
            return self._services[name]
        raise KeyError(f"服务未注册: {name}")
    
    def has(self, name: str) -> bool:
        """检查服务是否存在"""
        return name in self._services or name in self._factories
    
    def clear(self):
        """清空容器"""
        self._services.clear()
        self._factories.clear()


# 接口定义（用于依赖注入）
class IStateManager(ABC):
    """状态管理器接口"""
    
    @abstractmethod
    def get_state(self) -> Any:
        pass
    
    @abstractmethod
    def update_state(self, delta: Dict):
        pass


class IMemoryCortex(ABC):
    """记忆皮层接口"""
    
    @abstractmethod
    def store_memory(self, text: str, metadata: Optional[Dict] = None):
        pass
    
    @abstractmethod
    def recall_by_emotion(self, query_text: str, current_emotion_vector=None, top_k: int = 5) -> List[Dict]:
        pass


class IDriveSystem(ABC):
    """驱动力系统接口"""
    
    @abstractmethod
    def update(self, time_delta: float):
        pass
    
    @abstractmethod
    def consume_energy(self, amount: float):
        pass


class ILLMClient(ABC):
    """LLM客户端接口"""
    
    @abstractmethod
    async def chat_completions_create(self, messages: list, **kwargs):
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class ISelfEvolution(ABC):
    """自我进化接口"""
    
    @abstractmethod
    async def evolve(self, interaction_history: List[Any]) -> Dict[str, Any]:
        """执行自我进化"""
        pass
    
    @abstractmethod
    def calculate_reward(self, interaction: Any) -> float:
        """计算奖励值"""
        pass
    
    @abstractmethod
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化状态"""
        pass


# 全局配置实例
_global_config = None
_global_container = None


def get_config() -> NuwaConfig:
    """获取全局配置"""
    global _global_config
    if _global_config is None:
        _global_config = NuwaConfig()
    return _global_config


def set_config(config: NuwaConfig):
    """设置全局配置"""
    global _global_config
    _global_config = config


def get_container() -> DependencyContainer:
    """获取全局依赖容器"""
    global _global_container
    if _global_container is None:
        _global_container = DependencyContainer()
    return _global_container