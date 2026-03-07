"""
监控指标收集器

提供Prometheus兼容的指标收集功能
包含：
- 响应时间分布（Histogram）
- LLM调用成功率（Counter）
- 记忆检索效率（Histogram）
- 内存使用趋势（Gauge）
- 情感状态分布（Histogram）
- PID控制器参数（Gauge）
- RL训练状态（Gauge）
"""

import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np
import os

# 条件导入psutil，处理psutil不可用的情况
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil模块不可用，系统资源监控功能将受限")

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        start_http_server,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("Warning: prometheus_client not available, metrics will be logged only")


@dataclass
class MetricsConfig:
    """指标配置"""
    http_port: int = 8080
    metrics_path: str = "/metrics"
    enabled: bool = True
    buffer_size: int = 10000
    flush_interval: int = 30  # 秒


class MetricsCollector:
    """监控指标收集器"""
    
    def __init__(self, config: MetricsConfig = None):
        import threading
        self.config = config or MetricsConfig()
        self.lock = threading.Lock()
        
        # 指标存储
        self.response_times = deque(maxlen=self.config.buffer_size)
        self.llm_calls = defaultdict(lambda: {"success": 0, "total": 0})
        self.memory_retrieval_times = deque(maxlen=self.config.buffer_size)
        self.emotion_states = deque(maxlen=self.config.buffer_size)
        self.pid_params = {"kp": 0, "ki": 0, "kd": 0}
        self.rl_stats = {"episodes": 0, "avg_reward": 0.0}
        self.memory_nodes = 0
        
        # 黎曼几何计算耗时
        self.riemannian_times = {
            "potential": deque(maxlen=self.config.buffer_size),
            "gradient": deque(maxlen=self.config.buffer_size),
            "evolution": deque(maxlen=self.config.buffer_size),
        }
        
        # Prometheus指标
        self._init_prometheus_metrics()
        
        # 启动HTTP服务器
        if self.config.enabled:
            try:
                # 启动自定义HTTP服务器提供JSON格式指标
                from http.server import HTTPServer, BaseHTTPRequestHandler
                
                class MetricsHandler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        if self.path == '/metrics':
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            metrics_data = self.server.collector.get_system_status()
                            import json
                            self.wfile.write(json.dumps(metrics_data).encode('utf-8'))
                        else:
                            self.send_response(404)
                            self.end_headers()
                
                server = HTTPServer(('localhost', self.config.http_port), MetricsHandler)
                server.collector = self
                
                # 启动服务器线程
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
                print(f"✅ Metrics server started on port {self.config.http_port}")
                
                # 如果Prometheus可用，也启动Prometheus服务器
                if PROMETHEUS_AVAILABLE:
                    start_http_server(self.config.http_port + 1)
                    print(f"✅ Prometheus metrics server started on port {self.config.http_port + 1}")
            except Exception as e:
                print(f"⚠️ Failed to start metrics server: {e}")
    
    def _init_prometheus_metrics(self):
        """初始化Prometheus指标"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # 响应时间分布
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP请求响应时间',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # LLM调用统计
        self.llm_calls_total = Counter(
            'llm_calls_total',
            'LLM调用总数',
            ['status', 'model']
        )
        
        # 记忆检索时间
        self.memory_retrieval_duration = Histogram(
            'memory_retrieval_duration_seconds',
            '记忆检索耗时',
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
        )
        
        # 内存使用
        self.process_memory = Gauge(
            'process_resident_memory_bytes',
            '进程常驻内存（字节）'
        )
        
        self.process_cpu = Gauge(
            'process_cpu_seconds_total',
            '进程CPU总时间（秒）'
        )
        
        # 情感状态分布
        self.emotion_valence = Histogram(
            'nuwa_emotion_valence',
            '情感效价分布',
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        self.emotion_arousal = Histogram(
            'nuwa_emotion_arousal',
            '情感唤醒分布',
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # PID参数
        self.pid_kp = Gauge('pid_kp', 'PID Kp参数')
        self.pid_ki = Gauge('pid_ki', 'PID Ki参数')
        self.pid_kd = Gauge('pid_kd', 'PID Kd参数')
        
        # RL统计
        self.rl_training_episodes = Gauge(
            'rl_training_episodes',
            'RL训练轮次'
        )
        
        self.rl_avg_reward = Gauge(
            'rl_avg_reward',
            'RL平均奖励'
        )
        
        # 记忆图
        self.memory_graph_nodes = Gauge(
            'memory_graph_nodes',
            '记忆图节点数量'
        )
        
        # 黎曼几何计算耗时
        self.riemannian_potential_duration = Histogram(
            'riemannian_potential_duration_seconds',
            '黎曼势能计算耗时',
            buckets=[0.0001, 0.001, 0.01, 0.1, 0.5, 1.0]
        )
        
        self.riemannian_gradient_duration = Histogram(
            'riemannian_gradient_duration_seconds',
            '黎曼梯度计算耗时',
            buckets=[0.0001, 0.001, 0.01, 0.1, 0.5, 1.0]
        )
        
        self.riemannian_evolution_duration = Histogram(
            'riemannian_evolution_duration_seconds',
            '黎曼演化计算耗时',
            buckets=[0.0001, 0.001, 0.01, 0.1, 0.5, 1.0, 2.0]
        )
        
        # HTTP请求统计
        self.http_requests_total = Counter(
            'http_requests_total',
            'HTTP请求总数',
            ['method', 'endpoint', 'status']
        )
        
        # 事件统计
        self.events_total = Counter(
            'nuwa_events_total',
            '状态事件总数',
            ['event_type', 'source']
        )
        
        # 状态变化频率
        self.state_changes = Counter(
            'nuwa_state_changes_total',
            '状态变化总数',
            ['change_type']
        )
        
        # 缓存命中率
        self.cache_hits = Counter(
            'nuwa_cache_hits_total',
            '缓存命中次数',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'nuwa_cache_misses_total',
            '缓存未命中次数',
            ['cache_type']
        )
        
        # 事实更新统计
        self.fact_updates = Counter(
            'nuwa_facts_total',
            '事实更新总数',
            ['operation', 'source']
        )
        
        # 状态事件处理延迟
        self.event_processing_duration = Histogram(
            'nuwa_event_processing_duration_seconds',
            '事件处理延迟',
            buckets=[0.0001, 0.001, 0.01, 0.1, 0.5, 1.0]
        )
    
    # ==================== 指标记录方法 ====================
    
    def record_response_time(self, endpoint: str, duration: float):
        """记录响应时间"""
        with self.lock:
            self.response_times.append({
                "endpoint": endpoint,
                "duration": duration,
                "timestamp": time.time()
            })
        
        if PROMETHEUS_AVAILABLE:
            self.http_request_duration.observe(duration)
    
    def record_llm_call(self, model: str, success: bool):
        """记录LLM调用"""
        with self.lock:
            key = f"{model}"
            self.llm_calls[key]["total"] += 1
            if success:
                self.llm_calls[key]["success"] += 1
        
        if PROMETHEUS_AVAILABLE:
            status = "success" if success else "failure"
            self.llm_calls_total.labels(status=status, model=model).inc()
    
    def record_memory_retrieval(self, duration: float):
        """记录记忆检索"""
        with self.lock:
            self.memory_retrieval_times.append(duration)
        
        if PROMETHEUS_AVAILABLE:
            self.memory_retrieval_duration.observe(duration)
    
    def record_emotion_state(self, valence: float, arousal: float):
        """记录情感状态"""
        with self.lock:
            self.emotion_states.append({
                "valence": valence,
                "arousal": arousal,
                "timestamp": time.time()
            })
        
        if PROMETHEUS_AVAILABLE:
            self.emotion_valence.observe(valence)
            self.emotion_arousal.observe(arousal)
    
    def record_pid_params(self, kp: float, ki: float, kd: float):
        """记录PID参数"""
        with self.lock:
            self.pid_params = {"kp": kp, "ki": ki, "kd": kd}
        
        if PROMETHEUS_AVAILABLE:
            self.pid_kp.set(kp)
            self.pid_ki.set(ki)
            self.pid_kd.set(kd)
    
    def record_rl_stats(self, episodes: int, avg_reward: float):
        """记录RL统计"""
        with self.lock:
            self.rl_stats = {"episodes": episodes, "avg_reward": avg_reward}
        
        if PROMETHEUS_AVAILABLE:
            self.rl_training_episodes.set(episodes)
            self.rl_avg_reward.set(avg_reward)
    
    def record_memory_nodes(self, count: int):
        """记录记忆节点数量"""
        with self.lock:
            self.memory_nodes = count
        
        if PROMETHEUS_AVAILABLE:
            self.memory_graph_nodes.set(count)
    
    def record_riemannian_calculation(self, calc_type: str, duration: float):
        """记录黎曼几何计算耗时"""
        with self.lock:
            if calc_type in self.riemannian_times:
                self.riemannian_times[calc_type].append(duration)
        
        if PROMETHEUS_AVAILABLE:
            if calc_type == "potential":
                self.riemannian_potential_duration.observe(duration)
            elif calc_type == "gradient":
                self.riemannian_gradient_duration.observe(duration)
            elif calc_type == "evolution":
                self.riemannian_evolution_duration.observe(duration)
    
    def record_http_request(self, method: str, endpoint: str, status: int):
        """记录HTTP请求"""
        if PROMETHEUS_AVAILABLE:
            status_str = str(status)
            self.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_str
            ).inc()
    
    def record_event(self, event_type: str, source: str = "system"):
        """记录事件"""
        if PROMETHEUS_AVAILABLE:
            self.events_total.labels(
                event_type=event_type,
                source=source
            ).inc()
    
    def record_state_change(self, change_type: str):
        """记录状态变化"""
        if PROMETHEUS_AVAILABLE:
            self.state_changes.labels(change_type=change_type).inc()
    
    def record_cache_hit(self, cache_type: str):
        """记录缓存命中"""
        if PROMETHEUS_AVAILABLE:
            self.cache_hits.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """记录缓存未命中"""
        if PROMETHEUS_AVAILABLE:
            self.cache_misses.labels(cache_type=cache_type).inc()
    
    def record_fact_update(self, operation: str, source: str):
        """记录事实更新"""
        if PROMETHEUS_AVAILABLE:
            self.fact_updates.labels(
                operation=operation,
                source=source
            ).inc()
    
    def record_event_processing_duration(self, duration: float):
        """记录事件处理延迟"""
        if PROMETHEUS_AVAILABLE:
            self.event_processing_duration.observe(duration)
    
    def update_system_metrics(self):
        """更新系统指标"""
        if not PROMETHEUS_AVAILABLE or not PSUTIL_AVAILABLE:
            return
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_times = process.cpu_times()
            
            self.process_memory.set(memory_info.rss)
            self.process_cpu.set(cpu_times.user + cpu_times.system)
        except:
            pass
    
    # ==================== 查询方法 ====================
    
    def get_response_time_stats(self) -> Dict[str, Any]:
        """获取响应时间统计"""
        with self.lock:
            if not self.response_times:
                return {}
            
            times = [r["duration"] for r in self.response_times]
            
            return {
                "count": len(times),
                "mean": float(np.mean(times)),
                "median": float(np.median(times)),
                "p95": float(np.percentile(times, 95)),
                "p99": float(np.percentile(times, 99)),
                "min": float(np.min(times)),
                "max": float(np.max(times)),
            }
    
    def get_llm_success_rate(self, model: Optional[str] = None) -> float:
        """获取LLM成功率"""
        with self.lock:
            if model:
                data = self.llm_calls.get(f"{model}", {"success": 0, "total": 0})
            else:
                # 所有模型的总计
                total_success = sum(v["success"] for v in self.llm_calls.values())
                total_calls = sum(v["total"] for v in self.llm_calls.values())
                data = {"success": total_success, "total": total_calls}
            
            if data["total"] == 0:
                return 0.0
            
            return data["success"] / data["total"]
    
    def get_memory_retrieval_stats(self) -> Dict[str, Any]:
        """获取记忆检索统计"""
        with self.lock:
            if not self.memory_retrieval_times:
                return {}
            
            times = list(self.memory_retrieval_times)
            
            return {
                "count": len(times),
                "mean": float(np.mean(times)),
                "median": float(np.median(times)),
                "p95": float(np.percentile(times, 95)),
                "min": float(np.min(times)),
                "max": float(np.max(times)),
            }
    
    def get_emotion_distribution(self) -> Dict[str, Any]:
        """获取情感分布"""
        with self.lock:
            if not self.emotion_states:
                return {}
            
            valences = [e["valence"] for e in self.emotion_states]
            arousals = [e["arousal"] for e in self.emotion_states]
            
            return {
                "valence": {
                    "mean": float(np.mean(valences)),
                    "std": float(np.std(valences)),
                    "distribution": np.histogram(valences, bins=10)[0].tolist()
                },
                "arousal": {
                    "mean": float(np.mean(arousals)),
                    "std": float(np.std(arousals)),
                    "distribution": np.histogram(arousals, bins=10)[0].tolist()
                },
                "total_states": len(self.emotion_states)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "timestamp": time.time(),
            "pid_params": self.pid_params.copy(),
            "rl_stats": self.rl_stats.copy(),
            "memory_nodes": self.memory_nodes,
        }
        
        # 添加性能统计
        response_stats = self.get_response_time_stats()
        if response_stats:
            status["response_time"] = response_stats
        
        llm_rate = self.get_llm_success_rate()
        status["llm_success_rate"] = llm_rate
        
        retrieval_stats = self.get_memory_retrieval_stats()
        if retrieval_stats:
            status["memory_retrieval"] = retrieval_stats
        
        emotion_dist = self.get_emotion_distribution()
        if emotion_dist:
            status["emotion_distribution"] = emotion_dist
        
        # 系统资源
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                status["system"] = {
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads()
                }
            except:
                status["system"] = {}
        else:
            status["system"] = {"note": "psutil不可用"}
        
        return status
    
    def get_metrics_summary(self) -> str:
        """获取指标汇总（用于日志）"""
        status = self.get_system_status()
        
        lines = [
            "=== 系统指标汇总 ===",
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "性能指标:",
        ]
        
        if "response_time" in status:
            rt = status["response_time"]
            lines.append(f"  响应时间: {rt['mean']*1000:.1f}ms (P95: {rt['p95']*1000:.1f}ms)")
        
        lines.append(f"  LLM成功率: {status['llm_success_rate']*100:.1f}%")
        
        if "memory_retrieval" in status:
            mr = status["memory_retrieval"]
            lines.append(f"  记忆检索: {mr['mean']*1000:.1f}ms (P95: {mr['p95']*1000:.1f}ms)")
        
        lines.append("")
        lines.append("系统状态:")
        lines.append(f"  记忆节点: {status['memory_nodes']}")
        lines.append(f"  PID参数: Kp={status['pid_params']['kp']:.3f}, Ki={status['pid_params']['ki']:.3f}, Kd={status['pid_params']['kd']:.3f}")
        lines.append(f"  RL训练: {status['rl_stats']['episodes']}轮, 平均奖励: {status['rl_stats']['avg_reward']:.3f}")
        
        if "emotion_distribution" in status:
            ed = status["emotion_distribution"]
            lines.append(f"  情感状态: {ed['total_states']}个样本")
            lines.append(f"    效价均值: {ed['valence']['mean']:.2f} ± {ed['valence']['std']:.2f}")
            lines.append(f"    唤醒均值: {ed['arousal']['mean']:.2f} ± {ed['arousal']['std']:.2f}")
        
        if "system" in status and status["system"]:
            sys_info = status["system"]
            lines.append("")
            lines.append("资源使用:")
            lines.append(f"  内存: {sys_info.get('memory_mb', 0):.1f} MB")
            lines.append(f"  CPU: {sys_info.get('cpu_percent', 0):.1f}%")
            lines.append(f"  线程: {sys_info.get('threads', 0)}")
        
        return "\n".join(lines)
    
    def export_prometheus_metrics(self) -> str:
        """导出Prometheus格式的指标"""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus client not available\n"
        
        return generate_latest().decode('utf-8')
    
    # ==================== 实时监控 ====================
    
    def start_monitoring_thread(self):
        """启动监控线程（周期性更新系统指标）"""
        def monitor_loop():
            while True:
                try:
                    self.update_system_metrics()
                    time.sleep(30)  # 每30秒更新一次
                except Exception as e:
                    print(f"监控线程错误: {e}")
                    break
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        return thread


# ==================== 全局实例 ====================

# 全局指标收集器实例
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector


def init_metrics_collector(config: MetricsConfig = None) -> MetricsCollector:
    """初始化全局指标收集器"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector(config)
    return _global_metrics_collector


# ==================== 装饰器 ====================

def record_response_time(endpoint: str):
    """记录响应时间的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                collector.record_response_time(endpoint, duration)
                return result
            except Exception as e:
                duration = time.time() - start
                collector.record_response_time(endpoint + "_error", duration)
                raise
        return wrapper
    return decorator


def record_riemannian_calculation(calc_type: str):
    """记录黎曼几何计算的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                collector.record_riemannian_calculation(calc_type, duration)
                return result
            except Exception as e:
                raise
        return wrapper
    return decorator


def record_event_processing(event_type: str, source: str = "system"):
    """记录事件处理的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                # 记录事件
                collector.record_event(event_type, source)
                collector.record_event_processing_duration(duration)
                
                return result
            except Exception as e:
                collector.record_event(f"{event_type}_error", source)
                raise
        return wrapper
    return decorator


def record_cache_operation(cache_type: str):
    """记录缓存操作的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            result = func(*args, **kwargs)
            
            # 根据函数名和结果判断是命中还是未命中
            func_name = func.__name__
            if "get" in func_name.lower():
                if result is not None:
                    collector.record_cache_hit(cache_type)
                else:
                    collector.record_cache_miss(cache_type)
            
            return result
        return wrapper
    return decorator


def record_llm_call_performance(model: str):
    """记录LLM调用性能的装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                
                # 记录成功调用
                collector.record_llm_call(model, True)
                collector.record_response_time(f"llm_{model}", duration)
                
                return result
            except Exception as e:
                # 记录失败调用
                collector.record_llm_call(model, False)
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试指标收集器
    collector = init_metrics_collector()
    
    # 模拟一些指标
    collector.record_response_time("/api/chat", 0.15)
    collector.record_response_time("/api/chat", 0.23)
    collector.record_llm_call("gpt-3.5", True)
    collector.record_llm_call("gpt-3.5", False)
    collector.record_memory_retrieval(0.05)
    collector.record_emotion_state(0.7, 0.6)
    collector.record_pid_params(1.2, 0.15, 0.05)
    collector.record_rl_stats(100, 0.85)
    collector.record_memory_nodes(150)
    
    # 打印汇总
    print(collector.get_metrics_summary())