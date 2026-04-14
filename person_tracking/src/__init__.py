"""
Person Tracking System
基于 YOLOv11 和 ByteTrack 的人物检测、跟踪与定位系统

模块结构：
- core: 核心业务模块（检测器、跟踪器、处理管道）
- data: 数据处理模块（加载器、数据类型、轨迹管理）
- viz: 可视化模块
- export: 导出模块
- infra: 基础设施（配置、日志、异常）

使用方式:
    # Python API
    from src import run_tracking
    stats = run_tracking(source="video.mp4", output="output/tracked.mp4")
    
    # CLI
    python -m src.main --source video.mp4 --output output/tracked.mp4
"""

__version__ = "1.0.0"
__author__ = "Person Tracking Team"

# 导出便捷 API
from .main import run_tracking

__all__ = ["run_tracking"]
