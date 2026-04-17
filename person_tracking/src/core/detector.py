"""人物检测器模块

封装 Ultralytics YOLOv11 检测模型，提供：
- 模型加载和预热
- 人物检测（过滤只保留 person 类别）
- 结果转换为标准 Detection 格式
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from ..infra.config import DetectorConfig
from ..infra.exceptions import ModelLoadError, InferenceError
from ..infra.logger import get_logger
from ..data.types import BoundingBox, Detection

logger = get_logger("detector")


class PersonDetector:
    """人物检测器

    封装 YOLOv11 检测模型，专门用于人物检测。

    Attributes:
        config: 检测器配置
        model: YOLOv11 模型实例

    Example:
        >>> config = DetectorConfig(model_path="yolo11n.pt", confidence_threshold=0.5)
        >>> detector = PersonDetector(config)
        >>> detections = detector.detect(frame)
        >>> for det in detections:
        ...     print(f"Person detected: confidence={det.confidence:.2f}")
    """

    # COCO 数据集类别映射
    COCO_CLASSES = {
        0: "person",
        1: "bicycle",
        2: "car",
        # ... 其他类别省略
    }

    # person 类别 ID
    PERSON_CLASS_ID = 0

    def __init__(self, config: DetectorConfig) -> None:
        """初始化人物检测器

        Args:
            config: 检测器配置

        Raises:
            ModelLoadError: 模型加载失败
        """
        self.config = config
        self._model = None
        self._warmup_done = False

        # 加载模型
        self._load_model()

        logger.info(
            f"PersonDetector initialized: model={config.model_path}, "
            f"conf={config.confidence_threshold}, device={config.device}"
        )

    def _load_model(self) -> None:
        """加载 YOLOv11 模型

        Raises:
            ModelLoadError: 加载失败
        """
        try:
            from ultralytics import YOLO

            logger.debug(f"Loading model: {self.config.model_path}")
            self._model = YOLO(self.config.model_path)

            # 设置设备（处理 auto 情况）
            device = self.config.device
            if device == "auto":
                # 自动选择设备
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"
            
            # 将模型移动到指定设备
            self._model.to(device)

            logger.info(f"Model loaded successfully: {self.config.model_path}")

        except Exception as e:
            raise ModelLoadError(
                f"Failed to load YOLOv11 model",
                model_path=self.config.model_path,
                details=e,
            )

    def warmup(self, input_size: tuple[int, int] = (640, 480)) -> None:
        """模型预热

        运行一次虚拟推理，避免首帧延迟。

        Args:
            input_size: 输入图像尺寸 (height, width)
        """
        if self._warmup_done:
            return

        logger.debug(f"Warming up model with input size: {input_size}")

        # 创建虚拟图像
        dummy_image = np.zeros(
            (input_size[0], input_size[1], 3),
            dtype=np.uint8,
        )

        try:
            # 运行一次推理
            _ = self._model(
                dummy_image,
                conf=self.config.confidence_threshold,
                iou=self.config.iou_threshold,
                classes=self.config.classes,
                imgsz=self.config.imgsz,
                verbose=False,
            )
            self._warmup_done = True
            logger.debug("Model warmup completed")

        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")

    def detect(
        self,
        image: NDArray[np.uint8],
        frame_id: Optional[int] = None,
    ) -> list[Detection]:
        """检测图像中的人物

        Args:
            image: BGR 格式图像数组 (H, W, C)
            frame_id: 帧编号（用于错误报告）

        Returns:
            Detection 列表（仅包含 person 类别）

        Raises:
            InferenceError: 推理失败

        Example:
            >>> detections = detector.detect(frame)
            >>> print(f"Detected {len(detections)} persons")
        """
        if self._model is None:
            raise ModelLoadError("Model not loaded")

        try:
            # 运行推理
            results = self._model(
                image,
                conf=self.config.confidence_threshold,
                iou=self.config.iou_threshold,
                classes=self.config.classes,  # 只检测 person
                imgsz=self.config.imgsz,
                verbose=False,
            )

            # 转换结果
            detections = self._convert_results(results)

            # 记录日志
            logger.debug(
                f"Frame {frame_id}: detected {len(detections)} persons"
            )

            return detections

        except Exception as e:
            raise InferenceError(
                f"Detection inference failed",
                frame_id=frame_id,
                details=e,
            )

    def _convert_results(self, results) -> list[Detection]:
        """转换 YOLO 结果为 Detection 格式

        Args:
            results: YOLO 推理结果

        Returns:
            Detection 列表
        """
        detections = []

        if not results or len(results) == 0:
            return detections

        result = results[0]

        # 检查是否有检测结果
        if result.boxes is None or len(result.boxes) == 0:
            return detections

        # 提取边界框、置信度和类别
        boxes = result.boxes

        # 获取坐标 (xyxy 格式)
        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)

        # 转换为 Detection 对象
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            confidence = float(confidences[i])
            class_id = int(class_ids[i])

            # 创建边界框
            bbox = BoundingBox.from_xyxy(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                confidence=confidence,
            )

            # 创建检测结果
            detection = Detection(
                bbox=bbox,
                class_id=class_id,
                class_name="person",  # 只处理 person
            )

            detections.append(detection)

        return detections

    def get_model_info(self) -> dict:
        """获取模型信息

        Returns:
            模型信息字典
        """
        if self._model is None:
            return {"loaded": False}

        return {
            "loaded": True,
            "model_path": self.config.model_path,
            "device": self.config.device,
            "confidence_threshold": self.config.confidence_threshold,
            "iou_threshold": self.config.iou_threshold,
            "classes": self.config.classes,
            "warmup_done": self._warmup_done,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"PersonDetector(model={self.config.model_path}, "
            f"conf={self.config.confidence_threshold}, "
            f"device={self.config.device})"
        )
