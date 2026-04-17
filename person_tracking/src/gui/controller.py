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

import time
from typing import Optional, Any, TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal, Slot

from ..infra.config import Config, load_config

if TYPE_CHECKING:
    from ..core.pipeline import TrackingPipeline
    from .workers import VideoCaptureWorker, InferenceWorker


class AppState(Enum):
    """应用状态"""
    IDLE = auto()      # 就绪
    RUNNING = auto()   # 运行中
    PAUSED = auto()    # 已暂停
    ERROR = auto()     # 错误状态


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
    detections_updated: 检测结果更新 (list)
    trajectories_updated: 轨迹更新 (dict)
    """

    # 信号定义
    state_changed = Signal(object)      # AppState
    frame_ready = Signal(object)        # ProcessedData
    metrics_updated = Signal(dict)      # 性能指标
    error_occurred = Signal(str)        # 错误消息
    progress_updated = Signal(int, int) # (current, total)
    detections_updated = Signal(list)   # 检测结果
    trajectories_updated = Signal(dict) # 轨迹数据

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化控制器"""
        super().__init__(parent)
        self._state = AppState.IDLE
        self._config: Optional[Config] = None
        self._pipeline: Optional["TrackingPipeline"] = None
        self._video_info = VideoInfo()

        # Workers
        self._capture_worker: Optional["VideoCaptureWorker"] = None
        self._inference_worker: Optional["InferenceWorker"] = None

        # 当前源
        self._current_source: Optional[str] = None

        # 初始化配置
        self._config = load_config()

    @property
    def state(self) -> AppState:
        """获取当前状态"""
        return self._state

    @property
    def pipeline(self) -> Optional["TrackingPipeline"]:
        """获取Pipeline实例"""
        return self._pipeline

    @property
    def video_info(self) -> VideoInfo:
        """获取视频信息"""
        return self._video_info

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
            # 初始化 Pipeline 和 Workers
            self._initialize_pipeline()
            self._initialize_workers()

            # 启动 Workers
            self._inference_worker.start()
            self._capture_worker.start()

            self._set_state(AppState.RUNNING)
            return True
        except Exception as e:
            self.error_occurred.emit(f"启动失败: {str(e)}")
            self._set_state(AppState.ERROR)
            return False

    def pause(self) -> None:
        """暂停处理"""
        if self._state == AppState.RUNNING:
            if self._capture_worker:
                self._capture_worker.pause()
            if self._inference_worker:
                self._inference_worker.pause()
            self._set_state(AppState.PAUSED)

    def resume(self) -> None:
        """恢复处理"""
        if self._state == AppState.PAUSED:
            if self._capture_worker:
                self._capture_worker.resume()
            if self._inference_worker:
                self._inference_worker.resume()
            self._set_state(AppState.RUNNING)

    def stop(self) -> None:
        """停止处理"""
        self._stop_workers()
        self._cleanup()
        self._set_state(AppState.IDLE)

    def _initialize_pipeline(self) -> None:
        """初始化 Pipeline"""
        if self._pipeline is None:
            from ..core.pipeline import TrackingPipeline
            self._pipeline = TrackingPipeline(self._config)
            self._pipeline.warmup()

    def _initialize_workers(self) -> None:
        """初始化 Workers"""
        from .workers import VideoCaptureWorker, InferenceWorker

        # 创建 Capture Worker
        self._capture_worker = VideoCaptureWorker(
            source=self._current_source,
            target_fps=30.0,
            parent=self
        )

        # 创建 Inference Worker
        self._inference_worker = InferenceWorker(
            config=self._config,
            parent=self
        )
        self._inference_worker.set_pipeline(self._pipeline)

        # 连接 Worker 信号到 Controller 信号
        self._capture_worker.frame_ready.connect(self._on_capture_frame_ready)
        self._capture_worker.error.connect(self._on_worker_error)
        self._capture_worker.finished.connect(self._on_capture_finished)

        self._inference_worker.result_ready.connect(self._on_inference_result_ready)
        self._inference_worker.error.connect(self._on_worker_error)
        self._inference_worker.finished.connect(self._on_inference_finished)
        self._inference_worker.metrics_updated.connect(self._on_metrics_updated)

        # 连接 Capture -> Inference 的帧传递
        self._capture_worker.frame_ready.connect(self._inference_worker.submit_frame)

    def _on_capture_frame_ready(self, frame_data) -> None:
        """处理捕获的帧"""
        # 可以在这里添加预处理逻辑
        pass

    def _on_inference_result_ready(self, result) -> None:
        """处理推理结果 - 转发到 UI"""
        self.frame_ready.emit(result)
        self.detections_updated.emit(result.detections)
        self.trajectories_updated.emit(result.trajectories)

    def _on_metrics_updated(self, metrics: dict) -> None:
        """处理性能指标更新"""
        self.metrics_updated.emit(metrics)

    def _on_worker_error(self, error_msg: str) -> None:
        """处理 Worker 错误"""
        self.error_occurred.emit(error_msg)
        self._set_state(AppState.ERROR)

    def _on_capture_finished(self) -> None:
        """Capture Worker 结束"""
        if self._inference_worker:
            self._inference_worker.stop()
        self._set_state(AppState.IDLE)

    def _on_inference_finished(self) -> None:
        """Inference Worker 结束"""
        pass

    def _stop_workers(self) -> None:
        """停止 Workers"""
        if self._capture_worker:
            try:
                self._capture_worker.stop()
                self._capture_worker.wait(1000)
            except Exception:
                pass
            self._capture_worker = None

        if self._inference_worker:
            try:
                self._inference_worker.stop()
                self._inference_worker.wait(1000)
            except Exception:
                pass
            self._inference_worker = None

    def _cleanup(self) -> None:
        """清理资源"""
        self._pipeline = None
        self._capture_worker = None
        self._inference_worker = None

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

            # 如果InferenceWorker已创建，更新运行时参数
            if self._inference_worker and attr == 'confidence_threshold':
                self._inference_worker.set_confidence_threshold(value)

    def update_config_batch(self, config_dict: dict) -> None:
        """批量更新配置

        Args:
            config_dict: 配置字典 {'section': {'key': value}, ...}
        """
        for section, items in config_dict.items():
            for key, value in items.items():
                self.update_config(key, value)

    def export_csv(self, export_path: Path) -> Optional[Path]:
        """导出 CSV 日志

        Args:
            export_path: 导出目录路径

        Returns:
            导出的文件路径
        """
        if self._pipeline is None:
            return None

        source_name = Path(self._current_source).stem if self._current_source else "tracking"
        csv_file = export_path / f"{source_name}_tracking_log.csv"

        try:
            from ..export.csv_exporter import CSVExporter
            from ..data.types import TrackedObject, BoundingBox, Detection

            with CSVExporter(csv_file) as exporter:
                trajectories = self._pipeline.trajectory_manager.get_all_trajectories()
                frame_sequencer = 0

                for track_id, trajectory in trajectories.items():
                    for point in trajectory.points:
                        x, y, timestamp = point
                        frame_sequencer += 1

                        estimated_w, estimated_h = 50.0, 100.0
                        bbox = BoundingBox(
                            x=x - estimated_w / 2,
                            y=y - estimated_h / 2,
                            w=estimated_w,
                            h=estimated_h,
                            confidence=0.9
                        )

                        detection = Detection(
                            bbox=bbox,
                            class_id=0,
                            class_name="person",
                            track_id=track_id
                        )

                        tracked_obj = TrackedObject(
                            track_id=track_id,
                            detection=detection,
                            frame_id=frame_sequencer,
                            timestamp=timestamp
                        )

                        exporter.write_row(tracked_obj)

            return csv_file if exporter.row_count > 0 else None

        except Exception as e:
            self.error_occurred.emit(f"CSV导出失败: {str(e)}")
            return None

    def export_trajectory_stats(self, export_path: Path) -> Optional[Path]:
        """导出轨迹统计

        Args:
            export_path: 导出目录路径

        Returns:
            导出的文件路径
        """
        if self._pipeline is None:
            return None

        import json
        source_name = Path(self._current_source).stem if self._current_source else "tracking"
        stats_file = export_path / f"{source_name}_trajectory_stats.json"

        try:
            stats = self._pipeline.trajectory_manager.get_statistics()
            stats['export_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            stats['source'] = self._current_source

            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            return stats_file if stats.get('total_trajectories', 0) > 0 else None

        except Exception as e:
            self.error_occurred.emit(f"统计导出失败: {str(e)}")
            return None

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