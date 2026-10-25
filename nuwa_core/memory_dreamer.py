"""
Memory Dreamer Module

实现记忆压缩与遗忘机制（做梦系统）。
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .nuwa_state import NuwaState

import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN

from .logging_config import get_logger
from .vector_store import MEMORY_TYPE_RAW, MEMORY_TYPE_SUMMARY

logger = get_logger(__name__)


class MemoryDreamer:
    """
    MemoryDreamer: 负责记忆整理（做梦）。

    - 遗忘低价值记忆
    - 压缩相似记忆为摘要
    - 铭刻高价值记忆
    """

    HALF_LIFE_DAYS = 7.0
    ALPHA_EMOTION = 0.5
    BETA_FREQ = 0.2
    MAX_MEMORIES = 1000

    def __init__(self, memory_cortex, llm_client=None, model_name: str = "local-model", state: Optional["NuwaState"] = None):
        self.memory_cortex = memory_cortex
        self.llm_client = llm_client
        self.model_name = model_name
        self.state_ref = state

    def start_dreaming(self, limit: int = MAX_MEMORIES):
        """启动做梦流程"""
        raw_memories = self.memory_cortex.get_recent_memories(limit=limit, memory_type=MEMORY_TYPE_RAW)
        if not raw_memories:
            logger.info("没有可整理的记忆。")
            return

        # 语义垃圾回收：定义低质量回复关键词列表
        BAD_PHRASES = [
            "记忆功能还在学习中",
            "很抱歉",
            "我无法",
            "作为AI",
            "我记不清了",
            "我是AI模型",
            "记忆系统正在学习",
            "无法回答",
            "无法提供",
            "不具备",
            "不支持",
            "不了解"
        ]

        # 第一步：语义垃圾回收 - 删除低质量记忆
        semantic_gc_ids = []
        for record in raw_memories:
            text = record.get("text", "").lower()
            # 检查是否包含低质量关键词
            if any(phrase.lower() in text for phrase in BAD_PHRASES):
                rec_id = record.get("id")
                if rec_id:
                    semantic_gc_ids.append(rec_id)

        # 执行语义垃圾回收
        if semantic_gc_ids:
            unique_gc_ids = sorted(set(semantic_gc_ids))
            logger.info("语义垃圾回收：删除 %d 条低质量记忆", len(unique_gc_ids))
            try:
                self.memory_cortex.delete_memories(unique_gc_ids)
                logger.debug("低质量记忆已清理。")
            except Exception as e:
                logger.exception("语义垃圾回收失败: %s", e)

        # 第二步：继续处理剩余记忆
        vectors = []
        valid_records = []
        bad_ids = []  # 记录在本轮中检测到的"坏向量"记忆，用于一并删除
        for record in raw_memories:
            # 如果已经被语义垃圾回收删除，跳过
            rec_id = record.get("id")
            if rec_id and rec_id in semantic_gc_ids:
                continue

            vec = record.get("vector")
            # 显式检查为空/None/长度为0
            if vec is None:
                continue
            if isinstance(vec, (list, tuple)) and len(vec) == 0:
                continue
            arr = np.array(vec, dtype=np.float32)
            if arr.size == 0:
                continue
            # 过滤包含 NaN / Inf 的向量，避免 DBSCAN 报错
            if not np.isfinite(arr).all():
                text_preview = str(record.get("text", "")).replace("\n", " ")[:60]
                logger.debug("跳过包含 NaN/Inf 的向量记忆: %s", text_preview)
                if rec_id:
                    bad_ids.append(rec_id)
                continue
            vectors.append(arr)
            valid_records.append(record)

        if len(valid_records) < 2:
            logger.info("记忆数量不足，跳过整理。")
            return

        vectors = np.stack(vectors)
        # 再次在矩阵层面过滤含 NaN/Inf 的样本，双保险
        finite_mask = np.isfinite(vectors).all(axis=1)
        if not finite_mask.all():
            removed = int((~finite_mask).sum())
            logger.info("发现 %d 条含 NaN/Inf 的向量，在聚类前丢弃。", removed)
            # 记录这些记录的 id，后续统一从记忆库中删除
            for rec, keep in zip(valid_records, finite_mask, strict=False):
                if not keep and rec.get("id"):
                    bad_ids.append(rec["id"])
            vectors = vectors[finite_mask]
            valid_records = [rec for rec, keep in zip(valid_records, finite_mask, strict=False) if keep]

        if len(valid_records) < 2:
            logger.info("清洗后记忆数量不足，跳过整理。")
            return

        # 过滤掉范数为 0 的向量（纯零向量会在 cosine/距离计算中产生数值问题）
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        nonzero_mask = norms.squeeze(axis=1) > 0
        if not nonzero_mask.all():
            removed = int((~nonzero_mask).sum())
            logger.info("发现 %d 条零向量，在聚类前丢弃。", removed)
            for rec, keep in zip(valid_records, nonzero_mask, strict=False):
                if not keep and rec.get("id"):
                    bad_ids.append(rec["id"])
            vectors = vectors[nonzero_mask]
            valid_records = [rec for rec, keep in zip(valid_records, nonzero_mask, strict=False) if keep]

        # 如果本轮检测到了坏向量，直接从 LanceDB 中删除，避免污染后续检索
        if bad_ids:
            unique_bad_ids = sorted(set(bad_ids))
            logger.info("本轮共检测到 %d 条坏向量记忆，正在从记忆库中删除...", len(unique_bad_ids))
            try:
                self.memory_cortex.delete_memories(unique_bad_ids)
                logger.debug("坏向量记忆已清理。")
            except Exception as e:
                logger.exception("清理坏向量记忆失败: %s", e)

        if len(valid_records) < 2:
            logger.info("过滤零向量后记忆数量不足，跳过整理。")
            return

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized = vectors / norms

        # 使用欧式距离而不是 cosine，避免在 pdist 内部再次对零向量做 0/0 归一化
        distance_matrix = squareform(pdist(normalized, metric="euclidean"))
        if not np.isfinite(distance_matrix).all():
            logger.warning("距离矩阵仍包含 NaN/Inf，放弃本轮整理以保证安全。")
            return
        clustering = DBSCAN(metric="precomputed", eps=0.3, min_samples=2).fit(distance_matrix)
        labels = clustering.labels_

        unique_labels = set(labels)
        logger.info("开始整理 %d 条记忆，共 %d 个簇。", len(valid_records), len(unique_labels))

        for label in unique_labels:
            indices = np.where(labels == label)[0]
            cluster_records = [valid_records[i] for i in indices]
            scores = [self._calculate_score(rec) for rec in cluster_records]
            avg_score = float(np.mean(scores)) if scores else 0.0

            if label == -1 or avg_score < 0.2:
                self._handle_forgetting(cluster_records)
            elif 0.2 <= avg_score < 0.8:
                self._handle_compression(cluster_records)
            else:
                logger.info("铭刻高价值记忆簇 (score=%.2f)，保留 %d 条。", avg_score, len(cluster_records))

    def _calculate_score(self, mem: Dict[str, Any]) -> float:
        """按照指定公式计算记忆得分"""
        importance = mem.get("importance", 0.5)

        emotions = {}
        try:
            emotions = json.loads(mem.get("emotions", "") or "{}")
        except json.JSONDecodeError:
            emotions = {}
        emotion_strength = max(emotions.values()) if emotions else 0.0

        timestamp = float(mem.get("timestamp", time.time()))
        t_days = (time.time() - timestamp) / 86400.0
        decay = np.exp(- (np.log(2) / self.HALF_LIFE_DAYS) * t_days)

        freq = mem.get("access_count", 1) or 1
        freq_bonus = np.log(1 + freq)

        score = (importance * (1 + self.ALPHA_EMOTION * emotion_strength)) * decay + (self.BETA_FREQ * freq_bonus)
        return float(score)

    def _handle_forgetting(self, records: List[Dict[str, Any]]):
        if not records:
            return
        ids = [rec.get("id") for rec in records if rec.get("id")]
        if not ids:
            return
        logger.info("Forgetting noise memories (%d 条)...", len(ids))
        self.memory_cortex.delete_memories(ids)

    def _handle_compression(self, records: List[Dict[str, Any]]):
        if not records:
            return
        texts = [rec.get("text", "") for rec in records if rec.get("text")]
        if not texts:
            return
        summary, facts = self._summarize_cluster_texts(texts)
        if not summary:
            logger.warning("压缩失败，跳过。")
            return
        emotions = self._aggregate_emotions(records)
        metadata = {
            "type": MEMORY_TYPE_SUMMARY,
            "importance": 1.0,
            "emotions": emotions,
            "access_count": 0,
        }
        self.memory_cortex.store_memory(summary, metadata=metadata)
        ids = [rec.get("id") for rec in records if rec.get("id")]
        self.memory_cortex.delete_memories(ids)
        logger.info("压缩 %d 条记忆为摘要。", len(records))
        self._record_fact_updates(facts)

    def _summarize_cluster_texts(self, texts: List[str]) -> Tuple[str, Dict[str, str]]:
        if not texts:
            return "", {}
        joined_text = "\n".join(texts[:50])  # 控制长度
        prompt = (
            "你是女娲的梦境整理器，需要把以下相关对话压缩为记忆。"
            "请输出 JSON，格式为 {\"summary\": \"...\", \"facts\": {\"key\": \"value\", ...}}。"
            "summary 要求 1-2 句，facts 中记录可验证的关键事实（如姓名、关系、偏好等）。"
            "如果没有事实，可以让 facts 为空对象。\n\n"
            f"{joined_text}\n\nJSON："
        )
        if not self.llm_client:
            # 无 LLM 时采用简化策略
            return texts[0][:300], {}
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
            raw_content = response.choices[0].message.content.strip()
            summary, facts = self._parse_summary_and_facts(raw_content)
            return summary, facts
        except Exception as e:
            logger.exception("调用 LLM 总结失败: %s", e)
            return texts[0][:300], {}

    def _parse_summary_and_facts(self, content: str) -> Tuple[str, Dict[str, str]]:
        try:
            data = json.loads(content)
            summary = str(data.get("summary", "")).strip()
            facts_obj = data.get("facts") or {}
            facts: Dict[str, str] = {}
            if isinstance(facts_obj, dict):
                for key, value in facts_obj.items():
                    if key and value is not None:
                        facts[str(key)] = str(value)
            return summary or content.strip(), facts
        except json.JSONDecodeError:
            # 尝试从文本中提取 summary: 和 facts:
            summary = content.strip()
            return summary, {}

    def _record_fact_updates(self, facts: Dict[str, str]):
        if not facts:
            return
        if not self.state_ref:
            logger.warning("无法写入事实账本（state 引用不存在）。")
            return

        success_count = 0
        total = len(facts)
        for key, value in facts.items():
            if not key:
                continue
            if self.state_ref.update_fact(str(key), str(value), source="dream"):
                success_count += 1
        logger.info("尝试写入 %d 条事实，成功 %d 条（重复或冲突已忽略）。", total, success_count)

    def _aggregate_emotions(self, records: List[Dict[str, Any]]) -> Dict[str, float]:
        aggregated: Dict[str, List[float]] = {}
        for rec in records:
            try:
                emotions = json.loads(rec.get("emotions", "") or "{}")
            except json.JSONDecodeError:
                emotions = {}
            for key, value in emotions.items():
                aggregated.setdefault(key, []).append(float(value))
        return {k: float(np.mean(v)) for k, v in aggregated.items()}

    def evolve_character(self):
        """
        实现时间加权人格演化算法 (TWPE - Temporal Weighted Personality Evolution)

        从历史记忆中提取不同时间段的特征，更新演化人格数据。

        时间分桶逻辑（基于 time.time() - timestamp）：
        - bucket_1d: < 86400s (最近1天)
        - bucket_1m: < 30 * 86400s but > 1d (最近1个月，但超过1天)
        - bucket_3m: < 90 * 86400s but > 1m (最近3个月，但超过1个月)
        - bucket_1y: > 90 * 86400s (超过3个月)
        """
        if not self.memory_cortex or not self.state_ref:
            logger.warning("无法执行人格演化：memory_cortex 或 state_ref 不存在")
            return

        if not self.llm_client:
            logger.warning("无法执行人格演化：LLM 客户端不可用")
            return

        try:
            # 1. 获取最近的记忆
            recent_memories = self.memory_cortex.get_recent_memories(limit=2000, memory_type=MEMORY_TYPE_RAW)
            if not recent_memories:
                logger.info("没有记忆可用于人格演化")
                return

            # 2. 按时间戳分组到4个时间段
            current_time = time.time()
            one_day_seconds = 86400
            one_month_seconds = 30 * 86400
            three_months_seconds = 90 * 86400

            bucket_1d = []   # < 86400s
            bucket_1m = []   # < 30 * 86400s but > 1d
            bucket_3m = []   # < 90 * 86400s but > 1m
            bucket_1y = []   # > 90 * 86400s

            # 将记忆分配到对应的时间桶
            for mem in recent_memories:
                timestamp = float(mem.get("timestamp", current_time))
                text = mem.get("text", "").strip()
                if not text:
                    continue

                age_seconds = current_time - timestamp

                if age_seconds < one_day_seconds:
                    bucket_1d.append(text)
                elif age_seconds < one_month_seconds:
                    bucket_1m.append(text)
                elif age_seconds < three_months_seconds:
                    bucket_3m.append(text)
                else:
                    bucket_1y.append(text)

            # 3. 初始化演化人格数据
            current_persona = self.state_ref.evolved_persona.copy() if self.state_ref.evolved_persona else {}
            evolved_persona = {
                "short_term_vibe": current_persona.get("short_term_vibe", ""),
                "recent_habits": current_persona.get("recent_habits", ""),
                "relationship_phase": current_persona.get("relationship_phase", ""),
                "core_bond": current_persona.get("core_bond", ""),
                "weights": current_persona.get("weights", {
                    "short_term": 1.0,
                    "recent": 0.7,
                    "phase": 0.4,
                    "core": 0.2
                }),
                "last_evolution_time": current_time,
            }

            # 4. 处理 bucket_1d: Current Mood & Immediate Needs
            if bucket_1d:
                try:
                    sampled_texts = bucket_1d[:20]  # 采样最多20条
                    joined_text = "\n".join(sampled_texts)
                    prompt = (
                        "你是女娲的人格分析器。请分析以下最近1天的对话记忆，"
                        "提取用户的当前情绪状态和即时需求。"
                        "输出1-2句话的简洁总结，描述用户的当前心情和即时关注点。\n\n"
                        f"{joined_text}\n\n"
                        "总结："
                    )
                    response = self.llm_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是一个负责分析用户当前状态的人格分析器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.5,
                        max_tokens=128,
                    )
                    evolved_persona["short_term_vibe"] = response.choices[0].message.content.strip()
                    logger.debug("已提取1d特征: %d 条记忆，采样 %d 条", len(bucket_1d), len(sampled_texts))
                except Exception as e:
                    logger.exception("提取1d特征失败: %s", e)

            # 5. 处理 bucket_1m: Recent Habits & Topics
            if bucket_1m:
                try:
                    sampled_texts = bucket_1m[:20]  # 采样最多20条
                    joined_text = "\n".join(sampled_texts)
                    prompt = (
                        "你是女娲的人格分析器。请分析以下最近1个月的对话记忆，"
                        "提取用户的行为习惯、常见话题和互动模式。"
                        "输出1-2句话的简洁总结，描述用户的近期习惯和常聊话题。\n\n"
                        f"{joined_text}\n\n"
                        "总结："
                    )
                    response = self.llm_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是一个负责分析用户习惯的人格分析器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.5,
                        max_tokens=128,
                    )
                    evolved_persona["recent_habits"] = response.choices[0].message.content.strip()
                    logger.debug("已提取1m特征: %d 条记忆，采样 %d 条", len(bucket_1m), len(sampled_texts))
                except Exception as e:
                    logger.exception("提取1m特征失败: %s", e)

            # 6. 处理 bucket_3m: Relationship Definition
            if bucket_3m:
                try:
                    sampled_texts = bucket_3m[:20]  # 采样最多20条
                    joined_text = "\n".join(sampled_texts)
                    prompt = (
                        "你是女娲的人格分析器。请分析以下最近3个月的对话记忆，"
                        "提取用户与女娲的关系定义、关系发展阶段和互动深度。"
                        "输出1-2句话的简洁总结，描述当前的关系定义和关系特征。\n\n"
                        f"{joined_text}\n\n"
                        "总结："
                    )
                    response = self.llm_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是一个负责分析关系定义的人格分析器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.5,
                        max_tokens=128,
                    )
                    evolved_persona["relationship_phase"] = response.choices[0].message.content.strip()
                    logger.debug("已提取3m特征: %d 条记忆，采样 %d 条", len(bucket_3m), len(sampled_texts))
                except Exception as e:
                    logger.exception("提取3m特征失败: %s", e)

            # 7. 处理 bucket_1y: Core Shared Values
            if bucket_1y:
                try:
                    sampled_texts = bucket_1y[:20]  # 采样最多20条
                    joined_text = "\n".join(sampled_texts)
                    prompt = (
                        "你是女娲的人格分析器。请分析以下超过3个月的长期对话记忆，"
                        "提取用户与女娲的共享价值观、核心纽带和深层关系基础。"
                        "输出1-2句话的简洁总结，描述核心共享价值观和长期关系基础。\n\n"
                        f"{joined_text}\n\n"
                        "总结："
                    )
                    response = self.llm_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "你是一个负责分析长期关系的人格分析器。"},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.5,
                        max_tokens=128,
                    )
                    evolved_persona["core_bond"] = response.choices[0].message.content.strip()
                    logger.debug("已提取1y特征: %d 条记忆，采样 %d 条", len(bucket_1y), len(sampled_texts))
                except Exception as e:
                    logger.exception("提取1y特征失败: %s", e)

            # 8. 更新状态中的演化人格数据（线程安全）
            with self.state_ref._lock:
                self.state_ref.evolved_persona.update(evolved_persona)

            # 9. 输出统计信息
            updated_dims = len([k for k, v in evolved_persona.items()
                               if k not in ['last_evolution_time', 'weights'] and v])
            logger.info("人格演化完成：更新了 %d 个维度", updated_dims)
            logger.debug("时间分桶统计: 1d=%d, 1m=%d, 3m=%d, 1y=%d", len(bucket_1d), len(bucket_1m), len(bucket_3m), len(bucket_1y))

        except Exception as e:
            logger.exception("人格演化失败: %s", e)
            import traceback
            traceback.print_exc()
