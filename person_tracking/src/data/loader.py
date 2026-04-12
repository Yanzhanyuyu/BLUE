"""视频/摄像头加载器模块

提供视频文件和摄像头流的统一加载接口，支持：
- 视频文件读取（MP4, AVI, MOV 等）
- 摄像头实时流读取
- 帧迭代器接口
- 自动资源管理
"""

from pathlib import Path
from typing import Iterator, Optional, Union
import cv2
import numpy as np
from numpy.typing import NDArray

from .types import Frame
from ..infra.exceptions import VideoLoadError
from ..infra.logger import get_logger

logger = get_logger("loader")


class VideoLoader:
    """视频/摄像头加载器

    支持视频文件和摄像头流的统一加载，提供迭代器接口。

    Attributes:
        source: 视频源（文件路径或摄像头索引）
        fps: 视频帧率
        frame_count: 总帧数（摄像头返回 -1）
        width: 视频宽度
        height: 视频高度

    Example:
        >>> # 从视频文件加载
        >>> loader = VideoLoader("video.mp4")
        >>> for frame in loader:
        ...     print(f"Frame {frame.frame_id}: shape={frame.shape}")
        >>> loader.release()

        >>> # 从摄像头加载
        >>> loader = VideoLoader(0)  # 默认摄像头
        >>> for frame in loader:
        ...     cv2.imshow("Camera", frame.image)
        ...     if cv2.waitKey(1) == ord('q'):
        ...         break
        >>> loader.release()
    """

    def __init__(
        self,
        source: Union[str, int, Path],
        start_frame: int = 0,
    ) -> None:
        """初始化视频加载器

        Args:
            source: 视频源
                - str/Path: 视频文件路径
                - int: 摄像头索引（如 0 表示默认摄像头）
            start_frame: 起始帧号（仅视频文件有效）

        Raises:
            VideoLoadError: 无法打开视频源
        """
        self.source = source
        self.start_frame = start_frame
        self._frame_id = 0
        self._cap: Optional[cv2.VideoCapture] = None

        # 初始化视频捕获
        self._init_capture()

        # 记录初始化信息
        logger.info(
            f"VideoLoader initialized: source={source}, "
            f"fps={self.fps:.2f}, size={self.width}x{self.height}"
        )

    def _init_capture(self) -> None:
        """初始化视频捕获对象

        Raises:
            VideoLoadError: 初始化失败
        """
        # 创建 VideoCapture 对象
        if isinstance(self.source, (str, Path)):
            self._cap = cv2.VideoCapture(str(self.source))
            self._is_camera = False
        else:
            self._cap = cv2.VideoCapture(self.source)
            self._is_camera = True

        # 检查是否成功打开
        if not self._cap.isOpened():
            raise VideoLoadError(
                "Failed to open video source",
                source=self.source,
            )

        # 获取视频属性
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 跳转到起始帧
        if self.start_frame > 0 and not self._is_camera:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            self._frame_id = self.start_frame

    @property
    def fps(self) -> float:
        """获取视频帧率

        Returns:
            帧率（FPS）
        """
        return self._fps if self._fps > 0 else 30.0  # 默认 30 FPS

    @property
    def frame_count(self) -> int:
        """获取总帧数

        Returns:
            总帧数，摄像头返回 -1
        """
        return self._frame_count if not self._is_camera else -1

    @property
    def width(self) -> int:
        """获取视频宽度"""
        return self._width

    @property
    def height(self) -> int:
        """获取视频高度"""
        return self._height

    @property
    def duration(self) -> float:
        """获取视频时长（秒）

        Returns:
            时长（秒），摄像头返回 -1
        """
        if self._is_camera or self._fps <= 0:
            return -1.0
        return self._frame_count / self._fps

    @property
    def is_camera(self) -> bool:
        """是否为摄像头源"""
        return self._is_camera

    @property
    def current_frame_id(self) -> int:
        """获取当前帧 ID"""
        return self._frame_id

    def read_frame(self) -> Optional[Frame]:
        """读取单帧

        Returns:
            Frame 对象，如果到达视频末尾或读取失败返回 None

        Example:
            >>> loader = VideoLoader("video.mp4")
            >>> frame = loader.read_frame()
            >>> if frame:
            ...     print(f"Frame {frame.frame_id}")
        """
        if self._cap is None or not self._cap.isOpened():
            return None

        # 读取帧
        ret, image = self._cap.read()

        if not ret:
            return None

        # 计算时间戳
        timestamp = self._frame_id / self.fps if self.fps > 0 else 0.0

        # 创建 Frame 对象
        frame = Frame(
            frame_id=self._frame_id,
            timestamp=timestamp,
            image=image,
        )

        self._frame_id += 1

        return frame

    def seek(self, frame_id: int) -> bool:
        """跳转到指定帧（仅视频文件有效）

        Args:
            frame_id: 目标帧 ID

        Returns:
            是否跳转成功

        Note:
            摄像头不支持跳转。
        """
        if self._is_camera or self._cap is None:
            return False

        if frame_id < 0 or frame_id >= self._frame_count:
            return False

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        self._frame_id = frame_id
        return True

    def __iter__(self) -> Iterator[Frame]:
        """迭代返回帧数据

        Yields:
            Frame 对象

        Example:
            >>> for frame in VideoLoader("video.mp4"):
            ...     print(f"Processing frame {frame.frame_id}")
        """
        while True:
            frame = self.read_frame()
            if frame is None:
                break
            yield frame

    def __len__(self) -> int:
        """获取总帧数

        Returns:
            总帧数，摄像头返回 -1
        """
        return self.frame_count

    def __enter__(self) -> "VideoLoader":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.release()

    def release(self) -> None:
        """释放资源

        关闭视频捕获对象，释放摄像头。

        Example:
            >>> loader = VideoLoader("video.mp4")
            >>> # ... 处理视频 ...
            >>> loader.release()
        """
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.debug(f"VideoLoader released: source={self.source}")

    def is_opened(self) -> bool:
        """检查视频源是否打开

        Returns:
            是否已打开
        """
        return self._cap is not None and self._cap.isOpened()

    def get_info(self) -> dict:
        """获取视频信息

        Returns:
            包含视频信息的字典

        Example:
            >>> loader = VideoLoader("video.mp4")
            >>> info = loader.get_info()
            >>> print(info)
            {
                'source': 'video.mp4',
                'fps': 30.0,
                'frame_count': 900,
                'width': 1920,
                'height': 1080,
                'duration': 30.0,
                'is_camera': False
            }
        """
        return {
            "source": str(self.source),
            "fps": self.fps,
            "frame_count": self.frame_count,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "is_camera": self._is_camera,
        }


class VideoWriter:
    """视频写入器

    支持将处理后的帧写入视频文件。

    Example:
        >>> writer = VideoWriter("output.mp4", fps=30, size=(1920, 1080))
        >>> for frame in frames:
        ...     writer.write(frame.image)
        >>> writer.release()
    """

    def __init__(
        self,
        output_path: Union[str, Path],
        fps: float = 30.0,
        size: tuple[int, int] = (1920, 1080),
        codec: str = "mp4v",
    ) -> None:
        """初始化视频写入器

        Args:
            output_path: 输出文件路径
            fps: 帧率
            size: 视频尺寸 (width, height)
            codec: 视频编码器（如 'mp4v', 'XVID', 'H264'）
        """
        self.output_path = Path(output_path)
        self.fps = fps
        self.size = size
        self.codec = codec
        self._writer: Optional[cv2.VideoWriter] = None
        self._frame_count = 0

        # 确保输出目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建 VideoWriter
        self._create_writer()

        logger.info(
            f"VideoWriter initialized: output={output_path}, "
            f"fps={fps}, size={size}"
        )

    def _create_writer(self) -> None:
        """创建 VideoWriter 对象"""
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self._writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            self.size,
        )

        if not self._writer.isOpened():
            raise VideoLoadError(
                "Failed to create video writer",
                source=str(self.output_path),
            )

    def write(self, frame: NDArray[np.uint8]) -> bool:
        """写入单帧

        Args:
            frame: BGR 格式图像数组

        Returns:
            是否写入成功
        """
        if self._writer is None:
            return False

        # 检查尺寸是否匹配
        h, w = frame.shape[:2]
        if (w, h) != self.size:
            # 调整尺寸
            frame = cv2.resize(frame, self.size)

        self._writer.write(frame)
        self._frame_count += 1
        return True

    def release(self) -> None:
        """释放资源"""
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            logger.info(
                f"VideoWriter released: {self._frame_count} frames written to {self.output_path}"
            )

    def __enter__(self) -> "VideoWriter":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.release()

    @property
    def frame_count(self) -> int:
        """获取已写入帧数"""
        return self._frame_count
