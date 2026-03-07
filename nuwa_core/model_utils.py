import os
import threading
from typing import Optional, Callable

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_ENV_VAR = "NUWA_EMBEDDING_MODEL_PATH"
MODEL_CACHE_ROOT_VAR = "NUWA_MODEL_CACHE_DIR"

# 默认缓存目录：~/.nuwa/models/all-MiniLM-L6-v2
_default_cache_root = os.environ.get(
    MODEL_CACHE_ROOT_VAR,
    os.path.join(os.path.expanduser("~"), ".nuwa", "models"),
)
DEFAULT_EMBEDDING_DIR = os.path.join(_default_cache_root, EMBEDDING_MODEL_NAME)

_embedding_dir_cache: Optional[str] = None
_embedding_dir_lock = threading.Lock()


def _path_has_model(path: Optional[str]) -> bool:
    if not path:
        return False
    config_path = os.path.join(path, "config.json")
    return os.path.isdir(path) and os.path.exists(config_path)


def ensure_embedding_model_dir(loader_cls: Optional[Callable], verbose: bool = True) -> Optional[str]:
    """
    确保本地存在 embedding 模型目录；如果没有则下载一次。

    Args:
        loader_cls: SentenceTransformer 类（或兼容接口），用于下载模型
        verbose: 是否打印提示信息

    Returns:
        可用的本地模型目录路径；若失败则返回 None
    """
    global _embedding_dir_cache

    if loader_cls is None:
        return None

    with _embedding_dir_lock:
        if _path_has_model(_embedding_dir_cache):
            return _embedding_dir_cache

        candidates = []

        # 1) 环境变量显式指定
        env_path = os.environ.get(EMBEDDING_ENV_VAR)
        if env_path:
            candidates.append(env_path)

        # 2) 项目内自带的模型目录
        repo_dir = os.path.join(os.path.dirname(__file__), "models", EMBEDDING_MODEL_NAME)
        candidates.append(repo_dir)

        # 3) 默认缓存目录
        candidates.append(DEFAULT_EMBEDDING_DIR)

        for candidate in candidates:
            if _path_has_model(candidate):
                _embedding_dir_cache = candidate
                return candidate

        # 若所有候选均不存在，尝试下载到默认缓存
        target_dir = DEFAULT_EMBEDDING_DIR
        os.makedirs(target_dir, exist_ok=True)

        try:
            if verbose:
                print(f"📥 正在下载嵌入模型 {EMBEDDING_MODEL_NAME} 到 {target_dir} ...")
                # 检查是否设置了 HF_ENDPOINT 环境变量
                hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
                print(f"📡 使用模型源: {hf_endpoint}")
            # 下载模型
            model = loader_cls(EMBEDDING_MODEL_NAME)
            model.save(target_dir)
            _embedding_dir_cache = target_dir
            if verbose:
                print(f"✅ 嵌入模型已缓存到 {target_dir}")
            return target_dir
        except Exception as e:
            if verbose:
                print(f"❌ 下载嵌入模型失败：{e}")
                print("💡 尝试设置环境变量 HF_ENDPOINT 为国内源，例如：")
                print("   set HF_ENDPOINT=https://hf-mirror.com")
            return None

