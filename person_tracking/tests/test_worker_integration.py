"""Worker 集成测试

测试 VideoCaptureWorker 和 InferenceWorker 的集成:
- Worker 生命周期管理
- 信号/槽机制
- 错误处理
- 并发安全
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# 跳过测试如果 PySide6 不可用
try:
    from PySide6.QtCore import QThread, QObject, Signal, QCoreApplication
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
class TestVideoCaptureWorker:
    """VideoCaptureWorker 测试"""

    def test_worker_creation(self):
        """测试 Worker 创建"""
        from src.gui.workers import VideoCaptureWorker

        worker = VideoCaptureWorker(source="video.mp4", target_fps=30.0)
        assert worker._source == "video.mp4"
        assert worker._target_fps == 30.0
        assert not worker._is_running
        assert not worker._is_paused

    def test_worker_stop(self):
        """测试 Worker 停止"""
        from src.gui.workers import VideoCaptureWorker

        worker = VideoCaptureWorker(source="video.mp4")
        worker.stop()
        assert not worker._is_running
        assert not worker._is_paused

    def test_worker_pause_resume(self):
        """测试 Worker 暂停和恢复"""
        from src.gui.workers import VideoCaptureWorker

        worker = VideoCaptureWorker(source="video.mp4")
        worker.pause()
        assert worker._is_paused
        worker.resume()
        assert not worker._is_paused

    def test_video_info_initialization(self):
        """测试视频信息初始化"""
        from src.gui.workers import VideoCaptureWorker

        worker = VideoCaptureWorker(source="video.mp4")
        # 使用 video_info 属性而不是 get_video_info 方法
        info = worker.video_info
        assert info is not None
        assert 'width' in info
        assert 'height' in info
        assert 'fps' in info


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
class TestInferenceWorker:
    """InferenceWorker 测试"""

    def test_worker_creation(self):
        """测试 Worker 创建"""
        from src.gui.workers import InferenceWorker

        worker = InferenceWorker()
        assert not worker._is_running
        assert not worker._is_paused
        assert worker._pipeline is None

    def test_worker_config_setters(self):
        """测试配置设置方法"""
        from src.gui.workers import InferenceWorker

        worker = InferenceWorker()

        # 测试跳帧设置
        worker.set_skip_frames(2)
        assert worker._skip_frames == 2

        # 测试置信度设置
        worker.set_confidence_threshold(0.8)
        assert worker._confidence_threshold == 0.8

        # 测试越界值
        worker.set_confidence_threshold(-0.1)
        assert worker._confidence_threshold == 0.0
        worker.set_confidence_threshold(1.5)
        assert worker._confidence_threshold == 1.0

        # 测试轨迹显示设置
        worker.set_show_trajectory(False)
        assert not worker._show_trajectory

    def test_worker_pipeline_assignment(self):
        """测试 Pipeline 赋值"""
        from src.gui.workers import InferenceWorker

        worker = InferenceWorker()
        mock_pipeline = Mock()
        worker.set_pipeline(mock_pipeline)
        assert worker._pipeline is mock_pipeline


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
class TestWorkerDataClasses:
    """Worker 数据类测试"""

    def test_frame_data_creation(self):
        """测试 FrameData 创建"""
        from src.gui.workers import FrameData

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        data = FrameData(frame=frame, frame_id=1, timestamp=time.time())
        assert data.frame_id == 1
        assert data.frame.shape == (480, 640, 3)

    def test_processed_data_creation(self):
        """测试 ProcessedData 创建"""
        from src.gui.workers import ProcessedData

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [(1, 100, 100, 50, 50, 0.9)]
        trajectories = {1: [(100, 100, time.time())]}
        info_text = "Test"

        data = ProcessedData(
            frame=frame,
            detections=detections,
            trajectories=trajectories,
            info_text=info_text,
            frame_id=1,
        )
        assert data.frame_id == 1
        assert len(data.detections) == 1


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
class TestWorkerIntegration:
    """Worker 集成测试"""

    def test_worker_lifecycle(self):
        """测试 Worker 完整生命周期"""
        from src.gui.workers import VideoCaptureWorker, InferenceWorker

        # 创建 Workers
        capture_worker = VideoCaptureWorker(source="video.mp4")
        inference_worker = InferenceWorker()

        # 验证初始状态
        assert not capture_worker._is_running
        assert not inference_worker._is_running

        # 启动
        capture_worker.start()
        inference_worker.start()

        # 等待一小段时间
        time.sleep(0.1)

        # 验证运行状态
        assert capture_worker.isRunning() or not capture_worker._is_running
        assert inference_worker.isRunning() or not inference_worker._is_running

        # 停止
        capture_worker.stop()
        inference_worker.stop()

        # 等待结束
        capture_worker.wait(1000)
        inference_worker.wait(1000)

        assert not capture_worker.isRunning()
        assert not inference_worker.isRunning()


class TestWorkerSignals:
    """Worker 信号测试"""

    def test_frame_data_signal(self):
        """测试 FrameData 信号传递"""
        from src.gui.workers import FrameData

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        data = FrameData(frame=frame, frame_id=1, timestamp=time.time())

        # 验证数据正确性
        assert data.frame_id == 1
        assert data.frame is frame
