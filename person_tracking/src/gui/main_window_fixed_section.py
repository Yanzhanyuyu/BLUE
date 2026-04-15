# -*- coding: utf-8 -*-
"""Fix the _update_camera_frame method indentation"""

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function and replace it with fixed version
import re

# The problematic section pattern
old_section = '''    @Slot()
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

                # 从 trajectory_manager 获取轨迹 (使用公开方法)
                if hasattr(self._pipeline, 'trajectory_manager'):
                    trajectories = self._pipeline.trajectory_manager.get_all_recent_points(50)

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
                self._video_canvas.set_info_text(info_text)

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

    @Slot()
    def _on_config_value_changed(self) -> None:'''

new_section = '''    @Slot()
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

                # 从 trajectory_manager 获取轨迹 (使用公开方法)
                if hasattr(self._pipeline, 'trajectory_manager'):
                    trajectories = self._pipeline.trajectory_manager.get_all_recent_points(50)

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
                self._video_canvas.set_info_text(info_text)

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

    @Slot()
    def _on_config_value_changed(self) -> None:'''

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found - checking content...")
    # Print around _update_camera_frame
    idx = content.find('def _update_camera_frame')
    if idx >= 0:
        print(repr(content[idx:idx+500]))
