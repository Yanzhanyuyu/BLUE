"""MainWindow 真实运行路径测试。

覆盖场景：
1. 摄像头预览路径不会在 GUI 线程执行推理。
2. 启动 worker 模式前会停止摄像头预览路径，避免双路径并发。
3. MainWindow 导出链可导出 tracks.csv / trajectory_stats.json。
4. GUI 参数修改后至少一个真实参数立即影响 pipeline 配置。
"""

import os
import json
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

if PYSIDE6_AVAILABLE:
    from src.gui.main_window import MainWindow
    from src.infra.config import Config


class DummySignal:
    def connect(self, _slot):
        return None


class DummyCapture:
    def __init__(self):
        self.released = False

    def isOpened(self):
        return not self.released

    def read(self):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        return True, frame

    def release(self):
        self.released = True


class DummyTimer:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class DummyCaptureWorker:
    def __init__(self, source, target_fps=30.0, parent=None):
        self.source = source
        self.target_fps = target_fps
        self.parent = parent

        self.frame_ready = DummySignal()
        self.error = DummySignal()
        self.finished = DummySignal()

    def start(self):
        return None

    def stop(self):
        return None

    def wait(self, _timeout):
        return True

    def pause(self):
        return None

    def resume(self):
        return None

    @property
    def video_info(self):
        return {
            "width": 640,
            "height": 480,
            "fps": 30.0,
            "total_frames": 100,
            "current_frame": 0,
            "is_local_video": True,
        }


class DummyInferenceWorker:
    def __init__(self, config=None, parent=None):
        self.config = config
        self.parent = parent

        self.result_ready = DummySignal()
        self.error = DummySignal()
        self.finished = DummySignal()
        self.metrics_updated = DummySignal()

    def set_pipeline(self, _pipeline):
        return None

    def submit_frame(self, _frame_data):
        return None

    def set_confidence_threshold(self, _value):
        return None

    def set_iou_threshold(self, _value):
        return None

    def set_show_trajectory(self, _value):
        return None

    def start(self):
        return None

    def stop(self):
        return None

    def wait(self, _timeout):
        return True

    def pause(self):
        return None

    def resume(self):
        return None


class FakeTrajectoryManager:
    def __init__(self, trajectories):
        self._trajectories = trajectories

    def get_all_trajectories(self):
        return self._trajectories

    def get_statistics(self):
        total_trajectories = len(self._trajectories)
        total_points = sum(len(t.points) for t in self._trajectories.values())
        return {
            "total_trajectories": total_trajectories,
            "active_trajectories": total_trajectories,
            "total_points": total_points,
            "avg_trajectory_length": (total_points / total_trajectories) if total_trajectories else 0.0,
        }


@pytest.fixture(scope="module")
def qt_app():
    if not PYSIDE6_AVAILABLE:
        pytest.skip("PySide6 not available")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def main_window(qt_app):
    window = MainWindow()
    yield window
    window.close()


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_camera_preview_never_runs_pipeline(main_window):
    called = {"count": 0}

    def _process_frame(*_args, **_kwargs):
        called["count"] += 1
        return None, []

    main_window._camera_capture = DummyCapture()
    main_window._is_running = True
    main_window._pipeline = SimpleNamespace(process_frame=_process_frame)

    main_window._update_camera_frame()

    assert called["count"] == 0


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_start_worker_mode_stops_camera_preview_path(main_window, monkeypatch):
    import src.infra.config as config_module
    import src.core.pipeline as pipeline_module
    import src.gui.workers as workers_module

    class DummyPipeline:
        def __init__(self, config):
            self.config = config
            self.visualizer = SimpleNamespace(config=config.visualizer)
            self.trajectory_manager = FakeTrajectoryManager({})

        def warmup(self):
            return None

    monkeypatch.setattr(config_module, "load_config", lambda _path=None: Config())
    monkeypatch.setattr(pipeline_module, "TrackingPipeline", DummyPipeline)
    monkeypatch.setattr(workers_module, "VideoCaptureWorker", DummyCaptureWorker)
    monkeypatch.setattr(workers_module, "InferenceWorker", DummyInferenceWorker)

    main_window._camera_capture = DummyCapture()
    main_window._camera_timer = DummyTimer()
    main_window._current_source = "camera:0"

    started = main_window._start_worker_mode()

    assert started is True
    assert main_window._camera_capture is None
    assert main_window._camera_timer is None


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_mainwindow_export_chain_outputs_csv_and_json(main_window, tmp_path):
    from src.data.types import Trajectory

    traj = Trajectory(track_id=1)
    traj.add_point(10.0, 20.0, 1.0)
    traj.add_point(11.0, 21.0, 1.1)

    manager = FakeTrajectoryManager({1: traj})
    main_window._pipeline = SimpleNamespace(trajectory_manager=manager)
    main_window._current_source = "sample.mp4"

    csv_path = main_window._export_csv(tmp_path)
    stats_path = main_window._export_trajectory_stats(tmp_path)

    assert csv_path is not None and csv_path.exists()
    assert stats_path is not None and stats_path.exists()

    csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert csv_lines[0] == "track_id,point_index,timestamp,x,y"
    assert len(csv_lines) == 3

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    assert stats["total_trajectories"] == 1
    assert stats["total_points"] == 2


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_on_export_warns_when_no_data(main_window, monkeypatch):
    warnings = []

    manager = FakeTrajectoryManager({})
    main_window._pipeline = SimpleNamespace(trajectory_manager=manager)
    main_window._current_source = "sample.mp4"

    monkeypatch.setattr(QMessageBox, "warning", lambda *_args: warnings.append(_args[2]))

    main_window._on_export()

    assert warnings
    assert "轨迹数据" in warnings[0]


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_on_export_generates_files_via_mainwindow_path(main_window, tmp_path, monkeypatch):
    infos = []
    warnings = []

    from src.data.types import Trajectory

    traj = Trajectory(track_id=3)
    traj.add_point(100.0, 200.0, 2.0)
    manager = FakeTrajectoryManager({3: traj})

    main_window._pipeline = SimpleNamespace(trajectory_manager=manager)
    main_window._current_source = "sample.mp4"

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", lambda *_args: infos.append(_args[2]))
    monkeypatch.setattr(QMessageBox, "warning", lambda *_args: warnings.append(_args[2]))

    main_window._on_export()

    assert not warnings
    assert infos
    assert (tmp_path / "tracks.csv").exists()
    assert (tmp_path / "trajectory_stats.json").exists()


@pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not available")
def test_gui_param_change_updates_runtime_pipeline(main_window):
    cfg = Config()
    fake_pipeline = SimpleNamespace(
        config=cfg,
        visualizer=SimpleNamespace(config=cfg.visualizer),
    )

    main_window._pipeline = fake_pipeline
    main_window._is_running = True

    main_window._conf_spin.setValue(0.33)
    main_window._iou_spin.setValue(0.27)
    main_window._show_trajectory_check.setChecked(False)
    main_window._show_center_check.setChecked(False)

    main_window._on_config_value_changed()

    assert cfg.detector.confidence_threshold == pytest.approx(0.33, rel=1e-6)
    assert cfg.detector.iou_threshold == pytest.approx(0.27, rel=1e-6)
    assert fake_pipeline.visualizer.config.show_trajectory is False
    assert fake_pipeline.visualizer.config.show_center_point is False
