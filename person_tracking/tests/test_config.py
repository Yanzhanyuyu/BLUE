"""配置模块测试

测试配置加载和验证功能。
"""

import pytest
from pathlib import Path
import yaml

from src.infra.config import (
    Config,
    DetectorConfig,
    TrackerConfig,
    VisualizerConfig,
    PipelineConfig,
    LoggingConfig,
    load_config,
    save_config,
    resolve_tracker_config_path,
)
from src.infra.exceptions import ConfigurationError


class TestDetectorConfig:
    """检测器配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = DetectorConfig()
        assert config.model_path == "yolo11n.pt"
        assert config.confidence_threshold == 0.35
        assert config.device == "auto"  # 默认值改为 auto
        assert config.classes == [0]
        assert config.imgsz == 960
        assert config.max_det == 500

    def test_custom_config(self):
        """测试自定义配置"""
        config = DetectorConfig(
            model_path="yolo11s.pt",
            confidence_threshold=0.7,
            device="cpu",
        )
        assert config.model_path == "yolo11s.pt"
        assert config.confidence_threshold == 0.7
        assert config.device == "cpu"

    def test_validation_confidence(self):
        """测试置信度验证"""
        with pytest.raises(Exception):
            DetectorConfig(confidence_threshold=1.5)
        with pytest.raises(Exception):
            DetectorConfig(confidence_threshold=-0.1)


class TestTrackerConfig:
    """跟踪器配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = TrackerConfig()
        assert config.tracker_type == "bytetrack"
        assert config.track_buffer == 30
        assert config.match_thresh == 0.8


class TestVisualizerConfig:
    """可视化配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = VisualizerConfig()
        assert config.box_color == (0, 255, 0)
        assert config.trajectory_length == 50
        assert config.show_center_point is True


class TestConfig:
    """完整配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert config.detector is not None
        assert config.tracker is not None
        assert config.visualizer is not None

    def test_nested_config(self):
        """测试嵌套配置"""
        config = Config(
            detector=DetectorConfig(confidence_threshold=0.7),
            tracker=TrackerConfig(track_buffer=50),
        )
        assert config.detector.confidence_threshold == 0.7
        assert config.tracker.track_buffer == 50


class TestLoadConfig:
    """配置加载测试"""

    def test_load_default(self):
        """测试加载默认配置"""
        config = load_config()
        assert isinstance(config, Config)
        assert config.detector.model_path == "yolo11n.pt"
        assert config.detector.max_det == 500

    def test_load_from_file(self, temp_output_dir):
        """测试从文件加载"""
        # 创建临时配置文件
        config_dict = {
            "detector": {
                "model_path": "yolo11s.pt",
                "confidence_threshold": 0.6,
            }
        }
        config_file = temp_output_dir / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_dict, f)

        # 加载配置
        config = load_config(config_file)
        assert config.detector.model_path == "yolo11s.pt"
        assert config.detector.confidence_threshold == 0.6

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(ConfigurationError):
            load_config("nonexistent.yaml")


class TestSaveConfig:
    """配置保存测试"""

    def test_save_config(self, temp_output_dir):
        """测试保存配置"""
        config = Config()
        output_file = temp_output_dir / "saved_config.yaml"

        save_config(config, output_file)

        assert output_file.exists()

        # 验证可以重新加载
        loaded = load_config(output_file)
        assert loaded.detector.model_path == config.detector.model_path


class TestConfigSourceResolution:
    """配置来源解析测试"""

    def test_load_config_uses_default_yaml_when_present(self, monkeypatch, tmp_path):
        """测试 load_config(None) 会优先读取默认 YAML 文件"""
        from src.infra import config as config_module

        default_yaml = tmp_path / "default.yaml"
        default_yaml.write_text(
            yaml.dump(
                {
                    "detector": {
                        "model_path": "custom.pt",
                        "confidence_threshold": 0.23,
                    },
                    "tracker": {
                        "tracker_type": "bytetrack",
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", default_yaml)

        loaded = config_module.load_config()
        assert loaded.detector.model_path == "custom.pt"
        assert loaded.detector.confidence_threshold == pytest.approx(0.23, rel=1e-6)

    def test_resolve_tracker_config_path_prefers_explicit_path(self, tmp_path):
        """测试 tracker 配置路径优先使用显式路径"""
        tracker_yaml = tmp_path / "my_tracker.yaml"
        tracker_yaml.write_text("tracker_type: bytetrack\n", encoding="utf-8")

        tracker_cfg = TrackerConfig(
            tracker_type="bytetrack",
            tracker_config_path=str(tracker_yaml),
        )

        resolved = resolve_tracker_config_path(tracker_cfg)
        assert resolved == str(tracker_yaml)

    def test_resolve_tracker_config_path_fallback_string(self):
        """测试 tracker 配置在无文件时回退为 Ultralytics 默认字符串"""
        tracker_cfg = TrackerConfig(
            tracker_type="botsort",
            tracker_config_path=None,
        )

        resolved = resolve_tracker_config_path(tracker_cfg)
        assert resolved == "botsort.yaml"

    def test_project_bytetrack_yaml_contains_modern_keys(self):
        """测试项目 ByteTrack 配置包含新版 Ultralytics 所需字段"""
        from src.infra.config import DEFAULT_BYTETRACK_CONFIG_PATH

        assert DEFAULT_BYTETRACK_CONFIG_PATH.exists()

        with open(DEFAULT_BYTETRACK_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        assert "track_high_thresh" in cfg
        assert "track_low_thresh" in cfg
        assert "new_track_thresh" in cfg
        assert "match_thresh" in cfg
