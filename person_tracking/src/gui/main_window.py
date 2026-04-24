"""主窗口模块

人员检测跟踪系统的主窗口框架。

架构:
- MainWindow: 主窗口容器
- MenuBar: 菜单栏 (文件/编辑/视图/工具/帮助)
- MainToolBar: 工具栏 (快捷操作按钮)
- StatusBar: 状态栏 (运行状态/FPS/检测数)
- CentralWidget: 中央三栏布局区域

使用方式:
    window = MainWindow()
    window.show()
"""

import csv
import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from pathlib import Path

# 避免循环导入
if TYPE_CHECKING:
    import cv2
    from ..core.pipeline import TrackingPipeline

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QToolBar,
    QMenuBar,
    QMenu,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QFrame,
    QGroupBox,
    QScrollArea,
    QTableWidgetItem,
)
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QIcon
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize

from .widgets.video_canvas import VideoCanvas


class MainWindow(QMainWindow):
    """主窗口
    
    人员检测跟踪系统的主窗口框架。
    包含菜单栏、工具栏、状态栏和中央三栏布局。
    
    Signals:
        video_source_selected: 视频源被选择时发出
        start_requested: 请求开始处理时发出
        pause_requested: 请求暂停时发出
        stop_requested: 请求停止时发出
        config_changed: 配置变更时发出
    """
    
    # 信号定义
    video_source_selected = Signal(str)
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    config_changed = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化主窗口
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 窗口属性
        self.setWindowTitle("人员检测跟踪系统 - Person Tracking System")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # 状态变量
        self._is_running = False
        self._is_paused = False
        self._current_source: Optional[str] = None
        self._source_type: str = "local"

        # 源选择控件引用
        self._source_type_combo = None
        self._stream_url_label = None
        self._stream_url_edit = None
        self._stream_connect_btn = None

        # Mock 数据生成器 (用于演示)
        self._mock_generator: Optional[object] = None
        self._mock_timer: Optional[QTimer] = None

        # 摄像头相关
        self._camera_capture: Optional["cv2.VideoCapture"] = None  # OpenCV VideoCapture
        self._camera_timer: Optional[QTimer] = None
        
        # Pipeline 相关
        self._pipeline: Optional["TrackingPipeline"] = None  # TrackingPipeline
        self._frame_count: int = 0
        self._last_fps_time: float = 0.0


        # Worker 线程 (性能优化) - 必须在__init__中初始化
        self._capture_worker = None
        self._inference_worker = None

        # 视频信息 (用于进度条)
        self._video_info = {
            'width': 0, 'height': 0, 'fps': 0.0,
            'total_frames': 0, 'current_frame': 0, 'is_local_video': False
        }

        # 进度条拖动状态
        self._is_dragging_slider = False

            # 初始化 UI
        self._init_ui()
        self._init_menu_bar()
        self._init_tool_bar()
        self._init_status_bar()
        self._init_connections()

        # 不再自动启动 Mock 演示，改为显示待机画面
        self._show_idle_screen()
    
    def _init_ui(self) -> None:
        """初始化 UI 布局"""
        # 中央控件
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        # 主布局
        self._main_layout = QVBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 三栏布局 (使用 QSplitter)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(2)
        
        # 左侧参数面板
        self._left_panel = self._create_left_panel()
        
        # 中间视频区域
        self._center_panel = self._create_center_panel()
        
        # 右侧状态面板
        self._right_panel = self._create_right_panel()
        
        # 添加到分割器
        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._center_panel)
        self._splitter.addWidget(self._right_panel)
        
        # 设置初始比例 (左:中:右 = 1:3:1)
        self._splitter.setSizes([250, 700, 250])
        
        self._main_layout.addWidget(self._splitter)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧参数面板
        
        Returns:
            左侧面板组件
        """
        panel = QWidget()
        panel.setMinimumWidth(200)
        panel.setMaximumWidth(350)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("参数设置")
        title.setObjectName("titleLabel")
        title.setStyleSheet("""
            QLabel#titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 8px;
                background-color: #2D2D30;
                border-radius: 4px;
            }
        """)
        layout.addWidget(title)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        # 滚动内容
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(12)
        
        # 视频源参数组
        source_group = self._create_source_group()
        scroll_layout.addWidget(source_group)
        
        # 检测参数组
        detector_group = self._create_detector_group()
        scroll_layout.addWidget(detector_group)
        
        # 跟踪参数组
        tracker_group = self._create_tracker_group()
        scroll_layout.addWidget(tracker_group)
        
        # 可视化参数组
        visualizer_group = self._create_visualizer_group()
        scroll_layout.addWidget(visualizer_group)
        
        # 导出设置组
        export_group = self._create_export_group()
        scroll_layout.addWidget(export_group)
        
        # 弹性空间
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return panel
    
    def _create_source_group(self) -> QGroupBox:
        """创建视频源参数组"""
        group = QGroupBox("视频源")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 源类型选择
        from PySide6.QtWidgets import QComboBox, QLineEdit
        self._source_type_combo = QComboBox()
        self._source_type_combo.addItems(["本地文件", "摄像头", "RTSP/HTTP 流"])
        self._source_type_combo.currentTextChanged.connect(self._on_source_type_changed)
        layout.addWidget(QLabel("源类型:"))
        layout.addWidget(self._source_type_combo)
        
        # 文件路径
        self._source_path_label = QLabel("未选择")
        self._source_path_label.setStyleSheet("color: #808080;")
        layout.addWidget(QLabel("文件路径:"))
        layout.addWidget(self._source_path_label)
        
        # 选择按钮
        from PySide6.QtWidgets import QPushButton
        self._select_file_btn = QPushButton("选择文件...")
        self._select_file_btn.clicked.connect(self._on_select_file)
        layout.addWidget(self._select_file_btn)

        # RTSP/HTTP URL 输入
        self._stream_url_label = QLabel("流地址:")
        self._stream_url_edit = QLineEdit()
        self._stream_url_edit.setPlaceholderText("rtsp://example.com/stream 或 http(s)://...")
        self._stream_connect_btn = QPushButton("连接流")
        self._stream_connect_btn.clicked.connect(self._on_connect_stream)

        layout.addWidget(self._stream_url_label)
        layout.addWidget(self._stream_url_edit)
        layout.addWidget(self._stream_connect_btn)

        self._stream_url_label.hide()
        self._stream_url_edit.hide()
        self._stream_connect_btn.hide()

        return group
    
    def _create_detector_group(self) -> QGroupBox:
        """创建检测参数组"""
        group = QGroupBox("检测参数")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            color: #FFFFFF;
            border: 1px solid #4E4E52;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: #2D2D30;
        }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 置信度阈值
        from PySide6.QtWidgets import QDoubleSpinBox, QSlider
        self._conf_spin = QDoubleSpinBox()
        self._conf_spin.setRange(0.0, 1.0)
        self._conf_spin.setSingleStep(0.05)
        self._conf_spin.setValue(0.5)
        self._conf_spin.setToolTip("检测置信度阈值")
        self._conf_spin.valueChanged.connect(self._on_config_value_changed)
        layout.addWidget(QLabel("置信度阈值:"))
        layout.addWidget(self._conf_spin)

        # IOU 阈值
        self._iou_spin = QDoubleSpinBox()
        self._iou_spin.setRange(0.0, 1.0)
        self._iou_spin.setSingleStep(0.05)
        self._iou_spin.setValue(0.45)
        self._iou_spin.setToolTip("NMS IOU 阈值")
        self._iou_spin.valueChanged.connect(self._on_config_value_changed)
        layout.addWidget(QLabel("IOU 阈值:"))
        layout.addWidget(self._iou_spin)

        # 设备选择
        from PySide6.QtWidgets import QComboBox
        self._device_combo = QComboBox()
        self._device_combo.addItems(["AUTO", "CUDA", "CPU"])
        self._device_combo.currentTextChanged.connect(self._on_config_value_changed)
        layout.addWidget(QLabel("推理设备:"))
        layout.addWidget(self._device_combo)

        return group
    
    def _create_tracker_group(self) -> QGroupBox:
        """创建跟踪参数组"""
        group = QGroupBox("跟踪参数")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            color: #FFFFFF;
            border: 1px solid #4E4E52;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: #2D2D30;
        }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 跟踪器类型
        from PySide6.QtWidgets import QComboBox, QSpinBox
        self._tracker_type_combo = QComboBox()
        self._tracker_type_combo.addItems(["ByteTrack", "BotSort"])
        self._tracker_type_combo.currentTextChanged.connect(self._on_config_value_changed)
        layout.addWidget(QLabel("跟踪器类型:"))
        layout.addWidget(self._tracker_type_combo)

        # 轨迹缓冲
        self._buffer_spin = QSpinBox()
        self._buffer_spin.setRange(1, 100)
        self._buffer_spin.setValue(30)
        self._buffer_spin.setToolTip("轨迹缓冲帧数")
        self._buffer_spin.valueChanged.connect(self._on_config_value_changed)
        layout.addWidget(QLabel("轨迹缓冲:"))
        layout.addWidget(self._buffer_spin)

        return group
    
    def _create_visualizer_group(self) -> QGroupBox:
        """创建可视化参数组"""
        group = QGroupBox("可视化设置")
        group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            color: #FFFFFF;
            border: 1px solid #4E4E52;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: #2D2D30;
        }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 复选框选项
        from PySide6.QtWidgets import QCheckBox
        self._show_bbox_check = QCheckBox("显示边界框")
        self._show_bbox_check.setChecked(True)
        self._show_bbox_check.stateChanged.connect(self._on_config_value_changed)
        layout.addWidget(self._show_bbox_check)

        self._show_trajectory_check = QCheckBox("显示轨迹")
        self._show_trajectory_check.setChecked(True)
        self._show_trajectory_check.stateChanged.connect(self._on_config_value_changed)
        layout.addWidget(self._show_trajectory_check)

        self._show_id_check = QCheckBox("显示 ID 标签")
        self._show_id_check.setChecked(True)
        self._show_id_check.stateChanged.connect(self._on_config_value_changed)
        layout.addWidget(self._show_id_check)

        self._show_center_check = QCheckBox("显示中心点")
        self._show_center_check.setChecked(True)
        self._show_center_check.stateChanged.connect(self._on_config_value_changed)
        layout.addWidget(self._show_center_check)

        self._show_confidence_check = QCheckBox("显示置信度")
        self._show_confidence_check.setChecked(True)
        self._show_confidence_check.stateChanged.connect(self._on_config_value_changed)
        layout.addWidget(self._show_confidence_check)

        return group
    
    def _create_export_group(self) -> QGroupBox:
        """创建导出设置组"""
        group = QGroupBox("导出设置")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 复选框选项
        from PySide6.QtWidgets import QCheckBox
        self._save_video_check = QCheckBox("保存输出视频")
        self._save_video_check.setChecked(False)
        self._save_video_check.setEnabled(False)
        self._save_video_check.setToolTip("当前版本未实现视频导出")
        layout.addWidget(self._save_video_check)
        
        self._save_csv_check = QCheckBox("导出 CSV 日志")
        self._save_csv_check.setChecked(True)
        layout.addWidget(self._save_csv_check)
        
        return group
    
    def _create_center_panel(self) -> QWidget:
        """创建中间视频区域
        
        Returns:
            中间面板组件
        """
        panel = QWidget()
        panel.setMinimumWidth(400)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 视频画布
        self._video_canvas = VideoCanvas()
        layout.addWidget(self._video_canvas, 1)
        
        # 播放控制栏
        controls = self._create_playback_controls()
        layout.addWidget(controls)
        
        return panel
    
    def _create_playback_controls(self) -> QWidget:
        """创建播放控制栏"""
        controls = QWidget()
        controls.setMaximumHeight(60)
        controls.setStyleSheet("""
            QWidget {
                background-color: #2D2D30;
                border-radius: 6px;
            }
        """)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        from PySide6.QtWidgets import QPushButton, QSlider, QLabel
        
        # 播放按钮
        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(40, 40)
        self._play_btn.setToolTip("开始")
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                font-size: 16px;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #0098E5;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        layout.addWidget(self._play_btn)
        
        # 暂停按钮
        self._pause_btn = QPushButton("▮▮")
        self._pause_btn.setFixedSize(40, 40)
        self._pause_btn.setToolTip("暂停")
        self._pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #4E4E52;
                color: white;
                font-size: 12px;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #5E5E62;
            }
        """)
        layout.addWidget(self._pause_btn)
        
        # 停止按钮
        self._stop_btn = QPushButton("■")
        self._stop_btn.setFixedSize(40, 40)
        self._stop_btn.setToolTip("停止")
        self._stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #CE9178;
                color: white;
                font-size: 16px;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #DEA188;
            }
        """)
        layout.addWidget(self._stop_btn)
        
        # 进度条
        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setEnabled(False)
        self._progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background-color: #3E3E42;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background-color: #007ACC;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background-color: #007ACC;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._progress_slider, 1)
        
        # 时间显示
        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setStyleSheet("color: #D4D4D4; font-family: 'Consolas', monospace;")
        layout.addWidget(self._time_label)
        
        return controls
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧状态面板
        
        Returns:
            右侧面板组件
        """
        panel = QWidget()
        panel.setMinimumWidth(200)
        panel.setMaximumWidth(350)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("状态信息")
        title.setObjectName("titleLabel")
        title.setStyleSheet("""
            QLabel#titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 8px;
                background-color: #2D2D30;
                border-radius: 4px;
            }
        """)
        layout.addWidget(title)
        
        # 统计卡片组
        stats_group = QGroupBox("统计信息")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(12)
        
        # FPS 卡片
        fps_card = self._create_stat_card("当前帧率", "0.0", "FPS")
        stats_layout.addWidget(fps_card)
        
        # 帧数卡片
        frame_card = self._create_stat_card("当前帧", "0", "帧")
        stats_layout.addWidget(frame_card)
        
        # 检测数卡片
        detection_card = self._create_stat_card("检测数", "0", "人")
        stats_layout.addWidget(detection_card)
        
        layout.addWidget(stats_group)
        
        # 目标列表
        targets_group = QGroupBox("目标列表")
        targets_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        targets_layout = QVBoxLayout(targets_group)
        
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self._target_table = QTableWidget()
        self._target_table.setColumnCount(3)
        self._target_table.setHorizontalHeaderLabels(["ID", "置信度", "位置"])
        self._target_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._target_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._target_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._target_table.setColumnWidth(0, 50)
        self._target_table.setColumnWidth(1, 70)
        self._target_table.setAlternatingRowColors(True)
        self._target_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._target_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        targets_layout.addWidget(self._target_table)
        layout.addWidget(targets_group, 1)

        # 轨迹历史
        from .widgets.trajectory_list import TrajectoryList
        trajectory_group = QGroupBox("轨迹历史")
        trajectory_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        trajectory_layout = QVBoxLayout(trajectory_group)
        self._trajectory_list = TrajectoryList()
        trajectory_layout.addWidget(self._trajectory_list)
        layout.addWidget(trajectory_group, 1)

        # 日志面板
        from .widgets.log_panel import LogPanel
        log_group = QGroupBox("日志")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #4E4E52;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2D2D30;
            }
        """)
        
        log_layout = QVBoxLayout(log_group)
        self._log_panel = LogPanel()
        log_layout.addWidget(self._log_panel)
        layout.addWidget(log_group, 1)

        return panel
    
    def _create_stat_card(self, title: str, value: str, unit: str) -> QWidget:
        """创建统计卡片
        
        Args:
            title: 标题
            value: 数值
            unit: 单位
            
        Returns:
            卡片组件
        """
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #3E3E42;
                border-radius: 6px;
            }
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 数值
        value_label = QLabel(value)
        value_label.setObjectName("valueLabel")
        value_label.setStyleSheet("""
            QLabel#valueLabel {
                font-size: 20px;
                font-weight: bold;
                color: #007ACC;
            }
        """)
        layout.addWidget(value_label)
        
        # 单位
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(unit_label)
        
        return card
    
    def _init_menu_bar(self) -> None:
        """初始化菜单栏"""
        self._menu_bar = self.menuBar()
        self._menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2D2D30;
                color: #D4D4D4;
                padding: 4px;
            }
            QMenuBar::item:selected {
                background-color: #3E3E42;
            }
        """)
        
        # 文件菜单
        file_menu = self._menu_bar.addMenu("文件(&F)")
        
        open_video_action = QAction("打开视频(&O)", self)
        open_video_action.setShortcut(QKeySequence.StandardKey.Open)
        open_video_action.triggered.connect(self._on_open_video)
        file_menu.addAction(open_video_action)
        
        open_camera_action = QAction("打开摄像头(&C)", self)
        open_camera_action.triggered.connect(self._on_open_camera)
        file_menu.addAction(open_camera_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出结果(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self._menu_bar.addMenu("编辑(&E)")
        
        config_action = QAction("参数设置(&S)", self)
        config_action.setShortcut(QKeySequence("Ctrl+,"))
        edit_menu.addAction(config_action)
        
        edit_menu.addSeparator()
        
        reset_action = QAction("重置参数(&R)", self)
        edit_menu.addAction(reset_action)
        
        # 视图菜单
        view_menu = self._menu_bar.addMenu("视图(&V)")
        
        fullscreen_action = QAction("全屏(&F)", self)
        fullscreen_action.setShortcut(QKeySequence.StandardKey.FullScreen)
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        view_menu.addSeparator()
        
        reset_layout_action = QAction("重置布局(&R)", self)
        reset_layout_action.triggered.connect(self._reset_layout)
        view_menu.addAction(reset_layout_action)
        
        # 工具菜单
        tools_menu = self._menu_bar.addMenu("工具(&T)")
        
        model_action = QAction("模型管理(&M)", self)
        tools_menu.addAction(model_action)
        
        tools_menu.addSeparator()
        
        log_action = QAction("查看日志(&L)", self)
        tools_menu.addAction(log_action)
        
        # 帮助菜单
        help_menu = self._menu_bar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        doc_action = QAction("使用文档(&D)", self)
        help_menu.addAction(doc_action)
    
    def _init_tool_bar(self) -> None:
        """初始化工具栏"""
        self._tool_bar = QToolBar("主工具栏")
        self._tool_bar.setMovable(False)
        self._tool_bar.setIconSize(QSize(32, 32))
        self._tool_bar.setStyleSheet("""
            QToolBar {
                background-color: #2D2D30;
                border: none;
                padding: 4px;
                spacing: 4px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                color: #D4D4D4;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #3E3E42;
            }
            QToolButton:pressed {
                background-color: #007ACC;
            }
        """)
        
        self.addToolBar(self._tool_bar)
        
        # 添加工具按钮
        open_btn = QAction("📁 打开", self)
        open_btn.setToolTip("打开视频文件")
        open_btn.triggered.connect(self._on_open_video)
        self._tool_bar.addAction(open_btn)
        
        camera_btn = QAction("📷 摄像头", self)
        camera_btn.setToolTip("打开摄像头")
        camera_btn.triggered.connect(self._on_open_camera)
        self._tool_bar.addAction(camera_btn)
        
        self._tool_bar.addSeparator()
        
        start_btn = QAction("▶ 开始", self)
        start_btn.setToolTip("开始检测")
        start_btn.triggered.connect(self._on_start)
        self._tool_bar.addAction(start_btn)
        
        pause_btn = QAction("⏸ 暂停", self)
        pause_btn.setToolTip("暂停检测")
        pause_btn.triggered.connect(self._on_pause)
        self._tool_bar.addAction(pause_btn)
        
        stop_btn = QAction("⏹ 停止", self)
        stop_btn.setToolTip("停止检测")
        stop_btn.triggered.connect(self._on_stop)
        self._tool_bar.addAction(stop_btn)
        
        self._tool_bar.addSeparator()
        
        export_btn = QAction("💾 导出", self)
        export_btn.setToolTip("导出结果")
        export_btn.triggered.connect(self._on_export)
        self._tool_bar.addAction(export_btn)
        
        settings_btn = QAction("⚙ 设置", self)
        settings_btn.setToolTip("参数设置")
        self._tool_bar.addAction(settings_btn)
    
    def _init_status_bar(self) -> None:
        """初始化状态栏"""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        
        self._status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #007ACC;
                color: #FFFFFF;
                font-size: 12px;
                padding: 4px 8px;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # 状态指示器
        self._status_label = QLabel("● 就绪")
        self._status_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self._status_bar.addWidget(self._status_label)
        
        self._status_bar.addWidget(QLabel("|"))
        
        # FPS
        self._fps_status = QLabel("FPS: --")
        self._fps_status.setStyleSheet("color: #FFFFFF;")
        self._status_bar.addWidget(self._fps_status)
        
        self._status_bar.addWidget(QLabel("|"))
        
        # 检测数
        self._count_status = QLabel("检测数: 0")
        self._count_status.setStyleSheet("color: #FFFFFF;")
        self._status_bar.addWidget(self._count_status)
        
        self._status_bar.addWidget(QLabel("|"))
        
        # 设备
        self._device_status = QLabel("设备: AUTO")
        self._device_status.setStyleSheet("color: #FFFFFF;")
        self._status_bar.addPermanentWidget(self._device_status)
    
    def _init_connections(self) -> None:
        """初始化信号连接"""
        # 播放控制按钮
        self._play_btn.clicked.connect(self._on_start)
        self._pause_btn.clicked.connect(self._on_pause)
        self._stop_btn.clicked.connect(self._on_stop)
        
        # 视频画布信号
        self._video_canvas.frame_clicked.connect(self._on_frame_clicked)
    
    # ========================================================================
    # 槽函数
    # ========================================================================

    @Slot(str)
    def _on_source_type_changed(self, source_text: str) -> None:
        """处理源类型切换。"""
        source_map = {
            "本地文件": "local",
            "摄像头": "camera",
            "RTSP/HTTP 流": "stream",
        }
        self._source_type = source_map.get(source_text, "local")

        if self._source_type == "local":
            self._select_file_btn.setText("选择文件...")
            self._stream_url_label.hide()
            self._stream_url_edit.hide()
            self._stream_connect_btn.hide()
        elif self._source_type == "camera":
            self._select_file_btn.setText("连接摄像头")
            self._stream_url_label.hide()
            self._stream_url_edit.hide()
            self._stream_connect_btn.hide()
        else:
            self._select_file_btn.setText("连接流")
            self._stream_url_label.show()
            self._stream_url_edit.show()
            self._stream_connect_btn.show()
    
    @Slot()
    def _on_open_video(self) -> None:
        """打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )
        
        if file_path:
            self._is_running = False
            self._is_paused = False
            self._stop_all_sources()
            self._current_source = file_path
            self._source_type = "local"
            if self._source_type_combo is not None:
                self._source_type_combo.setCurrentText("本地文件")
            self._source_path_label.setText(Path(file_path).name)
            self._source_path_label.setStyleSheet("color: #D4D4D4;")
            self.video_source_selected.emit(file_path)
            self._update_status("已加载", "blue")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"已选择视频: {Path(file_path).name}")
    
    @Slot()
    def _on_open_camera(self) -> None:
        """打开摄像头"""
        # 停止其他源
        self._is_running = False
        self._is_paused = False
        self._stop_all_sources()
        
        # 尝试打开摄像头
        import cv2
        self._camera_capture = cv2.VideoCapture(0)
        
        if not self._camera_capture.isOpened():
            self._update_status("摄像头打开失败", "red")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error("无法打开摄像头，请检查设备")
            self._show_idle_screen()
            return
        
        self._current_source = "camera:0"
        self._source_type = "camera"
        if self._source_type_combo is not None:
            self._source_type_combo.setCurrentText("摄像头")
        self._source_path_label.setText("摄像头 0")
        self._source_path_label.setStyleSheet("color: #4EC9B0;")
        self._update_status("摄像头就绪", "blue")
        
        if hasattr(self, '_log_panel'):
            self._log_panel.log_info("摄像头已连接")
        
        # 启动摄像头定时器
        self._camera_timer = QTimer(self)
        self._camera_timer.timeout.connect(self._update_camera_frame)
        self._camera_timer.start(33)  # ~30 FPS

    @Slot()
    def _on_connect_stream(self) -> None:
        """连接 RTSP/HTTP 视频流。"""
        if self._stream_url_edit is None:
            return

        stream_url = self._stream_url_edit.text().strip()
        if not stream_url.startswith(("rtsp://", "http://", "https://")):
            QMessageBox.warning(self, "流地址无效", "请输入 rtsp:// 或 http(s):// 开头的地址")
            return

        self._is_running = False
        self._is_paused = False
        self._stop_all_sources()

        self._current_source = stream_url
        self._source_type = "stream"
        if self._source_type_combo is not None:
            self._source_type_combo.setCurrentText("RTSP/HTTP 流")
        self._source_path_label.setText(stream_url)
        self._source_path_label.setStyleSheet("color: #4EC9B0;")
        self._update_status("流地址已就绪", "blue")

        if hasattr(self, '_log_panel'):
            self._log_panel.log_info(f"已设置流地址: {stream_url}")

    @Slot()
    def _on_select_file(self) -> None:
        """从左侧面板选择文件按钮"""
        if self._source_type == "camera":
            self._on_open_camera()
            return

        if self._source_type == "stream":
            self._on_connect_stream()
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )

        if file_path:
            self._is_running = False
            self._is_paused = False
            self._stop_all_sources()
            self._current_source = file_path
            self._source_type = "local"
            if self._source_type_combo is not None:
                self._source_type_combo.setCurrentText("本地文件")
            self._source_path_label.setText(Path(file_path).name)
            self._source_path_label.setStyleSheet("color: #4EC9B0;")
            self.video_source_selected.emit(file_path)
            self._update_status("已加载", "blue")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"已选择视频: {Path(file_path).name}")

    def _start_worker_mode(self) -> bool:
        """启动 Worker 线程模式
        
        将视频采集和推理处理移到后台线程，避免阻塞 GUI 主线程。
        这是 Worker 集成的主要入口点。
        """
        if not self._current_source:
            if hasattr(self, '_log_panel'):
                self._log_panel.log_warning("请先选择视频源")
            return False
        
        try:
            # 停止现有 workers
            self._stop_workers()
            # 启动检测前停止摄像头预览，避免与 worker 双路径并发
            self._stop_camera()

            self._video_info = {
                'width': 0,
                'height': 0,
                'fps': 0.0,
                'total_frames': 0,
                'current_frame': 0,
                'is_local_video': False,
            }
            self._frame_count = 0
            self._progress_slider.setEnabled(False)
            self._progress_slider.setToolTip("当前仅支持进度显示，不支持拖动跳转")
            self._time_label.setText("00:00 / 00:00")
            
            # 创建配置
            from ..infra.config import load_config
            config = load_config()
            
            # 应用当前 UI 配置
            self._apply_ui_config_to_pipeline_config(config)
            
            # 初始化 Pipeline
            from ..core.pipeline import TrackingPipeline
            self._pipeline = TrackingPipeline(config)
            self._pipeline.warmup()
            self._device_status.setText(f"设备: {self._pipeline.config.detector.device.upper()}")
            
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info("Pipeline 已初始化并预热")
            
            # 创建 Capture Worker
            from .workers import VideoCaptureWorker, InferenceWorker
            
            self._capture_worker = VideoCaptureWorker(
                source=self._current_source,
                target_fps=30.0,
                parent=self
            )
            
            # 连接 Capture Worker 信号
            self._capture_worker.frame_ready.connect(self._on_worker_frame_ready)
            self._capture_worker.error.connect(self._on_worker_error)
            self._capture_worker.finished.connect(self._on_capture_finished)
            
            # 创建 Inference Worker
            self._inference_worker = InferenceWorker(
                config=config,
                parent=self
            )
            
            # 设置 Pipeline
            self._inference_worker.set_pipeline(self._pipeline)
            
            # 连接 Inference Worker 信号
            self._inference_worker.result_ready.connect(self._on_inference_result_ready)
            self._inference_worker.error.connect(self._on_worker_error)
            self._inference_worker.finished.connect(self._on_inference_finished)
            self._inference_worker.metrics_updated.connect(self._on_metrics_updated)
            
            # 连接 Capture -> Inference 的帧传递
            self._capture_worker.frame_ready.connect(self._inference_worker.submit_frame)
            
            # 启动 Workers
            self._inference_worker.start()
            self._capture_worker.start()
            
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"Worker 线程已启动: 源={self._current_source}")

            return True
            
        except Exception as e:
            self._update_status("启动失败", "red")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error(f"启动 Worker 失败: {str(e)}")
            self._is_running = False
            self._stop_workers()
            return False
    
    @Slot(object)
    def _on_worker_frame_ready(self, frame_data: object) -> None:
        """处理 Worker 捕获的帧 (仅预览模式使用)"""
        capture_worker = getattr(self, "_capture_worker", None)
        if capture_worker:
            self._video_info = capture_worker.video_info
            if self._video_info.get('is_local_video'):
                self._progress_slider.setEnabled(False)
                self._progress_slider.setToolTip("当前仅支持进度显示，不支持拖动跳转")
            else:
                self._progress_slider.setValue(0)
                self._time_label.setText("LIVE")

        # 在主线程中显示原始帧（当不运行检测时）
        if not self._is_running:
            self._video_canvas.set_frame(frame_data.frame)
    
    @Slot(object)
    def _on_inference_result_ready(self, result: object) -> None:
        """处理推理结果"""
        if not self._is_running:
            return
        
        try:
            # 显示处理后的帧（已由 Visualizer 渲染）
            self._video_canvas.set_frame(result.frame)
            self._video_canvas.set_info_text(result.info_text)
            
            # 更新目标表格
            self._update_target_table(result.detections)
            
            # 更新轨迹列表
            if hasattr(self, '_trajectory_list'):
                self._trajectory_list.update_trajectories(result.trajectories)
            
            # 更新进度条
            if self._video_info.get('is_local_video'):
                self._update_progress_from_frame(result.frame_id)
                
        except Exception as e:
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error(f"处理推理结果失败: {str(e)}")
    
    @Slot(dict)
    def _on_metrics_updated(self, metrics: dict) -> None:
        """更新性能指标"""
        fps = metrics.get('fps', 0)
        inference_time = metrics.get('inference_time', 0)
        detection_count = metrics.get('detection_count', 0)
        
        self._fps_status.setText(f"FPS: {fps:.1f}")
        self._count_status.setText(f"检测数: {detection_count}")
        
        # 记录性能日志
        if hasattr(self, '_log_panel') and self._is_running:
            if metrics.get('frame_id', 0) % 60 == 0:  # 每60帧记录一次
                self._log_panel.log_info(
                    f"性能指标 - FPS: {fps:.1f}, "
                    f"推理时间: {inference_time:.1f}ms, "
                    f"检测数: {detection_count}"
                )
    
    @Slot(str)
    def _on_worker_error(self, error_msg: str) -> None:
        """处理 Worker 错误"""
        self._update_status("错误", "red")
        if hasattr(self, '_log_panel'):
            self._log_panel.log_error(f"Worker 错误: {error_msg}")
        
        # 停止运行
        self._is_running = False
        self._stop_workers()
    
    @Slot()
    def _on_capture_finished(self) -> None:
        """Capture Worker 结束"""
        if hasattr(self, '_log_panel'):
            self._log_panel.log_info("视频采集已结束")
        
        # 停止 Inference Worker
        if self._inference_worker:
            self._inference_worker.stop()
        
        if self._is_running:
            self._is_running = False
            self._update_status("已停止", "gray")
    
    @Slot()
    def _on_inference_finished(self) -> None:
        """Inference Worker 结束"""
        if hasattr(self, '_log_panel'):
            self._log_panel.log_info("推理处理已结束")
    
    def _update_target_table(self, detections: list) -> None:
        """更新目标表格"""
        self._target_table.setRowCount(len(detections))
        for i, det in enumerate(detections):
            track_id, x, y, w, h, conf = det
            self._target_table.setItem(i, 0, QTableWidgetItem(str(track_id)))
            self._target_table.setItem(i, 1, QTableWidgetItem(f"{conf:.2f}"))
            self._target_table.setItem(i, 2, QTableWidgetItem(f"({int(x)}, {int(y)})"))
    
    def _update_progress_from_frame(self, frame_id: int) -> None:
        """根据帧 ID 更新进度条"""
        if not self._is_dragging_slider and self._video_info.get('total_frames', 0) > 0:
            total = self._video_info['total_frames']
            progress = int((min(frame_id, total) / total) * 100)
            self._progress_slider.setValue(progress)
            
            # 更新时间标签
            fps = self._video_info.get('fps', 0) or 30
            current_sec = frame_id / fps
            total_sec = total / fps
            self._time_label.setText(
                f"{self._format_time(current_sec)} / {self._format_time(total_sec)}"
            )
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _collect_ui_config_snapshot(self) -> dict:
        """采集当前 UI 参数快照。"""
        return {
            'detector': {
                'confidence_threshold': float(self._conf_spin.value()),
                'iou_threshold': float(self._iou_spin.value()),
                'device': self._device_combo.currentText().lower(),
            },
            'tracker': {
                'tracker_type': self._tracker_type_combo.currentText().lower(),
                'track_buffer': int(self._buffer_spin.value()),
            },
            'visualizer': {
                'show_bbox': self._show_bbox_check.isChecked(),
                'show_trajectory': self._show_trajectory_check.isChecked(),
                'show_id': self._show_id_check.isChecked(),
                'show_center_point': self._show_center_check.isChecked(),
                'show_confidence': self._show_confidence_check.isChecked(),
            },
        }
    
    def _apply_ui_config_to_pipeline_config(self, config: Any) -> None:
        """将 UI 配置应用到 Pipeline 配置"""
        ui_config = self._collect_ui_config_snapshot()

        config.detector.confidence_threshold = ui_config['detector']['confidence_threshold']
        config.detector.iou_threshold = ui_config['detector']['iou_threshold']
        config.detector.device = ui_config['detector']['device']

        config.tracker.tracker_type = ui_config['tracker']['tracker_type']
        config.tracker.track_buffer = ui_config['tracker']['track_buffer']

        config.visualizer.show_bbox = ui_config['visualizer']['show_bbox']
        config.visualizer.show_trajectory = ui_config['visualizer']['show_trajectory']
        config.visualizer.show_id = ui_config['visualizer']['show_id']
        config.visualizer.show_center_point = ui_config['visualizer']['show_center_point']
        config.visualizer.show_confidence = ui_config['visualizer']['show_confidence']

        self._device_status.setText(f"设备: {config.detector.device.upper()}")
    
    @Slot()
    def _on_start(self) -> None:
        """开始处理"""
        # 暂停恢复
        if self._is_running and self._is_paused:
            self._is_paused = False
            capture_worker = getattr(self, "_capture_worker", None)
            inference_worker = getattr(self, "_inference_worker", None)
            if capture_worker:
                capture_worker.resume()
            if inference_worker:
                inference_worker.resume()
            self._update_status("运行中", "green")
            self.start_requested.emit()
            return

        # 已在运行中，无需重复启动
        if self._is_running:
            return

        if not self._current_source:
            QMessageBox.warning(self, "开始处理", "请先选择视频源")
            return

        if self._source_type == "camera" and self._current_source != "camera:0":
            QMessageBox.warning(self, "开始处理", "当前为摄像头模式，请先点击“连接摄像头”")
            return

        if self._source_type == "stream" and not self._current_source.startswith(("rtsp://", "http://", "https://")):
            QMessageBox.warning(self, "开始处理", "当前为流模式，请先输入并连接 RTSP/HTTP 地址")
            return

        if self._source_type == "local" and self._current_source.startswith(("camera:", "rtsp://", "http://", "https://")):
            QMessageBox.warning(self, "开始处理", "当前为本地文件模式，请先选择本地视频文件")
            return

        self._is_running = True
        self._is_paused = False

        started = self._start_worker_mode()
        if not started:
            self._is_running = False
            self._is_paused = False
            return

        self._update_status("运行中", "green")
        self.start_requested.emit()
    
    @Slot()
    def _on_pause(self) -> None:
        """暂停处理"""
        if self._is_running and not self._is_paused:
            self._is_paused = True
            
            # 安全获取worker属性
            capture_worker = getattr(self, "_capture_worker", None)
            inference_worker = getattr(self, "_inference_worker", None)
            
            if capture_worker:
                capture_worker.pause()
            if inference_worker:
                inference_worker.pause()
                
            self._update_status("已暂停", "yellow")
            self.pause_requested.emit()
    
    @Slot()
    def _on_stop(self) -> None:
        """停止处理"""
        self._is_running = False
        self._is_paused = False

        self._stop_all_sources()
        self._video_info = {
            'width': 0,
            'height': 0,
            'fps': 0.0,
            'total_frames': 0,
            'current_frame': 0,
            'is_local_video': False,
        }

        # 重置进度条
        if hasattr(self, '_progress_slider'):
            self._progress_slider.setValue(0)
        if hasattr(self, '_time_label'):
            self._time_label.setText("00:00 / 00:00")

        self._update_status("已停止", "gray")
        self.stop_requested.emit()
    
    @Slot(int, int)
    def _on_frame_clicked(self, x: int, y: int) -> None:
        """处理帧点击事件"""
        # TODO: 实现点击目标选择
        pass
    
    @Slot()
    def _toggle_fullscreen(self) -> None:
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    @Slot()
    def _reset_layout(self) -> None:
        """重置布局"""
        self._splitter.setSizes([250, 700, 250])
    
    @Slot()
    def _show_about(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """<h2>人员检测跟踪系统</h2>
            <p>版本: 0.1.0</p>
            <p>基于 YOLOv11 和 ByteTrack 的实时人员检测与跟踪系统。</p>
            <p>功能特性:</p>
            <ul>
            <li>实时人员检测</li>
            <li>多目标跟踪</li>
            <li>轨迹记录与可视化</li>
            <li>结果导出</li>
            </ul>
            <p>© 2024 Person Tracking System</p>
            """
        )

    def _get_exportable_trajectories(self) -> dict:
        """获取可导出的轨迹（至少包含一个轨迹点）。"""
        if self._pipeline is None or not hasattr(self._pipeline, 'trajectory_manager'):
            return {}

        trajectories = self._pipeline.trajectory_manager.get_all_trajectories()
        return {
            track_id: trajectory
            for track_id, trajectory in trajectories.items()
            if getattr(trajectory, 'points', None)
        }

    @Slot()
    def _on_export(self) -> None:
        """导出当前 MainWindow 运行路径下的轨迹结果。"""
        if self._current_source is None:
            QMessageBox.warning(self, "导出", "请先选择视频源")
            return
        
        # 检查是否有处理数据可以导出
        if self._pipeline is None:
            QMessageBox.warning(self, "导出", "请先开始处理以生成数据")
            return

        trajectories = self._get_exportable_trajectories()
        if not trajectories:
            QMessageBox.warning(self, "导出", "当前没有可导出的轨迹数据")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_warning("导出取消：轨迹数据为空")
            return

        # 选择导出目录
        export_dir = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not export_dir:
            return
        
        export_path = Path(export_dir)
        self._update_status("导出中...", "blue")
        
        try:
            exported_files = []
            
            # 1. 导出 CSV 跟踪日志
            csv_path = self._export_csv(export_path)
            if csv_path:
                exported_files.append(f"CSV: {csv_path.name}")
            
            # 2. 导出轨迹统计数据
            stats_path = self._export_trajectory_stats(export_path)
            if stats_path:
                exported_files.append(f"统计: {stats_path.name}")
            
            # 3. 导出视频 - 暂不支持
            # video_path = self._export_video(export_path)
            # if video_path:
            #     exported_files.append(f"视频: {video_path.name}")
            
            # 显示结果
            if exported_files:
                files_text = "\n".join(f"  • {f}" for f in exported_files)
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"已成功导出以下文件到:\n{export_dir}\n\n{files_text}"
                )
                self._update_status("导出完成", "green")
                if hasattr(self, '_log_panel'):
                    self._log_panel.log_info(f"导出完成: {len(exported_files)} 个文件")
            else:
                QMessageBox.warning(self, "导出", "没有可导出的数据")
                self._update_status("就绪", "gray")
                
        except Exception as e:
            self._update_status("导出失败", "red")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出过程中发生错误:\n{str(e)}")
    
    def _export_csv(self, export_path: Path) -> Optional[Path]:
        """导出轨迹点 CSV。
        
        Args:
            export_path: 导出目录路径
            
        Returns:
            导出的文件路径，如果没有数据则返回 None
        """
        if self._pipeline is None:
            return None

        trajectories = self._get_exportable_trajectories()
        if not trajectories:
            return None

        csv_file = export_path / "tracks.csv"
        
        try:
            row_count = 0
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["track_id", "point_index", "timestamp", "x", "y"])

                for track_id, trajectory in trajectories.items():
                    for idx, (x, y, timestamp) in enumerate(trajectory.points):
                        writer.writerow([
                            int(track_id),
                            idx,
                            f"{timestamp:.6f}",
                            f"{x:.2f}",
                            f"{y:.2f}",
                        ])
                        row_count += 1

            if row_count == 0:
                return None

            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"CSV 导出: {row_count} 条轨迹点")

            return csv_file
                
        except Exception as e:
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error(f"CSV 导出失败: {str(e)}")
            raise
    
    def _export_trajectory_stats(self, export_path: Path) -> Optional[Path]:
        """导出轨迹统计数据
        
        Args:
            export_path: 导出目录路径
            
        Returns:
            导出的文件路径，如果没有数据则返回 None
        """
        if self._pipeline is None:
            return None
        
        trajectories = self._get_exportable_trajectories()
        if not trajectories:
            return None

        stats_file = export_path / "trajectory_stats.json"
        
        try:
            # 获取统计信息
            stats = self._pipeline.trajectory_manager.get_statistics()

            if stats.get('total_trajectories', 0) <= 0:
                return None
            
            # 添加导出时间戳
            stats['export_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stats['source'] = self._current_source
            stats['tracks'] = {
                str(track_id): {
                    'point_count': len(trajectory.points),
                    'start_timestamp': trajectory.points[0][2],
                    'end_timestamp': trajectory.points[-1][2],
                }
                for track_id, trajectory in trajectories.items()
            }
            
            # 写入 JSON
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"统计导出: {stats_file.name}")
            
            return stats_file
            
        except Exception as e:
            if hasattr(self, '_log_panel'):
                self._log_panel.log_error(f"统计导出失败: {str(e)}")
            raise
    
    def _export_video(self, export_path: Path) -> Optional[Path]:
        """导出处理后的视频
        
        Args:
            export_path: 导出目录路径
            
        Returns:
            导出的文件路径，如果没有数据则返回 None
        
        Note:
            当前版本返回 None，因为视频导出需要在处理过程中实时写入。
            后续可以添加重新处理功能来导出视频。
        """
        # 视频导出需要在处理过程中实时记录
        # 当前返回 None，表示暂不支持事后导出
        # 用户可以通过设置 pipeline.save_output = True 在处理时保存
        return None
    
    # ========================================================================
    # 内部方法
    # ========================================================================
    
    def _update_status(self, text: str, color: str) -> None:
        """更新状态显示
        
        Args:
            text: 状态文本
            color: 颜色 (green/yellow/red/blue/gray)
        """
        color_map = {
            "green": "#4EC9B0",
            "yellow": "#DC8C6A",
            "red": "#CE9178",
            "blue": "#007ACC",
            "gray": "#808080",
        }
        
        status_text = f"● {text}"
        self._status_label.setText(status_text)
        self._status_label.setStyleSheet(f"color: {color_map.get(color, '#FFFFFF')}; font-weight: bold;")
    
    def _start_mock_demo(self) -> None:
        """启动 Mock 演示（已废弃）。"""
        self._update_status("请先选择视频源", "yellow")

    def _stop_mock_demo(self) -> None:
        """停止 Mock 演示"""
        if self._mock_timer:
            self._mock_timer.stop()
            self._mock_timer = None
        self._mock_generator = None

    def _stop_all_sources(self) -> None:
        """停止所有视频源"""
        self._stop_workers()
        self._stop_mock_demo()
        self._stop_camera()

    def _stop_workers(self) -> None:
        """停止Worker线程 - 安全版本"""
        capture_worker = getattr(self, "_capture_worker", None)
        inference_worker = getattr(self, "_inference_worker", None)
        
        if capture_worker:
            try:
                capture_worker.stop()
                capture_worker.wait(1000)
            except Exception:
                pass
            self._capture_worker = None

        if inference_worker:
            try:
                inference_worker.stop()
                inference_worker.wait(1000)
            except Exception:
                pass
            self._inference_worker = None

    def _stop_camera(self) -> None:
        """停止摄像头"""
        if self._camera_timer:
            self._camera_timer.stop()
            self._camera_timer = None
        if self._camera_capture is not None:
            self._camera_capture.release()
            self._camera_capture = None

    def _show_idle_screen(self) -> None:
        """显示待机画面"""
        import numpy as np
        
        # 创建待机画面
        idle_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 绘制提示文字
        import cv2
        text = "请选择视频源"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 1.5, 2)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = (480 + text_size[1]) // 2
        cv2.putText(idle_frame, text, (text_x, text_y), font, 1.5, (100, 100, 100), 2)
        
        # 显示
        self._video_canvas.set_frame(idle_frame)
        self._video_canvas.set_info_text("等待视频源...")
        
        # 重置状态
        self._update_status("就绪", "gray")
    
    @Slot()
    def _update_mock_frame(self) -> None:
        """更新 Mock 帧"""
        # Mock功能已禁用，此方法保留但不再使用
        pass

    @Slot()
    def _update_camera_frame(self) -> None:
        """更新摄像头预览帧（仅预览，不做推理）。"""
        
        if self._camera_capture is None or not self._camera_capture.isOpened():
            return
        
        ret, frame = self._camera_capture.read()
        if not ret:
            return
        
        self._frame_count += 1

        self._video_canvas.set_frame(frame)
        self._video_canvas.set_info_text(f"Preview | Frame: {self._frame_count}")
        self._fps_status.setText("FPS: --")
        self._count_status.setText("预览模式")

    @Slot()
    def _on_config_value_changed(self) -> None:
        """处理配置值变化 - 热更新支持
        
        当用户在 UI 中修改参数时，立即更新配置并通知 InferenceWorker。
        """
        config_update = self._collect_ui_config_snapshot()
        self.config_changed.emit(config_update)

        detector_cfg = config_update['detector']
        tracker_cfg = config_update['tracker']
        visualizer_cfg = config_update['visualizer']

        # 运行时可热更新参数：置信度、IOU、可视化开关
        if self._pipeline is not None and hasattr(self._pipeline, 'config'):
            self._pipeline.config.detector.confidence_threshold = detector_cfg['confidence_threshold']
            self._pipeline.config.detector.iou_threshold = detector_cfg['iou_threshold']

            if hasattr(self._pipeline, 'visualizer'):
                viz_cfg = self._pipeline.visualizer.config
                viz_cfg.show_bbox = visualizer_cfg['show_bbox']
                viz_cfg.show_trajectory = visualizer_cfg['show_trajectory']
                viz_cfg.show_id = visualizer_cfg['show_id']
                viz_cfg.show_center_point = visualizer_cfg['show_center_point']
                viz_cfg.show_confidence = visualizer_cfg['show_confidence']

        # InferenceWorker 同步运行时参数
        if self._inference_worker:
            try:
                self._inference_worker.set_confidence_threshold(detector_cfg['confidence_threshold'])
                self._inference_worker.set_iou_threshold(detector_cfg['iou_threshold'])
                self._inference_worker.set_show_trajectory(visualizer_cfg['show_trajectory'])
            except Exception as e:
                if hasattr(self, '_log_panel'):
                    self._log_panel.log_warning(f"配置更新失败: {str(e)}")

        # 启动前参数（device/tracker_type/track_buffer）运行中不支持热更新
        restart_required = []
        if self._is_running and self._pipeline is not None and hasattr(self._pipeline, 'config'):
            if self._pipeline.config.detector.device != detector_cfg['device']:
                restart_required.append('device')
            if self._pipeline.config.tracker.tracker_type != tracker_cfg['tracker_type']:
                restart_required.append('tracker_type')
            if self._pipeline.config.tracker.track_buffer != tracker_cfg['track_buffer']:
                restart_required.append('track_buffer')

        if restart_required:
            msg = f"以下参数需重新开始后生效: {', '.join(restart_required)}"
            self._update_status("部分参数需重启生效", "yellow")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_warning(msg)
        elif hasattr(self, '_log_panel'):
            self._log_panel.log_info("配置已更新并生效")

        # 状态栏显示当前实际生效设备
        if self._is_running and self._pipeline is not None and hasattr(self._pipeline, 'config'):
            applied_device = self._pipeline.config.detector.device
        else:
            applied_device = detector_cfg['device']
        self._device_status.setText(f"设备: {applied_device.upper()}")

    def closeEvent(self, event) -> None:
        """关闭事件"""
        # 安全停止所有workers和源
        self._stop_workers()
        self._stop_all_sources()

        # 清理Pipeline
        if hasattr(self, '_pipeline') and self._pipeline:
            self._pipeline = None

        event.accept()
