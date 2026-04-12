"""GUI 应用入口

人员检测跟踪系统的 GUI 应用程序入口点。

功能:
- QApplication 初始化和配置
- 主题和样式加载
- 窗口创建和显示
- 应用生命周期管理

使用方式:
    # 命令行启动
    python -m src.gui.app
    
    # 代码调用
    from src.gui import run_gui
    run_gui()
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont


def get_stylesheet() -> str:
    """获取样式表内容
    
    Returns:
        样式表字符串
    """
    # 样式文件路径
    style_path = Path(__file__).parent / "resources" / "styles" / "dark.qss"
    
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # 如果文件不存在，返回空样式
    return ""


def create_application(argv: Optional[list] = None) -> QApplication:
    """创建 QApplication 实例
    
    Args:
        argv: 命令行参数，默认使用 sys.argv
        
    Returns:
        配置好的 QApplication 实例
    """
    if argv is None:
        argv = sys.argv
    
    # 创建应用
    app = QApplication(argv)
    
    # 设置应用属性
    app.setApplicationName("Person Tracking System")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("PersonTracking")
    app.setOrganizationDomain("persontracking.local")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 加载样式表
    style = get_stylesheet()
    if style:
        app.setStyleSheet(style)
    
    return app


def create_main_window() -> "MainWindow":
    """创建主窗口
    
    Returns:
        配置好的 MainWindow 实例
    """
    # 延迟导入避免循环依赖
    from .main_window import MainWindow
    
    window = MainWindow()
    return window


def run_gui(argv: Optional[list] = None) -> int:
    """运行 GUI 应用
    
    Args:
        argv: 命令行参数
        
    Returns:
        应用退出码
    """
    # 创建应用
    app = create_application(argv)
    
    # 创建主窗口
    window = create_main_window()
    
    # 显示窗口
    window.show()
    
    # 运行事件循环
    return app.exec()


def main() -> int:
    """主入口函数"""
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
