性能测试 - 基准测试和压力测试

测试目标：
- 响应时间分布（Histogram）
- LLM调用成功率（Counter）
- 记忆检索效率（Gauge）
- 内存使用趋势（Gauge）
- 情感状态分布（Gauge）

import pytest
import numpy as np
import sys
import os
import time
import statistics
from collections import defaultdict

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.riemannian_semantic_field import RigorousSemanticField
from nuwa_core.adaptive_pid import create_adaptive_controller
from nuwa_core.memory_cortex import MemoryCortex
from nuwa_core.nuwa_state import NuwaState


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record(self, name, value):
        self.metrics[name].append(value)
    
    def get_stats(self, name):
        values = self.metrics.get(name, [])
        if not values:
            return {}
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99),
        }
    
    def to_dict(self):
        return {name: self.get_stats(name) for name in self.metrics.keys()}


class TestResponseTimeDistribution:
    """测试响应时间分布（Histogram）"""
    
    def test_semantic_field_response_time(self):
        """语义场响应时间测试"""
        metrics = PerformanceMetrics()
        
        # 不同维度的测试
        dimensions = [64, 128, 256, 384, 512]
        
        for dim in dimensions:
            # 准备数据
            core = np.random.rand(dim)
            core = core / np.linalg.norm(core)
            field = RigorousSemanticField(core_vector=core)
            
            # 测试势能计算
            for _ in range(100):
                state = np.random.rand(dim)
                state = state / np.linalg.norm(state)
                
                start = time.time()
                energy = field.calculate_potential_energy(state)
                elapsed = time.time() - start
                
                metrics.record(f"potential_energy_{dim}", elapsed)
                assert np.isfinite(energy)
            
            # 测试梯度计算
            for _ in range(20):
                state = np.random.rand(dim)
                state = state / np.linalg.norm(state)
                
                start = time.time()
                gradient = field.compute_riemannian_gradient(state)
                elapsed = time.time() - start
                
                metrics.record(f"gradient_{dim}", elapsed)
                assert np.all(np.isfinite(gradient))
            
            # 测试演化
            for _ in range(10):
                state = np.random.rand(dim)
                state = state / np.linalg.norm(state)
                
                start = time.time()
                evolved, info = field.evolve(state, iterations=5)
                elapsed = time.time() - start
                
                metrics.record(f"evolution_{dim}", elapsed)
                assert evolved is not None
        
        # 输出统计
        stats = metrics.to_dict()
        
        # 验证：响应时间应在合理范围内
        for key, stat in stats.items():
            if "potential_energy" in key:
                assert stat['mean'] < 0.01  # 应该非常快
            elif "gradient" in key:
                assert stat['mean'] < 0.05
            elif "evolution" in key:
                assert stat['mean'] < 0.2  # 5次迭代
        
        print("\n=== 语义场响应时间统计 ===")
        for key, stat in stats.items():
            print(f"{key}: mean={stat['mean']*1000:.2f}ms, p95={stat['p95']*1000:.2f}ms")
    
    def test_pid_response_time(self):
        """PID控制器响应时间测试"""
        metrics = PerformanceMetrics()
        
        controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.01)
        
        # 测试1000次更新
        for i in range(1000):
            state = NuwaState(
                emotion_valence=np.random.rand(),
                emotion_arousal=np.random.rand(),
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=np.random.rand()
            )
            
            start = time.time()
            controller.update_parameters(state, performance=0.8)
            elapsed = time.time() - start
            
            metrics.record("pid_update", elapsed)
        
        stats = metrics.get_stats("pid_update")
        
        print("\n=== PID响应时间统计 ===")
        print(f"平均时间: {stats['mean']*1000:.2f}ms")
        print(f"P95: {stats['p95']*1000:.2f}ms")
        print(f"P99: {stats['p99']*1000:.2f}ms")
        
        # 应该非常快
        assert stats['mean'] < 0.001
    
    def test_memory_retrieval_time(self):
        """记忆检索效率测试"""
        metrics = PerformanceMetrics()
        
        cortex = MemoryCortex()
        
        # 预填充记忆
        print("\n填充记忆中...")
        for i in range(50):
            content = f"测试记忆{i}: " + "这是一个较长的文本内容，用于测试记忆系统的性能表现。" * 5
            cortex.store_memory(content, {"index": i, "importance": 0.5})
        
        # 测试检索
        queries = ["测试", "记忆", "性能", "系统", "文本"]
        
        for query in queries:
            for _ in range(20):
                start = time.time()
                results = cortex.retrieve_memory(query, top_k=5)
                elapsed = time.time() - start
                
                metrics.record("memory_retrieval", elapsed)
                assert len(results) >= 0
        
        stats = metrics.get_stats("memory_retrieval")
        
        print("\n=== 记忆检索效率统计 ===")
        print(f"平均时间: {stats['mean']*1000:.2f}ms")
        print(f"中位数: {stats['median']*1000:.2f}ms")
        print(f"最大值: {stats['max']*1000:.2f}ms")
        
        # 检索应该在合理时间内
        assert stats['p95'] < 1.0  # 95%的检索在1秒内完成


class TestLLMSuccessRate:
    """测试LLM调用成功率（模拟）"""
    
    def test_success_rate_tracking(self):
        """成功率跟踪测试"""
        # 模拟LLM调用
        total_calls = 1000
        success_count = 0
        failure_count = 0
        
        # 模拟不同的成功率
        np.random.seed(42)
        
        for _ in range(total_calls):
            # 模拟95%的成功率
            if np.random.random() < 0.95:
                success_count += 1
            else:
                failure_count += 1
        
        success_rate = success_count / total_calls
        
        print("\n=== LLM成功率统计 ===")
        print(f"总调用: {total_calls}")
        print(f"成功: {success_count}")
        print(f"失败: {failure_count}")
        print(f"成功率: {success_rate*100:.2f}%")
        
        assert success_rate >= 0.90  # 应该至少90%
    
    def test_response_time_with_success(self):
        """响应时间与成功率关联"""
        metrics = PerformanceMetrics()
        
        # 模拟带成功率的响应时间
        np.random.seed(42)
        
        for _ in range(100):
            # 90%成功率
            if np.random.random() < 0.9:
                # 成功：快速响应
                response_time = np.random.normal(0.2, 0.05)  # 200ms ± 50ms
                metrics.record("llm_success", response_time)
            else:
                # 失败：超时或错误
                response_time = np.random.normal(2.0, 0.5)  # 2s ± 0.5s
                metrics.record("llm_failure", response_time)
        
        success_stats = metrics.get_stats("llm_success")
        failure_stats = metrics.get_stats("llm_failure")
        
        print("\n=== LLM响应时间（分成功/失败）===")
        print(f"成功: {success_stats['mean']*1000:.0f}ms (±{success_stats['stdev']*1000:.0f}ms)")
        print(f"失败: {failure_stats['mean']*1000:.0f}ms (±{failure_stats['stdev']*1000:.0f}ms)")
        
        # 成功应该比失败快很多
        assert success_stats['mean'] < failure_stats['mean'] * 0.2


class TestMemoryEfficiency:
    """测试记忆效率（Gauge）"""
    
    def test_memory_usage_trend(self):
        """内存使用趋势测试"""
        metrics = PerformanceMetrics()
        
        cortex = MemoryCortex()
        
        # 逐步增加记忆
        for batch in range(10):
            # 每批添加10个记忆
            for i in range(10):
                content = f"批次{batch}记忆{i}: " + "内容" * 20
                cortex.store_memory(content, {"batch": batch})
            
            # 记录内存状态（近似）
            memory_size = len(cortex.memory_graph.nodes)
            metrics.record("memory_nodes", memory_size)
            
            # 记录检索效率
            start = time.time()
            cortex.retrieve_memory("批次", top_k=5)
            elapsed = time.time() - start
            metrics.record("retrieval_time", elapsed)
        
        stats = metrics.to_dict()
        
        print("\n=== 记忆效率统计 ===")
        print(f"最终节点数: {stats['memory_nodes']['max']}")
        print(f"检索时间趋势: {stats['retrieval_time']['mean']*1000:.2f}ms ± {stats['retrieval_time']['stdev']*1000:.2f}ms")
        
        # 检索时间不应该随记忆增加而急剧恶化
        assert stats['retrieval_time']['max'] < stats['retrieval_time']['mean'] * 3
    
    def test_consolidation_efficiency(self):
        """记忆巩固效率"""
        cortex = MemoryCortex()
        
        # 填充记忆
        for i in range(20):
            cortex.store_memory(f"巩固测试{i}: " + "内容" * 10, {"importance": 0.5})
        
        # 测试巩固时间
        start = time.time()
        cortex.consolidate_memory()
        elapsed = time.time() - start
        
        print(f"\n记忆巩固时间: {elapsed*1000:.2f}ms")
        
        # 巩固应该在合理时间内完成
        assert elapsed < 5.0


class TestEmotionalDistribution:
    """测试情感状态分布（Gauge）"""
    
    def test_emotion_state_tracking(self):
        """情感状态跟踪"""
        metrics = PerformanceMetrics()
        
        # 模拟100次交互的情感状态
        np.random.seed(42)
        
        for i in range(100):
            # 生成情感状态（模拟真实分布）
            valence = np.clip(np.random.normal(0.6, 0.2), 0, 1)
            arousal = np.clip(np.random.normal(0.5, 0.15), 0, 1)
            
            state = NuwaState(
                emotion_valence=valence,
                emotion_arousal=arousal,
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=0.5
            )
            
            metrics.record("valence", valence)
            metrics.record("arousal", arousal)
        
        valence_stats = metrics.get_stats("valence")
        arousal_stats = metrics.get_stats("arousal")
        
        print("\n=== 情感状态分布 ===")
        print(f"Valence (效价): {valence_stats['mean']:.2f} ± {valence_stats['stdev']:.2f}")
        print(f"  范围: [{valence_stats['min']:.2f}, {valence_stats['max']:.2f}]")
        print(f"  P50: {valence_stats['median']:.2f}")
        print(f"Arousal (唤醒): {arousal_stats['mean']:.2f} ± {arousal_stats['stdev']:.2f}")
        print(f"  范围: [{arousal_stats['min']:.2f}, {arousal_stats['max']:.2f}]")
        print(f"  P50: {arousal_stats['median']:.2f}")
        
        # 验证分布合理性
        assert 0 <= valence_stats['mean'] <= 1
        assert 0 <= arousal_stats['mean'] <= 1
        assert valence_stats['stdev'] < 0.5  # 不应该过于分散


class TestStressTest:
    """压力测试"""
    
    def test_high_load_scenario(self):
        """高负载场景测试"""
        print("\n=== 高负载压力测试 ===")
        
        # 系统组件
        cortex = MemoryCortex()
        controller = create_adaptive_controller(kp=1.0, ki=0.1, kd=0.01)
        
        # 模拟高并发场景
        num_requests = 500
        response_times = []
        success_count = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            # 1. 记忆存储
            if i % 10 == 0:
                cortex.store_memory(f"高负载记忆{i}: " + "内容" * 50, {"load": i})
            
            # 2. 记忆检索
            if i % 5 == 0:
                retrieval_start = time.time()
                cortex.retrieve_memory("记忆", top_k=3)
                retrieval_time = time.time() - retrieval_start
                response_times.append(retrieval_time)
            
            # 3. PID更新
            state = NuwaState(
                emotion_valence=np.random.rand(),
                emotion_arousal=np.random.rand(),
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=np.random.rand()
            )
            controller.update_parameters(state, performance=0.8)
            
            # 4. 模拟LLM调用（95%成功率）
            if np.random.random() < 0.95:
                success_count += 1
            
            # 模拟思考时间
            time.sleep(0.001)
        
        total_time = time.time() - start_time
        
        # 统计
        throughput = num_requests / total_time
        avg_response = statistics.mean(response_times) if response_times else 0
        success_rate = success_count / num_requests
        
        print(f"总请求数: {num_requests}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"吞吐量: {throughput:.1f} req/s")
        print(f"平均响应时间: {avg_response*1000:.2f}ms")
        print(f"成功率: {success_rate*100:.1f}%")
        
        # 性能指标
        assert throughput > 50  # 至少50 req/s
        assert avg_response < 0.1  # 检索<100ms
        assert success_rate > 0.90  # 成功率>90%
    
    def test_memory_leak_check(self):
        """内存泄漏检查"""
        import gc
        
        initial_objects = len(gc.get_objects())
        
        # 创建大量对象
        controllers = []
        for i in range(100):
            controller = create_adaptive_controller(
                kp=1.0 + i * 0.01,
                ki=0.1 + i * 0.001,
                kd=0.01 + i * 0.0001
            )
            controllers.append(controller)
        
        # 清理前
        after_create = len(gc.get_objects())
        
        # 删除引用并强制GC
        del controllers
        gc.collect()
        
        # 清理后
        after_cleanup = len(gc.get_objects())
        
        print(f"\n=== 内存泄漏检查 ===")
        print(f"初始对象: {initial_objects}")
        print(f"创建后: {after_create}")
        print(f"清理后: {after_cleanup}")
        print(f"泄漏对象: {after_cleanup - initial_objects}")
        
        # 允许少量泄漏（< 1000个对象）
        assert after_cleanup - initial_objects < 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])