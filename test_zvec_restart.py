"""
zvec 重启 / schema 演进验证：
1. 首次创建集合并写入
2. 模拟重启（重新 open 同一路径）→ 应成功读回
3. 旧 schema（缺 text 字段 / IP metric）→ 应自动销毁重建
用法: python test_zvec_restart.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import zvec
from nuwa_core.vector_store import ZvecStore, MemoryStore


def main():
    print("=" * 60)
    print("zvec 重启 / schema 演进验证")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp(prefix="nuwa_zvec_restart_"))
    try:
        path = str(tmp / "zvec")
        DIM = 8

        # ---- 1. 首次创建 ----
        s1 = ZvecStore(path, DIM)
        v = np.random.default_rng(1).random(DIM).astype(np.float32)
        s1.add("m0", v.tolist(), {
            "text": "重启前的记忆", "timestamp": 1000, "type": "raw",
            "importance": 0.5, "access_count": 0,
        })
        s1._collection.flush()
        print("[1] 首次创建并写入: OK")

        # ---- 2. 模拟重启（不 close，直接重新 open 会锁冲突，先 close）----
        s1._collection.close()
        s2 = ZvecStore(path, DIM)
        got = s2.fetch(["m0"])
        if "m0" not in got:
            print("[FAIL] 重启后无法读回记忆")
            return 1
        if got["m0"].fields.get("text") != "重启前的记忆":
            print(f"[FAIL] 重启后字段丢失: {got['m0'].fields}")
            return 1
        print("[2] 重启后读回: OK")

        # ---- 3. 旧 schema（无 text 字段 + IP metric）应被自动重建 ----
        s2._collection.close()
        old_schema = zvec.CollectionSchema(
            name="nuwa_memory",
            vectors=zvec.VectorSchema(
                "embedding", zvec.DataType.VECTOR_FP32, DIM,
                index_param=zvec.FlatIndexParam(metric_type=zvec.MetricType.IP),
            ),
            fields=[zvec.FieldSchema("timestamp", zvec.DataType.INT64, nullable=True)],
        )
        shutil.rmtree(path, ignore_errors=True)
        old = zvec.create_and_open(path=path, schema=old_schema)
        old.insert([zvec.Doc(id="legacy", vectors={"embedding": v.tolist()},
                             fields={"timestamp": 1})])
        old.close()
        print("[3] 已构造旧 schema 集合（缺 text 字段 / IP metric）")

        s3 = ZvecStore(path, DIM)
        fields = {f.name for f in s3._collection.schema.fields}
        metric = s3._collection.schema.vectors[0].index_param.metric_type
        metric_name = getattr(metric, "name", str(metric))
        if "text" not in fields:
            print(f"[FAIL] schema 未重建，字段: {fields}")
            return 1
        if metric_name != "COSINE":
            print(f"[FAIL] metric 未迁移，当前: {metric_name}")
            return 1
        print(f"[3] schema 自动重建: OK (fields={sorted(fields)}, metric={metric_name})")

        # ---- 4. 重建后可正常写入 ----
        s3.add("m1", v.tolist(), {"text": "重建后的记忆", "timestamp": 2000,
                                  "type": "raw", "importance": 0.6, "access_count": 0})
        res = s3.search(v.tolist(), topk=1)
        if not res or res[0].id != "m1":
            print("[FAIL] 重建后写入或检索失败")
            return 1
        print(f"[4] 重建后读写: OK (top1={res[0].id}, score={res[0].score:.3f})")

        print("\n[SUCCESS] 重启 / schema 演进验证通过")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
