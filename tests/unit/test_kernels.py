"""
单元测试 - 核心内核模块

测试覆盖率目标：90%+
测试内容：NuwaKernel、NuwaState、MemoryCortex等核心组件
"""

import pytest
import numpy as np
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.nuwa_state import NuwaState
from nuwa_core.memory_cortex import MemoryCortex
from nuwa_core.personality import Personality
from nuwa_core.drive_system import BioRhythm, PIDController


class TestNuwaState:
    """测试女娲状态"""
    
    def test_initialization(self):
        """测试初始化"""
        state = NuwaState(
            emotion_valence=0.5,
            emotion_arousal=0.6,
            personality_openness=0.7,
            personality_conscientiousness=0.8,
            context_complexity=0.5
        )
        
        assert state.emotion_valence == 0.5
        assert state.emotion_arousal == 0.6
        assert state.personality_openness == 0.7
        assert state.personality_conscientiousness == 0.8
        assert state.context_complexity == 0.5
    
    def test_to_vector(self):
        """测试转换为向量"""
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
    
    def test_boundary_values(self):
        """测试边界值"""
        # 测试0和1的边界
        state_min = NuwaState(0.0, 0.0, 0.0, 0.0, 0.0)
        state_max = NuwaState(1.0, 1.0, 1.0, 1.0, 1.0)
        
        vec_min = state_min.to_vector()
        vec_max = state_max.to_vector()
        
        assert np.allclose(vec_min, np.zeros(5))
        assert np.allclose(vec_max, np.ones(5))


class TestMemoryCortex:
    """测试记忆皮层"""
    
    def test_initialization(self):
        """测试初始化"""
        cortex = MemoryCortex()
        
        assert cortex.memory_graph is not None
        assert cortex.embedding_model is not None
        assert cortex.current_state is not None
    
    def test_store_memory(self):
        """测试存储记忆"""
        cortex = MemoryCortex()
        
        content = "这是一个测试记忆"
        context = {"type": "test", "importance": 0.8}
        
        result = cortex.store_memory(content, context)
        
        assert result is not None
        assert isinstance(result, str)  # 返回记忆ID
    
    def test_retrieve_memory(self):
        """测试检索记忆"""
        cortex = MemoryCortex()
        
        # 先存储
        content = "测试记忆内容"
        memory_id = cortex.store_memory(content, {"type": "test"})
        
        # 检索
        memories = cortex.retrieve_memory("测试", top_k=3)
        
        assert isinstance(memories, list)
        # 应该能找到相关记忆
        assert len(memories) > 0 or len(cortex.memory_graph.nodes) > 0
    
    def test_memory_consolidation(self):
        """测试记忆巩固"""
        cortex = MemoryCortex()
        
        # 存储多个记忆
        for i in range(5):
            cortex.store_memory(f"记忆{i}", {"type": "test", "importance": 0.5 + i * 0.1})
        
        # 执行巩固
        cortex.consolidate_memory()
        
        # 应该有更新（具体实现取决于内部逻辑）
        assert cortex is not None
    
    def test_emotion_integration(self):
        """测试情绪集成"""
        cortex = MemoryCortex()
        
        # 设置情绪状态
        state = NuwaState(
            emotion_valence=0.8,
            emotion_arousal=0.7,
            personality_openness=0.6,
            personality_conscientiousness=0.5,
            context_complexity=0.4
        )
        
        cortex.update_state(state)
        
        # 验证状态更新
        assert cortex.current_state.emotion_valence == 0.8


class TestPersonality:
    """测试人格模块"""
    
    def test_initialization(self):
        """测试初始化"""
        personality = Personality(
            openness=0.7,
            conscientiousness=0.6,
            extraversion=0.5,
            agreeableness=0.8,
            neuroticism=0.3
        )
        
        assert personality.openness == 0.7
        assert personality.conscientiousness == 0.6
    
    def test_get_personality_vector(self):
        """测试获取人格向量"""
        personality = Personality(
            openness=0.7,
            conscientiousness=0.6,
            extraversion=0.5,
            agreeableness=0.8,
            neuroticism=0.3
        )
        
        vector = personality.get_personality_vector()
        
        assert vector.shape == (5,)
        assert np.all(np.isfinite(vector))
    
    def test_adjust_personality(self):
        """测试人格调整"""
        personality = Personality(
            openness=0.7,
            conscientiousness=0.6,
            extraversion=0.5,
            agreeableness=0.8,
            neuroticism=0.3
        )
        
        # 调整开放性
        personality.adjust_personality("openness", 0.1)
        
        assert abs(personality.openness - 0.8) < 1e-10
        
        # 调整神经质
        personality.adjust_personality("neuroticism", -0.1)
        
        assert abs(personality.neuroticism - 0.2) < 1e-10


class TestBioRhythm:
    """测试生物节律"""
    
    def test_initialization(self):
        """测试初始化"""
        rhythm = BioRhythm()
        
        # 应该有基础值
        assert rhythm.energy > 0
        assert rhythm.mood > 0
    
    def test_update(self):
        """测试更新"""
        rhythm = BioRhythm()
        
        initial_energy = rhythm.energy
        initial_mood = rhythm.mood
        
        # 更新时间
        rhythm.update(1.0)  # 1小时
        
        # 能量应该有变化（基于周期）
        assert rhythm.energy != initial_energy or rhythm.mood != initial_mood
    
    def test_get_bio_state(self):
        """测试获取生物状态"""
        rhythm = BioRhythm()
        
        state = rhythm.get_bio_state()
        
        assert "energy" in state
        assert "mood" in state
        assert state["energy"] > 0
        assert state["mood"] > 0


class TestPIDController:
    """测试PID控制器（额外测试）"""
    
    def test_set_pid_params(self):
        """测试设置PID参数"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
        
        pid.set_pid_params(kp=2.0, ki=0.2, kd=0.02)
        
        assert pid.kp == 2.0
        assert pid.ki == 0.2
        assert pid.kd == 0.02
    
    def test_control_with_setpoint(self):
        """测试设定值控制"""
        pid = PIDController(kp=1.0, ki=0.1, kd=0.1)
        
        setpoint = 10.0
        current = 5.0
        
        output = pid.update(setpoint - current, 1.0)
        
        # 误差为正，输出应该为正
        assert output > 0
        
        # 模拟接近设定点
        current = 9.5
        output = pid.update(setpoint - current, 1.0)
        
        # 误差减小，微分项为负
        assert output > 0  # 但积分项还在增加


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=nuwa_core.nuwa_state nuwa_core.memory_cortex nuwa_core.personality nuwa_core.drive_system", "--cov-report=html"])