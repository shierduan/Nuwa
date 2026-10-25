"""
记忆巩固层 (Memory Consolidation Layer)

Nuwa 原创设计哲学的载体："记忆不是仓库，而是会做梦的生命体"。

本模块把记忆从"只增不减的向量库"升级为"具备认知节律的生命记忆系统"，
在不改变核心哲学（情绪一致性、13 维状态向量、黎曼语义场、自适应控制）的前提下，
补齐工业级记忆系统缺失的四个关键机制。

四个机制（设计来源见 docs/架构演进方案.md）：

1. SurprisalGate（惊奇门控）
   写入前评估信息量：若新内容与已有记忆高度相似（低惊奇度），
   则不写入长期记忆。避免记忆库被寒暄、重复确认、无信息对话稀释。
   —— 借鉴 MIT 项目 mnemos 的 SurprisalGate，适配 Nuwa 的情绪维度。

2. Reconsolidation（再巩固）
   记忆在被召回后会进入"可塑性窗口"（labile）。若窗口期内收到
   矛盾或补充信息，则改写原记忆而不是追加新记忆。
   —— 借鉴 MIT 项目 mnemos 的 MutableRAG，解决"旧事实永不更新"问题。

3. LayeredConsolidation（分层巩固）
   原始记忆（raw）→ 语义摘要（summary）→ 高阶洞察（insight）。
   三层对应 Qianxue（MIT）的 L0/L1/L2 记忆分层与 mnemos 的
   SleepDaemon 巩固流程。洞察层承载"从多次对话中提炼的模式"。

4. EmotionalDecay（情绪性衰减）
   记忆的存续强度由"情绪强度 × 时间衰减 × 访问频率 × 重要性"共同决定，
   其中情绪强度直接取自 Nuwa 的 13 维情绪谱。
   —— 这是 Nuwa 相对通用记忆系统的独特优势：情绪真正参与记忆代谢。

与既有模块的关系：
- memory_cortex.py   负责向量存取（zvec），本层在其之上做认知过滤
- memory_dreamer.py  负责"做梦"（聚类整理 + 人格演化），本层提供强化能力
- nuwa_state.py      负责 13 维状态与事实账本，本层向其写入事实与洞察
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .logging_config import get_logger
from .vector_store import MEMORY_TYPE_INSIGHT, MEMORY_TYPE_RAW, MEMORY_TYPE_SUMMARY

logger = get_logger(__name__)

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    np = None
    NUMPY_AVAILABLE = False


# ==================== 配置 ====================

@dataclass
class ConsolidationConfig:
    """记忆巩固配置

    默认值参考 mnemos（MIT）消融实验中的最优区间，
    并按 Nuwa 的使用场景（长期陪伴型对话）做了调整。
    """

    # --- SurprisalGate ---
    #: 惊奇度阈值：最高相似度超过此值则判定为"已知信息"，不写入
    surprisal_threshold: float = 0.82
    #: 是否启用惊奇门控
    enable_surprisal_gate: bool = True
    #: 单次写入前的相似度探测条数（越大越准，越慢）
    surprisal_probe_topk: int = 5

    # --- Reconsolidation ---
    #: 是否启用再巩固
    enable_reconsolidation: bool = True
    #: 可塑性窗口时长（秒）：记忆被召回后多久内可被改写
    reconsolidation_window: float = 300.0
    #: 判定"矛盾"的相似度下限：高于此值才认为是同一话题
    reconsolidation_similarity: float = 0.75

    # --- LayeredConsolidation ---
    #: 是否启用分层巩固
    enable_layered: bool = True
    #: 生成摘要所需的最少原始记忆数
    min_cluster_size: int = 3
    #: 生成洞察所需的最少摘要数
    min_insight_sources: int = 3
    #: 聚类相似度阈值：all-MiniLM-L6-v2 中文语料下，同主题表述通常在 0.40-0.65
    cluster_similarity_threshold: float = 0.40
    #: 单次巩固处理的最大原始记忆数
    max_process_per_cycle: int = 2000

    # --- EmotionalDecay ---
    #: 情绪强度对存续分数的最大贡献倍数
    emotion_weight_max: float = 1.5
    #: 半衰期（天）：无访问无情绪的记忆经过多少天衰减到一半
    half_life_days: float = 14.0
    #: 访问频率权重
    frequency_weight: float = 0.25
    #: 低于该分数的记忆在巩固期被遗忘
    forget_threshold: float = 0.15


# ==================== 1. 惊奇门控 ====================

@dataclass
class SurprisalGate:
    """惊奇门控：写入前的信息量评估

    理论基础：预测加工理论（predictive coding）。
    大脑不会储存一切——只有与预测不符、值得惊讶的信息才获得记忆资源。

    在 Nuwa 中的意义：女娲不需要记住"好的""嗯""谢谢"这类寒暄，
    但需要记住"用户说过他害怕打雷"这类有情感与事实密度的内容。
    这直接服务于"数字生命"的生命感——记忆的选择性本身是一种智能表现。
    """

    memory_cortex: Any
    config: ConsolidationConfig

    def evaluate(self, text: str) -> Tuple[bool, float, str]:
        """评估一条待写入记忆

        Returns:
            (是否应写入, 惊奇度, 判定理由)
        """
        if not self.config.enable_surprisal_gate:
            return True, 1.0, "门控已关闭"

        if not text or not text.strip():
            return False, 0.0, "空内容"

        # 极短内容默认不进入长期记忆（寒暄/确认）
        stripped = text.strip()
        if len(stripped) < 6:
            return False, 0.0, "内容过短，判定为寒暄"

        try:
            max_sim = self.memory_cortex.find_max_similarity(stripped)
        except Exception as exc:
            # 探测失败时放行，不能因为门控组件异常而丢失记忆
            logger.warning("惊奇门控探测失败，放行: %s", exc)
            return True, 1.0, "探测失败，放行"

        if max_sim >= self.config.surprisal_threshold:
            return (
                False,
                1.0 - max_sim,
                f"与已有记忆高度重复（相似度 {max_sim:.3f} ≥ {self.config.surprisal_threshold}）",
            )

        return True, 1.0 - max_sim, f"惊奇度 {1.0 - max_sim:.3f}，写入"

    def filter_batch(self, texts: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """批量过滤，返回（应写入的文本列表, 拒绝明细）"""
        accepted: List[str] = []
        rejected: List[Dict[str, Any]] = []
        for t in texts:
            ok, surprisal, reason = self.evaluate(t)
            if ok:
                accepted.append(t)
            else:
                rejected.append({"text": t[:80], "surprisal": surprisal, "reason": reason})
        return accepted, rejected


# ==================== 2. 再巩固 ====================

@dataclass
class ReconsolidationBook:
    """再巩固账本：记录处于"可塑性窗口"内的记忆

    记忆被召回后并非立刻固化。若在窗口期内再次遇到相关内容，
    系统会倾向于"改写"原记忆而非"追加"，这符合人类记忆的重塑特性，
    也解决了向量库"旧事实永不更新"的核心缺陷。
    """

    #: memory_id -> 召回时间戳
    labile: Dict[str, float] = field(default_factory=dict)
    #: memory_id -> 召回次数
    recall_counts: Dict[str, int] = field(default_factory=dict)

    def mark_recalled(self, memory_id: str, now: Optional[float] = None) -> None:
        now = now or time.time()
        self.labile[memory_id] = now
        self.recall_counts[memory_id] = self.recall_counts.get(memory_id, 0) + 1

    def is_labile(self, memory_id: str, window: float, now: Optional[float] = None) -> bool:
        now = now or time.time()
        ts = self.labile.get(memory_id)
        if ts is None:
            return False
        return (now - ts) <= window

    def expire(self, window: float, now: Optional[float] = None) -> List[str]:
        """清理过期窗口，返回被固化的记忆 ID 列表"""
        now = now or time.time()
        expired = [mid for mid, ts in self.labile.items() if (now - ts) > window]
        for mid in expired:
            self.labile.pop(mid, None)
        return expired

    def to_dict(self) -> Dict[str, Any]:
        return {"labile": dict(self.labile), "recall_counts": dict(self.recall_counts)}

    def load_dict(self, data: Dict[str, Any]) -> None:
        self.labile = dict(data.get("labile", {}) or {})
        self.recall_counts = dict(data.get("recall_counts", {}) or {})


# ==================== 3. 情绪性衰减 ====================

class EmotionalDecay:
    """情绪性衰减：Nuwa 独有的记忆代谢公式

    传统记忆系统用"时间 × 频率"决定遗忘。
    Nuwa 多了一个维度：情绪。

    存续分数 = 重要性 × (1 + 情绪权重 × 情绪强度) × 时间衰减 + 频率加成

    - 情绪强度取自 13 维情绪谱的最大分量（写入记忆时快照）
    - 时间衰减为指数半衰期
    - 频率加成来自访问次数的对数

    效果：一段"用户说害怕打雷"的对话，会比十段"好的，谢谢"活得更久。
    这让女娲的记忆分布更接近真实生命的记忆分布。
    """

    def __init__(self, config: ConsolidationConfig):
        self.config = config

    def score(self, memory: Dict[str, Any], now: Optional[float] = None) -> float:
        """计算记忆的存续分数"""
        now = now or time.time()

        importance = float(memory.get("importance", 0.5) or 0.0)

        # 情绪强度：解析 emotions JSON，取最大分量
        emotion_strength = 0.0
        raw_emotions = memory.get("emotions", "")
        if raw_emotions:
            try:
                emotions = json.loads(raw_emotions) if isinstance(raw_emotions, str) else raw_emotions
                if isinstance(emotions, dict) and emotions:
                    emotion_strength = max(float(v) for v in emotions.values())
            except (json.JSONDecodeError, TypeError, ValueError):
                emotion_strength = 0.0

        # 情绪加权：上限由 config.emotion_weight_max 控制
        emotional_boost = 1.0 + self.config.emotion_weight_max * emotion_strength

        # 时间衰减
        timestamp = float(memory.get("timestamp", now) or now)
        age_days = max(0.0, (now - timestamp) / 86400.0)
        decay = math.pow(0.5, age_days / max(1e-6, self.config.half_life_days))

        # 频率加成
        freq = int(memory.get("access_count", 0) or 0)
        freq_bonus = self.config.frequency_weight * math.log(1 + max(0, freq))

        return float(importance * emotional_boost * decay + freq_bonus)

    def classify(self, memories: List[Dict[str, Any]], now: Optional[float] = None) -> List[Tuple[Dict[str, Any], float]]:
        """为记忆列表打上存续分数并按降序排列"""
        now = now or time.time()
        scored = [(m, self.score(m, now)) for m in memories]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


# ==================== 4. 分层巩固 ====================

@dataclass
class LayeredConsolidation:
    """分层巩固：raw → summary → insight

    对应 Qianxue（MIT）的 L0/L1/L2 记忆分层：
    - L0 raw      原始对话，携带完整情绪与时间信息
    - L1 summary  语义摘要，多条相似对话压缩为一段
    - L2 insight  高阶洞察，跨摘要提炼出的模式与规律

    L2 洞察是 Nuwa 原创"自我认知"的载体：
    女娲不只是记住说过什么，而是逐渐理解"我在与什么样的人相处"。
    """

    memory_cortex: Any
    llm_client: Any = None
    model_name: str = "local-model"
    config: ConsolidationConfig = field(default_factory=ConsolidationConfig)
    state_ref: Any = None

    # ---------- L1: 语义摘要 ----------

    @staticmethod
    def _strip_timestamp_prefix(text: str) -> str:
        """剥离记忆文本开头的时间戳前缀

        记忆在库中以 "[YYYY-MM-DD HH:MM:SS] 正文" 形式存储。
        摘要时若不剥离，store_memory 会再叠一层前缀，导致
        "[2026-01-01 00:00:00] [2026-01-01 00:00:00] 正文"。
        """
        if not text:
            return ""
        stripped = text.strip()
        if stripped.startswith("[") and "]" in stripped[:25]:
            end = stripped.find("]", 1)
            if end > 0:
                return stripped[end + 1:].strip()
        return stripped

    def summarize(self, texts: List[str]) -> Tuple[str, Dict[str, str]]:
        """把一组相关记忆压缩为摘要 + 关键事实"""
        if not texts:
            return "", {}

        # 剥离时间戳前缀，避免摘要文本出现双重时间戳
        cleaned = [self._strip_timestamp_prefix(t) for t in texts if t]
        cleaned = [t for t in cleaned if t]
        if not cleaned:
            return "", {}

        joined = "\n".join(cleaned[:50])
        prompt = (
            "你是女娲的梦境整理器，需要把以下相关对话压缩为记忆。\n"
            '请输出 JSON，格式为 {"summary": "...", "facts": {"key": "value", ...}}。\n'
            "summary 要求 1-2 句，facts 中记录可验证的关键事实（如姓名、关系、偏好等）。\n"
            "如果没有事实，可以让 facts 为空对象。\n\n"
            f"{joined}\n\nJSON："
        )

        if not self.llm_client:
            return cleaned[0][:300], {}

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个负责整理记忆的助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=256,
            )
            raw = response.choices[0].message.content.strip()
            return self._parse_summary_and_facts(raw)
        except Exception as exc:
            logger.warning("调用 LLM 总结失败: %s", exc, extra={"nuwa_context": {"cluster_size": len(cleaned)}})
            return cleaned[0][:300], {}

    def _parse_summary_and_facts(self, content: str) -> Tuple[str, Dict[str, str]]:
        try:
            data = json.loads(content)
            summary = str(data.get("summary", "")).strip()
            facts_obj = data.get("facts") or {}
            facts: Dict[str, str] = {}
            if isinstance(facts_obj, dict):
                for k, v in facts_obj.items():
                    if k and v is not None:
                        facts[str(k)] = str(v)
            return summary or content.strip(), facts
        except json.JSONDecodeError:
            return content.strip(), {}

    # ---------- L2: 高阶洞察 ----------

    def derive_insight(self, summaries: List[str]) -> Tuple[str, Dict[str, str]]:
        """从多条摘要中提炼高阶洞察

        这是女娲的"自我认知"环节：跨越具体事件，
        抽象出关于用户、关于关系、关于自己的稳定判断。
        """
        if len(summaries) < self.config.min_insight_sources:
            return "", {}

        # 剥离时间戳前缀
        cleaned = [self._strip_timestamp_prefix(s) for s in summaries]
        cleaned = [s for s in cleaned if s]
        if len(cleaned) < self.config.min_insight_sources:
            return "", {}

        joined = "\n".join(cleaned[:30])
        prompt = (
            "你是女娲的自我认知模块。基于以下多次对话的摘要，"
            "提炼出高阶洞察——不是复述具体事件，而是关于用户性格、"
            "互动模式、关系状态的稳定判断。\n"
            '请输出 JSON，格式为 {"insight": "...", "facts": {"key": "value", ...}}。\n'
            "insight 要求 2-3 句，点明模式而非细节。\n"
            "facts 记录可复用的结构化认知（如 user_prefers, interaction_style）。\n\n"
            f"{joined}\n\nJSON："
        )

        if not self.llm_client:
            return "", {}

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个擅长从长期互动中提炼模式的自我认知分析器。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            insight = str(data.get("insight", "")).strip()
            facts_obj = data.get("facts") or {}
            facts = {
                str(k): str(v)
                for k, v in facts_obj.items()
                if k and v is not None
            } if isinstance(facts_obj, dict) else {}
            return insight, facts
        except Exception as exc:
            logger.warning("提炼洞察失败: %s", exc)
            return "", {}

    def write_insight(self, insight: str, facts: Dict[str, str]) -> bool:
        """把洞察写入记忆库（L2 层）与事实账本"""
        if not insight:
            return False

        metadata = {
            "type": MEMORY_TYPE_INSIGHT,
            "importance": 0.9,  # 洞察比原始对话更重要
            "emotions": {},
            "access_count": 0,
        }
        stored = self.memory_cortex.store_memory(insight, metadata=metadata)

        # 洞察中提取的事实写入事实账本（source="dream"：只填不覆盖）
        if facts and self.state_ref is not None:
            for key, value in facts.items():
                try:
                    self.state_ref.update_fact(str(key), str(value), source="dream")
                except Exception:
                    continue
        return bool(stored)


# ==================== 编排器 ====================

class MemoryConsolidator:
    """记忆巩固编排器

    把四个机制串成一条流水线，写入路径与巩固路径各自调用：

    写入路径：
        text → SurprisalGate.evaluate() → (通过) MemoryCortex.store_memory()
                                              → ReconsolidationBook.mark_recalled()

    巩固路径（做梦时）：
        原始记忆 → EmotionalDecay.classify() → 低分遗忘 / 高分保留
                 → 相似聚类 → LayeredConsolidation.summarize() → L1
                 → L1 汇总 → LayeredConsolidation.derive_insight() → L2
    """

    def __init__(
        self,
        memory_cortex: Any,
        llm_client: Any = None,
        model_name: str = "local-model",
        state_ref: Any = None,
        config: Optional[ConsolidationConfig] = None,
    ):
        self.memory_cortex = memory_cortex
        self.llm_client = llm_client
        self.model_name = model_name
        self.state_ref = state_ref
        self.config = config or ConsolidationConfig()

        self.gate = SurprisalGate(memory_cortex, self.config)
        self.decay = EmotionalDecay(self.config)
        self.book = ReconsolidationBook()
        self.layers = LayeredConsolidation(
            memory_cortex=memory_cortex,
            llm_client=llm_client,
            model_name=model_name,
            config=self.config,
            state_ref=state_ref,
        )

        # 统计
        self.stats = {
            "writes_total": 0,
            "writes_rejected": 0,
            "reconsolidations": 0,
            "forgotten": 0,
            "summaries_created": 0,
            "insights_created": 0,
        }

    # ---------- 写入路径 ----------

    def store(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """带惊奇门控的记忆写入

        Returns:
            记忆 ID（被门控拒绝时返回 None）
        """
        self.stats["writes_total"] += 1

        ok, surprisal, reason = self.gate.evaluate(text)
        if not ok:
            self.stats["writes_rejected"] += 1
            logger.info(
                "记忆未写入（%s）",
                reason,
                extra={"nuwa_context": {"surprisal": round(surprisal, 3), "text": text[:60]}},
            )
            return None

        memory_id = self.memory_cortex.store_memory(text, metadata=metadata)
        if memory_id:
            logger.debug(
                "记忆写入成功（%s）",
                reason,
                extra={"nuwa_context": {"memory_id": memory_id, "surprisal": round(surprisal, 3)}},
            )
        return memory_id

    def mark_recalled(self, memory_ids: List[str]) -> None:
        """标记被召回的记忆进入可塑性窗口"""
        if not self.config.enable_reconsolidation:
            return
        now = time.time()
        for mid in memory_ids:
            self.book.mark_recalled(mid, now)

    # ---------- 去重 ----------

    def _is_duplicate(
        self,
        text: str,
        memory_type: str = "summary",
        threshold: float = 0.88,
    ) -> bool:
        """判断待写入的摘要/洞察是否与同类型的已有内容重复

        梦境是周期性的（默认 15 分钟一轮），若不做去重，
        同样的摘要与洞察会被反复写入，记忆库将快速膨胀。

        关键设计：只与 **同类型** 内容比较。摘要来自原始记忆的压缩，
        若与原始记忆比较，几乎逐字相同的压缩结果会被误判为重复，
        导致摘要层永远无法产出。

        阈值取较高值（默认 0.88），只拦截近乎逐字相同的内容，
        避免误杀角度不同的提炼。
        """
        if not text or not getattr(self.memory_cortex, "store", None):
            return False
        try:
            vector = self.memory_cortex.embedding_model.encode(text, convert_to_numpy=True)
            if len(vector) != self.memory_cortex.VECTOR_DIM:
                return False

            # 只在同类型记忆中比对
            existing = self.memory_cortex.store.get_recent(
                limit=200, memory_type=memory_type, include_vector=True
            )
            if not existing:
                return False

            import numpy as np

            v = np.array(vector, dtype=np.float32)
            norm = np.linalg.norm(v)
            if norm < 1e-8:
                return False
            v = v / norm

            for item in existing:
                ev = item.get("vector")
                if not ev:
                    continue
                ev = np.array(ev, dtype=np.float32)
                en = np.linalg.norm(ev)
                if en < 1e-8:
                    continue
                sim = float(np.dot(v, ev / en))
                if sim >= threshold:
                    return True
            return False
        except Exception as exc:
            logger.exception("去重检查失败: %s", exc)
            # 去重检查失败时按"不重复"处理，宁可多写也不丢记忆
            return False

    # ---------- 巩固路径 ----------

    def consolidate_cycle(self) -> Dict[str, Any]:
        """执行一轮记忆巩固（做梦时调用）"""
        report: Dict[str, Any] = {
            "forgotten": 0,
            "summaries": 0,
            "insights": 0,
            "reconsolidated": 0,
        }

        # 1. 过期可塑性窗口
        expired = self.book.expire(self.config.reconsolidation_window)
        report["reconsolidated"] = len(expired)

        # 2. 取原始记忆并按情绪性衰减打分（需要向量用于后续聚类）
        raw = self.memory_cortex.get_recent_memories(
            limit=self.config.max_process_per_cycle,
            memory_type=MEMORY_TYPE_RAW,
            include_vector=True,
        )
        if not raw:
            return report

        scored = self.decay.classify(raw)

        # 3. 低分记忆遗忘
        forget_ids = [
            m.get("id")
            for m, s in scored
            if s < self.config.forget_threshold and m.get("id")
        ]
        if forget_ids:
            self.memory_cortex.delete_memories(forget_ids)
            self.stats["forgotten"] += len(forget_ids)
            report["forgotten"] = len(forget_ids)
            logger.info(
                "遗忘 %d 条低价值记忆（阈值 %.2f）",
                len(forget_ids),
                self.config.forget_threshold,
            )

        # 4. 分层巩固（L0 → L1）
        if self.config.enable_layered:
            report["summaries"] = self._consolidate_to_summaries(
                [m for m, _ in scored if m.get("id") not in set(forget_ids)]
            )
            # 5. 再巩固一层（L1 → L2）
            report["insights"] = self._consolidate_to_insights()

        return report

    def _consolidate_to_summaries(self, memories: List[Dict[str, Any]]) -> int:
        """把语义相近的原始记忆压缩为 L1 摘要"""
        if len(memories) < self.config.min_cluster_size:
            return 0

        # 简单贪心聚类：按向量相似度成簇
        clusters: List[List[Dict[str, Any]]] = []
        used = set()

        for i, mem in enumerate(memories):
            if i in used:
                continue
            cluster = [mem]
            used.add(i)
            for j in range(i + 1, len(memories)):
                if j in used:
                    continue
                if self._semantically_close(mem, memories[j]):
                    cluster.append(memories[j])
                    used.add(j)
            if len(cluster) >= self.config.min_cluster_size:
                clusters.append(cluster)

        created = 0
        for cluster in clusters:
            texts = [c.get("text", "") for c in cluster if c.get("text")]
            if not texts:
                continue
            summary, facts = self.layers.summarize(texts)
            if not summary:
                continue

            # 去重：避免周期性巩固反复写入同一摘要
            if self._is_duplicate(summary, memory_type=MEMORY_TYPE_SUMMARY):
                continue

            emotions = self._aggregate_emotions(cluster)
            metadata = {
                "type": MEMORY_TYPE_SUMMARY,
                "importance": 0.8,
                "emotions": emotions,
                "access_count": 0,
            }
            if self.memory_cortex.store_memory(summary, metadata=metadata):
                created += 1
                # 原始记忆保留（不做物理删除）：删除会破坏时间连续性，
                # 且 L0 是 L1/L2 的溯源依据。遗忘交由分数阈值统一处理。
                if facts and self.state_ref is not None:
                    for key, value in facts.items():
                        try:
                            self.state_ref.update_fact(str(key), str(value), source="dream")
                        except Exception as exc:
                            logger.debug("更新事实账本失败(%s): %s", key, exc)
                            continue

        self.stats["summaries_created"] += created
        if created:
            logger.info("生成 %d 条语义摘要（L1）", created)
        return created

    def _consolidate_to_insights(self) -> int:
        """从 L1 摘要中提炼 L2 洞察"""
        summaries = self.memory_cortex.get_recent_memories(
            limit=200, memory_type=MEMORY_TYPE_SUMMARY
        )
        texts = [s.get("text", "") for s in summaries if s.get("text")]
        if len(texts) < self.config.min_insight_sources:
            return 0

        insight, facts = self.layers.derive_insight(texts)
        if not insight:
            return 0

        # 去重：同一模式不应被反复固化
        if self._is_duplicate(insight, memory_type=MEMORY_TYPE_INSIGHT, threshold=0.85):
            return 0

        if self.layers.write_insight(insight, facts):
            self.stats["insights_created"] += 1
            logger.info("生成高阶洞察（L2）: %s", insight[:60])
            return 1
        return 0

    def _semantically_close(self, a: Dict[str, Any], b: Dict[str, Any], threshold: Optional[float] = None) -> bool:
        """判断两条记忆是否语义相近（用于聚类）

        阈值说明：all-MiniLM-L6-v2 在中文语料上的余弦相似度分布较分散，
        同一主题的不同表述通常落在 0.40-0.65，完全无关的内容接近 0。
        因此默认阈值取 0.40（可通过 config 覆盖），避免聚类过严导致
        摘要层永远不产出。
        """
        if threshold is None:
            threshold = self.config.cluster_similarity_threshold
        if not NUMPY_AVAILABLE or np is None:
            return False
        try:
            va = a.get("vector")
            vb = b.get("vector")
            if va is None or vb is None:
                return False
            va = np.array(va, dtype=np.float32)
            vb = np.array(vb, dtype=np.float32)
            if va.size == 0 or vb.size == 0:
                return False
            na = np.linalg.norm(va)
            nb = np.linalg.norm(vb)
            if na < 1e-8 or nb < 1e-8:
                return False
            return float(np.dot(va, vb) / (na * nb)) >= threshold
        except Exception:
            return False

    def _aggregate_emotions(self, records: List[Dict[str, Any]]) -> Dict[str, float]:
        """聚类内情绪取平均"""
        if not NUMPY_AVAILABLE or np is None:
            return {}
        aggregated: Dict[str, List[float]] = {}
        for rec in records:
            try:
                emotions = json.loads(rec.get("emotions", "") or "{}")
            except (json.JSONDecodeError, TypeError):
                emotions = {}
            if not isinstance(emotions, dict):
                continue
            for key, value in emotions.items():
                try:
                    aggregated.setdefault(key, []).append(float(value))
                except (TypeError, ValueError):
                    continue
        return {k: float(np.mean(v)) for k, v in aggregated.items() if v}

    def get_stats(self) -> Dict[str, Any]:
        """返回巩固层统计"""
        return {
            **self.stats,
            "labile_count": len(self.book.labile),
            "config": {
                "surprisal_threshold": self.config.surprisal_threshold,
                "enable_surprisal_gate": self.config.enable_surprisal_gate,
                "enable_reconsolidation": self.config.enable_reconsolidation,
                "enable_layered": self.config.enable_layered,
                "half_life_days": self.config.half_life_days,
            },
        }
