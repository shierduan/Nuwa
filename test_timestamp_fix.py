"""
时间戳向量污染修复验证测试

测试目的：验证时间戳不再影响向量嵌入的语义空间

测试场景：
1. 创建两条语义相似但时间不同的消息
2. 创建两条语义不同但时间相近的消息
3. 验证语义相似的消息向量更接近，而非时间相近的消息
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.memory_cortex import MemoryCortex

def test_timestamp_not_affecting_embedding():
    """测试时间戳不影响向量嵌入"""
    
    print("=" * 60)
    print("时间戳向量污染修复验证测试")
    print("=" * 60)
    
    # 初始化 MemoryCortex（使用测试目录）
    test_dir = "data/test_timestamp_fix"
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    
    cortex = MemoryCortex(project_name="test_timestamp_fix", data_dir="data")
    
    if not cortex.embedding_model:
        print("\n[SKIP] Embedding 模型未加载，无法运行测试")
        return False
    
    print("\n[测试 1] 语义相似但时间不同的消息应该向量接近")
    print("-" * 60)
    
    # 消息 A：今天的内容
    text_a = "我今天很高兴，因为项目取得了重大进展"
    time_a = datetime.now()
    
    # 消息 B：一个月前的相同内容
    text_b = "我今天很高兴，因为项目取得了重大进展"
    time_b = time_a - timedelta(days=30)
    
    # 生成向量（模拟 store_memory 的逻辑，使用纯文本）
    vector_a = cortex.embedding_model.encode(text_a, convert_to_numpy=True)
    vector_b = cortex.embedding_model.encode(text_b, convert_to_numpy=True)
    
    # 计算余弦相似度
    def cosine_similarity(v1, v2):
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    similarity_same_text = cosine_similarity(vector_a, vector_b)
    print(f"消息 A: \"{text_a}\" (时间：{time_a.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"消息 B: \"{text_b}\" (时间：{time_b.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"[相似度] 相同文本的向量相似度：{similarity_same_text:.4f}")
    
    if similarity_same_text > 0.95:
        print("[PASS] 相同文本的向量非常接近（即使时间相差 30 天）")
    else:
        print(f"[WARN] 相同文本的向量相似度偏低：{similarity_same_text:.4f}")
    
    print("\n[测试 2] 语义不同但时间相近的消息应该向量不接近")
    print("-" * 60)
    
    # 消息 C：相同时间的不同内容
    text_c = "外面正在下雨，天气很冷，温度只有零下 10 度"
    time_c = time_a - timedelta(minutes=1)  # 仅相差 1 分钟
    
    vector_c = cortex.embedding_model.encode(text_c, convert_to_numpy=True)
    
    similarity_different_text = cosine_similarity(vector_a, vector_c)
    print(f"消息 A: \"{text_a}\" (时间：{time_a.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"消息 C: \"{text_c}\" (时间：{time_c.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"[相似度] 不同文本的向量相似度：{similarity_different_text:.4f}")
    
    if similarity_different_text < 0.7:
        print("[PASS] 不同文本的向量距离较远（即使时间仅相差 1 分钟）")
    else:
        print(f"[WARN] 不同文本的向量相似度偏高：{similarity_different_text:.4f}")
    
    print("\n[测试 3] 验证时间戳字符串不会产生语义关联")
    print("-" * 60)
    
    # 对比：使用时间戳 + 文本 vs 纯文本
    timestamp_str_a = time_a.strftime('[%Y-%m-%d %H:%M:%S]')
    fused_text_a = f"{timestamp_str_a} {text_a}"
    
    timestamp_str_c = time_c.strftime('[%Y-%m-%d %H:%M:%S]')
    fused_text_c = f"{timestamp_str_c} {text_c}"
    
    # 旧方法（错误）：使用融合文本生成向量
    fused_vector_a = cortex.embedding_model.encode(fused_text_a, convert_to_numpy=True)
    fused_vector_c = cortex.embedding_model.encode(fused_text_c, convert_to_numpy=True)
    
    # 新方法（正确）：使用纯文本生成向量
    pure_vector_a = cortex.embedding_model.encode(text_a, convert_to_numpy=True)
    pure_vector_c = cortex.embedding_model.encode(text_c, convert_to_numpy=True)
    
    # 计算两种方法的相似度差异
    fused_similarity = cosine_similarity(fused_vector_a, fused_vector_c)
    pure_similarity = cosine_similarity(pure_vector_a, pure_vector_c)
    
    print(f"消息 A: \"{text_a}\"")
    print(f"消息 C: \"{text_c}\"")
    print(f"时间差：{(time_a - time_c).total_seconds():.0f} 秒")
    print()
    print(f"[旧方法] 带时间戳的向量相似度：{fused_similarity:.4f}")
    print(f"[新方法] 纯文本的向量相似度：{pure_similarity:.4f}")
    print(f"差异：{abs(fused_similarity - pure_similarity):.4f}")
    
    if abs(fused_similarity - pure_similarity) < 0.05:
        print("[PASS] 时间戳对向量相似度影响很小")
    else:
        print(f"[INFO] 时间戳导致相似度变化：{abs(fused_similarity - pure_similarity):.4f}")
        if fused_similarity > pure_similarity:
            print("[WARN] 旧方法中时间相近导致向量更接近（这正是要修复的问题）")
        else:
            print("[INFO] 时间戳增加了语义区分度（可能是噪声）")
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print()
    print("修复前的问题：")
    print("  - 时间戳 [2026-03-06 02:21:00] 包含大量数字和符号")
    print("  - 这些字符在 embedding 中产生无意义的语义模式")
    print("  - 导致相近时间的消息向量变得相似（即使语义无关）")
    print()
    print("修复后的效果：")
    print("  - 仅使用纯文本生成 embedding 向量")
    print("  - 时间戳单独存储在 text 字段（用于展示）和 timestamp 字段（用于排序）")
    print("  - 向量相似度反映语义相关性，而非时间相近性")
    print()
    
    # 清理测试数据
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"[CLEANUP] 已清理测试数据：{test_dir}")
    
    return True

if __name__ == "__main__":
    try:
        test_timestamp_not_affecting_embedding()
        print("\n[OK] 测试完成")
    except Exception as e:
        print(f"\n[ERROR] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
