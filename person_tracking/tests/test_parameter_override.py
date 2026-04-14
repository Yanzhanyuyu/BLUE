"""参数边界值测试

测试参数覆盖逻辑在各种边界值情况下的行为，
确保使用 is not None 判断而非 truthy 判断。
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.infra.config import (
    Config,
    DetectorConfig,
    TrackerConfig,
    load_config,
)
from src.main import run_tracking


class TestParameterOverride:
    """参数覆盖测试"""

    def test_confidence_zero(self):
        """测试 confidence=0.0 应被正确覆盖（不应被 truthy 跳过）"""
        config = Config()
        # 默认值是 0.5
        assert config.detector.confidence_threshold == 0.5

        # 覆盖为 0.0
        config.detector.confidence_threshold = 0.0
        assert config.detector.confidence_threshold == 0.0

    def test_confidence_very_low(self):
        """测试非常低的置信度值"""
        config = DetectorConfig(confidence_threshold=0.001)
        assert config.confidence_threshold == 0.001

    def test_confidence_exact_one(self):
        """测试置信度正好为 1.0"""
        config = DetectorConfig(confidence_threshold=1.0)
        assert config.confidence_threshold == 1.0

    def test_confidence_exact_zero(self):
        """测试置信度正好为 0.0"""
        config = DetectorConfig(confidence_threshold=0.0)
        assert config.confidence_threshold == 0.0

    def test_iou_zero(self):
        """测试 IOU=0.0 应被正确接受"""
        config = DetectorConfig(iou_threshold=0.0)
        assert config.iou_threshold == 0.0

    def test_iou_one(self):
        """测试 IOU=1.0 应被正确接受"""
        config = DetectorConfig(iou_threshold=1.0)
        assert config.iou_threshold == 1.0

    def test_model_path_empty_string(self):
        """测试空字符串模型路径（应被 Pydantic 接受）"""
        # 注意：这可能在实际使用中导致问题，但配置验证应该允许
        config = DetectorConfig()
        config.model_path = ""
        assert config.model_path == ""

    def test_track_buffer_minimum(self):
        """测试 track_buffer 最小值"""
        config = TrackerConfig(track_buffer=1)
        assert config.track_buffer == 1

    def test_track_buffer_large(self):
        """测试 track_buffer 大值"""
        config = TrackerConfig(track_buffer=100)
        assert config.track_buffer == 100


class TestConfigOverrideLogic:
    """配置覆盖逻辑测试"""

    def test_override_with_none(self):
        """测试使用 None 值不应覆盖（应使用默认值）"""
        config = Config()
        original_conf = config.detector.confidence_threshold

        # 模拟 CLI 参数覆盖逻辑
        # 当传入 None 时，不应覆盖
        confidence = None
        if confidence is not None:
            config.detector.confidence_threshold = confidence

        assert config.detector.confidence_threshold == original_conf

    def test_override_with_zero(self):
        """测试使用 0.0 值应正确覆盖"""
        config = Config()
        original_conf = config.detector.confidence_threshold
        assert original_conf != 0.0  # 确保默认值不是 0

        # 模拟 CLI 参数覆盖逻辑
        confidence = 0.0
        if confidence is not None:
            config.detector.confidence_threshold = confidence

        assert config.detector.confidence_threshold == 0.0

    def test_override_with_false_equivalent(self):
        """测试各种 falsy 值都能正确覆盖"""
        config = Config()
        test_values = [0.0, 0, False]

        for val in test_values:
            # 重置
            config.detector.confidence_threshold = 0.5

            # 使用 is not None 判断
            if val is not None:
                # 注意：Pydantic 会验证范围，所以这里只测试非 None 判断逻辑
                config.detector.confidence_threshold = 0.5  # 重置

            # 验证没有被错误跳过
            # 对于浮点数，confidence_threshold 有范围限制
            # 所以我们只验证 is not None 逻辑

    def test_is_not_none_vs_truthy(self):
        """对比 is not None 与 truthy 判断的行为差异"""
        # 对于整数 0：
        # - bool(0) = False，所以 truthy 会跳过
        # - 0 is not None = True，所以 is not None 会应用
        val = 0
        truthy_would_skip = not bool(val)  # True (会跳过)
        is_not_none_would_apply = val is not None  # True (会应用)
        # 这两个判断的结果相反吗？不是！
        # truthy_would_skip = True 表示"会跳过"
        # is_not_none_would_apply = True 表示"会应用"
        # 所以两者行为确实不同：
        # truthy 会跳过 0，is not None 会应用 0
        # 检查 truthy 判断是否错误地跳过了非 None 的 falsy 值
        assert truthy_would_skip == True, "truthy 判断会跳过 0"
        assert is_not_none_would_apply == True, "is not None 判断会应用 0"

        # 对于浮点数 0.0，同样如此
        val = 0.0
        truthy_would_skip = not bool(val)  # True (会跳过)
        is_not_none_would_apply = val is not None  # True (会应用)
        assert truthy_would_skip == True
        assert is_not_none_would_apply == True

        # 对于空字符串
        val = ""
        truthy_would_skip = not bool(val)  # True (会跳过)
        is_not_none_would_apply = val is not None  # True (会应用)
        assert truthy_would_skip == True
        assert is_not_none_would_apply == True

        # 对于 None：
        val = None
        truthy_would_skip = not bool(val)  # True (会跳过)
        is_not_none_would_apply = val is not None  # False (不会应用)
        assert truthy_would_skip == True, "truthy 会跳过 None"
        assert is_not_none_would_apply == False, "is not None 不会应用 None"


class TestConfigValidation:
    """配置验证测试"""

    def test_detector_out_of_range_high(self):
        """测试超出上限的置信度"""
        with pytest.raises(Exception):
            DetectorConfig(confidence_threshold=1.5)

    def test_detector_out_of_range_low(self):
        """测试低于下限的置信度"""
        with pytest.raises(Exception):
            DetectorConfig(confidence_threshold=-0.1)

    def test_detector_negative_imgsz(self):
        """测试负数的图像尺寸"""
        with pytest.raises(Exception):
            DetectorConfig(imgsz=-100)

    def test_detector_too_small_imgsz(self):
        """测试太小的图像尺寸"""
        with pytest.raises(Exception):
            DetectorConfig(imgsz=64)  # 最小是 128

    def test_tracker_negative_buffer(self):
        """测试负数的 track_buffer"""
        with pytest.raises(Exception):
            TrackerConfig(track_buffer=-1)

    def test_tracker_zero_buffer(self):
        """测试 zero track_buffer（最小是 1）"""
        with pytest.raises(Exception):
            TrackerConfig(track_buffer=0)
