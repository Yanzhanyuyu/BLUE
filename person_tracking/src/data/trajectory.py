"""轨迹管理模块

管理所有跟踪对象的轨迹历史，支持：
- 轨迹点添加和更新
- 轨迹历史查询
- 失效轨迹清理
- 轨迹统计分析
"""

from typing import Optional
from collections import defaultdict

from .types import Trajectory, TrackedObject
from ..infra.logger import get_logger

logger = get_logger("trajectory")


class TrajectoryManager:
    """轨迹管理器

    管理所有跟踪对象的轨迹历史记录。

    Attributes:
        trajectories: 轨迹字典 {track_id: Trajectory}
        max_trajectory_length: 单个轨迹最大长度
        inactive_threshold: 失效阈值（帧数）

    Example:
        >>> manager = TrajectoryManager(max_length=100)
        >>> # 添加轨迹点
        >>> manager.update(tracked_obj)
        >>> # 获取轨迹
        >>> trajectory = manager.get_trajectory(track_id=1)
        >>> # 获取最近50个点
        >>> points = manager.get_recent_points(track_id=1, n=50)
    """

    def __init__(
        self,
        max_trajectory_length: int = 100,
        inactive_threshold: int = 30,
    ) -> None:
        """初始化轨迹管理器

        Args:
            max_trajectory_length: 单个轨迹最大长度（防止内存泄漏）
            inactive_threshold: 失效阈值（连续N帧未更新视为失效）
        """
        self.max_trajectory_length = max_trajectory_length
        self.inactive_threshold = inactive_threshold
        self._trajectories: dict[int, Trajectory] = {}
        self._last_update_frame: dict[int, int] = {}
        self._current_frame_id: int = 0

        logger.debug(
            f"TrajectoryManager initialized: max_length={max_trajectory_length}, "
            f"inactive_threshold={inactive_threshold}"
        )

    def update(self, tracked_obj: TrackedObject) -> None:
        """更新轨迹

        根据跟踪对象更新对应的轨迹历史。

        Args:
            tracked_obj: 跟踪对象
        """
        track_id = tracked_obj.track_id
        center = tracked_obj.center
        timestamp = tracked_obj.timestamp

        # 获取或创建轨迹
        if track_id not in self._trajectories:
            self._trajectories[track_id] = Trajectory(
                track_id=track_id,
                max_length=self.max_trajectory_length,
            )
            logger.debug(f"New trajectory created: track_id={track_id}")

        # 添加轨迹点
        self._trajectories[track_id].add_point(
            x=center[0],
            y=center[1],
            timestamp=timestamp,
        )

        # 更新最后更新帧
        self._last_update_frame[track_id] = tracked_obj.frame_id

    def update_batch(self, tracked_objects: list[TrackedObject]) -> None:
        """批量更新轨迹

        Args:
            tracked_objects: 跟踪对象列表
        """
        for obj in tracked_objects:
            self.update(obj)

    def get_trajectory(self, track_id: int) -> Optional[Trajectory]:
        """获取指定 track_id 的轨迹

        Args:
            track_id: 跟踪 ID

        Returns:
            Trajectory 对象，如果不存在返回 None
        """
        return self._trajectories.get(track_id)

    def get_all_trajectories(self) -> dict[int, Trajectory]:
        """获取所有轨迹

        Returns:
            轨迹字典 {track_id: Trajectory}
        """
        return self._trajectories.copy()

    def get_recent_points(
        self,
        track_id: int,
        n: int = 50,
    ) -> list[tuple[float, float, float]]:
        """获取指定轨迹的最近 N 个点

        Args:
            track_id: 跟踪 ID
            n: 点数量

        Returns:
            轨迹点列表 [(x, y, timestamp), ...]
        """
        trajectory = self._trajectories.get(track_id)
        if trajectory is None:
            return []
        return trajectory.get_recent_points(n)

    def get_active_track_ids(self) -> list[int]:
        """获取所有活跃的 track_id

        活跃定义为：最近 inactive_threshold 帧内有过更新。

        Returns:
            活跃的 track_id 列表
        """
        active_ids = []
        min_frame = self._current_frame_id - self.inactive_threshold

        for track_id, last_frame in self._last_update_frame.items():
            if last_frame >= min_frame:
                active_ids.append(track_id)

        return active_ids

    def cleanup_inactive(self, current_frame_id: int) -> int:
        """清理失效轨迹

        移除超过 inactive_threshold 帧未更新的轨迹。

        Args:
            current_frame_id: 当前帧 ID

        Returns:
            清理的轨迹数量
        """
        self._current_frame_id = current_frame_id
        min_frame = current_frame_id - self.inactive_threshold

        # 找出失效的 track_id
        inactive_ids = [
            track_id
            for track_id, last_frame in self._last_update_frame.items()
            if last_frame < min_frame
        ]

        # 清理失效轨迹
        for track_id in inactive_ids:
            self._trajectories.pop(track_id, None)
            self._last_update_frame.pop(track_id, None)

        if inactive_ids:
            logger.debug(
                f"Cleaned up {len(inactive_ids)} inactive trajectories: {inactive_ids}"
            )

        return len(inactive_ids)

    def clear(self) -> None:
        """清空所有轨迹"""
        self._trajectories.clear()
        self._last_update_frame.clear()
        self._current_frame_id = 0
        logger.debug("All trajectories cleared")

    def get_statistics(self) -> dict:
        """获取轨迹统计信息

        Returns:
            统计信息字典

        Example:
            >>> stats = manager.get_statistics()
            >>> print(stats)
            {
                'total_trajectories': 10,
                'active_trajectories': 5,
                'total_points': 500,
                'avg_trajectory_length': 50.0
            }
        """
        total_trajectories = len(self._trajectories)
        active_trajectories = len(self.get_active_track_ids())
        total_points = sum(len(t.points) for t in self._trajectories.values())
        avg_length = total_points / total_trajectories if total_trajectories > 0 else 0.0

        return {
            "total_trajectories": total_trajectories,
            "active_trajectories": active_trajectories,
            "total_points": total_points,
            "avg_trajectory_length": avg_length,
        }

    def __len__(self) -> int:
        """获取轨迹数量"""
        return len(self._trajectories)

    def __contains__(self, track_id: int) -> bool:
        """检查轨迹是否存在"""
        return track_id in self._trajectories

    def __iter__(self):
        """迭代所有轨迹"""
        return iter(self._trajectories.items())
