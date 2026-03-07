"""
记忆向量修复验证脚本

验证已更新的记忆向量是否正确（使用纯文本生成，而非包含时间戳）
"""

import os
import sys
import numpy as np
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.memory_cortex import MemoryCortex

def verify_vectors(project_name: str = "nuwa", data_dir: str = "data"):
    """
    验证记忆向量是否正确
    
    Args:
        project_name: 项目名称
        data_dir: 数据目录
    """
    print("=" * 70)
    print("记忆向量修复验证")
    print("=" * 70)
    print()
    
    # 初始化 MemoryCortex
    cortex = MemoryCortex(project_name=project_name, data_dir=data_dir)
    
    if not cortex.embedding_model:
        print("[ERROR] Embedding 模型未加载")
        return
    
    if not cortex.table:
        print("[ERROR] 记忆表未初始化")
        return
    
    # 获取所有记忆
    df = cortex.table.to_pandas()
    
    if df.empty:
        print("[INFO] 没有记忆数据")
        return
    
    print(f"共检查 {len(df)} 条记忆\n")
    
    # 随机抽样检查
    sample_size = min(5, len(df))
    samples = df.sample(n=sample_size, random_state=42)
    
    print(f"[抽样检查] 随机抽取 {sample_size} 条记忆进行验证\n")
    print("-" * 70)
    
    all_correct = True
    
    for idx, row in samples.iterrows():
        memory_id = row.get("id", "")
        stored_text = str(row.get("text", ""))
        stored_vector = row.get("vector")
        
        # 提取纯文本
        import re
        timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*')
        match = timestamp_pattern.match(stored_text)
        
        if match:
            pure_text = stored_text[match.end():].strip()
            has_timestamp_prefix = True
        else:
            pure_text = stored_text.strip()
            has_timestamp_prefix = False
        
        # 重新生成向量
        regenerated_vector = cortex.embedding_model.encode(pure_text, convert_to_numpy=True)
        
        # 计算余弦相似度
        def cosine_similarity(v1, v2):
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        
        # 将存储的向量转换为 numpy
        if isinstance(stored_vector, list):
            stored_vec = np.array(stored_vector, dtype=np.float32)
        else:
            stored_vec = np.array(stored_vector, dtype=np.float32)
        
        similarity = cosine_similarity(stored_vec, regenerated_vector)
        
        # 判断是否正确
        is_correct = similarity > 0.98  # 相似度很高说明是使用纯文本生成的
        
        status = "[OK]" if is_correct else "[FAIL]"
        print(f"{status} 记忆 ID: {memory_id}")
        print(f"     时间戳前缀：{'有' if has_timestamp_prefix else '无'}")
        print(f"     纯文本：{pure_text[:50]}...")
        print(f"     向量相似度：{similarity:.4f}")
        
        if not is_correct:
            all_correct = False
            print(f"     [WARN] 向量可能不是使用纯文本生成的！")
        
        print()
    
    print("-" * 70)
    print()
    
    if all_correct:
        print("[SUCCESS] 所有抽检的记忆向量都正确！")
        print()
        print("修复效果确认：")
        print("  ✓ 向量使用纯文本生成（不包含时间戳）")
        print("  ✓ 语义相似度准确反映内容相关性")
        print("  ✓ 时间戳不再影响向量空间")
    else:
        print("[WARN] 发现部分记忆向量可能有问题")
        print("建议运行 regenerate_memory_vectors.py 重新生成向量")
    
    print()
    
    # 额外测试：检查时间相近但语义不同的记忆
    print("-" * 70)
    print("[进阶测试] 检查时间相近但语义不同的记忆向量距离")
    print()
    
    # 按时间戳排序
    df_sorted = df.sort_values("timestamp", ascending=True)
    
    # 检查相邻时间的记忆
    if len(df_sorted) >= 2:
        adjacent_pairs = []
        for i in range(len(df_sorted) - 1):
            row1 = df_sorted.iloc[i]
            row2 = df_sorted.iloc[i + 1]
            
            time_diff = abs(float(row2["timestamp"]) - float(row1["timestamp"]))
            
            # 只检查时间差在 1 小时内的记忆对
            if time_diff < 3600:  # 3600 秒 = 1 小时
                text1 = str(row1["text"])
                text2 = str(row2["text"])
                
                # 提取纯文本
                import re
                timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*')
                pure1 = timestamp_pattern.sub('', text1).strip()
                pure2 = timestamp_pattern.sub('', text2).strip()
                
                # 如果文本不同，计算向量相似度
                if pure1 != pure2 and len(pure1) > 10 and len(pure2) > 10:
                    vec1 = cortex.embedding_model.encode(pure1, convert_to_numpy=True)
                    vec2 = cortex.embedding_model.encode(pure2, convert_to_numpy=True)
                    
                    sim = cosine_similarity(vec1, vec2)
                    adjacent_pairs.append((time_diff, sim, pure1[:30], pure2[:30]))
        
        if adjacent_pairs:
            # 按时间差排序
            adjacent_pairs.sort(key=lambda x: x[0])
            
            print(f"找到 {len(adjacent_pairs)} 对时间相近（<1 小时）但语义不同的记忆")
            print()
            
            # 显示最接近的 3 对
            for i, (time_diff, sim, text1, text2) in enumerate(adjacent_pairs[:3]):
                time_min = time_diff / 60
                print(f"第 {i+1} 对:")
                print(f"  时间差：{time_min:.1f} 分钟")
                print(f"  文本 1: {text1}...")
                print(f"  文本 2: {text2}...")
                print(f"  向量相似度：{sim:.4f}")
                
                if sim < 0.7:
                    print(f"  [OK] 语义不同的记忆向量距离较远")
                else:
                    print(f"  [INFO] 语义相似度较高（可能是相关对话）")
                print()
            
            # 统计平均相似度
            avg_sim = sum(p[1] for p in adjacent_pairs) / len(adjacent_pairs)
            print(f"平均向量相似度：{avg_sim:.4f}")
            
            if avg_sim < 0.6:
                print("[OK] 时间相近的记忆向量不会仅因时间而变得相似")
            else:
                print("[INFO] 部分时间相近的记忆语义也相近（正常现象）")
        else:
            print("[INFO] 没有找到时间相近的记忆对")

if __name__ == "__main__":
    project_name = sys.argv[1] if len(sys.argv) > 1 else "nuwa"
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    
    verify_vectors(project_name=project_name, data_dir=data_dir)
