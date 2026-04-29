"""处理管道模块

协调检测、跟踪、可视化和导出的完整处理流程。

处理流程：
    1. 加载视频/摄像头
    2. 逐帧处理：
       - 检测人物
       - 跟踪关联
       - 更新轨迹
       - 渲染可视化
       - 导出日志
    3. 释放资源
"""

from pathlib import Path
from typing import Optional, Union, Callable
import time
import numpy as np
from numpy.typing import NDArray

from ultralytics import YOLO

from ..infra.config import Config, resolve_tracker_config_path
from ..infra.exceptions import VideoLoadError, InferenceError
from ..infra.logger import get_logger, setup_logger
from ..data.loader import VideoLoader, VideoWriter
from ..data.types import Frame, TrackedObject, PerformanceMetrics
from ..data.trajectory import TrajectoryManager
from ..viz.visualizer import Visualizer
from ..export.csv_exporter import CSVExporter

logger = get_logger("pipeline")


class FrameStateCache:
    """帧状态缓存 - 保持跳帧期间视觉连续性

    当跳帧时，使用上一帧的渲染结果或预测位置保持视觉连续性，
    避免输出视频中跳过的帧显示为无标注的原始帧。
    """

    def __init__(self, max_cache_size: int = 5):
        """初始化缓存

        Args:
            max_cache_size: 最大缓存帧数（用于平滑）
        """
        self._max_cache_size = max_cache_size
        self._last_tracked_objects: list = []
        self._last_trajectories: dict = {}
        self._last_annotated_frame: Optional[np.ndarray] = None
        self._last_frame_id: int = 0
        self._last_timestamp: float = 0.0
        self._frame_history: list = []  # 用于平滑

    def update(
        self,
        frame_id: int,
        timestamp: float,
        tracked_objects: list,
        trajectories: dict,
        annotated_frame: np.ndarray
    ) -> None:
        """更新缓存

        Args:
            frame_id: 当前帧ID
            timestamp: 当前时间戳
            tracked_objects: 当前跟踪对象列表
            trajectories: 当前轨迹字典
            annotated_frame: 已渲染的帧
        """
        self._last_tracked_objects = tracked_objects.copy() if tracked_objects else []
        self._last_trajectories = trajectories.copy() if trajectories else {}
        self._last_annotated_frame = annotated_frame.copy() if annotated_frame is not None else None
        self._last_frame_id = frame_id
        self._last_timestamp = timestamp

        # 维护历史记录（用于平滑）
        self._frame_history.append({
            'frame_id': frame_id,
            'timestamp': timestamp,
            'tracked_objects': self._last_tracked_objects,
            'trajectories': self._last_trajectories,
        })
        if len(self._frame_history) > self._max_cache_size:
            self._frame_history.pop(0)

    def get_last_annotated_frame(self) -> Optional[np.ndarray]:
        """获取上一帧已渲染的帧（用于跳帧时显示）

        Returns:
            上一帧的已渲染帧图像，如果没有则返回 None
        """
        return self._last_annotated_frame

    def get_interpolated_frame(
        self,
        current_frame: np.ndarray,
        visualizer,
        frame_id: int
    ) -> np.ndarray:
        """获取插值帧（跳帧时使用）

        策略：基于上一帧的跟踪对象进行位置预测，并重新渲染

        Args:
            current_frame: 当前原始帧
            visualizer: 可视化器
            frame_id: 当前帧ID

        Returns:
            插值后的渲染帧
        """
        # 如果有上一帧的渲染结果，直接复用（最简单且视觉效果一致）
        if self._last_annotated_frame is not None:
            # 注意：这里直接使用上一帧的渲染结果
            # 这可能导致目标位置稍微滞后，但保证了视觉连续性
            # 如果需要精确预测，可以实现卡尔曼滤波预测
            return self._last_annotated_frame.copy()

        # 如果没有缓存，返回原始帧（首次跳帧时的降级处理）
        return current_frame.copy()

    def get_last_tracked_objects(self) -> list:
        """获取上一帧的跟踪对象"""
        return self._last_tracked_objects.copy()

    def get_last_trajectories(self) -> dict:
        """获取上一帧的轨迹"""
        return self._last_trajectories.copy()

    def clear(self) -> None:
        """清空缓存"""
        self._last_tracked_objects = []
        self._last_trajectories = {}
        self._last_annotated_frame = None
        self._last_frame_id = 0
        self._last_timestamp = 0.0
        self._frame_history = []


class TrackingPipeline:
    """检测跟踪处理管道

    协调 YOLOv11 检测和 ByteTrack 跟踪的完整处理流程。

    Attributes:
        config: 系统配置
        model: YOLO 模型
        visualizer: 可视化渲染器
        trajectory_manager: 轨迹管理器

    Example:
        >>> config = load_config("config/default.yaml")
        >>> pipeline = TrackingPipeline(config)
        >>> pipeline.run("input.mp4", "output/tracked.mp4")
    """

    def __init__(self, config: Config) -> None:
        """初始化处理管道

        Args:
            config: 系统配置

        Raises:
            ModelLoadError: 模型加载失败
        """
        self.config = config

        # 初始化组件
        self._setup_components()

        # 性能指标（使用统一的MetricsCollector）
        from ..infra.metrics import MetricsCollector
        self._metrics_collector = MetricsCollector()
        self._metrics = PerformanceMetrics()

        # 帧状态缓存（用于跳帧时保持视觉连续性）
        self._frame_cache = FrameStateCache()

        logger.info(
            f"TrackingPipeline initialized: model={config.detector.model_path}"
        )

    def _setup_components(self) -> None:
        """初始化各组件"""
        # 初始化日志
        setup_logger(
            level=self.config.logging.level,
            log_file=self.config.logging.file,
            rotation=self.config.logging.rotation,
        )

        # 加载 YOLO 模型
        logger.info(f"Loading model: {self.config.detector.model_path}")
        self.model = YOLO(self.config.detector.model_path)

        # 设置设备（处理 auto 情况）
        device = self.config.detector.device
        if device == "auto":
            import torch
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        logger.info(f"Using device: {device}")
        self.model.to(device)

        tracker_cfg_path = resolve_tracker_config_path(self.config.tracker)
        logger.info(f"Using tracker config: {tracker_cfg_path}")

        # 初始化可视化器
        self.visualizer = Visualizer(self.config.visualizer)

        # 初始化轨迹管理器
        self.trajectory_manager = TrajectoryManager(
            max_trajectory_length=self.config.visualizer.trajectory_length,
            inactive_threshold=self.config.tracker.track_buffer,
        )

    def warmup(self) -> None:
        """模型预热

        运行一次虚拟推理，避免首帧延迟。
        """
        if not self.config.pipeline.warmup:
            return

        logger.debug("Warming up model...")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        tracker_cfg_path = resolve_tracker_config_path(self.config.tracker)
        _ = self.model.track(
            dummy_frame,
            conf=self.config.detector.confidence_threshold,
            classes=self.config.detector.classes,
            max_det=self.config.detector.max_det,
            tracker=tracker_cfg_path,
            persist=True,
            verbose=False,
        )
        logger.debug("Model warmup completed")

    def process_frame(
        self,
        frame: Frame,
        enable_tracking: bool = True,
        render: bool = True,
    ) -> tuple[Frame, list[TrackedObject]]:
        """处理单帧

        执行检测、跟踪、轨迹更新，可选渲染可视化。

        Args:
            frame: 输入帧
            enable_tracking: 是否启用跟踪
            render: 是否渲染可视化结果到帧上（默认True）

        Returns:
            元组 (处理后的帧, 跟踪对象列表)
            如果render=True，返回的帧包含渲染的检测结果

        Example:
            >>> processed_frame, tracked_objs = pipeline.process_frame(frame)
            >>> # processed_frame.image 包含渲染后的图像
        """
        start_time = time.time()

        # 使用 YOLO 的 track 方法同时进行检测和跟踪
        if enable_tracking:
            tracker_cfg_path = resolve_tracker_config_path(self.config.tracker)
            results = self.model.track(
                frame.image,
                conf=self.config.detector.confidence_threshold,
                iou=self.config.detector.iou_threshold,
                classes=self.config.detector.classes,
                imgsz=self.config.detector.imgsz,
                max_det=self.config.detector.max_det,
                tracker=tracker_cfg_path,
                persist=True,
                verbose=False,
            )
        else:
            # 仅检测
            results = self.model(
                frame.image,
                conf=self.config.detector.confidence_threshold,
                iou=self.config.detector.iou_threshold,
                classes=self.config.detector.classes,
                imgsz=self.config.detector.imgsz,
                max_det=self.config.detector.max_det,
                verbose=False,
            )

        # 转换为 TrackedObject
        tracked_objects = self._convert_results(results, frame.frame_id, frame.timestamp)

        # 更新轨迹
        for obj in tracked_objects:
            self.trajectory_manager.update(obj)

        # 清理失效轨迹
        self.trajectory_manager.cleanup_inactive(frame.frame_id)

        # 更新帧数据
        frame.tracked_objects = tracked_objects

        # 计算推理时间
        elapsed = time.time() - start_time
        inference_time_ms = elapsed * 1000

        # 使用统一的MetricsCollector（解决FPS多源计算问题）
        self._metrics_collector.report_frame(
            frame_id=frame.frame_id,
            inference_time_ms=inference_time_ms,
            detection_count=len(tracked_objects)
        )

        # 获取统一计算的性能指标
        metrics = self._metrics_collector.get_snapshot()

        # 渲染可视化结果（避免GUI层重复渲染）
        if render:
            annotated = self.visualizer.render(
                frame.image,
                tracked_objects,
                self.trajectory_manager.get_all_trajectories(),
            )
            annotated = self.visualizer.draw_info(
                annotated,
                frame.frame_id,
                metrics.fps,  # 使用统一计算的FPS
                len(tracked_objects),
            )
            frame.image = annotated

        return frame, tracked_objects

    def _convert_results(
        self,
        results,
        frame_id: int,
        timestamp: float,
    ) -> list[TrackedObject]:
        """转换 YOLO 跟踪结果

        Args:
            results: YOLO 跟踪结果
            frame_id: 帧编号
            timestamp: 时间戳

        Returns:
            TrackedObject 列表
        """
        from ..data.types import BoundingBox, Detection

        tracked_objects = []

        if not results or len(results) == 0:
            return tracked_objects

        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return tracked_objects

        boxes = result.boxes

        # 检查是否有 track_id（跟踪模式）
        has_tracking = boxes.id is not None

        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)

        if has_tracking:
            track_ids = boxes.id.cpu().numpy().astype(int)
        else:
            # 仅检测模式，使用临时 ID
            track_ids = list(range(len(xyxy)))

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            confidence = float(confidences[i])
            class_id = int(class_ids[i])
            track_id = int(track_ids[i])

            bbox = BoundingBox.from_xyxy(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                confidence=confidence,
            )

            detection = Detection(
                bbox=bbox,
                class_id=class_id,
                class_name="person",
                track_id=track_id,
            )

            tracked_obj = TrackedObject(
                track_id=track_id,
                detection=detection,
                frame_id=frame_id,
                timestamp=timestamp,
            )

            tracked_objects.append(tracked_obj)

        return tracked_objects

    def run(
        self,
        source: Union[str, int, Path],
        output_path: Optional[str | Path] = None,
        csv_path: Optional[str | Path] = None,
        show: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        """运行完整处理流程

        Args:
            source: 视频源（文件路径或摄像头索引）
            output_path: 输出视频路径（可选）
            csv_path: CSV 日志路径（可选）
            show: 是否实时显示结果
            progress_callback: 进度回调函数 callback(current_frame, total_frames)

        Returns:
            处理结果统计

        Example:
            >>> stats = pipeline.run("input.mp4", "output/tracked.mp4")
            >>> print(f"Processed {stats['total_frames']} frames")
        """
        # 初始化
        self.warmup()

        # 打开视频
        loader = VideoLoader(source)
        total_frames = loader.frame_count

        # 创建输出写入器
        writer = None
        if output_path and self.config.pipeline.save_output:
            fps = loader.fps if self.config.pipeline.output_fps is None else self.config.pipeline.output_fps
            writer = VideoWriter(
                output_path,
                fps=fps,
                size=(loader.width, loader.height),
            )

        # 创建 CSV 导出器
        csv_exporter = None
        if csv_path:
            csv_exporter = CSVExporter(csv_path)

        # 重置轨迹
        self.trajectory_manager.clear()
        self.visualizer.clear_color_cache()
        self._frame_cache.clear()

        logger.info(
            f"Starting processing: source={source}, "
            f"total_frames={total_frames}, "
            f"output={output_path}, csv={csv_path}"
        )

        start_time = time.time()

        # 跳帧计数器
        frame_counter = 0
        skip_frames = self.config.pipeline.skip_frames

        # 上一帧渲染结果（用于跳帧时保持连续性）
        last_annotated_frame: Optional[np.ndarray] = None

        try:
            # 处理每一帧
            for frame in loader:
                frame_counter += 1

                # 跳帧逻辑：每 (skip_frames + 1) 帧处理一次
                should_process = (
                    skip_frames == 0 or
                    frame_counter % (skip_frames + 1) == 1 or
                    frame_counter == 1  # 第一帧总是处理
                )

                if should_process:
                    # 正常处理帧
                    processed_frame, tracked_objects = self.process_frame(
                        frame, enable_tracking=True, render=False
                    )

                    # 渲染可视化
                    annotated = self.visualizer.render(
                        processed_frame.image,
                        tracked_objects,
                        self.trajectory_manager.get_all_trajectories(),
                    )

                    # 获取统一计算的性能指标
                    metrics = self._metrics_collector.get_snapshot()

                    # 绘制帧信息
                    annotated = self.visualizer.draw_info(
                        annotated,
                        frame.frame_id,
                        metrics.fps,
                        len(tracked_objects),
                    )

                    # 更新缓存
                    self._frame_cache.update(
                        frame.frame_id,
                        frame.timestamp,
                        tracked_objects,
                        self.trajectory_manager.get_all_trajectories(),
                        annotated
                    )

                    # 保存当前渲染结果
                    last_annotated_frame = annotated.copy()

                else:
                    # 跳过的帧：使用缓存的上一帧渲染结果（关键修复）
                    cached_frame = self._frame_cache.get_last_annotated_frame()
                    if cached_frame is not None:
                        # 使用上一帧的渲染结果（保持视觉连续性）
                        annotated = cached_frame.copy()
                    elif last_annotated_frame is not None:
                        # 备用方案
                        annotated = last_annotated_frame.copy()
                    else:
                        # 首次跳帧，没有上一帧，显示原始帧（降级处理）
                        annotated = frame.image.copy()

                # 写入输出视频（关键修复：所有帧都有标注）
                if writer:
                    writer.write(annotated)

                # CSV 导出（只导出实际处理的帧）
                if csv_exporter and should_process:
                    # 获取当前跟踪对象并导出
                    current_tracked = self._frame_cache.get_last_tracked_objects()
                    if current_tracked:
                        csv_exporter.write_batch(current_tracked)

                # 实时显示
                if show:
                    import cv2
                    cv2.imshow("Person Tracking", annotated)
                    if cv2.waitKey(1) == ord('q'):
                        break

            # 进度回调
            if progress_callback and total_frames > 0:
                progress_callback(frame.frame_id + 1, total_frames)

        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise

        finally:
            # 清理资源
            loader.release()
            if writer:
                writer.release()
            if csv_exporter:
                csv_exporter.close()
            if show:
                import cv2
                cv2.destroyAllWindows()

        # 统计信息（使用MetricsCollector）
        elapsed = time.time() - start_time
        final_metrics = self._metrics_collector.get_snapshot()
        stats = {
            "total_frames": final_metrics.frame_count,
            "elapsed_time": elapsed,
            "avg_fps": final_metrics.frame_count / elapsed if elapsed > 0 else 0,
            "trajectories_created": len(self.trajectory_manager),
        }

        logger.info(
            f"Processing completed: {stats['total_frames']} frames, "
            f"{stats['elapsed_time']:.2f}s, {stats['avg_fps']:.1f} FPS"
        )

        return stats

    def get_metrics(self) -> PerformanceMetrics:
        """获取性能指标

        Returns:
            性能指标对象
        """
        return self._metrics
