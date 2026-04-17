"""
Person Tracking System
基于 YOLOv11 和 ByteTrack 的人物检测、跟踪与定位系统

模块结构：
- core: 核心业务模块（检测器、跟踪器、处理管道）
- data: 数据处理模块（加载器、数据类型、轨迹管理）
- viz: 可视化模块
- export: 导出模块
- infra: 基础设施（配置、日志、异常）
- gui: 图形用户界面模块（PySide6）

使用方式:
# Python API（仅在需要时导入，避免 GUI 启动时加载 YOLO）
from src.main import run_tracking
stats = run_tracking(source="video.mp4", output="output/tracked.mp4")

# CLI
python -m src.main --source video.mp4 --output output/tracked.mp4

# GUI 启动（不依赖 YOLO，可以独立运行）
python -m src.gui.app
"""

__version__ = "1.0.0"
__author__ = "Person Tracking Team"

# 注意：不在 __init__.py 中直接导入 run_tracking
# 这样可以避免 GUI 启动时意外加载 PyTorch/YOLO
# 用户需要时直接: from src.main import run_tracking

__all__ = []
