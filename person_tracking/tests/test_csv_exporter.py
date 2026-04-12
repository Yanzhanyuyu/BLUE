"""CSV 导出测试

测试 CSVExporter 的功能。
"""

import pytest
from pathlib import Path
import csv

from src.export.csv_exporter import CSVExporter, export_to_csv
from src.data.types import TrackedObject, Detection, BoundingBox


class TestCSVExporter:
    """CSV 导出器测试"""

    def test_exporter_creation(self, temp_output_dir):
        """测试导出器创建"""
        output_path = temp_output_dir / "test.csv"
        exporter = CSVExporter(output_path)
        assert exporter.output_path == output_path
        exporter.close()

    def test_write_header(self, temp_output_dir):
        """测试写入表头"""
        output_path = temp_output_dir / "test.csv"
        with CSVExporter(output_path) as exporter:
            pass  # 表头在创建时自动写入

        # 验证表头
        with open(output_path, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "track_id" in header
            assert "frame_id" in header
            assert "confidence" in header

    def test_write_row(self, temp_output_dir, sample_tracked_object):
        """测试写入单行"""
        output_path = temp_output_dir / "test.csv"

        with CSVExporter(output_path) as exporter:
            exporter.write_row(sample_tracked_object)

        # 验证内容
        with open(output_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["track_id"] == "1"
            assert rows[0]["class_name"] == "person"

    def test_write_batch(self, temp_output_dir):
        """测试批量写入"""
        output_path = temp_output_dir / "test.csv"

        # 创建多个跟踪对象
        tracked_objects = []
        for i in range(5):
            bbox = BoundingBox(x=100 + i * 50, y=100, w=50, h=80, confidence=0.9)
            detection = Detection(bbox=bbox, class_id=0, class_name="person")
            obj = TrackedObject(
                track_id=i,
                detection=detection,
                frame_id=i,
                timestamp=i * 0.033,
            )
            tracked_objects.append(obj)

        with CSVExporter(output_path) as exporter:
            exporter.write_batch(tracked_objects)
            assert exporter.row_count == 5

    def test_context_manager(self, temp_output_dir, sample_tracked_object):
        """测试上下文管理器"""
        output_path = temp_output_dir / "test.csv"

        with CSVExporter(output_path) as exporter:
            exporter.write_row(sample_tracked_object)

        # 文件应该已关闭
        assert exporter._file is None


class TestExportToCSV:
    """便捷导出函数测试"""

    def test_export_function(self, temp_output_dir):
        """测试便捷导出函数"""
        output_path = temp_output_dir / "test.csv"

        # 创建跟踪对象
        tracked_objects = []
        for i in range(3):
            bbox = BoundingBox(x=100 + i * 50, y=100, w=50, h=80, confidence=0.9)
            detection = Detection(bbox=bbox, class_id=0, class_name="person")
            obj = TrackedObject(
                track_id=i,
                detection=detection,
                frame_id=i,
                timestamp=i * 0.033,
            )
            tracked_objects.append(obj)

        count = export_to_csv(tracked_objects, output_path)
        assert count == 3

        # 验证文件存在
        assert output_path.exists()
