"""
GraphEnhancedMemoryCortex 透传回归测试

背景：2026-10-25 重构时，nuwa_core/memory_graph.py 因迁移脚本损坏被
git checkout 恢复，导致上一轮已修复的三个透传缺陷被意外回滚：

  1. get_recent_memories() 不接受 include_vector
     -> 巩固层聚类取不到向量，L1 摘要永不产出
  2. find_max_similarity() 缺失
     -> 惊奇门控探测失败（降级放行），门控形同虚设
  3. store_memory() 自行生成记忆 ID
     -> 图节点 ID 与向量库 ID 不一致，检索结果无法合并

本测试锁定这三个行为，防止再次回滚。
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from nuwa_core.memory_graph import GraphEnhancedMemoryCortex  # noqa: E402

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    mark = "OK  " if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  <- {detail}" if detail and not cond else ""))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="nuwa_graph_passthrough_")
    cortex = GraphEnhancedMemoryCortex(project_name="passthrough", data_dir=tmp)

    # ---------- 1. include_vector 透传 ----------
    print("\n--- 1. get_recent_memories(include_vector=True) ---")
    mid = cortex.store_memory("图透传回归测试：北海道的雪与约定", metadata={"importance": 0.7})
    check("store_memory 返回 memory_id", bool(mid), f"got {mid!r}")

    rows = cortex.get_recent_memories(limit=10, include_vector=True)
    check(
        "include_vector=True 被接受且返回向量",
        bool(rows) and isinstance(rows[0].get("vector"), list) and len(rows[0]["vector"]) > 0,
        f"rows={len(rows)}, first_has_vector={'vector' in rows[0] if rows else 'N/A'}",
    )

    rows_novec = cortex.get_recent_memories(limit=10, include_vector=False)
    check(
        "include_vector=False 时不返回向量",
        bool(rows_novec) and "vector" not in rows_novec[0],
    )

    # ---------- 2. find_max_similarity 透传 ----------
    print("\n--- 2. find_max_similarity() 透传 ---")
    sim = cortex.find_max_similarity("图透传回归测试：北海道的雪与约定")
    check(
        "find_max_similarity 命中已写入记忆（相似度应接近 1.0）",
        sim > 0.95,
        f"sim={sim}",
    )
    sim_new = cortex.find_max_similarity("量子纠缠在凝聚态物理中的表现形式")
    check(
        "find_max_similarity 对无关文本返回低相似度",
        sim_new < 0.6,
        f"sim={sim_new}",
    )

    # ---------- 3. 图节点 ID 与向量库 ID 一致 ----------
    print("\n--- 3. 图节点 ID 与向量库 ID 一致性 ---")
    # 注意：NetworkX Graph 实现了 __len__（返回节点数），空图为 falsy。
    # 因此必须用 "is not None" 而非直接 truthiness 判断图是否存在。
    graph = cortex.memory_graph.graph
    check("记忆图对象存在", graph is not None)
    graph_nodes = set(graph.nodes) if graph is not None else set()
    check(
        "图节点包含底层返回的 memory_id",
        mid in graph_nodes,
        f"mid={mid}, graph_nodes={sorted(graph_nodes)[:3]}",
    )

    node_meta = {}
    if graph is not None and mid in graph:
        node_meta = graph.nodes[mid].get("metadata", {})
    check(
        "图节点 metadata 携带 id 字段",
        node_meta.get("id") == mid,
        f"metadata={node_meta}",
    )

    # ---------- 4. 统计接口 ----------
    print("\n--- 4. get_stats / get_index_info ---")
    stats = cortex.get_stats()
    check("get_stats 返回向量库统计", isinstance(stats, dict) and stats.get("count", 0) >= 1, f"{stats}")
    info = cortex.get_index_info()
    check("get_index_info 返回索引信息", isinstance(info, dict), f"{info}")

    stat = cortex.get_statistics()
    check(
        "get_statistics 使用 vector_store 键（非过时的 lancedb）",
        "vector_store" in stat and "lancedb" not in stat,
        f"keys={list(stat.keys())}",
    )

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        for f in FAIL:
            print(f"  - {f}")
        return 1
    print("[SUCCESS] 图增强记忆透传回归验证通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
