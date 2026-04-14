"""轨迹管理测试

测试 TrajectoryManager 的功能。
"""

import pytest

from src.data.trajectory import TrajectoryManager
from src.data.types import TrackedObject, Detection, BoundingBox


class TestTrajectoryManager:
    """轨迹管理器测试"""

    def test_manager_creation(self):
        """测试管理器创建"""
        manager = TrajectoryManager(
            max_trajectory_length=100,
            inactive_threshold=30,
        )
        assert len(manager) == 0

    def test_manager_update(self, sample_detection):
        """测试轨迹更新"""
        manager = TrajectoryManager()
        tracked_obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        manager.update(tracked_obj)
        assert len(manager) == 1
        assert 1 in manager

    def test_manager_get_trajectory(self, sample_detection):
        """测试获取轨迹"""
        manager = TrajectoryManager()
        tracked_obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        manager.update(tracked_obj)
        trajectory = manager.get_trajectory(1)
        assert trajectory is not None
        assert trajectory.track_id == 1
        assert len(trajectory.points) == 1

    def test_manager_cleanup_inactive(self, sample_detection):
        """测试清理失效轨迹"""
        manager = TrajectoryManager(inactive_threshold=5)

        # 添加轨迹
        tracked_obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        manager.update(tracked_obj)
        assert len(manager) == 1

        # 模拟时间流逝
        cleaned = manager.cleanup_inactive(10)
        assert cleaned == 1
        assert len(manager) == 0

    def test_manager_get_active_ids(self, sample_detection):
        """测试获取活跃 ID"""
        manager = TrajectoryManager(inactive_threshold=10)

        # 添加多个轨迹
        for i in range(3):
            bbox = BoundingBox(x=100 + i * 50, y=100, w=50, h=80, confidence=0.9)
            detection = Detection(bbox=bbox, class_id=0, class_name="person")
            tracked_obj = TrackedObject(
                track_id=i,
                detection=detection,
                frame_id=0,
                timestamp=0.0,
            )
            manager.update(tracked_obj)

        # 只有前两个在活跃范围内
        manager.cleanup_inactive(5)
        active_ids = manager.get_active_track_ids()
        assert len(active_ids) == 3

    def test_manager_statistics(self, sample_detection):
        """测试统计信息"""
        manager = TrajectoryManager()

        # 添加轨迹
        for i in range(3):
            bbox = BoundingBox(x=100 + i * 50, y=100, w=50, h=80, confidence=0.9)
            detection = Detection(bbox=bbox, class_id=0, class_name="person")
            tracked_obj = TrackedObject(
                track_id=i,
                detection=detection,
                frame_id=i,
                timestamp=i * 0.033,
            )
            manager.update(tracked_obj)

        stats = manager.get_statistics()
        assert stats["total_trajectories"] == 3
        assert stats["total_points"] == 3

    def test_manager_clear(self, sample_detection):
        """测试清空轨迹"""
        manager = TrajectoryManager()
        tracked_obj = TrackedObject(
            track_id=1,
            detection=sample_detection,
            frame_id=0,
            timestamp=0.0,
        )
        manager.update(tracked_obj)
        assert len(manager) == 1
        manager.clear()
        assert len(manager) == 0

    def test_manager_get_all_recent_points(self, sample_detection):
        """测试获取所有轨迹的最近 N 个点"""
        manager = TrajectoryManager(max_trajectory_length=100)
        
        # 添加多个轨迹
        for i in range(3):
            bbox = BoundingBox(x=100 + i * 50, y=100, w=50, h=80, confidence=0.9)
            detection = Detection(bbox=bbox, class_id=0, class_name="person")
            for frame_id in range(5):
                tracked_obj = TrackedObject(
                    track_id=i,
                    detection=detection,
                    frame_id=frame_id,
                    timestamp=frame_id * 0.033,
                )
                manager.update(tracked_obj)
        
        # 测试获取最近 3 个点
        recent_points = manager.get_all_recent_points(n=3)
        assert len(recent_points) == 3
        for track_id in range(3):
            assert track_id in recent_points
            assert len(recent_points[track_id]) == 3

    def test_manager_get_all_recent_points_empty(self):
        """测试空轨迹管理器的 get_all_recent_points"""
        manager = TrajectoryManager()
        recent_points = manager.get_all_recent_points()
        assert recent_points == {}
