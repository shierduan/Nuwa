"""
向量存储抽象层 (Vector Store Abstraction)

设计目标：
- 将记忆的存储引擎与业务逻辑解耦，便于替换/测试/回滚
- 保持 Nuwa 的设计哲学：记忆 = 语义向量 + 情绪向量 + 时间权重 + 重要性
- 默认使用阿里 zvec（进程内嵌入式向量库，类 SQLite），无需独立服务

对外接口极简：add / search / update / delete / get_recent / fetch / stats

迁移说明（2026-10）：
    原实现以 LanceDB 为唯一后端，MemoryCortex 直接调用 LanceDB 专有 API
    （table.add / table.search / table.to_pandas / table.update(where=...)）。
    本层将所有存储能力收敛为上述统一接口，MemoryCortex 只依赖抽象，
    底层切换到 zvec 时业务代码零改动。
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .logging_config import get_logger

logger = get_logger(__name__)

# ============ 可选依赖探测 ============
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    np = None
    NUMPY_AVAILABLE = False

try:
    import zvec

    ZVEC_AVAILABLE = True
except ImportError:  # pragma: no cover
    zvec = None
    ZVEC_AVAILABLE = False


@dataclass
class SearchResult:
    """检索结果（score 越大越相似）"""

    id: str
    score: float
    fields: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None


# ============ 记忆类型分层（L0/L1/L2） ============
# 统一在此定义，避免各处硬编码字符串导致"写入用一种类型、
# 过滤用另一种类型"的静默失效（曾导致对话记忆永远不进巩固流程）。
MEMORY_TYPE_RAW = "raw"          # L0 原始层：原始对话片段
MEMORY_TYPE_SUMMARY = "summary"  # L1 语义摘要：多条原始记忆的压缩
MEMORY_TYPE_INSIGHT = "insight"  # L2 高阶洞察：跨摘要提炼的模式

#: 全部合法记忆类型
MEMORY_TYPES = (MEMORY_TYPE_RAW, MEMORY_TYPE_SUMMARY, MEMORY_TYPE_INSIGHT)


class MemoryStore(ABC):
    """记忆存储抽象基类

    上层 MemoryCortex 只依赖本抽象，不感知底层是 zvec 还是其它引擎。
    """

    #: 向量维度（all-MiniLM-L6-v2 = 384）
    VECTOR_DIM = 384

    @abstractmethod
    def add(self, id: str, vector: List[float], fields: Dict[str, Any]) -> bool:
        """写入一条记忆"""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        vector: List[float],
        topk: int = 10,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """向量检索（支持标量过滤表达式）"""
        raise NotImplementedError

    @abstractmethod
    def update(self, id: str, vector: List[float], fields: Dict[str, Any]) -> bool:
        """更新一条记忆（用于记忆强化：访问次数、情绪向量、重要性）"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """按 ID 删除记忆"""
        raise NotImplementedError

    @abstractmethod
    def get_recent(
        self, limit: int = 1000, memory_type: str = "raw", include_vector: bool = False
    ) -> List[Dict[str, Any]]:
        """获取最近的记忆（按时间倒序）"""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, ids: List[str]) -> Dict[str, SearchResult]:
        """按 ID 精确取回记忆（用于读取后原样更新，保留向量）"""
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """存储统计信息"""
        raise NotImplementedError


class ZvecStore(MemoryStore):
    """基于阿里 zvec 的嵌入式向量存储

    选型理由（契合 Nuwa 定位）：
    - 进程内运行，零部署零运维，适合消费级硬件
    - 持久化 + WAL，崩溃自动恢复（数字生命需长期连续性）
    - 支持稠密向量 + 标量过滤（承载"情绪一致性检索"）

    关键实现约定（2026-10 修复）：
    1. metric 固定为 COSINE。zvec 默认是 IP（内积），其 score 越大越相似，
       与上层"score 越小越相似"的距离语义冲突，会导致检索结果排序完全颠倒。
       COSINE 下 zvec 返回的是 cosine distance（0 = 完全相同），
       对应 similarity = 1 - score，语义清晰且与 LanceDB 时代一致。
    2. zvec.open() 与 zvec.create_and_open() 的职责不同：
       create_and_open 要求路径不存在（否则抛 "path exists"），
       因此重启后必须走 open() 分支，否则第二次启动即失败。
    3. 打开后校验 schema（字段集合 / 维度 / metric），不匹配则销毁重建，
       以支持 schema 演进（如新增 text 字段）与 metric 迁移。
    """

    #: zvec 标量字段定义（nullable=True 兼容历史数据缺失字段）
    SCALAR_FIELDS = [
        ("text", "STRING"),           # 记忆正文（带时间戳前缀）
        ("emotion_vector", "STRING"),  # JSON 字符串（13 维情绪向量）
        ("emotions", "STRING"),        # JSON 字符串（情绪标签字典）
        ("importance", "FLOAT"),
        ("timestamp", "INT64"),
        ("type", "STRING"),            # raw / summary / insight
        ("access_count", "INT64"),
    ]

    #: 向量相似度度量：COSINE（score = 余弦距离，0 = 最相似）
    METRIC = "COSINE"

    def __init__(self, path: str, dim: int = MemoryStore.VECTOR_DIM):
        self.path = path
        self.dim = dim
        self._collection = None
        self._init_collection()

    def _build_schema(self):
        """构建 zvec CollectionSchema（向量 + 标量字段）"""
        field_type_map = {
            "STRING": zvec.DataType.STRING,
            "FLOAT": zvec.DataType.FLOAT,
            "INT64": zvec.DataType.INT64,
        }
        # nullable=True：允许部分记忆缺少某些标量字段（如尚未计算情绪向量）
        fields = [
            zvec.FieldSchema(name, field_type_map[dtype], nullable=True)
            for name, dtype in self.SCALAR_FIELDS
        ]
        metric = getattr(zvec.MetricType, self.METRIC, zvec.MetricType.COSINE)
        return zvec.CollectionSchema(
            name="nuwa_memory",
            vectors=zvec.VectorSchema(
                "embedding",
                zvec.DataType.VECTOR_FP32,
                self.dim,
                # 显式指定度量：FlatIndexParam 在建集合时决定 score 语义
                index_param=zvec.FlatIndexParam(metric_type=metric),
            ),
            fields=fields,
        )

    def _schema_matches(self, collection) -> bool:
        """校验已打开集合的 schema 是否与当前期望一致"""
        try:
            existing_fields = {f.name for f in collection.schema.fields}
            expected_fields = {name for name, _ in self.SCALAR_FIELDS}
            if existing_fields != expected_fields:
                return False

            vectors = collection.schema.vectors
            if len(vectors) != 1 or vectors[0].dimension != self.dim:
                return False

            metric = getattr(vectors[0].index_param, "metric_type", None)
            metric_name = getattr(metric, "name", None) or str(metric)
            return metric_name == self.METRIC
        except Exception:
            return False

    def _init_collection(self):
        """创建或打开集合（兼容重启与 schema 演进）"""
        if not ZVEC_AVAILABLE:
            raise RuntimeError("zvec 未安装，请执行: pip install zvec")

        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # 分支 1：集合已存在 → open + schema 校验
        if os.path.exists(self.path):
            try:
                collection = zvec.open(self.path)
            except Exception as e:
                raise RuntimeError(f"打开 zvec 集合失败: {e}") from e

            if self._schema_matches(collection):
                self._collection = collection
                return

            # schema 不匹配（如旧版缺 text 字段，或 metric 从 IP 迁移为 COSINE）
            # 销毁重建：记忆可从事实账本与摘要重新生成，保留旧结构反而会造成
            # 后续写入静默失败（字段缺失 / 排序颠倒）
            logger.info("zvec schema 不匹配，销毁并重建集合")
            try:
                collection.destroy()
            except Exception as exc:
                logger.warning("销毁旧集合失败: %s", exc)
                # 销毁失败则物理删除目录
                shutil.rmtree(self.path, ignore_errors=True)

        # 分支 2：集合不存在 → 创建
        try:
            self._collection = zvec.create_and_open(
                path=self.path, schema=self._build_schema()
            )
        except Exception as e:
            raise RuntimeError(f"初始化 zvec 集合失败: {e}") from e

    # ---------- 接口实现 ----------

    def add(self, id: str, vector: List[float], fields: Dict[str, Any]) -> bool:
        try:
            safe = self._sanitize_fields(fields)
            doc = zvec.Doc(id=id, vectors={"embedding": vector}, fields=safe)
            self._collection.insert([doc])
            return True
        except Exception as exc:
            logger.warning("zvec 写入失败: %s", exc, extra={"nuwa_context": {"id": id}})
            return False

    def update(self, id: str, vector: List[float], fields: Dict[str, Any]) -> bool:
        """更新一条记忆。

        zvec 的 update 要求 Doc 带完整向量；这里若调用方未提供向量，
        会先 fetch 现有向量再回写，避免把记忆的语义表示清零。
        """
        try:
            if not vector:
                existing = self.fetch([id]).get(id)
                if existing is None or not existing.vector:
                    logger.warning("zvec 更新失败：记忆 %s 不存在或缺少向量", id)
                    return False
                vector = existing.vector

            safe = self._sanitize_fields(fields)
            # upsert 语义更稳：内存中不存在时也能写入
            self._collection.upsert([zvec.Doc(id=id, vectors={"embedding": vector}, fields=safe)])
            return True
        except Exception as exc:
            logger.warning("zvec 更新失败: %s", exc, extra={"nuwa_context": {"id": id}})
            return False

    def search(
        self, vector: List[float], topk: int = 10, filter_expr: Optional[str] = None
    ) -> List[SearchResult]:
        """向量检索

        score 语义（metric=COSINE）：zvec 返回余弦距离，0 = 完全相同。
        本层统一转换为"相似度"（越大越相似，范围 [0,1]），
        供上层直接按相似度排序。
        """
        try:
            kwargs: Dict[str, Any] = {"topk": max(1, int(topk))}
            if filter_expr:
                kwargs["filter"] = filter_expr
            docs = self._collection.query(
                zvec.Query("embedding", vector=vector), **kwargs
            )
            results: List[SearchResult] = []
            for d in (docs or []):
                distance = float(getattr(d, "score", 0.0) or 0.0)
                # 余弦距离 -> 相似度
                similarity = max(0.0, min(1.0, 1.0 - distance))
                results.append(
                    SearchResult(
                        id=getattr(d, "id", "") or "",
                        score=similarity,
                        fields=dict(getattr(d, "fields", {}) or {}),
                    )
                )
            # 相似度降序（zvec 已按距离升序返回，此处显式保证）
            results.sort(key=lambda r: r.score, reverse=True)
            return results
        except Exception as exc:
            logger.exception("zvec 检索失败: %s", exc)
            return []

    def delete(self, ids: List[str]) -> bool:
        if not ids:
            return True
        try:
            self._collection.delete(list(ids))
            return True
        except Exception as exc:
            logger.exception("zvec 删除失败: %s", exc, extra={"nuwa_context": {"count": len(ids)}})
            return False

    def get_recent(
        self, limit: int = 1000, memory_type: str = "raw", include_vector: bool = False
    ) -> List[Dict[str, Any]]:
        """获取最近记忆：遍历全部文档 → 按 type 过滤 → 按时间倒序 → 截断

        说明：zvec 的 query 必须提供向量，无法直接做"全表按标量排序"，
        因此这里用 iter_docs() 遍历后在 Python 侧排序。记忆规模
        （数千条）下开销可接受。

        Args:
            limit: 返回条数上限
            memory_type: 记忆类型过滤（raw / summary / insight），空串表示不过滤
            include_vector: 是否携带向量（聚类等算法需要，默认关闭以省内存）
        """
        try:
            rows: List[Dict[str, Any]] = []
            field_names = [name for name, _ in self.SCALAR_FIELDS]
            for d in self._collection.iter_docs(
                output_fields=field_names, include_vector=include_vector
            ):
                row = dict(getattr(d, "fields", {}) or {})
                row["id"] = getattr(d, "id", "") or ""
                if not row["id"]:
                    continue
                if include_vector:
                    vectors = getattr(d, "vectors", None) or {}
                    vec = vectors.get("embedding") if isinstance(vectors, dict) else None
                    if vec is not None:
                        row["vector"] = list(vec)
                rows.append(row)

            if memory_type:
                rows = [r for r in rows if r.get("type") == memory_type]
            rows.sort(key=lambda x: float(x.get("timestamp", 0) or 0), reverse=True)
            return rows[:limit]
        except Exception as exc:
            logger.exception("zvec 获取最近记忆失败: %s", exc)
            return []

    def fetch(self, ids: List[str]) -> Dict[str, SearchResult]:
        """按 ID 精确取回记忆（含向量），用于"读-改-写"闭环"""
        if not ids:
            return {}
        try:
            field_names = [name for name, _ in self.SCALAR_FIELDS]
            raw = self._collection.fetch(
                list(ids), output_fields=field_names, include_vector=True
            )
            out: Dict[str, SearchResult] = {}
            for doc_id, doc in (raw or {}).items():
                vectors = getattr(doc, "vectors", None) or {}
                vec = vectors.get("embedding") if isinstance(vectors, dict) else None
                out[doc_id] = SearchResult(
                    id=doc_id,
                    score=0.0,
                    fields=dict(getattr(doc, "fields", {}) or {}),
                    vector=list(vec) if vec is not None else None,
                )
            return out
        except Exception as exc:
            logger.exception("zvec fetch 失败: %s", exc, extra={"nuwa_context": {"count": len(ids)}})
            return {}

    def stats(self) -> Dict[str, Any]:
        base = {"backend": "zvec", "path": self.path, "dim": self.dim}
        try:
            count = sum(
                1 for d in self._collection.iter_docs()
                if getattr(d, "id", "")
            )
            base["count"] = count
        except Exception:
            pass
        return base

    @classmethod
    def _sanitize_fields(cls, fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """规范化标量字段：仅保留 schema 声明的字段，缺失的补 None

        zvec 对 nullable=False 的字段要求必须提供值，缺失会报
        "field[xxx] is required but not provided"。本 schema 全部字段
        声明为 nullable=True，这里统一补齐 None 以保证写入稳定。
        """
        safe: Dict[str, Any] = {name: None for name, _ in cls.SCALAR_FIELDS}
        for k, v in (fields or {}).items():
            if k not in safe:
                continue
            # zvec INT64 字段必须是整数，这里做一次归一化
            if k == "timestamp":
                try:
                    safe[k] = int(float(v)) if v is not None else None
                except (TypeError, ValueError):
                    safe[k] = None
            elif k == "access_count":
                try:
                    safe[k] = int(v) if v is not None else None
                except (TypeError, ValueError):
                    safe[k] = None
            elif k == "importance":
                try:
                    safe[k] = float(v) if v is not None else None
                except (TypeError, ValueError):
                    safe[k] = None
            else:
                safe[k] = v
        return safe


def create_store(path: str = "data/nuwa/zvec", dim: int = MemoryStore.VECTOR_DIM) -> MemoryStore:
    """工厂函数：创建向量存储实例"""
    return ZvecStore(path, dim)
