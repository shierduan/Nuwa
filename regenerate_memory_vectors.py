"""
记忆向量重新生成脚本

用途：为已有的记忆数据重新生成向量（使用纯文本，不包含时间戳前缀）

背景：
- 旧版本：向量生成时使用 [时间戳] 文本，导致时间戳污染语义空间
- 新版本：仅使用纯文本生成向量，时间戳单独存储用于展示

此脚本会：
1. 读取所有现有的记忆数据
2. 从 text 字段中提取纯文本（移除时间戳前缀）
3. 使用纯文本重新生成向量嵌入
4. 更新数据库中的记录
"""

import os
import sys
import re
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.memory_cortex import MemoryCortex

def extract_pure_text(text_with_timestamp: str) -> str:
    """
    从包含时间戳的文本中提取纯文本
    
    Args:
        text_with_timestamp: 格式为 "[YYYY-MM-DD HH:MM:SS] 文本内容" 的字符串
    
    Returns:
        纯文本内容（不包含时间戳前缀）
    """
    # 匹配时间戳前缀的正则表达式
    timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*')
    
    # 如果匹配到时间戳前缀，移除它
    match = timestamp_pattern.match(text_with_timestamp)
    if match:
        return text_with_timestamp[match.end():].strip()
    
    # 没有时间戳前缀，直接返回
    return text_with_timestamp.strip()

def regenerate_all_vectors(project_name: str = "nuwa", data_dir: str = "data"):
    """
    为所有记忆重新生成向量
    
    Args:
        project_name: 项目名称（默认 "nuwa"）
        data_dir: 数据目录（默认 "data"）
    
    Returns:
        int: 成功更新的记忆数量
    """
    print("=" * 70)
    print("记忆向量重新生成工具")
    print("=" * 70)
    print()
    print(f"项目：{project_name}")
    print(f"数据目录：{data_dir}")
    print()
    
    # 初始化 MemoryCortex
    cortex = MemoryCortex(project_name=project_name, data_dir=data_dir)
    
    if not cortex.embedding_model:
        print("[ERROR] Embedding 模型未加载，无法重新生成向量")
        return 0
    
    if not cortex.table:
        print("[ERROR] 记忆表未初始化，无法重新生成向量")
        return 0
    
    try:
        # 获取所有记忆
        print("[INFO] 正在加载所有记忆...")
        df = cortex.table.to_pandas()
        
        if df.empty:
            print("[INFO] 没有记忆需要更新")
            return 0
        
        total_count = len(df)
        print(f"[INFO] 共找到 {total_count} 条记忆")
        print()
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # 遍历所有记忆
        for idx, row in df.iterrows():
            memory_id = str(row.get("id", ""))
            old_text = str(row.get("text", "")).strip()
            
            # 跳过空记录
            if not old_text:
                skipped_count += 1
                continue
            
            old_vector = row.get("vector")
            
            # 跳过无效向量
            if old_vector is None or (isinstance(old_vector, list) and len(old_vector) == 0):
                error_count += 1
                continue
            
            # 提取纯文本
            pure_text = extract_pure_text(old_text)
            
            # 检查是否需要更新
            if pure_text == old_text:
                # 已经是纯文本，不需要更新
                skipped_count += 1
                continue
            
            # 重新生成向量
            try:
                new_vector = cortex.embedding_model.encode(pure_text, convert_to_numpy=True)
                
                # 检查向量维度
                if len(new_vector) != cortex.VECTOR_DIM:
                    print(f"[WARN] 记忆 {memory_id} 向量维度不匹配，跳过")
                    error_count += 1
                    continue
                
                # 准备更新数据
                update_data = {
                    "id": memory_id,
                    "text": old_text,  # 保持原文本（包含时间戳前缀用于展示）
                    "vector": new_vector.tolist(),  # 使用新生成的纯文本向量
                }
                
                # 获取其他字段
                full_data = {
                    "id": memory_id,
                    "text": old_text,
                    "vector": new_vector.tolist(),
                    "emotion_vector": str(row.get("emotion_vector", "")),
                    "timestamp": float(row.get("timestamp", 0.0)),
                    "importance": float(row.get("importance", 0.5)),
                    "type": str(row.get("type", "raw")),
                    "emotions": str(row.get("emotions", "{}")),
                    "access_count": int(row.get("access_count", 0)),
                }
                
                # 删除旧记录
                cortex.table.delete(f"id = '{memory_id}'")
                
                # 插入新记录
                cortex.table.add([full_data])
                
                updated_count += 1
                
                # 进度显示
                if (updated_count % 10) == 0:
                    print(f"[PROGRESS] 已更新 {updated_count}/{total_count} 条记忆")
                
            except Exception as e:
                print(f"[ERROR] 记忆 {memory_id} 更新失败：{e}")
                error_count += 1
                continue
        
        # 输出统计
        print()
        print("=" * 70)
        print("更新完成")
        print("=" * 70)
        print(f"总记忆数：{total_count}")
        print(f"已更新：{updated_count} 条")
        print(f"已跳过：{skipped_count} 条（已经是纯文本向量）")
        print(f"失败：{error_count} 条")
        print()
        
        if updated_count > 0:
            print("[SUCCESS] 向量重新生成完成！")
            print()
            print("改进效果：")
            print("  - 向量相似度现在反映语义相关性，而非时间相近性")
            print("  - 时间戳不再污染向量空间")
            print("  - 检索结果更加准确")
        else:
            print("[INFO] 没有需要更新的记忆")
        
        return updated_count
        
    except Exception as e:
        print(f"[ERROR] 重新生成向量失败：{e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # 可以从命令行参数指定项目名称
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    else:
        project_name = "nuwa"  # 默认项目名称
    
    if len(sys.argv) > 2:
        data_dir = sys.argv[2]
    else:
        data_dir = "data"  # 默认数据目录
    
    # 执行重新生成
    regenerate_all_vectors(project_name=project_name, data_dir=data_dir)
