"""
自适应PID参数调整 (Adaptive PID Parameter Tuning)

基于强化学习的动态PID参数调整系统，用于优化女娲系统的控制性能。

核心思想：
- 使用PPO代理根据系统状态动态调整PID参数
- 实时适应不同的交互模式
- 通过奖励机制优化控制性能
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from collections import deque
import random

# 尝试导入必要的库
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .nuwa_state import NuwaState


@dataclass
class PIDController:
    """基础PID控制器"""
    
    kp: float = 1.0      # 比例增益
    ki: float = 0.1      # 积分增益
    kd: float = 0.01     # 微分增益
    
    # 积分项累积
    _integral: float = 0.0
    _last_error: float = 0.0
    
    # 参数边界
    kp_min: float = 0.0
    kp_max: float = 5.0
    ki_min: float = 0.0
    ki_max: float = 2.0
    kd_min: float = 0.0
    kd_max: float = 1.0
    
    def compute(self, error: float, dt: float = 1.0) -> float:
        """
        计算PID输出
        
        Args:
            error: 误差值 (目标 - 实际)
            dt: 时间步长
            
        Returns:
            控制输出
        """
        # 积分项
        self._integral += error * dt
        self._integral = np.clip(self._integral, -10.0, 10.0)  # 抗积分饱和
        
        # 微分项
        derivative = (error - self._last_error) / dt if dt > 0 else 0.0
        
        # PID输出
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        
        # 更新历史
        self._last_error = error
        
        return output
    
    def reset(self):
        """重置PID状态"""
        self._integral = 0.0
        self._last_error = 0.0
    
    def clamp_parameters(self):
        """限制参数在有效范围内"""
        self.kp = np.clip(self.kp, self.kp_min, self.kp_max)
        self.ki = np.clip(self.ki, self.ki_min, self.ki_max)
        self.kd = np.clip(self.kd, self.kd_min, self.kd_max)


class PPOAgent:
    """
    PPO代理 - 用于调整PID参数
    
    简化版PPO，用于连续动作空间
    """
    
    def __init__(self, state_dim: int = 17, action_dim: int = 3):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        if TORCH_AVAILABLE:
            self.actor = ActorNetwork(state_dim, action_dim)
            self.critic = CriticNetwork(state_dim)
            self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=1e-4)
            self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=1e-3)
            
            # 经验缓冲区
            self.memory = []
            self.max_memory = 1000
        
        # 探索参数
        self.epsilon = 0.2  # PPO裁剪参数
        self.gamma = 0.99   # 折扣因子
        self.tau = 0.95     # GAE参数
        
        # 统计信息
        self.total_steps = 0
        self.episode_reward = 0.0
    
    def select_action(self, state_vector: np.ndarray) -> Dict[str, float]:
        """
        根据状态选择动作（PID参数调整量）
        
        Args:
            state_vector: 系统状态向量
            
        Returns:
            动作字典：kp_delta, ki_delta, kd_delta
        """
        if not TORCH_AVAILABLE or self.actor is None:
            # 回退到随机探索
            return {
                'kp_delta': random.uniform(-0.1, 0.1),
                'ki_delta': random.uniform(-0.05, 0.05),
                'kd_delta': random.uniform(-0.02, 0.02),
            }
        
        # 转换为tensor
        state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
        
        # 获取动作分布
        with torch.no_grad():
            action_mean, action_std = self.actor(state_tensor)
            
            # 创建正态分布
            from torch.distributions import Normal
            dist = Normal(action_mean, action_std)
            
            # 采样动作
            action = dist.sample()
            
            # 转换为numpy
            action_np = action.numpy()[0]
        
        # 限制动作幅度
        action_np = np.clip(action_np, -0.2, 0.2)
        
        return {
            'kp_delta': float(action_np[0]),
            'ki_delta': float(action_np[1]),
            'kd_delta': float(action_np[2]),
        }
    
    def update(self, state: np.ndarray, action: Dict[str, float], reward: float, next_state: Optional[np.ndarray] = None):
        """
        更新PPO代理
        
        Args:
            state: 当前状态
            action: 执行的动作
            reward: 获得的奖励
            next_state: 下一个状态（可选）
        """
        if not TORCH_AVAILABLE:
            return
        
        # 存储经验
        self.memory.append({
            'state': state,
            'action': np.array([action['kp_delta'], action['ki_delta'], action['kd_delta']]),
            'reward': reward,
            'next_state': next_state if next_state is not None else state,
        })
        
        self.total_steps += 1
        self.episode_reward += reward
        
        # 经验回放训练
        if len(self.memory) >= 128:  # 批量大小
            self._train()
            self.memory = []  # 清空缓冲区
    
    def _train(self):
        """执行PPO训练"""
        if len(self.memory) == 0:
            return
        
        # 转换为批量
        batch = {k: [d[k] for d in self.memory] for k in self.memory[0].keys()}
        
        states = torch.FloatTensor(np.array(batch['state']))
        actions = torch.FloatTensor(np.array(batch['action']))
        rewards = torch.FloatTensor(np.array(batch['reward'])).unsqueeze(1)
        next_states = torch.FloatTensor(np.array(batch['next_state']))
        
        # 计算优势函数
        with torch.no_grad():
            values = self.critic(states)
            next_values = self.critic(next_states)
            
            # GAE优势计算
            deltas = rewards + self.gamma * next_values - values
            advantages = self._compute_gae(deltas, values)
        
        # 计算旧策略的概率
        old_mean, old_std = self.actor(states)
        from torch.distributions import Normal
        old_dist = Normal(old_mean, old_std)
        old_log_prob = old_dist.log_prob(actions).sum(dim=1, keepdim=True)
        
        # PPO更新（多次）
        for _ in range(4):
            # 新策略
            new_mean, new_std = self.actor(states)
            new_dist = Normal(new_mean, new_std)
            new_log_prob = new_dist.log_prob(actions).sum(dim=1, keepdim=True)
            
            # 比例
            ratio = torch.exp(new_log_prob - old_log_prob)
            
            # PPO损失
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.epsilon, 1 + self.epsilon) * advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # 价值损失
            values_pred = self.critic(states)
            critic_loss = nn.MSELoss()(values_pred, values + advantages)
            
            # 更新Actor
            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()
            
            # 更新Critic
            self.critic_optimizer.zero_grad()
            critic_loss.backward()
            self.critic_optimizer.step()
    
    def _compute_gae(self, deltas: torch.Tensor, values: torch.Tensor) -> torch.Tensor:
        """计算广义优势估计(GAE)"""
        advantages = torch.zeros_like(deltas)
        gae = 0
        for t in reversed(range(len(deltas))):
            gae = deltas[t] + self.gamma * self.tau * gae
            advantages[t] = gae
        return advantages
    
    def get_stats(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        return {
            'total_steps': self.total_steps,
            'episode_reward': self.episode_reward,
            'memory_size': len(self.memory) if hasattr(self, 'memory') else 0,
        }


class ActorNetwork(nn.Module):
    """Actor网络 - 输出PID参数调整量"""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        
        self.action_dim = action_dim
        
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim * 2),  # 输出均值和标准差
        )
        
        # 初始标准差
        self.log_std = nn.Parameter(torch.zeros(action_dim))
        
    def forward(self, x: torch.Tensor):
        x = self.net(x)
        
        # 分离均值和标准差
        mean = x[:, :self.action_dim]
        log_std = x[:, self.action_dim:] + self.log_std
        
        # 标准差必须为正
        std = torch.exp(log_std)
        
        return mean, std


class CriticNetwork(nn.Module):
    """Critic网络 - 评估状态价值"""
    
    def __init__(self, state_dim: int):
        super().__init__()
        
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),  # 输出标量价值
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class AdaptivePIDController:
    """自适应PID控制器 - 基于RL代理调整PID参数"""
    
    base_pid: PIDController = field(default_factory=PIDController)
    rl_agent: Optional[PPOAgent] = None
    
    # 性能跟踪
    performance_history: deque = field(default_factory=lambda: deque(maxlen=100))
    error_history: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # 自适应参数
    adaptation_rate: float = 0.1  # 参数调整速率
    performance_threshold: float = 0.8  # 性能阈值
    
    # 统计信息
    total_adaptations: int = 0
    avg_performance: float = 0.0
    
    def __post_init__(self):
        """初始化后配置RL代理"""
        if self.rl_agent is None:
            # 默认状态维度：NuwaState的向量表示维度
            # NuwaState有：energy, entropy, rapport, 3个drives, 6个emotions, 3个额外状态 = 17
            state_dim = 17
            action_dim = 3  # kp, ki, kd 三个参数的调整
            self.rl_agent = PPOAgent(state_dim, action_dim)
    
    def update_parameters(self, state: NuwaState, performance: float):
        """
        基于RL代理调整PID参数
        
        Args:
            state: 当前系统状态
            performance: 当前性能指标 (0-1)
        """
        # 1. 记录性能和误差
        self.performance_history.append(performance)
        
        # 计算误差（目标性能为1.0）
        error = 1.0 - performance
        self.error_history.append(error)
        
        # 2. 获取状态向量
        state_vector = self._state_to_vector(state)
        
        # 3. RL代理选择动作
        action = self.rl_agent.select_action(state_vector)
        
        # 4. 更新PID参数
        old_params = (self.base_pid.kp, self.base_pid.ki, self.base_pid.kd)
        
        self.base_pid.kp += action['kp_delta'] * self.adaptation_rate
        self.base_pid.ki += action['ki_delta'] * self.adaptation_rate
        self.base_pid.kd += action['kd_delta'] * self.adaptation_rate
        
        # 限制参数范围
        self.base_pid.clamp_parameters()
        
        # 5. 计算奖励
        reward = self.calculate_reward(performance, error, old_params)
        
        # 6. 更新RL代理
        next_state = state  # 简化：假设状态变化不大
        self.rl_agent.update(state_vector, action, reward, self._state_to_vector(next_state))
        
        # 7. 更新统计信息
        self.total_adaptations += 1
        self._update_avg_performance(performance)
        
        if abs(action['kp_delta']) > 0.01 or abs(action['ki_delta']) > 0.01 or abs(action['kd_delta']) > 0.01:
            print(f"[AdaptivePID] 调整: ∆kp={action['kp_delta']:.4f}, ∆ki={action['ki_delta']:.4f}, ∆kd={action['kd_delta']:.4f}")
            print(f"[AdaptivePID] 新参数: kp={self.base_pid.kp:.4f}, ki={self.base_pid.ki:.4f}, kd={self.base_pid.kd:.4f}")
    
    def calculate_reward(self, performance: float, error: float, old_params: tuple) -> float:
        """
        计算奖励函数
        
        奖励 = 性能提升 - 参数变化惩罚 - 误差惩罚
        
        Args:
            performance: 当前性能
            error: 误差
            old_params: 旧参数 (kp, ki, kd)
            
        Returns:
            奖励值
        """
        # 1. 性能奖励（越高越好）
        performance_reward = performance * 2.0
        
        # 2. 误差惩罚（越低越好）
        error_penalty = -error * 1.0
        
        # 3. 参数变化惩罚（鼓励稳定性）
        new_params = (self.base_pid.kp, self.base_pid.ki, self.base_pid.kd)
        param_change = sum(abs(new - old) for new, old in zip(new_params, old_params))
        stability_penalty = -param_change * 0.5
        
        # 4. 性能趋势奖励（如果性能在提升）
        trend_bonus = 0.0
        if len(self.performance_history) >= 2:
            recent = list(self.performance_history)[-5:]
            if len(recent) >= 2 and np.mean(recent[-2:]) > np.mean(recent[:2]):
                trend_bonus = 0.2
        
        # 总奖励
        total_reward = performance_reward + error_penalty + stability_penalty + trend_bonus
        
        # 限制奖励范围
        total_reward = np.clip(total_reward, -5.0, 5.0)
        
        return total_reward
    
    def _state_to_vector(self, state: NuwaState) -> np.ndarray:
        """
        将NuwaState转换为状态向量
        
        结构：
        [energy, entropy, rapport, 
         social_hunger, curiosity, drive3,
         joy, sadness, anger, fear, surprise, trust,
         stability, adaptability, memory_usage]
        """
        vector = []
        
        # 基础状态 (3)
        vector.extend([
            state.energy,
            state.system_entropy,
            state.rapport,
        ])
        
        # 驱动力 (3)
        drives = list(state.drives.values())
        if len(drives) >= 3:
            vector.extend(drives[:3])
        else:
            vector.extend(drives + [0.0] * (3 - len(drives)))
        
        # 情绪谱 (6)
        emotions = list(state.emotional_spectrum.values())
        if len(emotions) >= 6:
            vector.extend(emotions[:6])
        else:
            vector.extend(emotions + [0.0] * (6 - len(emotions)))
        
        # 额外状态 - 基于当前状态计算 (3)
        # 稳定性：熵值的倒数
        stability = 1.0 - state.system_entropy if state.system_entropy < 1.0 else 0.0
        vector.append(stability)
        
        # 适应性：基于能量和熵
        adaptability = (state.energy * 0.5 + (1.0 - state.system_entropy) * 0.5)
        vector.append(adaptability)
        
        # 记忆使用率（估算）
        memory_usage = min(1.0, len(self.performance_history) / 100.0)
        vector.append(memory_usage)
        
        # 确保长度为17
        if len(vector) < 17:
            vector.extend([0.0] * (17 - len(vector)))
        elif len(vector) > 17:
            vector = vector[:17]
        
        return np.array(vector, dtype=np.float32)
    
    def _update_avg_performance(self, performance: float):
        """更新平均性能"""
        if len(self.performance_history) > 0:
            self.avg_performance = np.mean(list(self.performance_history)[-50:])
    
    def get_status(self) -> Dict[str, Any]:
        """获取控制器状态"""
        return {
            'pid_parameters': {
                'kp': self.base_pid.kp,
                'ki': self.base_pid.ki,
                'kd': self.base_pid.kd,
            },
            'performance': {
                'current': self.performance_history[-1] if self.performance_history else 0.0,
                'average': self.avg_performance,
                'history': list(self.performance_history)[-10:],
            },
            'rl_agent': self.rl_agent.get_stats(),
            'adaptations': self.total_adaptations,
        }
    
    def reset(self):
        """重置控制器状态"""
        self.base_pid.reset()
        self.performance_history.clear()
        self.error_history.clear()
        self.total_adaptations = 0
        self.avg_performance = 0.0


# ==================== 兼容性接口 ====================

def create_adaptive_controller(kp: float = 1.0, ki: float = 0.1, kd: float = 0.01) -> AdaptivePIDController:
    """
    创建自适应PID控制器（兼容性函数）
    
    Args:
        kp: 初始比例增益
        ki: 初始积分增益
        kd: 初始微分增益
        
    Returns:
        自适应PID控制器实例
    """
    base_pid = PIDController(kp=kp, ki=ki, kd=kd)
    return AdaptivePIDController(base_pid=base_pid)


def compute_control_output(controller: AdaptivePIDController, error: float, state: NuwaState, performance: float) -> tuple[float, Dict[str, Any]]:
    """
    计算控制输出（兼容性函数）
    
    Args:
        controller: 自适应PID控制器
        error: 误差值
        state: 系统状态
        performance: 性能指标
        
    Returns:
        (控制输出, 控制器状态)
    """
    # 更新参数
    controller.update_parameters(state, performance)
    
    # 计算输出
    output = controller.base_pid.compute(error)
    
    # 获取状态
    status = controller.get_status()
    
    return output, status


# ==================== 使用示例 ====================

def demo_adaptive_pid():
    """演示自适应PID控制器的使用"""
    print("="*60)
    print("自适应PID控制器演示")
    print("="*60)
    
    # 创建控制器
    controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.05)
    
    # 模拟系统状态
    state = NuwaState()
    state.energy = 0.8
    state.system_entropy = 0.3
    state.rapport = 0.7
    state.drives = {"social_hunger": 0.6, "curiosity": 0.8, "exploration": 0.5}
    state.emotional_spectrum = {"joy": 0.5, "sadness": 0.1, "anger": 0.0, "fear": 0.2, "surprise": 0.3, "trust": 0.6}
    
    print("\n初始状态:")
    print(f"  PID参数: kp={controller.base_pid.kp}, ki={controller.base_pid.ki}, kd={controller.base_pid.kd}")
    
    # 模拟控制过程
    print("\n模拟控制过程:")
    for i in range(10):
        # 模拟误差（逐渐减小）
        error = max(0.0, 0.5 - i * 0.04)
        
        # 模拟性能（逐渐提升）
        performance = min(1.0, 0.6 + i * 0.03)
        
        # 计算控制输出
        output, status = compute_control_output(controller, error, state, performance)
        
        print(f"  迭代 {i+1}: 误差={error:.3f}, 性能={performance:.3f}, 输出={output:.3f}")
        
        # 更新状态（模拟）
        state.energy = max(0.1, state.energy - 0.02)
        state.system_entropy = max(0.0, state.system_entropy - 0.01)
    
    print("\n最终状态:")
    final_status = controller.get_status()
    print(f"  PID参数: {final_status['pid_parameters']}")
    print(f"  平均性能: {final_status['performance']['average']:.3f}")
    print(f"  总调整次数: {final_status['adaptations']}")
    print(f"  RL代理统计: {final_status['rl_agent']}")
    
    print("\n[OK] 自适应PID控制器演示完成")