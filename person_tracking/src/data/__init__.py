"""数据处理模块

包含：
- loader: 视频/摄像头加载器
- types: 数据类型定义
- trajectory: 轨迹管理
"""

from .loader import VideoLoader
from .types import BoundingBox, Detection, TrackedObject, Frame, Trajectory
from .trajectory import TrajectoryManager

__all__ = [
    "VideoLoader",
    "BoundingBox",
    "Detection",
    "TrackedObject",
    "Frame",
    "Trajectory",
    "TrajectoryManager",
]
