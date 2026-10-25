"""
Nuwa核心模块 - 统一异步架构导出

提供向后兼容的导入路径
"""

# 导出统一异步内核
# 导出缓存管理器
from .cache_manager import CacheManager, get_cache_manager
from .drive_system import BioRhythm, PIDController
from .memory_cortex import MemoryCortex
from .memory_dreamer import MemoryDreamer
from .nuwa_kernel_async import NuwaKernelAsync

# 导出其他核心模块
from .nuwa_state import NuwaState
from .personality import Personality
from .riemannian_semantic_field import (
    StateVector,
    calculate_gradient,
    calculate_potential_energy,
    evolve,
    inverse_collapse,
    vectorize_state,
)
from .self_evolution_state import SelfEvolutionState

# 导出同步兼容层
from .sync_compat import AsyncLLMClient, SyncLLMClient, run_sync

__all__ = [
    # 统一异步架构
    "NuwaKernelAsync",
    "CacheManager",
    "get_cache_manager",
    "AsyncLLMClient",
    "SyncLLMClient",
    "run_sync",

    # 原有核心模块
    "NuwaState",
    "BioRhythm",
    "PIDController",
    "MemoryCortex",
    "vectorize_state",
    "StateVector",
    "calculate_potential_energy",
    "calculate_gradient",
    "evolve",
    "inverse_collapse",
    "MemoryDreamer",
    "Personality",
    "SelfEvolutionState",
]
