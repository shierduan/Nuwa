"""
女娲核心引擎 (Nuwa Core Engine)

一个完整的、独立的核心引擎包，包含：
- 女娲内核：类人AI对话系统（统一异步架构）

核心模块：
- nuwa_kernel_async: 女娲内核（统一异步架构），类人AI对话系统
- nuwa_state: 女娲状态管理
- drive_system: 生物节律系统
- memory_cortex: 记忆皮层
- memory_dreamer: 记忆梦境系统
- personality: 人格管理模块
- self_evolution: 自我进化模块
- self_evolution_state: 自我进化状态管理
- cache_manager: 缓存管理器
- memory_optimizer: 内存优化器
- riemannian_semantic_field: 黎曼几何语义场
- adaptive_pid: 自适应PID控制

注意：nuwa_kernel.py 已废弃，统一使用 nuwa_kernel_async.py
"""

# 女娲内核相关（统一为异步架构，保持向后兼容）
from .nuwa_kernel_async import NuwaKernelAsync as NuwaKernel
from .nuwa_kernel_async import NuwaKernelAsync  # 同时导出新的异步内核名称
from .nuwa_state import NuwaState
from .drive_system import BioRhythm, PIDController
from .memory_cortex import MemoryCortex
from .memory_dreamer import MemoryDreamer
from .personality import Personality
from .self_evolution_state import SelfEvolutionState
from .model_utils import (
    EMBEDDING_MODEL_NAME,
    DEFAULT_EMBEDDING_DIR,
    ensure_embedding_model_dir
)

# 事件系统
from .state_events import (
    StateEventType,
    StateEvent,
    StateEventEmitter,
    AsyncStateEventEmitter,
    StateEventListener,
    EventLogger,
    EventFilter,
    get_global_event_emitter,
    get_global_async_emitter,
    emit_global_event,
    emit_global_async_event,
)

# 自适应PID控制
from .adaptive_pid import (
    AdaptivePIDController,
    PPOAgent,
    create_adaptive_controller,
    compute_control_output,
)

# 监控指标收集
from .metrics_collector import (
    MetricsCollector,
    MetricsConfig,
    get_metrics_collector,
    init_metrics_collector,
    record_response_time,
    record_riemannian_calculation,
    record_event_processing,
    record_cache_operation,
    record_llm_call_performance,
)



__all__ = [
    # 女娲内核
    "NuwaKernel",
    "NuwaKernelAsync",  # 新增：导出异步内核名称
    "NuwaState",
    "BioRhythm",
    "PIDController",
    "MemoryCortex",
    "MemoryDreamer",
    "Personality",
    "SelfEvolutionState",
    # 自适应PID控制
    "AdaptivePIDController",
    "PPOAgent",
    "create_adaptive_controller",
    "compute_control_output",
    # 模型工具
    "EMBEDDING_MODEL_NAME",
    "DEFAULT_EMBEDDING_DIR",
    "ensure_embedding_model_dir",
    # 事件系统
    "StateEventType",
    "StateEvent",
    "StateEventEmitter",
    "AsyncStateEventEmitter",
    "StateEventListener",
    "EventLogger",
    "EventFilter",
    "get_global_event_emitter",
    "get_global_async_emitter",
    "emit_global_event",
    "emit_global_async_event",
    
    # 监控指标
    "MetricsCollector",
    "MetricsConfig",
    "get_metrics_collector",
    "init_metrics_collector",
    "record_response_time",
    "record_riemannian_calculation",
    "record_event_processing",
    "record_cache_operation",
    "record_llm_call_performance",
]

