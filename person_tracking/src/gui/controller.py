"""Deprecated GUI controller shim.

该模块曾维护与 MainWindow 并行的一套 GUI 状态管理逻辑，
但当前真实运行入口仅使用 MainWindow。
为避免长期双实现漂移，原控制器实现已移除，仅保留兼容壳。
"""

from typing import Optional
from warnings import warn

from PySide6.QtCore import QObject


class TrackingController(QObject):
    """已废弃：请改用 MainWindow 真实运行路径。"""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        warn(
            "TrackingController 已废弃，当前运行入口仅支持 MainWindow。",
            DeprecationWarning,
            stacklevel=2,
        )
