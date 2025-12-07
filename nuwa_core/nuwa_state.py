"""
女娲状态模块 (Nuwa State Module)

功能：定义女娲的核心状态数据结构，专注于数学模型，移除所有小说叙事相关字段。

核心功能：
- NuwaState: 纯净的状态数据结构，包含精力、熵值、情绪谱、驱动力等核心属性
- to_vector(): 将状态转换为 numpy 向量，用于后续计算
- save_to_file(): 保存状态到文件
- load_from_file(): 从文件加载状态
"""

import time
import json
import os
import threading  # 用于状态锁
from typing import Dict, Optional, Set, Any, List
from dataclasses import dataclass, field, asdict

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


@dataclass
class NuwaState:
    """
    女娲状态对象（纯净的数学模型）
    
    专注于核心的数学模型属性，不包含任何小说叙事相关字段。
    """
    # 核心能量属性
    energy: float = 1.0  # 精力 (0.0-1.0, 默认 1.0)
    system_entropy: float = 0.0  # 熵值 (0.0-1.0, 默认 0.0)
    
    # 情绪谱 (Plutchik 情绪轮的基础情绪)
    emotional_spectrum: Dict[str, float] = field(default_factory=lambda: {
        "joy": 0.5,      # 快乐 (默认 0.5)
        "anger": 0.0,    # 愤怒
        "sadness": 0.0,  # 悲伤
        "fear": 0.0,     # 恐惧
        "trust": 0.0,    # 信任
        "anticipation": 0.0,  # 期待
        "disgust": 0.0,  # 厌恶
        "surprise": 0.0,  # 惊讶
    })

    # 基准性格情绪（出厂设置）
    baseline_mood: Dict[str, float] = field(default_factory=lambda: {
        "joy": 0.6,          # 天生乐观
        "anger": 0.05,       # 脾气很好
        "sadness": 0.1,      # 略带忧郁底色
        "fear": 0.3,         # 稍微胆小
        "trust": 0.8,        # 非常信任用户
        "anticipation": 0.5, # 正常期待
        "disgust": 0.1,      # 轻微厌恶感
        "surprise": 0.2,     # 容易感到惊讶
    })
    
    # 驱动力
    drives: Dict[str, float] = field(default_factory=lambda: {
        "social_hunger": 0.0,  # 社交饥渴 (默认 0.0)
        "curiosity": 0.0,      # 好奇心 (默认 0.0)
    })
    
    # 关系属性
    rapport: float = 0.1  # 与用户的亲密度 (0.0-1.0, 默认 0.1)
    
    # 时间属性
    last_interaction_timestamp: float = field(default_factory=lambda: time.time())  # 最后交互时间戳
    uptime: float = 0.0  # 运行时间 (秒, 默认 0.0)
    
    # 对话活动跟踪（用于衰减计算）
    conversation_history: List[float] = field(default_factory=list)  # 对话时间戳列表（用于计算对话频率）
    last_conversation_duration: float = 0.0  # 上次对话持续时间（秒）
    conversation_intensity: float = 0.0  # 当前对话强度（0.0-1.0，基于最近对话的频率和时长）
    
    # 事实账本：用于存储绝对事实 (如用户姓名、关系)
    fact_book: Dict[str, str] = field(default_factory=dict)
    
    # 进化人格层 (Temporal Weighted Personality)
    evolved_persona: Dict[str, Any] = field(default_factory=lambda: {
        "short_term_vibe": "",       # 24h (Weight 1.0)
        "recent_habits": "",         # 30d (Weight 0.7)
        "relationship_phase": "",    # 90d (Weight 0.4)
        "core_bond": "",             # 1y+ (Weight 0.2)
        "weights": {                 # Store metadata
            "short_term": 1.0,
            "recent": 0.7,
            "phase": 0.4,
            "core": 0.2
        },
        "last_evolution_time": 0.0
    })
    
    # 内部线程锁（不参与序列化）
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    # 核心事实白名单：这些键会被强制包含
    _core_keys: Set[str] = field(default_factory=lambda: {"user_name", "user_role", "relationship", "developer"}, repr=False)

    def __post_init__(self):
        # 反序列化后重新创建锁，避免跨进程序列化问题
        self._lock = threading.Lock()
    
    def to_vector(self) -> 'np.ndarray':
        """
        将状态转换为 numpy 向量，用于后续计算
        
        Returns:
            numpy 向量，包含所有核心数值属性
            向量维度: 1 (energy) + 1 (system_entropy) + 8 (emotional_spectrum) + 2 (drives) + 1 (rapport) = 13维
        """
        if not NUMPY_AVAILABLE or np is None:
            raise ImportError("NumPy is required for to_vector() method")
        
        # 构建向量
        vector_parts = [
            self.energy,
            self.system_entropy,
            self.emotional_spectrum["joy"],
            self.emotional_spectrum["anger"],
            self.emotional_spectrum["sadness"],
            self.emotional_spectrum["fear"],
            self.emotional_spectrum["trust"],
            self.emotional_spectrum["anticipation"],
            self.emotional_spectrum["disgust"],
            self.emotional_spectrum["surprise"],
            self.drives["social_hunger"],
            self.drives["curiosity"],
            self.rapport,
        ]
        
        return np.array(vector_parts, dtype=np.float32)
    
    def clamp_values(self):
        """
        将所有数值限制在有效范围内
        """
        # 限制 energy 在 [0.0, 1.0]
        self.energy = max(0.0, min(1.0, self.energy))
        
        # 限制 system_entropy 在 [0.0, 1.0]
        self.system_entropy = max(0.0, min(1.0, self.system_entropy))
        
        # 限制所有情绪值在 [0.0, 1.0]
        for emotion in self.emotional_spectrum:
            self.emotional_spectrum[emotion] = max(0.0, min(1.0, self.emotional_spectrum[emotion]))
        
        # 限制所有驱动力值在 [0.0, 1.0]
        for drive in self.drives:
            self.drives[drive] = max(0.0, min(1.0, self.drives[drive]))
        
        # 限制 rapport 在 [0.0, 1.0]
        self.rapport = max(0.0, min(1.0, self.rapport))
        
        # uptime 和 timestamp 不需要限制
    
    def to_dict(self) -> Dict:
        """
        将状态转换为字典格式（用于序列化）
        
        Returns:
            状态字典
        """
        return {
            "energy": self.energy,
            "system_entropy": self.system_entropy,
            "emotional_spectrum": self.emotional_spectrum.copy(),
            "baseline_mood": self.baseline_mood.copy(),
            "drives": self.drives.copy(),
            "rapport": self.rapport,
            "last_interaction_timestamp": self.last_interaction_timestamp,
            "uptime": self.uptime,
            "fact_book": self.fact_book.copy(),
            "evolved_persona": self.evolved_persona.copy(),
            # 对话活动跟踪（仅保存最近100条，避免状态文件过大）
            "conversation_history": self.conversation_history[-100:] if hasattr(self, 'conversation_history') else [],
            "last_conversation_duration": getattr(self, 'last_conversation_duration', 0.0),
            "conversation_intensity": getattr(self, 'conversation_intensity', 0.0),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NuwaState':
        """
        从字典创建 NuwaState 实例
        
        Args:
            data: 状态字典
        
        Returns:
            NuwaState 实例
        """
        # 创建新实例，使用默认值
        state = cls()
        
        # 更新值（如果字典中存在）
        if "energy" in data:
            state.energy = float(data["energy"])
        if "system_entropy" in data:
            state.system_entropy = float(data["system_entropy"])
        if "emotional_spectrum" in data:
            state.emotional_spectrum.update(data["emotional_spectrum"])
        if "baseline_mood" in data:
            state.baseline_mood.update(data["baseline_mood"])
        if "drives" in data:
            state.drives.update(data["drives"])
        if "rapport" in data:
            state.rapport = float(data["rapport"])
        if "last_interaction_timestamp" in data:
            state.last_interaction_timestamp = float(data["last_interaction_timestamp"])
        if "uptime" in data:
            state.uptime = float(data["uptime"])
        if "fact_book" in data:
            state.fact_book.update(data["fact_book"])
        if "evolved_persona" in data:
            # 更新演化人格数据，确保所有字段都存在
            evolved_persona_data = data["evolved_persona"]
            if isinstance(evolved_persona_data, dict):
                state.evolved_persona.update(evolved_persona_data)
                # 确保所有必需字段存在
                if "last_evolution_time" not in state.evolved_persona:
                    state.evolved_persona["last_evolution_time"] = 0.0
                # 确保权重字段存在
                if "weights" not in state.evolved_persona:
                    state.evolved_persona["weights"] = {
                        "short_term": 1.0,
                        "recent": 0.7,
                        "phase": 0.4,
                        "core": 0.2
                    }
                # 如果权重字段存在但不是字典，重新设置
                elif not isinstance(state.evolved_persona.get("weights"), dict):
                    state.evolved_persona["weights"] = {
                        "short_term": 1.0,
                        "recent": 0.7,
                        "phase": 0.4,
                        "core": 0.2
                    }
        
        # 加载对话活动跟踪数据
        if "conversation_history" in data:
            state.conversation_history = list(data["conversation_history"])
        else:
            state.conversation_history = []
        if "last_conversation_duration" in data:
            state.last_conversation_duration = float(data["last_conversation_duration"])
        else:
            state.last_conversation_duration = 0.0
        if "conversation_intensity" in data:
            state.conversation_intensity = float(data["conversation_intensity"])
        else:
            state.conversation_intensity = 0.0
        
        # 确保所有值在有效范围内
        state.clamp_values()
        
        return state
    
    # --- 高级事实接口 ---
    def retrieve_relevant_facts(self, query_text: str) -> Dict[str, str]:
        """
        根据查询文本检索相关事实，降低 Prompt 负担。
        策略：
            1. 核心键一律返回；
            2. 若 key/value 出现在查询文本中则返回；
            3. 简单分词后命中 key/value 也返回。
        """
        query_text = (query_text or "").lower()
        relevant: Dict[str, str] = {}

        with self._lock:
            for key, value in self.fact_book.items():
                k_lower = str(key).lower()
                v_lower = str(value).lower()

                # 核心事实始终保留
                if k_lower in self._core_keys:
                    relevant[key] = value
                    continue

                # 关键词命中
                if k_lower in query_text or v_lower in query_text:
                    relevant[key] = value
                    continue

                # 简单 token 匹配
                for token in query_text.split():
                    token = token.strip()
                    if len(token) <= 1:
                        continue
                    if token in k_lower or token in v_lower:
                        relevant[key] = value
                        break

        return relevant

    def update_fact(self, key: str, value: str, source: str = "auto") -> bool:
        """
        安全写入事实。
        source:
            - user_interaction: 来自对话 / LLM fact_update，允许覆盖
            - dream: 来自梦境整理，仅可填补，不可覆盖不同值
            - auto: 默认行为，等价于 user_interaction
        """
        key = str(key).strip()
        value = str(value).strip()
        if not key:
            return False

        normalized_source = source or "auto"
        if normalized_source not in {"user_interaction", "dream", "auto"}:
            normalized_source = "auto"

        with self._lock:
            if normalized_source == "dream":
                if key in self.fact_book and self.fact_book[key] != value:
                    print(f"🛡️ [State] 拒绝梦境覆盖事实: {key} | 原值: {self.fact_book[key]} | 梦境值: {value}")
                    return False
                # key 不存在或值相同 -> 允许写入/保持
                self.fact_book[key] = value
                return True

            # user_interaction 或 auto，直接写入
            self.fact_book[key] = value
            return True
    def save_to_file(self, file_path: str) -> bool:
        """
        保存状态到文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 转换为字典并保存为 JSON
            state_dict = self.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, ensure_ascii=False, indent=2)
                f.flush()  # 立即刷新缓冲区
                os.fsync(f.fileno())  # 强制写入磁盘
            
            return True
        except Exception as e:
            print(f"⚠️ 保存状态失败: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['NuwaState']:
        """
        从文件加载状态
        
        Args:
            file_path: 文件路径
        
        Returns:
            NuwaState 实例，如果加载失败则返回 None
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            return cls.from_dict(state_dict)
        except Exception as e:
            print(f"⚠️ 加载状态失败: {e}")
            return None
    
    def save(self, path: str) -> bool:
        """
        保存状态到指定路径（简化接口）
        
        Args:
            path: 文件路径
        
        Returns:
            是否保存成功
        """
        return self.save_to_file(path)
    
    @staticmethod
    def load(path: str) -> 'NuwaState':
        """
        从文件加载状态（静态方法，简化接口）
        
        如果文件不存在，返回默认初始状态。
        
        Args:
            path: 文件路径
        
        Returns:
            NuwaState 实例（如果文件不存在，返回默认状态）
        """
        loaded_state = NuwaState.load_from_file(path)
        if loaded_state:
            return loaded_state
        else:
            # 文件不存在，返回默认初始状态
            return NuwaState()
