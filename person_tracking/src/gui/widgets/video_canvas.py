"""视频画布组件

用于显示视频帧和叠加检测结果的可视化组件。

功能:
- 显示 OpenCV 图像 (BGR 格式自动转换)
- 支持图像缩放和居中显示
- 支持绘制检测框、轨迹线、ID 标签
- 支持鼠标交互 (缩放、平移)

使用方式:
    canvas = VideoCanvas()
    canvas.set_frame(frame_image)  # numpy array
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QRect
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QFont,
    QMouseEvent,
    QWheelEvent,
)


class VideoCanvas(QWidget):
    """视频画布组件
    
    用于显示视频帧和叠加检测结果的可视化组件。
    支持图像缩放、居中显示和鼠标交互。
    
    Attributes:
        zoom_factor: 当前缩放因子
        min_zoom: 最小缩放比例
        max_zoom: 最大缩放比例
        
    Signals:
        frame_clicked: 点击帧时发出, 参数为 (x, y) 坐标
        zoom_changed: 缩放变化时发出, 参数为新的缩放因子
    """
    
    # 信号定义
    frame_clicked = Signal(int, int)  # 点击坐标
    zoom_changed = Signal(float)  # 缩放因子
    
    # 配色常量 (从设计文档)
    COLOR_BOX = QColor(0, 255, 0)  # 边界框颜色
    COLOR_TEXT = QColor(255, 255, 255)  # 文本颜色
    COLOR_TRAJECTORY = QColor(255, 0, 0)  # 轨迹颜色
    COLOR_CENTER_POINT = QColor(255, 255, 0)  # 中心点颜色
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化视频画布
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 内部状态
        self._current_frame: Optional[NDArray[np.uint8]] = None
        self._current_pixmap: Optional[QPixmap] = None
        self._overlay_data: dict = {}  # 叠加层数据
        
        # 缩放和平移状态
        self._zoom_factor: float = 1.0
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._last_mouse_pos: QPoint = QPoint()
        
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
        
        self._layout.addWidget(self._image_label)
    
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
    
    def set_frame(self, frame: NDArray[np.uint8], copy: bool = False) -> None:
        """设置当前显示的帧
        
        Args:
            frame: BGR 格式的图像数组 (H, W, C)
        """
        if frame is None or frame.size == 0:
            return
        
        self._current_frame = frame.copy() if copy else frame
        self._update_display()
    
    def set_overlay(
        self,
        detections: Optional[list] = None,
        trajectories: Optional[dict] = None,
        info_text: Optional[str] = None,
    ) -> None:
        """设置叠加层数据
        
        Args:
            detections: 检测结果列表, 每个元素包含 (track_id, x, y, w, h, confidence)
            trajectories: 轨迹数据字典, {track_id: [(x, y, timestamp), ...]}
            info_text: 左上角信息文本
        """
        self._overlay_data = {
            "detections": detections or [],
            "trajectories": trajectories or {},
            "info_text": info_text,
        }
        self._update_display()
    
    def clear(self) -> None:
        """清除画布"""
        self._current_frame = None
        self._current_pixmap = None
        self._overlay_data = {}
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
        """更新显示"""
        if self._current_frame is None:
            return
        
        # 绘制叠加层
        display_frame = self._draw_overlay(self._current_frame.copy())
        
        # 转换 BGR 到 RGB
        if display_frame.ndim == 3 and display_frame.shape[2] == 3:
            rgb_frame = np.ascontiguousarray(display_frame[:, :, ::-1])
        else:
            rgb_frame = display_frame
        
        # 创建 QImage
        h, w = rgb_frame.shape[:2]
        bytes_per_line = 3 * w
        q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # 计算缩放后的尺寸
        scaled_w = int(w * self._zoom_factor)
        scaled_h = int(h * self._zoom_factor)
        
        # 缩放图像
        if scaled_w > 0 and scaled_h > 0:
            scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                scaled_w, scaled_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation  # 性能优化：使用快速缩放
            )
            self._current_pixmap = scaled_pixmap
            self._image_label.setPixmap(scaled_pixmap)
            self._image_label.resize(scaled_pixmap.size())
        
        # 更新信息标签
        self._update_info_label()
    
    def _draw_overlay(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """绘制叠加层
        
        Args:
            frame: 原始帧
            
        Returns:
            绘制叠加层后的帧
        """
        import cv2
        
        detections = self._overlay_data.get("detections", [])
        trajectories = self._overlay_data.get("trajectories", {})
        
        # 绘制轨迹
        for track_id, points in trajectories.items():
            if len(points) >= 2:
                # 提取坐标
                pts = [(int(p[0]), int(p[1])) for p in points[-50:]]  # 最近50个点
                for i in range(1, len(pts)):
                    cv2.line(
                        frame, pts[i-1], pts[i],
                        (255, 0, 0),  # 蓝色 (BGR)
                        2,
                        cv2.LINE_AA
                    )
        
        # 绘制检测框
        for det in detections:
            if len(det) >= 6:
                track_id, x, y, w, h, confidence = det[:6]
                x, y, w, h = int(x), int(y), int(w), int(h)
                
                # 边界框
                cv2.rectangle(
                    frame,
                    (x, y), (x + w, y + h),
                    (0, 255, 0),  # 绿色
                    2
                )
                
                # ID 标签
                label = f"ID:{track_id} {confidence:.2f}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                
                # 计算文本大小
                (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # 绘制文本背景
                cv2.rectangle(
                    frame,
                    (x, y - text_h - 10),
                    (x + text_w + 10, y),
                    (0, 255, 0),
                    -1
                )
                
                # 绘制文本
                cv2.putText(
                    frame, label,
                    (x + 5, y - 5),
                    font, font_scale,
                    (255, 255, 255),
                    thickness,
                    cv2.LINE_AA
                )
                
                # 中心点
                center_x, center_y = x + w // 2, y + h // 2
                cv2.circle(frame, (center_x, center_y), 4, (255, 255, 0), -1)
        
        return frame
    
    def _update_info_label(self) -> None:
        """更新信息标签"""
        info_text = self._overlay_data.get("info_text", "")
        if info_text:
            self._info_label.setText(info_text)
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


# 用于测试和演示的 Mock 数据生成器
class MockFrameGenerator:
    """Mock 帧生成器
    
    用于在没有真实视频源时生成测试帧。
    """
    
    def __init__(self, width: int = 640, height: int = 480):
        """初始化
        
        Args:
            width: 帧宽度
            height: 帧高度
        """
        self.width = width
        self.height = height
        self._frame_count = 0
        self._targets = [
            {"id": 1, "x": 100, "y": 100, "vx": 3, "vy": 2},
            {"id": 2, "x": 400, "y": 200, "vx": -2, "vy": 1},
            {"id": 3, "x": 300, "y": 300, "vx": 1, "vy": -2},
        ]
    
    def generate(self) -> tuple[NDArray[np.uint8], list, dict, str]:
        """生成一帧
        
        Returns:
            (frame, detections, trajectories, info_text) 元组
        """
        import cv2
        
        # 创建渐变背景
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 绘制网格背景
        for i in range(0, self.width, 50):
            cv2.line(frame, (i, 0), (i, self.height), (40, 40, 40), 1)
        for i in range(0, self.height, 50):
            cv2.line(frame, (0, i), (self.width, i), (40, 40, 40), 1)
        
        # 更新目标位置并绘制
        detections = []
        trajectories = {}
        
        for target in self._targets:
            # 更新位置
            target["x"] += target["vx"]
            target["y"] += target["vy"]
            
            # 边界反弹
            if target["x"] < 50 or target["x"] > self.width - 50:
                target["vx"] *= -1
            if target["y"] < 50 or target["y"] > self.height - 50:
                target["vy"] *= -1
            
            # 确保在范围内
            target["x"] = max(50, min(self.width - 50, target["x"]))
            target["y"] = max(50, min(self.height - 50, target["y"]))
            
            # 生成检测结果
            w, h = 60, 80
            confidence = 0.85 + 0.1 * np.random.random()
            detections.append((
                target["id"],
                target["x"] - w // 2,
                target["y"] - h // 2,
                w, h, confidence
            ))
            
            # 绘制简单人形轮廓
            center = (int(target["x"]), int(target["y"]))
            cv2.circle(frame, center, 30, (60, 60, 100), -1)
            cv2.circle(frame, (center[0], center[1] - 40), 15, (70, 70, 100), -1)
        
        self._frame_count += 1
        
        # 生成轨迹数据 (模拟)
        for det in detections:
            track_id = det[0]
            if track_id not in trajectories:
                trajectories[track_id] = []
            trajectories[track_id].append((det[1] + det[3]//2, det[2] + det[4]//2, self._frame_count * 0.033))
        
        # 信息文本
        fps = 28.5 + np.random.random() * 3
        info_text = f"Frame: {self._frame_count} | FPS: {fps:.1f}\nPersons: {len(self._targets)}"
        
        return frame, detections, trajectories, info_text
