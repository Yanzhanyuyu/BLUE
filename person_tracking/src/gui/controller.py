"""GUI 控制器层

职责：
- 协调 Pipeline、Workers、Config 之间的交互
- 处理业务逻辑（开始/停止/暂停/导出）
- 状态管理（运行状态、视频信息）
- 不直接操作UI，通过信号与UI通信

设计原则：
- 主线程安全：所有UI更新通过信号发出
- 配置同步：自动将UI配置变更同步到Pipeline
- 状态机：明确的状态转换（就绪->运行->暂停->停止）

作者：AI Assistant
日期：2026-04-15
"""

from typing import Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal, Slot

from ..infra.config import Config, load_config
from ..core.pipeline import TrackingPipeline


class AppState(Enum):
    """应用状态"""
    IDLE = auto()  # 就绪
    RUNNING = auto()  # 运行中
    PAUSED = auto()  # 已暂停
    ERROR = auto()  # 错误状态


@dataclass
class VideoInfo:
    """视频信息"""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    total_frames: int = 0
    current_frame: int = 0
    is_local_video: bool = False


class TrackingController(QObject):
    """跟踪控制器

    信号：
        state_changed: 状态变化 (AppState)
        frame_ready: 帧就绪 (numpy.ndarray)
        metrics_updated: 性能指标更新 (dict)
        error_occurred: 错误发生 (str)
        progress_updated: 进度更新 (int, int) # current, total
    """

    # 信号定义
    state_changed = Signal(object)  # AppState
    frame_ready = Signal(object)  # NDArray[np.uint8]
    metrics_updated = Signal(dict)
    error_occurred = Signal(str)
    progress_updated = Signal(int, int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化控制器

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._state = AppState.IDLE
        self._config: Optional[Config] = None
        self._pipeline: Optional[TrackingPipeline] = None
        self._video_info = VideoInfo()

        # Workers（在start时初始化）
        self._capture_worker = None
        self._inference_worker = None

        # 当前源
        self._current_source: Optional[str] = None

    @property
    def state(self) -> AppState:
        """获取当前状态"""
        return self._state

    @property
    def pipeline(self) -> Optional[TrackingPipeline]:
        """获取Pipeline实例"""
        return self._pipeline

    def set_source(self, source: str) -> bool:
        """设置视频源

        Args:
            source: 视频源路径或摄像头索引

        Returns:
            是否设置成功
        """
        self._current_source = source
        return True

    def initialize(self, config: Optional[Config] = None) -> bool:
        """初始化控制器

        Args:
            config: 配置对象，None则使用默认配置

        Returns:
            是否初始化成功
        """
        try:
            self._config = config or load_config()
            self._set_state(AppState.IDLE)
            return True
        except Exception as e:
            self.error_occurred.emit(f"初始化失败: {str(e)}")
            return False

    def start(self) -> bool:
        """开始处理

        Returns:
            是否成功启动
        """
        if self._state == AppState.RUNNING:
            return True

        if not self._current_source:
            self.error_occurred.emit("未选择视频源")
            return False

        try:
            self._set_state(AppState.RUNNING)
            return True
        except Exception as e:
            self.error_occurred.emit(f"启动失败: {str(e)}")
            self._set_state(AppState.ERROR)
            return False

    def pause(self) -> None:
        """暂停处理"""
        if self._state == AppState.RUNNING:
            self._set_state(AppState.PAUSED)

    def stop(self) -> None:
        """停止处理"""
        self._set_state(AppState.IDLE)
        self._cleanup()

    def update_config(self, key: str, value: Any) -> None:
        """更新配置项（热更新）

        Args:
            key: 配置项名称
            value: 新值
        """
        if self._config is None:
            return

        # 映射UI配置到Pipeline配置
        config_map = {
            'confidence_threshold': ('detector', 'confidence_threshold'),
            'iou_threshold': ('detector', 'iou_threshold'),
            'device': ('detector', 'device'),
            'show_bbox': ('visualizer', 'show_bbox'),
            'show_trajectory': ('visualizer', 'show_trajectory'),
            'show_id': ('visualizer', 'show_id'),
            'show_center_point': ('visualizer', 'show_center_point'),
            'show_confidence': ('visualizer', 'show_confidence'),
        }

        if key in config_map:
            section, attr = config_map[key]
            setattr(getattr(self._config, section), attr, value)

            # 如果Pipeline已初始化，同步更新
            if self._pipeline and hasattr(self._pipeline, 'visualizer'):
                viz_config = self._pipeline.visualizer.config
                if hasattr(viz_config, attr):
                    setattr(viz_config, attr, value)

    def get_current_source(self) -> Optional[str]:
        """获取当前视频源"""
        return self._current_source

    def get_config(self) -> Optional[Config]:
        """获取当前配置"""
        return self._config

    def _set_state(self, new_state: AppState) -> None:
        """设置新状态

        Args:
            new_state: 新状态
        """
        old_state = self._state
        self._state = new_state
        if old_state != new_state:
            self.state_changed.emit(new_state)

    def _cleanup(self) -> None:
        """清理资源"""
        self._capture_worker = None
        self._inference_worker = None
