"""视频画布组件 - 纯显示层（重构后）

用于显示已由 Visualizer 渲染好的帧，不再负责任何检测框、轨迹、ID的绘制。

职责：
- 显示已由 Pipeline/Visualizer 渲染好的帧
- 高质量缩放显示（SmoothTransformation）
- 鼠标交互（缩放、平移）
- 信息文本显示（帧号、FPS等）

使用方式：
canvas = VideoCanvas()
canvas.set_frame(rendered_frame)  # 必须是已由 Visualizer 渲染的帧

重构说明：
- 移除了 _draw_overlay 方法（不再二次绘制）
- 移除了所有 OpenCV 绘制代码
- 移除了硬编码颜色常量（颜色由 VisualizerConfig 控制）
- set_frame 现在只接收已渲染的帧
- 缩放改为高质量模式（SmoothTransformation）
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QMouseEvent,
    QWheelEvent,
)


class VideoCanvas(QWidget):
    """视频画布组件 - 纯显示层

    重要：本组件不负责任何可视化元素的绘制。
    所有边界框、轨迹、ID、文字都应由 Visualizer 在 Pipeline 层完成渲染，
    本组件仅负责将已渲染的帧高质量地显示出来。

    信号：
        frame_clicked: 点击画布时发出，参数为 (x, y) 坐标
        zoom_changed: 缩放变化时发出，参数为新的缩放因子
    """

    # 信号定义
    frame_clicked = Signal(int, int)  # 点击坐标
    zoom_changed = Signal(float)  # 缩放因子变化
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化视频画布

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        # 内部状态
        self._current_frame: Optional[NDArray[np.uint8]] = None
        self._current_pixmap: Optional[QPixmap] = None

        # 缩放和平移状态
        self._zoom_factor: float = 1.0
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._last_mouse_pos: QPoint = QPoint()

        # 高质量渲染标志
        self._high_quality_render: bool = True

        # 信息文本
        self._info_text: str = ""

        # 初始化 UI
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self) -> None:
        """初始化 UI 布局"""
        # 设置尺寸策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 240)
        
        # 主布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # 图像显示标签
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, 
            QSizePolicy.Policy.Ignored
        )
        self._image_label.setMinimumSize(1, 1)
        
        # 信息叠加标签 (帧号、FPS 等)
        self._info_label = QLabel()
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._info_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background-color: rgba(30, 30, 30, 180);
                padding: 8px;
                border-radius: 4px;
                font-family: 'Consolas', 'Microsoft YaHei Mono', monospace;
                font-size: 12px;
            }
        """)
        
        # 将信息标签置于图像标签之上
        self._image_label.setParent(self)
        self._info_label.setParent(self)
        self._info_label.raise_()

        # 注意：图像标签不添加到布局，由代码手动控制位置（居中显示）
        # 这样可以避免布局刷新导致的位置跳动问题
        # _info_label 也不添加到布局，使用绝对位置固定在左上角

    def _apply_style(self) -> None:
        """应用样式"""
        self.setStyleSheet("""
            VideoCanvas {
                background-color: #1E1E1E;
                border: 2px solid #4E4E52;
                border-radius: 8px;
            }
        """)
    
    # ========================================================================
    # 公共方法
    # ========================================================================
    
    def set_frame(self, frame: NDArray[np.uint8]) -> None:
        """设置当前显示的帧（必须是已渲染的帧）

        重要：传入的 frame 必须已由 Visualizer.render() 渲染完成，
        包含检测框、轨迹、ID、文字等所有可视化元素。
        本方法不负责任何绘制，只负责显示。

        Args:
            frame: BGR 格式的图像数组 (H, W, C)，已由 Visualizer 渲染
        """
        if frame is None or frame.size == 0:
            return

        self._current_frame = frame
        self._update_display()
    
    def set_info_text(self, text: str) -> None:
        """设置信息文本（显示在左上角）

        Args:
            text: 信息文本，支持多行
        """
        self._info_text = text
        self._update_info_label()
    
    def clear(self) -> None:
        """清除画布"""
        self._current_frame = None
        self._current_pixmap = None
        self._info_text = ""
        self._image_label.clear()
        self._info_label.clear()
    
    def get_zoom(self) -> float:
        """获取当前缩放因子"""
        return self._zoom_factor
    
    def set_zoom(self, factor: float) -> None:
        """设置缩放因子
        
        Args:
            factor: 新的缩放因子
        """
        factor = max(self._min_zoom, min(self._max_zoom, factor))
        if factor != self._zoom_factor:
            self._zoom_factor = factor
            self._update_display()
            self.zoom_changed.emit(factor)
    
    def reset_zoom(self) -> None:
        """重置缩放为适应窗口"""
        self._zoom_factor = 1.0
        self._pan_offset = QPoint(0, 0)
        self._update_display()
    
    def fit_to_window(self) -> None:
        """适应窗口大小"""
        if self._current_frame is None:
            return
        
        frame_h, frame_w = self._current_frame.shape[:2]
        widget_w, widget_h = self.width(), self.height()
        
        if widget_w > 0 and widget_h > 0:
            scale_x = widget_w / frame_w
            scale_y = widget_h / frame_h
            self._zoom_factor = min(scale_x, scale_y, 1.0)
            self._update_display()
    
    # ========================================================================
    # 内部方法
    # ========================================================================
    
    def _update_display(self) -> None:
        """更新显示 - 高质量缩放"""
        if self._current_frame is None:
            return

        frame = self._current_frame

        # 转换为 RGB 格式（OpenCV使用BGR，Qt使用RGB）
        if frame.ndim == 3 and frame.shape[2] == 3:
            rgb_frame = frame[:, :, ::-1]  # BGR to RGB
            rgb_frame = np.ascontiguousarray(rgb_frame)
        else:
            rgb_frame = frame

        h, w = rgb_frame.shape[:2]
        bytes_per_line = 3 * w

        # 创建 QImage
        q_image = QImage(
            rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )

        # 计算缩放尺寸
        scaled_w = int(w * self._zoom_factor)
        scaled_h = int(h * self._zoom_factor)

        if scaled_w > 0 and scaled_h > 0:
            # 关键修改：使用 SmoothTransformation 代替 FastTransformation
            # 确保视觉质量，不要为了表面流畅牺牲清晰度
            transform_mode = (
                Qt.TransformationMode.SmoothTransformation
                if self._high_quality_render
                else Qt.TransformationMode.FastTransformation
            )

            scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                scaled_w, scaled_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                transform_mode
            )
            self._current_pixmap = scaled_pixmap
            self._image_label.setPixmap(scaled_pixmap)
            self._image_label.resize(scaled_pixmap.size())

            # 修复：显式居中显示，防止位置跳动
            # AlignCenter 只对 pixmap 内容有效，对 label 自身位置无效
            center_x = (self.width() - scaled_pixmap.width()) // 2
            center_y = (self.height() - scaled_pixmap.height()) // 2
            self._image_label.move(center_x, center_y)

        # 更新信息标签
        self._update_info_label()

    def _update_info_label(self) -> None:
        """更新信息标签"""
        if self._info_text:
            self._info_label.setText(self._info_text)
            self._info_label.adjustSize()
            self._info_label.move(10, 10)
            self._info_label.show()
        else:
            self._info_label.hide()
    
    # ========================================================================
    # 事件处理
    # ========================================================================
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动事件"""
        if self._is_panning:
            delta = event.pos() - self._last_mouse_pos
            self._pan_offset += delta
            self._last_mouse_pos = event.pos()
            self._image_label.move(
                self._pan_offset.x() + (self.width() - self._image_label.width()) // 2,
                self._pan_offset.y() + (self.height() - self._image_label.height()) // 2
            )
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # 发送点击信号
            if self._current_frame is not None:
                # 计算点击在原始帧上的坐标
                label_pos = self._image_label.mapFromParent(event.pos())
                x = int(label_pos.x() / self._zoom_factor)
                y = int(label_pos.y() / self._zoom_factor)
                self.frame_clicked.emit(x, y)
        
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """滚轮事件 - 缩放"""
        # 获取滚轮方向
        delta = event.angleDelta().y()
        
        # 计算新的缩放因子
        zoom_delta = 0.1 if delta > 0 else -0.1
        new_zoom = self._zoom_factor + zoom_delta
        
        # 限制缩放范围
        self.set_zoom(new_zoom)
        
        event.accept()
    
    def resizeEvent(self, event) -> None:
        """调整大小事件"""
        super().resizeEvent(event)
        if self._current_frame is not None:
            self._update_display()
