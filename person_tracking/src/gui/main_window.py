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

from typing import Optional, TYPE_CHECKING
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
from PySide6.QtGui import QActionGroup, QKeySequence, QIcon

from .widgets.video_canvas import VideoCanvas, MockFrameGenerator


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

        # Mock 数据生成器 (用于演示)
        self._mock_generator: Optional[MockFrameGenerator] = None
        self._mock_timer: Optional[QTimer] = None

        # 摄像头相关
        self._camera_capture: Optional["cv2.VideoCapture"] = None  # OpenCV VideoCapture
        self._camera_timer: Optional[QTimer] = None
        
        # Pipeline 相关
        self._pipeline: Optional["TrackingPipeline"] = None  # TrackingPipeline
        self._frame_count: int = 0
        self._last_fps_time: float = 0.0

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
        from PySide6.QtWidgets import QComboBox
        source_type = QComboBox()
        source_type.addItems(["本地文件", "摄像头", "RTSP 流"])
        layout.addWidget(QLabel("源类型:"))
        layout.addWidget(source_type)
        
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
        conf_spin = QDoubleSpinBox()
        conf_spin.setRange(0.0, 1.0)
        conf_spin.setSingleStep(0.05)
        conf_spin.setValue(0.5)
        conf_spin.setToolTip("检测置信度阈值")
        layout.addWidget(QLabel("置信度阈值:"))
        layout.addWidget(conf_spin)
        
        # IOU 阈值
        iou_spin = QDoubleSpinBox()
        iou_spin.setRange(0.0, 1.0)
        iou_spin.setSingleStep(0.05)
        iou_spin.setValue(0.45)
        iou_spin.setToolTip("NMS IOU 阈值")
        layout.addWidget(QLabel("IOU 阈值:"))
        layout.addWidget(iou_spin)
        
        # 设备选择
        from PySide6.QtWidgets import QComboBox
        device_combo = QComboBox()
        device_combo.addItems(["CUDA", "CPU"])
        layout.addWidget(QLabel("推理设备:"))
        layout.addWidget(device_combo)
        
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
        tracker_type = QComboBox()
        tracker_type.addItems(["ByteTrack", "BotSort"])
        layout.addWidget(QLabel("跟踪器类型:"))
        layout.addWidget(tracker_type)
        
        # 轨迹缓冲
        buffer_spin = QSpinBox()
        buffer_spin.setRange(1, 100)
        buffer_spin.setValue(30)
        buffer_spin.setToolTip("轨迹缓冲帧数")
        layout.addWidget(QLabel("轨迹缓冲:"))
        layout.addWidget(buffer_spin)
        
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
        show_bbox = QCheckBox("显示边界框")
        show_bbox.setChecked(True)
        layout.addWidget(show_bbox)
        
        show_trajectory = QCheckBox("显示轨迹")
        show_trajectory.setChecked(True)
        layout.addWidget(show_trajectory)
        
        show_id = QCheckBox("显示 ID 标签")
        show_id.setChecked(True)
        layout.addWidget(show_id)
        
        show_center = QCheckBox("显示中心点")
        show_center.setChecked(True)
        layout.addWidget(show_center)
        
        show_confidence = QCheckBox("显示置信度")
        show_confidence.setChecked(True)
        layout.addWidget(show_confidence)
        
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
        save_video = QCheckBox("保存输出视频")
        save_video.setChecked(True)
        layout.addWidget(save_video)
        
        save_csv = QCheckBox("导出 CSV 日志")
        save_csv.setChecked(True)
        layout.addWidget(save_csv)
        
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
        self._device_status = QLabel("设备: CUDA")
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
            self._current_source = file_path
            self._source_path_label.setText(Path(file_path).name)
            self._source_path_label.setStyleSheet("color: #D4D4D4;")
            self.video_source_selected.emit(file_path)
            self._update_status("已加载", "blue")
    
    @Slot()
    def _on_open_camera(self) -> None:
        """打开摄像头"""
        # 停止其他源
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
    def _on_select_file(self) -> None:
        """从左侧面板选择文件按钮"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )

        if file_path:
            self._current_source = file_path
            self._source_path_label.setText(Path(file_path).name)
            self._source_path_label.setStyleSheet("color: #4EC9B0;")
            self.video_source_selected.emit(file_path)
            self._update_status("已加载", "blue")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"已选择视频: {Path(file_path).name}")
    
    @Slot()
    def _on_start(self) -> None:
        """开始处理"""
        if not self._is_running:
            self._is_running = True
            self._is_paused = False
            self._update_status("运行中", "green")
            self.start_requested.emit()
    
    @Slot()
    def _on_pause(self) -> None:
        """暂停处理"""
        if self._is_running and not self._is_paused:
            self._is_paused = True
            self._update_status("已暂停", "yellow")
            self.pause_requested.emit()
    
    @Slot()
    def _on_stop(self) -> None:
        """停止处理"""
        self._is_running = False
        self._is_paused = False
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

    @Slot()
    def _on_export(self) -> None:
        """导出结果"""
        if self._current_source is None:
            QMessageBox.warning(self, "导出", "请先选择视频源")
            return
        
        # 选择导出目录
        export_dir = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if export_dir:
            self._update_status("导出中...", "blue")
            if hasattr(self, '_log_panel'):
                self._log_panel.log_info(f"导出目录: {export_dir}")
            # TODO: 实际导出逻辑将在后续阶段实现
            QMessageBox.information(
                self,
                "导出",
                f"导出功能将在后续阶段实现\n目标目录: {export_dir}"
            )
            self._update_status("导出完成", "green")
    
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
        """启动 Mock 演示"""
        # 先停止其他源
        self._stop_all_sources()
        
        self._mock_generator = MockFrameGenerator()
        self._mock_timer = QTimer(self)
        self._mock_timer.timeout.connect(self._update_mock_frame)
        self._mock_timer.start(33)  # ~30 FPS

    def _stop_mock_demo(self) -> None:
        """停止 Mock 演示"""
        if self._mock_timer:
            self._mock_timer.stop()
            self._mock_timer = None
        self._mock_generator = None

    def _stop_all_sources(self) -> None:
        """停止所有视频源"""
        self._stop_mock_demo()
        self._stop_camera()

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
        self._video_canvas.set_overlay(info_text="等待视频源...")
        
        # 重置状态
        self._update_status("就绪", "gray")
    
    @Slot()
    def _update_mock_frame(self) -> None:
        """更新 Mock 帧"""
        if self._mock_generator:
            frame, detections, trajectories, info_text = self._mock_generator.generate()
            self._video_canvas.set_frame(frame)
            self._video_canvas.set_overlay(detections, trajectories, info_text)

            # 更新状态栏
            fps = 28.5 + (hash(str(self._mock_generator._frame_count)) % 30) / 10
            self._fps_status.setText(f"FPS: {fps:.1f}")
            self._count_status.setText(f"检测数: {len(detections)}")

            # 更新目标表格
            self._target_table.setRowCount(len(detections))
            for i, det in enumerate(detections):
                track_id, x, y, w, h, conf = det
                self._target_table.setItem(i, 0, QTableWidgetItem(str(track_id)))
                self._target_table.setItem(i, 1, QTableWidgetItem(f"{conf:.2f}"))
                self._target_table.setItem(i, 2, QTableWidgetItem(f"({int(x)}, {int(y)})"))

            # 更新轨迹列表
            if hasattr(self, '_trajectory_list'):
                self._trajectory_list.update_trajectories(trajectories)

        # 记录日志 (每10帧记录一次)
        if hasattr(self, '_log_panel') and self._mock_generator._frame_count % 30 == 0:
            self._log_panel.log_info(f"Frame: {self._mock_generator._frame_count}, Detections: {len(detections)}")

    @Slot()
    def _update_camera_frame(self) -> None:
        """更新摄像头帧"""
        import time
        
        if self._camera_capture is None or not self._camera_capture.isOpened():
            return
        
        ret, frame = self._camera_capture.read()
        if not ret:
            return
        
        self._frame_count += 1
        
        # 如果正在运行检测，执行检测逻辑
        if self._is_running:
            try:
                # 延迟初始化 Pipeline
                if self._pipeline is None:
                    from ..infra.config import load_config
                    from ..core.pipeline import TrackingPipeline
                    from ..data.types import Frame as DataFrame
                    
                    config = load_config()  # 使用默认配置
                    self._pipeline = TrackingPipeline(config)
                    self._pipeline.warmup()
                    
                    if hasattr(self, '_log_panel'):
                        self._log_panel.log_info("Pipeline 已初始化")
                
                # 创建帧对象
                from ..data.types import Frame as DataFrame
                timestamp = time.time()
                data_frame = DataFrame(
                    frame_id=self._frame_count,
                    timestamp=timestamp,
                    image=frame
                )
                
                # 执行检测和跟踪
                processed_frame, tracked_objects = self._pipeline.process_frame(data_frame)
                
                # 准备叠加数据
                detections = []
                trajectories = {}
                
                for obj in tracked_objects:
                    bbox = obj.bbox
                    detections.append((
                        obj.track_id,
                        int(bbox.x),
                        int(bbox.y),
                        int(bbox.w),
                        int(bbox.h),
                        bbox.confidence
                    ))
                
                # 从 trajectory_manager 获取轨迹
                if hasattr(self._pipeline, 'trajectory_manager'):
                    for track_id, traj in self._pipeline.trajectory_manager._trajectories.items():
                        trajectories[track_id] = traj.points[-50:]  # 最近50个点
                
                # 计算并显示 FPS
                current_time = time.time()
                if self._last_fps_time > 0:
                    fps = 1.0 / (current_time - self._last_fps_time) if (current_time - self._last_fps_time) > 0 else 0
                    self._fps_status.setText(f"FPS: {fps:.1f}")
                self._last_fps_time = current_time
                
                # 信息文本
                info_text = f"Frame: {self._frame_count} | Persons: {len(tracked_objects)}"
                
                # 显示处理后的帧
                self._video_canvas.set_frame(processed_frame.image)
                self._video_canvas.set_overlay(detections, trajectories, info_text)
                
                # 更新状态
                self._count_status.setText(f"检测数: {len(tracked_objects)}")
                
                # 更新目标表格
                self._target_table.setRowCount(len(detections))
                for i, det in enumerate(detections):
                    track_id, x, y, w, h, conf = det
                    self._target_table.setItem(i, 0, QTableWidgetItem(str(track_id)))
                    self._target_table.setItem(i, 1, QTableWidgetItem(f"{conf:.2f}"))
                    self._target_table.setItem(i, 2, QTableWidgetItem(f"({int(x)}, {int(y)})"))
                
                # 更新轨迹列表
                if hasattr(self, '_trajectory_list'):
                    self._trajectory_list.update_trajectories(trajectories)
                
                # 记录日志
                if hasattr(self, '_log_panel') and self._frame_count % 30 == 0:
                    self._log_panel.log_info(f"Frame: {self._frame_count}, 检测到 {len(tracked_objects)} 人")
                    
            except Exception as e:
                if hasattr(self, '_log_panel'):
                    self._log_panel.log_error(f"检测错误: {str(e)}")
                # 出错时显示原始帧
                self._video_canvas.set_frame(frame)
        else:
            # 仅显示预览
            self._video_canvas.set_frame(frame)
            self._fps_status.setText("FPS: --")
            self._count_status.setText("预览模式")
    
    def closeEvent(self, event) -> None:
        """关闭事件"""
        # 停止所有源
        self._stop_all_sources()
        event.accept()
