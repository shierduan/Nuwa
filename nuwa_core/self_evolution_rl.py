"""
强化学习自我进化模块 (Reinforcement Learning Self Evolution)

功能：基于强化学习的自我进化机制，通过Q-Learning优化人格参数。

核心特性：
- Q网络：学习最优人格参数调整策略
- 经验回放：存储交互历史和奖励
- 奖励函数：基于用户满意度、对话质量、情绪稳定性
- 异步训练：支持后台训练和实时进化

技术栈：
- Q-Learning: 离散状态下的强化学习
- PyTorch (可选): 用于神经网络实现
- NumPy: 数值计算
"""

import json
import os
import time
import random
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import deque
import threading

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # 如果没有PyTorch，使用NumPy实现简单的Q表
    pass


class Interaction:
    """
    交互记录 - 封装一次完整的对话交互
    
    用于强化学习的奖励计算
    """
    
    def __init__(self, user_input: str, ai_response: str, 
                 user_satisfaction: float = 0.5,
                 quality_score: float = 0.5,
                 emotional_stability: float = 0.5,
                 timestamp: Optional[float] = None):
        """
        初始化交互记录
        
        Args:
            user_input: 用户输入
            ai_response: AI回复
            user_satisfaction: 用户满意度 (0-1)
            quality_score: 对话质量 (0-1)
            emotional_stability: 情绪稳定性 (0-1)
            timestamp: 时间戳
        """
        self.user_input = user_input
        self.ai_response = ai_response
        self.user_satisfaction = float(user_satisfaction)
        self.quality_score = float(quality_score)
        self.emotional_stability = float(emotional_stability)
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_input": self.user_input,
            "ai_response": self.ai_response,
            "user_satisfaction": self.user_satisfaction,
            "quality_score": self.quality_score,
            "emotional_stability": self.emotional_stability,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Interaction':
        """从字典创建"""
        return cls(
            user_input=data["user_input"],
            ai_response=data["ai_response"],
            user_satisfaction=data["user_satisfaction"],
            quality_score=data["quality_score"],
            emotional_stability=data["emotional_stability"],
            timestamp=data["timestamp"],
        )


class ReplayBuffer:
    """
    经验回放缓冲区 - 存储交互历史
    
    功能：
    - 添加交互记录
    - 采样训练批次
    - 保存/加载经验
    - 自动清理旧经验
    """
    
    def __init__(self, capacity: int = 10000):
        """
        初始化经验回放缓冲区
        
        Args:
            capacity: 最大容量
        """
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.lock = threading.Lock()
        
        print(f"[OK] ReplayBuffer 初始化完成，容量: {capacity}")
    
    def add(self, interaction: Interaction, reward: float):
        """
        添加交互和奖励
        
        Args:
            interaction: 交互记录
            reward: 奖励值
        """
        with self.lock:
            experience = {
                "interaction": interaction,
                "reward": reward,
                "timestamp": time.time(),
            }
            self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Dict[str, Any]]:
        """
        采样训练批次
        
        Args:
            batch_size: 批次大小
            
        Returns:
            经验列表
        """
        with self.lock:
            if len(self.buffer) < batch_size:
                return list(self.buffer)
            
            return random.sample(list(self.buffer), batch_size)
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """当前大小"""
        return len(self.buffer)
    
    def is_ready(self, threshold: int = 1000) -> bool:
        """
        检查是否准备好训练
        
        Args:
            threshold: 训练阈值
            
        Returns:
            是否可以训练
        """
        return self.size() >= threshold
    
    def save(self, filepath: str) -> bool:
        """
        保存经验到文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            是否成功
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with self.lock:
                data = [exp["interaction"].to_dict() for exp in self.buffer]
                rewards = [exp["reward"] for exp in self.buffer]
                timestamps = [exp["timestamp"] for exp in self.buffer]
            
            save_data = {
                "interactions": data,
                "rewards": rewards,
                "timestamps": timestamps,
                "metadata": {
                    "size": len(data),
                    "saved_at": datetime.now().isoformat(),
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"[WARN] 保存经验失败: {e}")
            return False
    
    def load(self, filepath: str) -> bool:
        """
        从文件加载经验
        
        Args:
            filepath: 文件路径
            
        Returns:
            是否成功
        """
        if not os.path.exists(filepath):
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            interactions = save_data["interactions"]
            rewards = save_data["rewards"]
            timestamps = save_data["timestamps"]
            
            with self.lock:
                self.buffer.clear()
                for i, inter_data in enumerate(interactions):
                    interaction = Interaction.from_dict(inter_data)
                    experience = {
                        "interaction": interaction,
                        "reward": rewards[i],
                        "timestamp": timestamps[i],
                    }
                    self.buffer.append(experience)
            
            print(f"📥 已加载 {len(interactions)} 条经验")
            return True
        except Exception as e:
            print(f"[WARN] 加载经验失败: {e}")
            return False


class QNetwork:
    """
    Q网络 - 离散状态下的Q值估计
    
    如果PyTorch可用，使用神经网络；
    否则，使用Q表（NumPy数组）
    """
    
    def __init__(self, state_dim: int, action_dim: int, learning_rate: float = 0.001):
        """
        初始化Q网络
        
        Args:
            state_dim: 状态维度
            action_dim: 动作维度
            learning_rate: 学习率
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        
        if TORCH_AVAILABLE:
            self.model = NeuralNetwork(state_dim, action_dim)
            self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
            self.use_torch = True
            print(f"[OK] QNetwork 使用PyTorch实现")
        else:
            # 使用Q表
            self.q_table = np.zeros((state_dim, action_dim))
            self.use_torch = False
            print(f"[WARN] QNetwork 使用NumPy Q表实现（未安装PyTorch）")
    
    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """
        获取状态的Q值
        
        Args:
            state: 状态向量
            
        Returns:
            Q值数组
        """
        if self.use_torch:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                q_values = self.model(state_tensor).numpy()[0]
                return q_values
        else:
            # Q表查找（状态离散化）
            state_idx = self._discretize_state(state)
            return self.q_table[state_idx]
    
    def update(self, states: np.ndarray, actions: np.ndarray, targets: np.ndarray):
        """
        更新Q网络
        
        Args:
            states: 状态批次
            actions: 动作批次
            targets: 目标Q值批次
        """
        if self.use_torch:
            # PyTorch训练
            states_tensor = torch.FloatTensor(states)
            actions_tensor = torch.LongTensor(actions)
            targets_tensor = torch.FloatTensor(targets)
            
            # 前向传播
            current_q = self.model(states_tensor)
            
            # 选择执行的动作的Q值
            current_q_selected = current_q.gather(1, actions_tensor.unsqueeze(1)).squeeze()
            
            # 计算损失
            loss = nn.MSELoss()(current_q_selected, targets_tensor)
            
            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
        else:
            # Q表更新
            for i in range(len(states)):
                state_idx = self._discretize_state(states[i])
                action = actions[i]
                target = targets[i]
                
                # 简单的Q学习更新
                learning_rate = 0.1
                self.q_table[state_idx, action] += learning_rate * (target - self.q_table[state_idx, action])
    
    def _discretize_state(self, state: np.ndarray) -> int:
        """
        将连续状态离散化为Q表索引
        
        Args:
            state: 连续状态
            
        Returns:
            离散状态索引
        """
        if not NUMPY_AVAILABLE:
            return 0
        
        # 简单的离散化：将每个维度分为3个区间（低、中、高）
        discretized = []
        for val in state:
            if val < 0.33:
                discretized.append(0)
            elif val < 0.66:
                discretized.append(1)
            else:
                discretized.append(2)
        
        # 转换为一维索引
        idx = 0
        for i, d in enumerate(discretized):
            idx += d * (3 ** i)
        
        return idx % self.state_dim  # 确保在范围内


class NeuralNetwork(nn.Module):
    """神经网络Q网络（PyTorch实现）"""
    
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, action_dim)
        self.relu = nn.ReLU()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class SelfEvolutionRL:
    """
    强化学习自我进化管理类
    
    功能：
    - Q网络学习最优人格参数调整策略
    - 经验回放存储交互历史
    - 奖励函数计算
    - 异步训练和进化
    """
    
    def __init__(self, state_manager, memory_cortex, llm_client, 
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化强化学习自我进化
        
        Args:
            state_manager: 状态管理器
            memory_cortex: 记忆皮层
            llm_client: LLM客户端
            config: 配置参数
        """
        self.state_manager = state_manager
        self.memory_cortex = memory_cortex
        self.llm_client = llm_client
        
        # 默认配置
        self.config = {
            "state_dim": 17,  # 状态维度（3个核心属性 + 8个情绪 + 2个驱动力 + 4个历史统计）
            "action_dim": 13,  # 动作维度（13个可调整参数）
            "learning_rate": 0.001,
            "gamma": 0.99,  # 折扣因子
            "epsilon": 0.1,  # 探索率
            "batch_size": 64,
            "target_update_freq": 100,  # 目标网络更新频率
            "experience_threshold": 1000,  # 训练阈值
            "evolution_interval": 3600,  # 进化间隔（秒）
            "max_history": 50,  # 历史记录最大长度
        }
        
        if config:
            self.config.update(config)
        
        # 经验回放缓冲区
        self.replay_buffer = ReplayBuffer(capacity=10000)
        
        # Q网络
        self.q_network = QNetwork(
            state_dim=self.config["state_dim"],
            action_dim=self.config["action_dim"],
            learning_rate=self.config["learning_rate"]
        )
        
        # 目标网络（用于稳定训练）
        if self.q_network.use_torch:
            self.target_network = QNetwork(
                state_dim=self.config["state_dim"],
                action_dim=self.config["action_dim"]
            )
            self.target_network.model.load_state_dict(self.q_network.model.state_dict())
        else:
            self.target_network = None
        
        # 进化状态
        self.evolution_state = {
            "last_evolution_time": 0.0,
            "evolution_count": 0,
            "total_reward": 0.0,
            "training_loss": 0.0,
            "is_training": False,
        }
        
        # 训练控制
        self._training_task = None
        self._stop_training = False
        
        print("=" * 60)
        print("🤖 SelfEvolutionRL 初始化完成")
        print(f"   状态维度: {self.config['state_dim']}")
        print(f"   动作维度: {self.config['action_dim']}")
        print(f"   使用PyTorch: {self.q_network.use_torch}")
        print("=" * 60)
    
    def get_state_vector(self) -> np.ndarray:
        """
        获取当前状态向量
        
        状态向量结构：
        [核心属性(3) + 情绪(8) + 驱动力(2) + 历史统计(4)] = 17维
        
        Returns:
            状态向量
        """
        if not NUMPY_AVAILABLE:
            return np.array([0.5] * self.config["state_dim"])
        
        state = self.state_manager.get_state()
        
        # 核心属性
        core_attrs = [
            state.energy,
            state.system_entropy,
            state.rapport,
        ]
        
        # 情绪谱（8维）
        emotions = list(state.emotional_spectrum.values())
        
        # 驱动力（2维）
        drives = list(state.drives.values())
        
        # 历史统计（4维）- 从记忆皮层获取
        history_stats = [0.5, 0.5, 0.5, 0.5]  # 默认值
        try:
            if hasattr(self.memory_cortex, 'get_index_info'):
                info = self.memory_cortex.get_index_info()
                if info:
                    # 使用记忆数量、平均相似度等作为统计
                    memory_count = info.get('count', 0)
                    normalized_count = min(memory_count / 1000.0, 1.0)
                    history_stats = [normalized_count, 0.5, 0.5, 0.5]
        except:
            pass
        
        # 组合状态向量
        state_vector = np.array(core_attrs + emotions + drives + history_stats, dtype=np.float32)
        
        # 确保在[0, 1]范围内
        state_vector = np.clip(state_vector, 0.0, 1.0)
        
        return state_vector
    
    def get_action_space(self) -> List[Dict[str, Any]]:
        """
        获取动作空间定义
        
        动作对应13个可调整参数：
        0-7: 情绪参数 (joy, anger, sadness, fear, trust, anticipation, disgust, surprise)
        8-9: 驱动力 (social_hunger, curiosity)
        10-12: 核心属性 (energy, system_entropy, rapport)
        
        Returns:
            动作描述列表
        """
        return [
            {"param": "joy", "desc": "增加喜悦", "effect": 0.1},
            {"param": "anger", "desc": "减少愤怒", "effect": -0.1},
            {"param": "sadness", "desc": "减少悲伤", "effect": -0.1},
            {"param": "fear", "desc": "减少恐惧", "effect": -0.1},
            {"param": "trust", "desc": "增加信任", "effect": 0.1},
            {"param": "anticipation", "desc": "增加期待", "effect": 0.1},
            {"param": "disgust", "desc": "减少厌恶", "effect": -0.1},
            {"param": "surprise", "desc": "增加惊喜", "effect": 0.1},
            {"param": "social_hunger", "desc": "降低社交饥渴", "effect": -0.15},
            {"param": "curiosity", "desc": "增加好奇心", "effect": 0.1},
            {"param": "energy", "desc": "恢复精力", "effect": 0.2},
            {"param": "system_entropy", "desc": "降低系统熵", "effect": -0.15},
            {"param": "rapport", "desc": "增进亲密度", "effect": 0.1},
        ]
    
    def calculate_reward(self, interaction: Interaction) -> float:
        """
        计算单次交互的奖励值
        
        奖励公式：
        reward = 0.4 * user_satisfaction + 0.3 * conversation_quality + 0.3 * emotional_stability
        
        Args:
            interaction: 交互记录
            
        Returns:
            奖励值 (-1.0 到 1.0)
        """
        # 基础奖励计算
        base_reward = (
            0.4 * interaction.user_satisfaction +
            0.3 * interaction.quality_score +
            0.3 * interaction.emotional_stability
        )
        
        # 惩罚项：如果用户满意度过低
        if interaction.user_satisfaction < 0.3:
            base_reward -= 0.2
        
        # 奖励项：如果所有指标都很高
        if (interaction.user_satisfaction > 0.7 and 
            interaction.quality_score > 0.7 and 
            interaction.emotional_stability > 0.7):
            base_reward += 0.1
        
        return np.clip(base_reward, -1.0, 1.0)
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        选择动作（Epsilon-Greedy策略）
        
        Args:
            state: 当前状态
            training: 是否在训练模式
            
        Returns:
            动作索引
        """
        if training and random.random() < self.config["epsilon"]:
            # 探索：随机选择动作
            return random.randint(0, self.config["action_dim"] - 1)
        
        # 利用：选择Q值最高的动作
        q_values = self.q_network.get_q_values(state)
        return int(np.argmax(q_values))
    
    def apply_action(self, action_idx: int, reward: float) -> bool:
        """
        应用动作（调整人格参数）
        
        Args:
            action_idx: 动作索引
            reward: 奖励值（用于调整强度）
            
        Returns:
            是否成功
        """
        action_space = self.get_action_space()
        
        if action_idx >= len(action_space):
            return False
        
        action = action_space[action_idx]
        param = action["param"]
        base_effect = action["effect"]
        
        # 根据奖励调整效果强度
        # 奖励越高，正向动作越强；奖励越低，负向动作越强
        intensity = abs(reward) * 0.5 + 0.5  # 映射到 [0.5, 1.0]
        effect = base_effect * intensity
        
        # 构建状态更新
        state_update = {param: effect}
        
        # 应用更新
        self.state_manager.update_state(state_update)
        
        if self.config.get("enable_debug", False):
            print(f"🎯 应用动作 {action_idx}: {param} = {effect:.3f}")
        
        return True
    
    async def evolve(self, interaction_history: List[Interaction]) -> Dict[str, Any]:
        """
        异步进化方法
        
        1. 为历史交互计算奖励
        2. 存储到经验回放缓冲区
        3. 如果经验足够，触发训练
        4. 更新进化状态
        
        Args:
            interaction_history: 交互历史列表
            
        Returns:
            进化结果
        """
        if not interaction_history:
            return {"error": "无交互历史"}
        
        # 1. 计算奖励并存储经验
        total_reward = 0
        for interaction in interaction_history:
            reward = self.calculate_reward(interaction)
            self.replay_buffer.add(interaction, reward)
            total_reward += reward
        
        avg_reward = total_reward / len(interaction_history)
        
        # 2. 更新进化状态
        self.evolution_state["last_evolution_time"] = time.time()
        self.evolution_state["evolution_count"] += 1
        self.evolution_state["total_reward"] += avg_reward
        
        # 3. 检查是否需要训练
        result = {
            "evolution_count": self.evolution_state["evolution_count"],
            "buffer_size": self.replay_buffer.size(),
            "avg_reward": avg_reward,
            "trained": False,
        }
        
        if self.replay_buffer.is_ready(self.config["experience_threshold"]):
            # 触发训练
            training_result = await self.train_evolution_policy()
            result.update(training_result)
            result["trained"] = True
        
        # 4. 检查是否需要应用进化
        current_time = time.time()
        if current_time - self.evolution_state["last_evolution_time"] >= self.config["evolution_interval"]:
            await self.apply_evolution()
            result["evolution_applied"] = True
        
        return result
    
    async def train_evolution_policy(self) -> Dict[str, Any]:
        """
        训练进化策略
        
        使用经验回放进行Q-Learning训练
        
        Returns:
            训练结果
        """
        if self.replay_buffer.size() < self.config["batch_size"]:
            return {"error": "经验不足"}
        
        # 采样批次
        batch = self.replay_buffer.sample(self.config["batch_size"])
        
        # 准备训练数据
        states = []
        actions = []
        rewards = []
        next_states = []
        
        for experience in batch:
            interaction = experience["interaction"]
            reward = experience["reward"]
            
            # 获取当前状态和下一状态
            current_state = self.get_state_vector()
            
            # 应用动作后的状态（近似）
            # 这里简化处理：假设应用动作后状态有微小变化
            next_state = current_state + np.random.normal(0, 0.01, size=current_state.shape)
            next_state = np.clip(next_state, 0.0, 1.0)
            
            # 选择动作（基于当前状态）
            action = self.select_action(current_state, training=True)
            
            states.append(current_state)
            actions.append(action)
            rewards.append(reward)
            next_states.append(next_state)
        
        states = np.array(states)
        actions = np.array(actions)
        rewards = np.array(rewards)
        next_states = np.array(next_states)
        
        # 计算目标Q值
        if self.q_network.use_torch:
            # 使用目标网络计算下一状态的Q值
            with torch.no_grad():
                next_q_values = self.target_network.model(torch.FloatTensor(next_states)).numpy()
            max_next_q = np.max(next_q_values, axis=1)
        else:
            # 使用Q表
            max_next_q = np.max([self.q_network.get_q_values(ns) for ns in next_states], axis=0)
        
        # Q-Learning目标: target = reward + gamma * max_next_q
        targets = rewards + self.config["gamma"] * max_next_q
        
        # 更新Q网络
        self.q_network.update(states, actions, targets)
        
        # 更新目标网络（定期）
        if (self.evolution_state.get("training_step", 0) % self.config["target_update_freq"] == 0 and 
            self.q_network.use_torch):
            self.target_network.model.load_state_dict(self.q_network.model.state_dict())
        
        # 记录训练状态
        self.evolution_state["training_step"] = self.evolution_state.get("training_step", 0) + 1
        self.evolution_state["training_loss"] = float(np.mean(np.abs(targets)))  # 简单的损失估计
        
        return {
            "training_step": self.evolution_state["training_step"],
            "loss": self.evolution_state["training_loss"],
            "batch_size": len(batch),
        }
    
    async def apply_evolution(self) -> Dict[str, Any]:
        """
        应用进化 - 基于当前Q网络调整人格参数
        
        Returns:
            应用结果
        """
        current_state = self.get_state_vector()
        
        # 选择最优动作
        best_action = self.select_action(current_state, training=False)
        
        # 获取动作对应的参数调整
        action_space = self.get_action_space()
        action = action_space[best_action]
        
        # 应用调整（使用平均奖励作为强度）
        avg_reward = self.evolution_state.get("total_reward", 0) / max(self.evolution_state["evolution_count"], 1)
        
        success = self.apply_action(best_action, avg_reward)
        
        result = {
            "action_idx": best_action,
            "param": action["param"],
            "effect": action["effect"],
            "applied": success,
            "avg_reward": avg_reward,
        }
        
        if success:
            print(f"✨ 进化应用成功: {action['desc']} (强度: {avg_reward:.3f})")
        
        return result
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """
        获取进化状态总结
        
        Returns:
            进化状态信息
        """
        return {
            "evolution_count": self.evolution_state["evolution_count"],
            "total_reward": self.evolution_state["total_reward"],
            "avg_reward": self.evolution_state["total_reward"] / max(self.evolution_state["evolution_count"], 1),
            "experience_buffer_size": self.replay_buffer.size(),
            "training_step": self.evolution_state.get("training_step", 0),
            "training_loss": self.evolution_state["training_loss"],
            "last_evolution_time": self.evolution_state["last_evolution_time"],
            "is_training": self.evolution_state["is_training"],
        }
    
    def save_state(self, directory: str) -> bool:
        """
        保存进化状态
        
        Args:
            directory: 保存目录
            
        Returns:
            是否成功
        """
        try:
            os.makedirs(directory, exist_ok=True)
            
            # 保存进化状态
            state_file = os.path.join(directory, "evolution_state.json")
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.evolution_state, f, ensure_ascii=False, indent=2)
            
            # 保存经验回放
            buffer_file = os.path.join(directory, "experience_buffer.json")
            self.replay_buffer.save(buffer_file)
            
            # 保存Q网络（如果使用PyTorch）
            if self.q_network.use_torch:
                qnet_file = os.path.join(directory, "q_network.pth")
                torch.save(self.q_network.model.state_dict(), qnet_file)
            
            print(f"[SAVE] 强化学习状态已保存到 {directory}")
            return True
        except Exception as e:
            print(f"[WARN] 保存状态失败: {e}")
            return False
    
    def load_state(self, directory: str) -> bool:
        """
        加载进化状态
        
        Args:
            directory: 加载目录
            
        Returns:
            是否成功
        """
        try:
            # 加载进化状态
            state_file = os.path.join(directory, "evolution_state.json")
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                self.evolution_state.update(saved_state)
            
            # 加载经验回放
            buffer_file = os.path.join(directory, "experience_buffer.json")
            if os.path.exists(buffer_file):
                self.replay_buffer.load(buffer_file)
            
            # 加载Q网络
            if self.q_network.use_torch:
                qnet_file = os.path.join(directory, "q_network.pth")
                if os.path.exists(qnet_file):
                    self.q_network.model.load_state_dict(torch.load(qnet_file))
                    self.target_network.model.load_state_dict(self.q_network.model.state_dict())
            
            print(f"📥 强化学习状态已从 {directory} 加载")
            return True
        except Exception as e:
            print(f"[WARN] 加载状态失败: {e}")
            return False


# 导出接口
__all__ = ["Interaction", "ReplayBuffer", "QNetwork", "SelfEvolutionRL"]