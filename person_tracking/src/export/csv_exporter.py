"""CSV日志导出模块

提供检测跟踪结果的CSV导出功能，支持：
- 结构化日志写入
- 批量导出
- 自动文件管理
"""

import csv
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..data.types import TrackedObject
from ..infra.exceptions import ExportError
from ..infra.logger import get_logger

logger = get_logger("csv_exporter")


class CSVExporter:
    """CSV日志导出器

    将检测跟踪结果导出为CSV文件。

    输出格式：
        track_id, frame_id, timestamp, x, y, w, h, confidence, class_name

    Attributes:
        output_path: 输出文件路径
        file: 文件对象
        writer: CSV写入器

    Example:
        >>> exporter = CSVExporter("output/tracking_log.csv")
        >>> exporter.write_row(tracked_obj)
        >>> exporter.close()
    """

    # CSV 表头
    HEADER = [
        "track_id",
        "frame_id",
        "timestamp",
        "x",
        "y",
        "w",
        "h",
        "confidence",
        "class_name",
    ]

    def __init__(
        self,
        output_path: str | Path,
        mode: str = "w",
    ) -> None:
        """初始化CSV导出器

        Args:
            output_path: 输出文件路径
            mode: 写入模式
                - 'w': 覆盖写入（默认）
                - 'a': 追加写入

        Raises:
            ExportError: 文件创建失败
        """
        self.output_path = Path(output_path)
        self.mode = mode
        self._file = None
        self._writer = None
        self._row_count = 0

        # 确保输出目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件
        self._create_file()

        logger.info(f"CSVExporter initialized: output={output_path}")

    def _create_file(self) -> None:
        """创建CSV文件并写入表头

        Raises:
            ExportError: 文件创建失败
        """
        try:
            self._file = open(
                self.output_path,
                self.mode,
                newline="",
                encoding="utf-8",
            )
            self._writer = csv.writer(self._file)

            # 如果是覆盖模式或文件为空，写入表头
            if self.mode == "w":
                self.write_header()

        except Exception as e:
            raise ExportError(
                f"Failed to create CSV file",
                output_path=str(self.output_path),
                details=e,
            )

    def write_header(self) -> None:
        """写入CSV表头"""
        if self._writer is not None:
            self._writer.writerow(self.HEADER)
            self._file.flush()
            logger.debug(f"CSV header written: {self.HEADER}")

    def write_row(self, tracked_obj: TrackedObject) -> None:
        """写入单条跟踪记录

        Args:
            tracked_obj: 跟踪对象

        Raises:
            ExportError: 写入失败

        Example:
            >>> exporter.write_row(tracked_obj)
        """
        if self._writer is None:
            raise ExportError("CSV file not open")

        try:
            bbox = tracked_obj.bbox
            row = [
                tracked_obj.track_id,
                tracked_obj.frame_id,
                f"{tracked_obj.timestamp:.3f}",
                f"{bbox.x:.2f}",
                f"{bbox.y:.2f}",
                f"{bbox.w:.2f}",
                f"{bbox.h:.2f}",
                f"{bbox.confidence:.4f}",
                tracked_obj.detection.class_name,
            ]

            self._writer.writerow(row)
            self._row_count += 1

        except Exception as e:
            raise ExportError(
                f"Failed to write CSV row",
                output_path=str(self.output_path),
                details=e,
            )

    def write_batch(self, tracked_objects: List[TrackedObject]) -> None:
        """批量写入跟踪记录

        Args:
            tracked_objects: 跟踪对象列表

        Example:
            >>> exporter.write_batch(tracked_objects)
        """
        for obj in tracked_objects:
            self.write_row(obj)

    def flush(self) -> None:
        """刷新缓冲区"""
        if self._file is not None:
            self._file.flush()

    def close(self) -> None:
        """关闭文件

        Example:
            >>> exporter.close()
        """
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None

            logger.info(
                f"CSVExporter closed: {self._row_count} rows written to {self.output_path}"
            )

    def __enter__(self) -> "CSVExporter":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.close()

    @property
    def row_count(self) -> int:
        """获取已写入行数"""
        return self._row_count

    def get_summary(self) -> dict:
        """获取导出摘要

        Returns:
            导出摘要字典
        """
        return {
            "output_path": str(self.output_path),
            "row_count": self._row_count,
            "is_open": self._file is not None,
        }


def export_to_csv(
    tracked_objects: List[TrackedObject],
    output_path: str | Path,
) -> int:
    """便捷导出函数

    将跟踪对象列表导出到CSV文件。

    Args:
        tracked_objects: 跟踪对象列表
        output_path: 输出文件路径

    Returns:
        写入的记录数

    Example:
        >>> count = export_to_csv(tracked_objects, "output/log.csv")
        >>> print(f"Exported {count} records")
    """
    with CSVExporter(output_path) as exporter:
        exporter.write_batch(tracked_objects)
        return exporter.row_count
