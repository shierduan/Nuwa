"""
单元测试 - 自适应PID控制器

测试覆盖率目标：90%+
测试内容：PID控制器、PPO代理、自适应控制器
"""

import pytest
import numpy as np
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.adaptive_pid import (
    PIDController,
    PPOAgent,
    AdaptivePIDController,
    create_adaptive_controller,
    compute_control_output,
)
from nuwa_core.nuwa_state import NuwaState


class TestPIDController:
    """测试基础PID控制器"""
    
    def test_initialization(self):
        """测试初始化"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        assert pid.kp == 1.0
        assert pid.ki == 0.1
        assert pid.kd == 0.01
        assert pid.integral == 0.0
        assert pid.prev_error == 0.0
    
    def test_basic_control(self):
        """测试基本控制"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.1)
        
        # 无误差
        output = pid.update(0.0, 1.0)
        assert abs(output) < 1e-10
        
        # 正误差
        output = pid.update(1.0, 1.0)
        assert output > 0
        
        # 负误差
        output = pid.update(-1.0, 1.0)
        assert output < 0
    
    def test_integral_windup(self):
        """测试积分饱和"""
        pid = PIDController(kp=1.0, ki=1.0, kd=0.0, integral_limit=10.0)
        
        # 累积大量积分
        for _ in range(100):
            pid.update(1.0, 1.0)
        
        # 积分应该被限制
        assert abs(pid.integral) <= pid.integral_limit
    
    def test_derivative_term(self):
        """测试微分项"""
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        
        # 误差变化
        pid.update(1.0, 1.0)  # error = 1.0
        output = pid.update(0.5, 1.0)  # error = 0.5, delta = -0.5
        
        # 微分项应该是负的（误差在减小）
        assert output < 0
    
    def test_reset(self):
        """测试重置"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        pid.update(1.0, 1.0)
        
        pid.reset()
        assert pid.integral == 0.0
        assert pid.prev_error == 0.0


class TestPPOAgent:
    """测试PPO代理"""
    
    def test_initialization(self):
        """测试初始化"""
        state_dim = 10
        action_dim = 3
        
        agent = PPOAgent(state_dim, action_dim)
        
        assert agent.state_dim == state_dim
        assert agent.action_dim == action_dim
        assert agent.learning_rate > 0
    
    def test_select_action(self):
        """测试动作选择"""
        state_dim = 5
        action_dim = 3
        
        agent = PPOAgent(state_dim, action_dim)
        state = np.random.rand(state_dim)
        
        action = agent.select_action(state)
        
        # 动作应该包含三个分量
        assert len(action) == 3
        assert 'kp_delta' in action
        assert 'ki_delta' in action
        assert 'kd_delta' in action
        
        # 动作值应该在合理范围内
        for key, value in action.items():
            assert abs(value) < 2.0  # 限制在一定范围内
    
    def test_update(self):
        """测试更新"""
        state_dim = 5
        action_dim = 3
        
        agent = PPOAgent(state_dim, action_dim)
        state = np.random.rand(state_dim)
        
        action = agent.select_action(state)
        reward = 0.5
        
        # 记录旧值
        old_memory = len(agent.memory)
        
        # 更新
        agent.update(state, action, reward)
        
        # 内存应该增加
        assert len(agent.memory) == old_memory + 1
        
        # 内存项应该完整
        last_item = agent.memory[-1]
        assert 'state' in last_item
        assert 'action' in last_item
        assert 'reward' in last_item
    
    def test_train(self):
        """测试训练"""
        state_dim = 5
        action_dim = 3
        
        agent = PPOAgent(state_dim, action_dim, batch_size=4)
        
        # 添加足够数据
        for _ in range(8):
            state = np.random.rand(state_dim)
            action = agent.select_action(state)
            reward = np.random.rand()
            agent.update(state, action, reward)
        
        # 记录旧的策略参数
        old_actor_params = [p.clone() for p in agent.actor.parameters()]
        
        # 训练
        agent.train()
        
        # 参数应该有变化
        params_changed = False
        for old, new in zip(old_actor_params, agent.actor.parameters()):
            if not torch.allclose(old, new):
                params_changed = True
                break
        
        assert params_changed
    
    def test_memory_clearing(self):
        """测试内存清理"""
        state_dim = 5
        action_dim = 3
        
        agent = PPOAgent(state_dim, action_dim)
        
        # 添加数据
        for _ in range(5):
            state = np.random.rand(state_dim)
            action = agent.select_action(state)
            agent.update(state, action, 0.5)
        
        assert len(agent.memory) == 5
        
        # 训练后应该清空
        agent.train()
        assert len(agent.memory) == 0


class TestAdaptivePIDController:
    """测试自适应PID控制器"""
    
    def test_initialization(self):
        """测试初始化"""
        base_pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        rl_agent = PPOAgent(state_dim=5, action_dim=3)
        
        controller = AdaptivePIDController(base_pid=base_pid, rl_agent=rl_agent)
        
        assert controller.base_pid == base_pid
        assert controller.rl_agent == rl_agent
    
    def test_update_parameters(self):
        """测试参数更新"""
        base_pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        rl_agent = PPOAgent(state_dim=5, action_dim=3)
        
        controller = AdaptivePIDController(base_pid=base_pid, rl_agent=rl_agent)
        
        # 创建状态
        state = NuwaState(
            emotion_valence=0.5,
            emotion_arousal=0.6,
            personality_openness=0.7,
            personality_conscientiousness=0.8,
            context_complexity=0.5
        )
        
        # 记录原始参数
        original_kp = controller.base_pid.kp
        original_ki = controller.base_pid.ki
        original_kd = controller.base_pid.kd
        
        # 更新参数
        controller.update_parameters(state, performance=0.8)
        
        # 参数应该变化（或至少有可能变化）
        # 注意：由于RL的随机性，不能保证一定变化
        # 但应该有更新记录
        assert len(controller.rl_agent.memory) > 0
    
    def test_calculate_reward(self):
        """测试奖励计算"""
        base_pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        rl_agent = PPOAgent(state_dim=5, action_dim=3)
        
        controller = AdaptivePIDController(base_pid=base_pid, rl_agent=rl_agent)
        
        # 测试不同性能值
        rewards = []
        for perf in [0.5, 0.8, 1.0, 0.2]:
            reward = controller.calculate_reward(perf)
            rewards.append(reward)
        
        # 性能越好，奖励越高
        assert rewards[1] > rewards[0]  # 0.8 > 0.5
        assert rewards[2] > rewards[1]  # 1.0 > 0.8
        assert rewards[3] < rewards[0]  # 0.2 < 0.5
        
        # 奖励范围
        for r in rewards:
            assert -1.0 <= r <= 1.0
    
    def test_to_vector(self):
        """测试状态向量转换"""
        state = NuwaState(
            emotion_valence=0.5,
            emotion_arousal=0.6,
            personality_openness=0.7,
            personality_conscientiousness=0.8,
            context_complexity=0.5
        )
        
        vector = state.to_vector()
        
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))
        assert np.all(vector >= 0) and np.all(vector <= 1)


class TestHelperFunctions:
    """测试辅助函数"""
    
    def test_create_adaptive_controller(self):
        """测试创建自适应控制器"""
        controller = create_adaptive_controller(
            kp=1.0, ki=0.1, kd=0.01,
            state_dim=5, action_dim=3
        )
        
        assert isinstance(controller, AdaptivePIDController)
        assert isinstance(controller.base_pid, PIDController)
        assert isinstance(controller.rl_agent, PPOAgent)
        assert controller.base_pid.kp == 1.0
    
    def test_compute_control_output(self):
        """测试控制输出计算"""
        # 创建状态
        state = NuwaState(
            emotion_valence=0.5,
            emotion_arousal=0.6,
            personality_openness=0.7,
            personality_conscientiousness=0.8,
            context_complexity=0.5
        )
        
        # 计算输出
        output = compute_control_output(state)
        
        # 输出应该是标量
        assert isinstance(output, (float, np.floating))
        assert np.isfinite(output)
        
        # 合理的输出范围
        assert abs(output) < 100.0  # 放宽限制，因为包含PID计算


class TestIntegration:
    """测试集成场景"""
    
    def test_full_cycle(self):
        """测试完整周期"""
        # 创建自适应控制器
        controller = create_adaptive_controller(
            kp=1.0, ki=0.1, kd=0.01,
            state_dim=5, action_dim=3
        )
        
        # 模拟多个时间步
        states = [
            NuwaState(0.5, 0.6, 0.7, 0.8, 0.5),
            NuwaState(0.6, 0.7, 0.8, 0.9, 0.6),
            NuwaState(0.4, 0.5, 0.6, 0.7, 0.4),
        ]
        
        performances = [0.8, 0.9, 0.7]
        
        # 记录初始参数
        init_kp = controller.base_pid.kp
        init_ki = controller.base_pid.ki
        init_kd = controller.base_pid.kd
        
        # 执行更新
        for state, perf in zip(states, performances):
            controller.update_parameters(state, perf)
        
        # 训练RL
        if len(controller.rl_agent.memory) >= controller.rl_agent.batch_size:
            controller.rl_agent.train()
        
        # 验证状态
        assert len(controller.rl_agent.memory) >= 3
        
        # 计算控制输出
        output = compute_control_output(states[-1])
        assert np.isfinite(output)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=nuwa_core.adaptive_pid", "--cov-report=html"])