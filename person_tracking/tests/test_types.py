"""数据类型测试

测试核心数据类的基本功能。
"""

import pytest
import numpy as np

from src.data.types import (
    BoundingBox,
    Detection,
    TrackedObject,
    Frame,
    Trajectory,
    PerformanceMetrics,
)


class TestBoundingBox:
    """边界框测试"""

    def test_bbox_creation(self):
        """测试边界框创建"""
        bbox = BoundingBox(x=100, y=100, w=50, h=80, confidence=0.95)
        assert bbox.x == 100
        assert bbox.y == 100
        assert bbox.w == 50
        assert bbox.h == 80
        assert bbox.confidence == 0.95

    def test_bbox_center(self):
        """测试中心点计算"""
        bbox = BoundingBox(x=100, y=100, w=50, h=80)
        center = bbox.center
        assert center == (125.0, 140.0)

    def test_bbox_area(self):
        """测试面积计算"""
        bbox = BoundingBox(x=0, y=0, w=10, h=20)
        assert bbox.area == 200

    def test_bbox_to_xyxy(self):
        """测试 xyxy 格式转换"""
        bbox = BoundingBox(x=100, y=100, w=50, h=80)
        x1, y1, x2, y2 = bbox.to_xyxy()
        assert (x1, y1, x2, y2) == (100.0, 100.0, 150.0, 180.0)

    def test_bbox_from_xyxy(self):
        """测试从 xyxy 创建"""
        bbox = BoundingBox.from_xyxy(100, 100, 150, 180, confidence=0.95)
        assert bbox.x == 100
        assert bbox.y == 100
        assert bbox.w == 50
        assert bbox.h == 80

    def test_bbox_iou(self):
        """测试 IOU 计算"""
        bbox1 = BoundingBox.from_xyxy(0, 0, 100, 100)
        bbox2 = BoundingBox.from_xyxy(50, 50, 150, 150)
        iou = bbox1.iou(bbox2)
        # 交集: 50x50 = 2500
        # 并集: 10000 + 10000 - 2500 = 17500
        # IOU = 2500 / 17500 ≈ 0.143
        assert 0.14 < iou < 0.15

    def test_bbox_iou_no_overlap(self):
        """测试无重叠时的 IOU"""
        bbox1 = BoundingBox(x=0, y=0, w=10, h=10)
        bbox2 = BoundingBox(x=100, y=100, w=10, h=10)
        assert bbox1.iou(bbox2) == 0.0


class TestDetection:
    """检测结果测试"""

    def test_detection_creation(self, sample_bbox):
        """测试检测结果创建"""
        detection = Detection(
            bbox=sample_bbox,
            class_id=0,
            class_name="person",
        )
        assert detection.class_id == 0
        assert detection.class_name == "person"
        assert detection.confidence == 0.95
        assert detection.track_id is None

    def test_detection_assign_track_id(self, sample_bbox):
        """测试分配跟踪 ID"""
        detection = Detection(
            bbox=sample_bbox,
            class_id=0,
            class_name="person",
        )
        detection_with_id = detection.assign_track_id(1)
        assert detection_with_id.track_id == 1


class TestTrackedObject:
    """跟踪对象测试"""

    def test_tracked_object_creation(self, sample_detection):
        """测试跟踪对象创建"""
        obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        assert obj.track_id == 1
        assert obj.frame_id == 0
        assert obj.confidence == 0.95

    def test_tracked_object_center(self, sample_detection):
        """测试中心点访问"""
        obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        center = obj.center
        assert center == (125.0, 140.0)


class TestFrame:
    """帧数据测试"""

    def test_frame_creation(self, sample_image):
        """测试帧创建"""
        frame = Frame(
            frame_id=0,
            timestamp=0.0,
            image=sample_image,
        )
        assert frame.frame_id == 0
        assert frame.height == 480
        assert frame.width == 640

    def test_frame_add_detection(self, sample_image, sample_detection):
        """测试添加检测结果"""
        frame = Frame(
            frame_id=0,
            timestamp=0.0,
            image=sample_image,
        )
        frame.add_detection(sample_detection)
        assert len(frame.detections) == 1


class TestTrajectory:
    """轨迹测试"""

    def test_trajectory_creation(self):
        """测试轨迹创建"""
        trajectory = Trajectory(track_id=1)
        assert trajectory.track_id == 1
        assert len(trajectory.points) == 0

    def test_trajectory_add_point(self):
        """测试添加轨迹点"""
        trajectory = Trajectory(track_id=1)
        trajectory.add_point(100, 100, 0.0)
        trajectory.add_point(110, 105, 0.033)
        assert len(trajectory.points) == 2
        assert trajectory.last_point == (110, 105, 0.033)

    def test_trajectory_max_length(self):
        """测试轨迹长度限制"""
        trajectory = Trajectory(track_id=1, max_length=5)
        for i in range(10):
            trajectory.add_point(i, i, i * 0.033)
        assert len(trajectory.points) == 5
        # 保留最后5个点
        assert trajectory.points[0] == (5, 5, 0.165)

    def test_trajectory_get_recent_points(self):
        """测试获取最近点"""
        trajectory = Trajectory(track_id=1)
        for i in range(10):
            trajectory.add_point(i, i, i * 0.033)
        recent = trajectory.get_recent_points(3)
        assert len(recent) == 3
        # 浮点数比较使用近似值
        assert abs(recent[-1][2] - 0.297) < 0.001

    def test_trajectory_duration(self):
        """测试轨迹持续时间"""
        trajectory = Trajectory(track_id=1)
        trajectory.add_point(0, 0, 0.0)
        trajectory.add_point(100, 100, 1.0)
        assert trajectory.duration == 1.0


class TestPerformanceMetrics:
    """性能指标测试"""

    def test_metrics_creation(self):
        """测试性能指标创建"""
        metrics = PerformanceMetrics()
        assert metrics.fps == 0.0
        assert metrics.total_frames == 0

    def test_metrics_update_fps(self):
        """测试 FPS 更新"""
        metrics = PerformanceMetrics()
        metrics.update_fps(30.0)
        assert metrics.fps == 30.0
        # 移动平均
        metrics.update_fps(30.0)
        assert 29 < metrics.fps < 31
