# 人员检测跟踪系统

基于 YOLOv11 和 ByteTrack 的人物检测、跟踪与定位系统。

## 功能特性

- ✅ 人物检测（基于 YOLOv11）
- ✅ 多目标跟踪（基于 ByteTrack）
- ✅ 轨迹记录与可视化
- ✅ CSV 日志导出
- ✅ 支持视频文件和摄像头
- ✅ **图形用户界面（PySide6）** 🆕
- ✅ 模块化设计，易于扩展

## 快速开始

### 安装依赖

```bash
cd person_tracking

# 安装核心依赖
pip install -r requirements.txt

# 安装 GUI 依赖（可选）
pip install -r requirements-gui.txt
```

### 命令行使用

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

### 图形界面使用 🆕

```bash
# 启动 GUI 应用
python -m src.gui.app
```

或通过 Python 代码启动：

```python
from src.gui import run_gui
run_gui()
```

#### GUI 功能说明

| 功能 | 说明 |
|------|------|
| 视频源选择 | 支持本地文件、摄像头、RTSP 流 |
| 参数配置 | 检测置信度、IOU 阈值、设备选择 |
| 实时预览 | 视频画面 + 检测框 + 轨迹叠加 |
| 状态监控 | FPS、检测数、目标列表 |
| 轨迹历史 | 查看选中目标的轨迹记录 |
| 日志面板 | 系统运行日志实时显示 |
| 结果导出 | 导出视频和 CSV 日志 |

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

### 五层架构设计

| 层级 | 模块 | 职责 |
|------|------|------|
| GUI 层 | gui/ | 图形用户界面（PySide6） |
| 应用层 | main.py | CLI 入口、用户交互 |
| 核心层 | core/ | 检测器、跟踪器、处理管道 |
| 数据层 | data/ | 视频加载、数据类型、轨迹管理 |
| 基础设施层 | infra/ | 配置、日志、异常处理 |

### GUI 架构 🆕

```
┌─────────────────────────────────────────────────────────────┐
│                    PySide6 GUI 应用层                        │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│ │   Views     │ │ Controllers │ │  Services   │ │ Workers │ │
│ │  (视图层)   │◄│  (控制层)   │◄│  (服务层)   │◄│(工作线程)│ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    核心算法层（不修改）                       │
│               core/pipeline.py - TrackingPipeline           │
├─────────────────────────────────────────────────────────────┤
│                 数据与基础设施层（不修改）                    │
│       config.py │ logger.py │ exceptions.py │ loader.py     │
└─────────────────────────────────────────────────────────────┘
```

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
TrajectoryManager  Visualizer
│                  │
│                  ▼
│          渲染后的帧图像
│
▼
CSVExporter ───> 日志文件
```

### 模块职责

**核心模块：**
- `detector.py`: 封装 YOLOv11，输出 person 类别的检测结果
- `tracker.py`: 封装 ByteTrack，维护 track_id 跨帧关联
- `pipeline.py`: 协调检测→跟踪→可视化→导出的完整流程

**数据模块：**
- `loader.py`: 统一视频文件和摄像头流的加载接口
- `types.py`: 核心数据类型定义
- `trajectory.py`: 轨迹历史管理

**GUI 模块 🆕：**
- `main_window.py`: 主窗口框架，包含菜单栏、工具栏、状态栏
- `video_canvas.py`: 视频画布组件，支持检测框和轨迹叠加
- `trajectory_list.py`: 轨迹历史列表组件
- `log_panel.py`: 系统日志显示面板

## 项目结构

```
person_tracking/
├── config/                    # 配置文件
│   ├── default.yaml           # 默认配置
│   └── bytetrack.yaml         # ByteTrack 配置
├── src/                       # 源代码
│   ├── gui/                   # GUI 模块 🆕
│   │   ├── __init__.py
│   │   ├── app.py             # 应用入口
│   │   ├── main_window.py     # 主窗口
│   │   ├── widgets/           # 可复用组件
│   │   │   ├── video_canvas.py
│   │   │   ├── trajectory_list.py
│   │   │   └── log_panel.py
│   │   ├── views/             # 视图层
│   │   └── resources/         # 资源文件
│   │       └── styles/
│   │           └── dark.qss   # 深色主题
│   ├── core/                  # 核心模块
│   │   ├── detector.py        # 检测器
│   │   ├── tracker.py         # 跟踪器
│   │   └── pipeline.py        # 处理管道
│   ├── data/                  # 数据模块
│   │   ├── loader.py          # 视频加载
│   │   ├── types.py           # 数据类型
│   │   └── trajectory.py      # 轨迹管理
│   ├── viz/                   # 可视化模块
│   │   └── visualizer.py
│   ├── export/                # 导出模块
│   │   └── csv_exporter.py
│   ├── infra/                 # 基础设施
│   │   ├── config.py          # 配置管理
│   │   ├── logger.py          # 日志配置
│   │   └── exceptions.py      # 异常定义
│   └── main.py                # CLI 主入口
├── tests/                     # 测试
├── output/                    # 输出目录
├── logs/                      # 日志目录
├── requirements.txt           # 核心依赖
└── requirements-gui.txt       # GUI 依赖 🆕
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
- PySide6 >= 6.5.0（用于 GUI）

## 许可证

MIT License
