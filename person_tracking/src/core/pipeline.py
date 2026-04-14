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

from ..infra.config import Config
from ..infra.exceptions import VideoLoadError, InferenceError
from ..infra.logger import get_logger, setup_logger
from ..data.loader import VideoLoader, VideoWriter
from ..data.types import Frame, TrackedObject, PerformanceMetrics
from ..data.trajectory import TrajectoryManager
from ..viz.visualizer import Visualizer
from ..export.csv_exporter import CSVExporter

logger = get_logger("pipeline")


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

        # 性能指标
        self._metrics = PerformanceMetrics()

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

        # 设置设备
        self.model.to(self.config.detector.device)

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
        _ = self.model.track(
            dummy_frame,
            conf=self.config.detector.confidence_threshold,
            classes=self.config.detector.classes,
            tracker=f"{self.config.tracker.tracker_type}.yaml",
            persist=True,
            verbose=False,
        )
        logger.debug("Model warmup completed")

    def process_frame(
        self,
        frame: Frame,
        enable_tracking: bool = True,
    ) -> tuple[Frame, list[TrackedObject]]:
        """处理单帧

        执行检测、跟踪、轨迹更新。

        Args:
            frame: 输入帧
            enable_tracking: 是否启用跟踪

        Returns:
            元组 (处理后的帧, 跟踪对象列表)

        Example:
            >>> processed_frame, tracked_objs = pipeline.process_frame(frame)
        """
        start_time = time.time()

        # 使用 YOLO 的 track 方法同时进行检测和跟踪
        if enable_tracking:
            results = self.model.track(
                frame.image,
                conf=self.config.detector.confidence_threshold,
                iou=self.config.detector.iou_threshold,
                classes=self.config.detector.classes,
                imgsz=self.config.detector.imgsz,
                tracker=f"{self.config.tracker.tracker_type}.yaml",
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

        # 更新性能指标
        elapsed = time.time() - start_time
        if self._metrics.fps == 0:
            self._metrics.fps = 1.0 / elapsed if elapsed > 0 else 0
        else:
            self._metrics.fps = 0.9 * self._metrics.fps + 0.1 * (1.0 / elapsed if elapsed > 0 else 0)
        self._metrics.total_frames += 1

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

        logger.info(
            f"Starting processing: source={source}, "
            f"total_frames={total_frames}, "
            f"output={output_path}, csv={csv_path}"
        )

        start_time = time.time()

        # 跳帧计数器
        frame_counter = 0
        skip_frames = self.config.pipeline.skip_frames

        try:
            # 处理每一帧
            for frame in loader:
                frame_counter += 1

                # 跳帧逻辑：每 (skip_frames + 1) 帧处理一次
                if skip_frames > 0 and frame_counter % (skip_frames + 1) != 0:
                    # 跳过的帧仍然写入输出视频（如果需要），但不进行检测
                    if writer:
                        writer.write(frame.image)
                    if progress_callback and total_frames > 0:
                        progress_callback(frame.frame_id + 1, total_frames)
                    continue

                # 处理帧
                processed_frame, tracked_objects = self.process_frame(frame)

                # 渲染可视化
                annotated = self.visualizer.render(
                    processed_frame.image,
                    tracked_objects,
                    self.trajectory_manager.get_all_trajectories(),
                )

                # 绘制帧信息
                annotated = self.visualizer.draw_info(
                    annotated,
                    frame.frame_id,
                    self._metrics.fps,
                    len(tracked_objects),
                )

                # 写入输出视频
                if writer:
                    writer.write(annotated)

                # 写入 CSV
                if csv_exporter:
                    csv_exporter.write_batch(tracked_objects)

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

        # 统计信息
        elapsed = time.time() - start_time
        stats = {
            "total_frames": self._metrics.total_frames,
            "elapsed_time": elapsed,
            "avg_fps": self._metrics.total_frames / elapsed if elapsed > 0 else 0,
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
