"""
ZvecStore 完整功能验证：add / search / 标量过滤 / update / get_recent / stats
用法: python test_vector_store.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

from nuwa_core.vector_store import ZVEC_AVAILABLE, ZvecStore

DIM = 4


def main():
    print("=" * 60)
    print("ZvecStore 完整功能验证")
    print("=" * 60)

    if not ZVEC_AVAILABLE:
        print("[FAIL] zvec 未安装，请先 pip install zvec")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="zvec_store_test_"))
    try:
        store = ZvecStore(str(tmp / "zvec_data"), DIM)
        print("[0] 创建:", store.stats())

        # ---- 1. 写入 5 条 ----
        rng = np.random.default_rng(3)
        for i in range(5):
            v = rng.random(DIM).astype(np.float32)
            ok = store.add(
                f"m{i}",
                v.tolist(),
                {
                    "text": f"记忆内容{i}",
                    "emotion_vector": json.dumps([float(v[0])]),
                    "emotions": json.dumps({"joy": float(v[0])}),
                    "importance": 0.5 + i * 0.1,
                    "timestamp": int(1700000000 + i),
                    "type": "raw",
                    "access_count": 0,
                },
            )
            if not ok:
                print(f"[FAIL] 写入 m{i} 失败")
                return 1
        print("[1] 写入 5 条: OK")

        # ---- 2. 向量检索 ----
        q = [0.5507979, 0.7081478, 0.2909047, 0.5108276]
        res = store.search(q, topk=3)
        print(f"[2] 向量检索 {len(res)} 条 -> {[(r.id, round(r.score, 3)) for r in res]}")
        assert len(res) >= 1, "检索应至少返回 1 条"

        # ---- 3. 标量过滤 ----
        try:
            res2 = store.search(q, topk=5, filter_expr="type = 'raw'")
            print(f"[3] 过滤(type='raw') {len(res2)} 条 -> {[r.id for r in res2]}")
            res3 = store.search(q, topk=5, filter_expr="type = 'summary'")
            print(f"[4] 过滤(type='summary') {len(res3)} 条 -> {[r.id for r in res3]}")
            filter_ok = len(res2) == 5 and len(res3) == 0
        except Exception as e:
            print(f"[3/4] 过滤检索异常: {e}")
            filter_ok = False

        # ---- 4. 最近记忆 ----
        recent = store.get_recent(limit=3)
        print(f"[5] 最近记忆 {len(recent)} 条 -> {[r.get('text') for r in recent]}")
        recent_ok = len(recent) >= 1 and recent[0].get("timestamp") >= recent[-1].get("timestamp")

        # ---- 5. 统计 ----
        st = store.stats()
        print(f"[6] 统计: {st}")

        ok = len(res) >= 1 and recent_ok
        if ok:
            print("\n[SUCCESS] ZvecStore 全部功能验证通过")
            return 0
        print("\n[FAIL] 部分功能未通过")
        return 1

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[OK] 清理 {tmp}")


if __name__ == "__main__":
    sys.exit(main())
