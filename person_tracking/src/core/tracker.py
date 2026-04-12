"""人物跟踪器模块

封装 ByteTrack 跟踪算法，提供：
- 跨帧目标关联
- track_id 维护
- 结果转换为标准 TrackedObject 格式
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray
from pathlib import Path

from ..infra.config import TrackerConfig
from ..infra.exceptions import InferenceError
from ..infra.logger import get_logger
from ..data.types import Detection, TrackedObject

logger = get_logger("tracker")


class PersonTracker:
    """人物跟踪器

    封装 ByteTrack 跟踪算法，基于 Ultralytics 内置跟踪器实现。

    Attributes:
        config: 跟踪器配置
        tracker: 跟踪器实例

    Note:
        Ultralytics YOLOv11 内置了 ByteTrack 支持，可以直接使用
        model.track() 方法进行跟踪。

    Example:
        >>> config = TrackerConfig(tracker_type="bytetrack")
        >>> tracker = PersonTracker(config)
        >>> # 与检测器配合使用
        >>> tracked_objects = tracker.update(detections, frame, frame_id)
    """

    def __init__(self, config: TrackerConfig) -> None:
        """初始化人物跟踪器

        Args:
            config: 跟踪器配置
        """
        self.config = config
        self._tracker_config = None
        self._frame_count = 0

        # 创建跟踪器配置
        self._setup_tracker()

        logger.info(
            f"PersonTracker initialized: type={config.tracker_type}, "
            f"track_buffer={config.track_buffer}"
        )

    def _setup_tracker(self) -> None:
        """设置跟踪器配置"""
        # 创建 ByteTrack 配置字典
        # Ultralytics 内置的跟踪器使用 YAML 配置
        self._tracker_config = {
            "tracker_type": self.config.tracker_type,
            "track_buffer": self.config.track_buffer,
            "match_thresh": self.config.match_thresh,
            "track_thresh": self.config.track_thresh,
            "new_track_thresh": self.config.new_track_thresh,
        }

    def update(
        self,
        detections: list[Detection],
        frame: NDArray[np.uint8],
        frame_id: int = 0,
        timestamp: float = 0.0,
    ) -> list[TrackedObject]:
        """更新跟踪状态

        根据检测结果更新跟踪状态，返回关联了 track_id 的对象列表。

        Args:
            detections: 当前帧检测结果
            frame: 当前帧图像（BGR 格式）
            frame_id: 帧编号
            timestamp: 时间戳

        Returns:
            TrackedObject 列表

        Note:
            此方法设计为与检测器配合使用。Ultralytics 的 model.track()
            方法会同时进行检测和跟踪。如果已有检测结果，可以手动关联。

            推荐使用 TrackingPipeline 统一管理检测和跟踪流程。
        """
        # 将检测结果转换为带 track_id 的跟踪对象
        # 注意：这里简化处理，实际使用中应与检测器配合
        tracked_objects = []

        for detection in detections:
            # 如果检测已经有 track_id，创建 TrackedObject
            if detection.track_id is not None:
                tracked_obj = TrackedObject(
                    track_id=detection.track_id,
                    detection=detection,
                    frame_id=frame_id,
                    timestamp=timestamp,
                )
                tracked_objects.append(tracked_obj)

        self._frame_count += 1
        return tracked_objects

    def reset(self) -> None:
        """重置跟踪器状态

        清空所有跟踪状态，用于处理新视频。
        """
        self._frame_count = 0
        logger.debug("Tracker state reset")

    def get_tracker_config(self) -> dict:
        """获取跟踪器配置

        Returns:
            跟踪器配置字典
        """
        return self._tracker_config.copy()

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"PersonTracker(type={self.config.tracker_type}, "
            f"track_buffer={self.config.track_buffer})"
        )


class YOLOTrackerWrapper:
    """YOLO 跟踪器封装

    直接使用 Ultralytics YOLO 的 track() 方法进行检测+跟踪一体化。

    这种方式更简单，直接调用 model.track() 即可完成检测和跟踪。

    Example:
        >>> from ultralytics import YOLO
        >>> model = YOLO("yolo11n.pt")
        >>> results = model.track(source="video.mp4", tracker="bytetrack.yaml", persist=True)
    """

    def __init__(
        self,
        model,
        tracker_config: TrackerConfig,
    ) -> None:
        """初始化 YOLO 跟踪器封装

        Args:
            model: YOLO 模型实例
            tracker_config: 跟踪器配置
        """
        self.model = model
        self.tracker_config = tracker_config
        self._frame_count = 0

        logger.info(
            f"YOLOTrackerWrapper initialized: tracker={tracker_config.tracker_type}"
        )

    def track(
        self,
        frame: NDArray[np.uint8],
        frame_id: int = 0,
        timestamp: float = 0.0,
        confidence: float = 0.5,
        classes: list[int] = None,
    ) -> list[TrackedObject]:
        """检测并跟踪

        一体化检测+跟踪，返回带 track_id 的跟踪对象。

        Args:
            frame: BGR 格式图像
            frame_id: 帧编号
            timestamp: 时间戳
            confidence: 检测置信度阈值
            classes: 要检测的类别列表

        Returns:
            TrackedObject 列表

        Example:
            >>> tracker = YOLOTrackerWrapper(model, config)
            >>> tracked_objects = tracker.track(frame)
            >>> for obj in tracked_objects:
            ...     print(f"ID: {obj.track_id}, pos: {obj.center}")
        """
        if classes is None:
            classes = [0]  # 默认只检测 person

        try:
            # 使用 YOLO 的 track 方法
            results = self.model.track(
                frame,
                conf=confidence,
                classes=classes,
                tracker=f"{self.tracker_config.tracker_type}.yaml",
                persist=True,
                verbose=False,
            )

            # 转换结果
            tracked_objects = self._convert_results(
                results,
                frame_id,
                timestamp,
            )

            self._frame_count += 1
            return tracked_objects

        except Exception as e:
            raise InferenceError(
                f"Tracking inference failed",
                frame_id=frame_id,
                details=e,
            )

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
        tracked_objects = []

        if not results or len(results) == 0:
            return tracked_objects

        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return tracked_objects

        boxes = result.boxes

        # 检查是否有 track_id
        if boxes.id is None:
            logger.warning("No track IDs in results, tracking may not be enabled")
            return tracked_objects

        # 提取数据
        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        track_ids = boxes.id.cpu().numpy().astype(int)

        # 转换为 TrackedObject
        for i in range(len(xyxy)):
            from ..data.types import BoundingBox, Detection

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

    def reset(self) -> None:
        """重置跟踪器"""
        self._frame_count = 0
        logger.debug("YOLOTrackerWrapper reset")
