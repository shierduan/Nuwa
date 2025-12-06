"""
生物节律系统模块 (Bio-Rhythm System Module)

功能：使用 PID 与简单代谢模型调节生物节律，管理精力恢复、社交饥渴增长、好奇心衰减与情绪回归。

核心功能：
- BioRhythm: 生物节律控制器，管理状态的动态演化
- PIDController: PID 控制器（复用太一引擎的逻辑），用于情绪回归控制
"""

import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .nuwa_state import NuwaState

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class PIDController:
    """
    通用 PID 控制器，用于让某个状态值平滑回归目标值。
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        setpoint: float = 0.0,
        output_limits: tuple[float | None, float | None] = (None, None),
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits  # (min, max)
        self._prev_error = 0.0
        self._integral = 0.0
        self._last_time: float | None = None

    def update(self, measurement: float, current_time: float | None = None) -> float:
        """
        基于当前测量值更新 PID 输出。

        Args:
            measurement: 当前测量值
            current_time: 当前时间戳（秒），默认为 time.time()
        """
        if current_time is None:
            current_time = time.time()

        if self._last_time is None:
            self._last_time = current_time
            return 0.0

        dt = current_time - self._last_time
        if dt <= 0.0:
            return 0.0

        error = self.setpoint - measurement

        # 积分项（带限幅防饱和）
        self._integral += error * dt
        lo, hi = self.output_limits
        if lo is not None and hi is not None:
            self._integral = max(lo, min(hi, self._integral))

        derivative = (error - self._prev_error) / dt

        output = (self.kp * error) + (self.ki * self._integral) + (self.kd * derivative)

        self._prev_error = error
        self._last_time = current_time

        # 输出限幅
        if lo is not None and hi is not None:
            output = max(lo, min(hi, output))

        return output

    def reset(self):
        """重置 PID 控制器状态"""
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_time = None


class BioRhythm:
    """
    生物节律控制器
    
    管理女娲状态的动态演化，包括：
    - 精力衰减
    - 社交饥渴增长
    - 情绪回归（使用 PID 控制）
    - 边际递减效应
    - 基于对话活动的动态衰减
    """
    
    def __init__(self, state: 'NuwaState'):
        """
        初始化生物节律控制器。

        这里不再使用"每秒线性快速衰减"的调试模式，而是更拟真的：
        - 精力在休息时缓慢恢复
        - 精力越低，社交欲望/好奇心越弱
        - 混乱度与情绪会随时间缓慢回归基线
        - 考虑边际递减效应和对话活动的影响
        """
        self.state = state

        # 情绪回归控制器：目标是平静(0.5)
        self.emotion_pid = PIDController(
            kp=0.1,
            ki=0.01,
            kd=0.05,
            setpoint=0.5,
            output_limits=(-0.1, 0.1),
        )
        # 熵值回归控制器：目标是有序(0.0)
        self.entropy_pid = PIDController(
            kp=0.2,
            ki=0.05,
            kd=0.01,
            setpoint=0.0,
            output_limits=(-0.1, 0.1),
        )
    
    @staticmethod
    def apply_marginal_effect(current_value: float, delta: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        应用边际递减效应：当值接近边界时，相同的增量产生更小的实际变化。
        
        使用 S 型曲线（sigmoid-like）函数实现边际递减：
        - 当值接近 min_val 时，正向增量效果减弱
        - 当值接近 max_val 时，正向增量效果减弱
        - 当值接近 min_val 时，负向增量效果增强（更容易下降）
        - 当值接近 max_val 时，负向增量效果增强（更容易下降）
        
        Args:
            current_value: 当前值
            delta: 原始增量
            min_val: 最小值边界
            max_val: 最大值边界
        
        Returns:
            应用边际效应后的实际增量
        """
        if delta == 0.0:
            return 0.0
        
        # 归一化到 [0, 1] 范围
        normalized = (current_value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
        
        # 计算边际效应因子（使用平滑的 S 型曲线）
        # 当 normalized 接近 0 或 1 时，因子接近 0.3（边际效应强）
        # 当 normalized 接近 0.5 时，因子接近 1.0（边际效应弱）
        # 使用双曲正切函数实现平滑过渡
        if delta > 0:
            # 正向增量：值越高，边际效应越强
            margin_factor = 0.3 + 0.7 * (1.0 - abs(normalized - 0.5) * 2.0) ** 2
        else:
            # 负向增量：值越低，边际效应越强（更容易下降）
            margin_factor = 0.3 + 0.7 * (1.0 - abs(normalized - 0.5) * 2.0) ** 2
        
        # 应用边际效应
        effective_delta = delta * margin_factor
        
        return effective_delta
    
    def calculate_conversation_intensity(self, current_time: float) -> float:
        """
        计算当前对话强度（基于最近对话的频率和时长）。
        
        Args:
            current_time: 当前时间戳
        
        Returns:
            对话强度 (0.0-1.0)
        """
        if not hasattr(self.state, 'conversation_history') or not self.state.conversation_history:
            return 0.0
        
        # 只考虑最近1小时内的对话
        recent_window = 3600.0  # 1小时
        recent_conversations = [
            ts for ts in self.state.conversation_history
            if current_time - ts <= recent_window
        ]
        
        if not recent_conversations:
            return 0.0
        
        # 计算对话频率（最近1小时内的对话次数）
        conversation_count = len(recent_conversations)
        frequency_factor = min(1.0, conversation_count / 10.0)  # 10次对话为满强度
        
        # 计算平均对话间隔（间隔越短，强度越高）
        if len(recent_conversations) > 1:
            intervals = [
                recent_conversations[i] - recent_conversations[i-1]
                for i in range(1, len(recent_conversations))
            ]
            avg_interval = sum(intervals) / len(intervals) if intervals else recent_window
            interval_factor = max(0.0, 1.0 - avg_interval / 300.0)  # 5分钟间隔为满强度
        else:
            interval_factor = 0.5
        
        # 考虑上次对话的持续时间
        duration_factor = min(1.0, getattr(self.state, 'last_conversation_duration', 0.0) / 60.0)  # 60秒为满强度
        
        # 综合计算强度（加权平均）
        intensity = (frequency_factor * 0.4 + interval_factor * 0.4 + duration_factor * 0.2)
        
        return max(0.0, min(1.0, intensity))
    
    def consume_energy(self, amount: float, conversation_intensity: float = 0.0):
        """
        主动消耗：当进行思考或对话时调用。
        
        考虑边际效应和对话强度：
        - 能量越低，消耗越困难（边际效应）
        - 对话强度越高，消耗越大
        
        Args:
            amount: 基础消耗量
            conversation_intensity: 对话强度 (0.0-1.0)，影响实际消耗量
        """
        # 根据对话强度调整消耗量（高强度对话消耗更多）
        intensity_multiplier = 1.0 + conversation_intensity * 0.5  # 最多增加50%
        effective_amount = amount * intensity_multiplier
        
        # 应用边际效应：能量越低，消耗越困难
        current_energy = self.state.energy
        effective_delta = -self.apply_marginal_effect(current_energy, -effective_amount, 0.0, 1.0)
        
        self.state.energy += effective_delta
        self.state.clamp_values()

    def decay(self, time_delta: float):
        """
        生物代谢 (Metabolism): 后台自然流逝的影响。

        拟真逻辑：
        1. 休息回血：不对话时，能量缓慢恢复（对话强度越高，恢复越慢）。
        2. 疲劳压制：能量越低，其他欲望(好奇/社交)越弱。
        3. 熵值与情绪随时间自然回归（对话强度影响回归速度）。
        4. 社交饥渴增长（考虑边际效应和对话活动）。
        """
        current_time = time.time()
        
        # 计算当前对话强度
        conversation_intensity = self.calculate_conversation_intensity(current_time)
        if hasattr(self.state, 'conversation_intensity'):
            self.state.conversation_intensity = conversation_intensity

        # --- 1. 精力恢复 (Resting Recovery) ---
        # 设定：完全回满约需1小时的静默休息
        base_recovery_rate = 0.0003  # 每秒约 +0.0003，约 1 小时可从 0 恢复到 1
        
        # 对话强度越高，恢复越慢（连续对话时恢复速度降低）
        recovery_rate = base_recovery_rate * (1.0 - conversation_intensity * 0.9)  # 高强度时恢复速度降至10%
        
        # 应用更强的边际效应：能量越高，恢复越慢（接近满值时恢复困难）
        current_energy = self.state.energy
        recovery_delta = recovery_rate * time_delta
        # 自定义边际效应函数：能量越高，恢复越困难，更符合真实生理规律
        def strong_marginal_effect(value, delta, min_val=0.0, max_val=1.0):
            # 归一化
            normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            # 更强的边际效应：能量接近满值时，恢复率急剧下降
            margin_factor = 0.1 + 0.9 * (1.0 - normalized) ** 3
            return delta * margin_factor
        
        effective_recovery = strong_marginal_effect(current_energy, recovery_delta, 0.0, 1.0)
        self.state.energy += effective_recovery

        # --- 2. 计算疲劳压制因子 (Fatigue Suppression) ---
        # 能量越低，压制越强；当 energy < 0.1 时几乎躺平
        energy_factor = max(0.0, (self.state.energy - 0.1) / 0.9)

        # --- 3. 社交饥渴 (Social Hunger) ---
        # 基础增长：加快增长速度，约数小时达到触发阈值（0.6）
        # 从0到0.6大约需要2-3小时（更快触发主动对话）
        base_hunger_growth = 0.0001  # 提高5倍，从0.00002到0.0001
        # 如果很累(energy_factor 低)，就不想理人，饥渴感增长变慢
        effective_growth = base_hunger_growth * (energy_factor ** 2)
        
        # 对话强度影响：高强度对话后，社交饥渴增长变慢（刚聊过，暂时不想聊）
        # 但影响减弱，让饥渴更快恢复
        if conversation_intensity > 0.5:
            effective_growth *= (1.0 - conversation_intensity * 0.3)  # 高强度时增长速度降至70%（之前是50%）

        current_hunger = self.state.drives.get("social_hunger", 0.0)
        hunger_delta = (1.0 - current_hunger) * (1 - math.exp(-effective_growth * time_delta))
        
        # 应用边际效应：饥渴值越高，增长越慢
        effective_hunger_delta = self.apply_marginal_effect(current_hunger, hunger_delta, 0.0, 1.0)
        self.state.drives["social_hunger"] = current_hunger + effective_hunger_delta

        # --- 4. 好奇心 (Curiosity) 自然衰减 ---
        # 好奇心如果不被满足，会随时间慢慢淡去
        curiosity_decay_k = 0.00004  # 半衰期若干小时
        # 如果很累，好奇心掉得更快（没精力好奇）
        if self.state.energy < 0.3:
            curiosity_decay_k *= 5.0
        
        # 对话强度影响：高强度对话后，好奇心衰减更快（刚聊过，好奇心得到一定满足）
        if conversation_intensity > 0.3:
            curiosity_decay_k *= (1.0 + conversation_intensity * 0.5)  # 高强度时衰减速度增加50%

        current_curiosity = self.state.drives.get("curiosity", 0.0)
        curiosity_decay = current_curiosity * (1 - math.exp(-curiosity_decay_k * time_delta))
        
        # 应用边际效应：好奇心值越低，衰减越慢
        effective_decay = self.apply_marginal_effect(current_curiosity, -curiosity_decay, 0.0, 1.0)
        self.state.drives["curiosity"] = current_curiosity + effective_decay

        # --- 5. 运行时间与数值钳位 ---
        self.state.uptime += time_delta
        
        # 清理过期的对话历史（保留最近24小时）
        if hasattr(self.state, 'conversation_history'):
            cutoff_time = current_time - 86400.0  # 24小时
            self.state.conversation_history = [
                ts for ts in self.state.conversation_history
                if ts > cutoff_time
            ]
        
        self.state.clamp_values()
    
    def regulate(self):
        """
        使用 PID 让混乱度与情绪回归到“性格基准线”，并模拟不同情绪的惯性和联动影响。
        
        情感联动规则：
        - 愤怒会降低快乐和信任
        - 恐惧会降低信任和期待
        - 悲伤会降低快乐和期待
        - 快乐会降低悲伤和恐惧
        - 信任会降低愤怒和恐惧
        - 期待会降低悲伤
        
        情绪对亲密度的影响：
        - 愤怒和恐惧会快速降低亲密度
        - 快乐和信任会增加亲密度
        
        情绪对精力的影响：
        - 强烈的负面情绪会消耗精力
        - 强烈的正面情绪会恢复精力
        """
        now = time.time()

        # 1. 熵值自然回归 (混乱 -> 有序)
        entropy_correction = self.entropy_pid.update(self.state.system_entropy, current_time=now)
        self.state.system_entropy += entropy_correction

        # 2. 情绪回归：以 baseline_mood 作为目标，按不同惯性速度回归
        baseline = getattr(self.state, "baseline_mood", {}) or {}
        # Plutchik情绪轮模型的8种基本情绪
        # 对立关系：joy-sadness, anger-fear, trust-disgust, anticipation-surprise
        base_decay_rates = {
            "joy": 0.005,          # 快乐易逝
            "sadness": 0.008,      # 悲伤衰减较慢
            "anger": 0.01,         # 愤怒衰减较快
            "fear": 0.008,         # 恐惧衰减较快
            "trust": 0.003,        # 信任稳固持久
            "disgust": 0.009,      # 厌恶衰减较快
            "anticipation": 0.006, # 期待会随时间消减
            "surprise": 0.012,     # 惊讶衰减最快
        }
        default_rate = 0.004
        
        # 情绪心理属性矩阵：基于心理学研究的情绪效价和唤醒度
        emotion_properties = {
            "joy": {"valence": 1.0, "arousal": 0.6, "duration": 0.5},         # 高正效价，中等唤醒度，持续时间中等
            "sadness": {"valence": -1.0, "arousal": 0.3, "duration": 0.8},   # 高负效价，低唤醒度，持续时间长
            "anger": {"valence": -0.8, "arousal": 0.9, "duration": 0.6},    # 高负效价，高唤醒度，持续时间中等
            "fear": {"valence": -0.9, "arousal": 0.8, "duration": 0.7},    # 高负效价，高唤醒度，持续时间较长
            "trust": {"valence": 0.7, "arousal": 0.4, "duration": 0.9},    # 正效价，低唤醒度，持续时间长
            "disgust": {"valence": -0.7, "arousal": 0.6, "duration": 0.5},  # 负效价，中等唤醒度，持续时间中等
            "anticipation": {"valence": 0.5, "arousal": 0.7, "duration": 0.6}, # 正效价，高唤醒度，持续时间中等
            "surprise": {"valence": 0.0, "arousal": 0.8, "duration": 0.3}   # 中性效价，高唤醒度，持续时间短
        }
        
        # 情绪对立关系矩阵（Plutchik情绪轮的对立情绪对）
        emotion_opposites = {
            "joy": "sadness",
            "sadness": "joy",
            "anger": "fear",
            "fear": "anger",
            "trust": "disgust",
            "disgust": "trust",
            "anticipation": "surprise",
            "surprise": "anticipation"
        }
        
        # 情绪相互作用强度矩阵：基于心理学研究的情绪影响强度
        # 行：影响源情绪，列：目标情绪，值：影响强度（正数为促进，负数为抑制）
        emotion_interaction_matrix = {
            "joy": {
                "joy": 0.1,      # 快乐增强自身
                "sadness": -0.5,  # 快乐抑制悲伤
                "anger": -0.3,    # 快乐抑制愤怒
                "fear": -0.4,     # 快乐抑制恐惧
                "trust": 0.3,     # 快乐增强信任
                "disgust": -0.2,  # 快乐抑制厌恶
                "anticipation": 0.2, # 快乐增强期待
                "surprise": 0.1   # 快乐略微增强惊讶
            },
            "sadness": {
                "joy": -0.4,      # 悲伤抑制快乐
                "sadness": 0.15,   # 悲伤增强自身
                "anger": 0.2,      # 悲伤可能引发愤怒
                "fear": 0.3,       # 悲伤增强恐惧
                "trust": -0.3,     # 悲伤抑制信任
                "disgust": 0.1,    # 悲伤略微增强厌恶
                "anticipation": -0.3, # 悲伤抑制期待
                "surprise": -0.1   # 悲伤抑制惊讶
            },
            "anger": {
                "joy": -0.5,      # 愤怒抑制快乐
                "sadness": -0.2,  # 愤怒抑制悲伤
                "anger": 0.2,      # 愤怒增强自身
                "fear": -0.4,     # 愤怒抑制恐惧（愤怒-恐惧的对抗关系）
                "trust": -0.4,     # 愤怒抑制信任
                "disgust": 0.3,    # 愤怒增强厌恶
                "anticipation": 0.2, # 愤怒增强期待（愤怒的目标导向）
                "surprise": -0.1   # 愤怒抑制惊讶
            },
            "fear": {
                "joy": -0.4,      # 恐惧抑制快乐
                "sadness": 0.3,   # 恐惧增强悲伤
                "anger": -0.3,    # 恐惧抑制愤怒（愤怒-恐惧的对抗关系）
                "fear": 0.15,     # 恐惧增强自身
                "trust": -0.5,     # 恐惧抑制信任
                "disgust": 0.2,    # 恐惧增强厌恶
                "anticipation": -0.4, # 恐惧抑制期待
                "surprise": 0.3    # 恐惧增强惊讶
            },
            "trust": {
                "joy": 0.3,       # 信任增强快乐
                "sadness": -0.3,  # 信任抑制悲伤
                "anger": -0.4,    # 信任抑制愤怒
                "fear": -0.5,     # 信任抑制恐惧
                "trust": 0.1,     # 信任增强自身
                "disgust": -0.5,   # 信任抑制厌恶
                "anticipation": 0.3, # 信任增强期待
                "surprise": 0.1   # 信任略微增强惊讶
            },
            "disgust": {
                "joy": -0.3,      # 厌恶抑制快乐
                "sadness": 0.2,   # 厌恶增强悲伤
                "anger": 0.3,      # 厌恶增强愤怒
                "fear": 0.2,       # 厌恶增强恐惧
                "trust": -0.5,     # 厌恶抑制信任
                "disgust": 0.15,   # 厌恶增强自身
                "anticipation": -0.3, # 厌恶抑制期待
                "surprise": 0.2    # 厌恶增强惊讶
            },
            "anticipation": {
                "joy": 0.3,       # 期待增强快乐
                "sadness": -0.2,  # 期待抑制悲伤
                "anger": 0.2,      # 期待增强愤怒（期待落空时）
                "fear": -0.1,     # 期待略微抑制恐惧
                "trust": 0.2,      # 期待增强信任
                "disgust": -0.2,   # 期待抑制厌恶
                "anticipation": 0.15, # 期待增强自身
                "surprise": -0.4   # 期待抑制惊讶
            },
            "surprise": {
                "joy": 0.1,       # 惊讶略微增强快乐
                "sadness": 0.1,   # 惊讶略微增强悲伤
                "anger": 0.1,      # 惊讶略微增强愤怒
                "fear": 0.3,       # 惊讶增强恐惧
                "trust": -0.2,     # 惊讶抑制信任
                "disgust": 0.2,    # 惊讶增强厌恶
                "anticipation": -0.4, # 惊讶抑制期待
                "surprise": 0.2    # 惊讶增强自身
            }
        }
        
        # 计算对话强度（影响情绪回归速度）
        current_time = time.time()
        conversation_intensity = self.calculate_conversation_intensity(current_time)
        
        # 神经递质模拟：基于仿生学的神经调节机制
        # 神经递质水平会影响情绪的易感性和稳定性
        neurotransmitters = {
            "serotonin": 0.7,     # 血清素：调节情绪稳定、快乐感（低：抑郁，高：平静）
            "dopamine": 0.6,      # 多巴胺：调节奖励、动机（低：无动力，高：兴奋）
            "norepinephrine": 0.5, # 去甲肾上腺素：调节警觉性、压力反应（低：疲劳，高：焦虑）
            "oxytocin": 0.4,       # 催产素：调节信任、社交连接（低：孤独，高：亲密）
        }
        
        # 神经递质对情绪的影响矩阵
        neurotransmitter_effects = {
            "serotonin": {
                "joy": 0.3,      # 血清素增加快乐
                "sadness": -0.4, # 血清素减少悲伤
                "anger": -0.3,   # 血清素减少愤怒
                "fear": -0.3,    # 血清素减少恐惧
                "trust": 0.2,    # 血清素增加信任
                "disgust": -0.2, # 血清素减少厌恶
            },
            "dopamine": {
                "joy": 0.2,      # 多巴胺增加快乐
                "sadness": -0.3, # 多巴胺减少悲伤
                "anger": 0.1,    # 多巴胺轻微增加愤怒
                "anticipation": 0.4, # 多巴胺增加期待
                "surprise": 0.2, # 多巴胺增加惊讶
            },
            "norepinephrine": {
                "anger": 0.3,     # 去甲肾上腺素增加愤怒
                "fear": 0.3,      # 去甲肾上腺素增加恐惧
                "anticipation": 0.2, # 去甲肾上腺素增加期待
                "surprise": 0.3,  # 去甲肾上腺素增加惊讶
            },
            "oxytocin": {
                "trust": 0.5,     # 催产素增加信任
                "joy": 0.2,       # 催产素增加快乐
                "sadness": -0.3,  # 催产素减少悲伤
                "fear": -0.3,     # 催产素减少恐惧
            },
        }
        
        # 高强度对话时，情绪回归速度加快（情绪波动后快速恢复）
        intensity_multiplier = 1.0 + conversation_intensity * 0.5  # 最多加快50%

        # 保存原始情绪值用于联动计算
        original_emotions = self.state.emotional_spectrum.copy()
        emotions = self.state.emotional_spectrum

        # 情绪动态模型：使用一阶微分方程描述情绪变化
        # 方程形式：de/dt = -k*(e - e0) + Σ (interaction_strength(e,f)*f) for all f
        # 其中：
        #   k 是衰减率
        #   e0 是基线值
        #   interaction_strength(e,f) 是情绪e和f之间的相互作用强度
        
        # 初始化情绪变化率字典
        emotion_changes = {}
        
        # 计算每种情绪的变化率
        for emotion, value in self.state.emotional_spectrum.items():
            target = baseline.get(emotion, 0.0)
            
            # 1. 自然衰减项：向基线回归
            base_rate = base_decay_rates.get(emotion, default_rate)
            intensity_factor = 1.0 + value * 0.5  # 情绪越强烈，衰减越快
            decay_rate = base_rate * intensity_multiplier * intensity_factor
            natural_decay = -decay_rate * (value - target)  # 一阶线性回归项
            
            # 2. 情绪相互作用项：基于情绪相互作用矩阵
            interaction_effect = 0.0
            
            # 计算所有其他情绪对当前情绪的影响
            for source_emotion, source_value in emotions.items():
                if source_emotion == emotion:
                    continue  # 跳过自身影响
                
                # 查找影响强度
                if source_emotion in emotion_interaction_matrix and emotion in emotion_interaction_matrix[source_emotion]:
                    strength = emotion_interaction_matrix[source_emotion][emotion]
                    # 计算影响：源情绪强度 * 影响强度
                    interaction_effect += strength * source_value
            
            # 3. 情绪效价一致性影响：正效价情绪相互促进，负效价情绪相互促进
            valence_effect = 0.0
            current_valence = emotion_properties.get(emotion, {}).get("valence", 0.0)
            
            for other_emotion, other_value in emotions.items():
                if other_emotion == emotion:
                    continue
                
                other_valence = emotion_properties.get(other_emotion, {}).get("valence", 0.0)
                # 效价一致的情绪相互促进
                valence_consistency = current_valence * other_valence
                valence_effect += 0.05 * valence_consistency * other_value
            
            # 4. 神经递质影响：仿生学的神经调节机制
            neurotransmitter_effect = 0.0
            
            for nt, nt_level in neurotransmitters.items():
                if nt in neurotransmitter_effects and emotion in neurotransmitter_effects[nt]:
                    effect_strength = neurotransmitter_effects[nt][emotion]
                    neurotransmitter_effect += effect_strength * nt_level * 0.1  # 神经递质影响系数
            
            # 5. 情绪自身强度的非线性调节
            # 情绪越强烈，其变化越困难（边际效应）
            intensity_regulation = -0.05 * value * (value - 1.0) * (value + 1.0)  # 三次非线性项
            
            # 总变化率：综合所有影响因素
            total_change = natural_decay + interaction_effect + valence_effect + neurotransmitter_effect + intensity_regulation
            emotion_changes[emotion] = total_change
        
        # 应用情绪变化率
        for emotion, change_rate in emotion_changes.items():
            # 限制变化率的最大绝对值，防止情绪突变
            max_change = 0.1  # 每秒最大变化量
            clamped_change = max(-max_change, min(max_change, change_rate))
            
            # 更新情绪值
            new_value = self.state.emotional_spectrum.get(emotion, 0.0) + clamped_change
            # 应用边际效应：使情绪变化更自然
            effective_new_value = self.apply_marginal_effect(
                self.state.emotional_spectrum.get(emotion, 0.0),
                clamped_change,
                0.0,
                1.0
            ) + self.state.emotional_spectrum.get(emotion, 0.0)
            
            # 确保情绪值在有效范围内
            self.state.emotional_spectrum[emotion] = max(0.0, min(1.0, effective_new_value))

        # 3. 中立语境下的微小情绪调节：自动降低负面情绪
        # 当没有强烈情绪触发时，负面情绪应缓慢降低
        for emotion in ["anger", "sadness", "fear"]:
            if emotions[emotion] > baseline.get(emotion, 0.0) + 0.1:
                # 负面情绪高于基线时，额外增加微小衰减
                emotions[emotion] = max(baseline.get(emotion, 0.0), emotions[emotion] - 0.002)

        # 4. 情感联动：实现情绪之间的连续联动效应
        
        # 愤怒的影响：降低快乐、信任和期待
        anger = emotions["anger"]
        emotions["joy"] = max(0.0, emotions["joy"] - anger * 0.15)
        emotions["trust"] = max(0.0, emotions["trust"] - anger * 0.2)
        emotions["anticipation"] = max(0.0, emotions["anticipation"] - anger * 0.15)
        
        # 恐惧的影响：降低信任、期待和快乐
        fear = emotions["fear"]
        emotions["trust"] = max(0.0, emotions["trust"] - fear * 0.25)
        emotions["anticipation"] = max(0.0, emotions["anticipation"] - fear * 0.2)
        emotions["joy"] = max(0.0, emotions["joy"] - fear * 0.1)
        
        # 悲伤的影响：降低快乐、期待和信任
        sadness = emotions["sadness"]
        emotions["joy"] = max(0.0, emotions["joy"] - sadness * 0.2)
        emotions["anticipation"] = max(0.0, emotions["anticipation"] - sadness * 0.15)
        emotions["trust"] = max(0.0, emotions["trust"] - sadness * 0.05)
        
        # 快乐的影响：降低悲伤、恐惧和愤怒，增加期待
        joy = emotions["joy"]
        emotions["sadness"] = max(0.0, emotions["sadness"] - joy * 0.2)
        emotions["fear"] = max(0.0, emotions["fear"] - joy * 0.15)
        emotions["anger"] = max(0.0, emotions["anger"] - joy * 0.1)
        emotions["anticipation"] = min(1.0, emotions["anticipation"] + joy * 0.15)
        
        # 信任的影响：降低愤怒、恐惧和悲伤，增加期待
        trust = emotions["trust"]
        emotions["anger"] = max(0.0, emotions["anger"] - trust * 0.15)
        emotions["fear"] = max(0.0, emotions["fear"] - trust * 0.2)
        emotions["sadness"] = max(0.0, emotions["sadness"] - trust * 0.1)
        emotions["anticipation"] = min(1.0, emotions["anticipation"] + trust * 0.1)
        
        # 期待的影响：降低悲伤、恐惧，增加快乐和信任
        anticipation = emotions["anticipation"]
        emotions["sadness"] = max(0.0, emotions["sadness"] - anticipation * 0.15)
        emotions["fear"] = max(0.0, emotions["fear"] - anticipation * 0.1)
        emotions["joy"] = min(1.0, emotions["joy"] + anticipation * 0.1)
        emotions["trust"] = min(1.0, emotions["trust"] + anticipation * 0.08)
        
        # 5. 情绪对生理状态的影响模型：基于心理学和生理学研究
        
        # 5.1 情绪对亲密度的影响
        # 计算情绪影响因子，基于情绪的效价和唤醒度
        rapport_change = 0.0
        
        for emotion, value in emotions.items():
            if emotion in emotion_properties:
                prop = emotion_properties[emotion]
                valence = prop["valence"]
                
                # 基于情绪效价和强度计算对亲密度的影响
                # 正效价情绪增加亲密度，负效价情绪降低亲密度
                # 愤怒和恐惧对亲密度的影响更大
                emotion_weight = 1.0
                if emotion in ["anger", "fear"]:
                    emotion_weight = 1.5  # 愤怒和恐惧对亲密度影响更大
                elif emotion in ["joy", "trust"]:
                    emotion_weight = 1.2  # 快乐和信任对亲密度影响较大
                
                rapport_change += valence * value * 0.01 * emotion_weight
        
        # 应用边际效应，亲密度越高，变化越困难
        if rapport_change != 0.0:
            effective_rapport_delta = self.apply_marginal_effect(self.state.rapport, rapport_change, 0.0, 1.0)
            self.state.rapport += effective_rapport_delta
        
        # 5.2 情绪对精力的影响：基于情绪的效价、唤醒度和持续时间
        # 计算整体情绪效价和唤醒度
        total_valence = 0.0
        total_arousal = 0.0
        emotion_count = 0
        
        for emotion, value in emotions.items():
            if emotion in emotion_properties:
                prop = emotion_properties[emotion]
                total_valence += prop["valence"] * value
                total_arousal += prop["arousal"] * value
                emotion_count += 1
        
        avg_valence = total_valence / max(1, emotion_count)
        avg_arousal = total_arousal / max(1, emotion_count)
        
        # 情绪对精力的影响机制：
        # - 高唤醒度情绪（无论正负面）会消耗更多精力
        # - 正效价情绪在低到中等唤醒度时会恢复精力
        # - 负效价情绪在任何唤醒度下都会消耗精力
        energy_change = 0.0
        
        # 唤醒度的精力消耗
        arousal_cost = 0.001 * avg_arousal * avg_arousal  # 二次关系，高唤醒度消耗更快
        
        # 效价的精力影响
        valence_benefit = 0.0008 * avg_valence * (1.0 - avg_arousal)  # 正效价在低唤醒度时恢复精力
        
        energy_change = -arousal_cost + valence_benefit
        
        # 应用边际效应，精力越高或越低，变化越困难
        if energy_change != 0.0:
            effective_energy_delta = self.apply_marginal_effect(self.state.energy, energy_change, 0.0, 1.0)
            self.state.energy += effective_energy_delta
        
        # 5.3 情绪对系统熵的影响
        # 情绪越强烈，系统熵越高（混乱度增加）
        emotion_intensity = sum(emotions.values()) / max(1, len(emotions))
        entropy_change = 0.0005 * emotion_intensity  # 情绪强度增加熵值
        
        if entropy_change != 0.0:
            effective_entropy_delta = self.apply_marginal_effect(self.state.system_entropy, entropy_change, 0.0, 1.0)
            self.state.system_entropy += effective_entropy_delta
        
        # 5.4 情绪对驱动力的影响
        # 正效价情绪增加好奇心和社交饥渴
        # 负效价情绪降低好奇心和社交饥渴
        for drive in ["curiosity", "social_hunger"]:
            drive_change = 0.0005 * avg_valence * (1.0 - self.state.drives[drive])  # 边际效应，驱动力越低，变化越容易
            self.state.drives[drive] = max(0.0, min(1.0, self.state.drives[drive] + drive_change))
        
        # 确保所有值在有效范围内
        self.state.clamp_values()
    
    def update(self, time_delta: float):
        """
        更新生物节律（衰减 + 调节）
        
        Args:
            time_delta: 时间差（秒）
        """
        # 先进行自然衰减
        self.decay(time_delta)
        
        # 然后进行情绪回归调节
        self.regulate()

