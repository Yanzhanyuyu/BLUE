"""性能指标收集模块

提供统一的性能指标计算和收集，支持多源数据汇总。
用于解决GUI层帧率显示与实际推理结果不匹配的问题。
"""

import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field
from collections import deque


@dataclass
class FrameMetrics:
    """单帧性能指标"""
    frame_id: int
    timestamp: float
    inference_time_ms: float = 0.0
    detection_count: int = 0


@dataclass
class PerformanceSnapshot:
    """性能指标快照"""
    fps: float = 0.0
    inference_time_ms: float = 0.0
    detection_count: int = 0
    frame_count: int = 0
    elapsed_time: float = 0.0


class MetricsCollector:
    """性能指标收集器
    
    统一的性能指标计算中心，解决多源FPS计算不一致问题。
    
    Usage:
        collector = MetricsCollector(window_size=30)
        
        # Worker中报告
        collector.report_frame(frame_id, inference_time, detection_count)
        
        # UI中定期获取
        metrics = collector.get_snapshot()
        print(f"FPS: {metrics.fps:.1f}")
    """
    
    def __init__(self, window_size: int = 30) -> None:
        """初始化
        
        Args:
            window_size: 滑动窗口大小，用于计算平均FPS
        """
        self._window_size = window_size
        self._lock = threading.Lock()
        
        # 帧历史记录（滑动窗口）
        self._frame_history: deque[FrameMetrics] = deque(maxlen=window_size)
        
        # 总统计
        self._total_frames = 0
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        
        # 回调
        self._listeners: list[Callable[[PerformanceSnapshot], None]] = []
    
    def start(self) -> None:
        """开始收集"""
        with self._lock:
            self._start_time = time.time()
            self._last_update_time = self._start_time
            self._total_frames = 0
            self._frame_history.clear()
    
    def stop(self) -> None:
        """停止收集"""
        with self._lock:
            self._start_time = None
    
    def report_frame(
        self,
        frame_id: int,
        inference_time_ms: float = 0.0,
        detection_count: int = 0
    ) -> None:
        """报告一帧的处理结果
        
        Args:
            frame_id: 帧编号
            inference_time_ms: 推理耗时（毫秒）
            detection_count: 检测到的目标数量
        """
        now = time.time()
        
        with self._lock:
            if self._start_time is None:
                self._start_time = now
                self._last_update_time = now
            
            metrics = FrameMetrics(
                frame_id=frame_id,
                timestamp=now,
                inference_time_ms=inference_time_ms,
                detection_count=detection_count
            )
            
            self._frame_history.append(metrics)
            self._total_frames += 1
            self._last_update_time = now
            
            # 触发回调
            snapshot = self._calculate_snapshot_unlocked()
        
        # 在锁外触发回调，避免死锁
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception:
                pass
    
    def get_snapshot(self) -> PerformanceSnapshot:
        """获取当前性能指标快照
        
        Returns:
            PerformanceSnapshot对象
        """
        with self._lock:
            return self._calculate_snapshot_unlocked()
    
    def _calculate_snapshot_unlocked(self) -> PerformanceSnapshot:
        """计算快照（内部使用，不持有锁）"""
        if not self._frame_history or self._start_time is None:
            return PerformanceSnapshot()
        
        # 计算FPS
        if len(self._frame_history) >= 2:
            time_span = self._frame_history[-1].timestamp - self._frame_history[0].timestamp
            if time_span > 0:
                fps = (len(self._frame_history) - 1) / time_span
            else:
                fps = 0.0
        else:
            fps = 0.0
        
        # 计算平均推理时间
        if self._frame_history:
            avg_inference = sum(m.inference_time_ms for m in self._frame_history) / len(self._frame_history)
        else:
            avg_inference = 0.0
        
        # 获取最新检测数
        detection_count = self._frame_history[-1].detection_count if self._frame_history else 0
        
        # 计算总耗时
        elapsed = self._last_update_time - self._start_time if self._last_update_time else 0
        
        return PerformanceSnapshot(
            fps=fps,
            inference_time_ms=avg_inference,
            detection_count=detection_count,
            frame_count=self._total_frames,
            elapsed_time=elapsed
        )
    
    def add_listener(self, callback: Callable[[PerformanceSnapshot], None]) -> None:
        """添加指标更新监听器
        
        Args:
            callback: 回调函数，接收PerformanceSnapshot
        """
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[PerformanceSnapshot], None]) -> None:
        """移除监听器
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._frame_history.clear()
            self._total_frames = 0
            self._start_time = None
            self._last_update_time = None
    
    @property
    def is_active(self) -> bool:
        """是否正在收集"""
        return self._start_time is not None
    
    @property
    def total_frames(self) -> int:
        """总帧数"""
        return self._total_frames


# 全局单例，用于跨组件共享
_global_collector: Optional[MetricsCollector] = None
_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """获取全局MetricsCollector实例
    
    Returns:
        MetricsCollector单例
    """
    global _global_collector
    if _global_collector is None:
        with _lock:
            if _global_collector is None:
                _global_collector = MetricsCollector()
    return _global_collector


def reset_metrics_collector() -> None:
    """重置全局收集器"""
    global _global_collector
    with _lock:
        if _global_collector:
            _global_collector.reset()
        _global_collector = None
