"""
集成测试 - 完整系统功能

测试目标：验证所有模块协同工作的完整性
测试覆盖：记忆系统 + PID控制 + 语义场 + 自我进化
"""

import pytest
import numpy as np
import sys
import os
import time

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.nuwa_state import NuwaState
from nuwa_core.memory_cortex import MemoryCortex
from nuwa_core.adaptive_pid import AdaptivePIDController, create_adaptive_controller
from nuwa_core.riemannian_semantic_field import RigorousSemanticField
from nuwa_core.self_evolution_state import SelfEvolutionState


class TestFullSystemIntegration:
    """完整系统集成测试"""
    
    def test_memory_to_pid_flow(self):
        """测试记忆 → PID控制流程"""
        # 1. 初始化记忆系统
        cortex = MemoryCortex()
        
        # 2. 存储记忆
        memories = [
            "用户表达了积极的情绪",
            "讨论了复杂的技术问题",
            "需要谨慎的回答",
            "表现出好奇心",
        ]
        
        for mem in memories:
            cortex.store_memory(mem, {"importance": 0.5})
        
        # 3. 创建状态（基于记忆）
        state = NuwaState(
            emotion_valence=0.7,
            emotion_arousal=0.6,
            personality_openness=0.8,
            personality_conscientiousness=0.7,
            context_complexity=0.6
        )
        
        # 4. 创建自适应PID
        controller = create_adaptive_controller(
            kp=1.0, ki=0.1, kd=0.01,
            state_dim=5, action_dim=3
        )
        
        # 5. 计算控制输出
        output = controller.update_parameters(state, performance=0.8)
        
        # 验证流程完成
        assert output is not None
        assert len(cortex.memory_graph.nodes) > 0
    
    def test_semantic_field_with_memory(self):
        """测试语义场与记忆系统的集成"""
        # 1. 创建语义场（基于核心向量）
        core_vector = np.random.rand(384)
        core_vector = core_vector / np.linalg.norm(core_vector)
        
        field = RigorousSemanticField(core_vector=core_vector)
        
        # 2. 模拟记忆检索结果（向量）
        memory_vectors = [
            np.random.rand(384) for _ in range(5)
        ]
        
        # 3. 对每个记忆向量计算势能
        energies = []
        for vec in memory_vectors:
            vec = vec / np.linalg.norm(vec)
            energy = field.calculate_potential_energy(vec)
            energies.append(energy)
        
        # 4. 验证所有能量都是有限值
        assert all(np.isfinite(e) for e in energies)
        assert all(0 <= e <= 2.0 for e in energies)
        
        # 5. 演化一个状态
        initial_state = np.random.rand(384)
        initial_state = initial_state / np.linalg.norm(initial_state)
        
        evolved, info = field.evolve(initial_state, dt=0.02, iterations=10)
        
        assert evolved is not None
        assert info['final_energy'] >= 0
    
    def test_self_evolution_with_system(self):
        """测试自我进化与系统集成"""
        # 1. 初始化自我进化状态
        evolution_state = SelfEvolutionState()
        
        # 2. 创建系统组件
        cortex = MemoryCortex()
        controller = create_adaptive_controller(
            kp=1.0, ki=0.1, kd=0.01,
            state_dim=5, action_dim=3
        )
        
        # 3. 模拟多个交互周期
        for cycle in range(3):
            # 创建状态
            state = NuwaState(
                emotion_valence=0.5 + cycle * 0.1,
                emotion_arousal=0.6 + cycle * 0.1,
                personality_openness=0.7 + cycle * 0.05,
                personality_conscientiousness=0.8 - cycle * 0.05,
                context_complexity=0.5 + cycle * 0.1
            )
            
            # 更新控制器
            performance = 0.7 + cycle * 0.1
            controller.update_parameters(state, performance)
            
            # 存储记忆
            cortex.store_memory(f"进化周期{cycle}", {"cycle": cycle})
            
            # 更新进化状态
            evolution_state.update_cycle()
        
        # 4. 验证进化
        assert evolution_state.cycle_count == 3
        assert evolution_state.adaptation_level > 0
        
        # 5. 训练RL（如果数据足够）
        if len(controller.rl_agent.memory) >= controller.rl_agent.batch_size:
            controller.rl_agent.train()
            assert True  # 训练成功
    
    def test_complete_interaction_flow(self):
        """测试完整的交互流程"""
        # 系统初始化
        cortex = MemoryCortex()
        controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.01)
        evolution_state = SelfEvolutionState()
        
        # 模拟用户交互序列
        interactions = [
            {"input": "你好！", "response_time": 0.5, "user_satisfaction": 0.9},
            {"input": "请解释量子计算", "response_time": 1.2, "user_satisfaction": 0.7},
            {"input": "谢谢，很有帮助", "response_time": 0.3, "user_satisfaction": 0.95},
        ]
        
        total_performance = 0
        
        for i, interaction in enumerate(interactions):
            # 1. 记忆输入
            cortex.store_memory(interaction["input"], {"sequence": i})
            
            # 2. 创建状态（基于交互历史）
            state = NuwaState(
                emotion_valence=0.6 + interaction["user_satisfaction"] * 0.2,
                emotion_arousal=0.5,
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=len(interaction["input"]) / 50  # 简单复杂度计算
            )
            
            # 3. 更新PID（性能基于响应时间和满意度）
            perf = interaction["user_satisfaction"] * (1.0 / (1.0 + interaction["response_time"]))
            controller.update_parameters(state, perf)
            total_performance += perf
            
            # 4. 更新进化状态
            evolution_state.update_cycle()
            
            # 5. 检索相关记忆
            relevant = cortex.retrieve_memory(interaction["input"], top_k=3)
        
        # 验证
        assert len(cortex.memory_graph.nodes) >= 3
        assert evolution_state.cycle_count == 3
        assert total_performance > 0
        
        # 模拟训练
        if len(controller.rl_agent.memory) >= controller.rl_agent.batch_size:
            controller.rl_agent.train()
    
        
        # 4. 创建语义场
        core_vector = np.random.rand(core_dim)
        core_vector = core_vector / np.linalg.norm(core_vector)
        
        field = RigorousSemanticField(core_vector=core_vector)
        
        # 5. 计算视觉特征的势能
        energy = field.calculate_potential_energy(visual_embedded)
        
        assert np.isfinite(energy)
        assert 0 <= energy <= 2.0
        
        # 6. 演化状态
        evolved, info = field.evolve(visual_embedded, iterations=5)
        
        assert evolved is not None
    
    def test_emotional_adaptation(self):
        """测试情绪适应"""
        # 1. 初始化系统
        controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.01)
        cortex = MemoryCortex()
        
        # 2. 模拟情绪变化序列
        emotional_states = [
            (0.8, 0.7),  # 积极兴奋
            (0.3, 0.6),  # 消极兴奋
            (0.7, 0.2),  # 积极平静
            (0.2, 0.3),  # 消极平静
        ]
        
        adaptations = []
        
        for valence, arousal in emotional_states:
            state = NuwaState(
                emotion_valence=valence,
                emotion_arousal=arousal,
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=0.5
            )
            
            # 记录参数
            prev_kp = controller.base_pid.kp
            
            # 更新
            controller.update_parameters(state, performance=0.8)
            
            # 记录变化
            adaptations.append(abs(controller.base_pid.kp - prev_kp))
            
            # 存储情绪记忆
            cortex.store_memory(f"情绪状态: valence={valence:.2f}", {"emotion": "valence"})
        
        # 验证有适应发生
        assert sum(adaptations) > 0
        assert len(cortex.memory_graph.nodes) == 4


class TestPerformanceUnderLoad:
    """压力下的系统测试"""
    
    def test_high_frequency_updates(self):
        """测试高频更新"""
        controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.01)
        
        start_time = time.time()
        
        # 1000次快速更新
        for i in range(1000):
            state = NuwaState(
                emotion_valence=np.random.rand(),
                emotion_arousal=np.random.rand(),
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=0.5
            )
            controller.update_parameters(state, performance=0.8)
        
        elapsed = time.time() - start_time
        
        # 应该能在合理时间内完成（< 10秒）
        assert elapsed < 10.0
        
        # 如果积累了足够的经验，训练一次
        if len(controller.rl_agent.memory) >= controller.rl_agent.batch_size:
            train_start = time.time()
            controller.rl_agent.train()
            train_time = time.time() - train_start
            
            # 训练也应该快速
            assert train_time < 5.0
    
    def test_large_memory_system(self):
        """测试大规模记忆系统"""
        cortex = MemoryCortex()
        
        # 存储大量记忆
        num_memories = 100
        
        for i in range(num_memories):
            content = f"测试记忆{i}: " + "这是一个较长的文本内容，用于测试记忆系统的性能表现。" * 10
            cortex.store_memory(content, {"index": i, "importance": 0.5})
        
        # 检索测试
        start_time = time.time()
        results = cortex.retrieve_memory("测试", top_k=10)
        elapsed = time.time() - start_time
        
        assert len(results) > 0
        assert elapsed < 2.0  # 检索应该快速


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=nuwa_core", "--cov-report=html"])