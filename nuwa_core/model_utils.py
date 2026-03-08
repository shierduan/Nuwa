"""
模型工具函数 (Model Utilities)

提供模型下载、路径管理等辅助功能。
"""

import os
from pathlib import Path
from typing import Optional


# Embedding 模型配置
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIR = os.path.join("models", "embedding")


def ensure_embedding_model_dir(SentenceTransformer=None) -> Optional[str]:
    """
    确保 Embedding 模型目录存在，并返回模型路径
    
    Args:
        SentenceTransformer: SentenceTransformer 类（用于检查是否可用）
        
    Returns:
        模型路径字符串，如果失败则返回 None
    """
    # 获取项目根目录
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    # 模型目录
    model_dir = project_root / DEFAULT_EMBEDDING_DIR
    
    # 检查目录是否存在
    if not model_dir.exists():
        try:
            model_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] 创建模型目录：{model_dir}")
        except Exception as e:
            print(f"[WARN] 创建模型目录失败：{e}")
            return None
    
    # 检查模型文件是否存在
    model_path = model_dir / "all-MiniLM-L6-v2"
    
    if model_path.exists():
        return str(model_path)
    
    # 如果提供了 SentenceTransformer，尝试自动下载
    if SentenceTransformer is not None:
        try:
            print(f"[INFO] 尝试下载 Embedding 模型：{EMBEDDING_MODEL_NAME}")
            # 使用 SentenceTransformer 下载模型
            model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            # 保存模型到本地
            model.save(str(model_path))
            print(f"[OK] 模型已保存到：{model_path}")
            return str(model_path)
        except Exception as e:
            print(f"[WARN] 自动下载模型失败：{e}")
            return None
    
    return None
