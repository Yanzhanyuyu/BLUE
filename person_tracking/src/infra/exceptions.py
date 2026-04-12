"""自定义异常类

定义系统专用异常类型，用于精确错误处理和诊断。

异常层次结构：
    TrackingSystemError (基类)
    ├── ModelLoadError      - 模型加载失败
    ├── VideoLoadError      - 视频/摄像头加载失败
    ├── ConfigurationError  - 配置错误
    ├── InferenceError      - 推理过程错误
    └── ExportError         - 导出错误
"""

from typing import Optional, Any


class TrackingSystemError(Exception):
    """基础异常类

    所有系统异常的基类，提供统一的异常接口。

    Attributes:
        message: 错误消息
        details: 额外错误详情（可选）
    """

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        """初始化异常

        Args:
            message: 错误消息
            details: 额外错误详情（如原始异常、上下文数据等）
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回异常字符串表示"""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ModelLoadError(TrackingSystemError):
    """模型加载失败

    当检测模型无法加载时抛出。

    常见原因：
        - 模型文件不存在
        - 模型格式不正确
        - 版本不兼容
        - GPU内存不足
    """

    def __init__(
        self,
        message: str = "Failed to load model",
        model_path: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        """初始化模型加载异常

        Args:
            message: 错误消息
            model_path: 模型文件路径
            details: 额外详情
        """
        self.model_path = model_path
        if model_path:
            message = f"{message}: {model_path}"
        super().__init__(message, details)


class VideoLoadError(TrackingSystemError):
    """视频/摄像头加载失败

    当视频文件或摄像头无法打开时抛出。

    常见原因：
        - 文件不存在
        - 格式不支持
        - 摄像头被占用
        - 权限问题
    """

    def __init__(
        self,
        message: str = "Failed to load video source",
        source: Optional[str | int] = None,
        details: Optional[Any] = None,
    ) -> None:
        """初始化视频加载异常

        Args:
            message: 错误消息
            source: 视频源路径或摄像头索引
            details: 额外详情
        """
        self.source = source
        if source is not None:
            message = f"{message}: {source}"
        super().__init__(message, details)


class ConfigurationError(TrackingSystemError):
    """配置错误

    当配置文件或参数无效时抛出。

    常见原因：
        - 配置文件格式错误
        - 必需参数缺失
        - 参数值超出范围
        - 类型不匹配
    """

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        """初始化配置异常

        Args:
            message: 错误消息
            config_key: 配置项键名
            details: 额外详情
        """
        self.config_key = config_key
        if config_key:
            message = f"{message} (key: {config_key})"
        super().__init__(message, details)


class InferenceError(TrackingSystemError):
    """推理错误

    当检测或跟踪推理过程出错时抛出。

    常见原因：
        - 输入数据格式错误
        - 内存不足
        - GPU错误
        - 模型内部错误
    """

    def __init__(
        self,
        message: str = "Inference error",
        frame_id: Optional[int] = None,
        details: Optional[Any] = None,
    ) -> None:
        """初始化推理异常

        Args:
            message: 错误消息
            frame_id: 发生错误的帧ID
            details: 额外详情
        """
        self.frame_id = frame_id
        if frame_id is not None:
            message = f"{message} at frame {frame_id}"
        super().__init__(message, details)


class ExportError(TrackingSystemError):
    """导出错误

    当结果导出过程出错时抛出。

    常见原因：
        - 文件写入权限问题
        - 磁盘空间不足
        - 格式转换错误
        - 路径不存在
    """

    def __init__(
        self,
        message: str = "Export error",
        output_path: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        """初始化导出异常

        Args:
            message: 错误消息
            output_path: 输出文件路径
            details: 额外详情
        """
        self.output_path = output_path
        if output_path:
            message = f"{message}: {output_path}"
        super().__init__(message, details)
