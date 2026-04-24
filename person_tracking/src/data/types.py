"""数据类型定义模块

定义系统核心数据结构，用于：
- 检测结果表示
- 跟踪对象表示
- 帧数据封装
- 轨迹历史记录

所有类使用 dataclass 实现，保证不可变性和类型安全。
"""

from dataclasses import dataclass, field
from typing import Optional, Iterator
import numpy as np
from numpy.typing import NDArray


# ============================================================================
# 边界框
# ============================================================================


@dataclass
class BoundingBox:
    """边界框定义

    表示目标的矩形边界框，使用左上角坐标 + 宽高格式。

    Attributes:
        x: 左上角 x 坐标（像素）
        y: 左上角 y 坐标（像素）
        w: 边界框宽度（像素，必须 >= 0）
        h: 边界框高度（像素，必须 >= 0）
        confidence: 检测置信度 [0, 1]

    Note:
        坐标系：图像左上角为原点，x 向右，y 向下。

    Raises:
        ValueError: 当输入参数无效时
    """

    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """验证输入参数"""
        # 验证宽度和高度
        if self.w < 0:
            raise ValueError(f"宽度 w 不能为负数，当前值: {self.w}")
        if self.h < 0:
            raise ValueError(f"高度 h 不能为负数，当前值: {self.h}")

        # 验证置信度范围
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"置信度 confidence 必须在 [0, 1] 范围内，当前值: {self.confidence}"
            )

        # 验证坐标是否为数值
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.w, self.h, self.confidence]):
            raise ValueError("所有坐标和尺寸参数必须是数值类型")

    @property
    def center(self) -> tuple[float, float]:
        """计算边界框中心点坐标

        Returns:
            元组 (center_x, center_y)

        Example:
            >>> box = BoundingBox(x=100, y=100, w=50, h=80, confidence=0.95)
            >>> box.center
            (125.0, 140.0)
        """
        center_x = self.x + self.w / 2
        center_y = self.y + self.h / 2
        return (center_x, center_y)

    @property
    def area(self) -> float:
        """计算边界框面积

        Returns:
            面积值（像素平方）
        """
        return self.w * self.h

    @property
    def aspect_ratio(self) -> float:
        """计算边界框宽高比

        Returns:
            宽高比 (width / height)
        """
        if self.h == 0:
            return float("inf")
        return self.w / self.h

    def to_xyxy(self) -> tuple[float, float, float, float]:
        """转换为 (x1, y1, x2, y2) 格式

        Returns:
            元组 (x1, y1, x2, y2)

        Example:
            >>> box = BoundingBox(x=100, y=100, w=50, h=80, confidence=0.95)
            >>> box.to_xyxy()
            (100.0, 100.0, 150.0, 180.0)
        """
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    @classmethod
    def from_xyxy(
        cls,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        confidence: float = 1.0,
    ) -> "BoundingBox":
        """从 (x1, y1, x2, y2) 格式创建边界框

        Args:
            x1: 左上角 x 坐标
            y1: 左上角 y 坐标
            x2: 右下角 x 坐标
            y2: 右下角 y 坐标
            confidence: 检测置信度

        Returns:
            BoundingBox 实例

        Example:
            >>> box = BoundingBox.from_xyxy(100, 100, 150, 180, 0.95)
            >>> box.w, box.h
            (50.0, 80.0)
        """
        return cls(
            x=x1,
            y=y1,
            w=x2 - x1,
            h=y2 - y1,
            confidence=confidence,
        )

    def iou(self, other: "BoundingBox") -> float:
        """计算与另一个边界框的 IOU (Intersection over Union)

        Args:
            other: 另一个边界框

        Returns:
            IOU 值 [0, 1]

        Example:
            >>> box1 = BoundingBox.from_xyxy(0, 0, 100, 100)
            >>> box2 = BoundingBox.from_xyxy(50, 50, 150, 150)
            >>> box1.iou(box2)
            0.14285714285714285
        """
        # 计算交集
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.w, other.x + other.w)
        y2 = min(self.y + self.h, other.y + other.h)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)

        # 计算并集
        union = self.area + other.area - intersection

        if union == 0:
            return 0.0

        return intersection / union


# ============================================================================
# 检测结果
# ============================================================================


@dataclass
class Detection:
    """检测结果

    表示单次检测的结果，包含边界框、类别和置信度。

    Attributes:
        bbox: 边界框
        class_id: 类别 ID（COCO: person=0）
        class_name: 类别名称（如 "person"）
        track_id: 关联的跟踪 ID（跟踪后才赋值）
    """

    bbox: BoundingBox
    class_id: int
    class_name: str
    track_id: Optional[int] = None

    @property
    def confidence(self) -> float:
        """获取检测置信度"""
        return self.bbox.confidence

    @property
    def center(self) -> tuple[float, float]:
        """获取边界框中心点"""
        return self.bbox.center

    def assign_track_id(self, track_id: int) -> "Detection":
        """创建带跟踪 ID 的新检测对象

        Args:
            track_id: 跟踪 ID

        Returns:
            新的 Detection 实例（因为 dataclass 不可变）
        """
        return Detection(
            bbox=self.bbox,
            class_id=self.class_id,
            class_name=self.class_name,
            track_id=track_id,
        )


# ============================================================================
# 跟踪对象
# ============================================================================


@dataclass
class TrackedObject:
    """跟踪对象

    表示已关联 track_id 的检测对象，包含时序信息。

    Attributes:
        track_id: 跟踪 ID（全局唯一）
        detection: 关联的检测结果
        frame_id: 所在帧 ID
        timestamp: 时间戳（秒）
    """

    track_id: int
    detection: Detection
    frame_id: int
    timestamp: float

    @property
    def bbox(self) -> BoundingBox:
        """获取边界框"""
        return self.detection.bbox

    @property
    def center(self) -> tuple[float, float]:
        """获取中心点"""
        return self.bbox.center

    @property
    def confidence(self) -> float:
        """获取置信度"""
        return self.bbox.confidence


# ============================================================================
# 帧数据
# ============================================================================


@dataclass
class Frame:
    """帧数据

    封装单帧图像及其检测结果和跟踪结果。

    Attributes:
        frame_id: 帧 ID（从 0 开始）
        timestamp: 时间戳（秒）
        image: BGR 格式图像数组 (H, W, C)
        detections: 检测结果列表
        tracked_objects: 跟踪对象列表
    """

    frame_id: int
    timestamp: float
    image: NDArray[np.uint8]
    detections: list[Detection] = field(default_factory=list)
    tracked_objects: list[TrackedObject] = field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int, int]:
        """获取图像形状

        Returns:
            元组 (height, width, channels)
        """
        return self.image.shape

    @property
    def height(self) -> int:
        """获取图像高度"""
        return self.image.shape[0]

    @property
    def width(self) -> int:
        """获取图像宽度"""
        return self.image.shape[1]

    def add_detection(self, detection: Detection) -> None:
        """添加检测结果

        Args:
            detection: 检测结果
        """
        self.detections.append(detection)

    def add_tracked_object(self, tracked_obj: TrackedObject) -> None:
        """添加跟踪对象

        Args:
            tracked_obj: 跟踪对象
        """
        self.tracked_objects.append(tracked_obj)


# ============================================================================
# 轨迹历史
# ============================================================================


@dataclass
class Trajectory:
    """轨迹历史

    记录单个 track_id 的历史轨迹点。

    Attributes:
        track_id: 跟踪 ID
        points: 轨迹点列表，每个点为 (x, y, timestamp)
        max_length: 最大轨迹点数量（防止内存泄漏）
    """

    track_id: int
    points: list[tuple[float, float, float]] = field(default_factory=list)
    max_length: int = 100

    def add_point(self, x: float, y: float, timestamp: float) -> None:
        """添加轨迹点

        Args:
            x: 中心点 x 坐标
            y: 中心点 y 坐标
            timestamp: 时间戳

        Note:
            当轨迹点数量超过 max_length 时，自动移除最旧的点。
        """
        self.points.append((x, y, timestamp))

        # 保持轨迹长度限制
        if len(self.points) > self.max_length:
            self.points = self.points[-self.max_length :]

    def get_recent_points(self, n: int = 50) -> list[tuple[float, float, float]]:
        """获取最近 N 个轨迹点

        Args:
            n: 要获取的点数

        Returns:
            轨迹点列表 [(x, y, timestamp), ...]
        """
        return self.points[-n:] if n > 0 else []

    @property
    def last_point(self) -> Optional[tuple[float, float, float]]:
        """获取最后一个轨迹点

        Returns:
            最后一个点，或 None（如果轨迹为空）
        """
        return self.points[-1] if self.points else None

    @property
    def length(self) -> int:
        """获取轨迹长度

        Returns:
            轨迹点数量
        """
        return len(self.points)

    @property
    def duration(self) -> float:
        """计算轨迹持续时间

        Returns:
            持续时间（秒），如果少于2个点则返回0
        """
        if len(self.points) < 2:
            return 0.0
        return self.points[-1][2] - self.points[0][2]

    def clear(self) -> None:
        """清空轨迹"""
        self.points.clear()


# ============================================================================
# 性能指标
# ============================================================================


@dataclass
class PerformanceMetrics:
    """性能指标

    记录系统运行的性能数据。

    Attributes:
        fps: 实时帧率
        total_frames: 总处理帧数
        avg_detection_time_ms: 平均检测耗时（毫秒）
        avg_tracking_time_ms: 平均跟踪耗时（毫秒）
        avg_visualization_time_ms: 平均可视化耗时（毫秒）
        total_time_s: 总处理时间（秒）
    """

    fps: float = 0.0
    total_frames: int = 0
    avg_detection_time_ms: float = 0.0
    avg_tracking_time_ms: float = 0.0
    avg_visualization_time_ms: float = 0.0
    total_time_s: float = 0.0

    def update_fps(self, new_fps: float) -> None:
        """更新帧率（移动平均）

        Args:
            new_fps: 新的帧率测量值
        """
        if self.fps == 0.0:
            self.fps = new_fps
        else:
            # 简单移动平均
            self.fps = 0.9 * self.fps + 0.1 * new_fps
