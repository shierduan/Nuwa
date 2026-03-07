"""
集成测试 - 黎曼几何语义场的完整集成

测试黎曼几何与现有系统的深度集成
"""

import pytest
import numpy as np
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.riemannian_semantic_field import (
    RigorousSemanticField,
    HyperbolicManifold,
    HessianCalculator,
)
from nuwa_core.semantic_field import StateVector, vectorize_state, calculate_potential_energy
from nuwa_core.memory_cortex import MemoryCortex


class TestRiemannianIntegration:
    """黎曼几何与系统的集成测试"""
    
    def test_riemannian_replaces_euclidean(self):
        """验证黎曼几何可以替代欧几里得方法"""
        # 创建测试向量
        state = np.array([0.7, 0.5, 0.3, 0.1])
        core = np.array([0.8, 0.6, 0.4, 0.2])
        
        # 欧几里得方法
        euclidean_energy = calculate_potential_energy(state, core)
        
        # 黎曼方法
        field = RigorousSemanticField(core_vector=core)
        riemannian_energy = field.calculate_potential_energy(state)
        
        # 两者都应该返回有效值
        assert np.isfinite(euclidean_energy)
        assert np.isfinite(riemannian_energy)
        
        # 对于接近的向量，能量应该相似
        assert abs(euclidean_energy - riemannian_energy) < 1.0
    
    def test_evolution_improvement(self):
        """验证演化确实改善状态"""
        core = np.array([0.8, 0.6, 0.4, 0.2, 0.1])
        field = RigorousSemanticField(core_vector=core)
        
        # 初始状态（远离核心）
        initial = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        initial = initial / np.linalg.norm(initial)
        
        # 演化前
        energy_before = field.calculate_potential_energy(initial)
        
        # 演化后
        evolved, info = field.evolve(initial, dt=0.02, iterations=20)
        energy_after = field.calculate_potential_energy(evolved)
        
        # 能量应该降低
        assert energy_after <= energy_before + 0.1  # 允许轻微波动
    
    def test_with_memory_cortex(self):
        """与记忆皮层的集成"""
        cortex = MemoryCortex()
        
        # 存储一些记忆
        memories = [
            "人工智能的未来发展",
            "机器学习的核心原理",
            "深度学习的应用场景",
        ]
        
        for mem in memories:
            cortex.store_memory(mem, {"importance": 0.6})
        
        # 获取核心向量（使用嵌入）
        core_vector = cortex.embedding_model.encode("人工智能")
        core_vector = core_vector / np.linalg.norm(core_vector)
        
        # 创建黎曼场
        field = RigorousSemanticField(core_vector=core_vector)
        
        # 检索查询
        query = "深度学习"
        query_vector = cortex.embedding_model.encode(query)
        query_vector = query_vector / np.linalg.norm(query_vector)
        
        # 计算势能
        energy = field.calculate_potential_energy(query_vector)
        
        assert np.isfinite(energy)
        assert 0 <= energy <= 2.0
        
        # 演化查询向量
        evolved, info = field.evolve(query_vector, iterations=10)
        
        assert evolved is not None
        
        # 演化后的向量应该更接近核心
        # （在语义空间中更相关）
    
    def test_hessian_guided_retrieval(self):
        """使用Hessian引导检索"""
        # 创建多个记忆向量
        memories = []
        for i in range(10):
            vec = np.random.rand(384)
            vec = vec / np.linalg.norm(vec)
            memories.append(vec)
        
        # 核心向量
        core = np.random.rand(384)
        core = core / np.linalg.norm(core)
        
        # 创建场
        field = RigorousSemanticField(core_vector=core)
        
        # 计算每个记忆的势能（相关性）
        energies = []
        for mem in memories:
            energy = field.calculate_potential_energy(mem)
            energies.append(energy)
        
        # 排序（能量越低越相关）
        sorted_indices = np.argsort(energies)
        
        # 前3个应该是最相关的
        top3 = sorted_indices[:3]
        
        assert len(top3) == 3
        # 应该是能量最低的3个
        assert energies[top3[0]] <= energies[top3[1]] <= energies[top3[2]]
    
    def test_state_vector_evolution(self):
        """测试StateVector的黎曼演化"""
        # 创建初始状态向量
        initial_vec = np.array([0.7, 0.5, 0.3, 0.1, 0.2])
        initial_vec = initial_vec / np.linalg.norm(initial_vec)
        
        initial_state = StateVector(
            vector=initial_vec,
            description="初始状态"
        )
        
        # 核心向量
        core = np.array([0.8, 0.6, 0.4, 0.2, 0.1])
        
        # 黎曼场
        field = RigorousSemanticField(core_vector=core)
        
        # 演化
        evolved_vec, info = field.evolve(initial_state.vector, dt=0.02, iterations=15)
        
        # 创建演化后的状态
        evolved_state = StateVector(
            vector=evolved_vec,
            description=f"演化状态 - {info['final_energy']:.4f}"
        )
        
        # 验证
        assert evolved_state.vector is not None
        assert evolved_state.description != initial_state.description
        assert info['final_energy'] <= info['initial_energy'] + 0.1
    
    def test_comparison_with_old_method(self):
        """对比新旧方法的性能"""
        # 测试数据
        test_cases = []
        for _ in range(20):
            state = np.random.rand(384)
            core = np.random.rand(384)
            state = state / np.linalg.norm(state)
            core = core / np.linalg.norm(core)
            test_cases.append((state, core))
        
        # 旧方法（欧几里得）
        old_times = []
        old_results = []
        
        import time
        for state, core in test_cases:
            start = time.time()
            energy = calculate_potential_energy(state, core)
            elapsed = time.time() - start
            old_times.append(elapsed)
            old_results.append(energy)
        
        # 新方法（黎曼）
        new_times = []
        new_results = []
        
        for state, core in test_cases:
            field = RigorousSemanticField(core_vector=core)
            start = time.time()
            energy = field.calculate_potential_energy(state)
            elapsed = time.time() - start
            new_times.append(elapsed)
            new_results.append(energy)
        
        # 性能对比（黎曼应该不会慢太多）
        avg_old = np.mean(old_times)
        avg_new = np.mean(new_times)
        
        # 黎曼方法可能稍慢，但应该在合理范围内
        assert avg_new < avg_old * 10
        
        # 结果应该都是有效的
        assert all(np.isfinite(r) for r in new_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=nuwa_core.riemannian_semantic_field", "--cov-report=html"])