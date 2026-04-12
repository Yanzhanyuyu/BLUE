"""GUI 模块

人员检测跟踪系统的 PySide6 图形用户界面。

架构设计:
- Views: 纯 UI 渲染层
- Controllers: 连接 View 与 Service
- Services: 封装核心算法调用
- Workers: 后台线程执行耗时操作

使用方式:
    from src.gui import run_gui
    run_gui()
"""

from .app import run_gui, create_application, create_main_window
from .main_window import MainWindow
from .widgets import VideoCanvas

__version__ = "0.1.0"

__all__ = [
    "run_gui",
    "create_application",
    "create_main_window",
    "MainWindow",
    "VideoCanvas",
]
