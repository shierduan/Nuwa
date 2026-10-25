"""
探索 zvec：update 能力 + filter 表达式语法（为记忆强化做准备）
"""
import inspect
import shutil

import numpy as np
import zvec

print("update 签名:", inspect.signature(zvec.Collection.update))
print()

shutil.rmtree("./tmp_zvec_explore", ignore_errors=True)

schema = zvec.CollectionSchema(
    name="t",
    vectors=zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, 4),
    fields=[
        zvec.FieldSchema("text", zvec.DataType.STRING, nullable=True),
        zvec.FieldSchema("importance", zvec.DataType.FLOAT, nullable=True),
        zvec.FieldSchema("timestamp", zvec.DataType.INT64, nullable=True),
        zvec.FieldSchema("type", zvec.DataType.STRING, nullable=True),
    ],
)
c = zvec.create_and_open(path="./tmp_zvec_explore", schema=schema)

c.insert([
    zvec.Doc(id="a1", vectors={"embedding": [0.1, 0.2, 0.3, 0.4]},
              fields={"text": "第一条", "importance": 0.6,
                     "timestamp": 1700000001, "type": "raw"}),
    zvec.Doc(id="a2", vectors={"embedding": [0.4, 0.3, 0.2, 0.1]},
              fields={"text": "第二条", "importance": 0.8,
                     "timestamp": 1700000002, "type": "summary"}),
])
print("插入 2 条: OK")

q = [0.1, 0.2, 0.3, 0.4]

# 测试 filter 语法
tests = [
    ("无过滤", None),
    ("type='raw'", "type = 'raw'"),
    ("importance > 0.5", "importance > 0.5"),
    ("type='raw' AND importance>0.5", "type = 'raw' AND importance > 0.5"),
    ("timestamp > 1700000001", "timestamp > 1700000001"),
]

print("\n=== filter 语法测试 ===")
for name, f in tests:
    try:
        kwargs = {"topk": 10}
        if f:
            kwargs["filter"] = f
        docs = c.query(zvec.Query("embedding", vector=q), **kwargs)
        print(f"  {name}: {len(docs)} 条 -> {[getattr(d, 'id', '') for d in docs]}")
    except Exception as e:
        print(f"  {name}: [ERR] {type(e).__name__}: {e}")

# 测试 update（fetch + upsert 模式）
print("\n=== update 测试（fetch + upsert）===")
try:
    got = c.fetch(["a1"])
    doc = got["a1"]
    print("  fetch 到:", doc.id)
    print("  fields:", doc.fields)
    print("  has_vector:", doc.has_vector("embedding"))

    if doc.has_vector("embedding"):
        vec = doc.vector("embedding")
        new_fields = dict(doc.fields)
        new_fields["access_count"] = 5
        c.upsert([
            zvec.Doc(id="a1", vectors={"embedding": vec}, fields=new_fields)
        ])
        print("  upsert 成功")

        got2 = c.fetch(["a1"])
        print("  更新后 access_count:", got2["a1"].fields.get("access_count"))

except Exception as e:
    print(f"  update 异常: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

shutil.rmtree("./tmp_zvec_explore", ignore_errors=True)
print("\n[OK] 清理完成")
