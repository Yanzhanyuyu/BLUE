"""轨迹列表组件

显示选中目标的轨迹历史记录。

功能:
- 选择目标 ID 查看轨迹
- 显示轨迹点数和持续时间
- 支持轨迹数据实时更新
"""

from typing import Optional
from collections import deque

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, Slot


class TrajectoryList(QWidget):
    """轨迹列表组件
    
    显示选中目标的轨迹历史记录，支持 ID 选择和数据更新。
    
    Signals:
        track_id_selected: 选择轨迹 ID 时发出
    """
    
    track_id_selected = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化轨迹列表组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 轨迹数据存储
        self._trajectories: dict[int, list] = {}  # {track_id: [(x, y, t), ...]}
        self._current_track_id: Optional[int] = None
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # ID 选择区
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("选择 ID:"))
        
        self._id_combo = QComboBox()
        self._id_combo.setMinimumWidth(80)
        self._id_combo.currentIndexChanged.connect(self._on_id_changed)
        select_layout.addWidget(self._id_combo)
        
        layout.addLayout(select_layout)
        
        # 轨迹信息
        self._info_label = QLabel("点数: 0 | 持续: 0.0s")
        self._info_label.setStyleSheet("color: #808080; font-size: 11px;")
        layout.addWidget(self._info_label)
        
        # 轨迹点列表
        self._point_list = QListWidget()
        self._point_list.setAlternatingRowColors(True)
        self._point_list.setStyleSheet("""
            QListWidget {
                background-color: #2D2D30;
                border: 1px solid #4E4E52;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #007ACC;
            }
        """)
        layout.addWidget(self._point_list, 1)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    @Slot(dict)
    def update_trajectories(self, trajectories: dict[int, list]) -> None:
        """更新轨迹数据
        
        Args:
            trajectories: 轨迹数据字典 {track_id: [(x, y, t), ...]}
        """
        self._trajectories = trajectories
        
        # 更新 ID 下拉框
        current_ids = set(self._trajectories.keys())
        old_ids = {self._id_combo.itemData(i) for i in range(self._id_combo.count())}
        
        # 添加新 ID
        for tid in current_ids - old_ids:
            self._id_combo.addItem(f"ID: {tid}", tid)
        
        # 移除不存在的 ID
        for i in range(self._id_combo.count() - 1, -1, -1):
            if self._id_combo.itemData(i) not in current_ids:
                self._id_combo.removeItem(i)
        
        # 更新当前显示
        self._update_display()
    
    @Slot(int)
    def set_current_track(self, track_id: int) -> None:
        """设置当前选中的轨迹 ID
        
        Args:
            track_id: 轨迹 ID
        """
        self._current_track_id = track_id
        
        # 在下拉框中选择
        for i in range(self._id_combo.count()):
            if self._id_combo.itemData(i) == track_id:
                self._id_combo.setCurrentIndex(i)
                break
    
    @Slot()
    def _on_id_changed(self) -> None:
        """处理 ID 选择变化"""
        if self._id_combo.currentIndex() >= 0:
            track_id = self._id_combo.currentData()
            self._current_track_id = track_id
            self._update_display()
            self.track_id_selected.emit(track_id)
    
    def _update_display(self) -> None:
        """更新显示内容"""
        self._point_list.clear()
        
        if self._current_track_id is None or self._current_track_id not in self._trajectories:
            self._info_label.setText("点数: 0 | 持续: 0.0s")
            return
        
        points = self._trajectories[self._current_track_id]
        
        # 更新信息
        if points:
            duration = points[-1][2] - points[0][2] if len(points) > 1 else 0.0
            self._info_label.setText(f"点数: {len(points)} | 持续: {duration:.1f}s")
        else:
            self._info_label.setText("点数: 0 | 持续: 0.0s")
        
        # 显示最近的轨迹点 (最多50个)
        recent_points = points[-50:] if len(points) > 50 else points
        
        for i, (x, y, t) in enumerate(reversed(recent_points)):
            item = QListWidgetItem(f"({int(x)}, {int(y)}) @ {t:.3f}s")
            self._point_list.addItem(item)
    
    def clear(self) -> None:
        """清空数据"""
        self._trajectories = {}
        self._current_track_id = None
        self._id_combo.clear()
        self._point_list.clear()
        self._info_label.setText("点数: 0 | 持续: 0.0s")
