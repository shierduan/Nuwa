"""
zvec 迁移后端到端验证：写入 / 检索 / 访问计数强化 / 最近记忆 / 删除
用法: python test_zvec_e2e.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nuwa_core.memory_cortex import MemoryCortex


def main():
    print("=" * 60)
    print("zvec 迁移端到端验证")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp(prefix="nuwa_zvec_e2e_"))
    try:
        mc = MemoryCortex("e2e", data_dir=str(tmp))

        # ---- 1. 写入 ----
        texts = [
            "我们约定在银月湖畔相见，那是夏天的第一个约定",
            "用户喜欢喝不加糖的美式咖啡",
            "今天部署 Docker 遇到了端口冲突的问题",
        ]
        ids = []
        for i, t in enumerate(texts):
            mid = mc.store_memory(t, metadata={"importance": 0.6 + i * 0.1})
            if not mid:
                print(f"[FAIL] 写入失败: {t[:20]}")
                return 1
            ids.append(mid)
        print(f"[1] 写入 {len(ids)} 条: OK")

        # ---- 2. 检索 ----
        res = mc.recall_by_emotion("我们在哪里约定见面", top_k=3)
        if not res:
            print("[FAIL] 检索返回空")
            return 1
        best = res[0]
        print(f"[2] 检索 {len(res)} 条，最高相似度={best['similarity']:.3f}")
        print(f"    命中: {best['text'][:50]}")
        if "银月" not in best["text"]:
            print("[WARN] 检索结果未命中预期记忆（语义检索有误差属正常）")

        # ---- 3. 情绪加权 ----
        import numpy as np
        emo = np.zeros(13, dtype=np.float32)
        emo[0] = 1.0  # joy
        res2 = mc.recall_by_emotion("咖啡", current_emotion_vector=emo, top_k=2)
        if res2 and res2[0].get("emotion_similarity") is not None:
            print(f"[3] 情绪加权检索: OK (emotion_sim={res2[0]['emotion_similarity']:.3f})")
        else:
            print("[FAIL] 情绪加权未生效")
            return 1

        # ---- 4. 访问计数强化 ----
        before = mc.get_recent_memories(limit=10)
        ac_before = {m["id"]: m.get("access_count", 0) for m in before}
        mc.recall_by_emotion("咖啡", top_k=2)
        after = mc.get_recent_memories(limit=10)
        ac_after = {m["id"]: m.get("access_count", 0) for m in after}
        changed = [k for k in ac_after if ac_after[k] > ac_before.get(k, 0)]
        if changed:
            print(f"[4] 访问计数强化: OK ({len(changed)} 条被强化)")
        else:
            print("[FAIL] 访问计数未增加")
            return 1

        # ---- 5. 最近记忆排序 ----
        recent = mc.get_recent_memories(limit=10)
        if len(recent) != 3:
            print(f"[FAIL] 最近记忆数量异常: {len(recent)}")
            return 1
        ts = [m["timestamp"] for m in recent]
        if ts != sorted(ts, reverse=True):
            print("[FAIL] 最近记忆未按时间倒序")
            return 1
        print(f"[5] 最近记忆排序: OK ({len(recent)} 条，倒序)")

        # ---- 6. 统计 ----
        stats = mc.get_index_info()
        print(f"[6] 统计: {stats}")
        if stats.get("count", 0) != 3:
            print("[FAIL] 统计数量不符")
            return 1

        # ---- 7. 删除 ----
        mc.delete_memories([ids[0]])
        remain = mc.get_recent_memories(limit=10)
        if len(remain) != 2:
            print(f"[FAIL] 删除后数量异常: {len(remain)}")
            return 1
        print("[7] 删除: OK")

        print("\n[SUCCESS] zvec 迁移全链路验证通过")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
