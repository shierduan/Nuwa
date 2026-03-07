"""
依赖检查模块 (Dependencies Check Module)

提供统一的依赖检查和导入管理，确保可选依赖的优雅降级。
"""

import sys
from typing import Tuple, Optional

# 存储导入状态
_import_results = {}


def check_and_import_optional(name: str, module_name: str, required: bool = False) -> Tuple[bool, Optional[object]]:
    """
    检查并导入可选依赖
    
    Args:
        name: 依赖的名称（用于显示）
        module_name: 模块的实际名称
        required: 是否为必需依赖
        
    Returns:
        (是否成功，导入的模块或 None)
    """
    if name in _import_results:
        return _import_results[name]
    
    try:
        module = __import__(module_name, fromlist=[''])
        _import_results[name] = (True, module)
        return True, module
    except ImportError as e:
        _import_results[name] = (False, None)
        if required:
            print(f"[ERROR] 错误：缺少必需依赖 {name}")
            print(f"   请运行：pip install {module_name}")
            print(f"   详细错误：{e}")
            sys.exit(1)
        else:
            print(f"[WARN]  警告：{name} 未安装，相关功能将不可用")
            print(f"   如需使用，请运行：pip install {module_name}")
        return False, None


def get_pyarrow() -> Tuple[bool, Optional[object]]:
    """获取 pyarrow 模块"""
    return check_and_import_optional("PyArrow", "pyarrow", required=False)


def get_lancedb() -> Tuple[bool, Optional[object]]:
    """获取 lancedb 模块"""
    return check_and_import_optional("LanceDB", "lancedb", required=False)


def get_sentence_transformers() -> Tuple[bool, Optional[object]]:
    """获取 sentence-transformers 模块"""
    return check_and_import_optional("Sentence Transformers", "sentence_transformers", required=False)


def get_numpy() -> Tuple[bool, Optional[object]]:
    """获取 numpy 模块"""
    return check_and_import_optional("NumPy", "numpy", required=False)


def check_memory_dependencies() -> bool:
    """
    检查记忆系统相关的所有依赖
    
    Returns:
        是否所有依赖都可用
    """
    pyarrow_ok, _ = get_pyarrow()
    lancedb_ok, _ = get_lancedb()
    numpy_ok, _ = get_numpy()
    
    return pyarrow_ok and lancedb_ok and numpy_ok


def print_dependency_status():
    """打印所有依赖的状态"""
    print("\n📦 依赖状态检查:")
    
    deps = [
        ("PyArrow", get_pyarrow),
        ("LanceDB", get_lancedb),
        ("Sentence Transformers", get_sentence_transformers),
        ("NumPy", get_numpy),
    ]
    
    all_ok = True
    for name, getter in deps:
        ok, _ = getter()
        status = "[OK]" if ok else "[ERROR]"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False
    
    return all_ok
