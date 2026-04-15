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
)
from src.infra.exceptions import ConfigurationError


class TestDetectorConfig:
    """检测器配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = DetectorConfig()
        assert config.model_path == "yolo11n.pt"
        assert config.confidence_threshold == 0.5
        assert config.device == "auto"  # 默认值改为 auto
        assert config.classes == [0]

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
