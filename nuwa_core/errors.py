"""
女娲异常体系 (Nuwa Exception Hierarchy)

设计目标：
- 用明确的异常类型替代散落各处的裸 ``except:``，让故障可被捕获、可被分类、可被观测
- 所有异常都携带上下文（``context`` 字典），便于日志与指标系统提取结构化信息
- 异常层级保持扁平，捕获顺序符合直觉：``NuwaError`` -> ``NuwaConfigError`` -> ``NuwaStorageError`` -> ...

使用约定：
    from .errors import NuwaStorageError, handle_errors

    with handle_errors(NuwaStorageError, "写入记忆"):
        store.add(...)
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class NuwaError(Exception):
    """女娲系统所有自定义异常的基类。"""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: Dict[str, Any] = context

    def __str__(self) -> str:
        if not self.context:
            return self.message
        rendered = ", ".join(f"{k}={v!r}" for k, v in sorted(self.context.items()))
        return f"{self.message} ({rendered})"

    def to_dict(self) -> Dict[str, Any]:
        """转为可 JSON 序列化的结构化表示，供指标上报使用。"""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "context": dict(self.context),
        }


# ---------------------------------------------------------------------------
# 配置类异常
# ---------------------------------------------------------------------------
class NuwaConfigError(NuwaError):
    """配置文件缺失、字段非法、参数越界。"""


class DependencyMissingError(NuwaError):
    """必需的第三方依赖未安装。"""


# ---------------------------------------------------------------------------
# 存储类异常
# ---------------------------------------------------------------------------
class NuwaStorageError(NuwaError):
    """向量库 / 数据库 / 文件存储的读写失败。"""


class SchemaMismatchError(NuwaStorageError):
    """集合 schema 与预期不符，需要重建。"""


class DimensionMismatchError(NuwaStorageError):
    """向量维度与集合定义不一致。"""


# ---------------------------------------------------------------------------
# 模型类异常
# ---------------------------------------------------------------------------
class NuwaModelError(NuwaError):
    """LLM 调用失败、超时或返回内容无法解析。"""


class LLMTimeoutError(NuwaModelError):
    """模型调用超出指定时限。"""


class LLMResponseParseError(NuwaModelError):
    """模型返回内容不符合预期结构。"""


# ---------------------------------------------------------------------------
# 记忆子系统异常
# ---------------------------------------------------------------------------
class NuwaMemoryError(NuwaError):
    """记忆子系统通用异常。"""


class ConsolidationError(NuwaMemoryError):
    """记忆巩固流程失败。"""


class ConsolidationTimeoutError(ConsolidationError):
    """巩固流程超时。"""


class DreamCycleError(NuwaMemoryError):
    """梦境周期执行失败。"""


# ---------------------------------------------------------------------------
# 状态与内核异常
# ---------------------------------------------------------------------------
class NuwaStateError(NuwaError):
    """状态载入 / 持久化失败。"""


class KernelError(NuwaError):
    """内核编排失败。"""


class ChannelError(NuwaError):
    """外部通道（飞书 / 钉钉 / 企业微信）异常。"""


class handle_errors:
    """上下文管理器：把特定异常包装为统一异常类型并补充上下文。

    用法::

        with handle_errors(NuwaStorageError, "写入记忆", memory_id=mid):
            store.add(...)

    未被捕获的异常会记录一条 error 日志后以 ``NuwaStorageError`` 重新抛出，
    避免异常在调用栈里丢失原始语义。
    """

    __slots__ = ("_error_type", "_operation", "_extra", "_logger")

    def __init__(
        self,
        error_type: type,
        operation: str,
        logger: Optional[Any] = None,
        **extra: Any,
    ) -> None:
        self._error_type = error_type
        self._operation = operation
        self._extra = extra
        self._logger = logger

    def __enter__(self) -> "handle_errors":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            return False
        # 已经是我们自己的异常类型就不再包装，避免套娃
        if isinstance(exc, self._error_type):
            return False
        if isinstance(exc, NuwaError):
            return False

        from .logging_config import get_logger

        logger = self._logger or get_logger("nuwa.errors")
        context = {"operation": self._operation, "original": type(exc).__name__, **self._extra}
        logger.error(
            "%s 失败: %s",
            self._operation,
            exc,
            exc_info=True,
            extra={"nuwa_context": context},
        )
        raise self._error_type(str(exc), **context) from exc
