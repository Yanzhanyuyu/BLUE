# Person Tracking System

基于 YOLOv11 和 ByteTrack 的人物检测、跟踪与定位系统。

## 功能特性

- ✅ 人物检测（基于 YOLOv11）
- ✅ 多目标跟踪（基于 ByteTrack）
- ✅ 轨迹记录与可视化
- ✅ CSV 日志导出
- ✅ 支持视频文件和摄像头
- ✅ 模块化设计，易于扩展

## 快速开始

### 安装依赖

```bash
cd person_tracking
pip install -r requirements.txt
```

### 基本使用

```bash
# 处理视频文件
python -m src.main --source video.mp4 --output output/tracked.mp4

# 使用摄像头实时处理
python -m src.main --source 0 --show

# 导出 CSV 日志
python -m src.main --source video.mp4 --csv output/log.csv

# 指定配置文件
python -m src.main --source video.mp4 --config config/default.yaml
```

### Python API

```python
from src import run_tracking

# 运行跟踪
stats = run_tracking(
    source="video.mp4",
    output="output/tracked.mp4",
    csv="output/log.csv",
)

print(f"处理完成: {stats['total_frames']} 帧, {stats['avg_fps']:.1f} FPS")
```

## 系统架构

### 四层架构设计

| 层级 | 模块 | 职责 |
|------|------|------|
| 应用层 | main.py | CLI 入口、用户交互 |
| 核心层 | core/ | 检测器、跟踪器、处理管道 |
| 数据层 | data/ | 视频加载、数据类型、轨迹管理 |
| 基础设施层 | infra/ | 配置、日志、异常处理 |

### 数据流说明

```
视频源(视频文件/摄像头)
    │
    ▼
VideoLoader ───> Frame(frame_id, timestamp, image)
    │
    ▼
YOLOv11检测 ───> Detection(bbox, class_id, confidence)
    │
    ▼
ByteTrack跟踪 ───> TrackedObject(track_id, detection, frame_id)
    │
    ├──────────────────┐
    ▼                  ▼
TrajectoryManager   Visualizer
    │                  │
    │                  ▼
    │          渲染后的帧图像
    │
    ▼
CSVExporter ───> 日志文件
```

### 模块职责

- **detector.py**: 封装 YOLOv11，输出 person 类别的检测结果
- **tracker.py**: 封装 ByteTrack，维护 track_id 跨帧关联
- **pipeline.py**: 协调检测→跟踪→可视化→导出的完整流程
- **loader.py**: 统一视频文件和摄像头流的加载接口
- **visualizer.py**: 绘制边界框、ID、轨迹、中心点
- **csv_exporter.py**: 导出结构化日志

## 项目结构

```
person_tracking/
├── config/           # 配置文件
│   ├── default.yaml  # 默认配置
│   └── bytetrack.yaml # ByteTrack 配置
├── src/              # 源代码
│   ├── core/         # 核心模块
│   │   ├── detector.py   # 检测器
│   │   ├── tracker.py    # 跟踪器
│   │   └── pipeline.py   # 处理管道
│   ├── data/         # 数据模块
│   │   ├── loader.py     # 视频加载
│   │   ├── types.py      # 数据类型
│   │   └── trajectory.py # 轨迹管理
│   ├── viz/          # 可视化模块
│   │   └── visualizer.py
│   ├── export/       # 导出模块
│   │   └── csv_exporter.py
│   ├── infra/        # 基础设施
│   │   ├── config.py     # 配置管理
│   │   ├── logger.py     # 日志配置
│   │   └── exceptions.py # 异常定义
│   └── main.py       # 主入口
├── tests/            # 测试
├── output/           # 输出目录
├── logs/             # 日志目录
└── requirements.txt
```

## 异常处理策略

系统定义了完整的异常层次结构：

| 异常类型 | 触发场景 | 处理策略 |
|----------|----------|----------|
| ModelLoadError | 模型文件不存在或加载失败 | 记录错误，提示下载，退出 |
| VideoLoadError | 视频/摄像头无法打开 | 记录错误，退出 |
| ConfigurationError | 配置文件格式错误 | 使用默认配置 + 警告日志 |
| InferenceError | 单帧推理失败 | 跳过该帧，继续处理 |
| ExportError | CSV 写入失败 | 记录错误，不中断处理 |

## 日志方案

- **级别**: DEBUG/INFO/WARNING/ERROR/CRITICAL
- **格式**: `时间 | 级别 | 模块:函数:行号 - 消息`
- **输出**: 控制台(彩色) + 文件(自动轮转)
- **配置**: 通过 `config/default.yaml` 的 `logging` 部分配置

## 测试方案

### 单元测试（44个测试）

- `test_types.py`: 数据类型测试（BoundingBox, Detection, TrackedObject, Frame, Trajectory）
- `test_config.py`: 配置加载/保存测试
- `test_trajectory.py`: 轨迹管理测试
- `test_csv_exporter.py`: CSV 导出测试

### 运行测试

```bash
cd person_tracking
python -m pytest tests/ -v
```

## 配置说明

主要配置项（`config/default.yaml`）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| detector.model_path | 模型路径 | yolo11n.pt |
| detector.confidence_threshold | 检测置信度 | 0.5 |
| detector.device | 推理设备 | cuda |
| tracker.tracker_type | 跟踪器类型 | bytetrack |
| tracker.track_buffer | 轨迹缓冲帧数 | 30 |
| visualizer.trajectory_length | 轨迹显示长度 | 50 |

## 输出格式

### CSV 日志格式

| 字段 | 说明 |
|------|------|
| track_id | 跟踪 ID |
| frame_id | 帧编号 |
| timestamp | 时间戳 |
| x, y | 边界框左上角坐标 |
| w, h | 边界框宽高 |
| confidence | 检测置信度 |
| class_name | 类别名称 |

## 系统要求

- Python 3.10+
- CUDA 兼容 GPU（可选，用于加速）

## 许可证

MIT License
