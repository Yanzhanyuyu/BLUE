"""日志配置模块

使用 Loguru 配置系统日志，支持：
- 控制台彩色输出
- 文件日志（自动轮转）
- 多级别日志过滤
- 结构化日志格式
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger

# Type alias for Logger (loguru's logger is a Logger instance)
Logger = type(logger)


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_string: Optional[str] = None,
) -> Logger:
    """配置系统日志器

    配置 Loguru 日志器，支持控制台和文件输出。

    Args:
        level: 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_file: 日志文件路径，为 None 则不写入文件
        rotation: 日志轮转大小/时间，如 "10 MB" 或 "1 day"
        retention: 日志保留时间，如 "7 days"
        format_string: 自定义日志格式，为 None 使用默认格式

    Returns:
        配置好的 Logger 实例

    Example:
        >>> logger = setup_logger(
        ...     level="DEBUG",
        ...     log_file="logs/tracking.log",
        ...     rotation="10 MB"
        ... )
        >>> logger.info("System started")
        >>> logger.debug("Processing frame 100")
    """
    # 移除默认处理器
    logger.remove()

    # 默认日志格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 添加控制台处理器
    logger.add(
        sys.stdout,
        level=level,
        format=format_string,
        colorize=True,
        enqueue=True,
    )

    # 添加文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 文件格式（不带颜色）
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )

        logger.add(
            log_file,
            level=level,
            format=file_format,
            rotation=rotation,
            retention=retention,
            compression="zip",
            enqueue=True,
            encoding="utf-8",
        )

    return logger


# 模块级日志器实例
# 默认配置，可在应用启动时重新配置
_default_logger = setup_logger()


def get_logger(name: Optional[str] = None) -> Logger:
    """获取日志器

    获取带有模块名称的日志器实例。

    Args:
        name: 模块名称，为 None 返回默认日志器

    Returns:
        Logger 实例

    Example:
        >>> log = get_logger("detector")
        >>> log.info("Model loaded successfully")
    """
    if name:
        return logger.bind(name=name)
    return logger
