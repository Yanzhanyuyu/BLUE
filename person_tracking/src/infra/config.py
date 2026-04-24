"""配置管理模块

使用 Pydantic 进行配置验证，支持：
- YAML 配置文件加载
- 类型安全的配置验证
- 默认值支持
- 环境变量覆盖（可选）

配置结构：
    Config
    ├── detector: DetectorConfig
    ├── tracker: TrackerConfig
    ├── visualizer: VisualizerConfig
    ├── pipeline: PipelineConfig
    └── logging: LoggingConfig
"""

from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"
DEFAULT_BYTETRACK_CONFIG_PATH = PROJECT_ROOT / "config" / "bytetrack.yaml"


# ============================================================================
# 配置类定义
# ============================================================================


class DetectorConfig(BaseModel):
    """检测器配置

    配置 YOLOv11 检测模型参数。

    Attributes:
        model_path: 模型文件路径或名称（如 "yolo11n.pt"）
        confidence_threshold: 检测置信度阈值 [0, 1]
        iou_threshold: NMS IOU 阈值 [0, 1]
        device: 推理设备
        classes: 要检测的类别 ID 列表（COCO: person=0）
        imgsz: 推理图像尺寸
    """

    model_path: str = Field(
        default="yolo11n.pt",
        description="YOLOv11 模型路径",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="检测置信度阈值",
    )
    iou_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="NMS IOU 阈值",
    )
    device: Literal["cuda", "cpu", "mps", "auto"] = Field(
        default="auto",  # 改为auto自动选择，避免cuda不可用时报错
        description="推理设备（auto自动选择）",
    )
    classes: list[int] = Field(
        default=[0],
        description="检测类别 ID 列表（person=0）",
    )
    imgsz: int = Field(
        default=640,
        ge=128,
        le=1280,
        description="推理图像尺寸",
    )

    @field_validator('device', mode='before')
    @classmethod
    def resolve_auto_device(cls, v: str) -> str:
        """如果 device 为 auto，自动选择可用设备"""
        if v == 'auto':
            try:
                import torch
                if torch.cuda.is_available():
                    return 'cuda'
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return 'mps'
                else:
                    return 'cpu'
            except ImportError:
                return 'cpu'
        return v


class TrackerConfig(BaseModel):
    """跟踪器配置

    配置 ByteTrack 跟踪参数。

    Attributes:
        tracker_type: 跟踪器类型
        track_buffer: 轨迹缓冲帧数
        match_thresh: 跟踪匹配阈值
        track_thresh: 跟踪置信度阈值
        new_track_thresh: 新建轨迹阈值
    """

    tracker_type: Literal["bytetrack", "botsort"] = Field(
        default="bytetrack",
        description="跟踪器类型",
    )
    track_buffer: int = Field(
        default=30,
        ge=1,
        description="轨迹缓冲帧数",
    )
    match_thresh: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="跟踪匹配阈值",
    )
    track_thresh: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="跟踪置信度阈值",
    )
    new_track_thresh: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="新建轨迹阈值",
    )
    tracker_config_path: Optional[str] = Field(
        default=None,
        description="跟踪器配置文件路径（推荐填写项目内 config/bytetrack.yaml）",
    )


class VisualizerConfig(BaseModel):
    """可视化配置

    配置检测结果可视化参数。

    Attributes:
        box_color: 边界框颜色 (BGR)
        text_color: 文本颜色 (BGR)
        trajectory_color: 轨迹颜色 (BGR)
        line_thickness: 线条宽度
        trajectory_length: 显示的轨迹点数量
        show_center_point: 是否显示中心点
        show_confidence: 是否显示置信度
        font_scale: 字体缩放比例
        show_bbox: 是否显示边界框（GUI开关支持）
        show_trajectory: 是否显示轨迹（GUI开关支持）
        show_id: 是否显示ID标签（GUI开关支持）
    """

    box_color: tuple[int, int, int] = Field(
        default=(0, 255, 0),
        description="边界框颜色 (BGR)",
    )
    text_color: tuple[int, int, int] = Field(
        default=(255, 255, 255),
        description="文本颜色 (BGR)",
    )
    trajectory_color: tuple[int, int, int] = Field(
        default=(255, 0, 0),
        description="轨迹颜色 (BGR)",
    )
    line_thickness: int = Field(
        default=2,
        ge=1,
        le=10,
        description="线条宽度",
    )
    trajectory_length: int = Field(
        default=50,
        ge=0,
        description="显示的轨迹点数量",
    )
    show_center_point: bool = Field(
        default=True,
        description="是否显示中心点",
    )
    show_confidence: bool = Field(
        default=True,
        description="是否显示置信度",
    )
    font_scale: float = Field(
        default=0.6,
        ge=0.1,
        le=2.0,
        description="字体缩放比例",
    )
    # GUI显示开关配置（解决伪开关问题）
    show_bbox: bool = Field(
        default=True,
        description="是否显示边界框",
    )
    show_trajectory: bool = Field(
        default=True,
        description="是否显示轨迹",
    )
    show_id: bool = Field(
        default=True,
        description="是否显示ID标签",
    )


class PipelineConfig(BaseModel):
    """处理管道配置

    配置处理流程参数。

    Attributes:
        show_progress: 是否显示进度条
        save_output: 是否保存输出视频
        output_fps: 输出视频帧率（None 使用原视频帧率）
        skip_frames: 跳帧处理（0 表示不跳帧）
        warmup: 是否进行模型预热
    """

    show_progress: bool = Field(
        default=True,
        description="是否显示进度条",
    )
    save_output: bool = Field(
        default=True,
        description="是否保存输出视频",
    )
    output_fps: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=120.0,
        description="输出视频帧率",
    )
    skip_frames: int = Field(
        default=0,
        ge=0,
        description="跳帧处理数量",
    )
    warmup: bool = Field(
        default=True,
        description="是否进行模型预热",
    )


class LoggingConfig(BaseModel):
    """日志配置

    配置日志系统参数。

    Attributes:
        level: 日志级别
        format: 日志格式
        file: 日志文件路径
        rotation: 日志轮转大小
        retention: 日志保留时间
    """

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别",
    )
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日志格式",
    )
    file: str = Field(
        default="logs/tracking.log",
        description="日志文件路径",
    )
    rotation: str = Field(
        default="10 MB",
        description="日志轮转大小",
    )
    retention: str = Field(
        default="7 days",
        description="日志保留时间",
    )


class Config(BaseModel):
    """系统配置

    顶层配置类，包含所有子系统配置。

    Attributes:
        detector: 检测器配置
        tracker: 跟踪器配置
        visualizer: 可视化配置
        pipeline: 处理管道配置
        logging: 日志配置
    """

    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    visualizer: VisualizerConfig = Field(default_factory=VisualizerConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# ============================================================================
# 配置加载函数
# ============================================================================


def load_config(config_path: Optional[str | Path] = None) -> Config:
    """加载配置文件

    从 YAML 文件加载配置，并进行验证。

    Args:
        config_path: 配置文件路径；为 None 时自动尝试加载项目内 config/default.yaml

    Returns:
        验证后的 Config 实例

    Raises:
        ConfigurationError: 配置文件格式错误或验证失败

    Example:
        >>> config = load_config("config/default.yaml")
        >>> print(config.detector.model_path)
        'yolo11n.pt'
    """
    from .exceptions import ConfigurationError

    # 如果未指定配置文件，优先使用项目默认配置文件
    if config_path is None:
        if DEFAULT_CONFIG_PATH.exists():
            config_path = DEFAULT_CONFIG_PATH
        else:
            return Config()

    config_path = Path(config_path)

    # 相对路径按项目根目录解析
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    # 检查文件是否存在
    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            config_key=str(config_path),
        )

    # 读取 YAML 文件
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Failed to parse YAML configuration: {e}",
            config_key=str(config_path),
            details=e,
        )

    # 验证并创建配置实例
    try:
        return Config(**config_dict)
    except Exception as e:
        raise ConfigurationError(
            f"Configuration validation failed: {e}",
            details=e,
        )


def save_config(config: Config, output_path: str | Path) -> None:
    """保存配置到文件

    将配置保存为 YAML 文件。

    Args:
        config: 配置实例
        output_path: 输出文件路径

    Example:
        >>> config = Config()
        >>> save_config(config, "config/custom.yaml")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 转换为字典
    config_dict = config.model_dump()

    # 转换 tuple 为 list（YAML 不支持 tuple）
    def convert_tuples(obj):
        if isinstance(obj, dict):
            return {k: convert_tuples(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_tuples(item) for item in obj]
        elif isinstance(obj, tuple):
            return list(obj)
        return obj

    config_dict = convert_tuples(config_dict)

    # 使用自定义 Dumper 来处理 tuple
    class TupleDumper(yaml.SafeDumper):
        pass

    def tuple_representer(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', list(data))

    TupleDumper.add_representer(tuple, tuple_representer)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, Dumper=TupleDumper, default_flow_style=False, allow_unicode=True)


def resolve_tracker_config_path(tracker_config: TrackerConfig) -> str:
    """解析跟踪器配置路径。

    解析优先级：
    1. tracker_config_path（显式配置）
    2. 项目内 config/bytetrack.yaml（当 tracker_type=bytetrack）
    3. Ultralytics 外部默认字符串（如 bytetrack.yaml）
    """
    configured_path = tracker_config.tracker_config_path
    if configured_path:
        candidate = Path(configured_path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if candidate.exists():
            return str(candidate)
        # 显式配置但文件不存在时保留原值，交由调用方报错
        return str(configured_path)

    if tracker_config.tracker_type == "bytetrack" and DEFAULT_BYTETRACK_CONFIG_PATH.exists():
        return str(DEFAULT_BYTETRACK_CONFIG_PATH)

    return f"{tracker_config.tracker_type}.yaml"


# ============================================================================
# 默认配置实例
# ============================================================================

DEFAULT_CONFIG = Config()
