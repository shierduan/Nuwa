"""
女娲统一日志配置 (Nuwa Logging Configuration)

设计目标：
- 消灭散落 300+ 处的裸 ``print()``，统一为结构化日志
- 支持控制台 + 文件双输出，文件侧带轮转，避免日志无限增长
- 提供 ``get_logger(name)`` 工厂，子模块按层级继承根 logger 配置
- 日志级别可通过环境变量 ``NUWA_LOG_LEVEL`` 控制，容器场景免改代码

关键约定：
- 业务模块使用 ``get_logger(__name__)``，不要直接 ``logging.getLogger``
- 结构化上下���通过 ``extra={"nuwa_context": {...}}`` 传递
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

# 根 logger 名称，所有子 logger 都挂在它下面
ROOT_LOGGER_NAME = "nuwa"

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-38s | %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

# 日志文件默认位置（相对项目根）
_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILE = "nuwa.log"

# 避免重复挂载 handler 的哨兵
_CONFIGURED = False


class _ContextFormatter(logging.Formatter):
    """在消息后追加结构化上下文，便于日志检索。"""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        context = getattr(record, "nuwa_context", None)
        if context:
            rendered = ", ".join(f"{k}={v!r}" for k, v in sorted(context.items()))
            base = f"{base}  | {rendered}"
        return base


def _resolve_level() -> int:
    """从环境变量解析日志级别，非法值回退 INFO。"""
    raw = os.environ.get("NUWA_LOG_LEVEL", "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def _resolve_log_file() -> Optional[Path]:
    """确定日志文件路径；``NUWA_LOG_FILE`` 为空字符串时禁用文件输出。"""
    env = os.environ.get("NUWA_LOG_FILE")
    if env is not None:
        if env.strip() == "":
            return None
        return Path(env)

    data_dir = os.environ.get("NUWA_LOG_DIR", str(_DEFAULT_LOG_DIR))
    return Path(data_dir) / _DEFAULT_LOG_FILE


def setup_logging(
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
    *,
    force: bool = False,
    to_file: Optional[bool] = None,
) -> logging.Logger:
    """配置女娲根 logger。

    Args:
        level: 日志级别，None 时取 ``NUWA_LOG_LEVEL`` 环境变量（默认 INFO）
        log_file: 日志文件路径，None 时自动解析
        force: 是否强制重新配置（已配置时默认直接返回）
        to_file: 是否输出到文件，None 时自动判断

    Returns:
        根 logger 实例
    """
    global _CONFIGURED

    root = logging.getLogger(ROOT_LOGGER_NAME)
    if _CONFIGURED and not force:
        return root

    # 清理旧 handler，避免重复输出
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    root.setLevel(level if level is not None else _resolve_level())
    root.propagate = False

    formatter = _ContextFormatter(_DEFAULT_FORMAT, datefmt=_DEFAULT_DATEFMT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(root.level)
    root.addHandler(console)

    target = log_file if log_file is not None else _resolve_log_file()
    enable_file = to_file if to_file is not None else (target is not None)
    if enable_file and target is not None:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                target, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(root.level)
            root.addHandler(file_handler)
        except OSError as exc:  # 日志文件不可写不应拖垮整个系统
            root.warning("日志文件初始化失败，仅启用控制台输出: %s", exc)

    _CONFIGURED = True
    return root


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取受女娲日志体系管理的 logger。

    Args:
        name: 通常传 ``__name__``。若已带 ``nuwa.`` 前缀则去重，
              避免出现 ``nuwa.nuwa.xxx`` 这种嵌套层级。

    Returns:
        绑定了 ``nuwa`` 根 handler 的 logger
    """
    if not name:
        return logging.getLogger(ROOT_LOGGER_NAME)

    if name == ROOT_LOGGER_NAME or name.startswith(ROOT_LOGGER_NAME + "."):
        full = name
    else:
        full = f"{ROOT_LOGGER_NAME}.{name}"

    logger = logging.getLogger(full)
    # 首次使用时确保根 logger 已配置，这样独立运行某个模块也能出日志
    if not _CONFIGURED:
        setup_logging()
    return logger


def log_exception(logger: logging.Logger, message: str, **context) -> None:
    """记录异常并附带结构化上下文。"""
    logger.error(message, exc_info=True, extra={"nuwa_context": context})


__all__ = [
    "ROOT_LOGGER_NAME",
    "setup_logging",
    "get_logger",
    "log_exception",
]
