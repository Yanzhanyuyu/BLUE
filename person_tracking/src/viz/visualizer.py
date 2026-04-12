"""可视化模块

提供检测结果的渲染和可视化，支持：
- 边界框绘制
- track_id 标签显示
- 轨迹线绘制
- 中心点标记
- 置信度显示
"""

from typing import Optional
import cv2
import numpy as np
from numpy.typing import NDArray

from ..infra.config import VisualizerConfig
from ..data.types import TrackedObject, Trajectory
from ..infra.logger import get_logger

logger = get_logger("visualizer")


class Visualizer:
    """可视化渲染器

    渲染检测结果到帧上，包括边界框、标签、轨迹等。

    Attributes:
        config: 可视化配置

    Example:
        >>> config = VisualizerConfig(box_color=(0, 255, 0), trajectory_length=50)
        >>> viz = Visualizer(config)
        >>> annotated_frame = viz.render(frame, tracked_objects, trajectories)
    """

    def __init__(self, config: VisualizerConfig) -> None:
        """初始化可视化渲染器

        Args:
            config: 可视化配置
        """
        self.config = config
        self._color_map = {}  # track_id -> color 缓存

        logger.debug(
            f"Visualizer initialized: box_color={config.box_color}, "
            f"trajectory_length={config.trajectory_length}"
        )

    def render(
        self,
        frame: NDArray[np.uint8],
        tracked_objects: list[TrackedObject],
        trajectories: dict[int, Trajectory],
    ) -> NDArray[np.uint8]:
        """渲染检测结果

        在帧上绘制边界框、ID标签、轨迹、中心点等。

        Args:
            frame: 原始帧图像（BGR 格式）
            tracked_objects: 当前帧的跟踪对象列表
            trajectories: 轨迹历史字典 {track_id: Trajectory}

        Returns:
            渲染后的帧图像

        Example:
            >>> annotated = viz.render(frame, tracked_objects, trajectories)
            >>> cv2.imshow("Tracking", annotated)
        """
        # 复制帧，避免修改原图
        annotated = frame.copy()

        # 绘制轨迹（先绘制，避免遮挡边界框）
        if self.config.trajectory_length > 0:
            annotated = self._draw_trajectories(annotated, trajectories)

        # 绘制边界框和标签
        for obj in tracked_objects:
            annotated = self._draw_bbox(annotated, obj)

        return annotated

    def _draw_bbox(
        self,
        frame: NDArray[np.uint8],
        tracked_obj: TrackedObject,
    ) -> NDArray[np.uint8]:
        """绘制单个边界框

        Args:
            frame: 帧图像
            tracked_obj: 跟踪对象

        Returns:
            渲染后的帧
        """
        bbox = tracked_obj.bbox
        track_id = tracked_obj.track_id

        # 获取颜色（每个 track_id 使用不同颜色）
        color = self._get_color(track_id)

        # 边界框坐标
        x1, y1 = int(bbox.x), int(bbox.y)
        x2, y2 = int(bbox.x + bbox.w), int(bbox.y + bbox.h)

        # 绘制边界框
        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            self.config.line_thickness,
        )

        # 绘制中心点
        if self.config.show_center_point:
            center = bbox.center
            cv2.circle(
                frame,
                (int(center[0]), int(center[1])),
                radius=4,
                color=color,
                thickness=-1,  # 填充
            )

        # 绘制标签
        label = f"ID:{track_id}"
        if self.config.show_confidence:
            label += f" {tracked_obj.confidence:.2f}"

        # 标签背景
        (label_w, label_h), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            self.config.font_scale,
            1,
        )

        cv2.rectangle(
            frame,
            (x1, y1 - label_h - baseline - 5),
            (x1 + label_w, y1),
            color,
            -1,  # 填充
        )

        # 标签文本
        cv2.putText(
            frame,
            label,
            (x1, y1 - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.config.font_scale,
            self.config.text_color,
            1,
            cv2.LINE_AA,
        )

        return frame

    def _draw_trajectories(
        self,
        frame: NDArray[np.uint8],
        trajectories: dict[int, Trajectory],
    ) -> NDArray[np.uint8]:
        """绘制轨迹

        Args:
            frame: 帧图像
            trajectories: 轨迹字典

        Returns:
            渲染后的帧
        """
        for track_id, trajectory in trajectories.items():
            # 获取最近 N 个轨迹点
            points = trajectory.get_recent_points(self.config.trajectory_length)

            if len(points) < 2:
                continue

            # 获取颜色
            color = self._get_color(track_id)

            # 绘制轨迹线
            for i in range(1, len(points)):
                x1, y1, _ = points[i - 1]
                x2, y2, _ = points[i]

                # 渐变透明度（越新的点越不透明）
                alpha = i / len(points)
                thickness = max(1, int(self.config.line_thickness * alpha))

                cv2.line(
                    frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    color,
                    thickness,
                    cv2.LINE_AA,
                )

        return frame

    def _get_color(self, track_id: int) -> tuple[int, int, int]:
        """获取 track_id 对应的颜色

        每个 track_id 使用不同颜色，便于区分。

        Args:
            track_id: 跟踪 ID

        Returns:
            BGR 颜色元组
        """
        if track_id not in self._color_map:
            # 生成随机颜色（基于 track_id）
            np.random.seed(track_id % 1000)
            color = tuple(
                np.random.randint(50, 256, size=3).tolist()
            )
            self._color_map[track_id] = color

        return self._color_map[track_id]

    def draw_info(
        self,
        frame: NDArray[np.uint8],
        frame_id: int,
        fps: float = 0.0,
        person_count: int = 0,
    ) -> NDArray[np.uint8]:
        """绘制帧信息

        在帧上显示帧号、FPS、人数等信息。

        Args:
            frame: 帧图像
            frame_id: 帧编号
            fps: 当前 FPS
            person_count: 检测到的人数

        Returns:
            渲染后的帧
        """
        # 帧信息文本
        info_text = f"Frame: {frame_id}"
        if fps > 0:
            info_text += f" | FPS: {fps:.1f}"
        info_text += f" | Persons: {person_count}"

        # 绘制信息栏背景
        (text_w, text_h), baseline = cv2.getTextSize(
            info_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            1,
        )

        cv2.rectangle(
            frame,
            (0, 0),
            (text_w + 10, text_h + baseline + 10),
            (0, 0, 0),
            -1,
        )

        # 绘制文本
        cv2.putText(
            frame,
            info_text,
            (5, text_h + baseline + 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        return frame

    def clear_color_cache(self) -> None:
        """清除颜色缓存"""
        self._color_map.clear()
        logger.debug("Color cache cleared")
