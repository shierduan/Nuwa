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
    - 好奇心衰减与情绪回归
    - 神经递质系统：管理皮质醇、多巴胺、催产素
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

        # 内分泌系统（神经递质）
        # 这些值不是情绪，而是情绪的“生理残留”，代谢极慢 (半衰期 10-30分钟)
        self.neurotransmitters = {
            "cortisol": 0.0,      # 压力激素：由 Anger/Fear/Disgust 累积，导致“坏心情惯性”
            "dopamine": 0.5,      # 快乐激素：由 Joy/Anticipation 累积，提供“好心情惯性”
            "oxytocin": 0.3       # 依恋激素：由 Trust 累积，对抗 Cortisol
        }
        
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
        # 自定义边际效应函数：能量越高，恢复越困难，更符合真实生理规律
        def strong_marginal_effect(value, delta, min_val=0.0, max_val=1.0):
            # 归一化
            normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            # 更强的边际效应：能量接近满值时，恢复率急剧下降
            margin_factor = 0.1 + 0.9 * (1.0 - normalized) ** 3
            return delta * margin_factor
        
        effective_recovery = strong_marginal_effect(current_energy, recovery_rate * time_delta, 0.0, 1.0)
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
        基于8向量的动态平衡：实现神经递质与情绪的相互影响
        
        核心逻辑：
        1. 神经递质的【生成】 (Synthesis)
        2. 神经递质的【代谢】 (Metabolism)
        3. 神经递质对情绪的【反向钳制】 (Feedback Modulation)
        """
        emotions = self.state.emotional_spectrum
        neuro = self.neurotransmitters
        dt = 1.0  # 假设每次调用间隔 1秒

        # 1. 神经递质的【生成】 (Synthesis)
        # 压力激素：不仅是愤怒，恐惧和厌恶也会增加压力
        # 逻辑：负面情绪越高，压力积累越快
        stress_input = (emotions['anger'] + emotions['fear'] + emotions['disgust']) * 0.3
        neuro['cortisol'] = min(1.0, neuro['cortisol'] + stress_input * 0.01)

        # 快乐激素：快乐和期待会产生多巴胺
        reward_input = (emotions['joy'] + emotions['anticipation']) * 0.3
        neuro['dopamine'] = min(1.0, neuro['dopamine'] + reward_input * 0.01)

        # 依恋激素：信任产生催产素
        bond_input = emotions['trust'] * 0.3
        neuro['oxytocin'] = min(1.0, neuro['oxytocin'] + bond_input * 0.01)

        # 2. 神经递质的【代谢】 (Metabolism)
        # 催产素可以加速皮质醇的分解（安慰也就是 Trust 可以消气）
        cortisol_decay = 0.0005 * (1.0 + neuro['oxytocin'] * 2.0)
        neuro['cortisol'] = max(0.0, neuro['cortisol'] - cortisol_decay)
        
        # 多巴胺和催产素自然衰减
        neuro['dopamine'] = max(0.0, neuro['dopamine'] - 0.001)
        neuro['oxytocin'] = max(0.0, neuro['oxytocin'] - 0.001)

        # 3. 神经递质对情绪的【反向钳制】 (Feedback Modulation)
        # 这就是“生理惯性”的核心：激素水平决定了情绪的基准线（Floor）
        
        # [压力钳制]：如果体内皮质醇高，负面情绪无法彻底消失
        stress_floor = neuro['cortisol'] * 0.5  # 压力的一半转化为负面情绪基底
        
        # 应用钳制：不仅针对 Anger，也针对 Fear 和 Disgust (8向量的完整性)
        for neg_emo in ['anger', 'fear', 'disgust']:
            # 情绪不能低于压力基底
            emotions[neg_emo] = max(stress_floor, emotions[neg_emo])
        
        # [压力抑制]：皮质醇高时，快乐和信任极难建立
        if neuro['cortisol'] > 0.5:
            # 强制压制正面情绪，使其快速衰减
            suppression_factor = 1.0 + (neuro['cortisol'] - 0.5) * 2.0
            emotions['joy'] *= (1.0 - 0.01 * suppression_factor)
            emotions['trust'] *= (1.0 - 0.01 * suppression_factor)

        # [多巴胺加成]：多巴胺高时，悲伤衰减加快
        if neuro['dopamine'] > 0.5:
            emotions['sadness'] *= 0.95

        # 4. 数值安全钳位
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