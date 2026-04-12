"""基础设施模块

包含：
- config: 配置管理
- logger: 日志配置
- exceptions: 自定义异常
"""

from .config import Config, load_config
from .logger import setup_logger
from .exceptions import (
    TrackingSystemError,
    ModelLoadError,
    VideoLoadError,
    ConfigurationError,
    InferenceError,
    ExportError,
)

__all__ = [
    "Config",
    "load_config",
    "setup_logger",
    "TrackingSystemError",
    "ModelLoadError",
    "VideoLoadError",
    "ConfigurationError",
    "InferenceError",
    "ExportError",
]
