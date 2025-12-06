"""
女娲核心引擎 (Nuwa Core Engine)

一个完整的、独立的核心引擎包，包含：
- 女娲内核：类人AI对话系统
- 太一引擎：小说创作逻辑推演系统（兼容保留）

核心模块：
- nuwa_kernel: 女娲内核，类人AI对话系统
- nuwa_state: 女娲状态管理
- drive_system: 生物节律系统
- memory_cortex: 记忆皮层
- memory_dreamer: 记忆梦境系统
- personality: 人格管理模块
- self_evolution: 自我进化模块
- self_evolution_state: 自我进化状态管理
- state_machine: 状态机模块（太一引擎）
- causality_judge: 因果律判官模块（太一引擎）
- momentum_tracker: 叙事势能模块（太一引擎）
- semantic_field: 语义场论核心算法
- engine: 引擎控制器（太一引擎）
"""

# 女娲内核相关
from .nuwa_kernel import NuwaKernel
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

# 太一引擎相关（兼容保留）
from .state_machine import ChapterNode, NarrativeState, extract_state, extract_semantic_state
from .causality_judge import scan_conflicts, ConflictReport
from .momentum_tracker import calculate_momentum, MomentumReport, PacingLevel
from .semantic_field import (
    vectorize_state,
    StateVector,
    calculate_potential_energy,
    evolve,
    inverse_collapse,
    build_collapse_prompt,
)
from .engine import TaiyiEngine

__all__ = [
    # 女娲内核
    "NuwaKernel",
    "NuwaState",
    "BioRhythm",
    "PIDController",
    "MemoryCortex",
    "MemoryDreamer",
    "Personality",
    "SelfEvolutionState",
    # 模型工具
    "EMBEDDING_MODEL_NAME",
    "DEFAULT_EMBEDDING_DIR",
    "ensure_embedding_model_dir",
    # 太一引擎（兼容保留）
    "ChapterNode",
    "NarrativeState",
    "extract_state",
    "extract_semantic_state",
    "scan_conflicts",
    "ConflictReport",
    "calculate_momentum",
    "MomentumReport",
    "PacingLevel",
    "TaiyiEngine",
    # 语义场论
    "vectorize_state",
    "StateVector",
    "calculate_potential_energy",
    "evolve",
    "inverse_collapse",
    "build_collapse_prompt",
]

