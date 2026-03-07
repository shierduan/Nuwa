"""
监控系统集成测试

测试监控指标收集器与核心系统的集成
"""

import pytest
import sys
import os
import time
import threading

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

from nuwa_core.metrics_collector import (
    MetricsCollector,
    MetricsConfig,
    get_metrics_collector,
    init_metrics_collector,
    record_response_time,
    record_riemannian_calculation,
)
from nuwa_core.nuwa_state import NuwaState
from nuwa_core.riemannian_semantic_field import RigorousSemanticField


class TestMetricsCollectorIntegration:
    """测试指标收集器集成"""
    
    def test_global_collector_initialization(self):
        """测试全局收集器初始化"""
        # 重置全局实例
        import nuwa_core.metrics_collector as mc_module
        mc_module._global_metrics_collector = None
        
        # 初始化
        collector = init_metrics_collector()
        
        assert collector is not None
        assert isinstance(collector, MetricsCollector)
        
        # 再次获取应该是同一个实例
        collector2 = get_metrics_collector()
        assert collector is collector2
    
    def test_record_response_time(self):
        """测试记录响应时间"""
        collector = MetricsCollector()
        
        # 记录一些响应时间
        collector.record_response_time("/api/chat", 0.1)
        collector.record_response_time("/api/chat", 0.2)
        collector.record_response_time("/api/memory", 0.05)
        
        stats = collector.get_response_time_stats()
        
        assert stats["count"] == 3
        assert 0.05 <= stats["mean"] <= 0.2
        assert stats["min"] <= stats["mean"] <= stats["max"]
    
    def test_record_llm_call(self):
        """测试记录LLM调用"""
        collector = MetricsCollector()
        
        # 模拟调用
        for _ in range(8):
            collector.record_llm_call("gpt-3.5", True)
        for _ in range(2):
            collector.record_llm_call("gpt-3.5", False)
        
        success_rate = collector.get_llm_success_rate("gpt-3.5")
        
        assert success_rate == 0.8
    
    def test_record_memory_retrieval(self):
        """测试记录记忆检索"""
        collector = MetricsCollector()
        
        for i in range(10):
            collector.record_memory_retrieval(0.01 * (i + 1))
        
        stats = collector.get_memory_retrieval_stats()
        
        assert stats["count"] == 10
        assert 0.01 <= stats["mean"] <= 0.1
    
    def test_record_emotion_state(self):
        """测试记录情感状态"""
        collector = MetricsCollector()
        
        # 记录情感状态
        collector.record_emotion_state(0.7, 0.6)
        collector.record_emotion_state(0.3, 0.5)
        collector.record_emotion_state(0.8, 0.9)
        
        dist = collector.get_emotion_distribution()
        
        assert dist["total_states"] == 3
        assert 0.3 <= dist["valence"]["mean"] <= 0.8
    
    def test_record_pid_params(self):
        """测试记录PID参数"""
        collector = MetricsCollector()
        
        collector.record_pid_params(1.5, 0.2, 0.05)
        
        status = collector.get_system_status()
        
        assert status["pid_params"]["kp"] == 1.5
        assert status["pid_params"]["ki"] == 0.2
        assert status["pid_params"]["kd"] == 0.05
    
    def test_record_rl_stats(self):
        """测试记录RL统计"""
        collector = MetricsCollector()
        
        collector.record_rl_stats(100, 0.85)
        
        status = collector.get_system_status()
        
        assert status["rl_stats"]["episodes"] == 100
        assert abs(status["rl_stats"]["avg_reward"] - 0.85) < 1e-6
    
    def test_record_memory_nodes(self):
        """测试记录记忆节点"""
        collector = MetricsCollector()
        
        collector.record_memory_nodes(150)
        
        status = collector.get_system_status()
        
        assert status["memory_nodes"] == 150
    
    def test_record_riemannian_calculation(self):
        """测试记录黎曼几何计算"""
        collector = MetricsCollector()
        
        # 记录不同类型的计算
        collector.record_riemannian_calculation("potential", 0.001)
        collector.record_riemannian_calculation("gradient", 0.005)
        collector.record_riemannian_calculation("evolution", 0.02)
        
        # 应该有记录
        assert len(collector.riemannian_times["potential"]) == 1
        assert len(collector.riemannian_times["gradient"]) == 1
        assert len(collector.riemannian_times["evolution"]) == 1
    
    def test_get_system_status(self):
        """测试获取系统状态"""
        collector = MetricsCollector()
        
        # 填充一些数据
        collector.record_response_time("/test", 0.1)
        collector.record_llm_call("test", True)
        collector.record_memory_retrieval(0.05)
        collector.record_emotion_state(0.6, 0.7)
        collector.record_pid_params(1.0, 0.1, 0.01)
        collector.record_rl_stats(50, 0.9)
        collector.record_memory_nodes(100)
        
        status = collector.get_system_status()
        
        # 验证状态包含必要字段
        assert "timestamp" in status
        assert "pid_params" in status
        assert "rl_stats" in status
        assert "memory_nodes" in status
        assert "response_time" in status
        assert "llm_success_rate" in status
        assert "memory_retrieval" in status
        assert "emotion_distribution" in status
    
    def test_metrics_summary(self):
        """测试指标汇总"""
        collector = MetricsCollector()
        
        # 填充数据
        collector.record_response_time("/api", 0.15)
        collector.record_llm_call("gpt", True)
        collector.record_memory_retrieval(0.03)
        collector.record_emotion_state(0.7, 0.6)
        collector.record_pid_params(1.2, 0.15, 0.05)
        collector.record_rl_stats(100, 0.85)
        collector.record_memory_nodes(150)
        
        summary = collector.get_metrics_summary()
        
        # 验证摘要包含关键信息
        assert "系统指标汇总" in summary
        assert "响应时间" in summary
        assert "LLM成功率" in summary
        assert "记忆检索" in summary
        assert "记忆节点" in summary
        assert "PID参数" in summary
    
    def test_decorator_response_time(self):
        """测试响应时间装饰器"""
        collector = init_metrics_collector()
        
        @record_response_time("/test/decorator")
        def test_function():
            time.sleep(0.01)
            return "result"
        
        result = test_function()
        
        assert result == "result"
        
        # 检查是否记录了指标
        stats = collector.get_response_time_stats()
        assert stats["count"] >= 1
    
    def test_decorator_riemannian_calculation(self):
        """测试黎曼几何计算装饰器"""
        collector = init_metrics_collector()
        
        @record_riemannian_calculation("potential")
        def calculate_potential():
            time.sleep(0.001)
            return 0.5
        
        result = calculate_potential()
        
        assert result == 0.5
        
        # 检查记录
        assert len(collector.riemannian_times["potential"]) >= 1
    
    def test_concurrent_metrics_recording(self):
        """测试并发指标记录"""
        collector = MetricsCollector()
        
        def record_metrics(thread_id):
            for i in range(10):
                collector.record_response_time(f"/api/{thread_id}", 0.1 + i * 0.01)
                collector.record_llm_call("test", i % 2 == 0)
                time.sleep(0.001)
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=record_metrics, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有记录都被保存
        stats = collector.get_response_time_stats()
        assert stats["count"] >= 50  # 5线程 * 10次
        
        success_rate = collector.get_llm_success_rate("test")
        assert 0.4 <= success_rate <= 0.6  # 约50%成功率
    
    def test_prometheus_export(self):
        """测试Prometheus格式导出"""
        try:
            from prometheus_client import generate_latest
            collector = MetricsCollector()
            
            # 填充一些指标
            collector.record_response_time("/test", 0.1)
            collector.record_llm_call("test", True)
            
            # 导出
            metrics_text = collector.export_prometheus_metrics()
            
            # 验证格式
            assert "http_request_duration_seconds" in metrics_text
            assert "llm_calls_total" in metrics_text
            
        except ImportError:
            pytest.skip("prometheus_client not available")


class TestMonitoringWithCoreSystems:
    """测试监控与核心系统的集成"""
    
    def test_monitoring_with_semantic_field(self):
        """测试语义场计算的监控"""
        collector = init_metrics_collector()
        
        # 创建语义场
        core = np.random.rand(384)
        core = core / np.linalg.norm(core)
        field = RigorousSemanticField(core_vector=core)
        
        # 执行计算并记录指标
        state = np.random.rand(384)
        state = state / np.linalg.norm(state)
        
        # 势能计算
        start = time.time()
        energy = field.calculate_potential_energy(state)
        duration = time.time() - start
        collector.record_riemannian_calculation("potential", duration)
        
        # 梯度计算
        start = time.time()
        gradient = field.compute_riemannian_gradient(state)
        duration = time.time() - start
        collector.record_riemannian_calculation("gradient", duration)
        
        # 演化
        start = time.time()
        evolved, info = field.evolve(state, iterations=5)
        duration = time.time() - start
        collector.record_riemannian_calculation("evolution", duration)
        
        # 验证记录
        assert len(collector.riemannian_times["potential"]) >= 1
        assert len(collector.riemannian_times["gradient"]) >= 1
        assert len(collector.riemannian_times["evolution"]) >= 1
    
    def test_monitoring_with_pid_controller(self):
        """测试PID控制器的监控"""
        from nuwa_core.adaptive_pid import create_adaptive_controller
        
        collector = init_metrics_collector()
        controller = create_adaptive_controller()
        
        # 多次更新并记录
        for i in range(10):
            state = NuwaState(
                emotion_valence=np.random.rand(),
                emotion_arousal=np.random.rand(),
                personality_openness=0.7,
                personality_conscientiousness=0.8,
                context_complexity=0.5
            )
            
            performance = 0.8 + np.random.rand() * 0.2
            
            # 记录响应时间
            start = time.time()
            controller.update_parameters(state, performance)
            duration = time.time() - start
            
            collector.record_response_time("/pid/update", duration)
        
        # 记录PID参数
        collector.record_pid_params(
            controller.base_pid.kp,
            controller.base_pid.ki,
            controller.base_pid.kd
        )
        
        # 验证
        stats = collector.get_response_time_stats()
        assert stats["count"] >= 10


if __name__ == "__main__":
    # 运行测试
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", __file__, "-v", "-s"])