"""
结构化日志系统

功能：
- 结构化日志输出
- 不同日志级别
- 控制台和文件输出
- JSON格式支持
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台彩色格式器"""
    
    COLORS = {
        "DEBUG": "\033[36m",    # 青色
        "INFO": "\033[32m",     # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",    # 红色
        "CRITICAL": "\033[41m", # 红底
        "RESET": "\033[0m"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"{color}[{timestamp}] {record.levelname:<8}{reset}"
        module = f"{record.module}:{record.lineno}"
        
        return f"{prefix} {module:<25} - {record.getMessage()}"


def setup_logger(
    name: str = "nuwa-config",
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        json_output: 是否输出JSON格式
        log_file: 日志文件路径
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "nuwa-config") -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    带上下文的日志记录
    
    Args:
        logger: 日志记录器
        level: 日志级别
        message: 消息
        **context: 额外上下文
    """
    log_level = getattr(logging, level.upper())
    
    # 创建带有额外字段的LogRecord
    extra = {"extra": context}
    logger.log(log_level, message, extra=extra)


# 便捷函数
def debug(logger: logging.Logger, message: str, **context):
    log_with_context(logger, "DEBUG", message, **context)

def info(logger: logging.Logger, message: str, **context):
    log_with_context(logger, "INFO", message, **context)

def warning(logger: logging.Logger, message: str, **context):
    log_with_context(logger, "WARNING", message, **context)

def error(logger: logging.Logger, message: str, **context):
    log_with_context(logger, "ERROR", message, **context)

def critical(logger: logging.Logger, message: str, **context):
    log_with_context(logger, "CRITICAL", message, **context)


__all__ = [
    "setup_logger",
    "get_logger",
    "log_with_context",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "StructuredFormatter",
    "ConsoleFormatter",
]
