"""
单元测试 - 语义场论核心模块

测试覆盖率目标：90%+
测试内容：黎曼几何语义场的核心功能
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
    HyperbolicManifold,
    HessianCalculator,
    RigorousSemanticField,
    normalize_vector,
    cosine_similarity_smooth,
    verify_stability,
    calculate_potential_energy,
    calculate_gradient,
)
from nuwa_core.semantic_field import StateVector


class TestHyperbolicManifold:
    """测试双曲流形"""
    
    def test_initialization(self):
        """测试初始化"""
        manifold = HyperbolicManifold(curvature=-1.0)
        assert manifold.curvature == -1.0
    
    def test_project_tangent_basic(self):
        """测试基本的切空间投影"""
        manifold = HyperbolicManifold()
        point = np.array([1.0, 0.0, 0.0])
        reference = np.array([0.0, 1.0, 0.0])
        
        tangent = manifold.project_tangent(point, reference)
        
        # 投影应该与参考正交
        assert np.dot(tangent, reference) < 1e-10
        # 投影长度应该合理
        assert np.linalg.norm(tangent) <= 1.0
    
    def test_project_tangent_parallel(self):
        """测试平行向量的投影"""
        manifold = HyperbolicManifold()
        point = np.array([1.0, 0.0, 0.0])
        reference = np.array([1.0, 0.0, 0.0])
        
        tangent = manifold.project_tangent(point, reference)
        
        # 平行向量投影应为零
        assert np.linalg.norm(tangent) < 1e-10
    
    def test_exponential_map(self):
        """测试指数映射"""
        manifold = HyperbolicManifold()
        base = np.array([1.0, 0.0, 0.0])
        tangent = np.array([0.0, 0.3, 0.0])
        
        result = manifold.exponential_map(base, tangent)
        
        # 结果应该在单位球面上
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6
        # 结果应该是有限值
        assert np.all(np.isfinite(result))
    
    def test_edge_cases(self):
        """测试边界情况"""
        manifold = HyperbolicManifold()
        
        # 零向量
        zero = np.zeros(3)
        result = manifold.project_tangent(zero, zero)
        assert np.allclose(result, zero)
        
        # 极长向量（应被截断）
        large = np.array([100.0, 200.0, 300.0])
        ref = np.array([1.0, 0.0, 0.0])
        tangent = manifold.project_tangent(large, ref)
        assert np.linalg.norm(tangent) <= 1.0


class TestHessianCalculator:
    """测试Hessian计算器"""
    
    def test_initialization(self):
        """测试初始化"""
        hessian = HessianCalculator(epsilon=1e-5, regularization=1e-6)
        assert hessian.epsilon == 1e-5
        assert hessian.regularization == 1e-6
    
    def test_compute_basic(self):
        """测试基本的Hessian计算"""
        hessian = HessianCalculator()
        state = np.array([0.8, 0.6, 0.4])
        core = np.array([0.7, 0.7, 0.7])
        
        H = hessian.compute(state, core)
        
        # 形状正确
        assert H.shape == (3, 3)
        # 对称
        assert np.allclose(H, H.T)
        # 正定（所有特征值>0）
        eigenvalues = np.linalg.eigvals(H)
        assert np.all(eigenvalues > 0)
    
    def test_compute_stability(self):
        """测试数值稳定性"""
        hessian = HessianCalculator()
        
        # 测试各种输入
        test_cases = [
            np.array([0.0, 0.0, 0.0]),  # 零向量
            np.array([1e-10, 1e-10, 1e-10]),  # 极小向量
            np.array([np.nan, 0.6, 0.4]),  # NaN
            np.array([np.inf, 0.6, 0.4]),  # Inf
        ]
        
        for state in test_cases:
            core = np.array([0.7, 0.7, 0.7])
            H = hessian.compute(state, core)
            
            # 应该返回有限值
            assert np.all(np.isfinite(H))
            # 应该是对称的
            assert np.allclose(H, H.T)
    
    def test_regularization(self):
        """测试正则化效果"""
        hessian = HessianCalculator(regularization=1e-4)
        state = np.array([0.8, 0.6, 0.4])
        core = np.array([0.7, 0.7, 0.7])
        
        H = hessian.compute(state, core)
        
        # 特征值应该有下界
        eigenvalues = np.linalg.eigvals(H)
        assert np.min(eigenvalues) >= 1e-4 * 100 * (3/100)  # 考虑维度缩放


class TestRigorousSemanticField:
    """测试严格语义场"""
    
    def test_initialization(self):
        """测试初始化"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        assert field.core_vector is not None
        assert field.manifold is not None
        assert field.hessian is not None
    
    def test_potential_energy(self):
        """测试势能计算"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        # 相同向量：能量应为0
        energy_same = field.calculate_potential_energy(core)
        assert abs(energy_same) < 1e-10
        
        # 正交向量：能量应较大
        orth = np.array([0.0, 0.0, 0.0, 1.0])
        orth = orth / np.linalg.norm(orth)
        energy_orth = field.calculate_potential_energy(orth)
        assert energy_orth > 0.5
        
        # 相似向量：能量应较小
        similar = np.array([0.75, 0.65, 0.35, 0.25])
        similar = similar / np.linalg.norm(similar)
        energy_sim = field.calculate_potential_energy(similar)
        assert 0 < energy_sim < 0.1
    
    def test_potential_energy_stability(self):
        """测试势能的数值稳定性"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        # 边界情况
        test_cases = [
            np.array([0.0, 0.0, 0.0, 0.0]),
            np.array([1e-12, 1e-12, 1e-12, 1e-12]),
            np.array([np.nan, 0.6, 0.4, 0.2]),
            np.array([np.inf, 0.6, 0.4, 0.2]),
        ]
        
        for state in test_cases:
            energy = field.calculate_potential_energy(state)
            assert np.isfinite(energy)
            assert 0 <= energy <= 2.0
    
    def test_riemannian_gradient(self):
        """测试黎曼梯度计算"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        state = np.array([0.7, 0.5, 0.3, 0.1])
        gradient = field.compute_riemannian_gradient(state)
        
        # 维度正确
        assert gradient.shape == state.shape
        # 有限值
        assert np.all(np.isfinite(gradient))
        # 不为零（除非在核心）
        assert np.linalg.norm(gradient) > 0
    
    def test_gradient_stability(self):
        """测试梯度的数值稳定性"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        # 边界情况
        test_cases = [
            np.array([0.0, 0.0, 0.0, 0.0]),
            np.array([1e-12, 1e-12, 1e-12, 1e-12]),
            np.array([np.nan, 0.6, 0.4, 0.2]),
            np.array([np.inf, 0.6, 0.4, 0.2]),
        ]
        
        for state in test_cases:
            gradient = field.compute_riemannian_gradient(state)
            assert np.all(np.isfinite(gradient))
            assert np.linalg.norm(gradient) < 100.0
    
    def test_evolution(self):
        """测试演化过程"""
        core = np.array([0.8, 0.6, 0.4, 0.2, 0.1])
        field = RigorousSemanticField(core_vector=core)
        
        # 初始状态
        initial = np.array([0.5, 0.8, 0.2, 0.6, 0.3])
        initial = initial / np.linalg.norm(initial)
        
        # 演化
        evolved, info = field.evolve(initial, dt=0.02, iterations=20)
        
        # 结果验证
        assert evolved is not None
        assert np.all(np.isfinite(evolved))
        assert abs(np.linalg.norm(evolved) - 1.0) < 1e-6
        
        # 信息验证
        assert info['iterations'] > 0
        assert info['initial_energy'] >= 0
        assert info['final_energy'] >= 0
        assert len(info['energy_history']) > 0
    
    def test_evolution_convergence(self):
        """测试演化收敛性"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        # 从不同初始状态开始
        initial_states = [
            np.array([0.5, 0.8, 0.2, 0.6]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.7, 0.5, 0.3, 0.1]),
        ]
        
        for initial in initial_states:
            initial = initial / np.linalg.norm(initial)
            evolved, info = field.evolve(initial, dt=0.02, iterations=30)
            
            # 最终能量应该降低或保持低位
            final_energy = info['final_energy']
            assert final_energy <= 1.0
            
            # 演化后应该更接近核心
            from nuwa_core.riemannian_semantic_field import cosine_similarity_smooth
            sim_initial = cosine_similarity_smooth(initial, core)
            sim_final = cosine_similarity_smooth(evolved, core)
            
            # 允许略有退化，但不应该差太多
            assert sim_final >= sim_initial - 0.1


class TestCompatibilityFunctions:
    """测试兼容性函数"""
    
    def test_calculate_potential_energy(self):
        """测试兼容性势能函数"""
        state = np.array([0.7, 0.5, 0.3, 0.1])
        core = np.array([0.8, 0.6, 0.4, 0.2])
        
        energy = calculate_potential_energy(state, core)
        
        assert np.isfinite(energy)
        assert 0 <= energy <= 2.0
    
    def test_calculate_gradient(self):
        """测试兼容性梯度函数"""
        state = np.array([0.7, 0.5, 0.3, 0.1])
        core = np.array([0.8, 0.6, 0.4, 0.2])
        
        gradient = calculate_gradient(state, core)
        
        assert gradient.shape == state.shape
        assert np.all(np.isfinite(gradient))
    
    def test_calculate_gradient_with_epsilon(self):
        """测试带epsilon的梯度计算"""
        state = np.array([0.7, 0.5, 0.3, 0.1])
        core = np.array([0.8, 0.6, 0.4, 0.2])
        
        gradient1 = calculate_gradient(state, core, epsilon=1e-5)
        gradient2 = calculate_gradient(state, core, epsilon=1e-6)
        
        # 应该返回黎曼梯度（非零）
        assert np.linalg.norm(gradient1) > 0
        assert np.linalg.norm(gradient2) > 0


class TestAuxiliaryFunctions:
    """测试辅助函数"""
    
    def test_normalize_vector(self):
        """测试向量归一化"""
        vec = np.array([3.0, 4.0, 0.0])
        normalized = normalize_vector(vec)
        
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-10
        
        # 零向量
        zero = np.zeros(3)
        result = normalize_vector(zero)
        assert np.allclose(result, zero)
    
    def test_cosine_similarity_smooth(self):
        """测试平滑余弦相似度"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        
        sim = cosine_similarity_smooth(vec1, vec2)
        assert abs(sim) < 1e-10
        
        # 相同向量
        sim_same = cosine_similarity_smooth(vec1, vec1)
        assert abs(sim_same - 1.0) < 1e-10
        
        # 边界情况
        zero = np.zeros(3)
        sim_zero = cosine_similarity_smooth(vec1, zero)
        assert sim_zero == 0.0
    
    def test_verify_stability(self):
        """测试稳定性验证"""
        state = np.array([0.7, 0.5, 0.3, 0.1])
        core = np.array([0.8, 0.6, 0.4, 0.2])
        
        results = verify_stability(state, core)
        
        # 所有检查都应该通过
        assert results["zero_vector"]
        assert results["range_check"]
        assert results["energy_stable"]
        assert results["gradient_stable"]
        
        # 测试不稳定情况
        unstable_state = np.array([0.0, 0.0, 0.0, 0.0])
        results_unstable = verify_stability(unstable_state, core)
        
        # 零向量检查应失败
        assert not results_unstable["zero_vector"]


class TestStateVectorIntegration:
    """测试与StateVector的集成"""
    
    def test_state_vector_with_evolution(self):
        """测试StateVector与演化的集成"""
        core = np.array([0.8, 0.6, 0.4, 0.2])
        field = RigorousSemanticField(core_vector=core)
        
        initial = np.array([0.7, 0.5, 0.3, 0.1])
        evolved, info = field.evolve(initial, dt=0.02, iterations=10)
        
        # 创建StateVector
        state_vec = StateVector(
            vector=evolved,
            description="演化后的状态"
        )
        
        assert state_vec.vector is not None
        assert state_vec.description == "演化后的状态"
        assert np.all(np.isfinite(state_vec.vector))


class TestErrorHandling:
    """测试错误处理"""
    
    def test_missing_core_vector(self):
        """测试缺少核心向量的情况"""
        field = RigorousSemanticField(core_vector=None)
        state = np.array([0.7, 0.5, 0.3, 0.1])
        
        with pytest.raises(ValueError):
            field.calculate_potential_energy(state)
    
    def test_dimension_mismatch(self):
        """测试维度不匹配"""
        core = np.array([0.8, 0.6, 0.4])
        field = RigorousSemanticField(core_vector=core)
        
        # 不同维度的状态
        state = np.array([0.7, 0.5, 0.3, 0.1, 0.2])
        
        # 应该能够处理（自动截断）
        energy = field.calculate_potential_energy(state)
        assert np.isfinite(energy)
        
        gradient = field.compute_riemannian_gradient(state)
        assert gradient.shape == (3,)  # 截断到核心维度


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=nuwa_core.riemannian_semantic_field", "--cov-report=html"])