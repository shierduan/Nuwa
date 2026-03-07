"""
依赖注入容器配置

为监控指标收集器提供DI配置
"""

from dependency_injector import containers, providers
from .metrics_collector import MetricsCollector, MetricsConfig, get_metrics_collector
from .riemannian_semantic_field import RigorousSemanticField
from .adaptive_pid import AdaptivePIDController, create_adaptive_controller
from .memory_cortex import MemoryCortex


class MonitoringContainer(containers.DeclarativeContainer):
    """监控容器"""
    
    config = providers.Configuration()
    
    # 指标配置
    metrics_config = providers.Singleton(
        MetricsConfig,
        http_port=8080,
        metrics_path="/metrics",
        enabled=True,
        buffer_size=10000,
        flush_interval=30
    )
    
    # 指标收集器
    metrics_collector = providers.Singleton(
        MetricsCollector,
        config=metrics_config
    )


class CoreContainer(containers.DeclarativeContainer):
    """核心系统容器"""
    
    # 监控容器
    monitoring = providers.Container(MonitoringContainer)
    
    # 核心组件
    memory_cortex = providers.Singleton(MemoryCortex)
    
    # 语义场工厂
    semantic_field_factory = providers.Factory(
        RigorousSemanticField,
        core_vector=providers.Object(None)  # 需要动态设置
    )
    
    # PID控制器工厂
    pid_controller_factory = providers.Factory(
        create_adaptive_controller,
        kp=1.0,
        ki=0.1,
        kd=0.01,
        state_dim=5,
        action_dim=3
    )


# 全局容器实例
_global_container: Optional[CoreContainer] = None


def get_container() -> CoreContainer:
    """获取全局容器"""
    global _global_container
    if _global_container is None:
        _global_container = CoreContainer()
    return _global_container


def init_container() -> CoreContainer:
    """初始化全局容器"""
    global _global_container
    if _global_container is None:
        _global_container = CoreContainer()
        # 启动监控
        collector = _global_container.monitoring.metrics_collector()
        collector.start_monitoring_thread()
    return _global_container


__all__ = [
    "MonitoringContainer",
    "CoreContainer",
    "get_container",
    "init_container",
]