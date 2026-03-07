"""
测试工具/Fixtures

提供测试所需的辅助函数和模拟数据
"""

import numpy as np
import sys
import os
from typing import List, Dict, Any, Tuple

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.nuwa_state import NuwaState
from nuwa_core.riemannian_semantic_field import RigorousSemanticField


class MockEmbeddingModel:
    """模拟嵌入模型"""
    
    def __init__(self, dim=384):
        self.dim = dim
    
    def encode(self, text: str) -> np.ndarray:
        """生成基于文本的确定性向量"""
        # 使用哈希生成确定性向量
        hash_val = int.from_bytes(text.encode(), 'little') % (2**32)
        np.random.seed(hash_val % 10000)  # 限制种子范围
        
        vector = np.random.rand(self.dim)
        vector = vector / np.linalg.norm(vector)
        
        return vector


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_state(num: int = 10) -> List[NuwaState]:
        """生成测试状态列表"""
        states = []
        for i in range(num):
            state = NuwaState(
                emotion_valence=np.random.rand(),
                emotion_arousal=np.random.rand(),
                personality_openness=0.6 + np.random.rand() * 0.4,
                personality_conscientiousness=0.6 + np.random.rand() * 0.4,
                context_complexity=np.random.rand()
            )
            states.append(state)
        return states
    
    @staticmethod
    def generate_vector(dim: int = 384, normalized: bool = True) -> np.ndarray:
        """生成测试向量"""
        vec = np.random.rand(dim)
        if normalized:
            vec = vec / np.linalg.norm(vec)
        return vec
    
    @staticmethod
    def generate_memory_data(num: int = 20) -> List[Dict[str, Any]]:
        """生成测试记忆数据"""
        memories = []
        templates = [
            "用户询问了关于{}的问题",
            "讨论了{}的技术细节",
            "表达了对{}的兴趣",
            "请求关于{}的帮助",
            "分享了{}的经验",
        ]
        topics = ["AI", "编程", "数学", "物理", "心理学", "哲学", "艺术", "科学"]
        
        for i in range(num):
            template = templates[i % len(templates)]
            topic = topics[i % len(topics)]
            content = template.format(topic)
            
            memories.append({
                "content": content,
                "context": {
                    "importance": np.random.rand(),
                    "timestamp": i,
                    "type": "user_interaction"
                }
            })
        
        return memories
    
    @staticmethod
    def generate_interactions(num: int = 10) -> List[Dict[str, float]]:
        """生成交互数据（用于性能测试）"""
        interactions = []
        for i in range(num):
            interactions.append({
                "response_time": np.random.exponential(0.5),
                "user_satisfaction": np.random.beta(2, 1),  # 偏向高值
                "complexity": np.random.rand(),
            })
        return interactions


class TestMetricsCollector:
    """测试指标收集器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, name: str, value: float):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def record_batch(self, name: str, values: List[float]):
        """批量记录"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].extend(values)
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """获取统计信息"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        
        return {
            'count': len(values),
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'p95': float(np.percentile(values, 95)),
            'p99': float(np.percentile(values, 99)),
        }
    
    def print_summary(self):
        """打印汇总信息"""
        print("\n=== 测试指标汇总 ===")
        for name, values in self.metrics.items():
            stats = self.get_statistics(name)
            if stats:
                print(f"{name}:")
                print(f"  次数: {stats['count']}")
                print(f"  均值: {stats['mean']:.4f}")
                print(f"  标准差: {stats['std']:.4f}")
                print(f"  范围: [{stats['min']:.4f}, {stats['max']:.4f}]")
                print(f"  P95: {stats['p95']:.4f}")


class TestScenarios:
    """预定义测试场景"""
    
    @staticmethod
    def low_load_scenario():
        """低负载场景"""
        return {
            "num_requests": 50,
            "memory_growth": 5,
            "pid_updates": 10,
            "expected_throughput": "> 20 req/s",
            "expected_response_time": "< 50ms",
        }
    
    @staticmethod
    def medium_load_scenario():
        """中等负载场景"""
        return {
            "num_requests": 200,
            "memory_growth": 20,
            "pid_updates": 50,
            "expected_throughput": "> 50 req/s",
            "expected_response_time": "< 100ms",
        }
    
    @staticmethod
    def high_load_scenario():
        """高负载场景"""
        return {
            "num_requests": 1000,
            "memory_growth": 100,
            "pid_updates": 200,
            "expected_throughput": "> 100 req/s",
            "expected_response_time": "< 200ms",
        }
    
    @staticmethod
    def stress_scenario():
        """压力测试场景"""
        return {
            "num_requests": 5000,
            "memory_growth": 500,
            "pid_updates": 1000,
            "expected_throughput": "> 200 req/s",
            "expected_response_time": "< 500ms",
        }


class RiemannianTestHelper:
    """黎曼几何测试辅助"""
    
    @staticmethod
    def create_test_field(dim: int = 384) -> RigorousSemanticField:
        """创建测试用的语义场"""
        core = np.random.rand(dim)
        core = core / np.linalg.norm(core)
        return RigorousSemanticField(core_vector=core)
    
    @staticmethod
    def verify_field_properties(field: RigorousSemanticField, test_vector: np.ndarray) -> Dict[str, bool]:
        """验证语义场属性"""
        results = {}
        
        # 计算势能
        try:
            energy = field.calculate_potential_energy(test_vector)
            results['energy_finite'] = np.isfinite(energy)
            results['energy_valid'] = 0 <= energy <= 4.0
        except:
            results['energy_finite'] = False
            results['energy_valid'] = False
        
        # 计算梯度
        try:
            gradient = field.compute_riemannian_gradient(test_vector)
            results['gradient_finite'] = np.all(np.isfinite(gradient))
            results['gradient_shape'] = gradient.shape == test_vector.shape
            results['gradient_norm_ok'] = np.linalg.norm(gradient) < 1000.0
        except:
            results['gradient_finite'] = False
            results['gradient_shape'] = False
            results['gradient_norm_ok'] = False
        
        # 演化
        try:
            evolved, info = field.evolve(test_vector, iterations=3)
            results['evolution_valid'] = evolved is not None
            results['evolution_finite'] = evolved is not None and np.all(np.isfinite(evolved))
            if evolved is not None:
                results['evolution_normalized'] = abs(np.linalg.norm(evolved) - 1.0) < 1e-6
        except:
            results['evolution_valid'] = False
            results['evolution_finite'] = False
            results['evolution_normalized'] = False
        
        return results
    
    @staticmethod
    def performance_comparison(dimensions: List[int]) -> Dict[int, Dict[str, float]]:
        """不同维度的性能比较"""
        results = {}
        
        for dim in dimensions:
            field = RiemannianTestHelper.create_test_field(dim)
            test_vec = RiemannianTestHelper.generate_test_vector(dim)
            
            times = {}
            
            # 势能计算
            start = time.time()
            for _ in range(100):
                field.calculate_potential_energy(test_vec)
            times['potential'] = (time.time() - start) / 100
            
            # 梯度计算
            start = time.time()
            for _ in range(20):
                field.compute_riemannian_gradient(test_vec)
            times['gradient'] = (time.time() - start) / 20
            
            # 演化
            start = time.time()
            for _ in range(10):
                field.evolve(test_vec, iterations=5)
            times['evolution'] = (time.time() - start) / 10
            
            results[dim] = times
        
        return results
    
    @staticmethod
    def generate_test_vector(dim: int) -> np.ndarray:
        """生成测试向量"""
        vec = np.random.rand(dim)
        return vec / np.linalg.norm(vec)


# 全局辅助函数
def setup_test_environment():
    """设置测试环境"""
    np.random.seed(42)  # 可重复的测试
    return True


def teardown_test_environment():
    """清理测试环境"""
    # 清理临时文件等
    pass


def assert_vector_equal(v1, v2, tol=1e-6):
    """断言向量相等"""
    assert np.allclose(v1, v2, atol=tol), f"Vectors not equal: {v1} vs {v2}"


def assert_vector_normalized(v, tol=1e-6):
    """断言向量已归一化"""
    norm = np.linalg.norm(v)
    assert abs(norm - 1.0) < tol, f"Vector not normalized: norm={norm}"


def assert_energy_valid(energy):
    """断言能量值有效"""
    assert np.isfinite(energy), f"Energy not finite: {energy}"
    assert 0 <= energy <= 4.0, f"Energy out of range: {energy}"


if __name__ == "__main__":
    # 简单测试
    print("测试工具模块加载成功")
    
    # 测试数据生成器
    generator = TestDataGenerator()
    states = generator.generate_state(3)
    print(f"生成 {len(states)} 个测试状态")
    
    memories = generator.generate_memory_data(5)
    print(f"生成 {len(memories)} 个测试记忆")
    
    # 测试指标收集器
    collector = TestMetricsCollector()
    collector.record("test_metric", 1.5)
    collector.record("test_metric", 2.3)
    collector.record("test_metric", 1.8)
    
    stats = collector.get_statistics("test_metric")
    print(f"测试指标统计: {stats}")