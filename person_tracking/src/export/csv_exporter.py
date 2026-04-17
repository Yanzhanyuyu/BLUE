"""CSV日志导出模块

提供检测跟踪结果的CSV导出功能，支持：
- 结构化日志写入
- 批量导出
- 自动文件管理
- 原子写入（通过临时文件+重命名）
"""

import csv
import os
import tempfile
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
        atomic: bool = True,
    ) -> None:
        """初始化CSV导出器

        Args:
            output_path: 输出文件路径
            mode: 写入模式
                - 'w': 覆盖写入（默认）
                - 'a': 追加写入
            atomic: 是否使用原子写入（默认True），通过临时文件+重命名实现

        Raises:
            ExportError: 文件创建失败
        """
        self.output_path = Path(output_path)
        self.mode = mode
        self._atomic = atomic and mode == "w"  # 只有覆盖模式支持原子写入
        self._file = None
        self._writer = None
        self._row_count = 0
        self._temp_path: Optional[Path] = None

        # 确保输出目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件
        self._create_file()

        logger.info(f"CSVExporter initialized: output={output_path}, atomic={self._atomic}")

    def _create_file(self) -> None:
        """创建CSV文件并写入表头

        如果使用原子写入模式，会先写入临时文件，最后通过 close() 重命名为目标文件。

        Raises:
            ExportError: 文件创建失败
        """
        try:
            if self._atomic:
                # 原子写入：使用临时文件
                fd, temp_path = tempfile.mkstemp(
                    suffix=".csv.tmp",
                    prefix="tracking_",
                    dir=str(self.output_path.parent),
                )
                os.close(fd)  # 关闭文件描述符，我们只需要路径
                self._temp_path = Path(temp_path)
                self._file = open(
                    self._temp_path,
                    "w",
                    newline="",
                    encoding="utf-8",
                )
            else:
                # 普通写入
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

        如果使用原子写入模式，会将临时文件重命名为目标文件。
        在 Windows 上，文件必须先完全关闭才能重命名。

        Example:
            >>> exporter.close()
        """
        temp_path_to_rename = None
        
        if self._file is not None:
            self._file.flush()
            try:
                os.fsync(self._file.fileno())  # 确保数据写入磁盘
            except (OSError, ValueError):
                pass  # 某些情况下 fsync 可能失败
            
            # 获取临时文件路径（如果启用了原子写入）
            if self._atomic:
                temp_path_to_rename = self._temp_path
            
            self._file.close()
            self._file = None
            self._writer = None

        # 原子写入：临时文件重命名为目标文件
        # 必须在文件关闭后进行重命名（Windows 要求）
        if temp_path_to_rename is not None and temp_path_to_rename.exists():
            try:
                # 如果目标文件已存在，先删除（Windows 不支持覆盖重命名）
                if self.output_path.exists():
                    self.output_path.unlink()
                # 原子重命名
                os.rename(temp_path_to_rename, self.output_path)
                logger.debug(f"Atomic rename: {temp_path_to_rename} -> {self.output_path}")
            except OSError as e:
                # 清理临时文件
                if temp_path_to_rename.exists():
                    try:
                        temp_path_to_rename.unlink()
                    except OSError:
                        pass
                raise ExportError(
                    f"Failed to rename temp file to output",
                    output_path=str(self.output_path),
                    details=e,
                )

        self._temp_path = None

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
