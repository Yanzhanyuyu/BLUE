"""Pytest 配置文件

提供测试 fixtures 和共享配置。
"""

import pytest
import numpy as np
from numpy.typing import NDArray
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def sample_image() -> NDArray[np.uint8]:
    """创建测试用图像

    Returns:
        640x480 BGR 格式测试图像
    """
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_bbox():
    """创建测试用边界框"""
    from src.data.types import BoundingBox
    return BoundingBox(x=100, y=100, w=50, h=80, confidence=0.95)


@pytest.fixture
def sample_detection(sample_bbox):
    """创建测试用检测结果"""
    from src.data.types import Detection
    return Detection(
        bbox=sample_bbox,
        class_id=0,
        class_name="person",
    )


@pytest.fixture
def sample_tracked_object(sample_detection):
    """创建测试用跟踪对象"""
    from src.data.types import TrackedObject
    return TrackedObject(
        track_id=1,
        detection=sample_detection,
        frame_id=0,
        timestamp=0.0,
    )


@pytest.fixture
def sample_config():
    """创建测试用配置"""
    from src.infra.config import Config
    return Config()


@pytest.fixture
def temp_output_dir(tmp_path):
    """创建临时输出目录"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
