"""核心业务模块

包含：
- detector: 人物检测器（YOLOv11封装）
- tracker: 人物跟踪器（ByteTrack封装）
- pipeline: 处理管道
"""

from .detector import PersonDetector
from .tracker import PersonTracker
from .pipeline import TrackingPipeline

__all__ = ["PersonDetector", "PersonTracker", "TrackingPipeline"]
