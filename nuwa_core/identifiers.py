"""
女娲统一 ID 生成 (Nuwa Identifier Generation)

背景：
    历史实现使用 ``f"{int(time.time() * 1000)}_{hash(text) % 10000}"`` 作为记忆 ID。
    这存在三个问题：

    1. **跨进程不稳定** —— Python 对 str 的 ``hash()`` 默认启用哈希随机化
       （PYTHONHASHSEED），同一段文本在不同进程会得到不同后缀。
       重启后无法通过内容反推 ID，调试与数据迁移都受影响。
    2. **易碰撞** —— 后缀只有 10000 个取值空间，同毫秒写入两条相似文本
       极易产生相同 ID，导致后者静默覆盖前者。
    3. **不可复现** —— 测试无法构造确定的 ID。

本模块改用 ``blake2b`` 摘要（SHA-3 家族，与 hashlib 全平台可用），
取 8 字节 16 位十六进制作为内容指纹，配合微秒时间戳保证唯一性。
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Optional

# 内容指纹的十六进制长度（8 字节 = 64 bit）
_FINGERPRINT_LEN = 16


def content_fingerprint(text: str, length: int = _FINGERPRINT_LEN) -> str:
    """计算文本的稳定内容指纹。

    与内置 ``hash()`` 不同，blake2b 摘要是确定性的：同样的输入在任意进程、
    任意时刻都会得到同样的输出。

    Args:
        text: 原始文本
        length: 指纹十六进制长度，默认 16（64 bit）

    Returns:
        小写十六进制字符串
    """
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).hexdigest()
    return digest[:length]


def generate_memory_id(text: str, timestamp: Optional[float] = None) -> str:
    """生成记忆 ID。

    格式：``{微秒时间戳}_{内容指纹}``

    - 时间戳保证同一内容在不同时间的写入互不覆盖
    - 内容指纹跨进程稳定，便于按内容定位与幂等写入

    Args:
        text: 记忆正文
        timestamp: 可选的 Unix 时间戳（秒），默认取当前时间

    Returns:
        形如 ``1730000000123456_a3f9c1e20b8d4f57`` 的 ID
    """
    if timestamp is None:
        micros = int(time.time() * 1_000_000)
    else:
        micros = int(float(timestamp) * 1_000_000)
    return f"{micros}_{content_fingerprint(text)}"


def generate_session_id() -> str:
    """生成会话 ID（带时间前缀，便于日志按时间检索）。"""
    return f"s{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def generate_request_id(prefix: str = "req") -> str:
    """生成请求追踪 ID。"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


__all__ = [
    "content_fingerprint",
    "generate_memory_id",
    "generate_session_id",
    "generate_request_id",
]
