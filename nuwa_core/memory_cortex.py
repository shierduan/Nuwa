"""
记忆皮层模块 (Memory Cortex Module)

功能：封装向量存储，提供基于情绪一致性的记忆检索接口。

核心功能：
- MemoryCortex: 记忆皮层类，封装 VectorStore 操作
- recall_by_emotion(): RAG 检索接口，优先检索语义相关的记忆，并根据情绪向量进行加权

存储后端（2026-10 迁移）：
    由 LanceDB 迁移至 zvec（阿里 Proxima 引擎，进程内嵌入式）。
    迁移后不再依赖 pandas / pyarrow / lancedb，全部读写走
    VectorStore 抽象（见 nuwa_core/vector_store.py）。
    LanceDB 代码已移除，避免双后端维护成本与行为漂移。
"""

import json
import os
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from .identifiers import generate_memory_id
from .logging_config import get_logger
from .model_utils import ensure_embedding_model_dir
from .vector_store import (
    MEMORY_TYPE_RAW,
    MemoryStore,
    create_store,
)

# 延迟导入可选依赖，避免类型注解导致的导入错误
NUMPY_AVAILABLE = False
EMBEDDING_AVAILABLE = False

np = None
SentenceTransformer = None

# 尝试导入可选依赖
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    pass

logger = get_logger(__name__)


class MemoryCortex:
    """
    记忆皮层类

    封装向量存储，提供记忆存储和检索功能。
    支持基于语义相似度和情绪一致性的记忆检索。
    """

    # 向量维度（all-MiniLM-L6-v2 的维度是 384）
    VECTOR_DIM = 384

    def __init__(self, project_name: str, data_dir: str = "data"):
        """
        初始化记忆皮层

        Args:
            project_name: 项目名称
            data_dir: 数据目录（默认 "data"）
        """
        self.project_name = project_name
        self.data_dir = data_dir
        # zvec 存储目录（进程内嵌入式向量库）
        self.zvec_path = os.path.join(data_dir, project_name, "zvec")

        # 向量存储句柄（MemoryStore 抽象）
        self.store: Optional[MemoryStore] = None
        self._init_store()

        # 初始化 Embedding 模型
        self.embedding_model = None
        self._init_embedding_model()

    def _init_store(self):
        """初始化 zvec 向量存储

        存储后端可通过环境变量 NUWA_VECTOR_BACKEND 预留切换能力
        （当前仅 zvec 实现，保留接口以便未来接入其它引擎）。
        """
        backend = os.environ.get("NUWA_VECTOR_BACKEND", "zvec").lower()
        try:
            self.store = create_store(path=self.zvec_path, dim=self.VECTOR_DIM)
            logger.info("向量存储已初始化: %s -> %s", backend, self.zvec_path)
        except Exception:
            logger.exception("向量存储初始化失败(%s)", backend, extra={"nuwa_context": {"path": self.zvec_path}})
            self.store = None

    def _init_embedding_model(self):
        """初始化 Embedding 模型"""
        if not EMBEDDING_AVAILABLE or SentenceTransformer is None:
            logger.warning("SentenceTransformer 不可用，无法生成向量")
            return

        try:
            # 获取模型路径
            model_path = ensure_embedding_model_dir(SentenceTransformer)
            if not model_path:
                logger.warning("无法加载 Embedding 模型：缺少可用的本地目录，且自动下载失败。")
                return

            # 加载模型
            self.embedding_model = SentenceTransformer(model_path, local_files_only=True)
            logger.info("已加载 Embedding 模型: %s", model_path)
        except Exception as exc:
            logger.exception("初始化 Embedding 模型失败: %s", exc)
            self.embedding_model = None

    # ==================== 写入 ====================

    def store_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        存储记忆（内在时间感知版本）

        关键特性：将时间戳直接融合到文本内容中，格式为 [YYYY-MM-DD HH:MM:SS] 文本内容
        这样小模型（4B）可以直接从检索到的文本中读取时间信息，实现时间感知推理。

        Args:
            text: 记忆文本（原始文本，时间戳会自动添加）
            metadata: 可选的元数据（如时间戳、情绪向量等）
            timestamp: 可选的 datetime 对象，如果为 None 则使用当前时间

        Returns:
            成功返回 memory_id，失败返回 None
        """
        if not self.store:
            logger.warning("向量存储未初始化，无法存储记忆")
            return None

        if not self.embedding_model:
            logger.warning("Embedding 模型未加载，无法存储记忆")
            return None

        try:
            # 处理时间戳：优先使用传入的 timestamp，其次使用 metadata 中的 timestamp，最后使用当前时间
            if timestamp is not None:
                memory_datetime = timestamp
            elif metadata and "timestamp" in metadata and metadata["timestamp"] is not None:
                # 如果 metadata 中是 float（Unix 时间戳），转换为 datetime
                ts_value = metadata["timestamp"]
                if isinstance(ts_value, (int, float)):
                    memory_datetime = datetime.fromtimestamp(float(ts_value))
                elif isinstance(ts_value, datetime):
                    memory_datetime = ts_value
                else:
                    memory_datetime = datetime.now()
            else:
                memory_datetime = datetime.now()

            # 格式化时间戳字符串：YYYY-MM-DD HH:MM:SS
            timestamp_str = memory_datetime.strftime('%Y-%m-%d %H:%M:%S')

            # 关键改进：时间戳不用于生成向量，避免污染语义空间
            # 原因：时间戳中的数字和符号（如 [2026-03-06 02:21:00]）会在向量空间中产生噪声
            #       导致相近时间的消息向量变得相似，而非基于语义相似
            # 方案：仅使用纯文本内容生成 embedding，时间戳单独存储在 text 字段用于展示

            # 使用纯文本生成向量（不包含时间戳）
            vector = self.embedding_model.encode(text, convert_to_numpy=True)

            # 存储时将时间戳融合到文本中（用于检索结果展示）
            # 格式：[YYYY-MM-DD HH:MM:SS] 文本内容
            fused_text = f"[{timestamp_str}] {text}"

            # 确保向量维度正确
            if len(vector) != self.VECTOR_DIM:
                logger.error(
                    "向量维度不匹配: 期望 %d，实际 %d",
                    self.VECTOR_DIM,
                    len(vector),
                    extra={"nuwa_context": {"text": text[:80]}},
                )
                return None

            # 准备数据
            # 使用稳定内容指纹（blake2b）而非内置 hash()，避免哈希随机化导致
            # 跨进程 ID 不一致、同毫秒写入互相覆盖
            memory_id = generate_memory_id(text)

            # 处理 emotion_vector（转换为 JSON 字符串）
            emotion_vector_str = ""
            if metadata and "emotion_vector" in metadata and metadata["emotion_vector"] is not None:
                emotion_vec = metadata["emotion_vector"]
                if isinstance(emotion_vec, np.ndarray):
                    emotion_vec = emotion_vec.tolist()
                elif not isinstance(emotion_vec, list):
                    emotion_vec = list(emotion_vec)
                emotion_vector_str = json.dumps(emotion_vec, ensure_ascii=False)

            # 情绪字典（用于 Memory Dreamer）
            emotions_dict = {}
            if metadata and "emotions" in metadata and metadata["emotions"] is not None:
                emotions_dict = metadata["emotions"]
            elif hasattr(self, "state") and self.state is not None:
                emotions_dict = getattr(self.state, "emotional_spectrum", {})
            emotions_str = json.dumps(emotions_dict, ensure_ascii=False)

            # 将 datetime 转换为 Unix 时间戳（用于数据库存储）
            # 防御：Windows 上 datetime.timestamp() 对 1970 年之前的本地时间会抛
            # OSError(Errno 22)，此时降级为 0，由排序逻辑按 0 处理（最旧）
            try:
                memory_timestamp = float(memory_datetime.timestamp())
            except (OSError, OverflowError, ValueError):
                logger.warning("时间戳转换失败（%s），降级为 0", memory_datetime)
                memory_timestamp = 0.0

            # 构建符合 Schema 的数据
            fields = {
                "text": fused_text,           # 存储融合后的文本（包含时间戳）
                "emotion_vector": emotion_vector_str,  # JSON 字符串
                "timestamp": int(memory_timestamp),     # Unix 时间戳（用于排序和查询）
                "importance": float(metadata.get("importance", 0.5)) if metadata else 0.5,
                "type": str(metadata.get("type", MEMORY_TYPE_RAW)) if metadata else MEMORY_TYPE_RAW,
                "emotions": emotions_str,
                "access_count": int(metadata.get("access_count", 0)) if metadata else 0,
            }

            # 插入数据
            if not self.store.add(memory_id, vector.tolist(), fields):
                logger.warning("向量库写入失败", extra={"nuwa_context": {"memory_id": memory_id}})
                return None

            logger.debug(
                "已存储记忆 id=%s importance=%.2f text=%s",
                memory_id,
                fields["importance"],
                fused_text.replace("\n", " ")[:100],
            )
            return memory_id
        except Exception as exc:
            logger.exception("存储记忆失败: %s", exc, extra={"nuwa_context": {"text": text[:80]}})
            return None

    # ==================== 检索 ====================

    def recall_by_emotion(
        self,
        query_text: str,
        current_emotion_vector=None,
        top_k: int = 5,
        emotion_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        RAG 检索接口：优先检索语义相关的记忆，并根据情绪向量进行加权

        逻辑：
        1. 使用 query_text 生成查询向量
        2. 在向量存储中检索语义相似的记忆
        3. 如果提供了 current_emotion_vector，计算情绪一致性分数
        4. 综合语义相似度和情绪一致性，返回加权后的结果

        Args:
            query_text: 查询文本
            current_emotion_vector: 当前情绪向量（可选，用于情绪一致性加权）
            top_k: 返回的记忆数量
            emotion_weight: 情绪一致性权重（0.0-1.0，默认 0.3）

        Returns:
            记忆列表，每个记忆包含：
            - text: 记忆文本
            - similarity: 综合相似度分数 (0.0-1.0)
            - semantic_similarity: 语义相似度分数
            - emotion_similarity: 情绪一致性分数（如果有）
            - metadata: 元数据
        """
        if not self.store:
            return []

        if not self.embedding_model:
            logger.warning("Embedding 模型未加载，无法检索记忆")
            return []

        try:
            # 1. 生成查询向量
            query_vector = self.embedding_model.encode(query_text, convert_to_numpy=True)

            # 确保向量维度正确
            if len(query_vector) != self.VECTOR_DIM:
                logger.error(
                    "查询向量维度不匹配: 期望 %d，实际 %d",
                    self.VECTOR_DIM,
                    len(query_vector),
                )
                return []

            # 2. 向量检索（多取一些候选，供后续加权筛选）
            results = self.store.search(query_vector.tolist(), topk=top_k * 3)

            if not results:
                logger.debug("检索未命中: %s", query_text[:40])
                return []

            # 3. 计算综合相似度
            memories = []
            access_updates: List[Dict[str, Any]] = []
            current_ts = time.time()
            for res in results:
                fields = res.fields or {}
                memory_text = fields.get("text", "")
                if not memory_text:
                    continue

                # 语义相似度：MemoryStore 已统一返回"相似度"语义（越大越相似）
                semantic_similarity = float(res.score or 0.0)

                # 计算情绪一致性分数（如果有情绪向量）
                emotion_similarity = 1.0  # 默认值（无情绪向量时不影响结果）
                if current_emotion_vector is not None and NUMPY_AVAILABLE:
                    memory_emotion_str = fields.get("emotion_vector", "")
                    if memory_emotion_str:
                        try:
                            # emotion_vector 存储为 JSON 字符串，需要解析
                            memory_emotion_vec = np.array(json.loads(memory_emotion_str), dtype=np.float32)

                            # 计算情绪向量相似度
                            emotion_norm = np.linalg.norm(current_emotion_vector)
                            memory_emotion_norm = np.linalg.norm(memory_emotion_vec)

                            if emotion_norm > 0 and memory_emotion_norm > 0:
                                emotion_similarity = float(
                                    np.dot(current_emotion_vector, memory_emotion_vec) /
                                    (emotion_norm * memory_emotion_norm)
                                )
                                # 将相似度从 [-1, 1] 映射到 [0, 1]
                                emotion_similarity = (emotion_similarity + 1.0) / 2.0
                            else:
                                emotion_similarity = 0.5  # 中性值
                        except (json.JSONDecodeError, ValueError, TypeError):
                            emotion_similarity = 1.0

                # 综合相似度 = (1 - emotion_weight) * 语义相似度 + emotion_weight * 情绪相似度
                combined_similarity = (1.0 - emotion_weight) * semantic_similarity + emotion_weight * emotion_similarity

                # 过滤重复查询：如果记忆中的用户输入与当前查询高度相似，降低其分数
                # 这样可以避免检索到用户之前问过的相同问题，而是检索到实际的答案
                user_input_from_memory = self._extract_user_input_from_memory(memory_text)
                if user_input_from_memory:
                    query_similarity = self._calculate_string_similarity(query_text, user_input_from_memory)

                    # 如果相似度超过阈值（0.75），说明这是重复查询
                    if query_similarity > 0.75:
                        # 降低相似度：相似度越高，降低越多
                        # 例如：0.9 相似度 -> 降低到原来的 10%，0.8 相似度 -> 降低到原来的 20%
                        # 使用 max(0.05, ...) 确保至少保留 5% 的分数，避免完全排除
                        penalty_factor = max(0.05, 1.0 - query_similarity)  # 0.05 到 0.25
                        original_similarity = combined_similarity
                        combined_similarity = combined_similarity * penalty_factor
                        logger.debug(
                            "检测到重复查询（相似度=%.2f），降低记忆分数: %.3f -> %.3f",
                            query_similarity,
                            original_similarity,
                            combined_similarity,
                            extra={
                                "nuwa_context": {
                                    "query": query_text[:60],
                                    "memory_input": user_input_from_memory[:60],
                                }
                            },
                        )

                # 提取其他元数据
                timestamp_value = float(fields.get("timestamp", 0) or 0)
                current_access = int(fields.get("access_count", 0) or 0)
                metadata = {
                    "id": res.id,
                    "timestamp": timestamp_value,
                    "timestamp_human": self._format_timestamp(timestamp_value),
                    "age_seconds": max(0.0, current_ts - timestamp_value),
                    "importance": fields.get("importance", 0.5),
                    "type": fields.get("type", "raw"),
                    "emotions": fields.get("emotions", ""),
                    "access_count": current_access,
                }

                memories.append({
                    "text": memory_text,
                    "similarity": combined_similarity,
                    "semantic_similarity": semantic_similarity,
                    "emotion_similarity": emotion_similarity if current_emotion_vector is not None else None,
                    "metadata": metadata,
                })
                access_updates.append({"id": res.id, "new_value": current_access + 1})

            # 更新访问计数（记忆强化：被召回越频繁越持久）
            if access_updates:
                self._increment_access_counts(access_updates)

            # 4. 按综合相似度排序，返回 top_k
            memories.sort(key=lambda x: x["similarity"], reverse=True)
            top = memories[:top_k]

            # 检索结果摘要（debug 级别，不污染默认日志）
            if top:
                best = top[0]
                logger.debug(
                    "检索命中 %d 条，最高相似度=%.3f，示例: %s",
                    len(top),
                    best["similarity"],
                    best["text"].replace("\n", " ")[:80],
                    extra={"nuwa_context": {"query": query_text[:40]}},
                )

            return top
        except Exception as exc:
            logger.exception("记忆检索失败: %s", exc, extra={"nuwa_context": {"query": query_text[:60]}})
            return []

    # ==================== 辅助 ====================

    def _calculate_string_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个字符串的相似度（0.0-1.0）

        使用 SequenceMatcher 计算相似度，适用于检测重复查询。
        """
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()

    def _extract_user_input_from_memory(self, memory_text: str) -> Optional[str]:
        """
        从记忆文本中提取用户输入部分

        记忆格式可能是：
        - "[timestamp] 用户: ... 女娲: ..."
        - "用户: ... 女娲: ..."

        Args:
            memory_text: 记忆文本

        Returns:
            用户输入部分，如果无法提取则返回 None
        """
        if not memory_text:
            return None

        # 移除时间戳前缀（如果存在）
        text = memory_text
        if text.startswith("[") and "]" in text[:25]:
            # 找到第一个 ] 的位置
            end_idx = text.find("]", 1)
            if end_idx > 0:
                text = text[end_idx + 1:].strip()

        # 查找 "用户:" 或 "用户：" 标记
        user_markers = ["用户:", "用户："]
        for marker in user_markers:
            if marker in text:
                # 提取用户输入部分（到 "女娲:" 或 "女娲：" 之前）
                start_idx = text.find(marker)
                user_part = text[start_idx + len(marker):].strip()

                # 查找女娲回复的开始位置
                nuwa_markers = ["女娲:", "女娲："]
                for nuwa_marker in nuwa_markers:
                    if nuwa_marker in user_part:
                        end_idx = user_part.find(nuwa_marker)
                        user_part = user_part[:end_idx].strip()
                        break

                return user_part

        return None

    def _format_timestamp(self, ts: float) -> str:
        """将时间戳转换为人类可读的本地时间描述"""
        if not ts:
            return "(未知时间)"
        try:
            dt = datetime.fromtimestamp(float(ts)).astimezone()
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        except Exception:
            return "(时间解析失败)"

    def _increment_access_counts(self, updates: List[Dict[str, Any]]):
        """将指定记忆的访问次数 +1（记忆强化：召回即强化）"""
        if not updates or not self.store:
            return
        for item in updates:
            mem_id = item.get("id")
            new_value = item.get("new_value")
            if not mem_id:
                continue
            try:
                # 读-改-写：先取回完整记录与向量，再原样回写
                existing = self.store.fetch([mem_id]).get(mem_id)
                if existing is None:
                    continue
                fields = dict(existing.fields or {})
                fields["access_count"] = int(new_value)
                self.store.update(mem_id, existing.vector or [], fields)
            except Exception as exc:
                logger.warning("更新访问计数失败(%s): %s", mem_id, exc)
                continue

    def get_recent_memories(
        self, limit: int = 1000, memory_type: str = "raw", include_vector: bool = False
    ) -> List[Dict[str, Any]]:
        """获取最近的记忆列表（按时间倒序）

        Args:
            limit: 返回条数上限
            memory_type: 记忆类型过滤（raw / summary / insight），空串表示不过滤
            include_vector: 是否携带向量（聚类等算法需要）
        """
        if not self.store:
            return []
        try:
            rows = self.store.get_recent(
                limit=limit, memory_type=memory_type, include_vector=include_vector
            )
            # 兼容历史数据：早期版本把对话记忆标为 "dialogue"，
            # 而巩固/做梦流程按 "raw" 过滤，导致这些记忆永远不被整理。
            # 这里做类型归一，保证历史记忆也能进入巩固流程。
            if memory_type == MEMORY_TYPE_RAW:
                legacy = self.store.get_recent(
                    limit=limit, memory_type="dialogue", include_vector=include_vector
                )
                if legacy:
                    rows = rows + legacy
                    rows.sort(key=lambda x: float(x.get("timestamp", 0) or 0), reverse=True)
                    rows = rows[:limit]
            return rows
        except Exception as exc:
            logger.exception("获取记忆失败: %s", exc)
            return []

    def get_all_memories(self, limit: int = 5000, memory_type: str = "") -> List[Dict[str, Any]]:
        """获取全部记忆（memory_type 传空字符串表示不过滤）"""
        if not self.store:
            return []
        try:
            return self.store.get_recent(limit=limit, memory_type=memory_type)
        except Exception as exc:
            logger.exception("获取记忆失败: %s", exc)
            return []

    def delete_memories(self, memory_ids: List[str]) -> None:
        """删除指定 ID 的记忆"""
        if not memory_ids or not self.store:
            return
        try:
            self.store.delete(list(memory_ids))
        except Exception as exc:
            logger.exception("删除记忆失败: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        if not self.store:
            return {"backend": None, "count": 0}
        try:
            return self.store.stats()
        except Exception as exc:
            logger.exception("获取统计信息失败: %s", exc)
            return {"backend": "unknown", "count": 0}

    def find_max_similarity(self, text: str) -> float:
        """查询与给定文本最相似的已有记忆相似度（0.0-1.0）

        用于"惊奇门控"（SurprisalGate）：判断新信息相对于已有记忆
        到底有多"新"。相似度越高说明越可能是已知信息的重复。
        """
        if not self.store or not self.embedding_model or not text:
            return 0.0
        try:
            vector = self.embedding_model.encode(text, convert_to_numpy=True)
            if len(vector) != self.VECTOR_DIM:
                return 0.0
            results = self.store.search(vector.tolist(), topk=1)
            if not results:
                return 0.0
            return float(results[0].score or 0.0)
        except Exception as exc:
            logger.exception("计算最大相似度失败: %s", exc)
            return 0.0

    def get_index_info(self) -> Dict[str, Any]:
        """兼容接口：返回存储统计（历史 API 名称，调用方含 self_evolution_rl / memory_graph）

        迁移前该方法属于 LanceDB 索引信息；迁移后统一由 store.stats() 提供。
        """
        stats = self.get_stats()
        return {
            "count": stats.get("count", 0),
            "backend": stats.get("backend"),
            "path": stats.get("path"),
            "dim": stats.get("dim", self.VECTOR_DIM),
        }
