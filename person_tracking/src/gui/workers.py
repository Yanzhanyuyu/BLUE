"""GUI 工作线程模块

提供后台工作线程用于:
- 视频源读取 (VideoCapture Worker)
- 推理处理 (Inference Worker)

使用 Signal/Slot 机制与 GUI 线程安全通信。
"""

import time
import numpy as np
from numpy.typing import NDArray
from typing import Optional, Any
from dataclasses import dataclass

import cv2
from PySide6.QtCore import QThread, Signal, Slot

from ..infra.metrics import MetricsCollector, PerformanceSnapshot


@dataclass
class FrameData:
    """帧数据容器"""
    frame: NDArray[np.uint8]
    frame_id: int
    timestamp: float


@dataclass
class ProcessedData:
    """处理结果容器"""
    frame: NDArray[np.uint8]
    detections: list  # [(track_id, x, y, w, h, confidence), ...]
    trajectories: dict  # {track_id: [(x, y, timestamp), ...]}
    info_text: str
    frame_id: int


class VideoCaptureWorker(QThread):
    """视频捕获工作线程
    
    负责从视频文件、摄像头或 RTSP 流读取帧。
    使用 signal 与主线程通信，避免阻塞 GUI。
    
    Signals:
        frame_ready: 收到新帧时发出，参数为 FrameData
        error: 发生错误时发出，参数为错误消息
        finished: 线程结束时发出
    """
    
    frame_ready = Signal(object)  # FrameData
    error = Signal(str)
    finished = Signal()
    
    def __init__(
        self,
        source: str | int,
        target_fps: float = 30.0,
        parent: Optional[QThread] = None
    ) -> None:
        """初始化工作线程
        
        Args:
            source: 视频源 (文件路径、摄像头索引 "0"、RTSP URL)
            target_fps: 目标帧率，用于控制读取速度
            parent: 父线程
        """
        super().__init__(parent)
        self._source = source
        self._target_fps = target_fps
        self._frame_interval = 1.0 / target_fps if target_fps > 0 else 0
        
        self._capture: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._is_paused = False
        
        # 视频信息
        self._video_width = 0
        self._video_height = 0
        self._video_fps = 0.0
        self._total_frames = 0
        self._current_frame_pos = 0
        
    def run(self) -> None:
        """线程主循环"""
        self._is_running = True
        self._open_capture()
        
        if self._capture is None or not self._capture.isOpened():
            self.error.emit(f"无法打开视频源: {self._source}")
            self.finished.emit()
            return
        
        frame_id = 0
        last_time = time.time()
        
        while self._is_running:
            # 暂停时等待
            while self._is_paused and self._is_running:
                time.sleep(0.01)
            
            if not self._is_running:
                break
            
            # 控制帧率
            elapsed = time.time() - last_time
            if elapsed < self._frame_interval:
                time.sleep(self._frame_interval - elapsed)
            
            # 读取帧
            ret, frame = self._capture.read()
            
            if not ret:
                # 视频结束或读取失败
                if isinstance(self._source, str) and not self._source.startswith(('rtsp://', 'http://')):
                    # 本地视频文件结束后退出
                    break
                else:
                    # 实时流重试
                    time.sleep(0.1)
                    continue
            
            last_time = time.time()
            frame_id += 1
            self._current_frame_pos = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))
            
            # 发送帧数据到主线程
            frame_data = FrameData(
                frame=frame,
                frame_id=frame_id,
                timestamp=time.time()
            )
            self.frame_ready.emit(frame_data)
        
        self._release_capture()
        self.finished.emit()
    
    def _open_capture(self) -> None:
        """打开视频捕获"""
        # 解析 source
        if isinstance(self._source, str):
            if self._source.startswith('rtsp://') or self._source.startswith('http://'):
                # RTSP/Http 流
                self._capture = cv2.VideoCapture(self._source)
            elif self._source.startswith('camera:'):
                # 摄像头: camera:0
                idx = int(self._source.split(':')[1]) if ':' in self._source else 0
                self._capture = cv2.VideoCapture(idx)
            else:
                # 本地视频文件
                self._capture = cv2.VideoCapture(self._source)
        else:
            # 摄像头索引
            self._capture = cv2.VideoCapture(self._source)
        
        if self._capture and self._capture.isOpened():
            # 获取视频信息
            self._video_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._video_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._video_fps = self._capture.get(cv2.CAP_PROP_FPS)
            self._total_frames = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def _release_capture(self) -> None:
        """释放视频捕获资源"""
        if self._capture:
            self._capture.release()
            self._capture = None
    
    def stop(self) -> None:
        """停止线程"""
        self._is_running = False
        self._is_paused = False
    
    def pause(self) -> None:
        """暂停"""
        self._is_paused = True
    
    def resume(self) -> None:
        """恢复"""
        self._is_paused = False
    
    def seek(self, frame_position: int) -> bool:
        """跳转到指定帧位置 (仅对本地视频有效)
        
        Args:
            frame_position: 目标帧位置
            
        Returns:
            是否成功跳转
        """
        if self._capture and self._capture.isOpened() and self._total_frames > 0:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            self._current_frame_pos = frame_position
            return True
        return False
    
    @property
    def video_info(self) -> dict:
        """获取视频信息"""
        return {
            'width': self._video_width,
            'height': self._video_height,
            'fps': self._video_fps,
            'total_frames': self._total_frames,
            'current_frame': self._current_frame_pos,
            'is_local_video': self._total_frames > 0 and isinstance(self._source, str) and not self._source.startswith(('rtsp://', 'http://'))
        }


class InferenceWorker(QThread):
    """推理工作线程

    负责执行目标检测和跟踪推理。
    接收原始帧，输出带标注的帧和跟踪结果。

    Signals:
        result_ready: 推理完成时发出，参数为 ProcessedData
        error: 发生错误时发出
        finished: 线程结束时发出
    """

    result_ready = Signal(object)  # ProcessedData
    error = Signal(str)
    finished = Signal()
    metrics_updated = Signal(dict)  # 性能指标更新

    def __init__(
        self,
        config: Any = None,
        parent: Optional[QThread] = None
    ) -> None:
        """初始化推理工作线程

        Args:
            config: 配置对象
            parent: 父线程
        """
        super().__init__(parent)
        self._config = config
        self._pipeline = None

        # 控制标志
        self._is_running = False
        self._is_paused = False

        # 帧队列 (只保留最新帧)
        self._latest_frame: Optional[FrameData] = None
        self._frame_lock = None  # 简化处理：使用原子操作

        # 统一性能收集器（解决FPS多源计算问题）
        self._metrics_collector = MetricsCollector()

        # 跳帧设置
        self._skip_frames = 0
        self._frame_counter = 0

        # 配置参数 (运行时可更新)
        self._confidence_threshold = 0.5
        self._iou_threshold = 0.45
        self._show_trajectory = True
    
    def set_config(self, config: Any) -> None:
        """设置配置"""
        self._config = config
        if config:
            if hasattr(config, 'detector'):
                self._confidence_threshold = config.detector.confidence_threshold
                self._iou_threshold = config.detector.iou_threshold
            if hasattr(config, 'pipeline'):
                self._skip_frames = config.pipeline.skip_frames
    
    def set_skip_frames(self, skip: int) -> None:
        """设置跳帧数"""
        self._skip_frames = max(0, skip)
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """设置置信度阈值"""
        self._confidence_threshold = max(0.0, min(1.0, threshold))
    
    def set_show_trajectory(self, show: bool) -> None:
        """设置是否显示轨迹"""
        self._show_trajectory = show
    
    def set_pipeline(self, pipeline: Any) -> None:
        """设置处理管道"""
        self._pipeline = pipeline
    
    def submit_frame(self, frame_data: FrameData) -> None:
        """提交帧进行处理 (线程安全)
        
        Args:
            frame_data: 帧数据
        """
        self._latest_frame = frame_data
    
    def run(self) -> None:
        """线程主循环 - 修复跳帧连续性

        重构说明：
        - 跳过的帧使用上一帧渲染结果，保持视觉连续性
        - 只在 Pipeline 中渲染，Worker 不重复渲染
        """
        self._is_running = True
        self._metrics_collector.start()

        # 等待 pipeline 初始化
        while self._pipeline is None and self._is_running:
            time.sleep(0.1)

        if self._pipeline is None:
            self.error.emit("Pipeline 未初始化")
            self.finished.emit()
            return

        # 缓存上一帧的渲染结果和跟踪状态
        last_annotated_frame = None
        last_tracked_objects = []
        last_trajectories = {}

        while self._is_running:
            # 暂停时等待
            while self._is_paused and self._is_running:
                time.sleep(0.01)

            if not self._is_running:
                break

            # 获取最新帧
            frame_data = self._latest_frame
            if frame_data is None:
                time.sleep(0.001)
                continue

            # 跳帧逻辑 - 修复：保持视觉连续性
            self._frame_counter += 1
            should_process = (
                self._skip_frames == 0 or
                self._frame_counter % (self._skip_frames + 1) == 1 or
                self._frame_counter == 1  # 第一帧总是处理
            )

            try:
                start_time = time.time()

                if should_process:
                    # 正常处理帧（Pipeline统一渲染）
                    from ..data.types import Frame as DataFrame
                    data_frame = DataFrame(
                        frame_id=frame_data.frame_id,
                        timestamp=frame_data.timestamp,
                        image=frame_data.frame
                    )

                    # 执行推理（Pipeline统一渲染）
                    processed_frame, tracked_objects = self._pipeline.process_frame(
                        data_frame, enable_tracking=True, render=True
                    )

                    # 更新缓存
                    last_annotated_frame = processed_frame.image.copy()
                    last_tracked_objects = tracked_objects
                    if hasattr(self._pipeline, 'trajectory_manager'):
                        last_trajectories = self._pipeline.trajectory_manager.get_all_recent_points(50)

                    display_frame = last_annotated_frame

                else:
                    # 跳过的帧：使用缓存的渲染结果（关键修复）
                    if last_annotated_frame is not None:
                        display_frame = last_annotated_frame.copy()
                        tracked_objects = last_tracked_objects
                    else:
                        # 首次跳帧，无缓存，显示原始帧（降级处理）
                        display_frame = frame_data.frame.copy()
                        tracked_objects = []
                        last_trajectories = {}

                # 计算推理时间（仅处理过的帧）
                if should_process:
                    inference_time_ms = (time.time() - start_time) * 1000
                else:
                    inference_time_ms = 0  # 跳过的帧不计算推理时间

                # 使用统一的MetricsCollector报告帧数据
                self._metrics_collector.report_frame(
                    frame_id=frame_data.frame_id,
                    inference_time_ms=inference_time_ms,
                    detection_count=len(tracked_objects)
                )

                # 获取统一计算的性能指标
                metrics = self._metrics_collector.get_snapshot()

                # 准备检测结果
                detections = []
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

                # 获取轨迹 (使用公开方法)
                trajectories = {}
                if self._show_trajectory and hasattr(self._pipeline, 'trajectory_manager'):
                    trajectories = self._pipeline.trajectory_manager.get_all_recent_points(50)

                # 构建结果
                result = ProcessedData(
                    frame=display_frame,
                    detections=detections,
                    trajectories=trajectories,
                    info_text=f"Frame: {frame_data.frame_id} | Persons: {len(tracked_objects)}",
                    frame_id=frame_data.frame_id
                )

                # 发送结果
                self.result_ready.emit(result)

                # 发送性能指标（使用统一计算的值）
                self.metrics_updated.emit({
                    'fps': metrics.fps,
                    'inference_time': inference_time_ms,
                    'detection_count': len(tracked_objects),
                    'frame_count': metrics.frame_count
                })

            except Exception as e:
                self.error.emit(f"推理错误: {str(e)}")

        self._metrics_collector.stop()
        self.finished.emit()
    
    def stop(self) -> None:
        """停止线程"""
        self._is_running = False
        self._is_paused = False
    
    def pause(self) -> None:
        """暂停"""
        self._is_paused = True
    
    def resume(self) -> None:
        """恢复"""
        self._is_paused = False