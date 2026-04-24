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
# 启动 GUI 应用（推荐方式，不依赖 PyTorch 加载）
python run_gui.py

# 或使用批处理脚本（Windows）
run_gui.bat

# 或使用 Python 模块（需要完整 PyTorch 环境）
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
| 结果导出 | 导出 tracks.csv 与 trajectory_stats.json（视频导出入口已禁用） |

### Python API

```python
from src.main import run_tracking

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

> 注：`src/gui/controller.py` 当前为废弃兼容壳，真实运行路径以 `src/gui/main_window.py` 为准。

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
├── config/               # 配置文件
│   ├── default.yaml      # 默认配置
│   └── bytetrack.yaml    # ByteTrack 配置
├── scripts/              # 工具脚本 🆕
│   └── verify_api_export.py  # API 导出验证
├── src/                  # 源代码
│   ├── gui/              # GUI 模块
│   │   ├── __init__.py
│   │   ├── app.py        # 应用入口
│   │   ├── main_window.py # 主窗口
│   │   ├── workers.py    # 工作线程
│   │   └── widgets/      # 可复用组件
│   │       ├── video_canvas.py
│   │       ├── trajectory_list.py
│   │       └── log_panel.py
│   ├── core/             # 核心模块
│   │   ├── detector.py   # 检测器
│   │   ├── tracker.py    # 跟踪器
│   │   └── pipeline.py   # 处理管道
│   ├── data/             # 数据模块
│   │   ├── loader.py     # 视频加载
│   │   ├── types.py      # 数据类型
│   │   └── trajectory.py # 轨迹管理
│   ├── viz/              # 可视化模块
│   │   └── visualizer.py
│   ├── export/           # 导出模块
│   │   └── csv_exporter.py
│   ├── infra/            # 基础设施
│   │   ├── config.py     # 配置管理
│   │   ├── logger.py     # 日志配置
│   │   └── exceptions.py # 异常定义
│   ├── main.py           # CLI 主入口
│   └── __init__.py       # 包导出 (run_tracking)
├── tests/                # 测试
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_trajectory.py
│   ├── test_csv_exporter.py
│   └── test_parameter_override.py 🆕
├── docs/                 # 文档
│   ├── PROJECT_HANDOFF.md
│   ├── GUI_DESIGN_HANDOFF.md
│   └── SESSION_HANDOFF.md 🆕
├── output/               # 输出目录
├── logs/                 # 日志目录
├── AGENTS.md             # 项目规则文件 🆕
├── requirements.txt      # 核心依赖
└── requirements-gui.txt  # GUI 依赖
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

### 单元测试（91个测试）🆕

- `test_types.py`: 数据类型测试（BoundingBox, Detection, TrackedObject, Frame, Trajectory）
- `test_config.py`: 配置加载/保存测试
- `test_trajectory.py`: 轨迹管理测试
- `test_csv_exporter.py`: CSV 导出测试
- `test_parameter_override.py`: 参数边界值测试
- `test_worker_integration.py`: Worker 集成测试 🆕
- `test_export_functionality.py`: 导出功能测试 🆕

### 运行测试

```bash
cd person_tracking
python -m pytest tests/ -v
```

### API 导出验证 🆕

```bash
# 验证 README 中声明的 API 是否与源码一致
python scripts/verify_api_export.py
```

## 配置说明

主要配置项（`config/default.yaml`）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| detector.model_path | 模型路径 | yolo11n.pt |
| detector.confidence_threshold | 检测置信度 | 0.5 |
| detector.device | 推理设备 | auto |
| tracker.tracker_type | 跟踪器类型 | bytetrack |
| tracker.tracker_config_path | 跟踪器配置路径 | config/bytetrack.yaml |
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

## 最近更新

### 2026-04-17 真实调用链修复与收口 🆕

- ✅ **统一 GUI 唯一主路径**：摄像头定时器路径降级为纯预览，推理统一走 `VideoCaptureWorker + InferenceWorker`。
- ✅ **修复重复帧推理**：`InferenceWorker` 采用“原子取走 latest_frame + last_processed_frame_id”机制，停止送帧后不再重复处理旧帧。
- ✅ **打通参数生效链**：`_apply_ui_config_to_pipeline_config()` 完整落地，`_on_config_value_changed()` 区分“可热更新参数”与“需重启参数”。
- ✅ **修复 MainWindow 导出链**：补全 `_on_export()` / `_export_csv()` / `_export_trajectory_stats()`，稳定导出 `tracks.csv` 与 `trajectory_stats.json`，空数据给出明确提示。
- ✅ **清理伪架构**：`src/gui/controller.py` 降级为废弃兼容壳，避免并行维护两套 GUI 状态管理逻辑。
- ✅ **RTSP 入口收口**：GUI 增加 RTSP/HTTP URL 输入与连接逻辑，不再保留假入口。
- ✅ **配置来源收口**：默认启动自动读取 `config/default.yaml`，并优先使用项目内 `config/bytetrack.yaml`。
- ✅ **新增回归测试**：覆盖重复帧、摄像头路径互斥、MainWindow 导出链、GUI 参数生效、默认配置来源等关键场景。

### 2026-04-14 P1/P2 技术债修复完成 🆕

#### P1 技术债（全部修复）
- ✅ **Worker 线程集成** - VideoCaptureWorker + InferenceWorker 完整集成
- ✅ **导出功能** - 实现 CSV 导出和轨迹统计导出
- ✅ **show_progress 配置** - 配置项生效，CLI 支持静默模式
- ✅ **config_changed 信号** - UI 参数热更新，无需重启

#### P2 技术债（全部处理）
- ✅ **BoundingBox 输入验证** - 添加 `__post_init__` 边界检查
- ✅ **CSV 原子写入** - 实现临时文件+重命名机制，防止文件损坏
- ⚠️ **Pipeline 职责边界** - 明确为设计决策，无需修改

#### 测试增强
- ✅ 新增 Worker 集成测试（7 个）
- ✅ 新增导出功能测试（12 个）
- ✅ 新增参数边界值测试（19 个）
- ✅ 测试总数从 65 增加到 **91**，全部通过

#### GUI 启动优化
- ✅ **修复 GUI 启动问题** - 移除 `src/__init__.py` 的自动导入，避免 GUI 启动时加载 PyTorch
- ✅ **新增启动脚本** - `run_gui.py` 和 `run_gui.bat` 提供独立的 GUI 启动方式

---

### 2026-04-14 工程审计与增量改造
- ✅ 修复 `src/__init__.py` 未导出 `run_tracking` 的 API 一致性问题
- ✅ 修复参数覆盖使用 truthy 判断的 bug（改为 `is not None`）
- ✅ 修复 GUI 直接访问核心层私有成员的封装问题
- ✅ 实现 Pipeline CLI 模式的 `skip_frames` 支持
- ✅ 新增 `get_all_recent_points()` 公开方法
- ✅ 新增 API 导出验证脚本 `scripts/verify_api_export.py`
- ✅ 创建项目规则文件 `AGENTS.md`
- ✅ 创建会话交接文档 `docs/SESSION_HANDOFF.md`

### 2026-04-15 GUI 视频画面位置稳定性修复 🆕
修复了 GUI 中视频画面位置跳动的问题：

#### Bug 修复
- ✅ **视频画面居中稳定** - 修复画面在居中和左上角之间跳动的问题
- `src/gui/widgets/video_canvas.py`: 
  - 从布局中移除 `_image_label`，改为直接子 widget，避免布局管理器与手动定位冲突
  - 在 `_update_display()` 中添加显式居中逻辑
- **问题原因**: `AlignCenter` 仅对 pixmap 内容有效，对 label 位置无效；`_image_label` 被添加到 `QVBoxLayout` 导致布局刷新时位置跳动
- **解决方案**: 
  - 从布局中移除 label，由代码手动控制位置
  - 添加显式 `move()` 调用确保画面始终居中
  - 保留 pan 功能（通过偏移量计算）

### 2026-04-15 GUI 架构重构与性能优化
本次重构解决了核心架构问题，在不牺牲视觉观感的前提下提升性能：

#### 核心架构修复
- ✅ **统一渲染源** - 移除 VideoCanvas 的二次绘制，Visualizer 成为唯一渲染器
- `src/gui/widgets/video_canvas.py`: 移除 `_draw_overlay()` 方法，改为纯显示组件
- `src/viz/visualizer.py`: 添加 `show_bbox/trajectory/id` 配置开关支持
- ✅ **跳帧连续性** - 跳过的帧使用上一帧渲染结果，消除闪烁和轨迹断裂
- `src/core/pipeline.py`: 新增 `FrameStateCache` 类保持视觉连续性
- `src/gui/workers.py`: 修复跳帧逻辑使用缓存结果
- ✅ **配置开关全链路** - GUI 开关实时同步到 Pipeline 配置
- `src/infra/config.py`: `VisualizerConfig` 新增显示开关配置
- `src/gui/main_window.py`: 实现 `_apply_ui_config_to_pipeline_config()` 方法

#### 工程结构优化
- ✅ **标准包导入** - 移除 `run_gui.py` 的 `sys.path.insert` 绕过
- ✅ **设备自动选择** - `device` 默认改为 `"auto"`，自动选择 cuda/mps/cpu
- ✅ **高质量缩放** - VideoCanvas 使用 `SmoothTransformation` 替代 `FastTransformation`
- ✅ **依赖清理** - `requirements-gui.txt` 移除重复依赖声明

#### 文档
- ✅ 新增重构报告 `docs/REFACTOR_REPORT.md`（含 A-G 完整分析）

### 性能优化 (2024)
- ✅ 视频采集和推理已移出GUI主线程，使用独立的Worker线程
- ✅ VideoCanvas优化：减少不必要的图像拷贝，使用快速缩放
- ✅ 新增 `workers.py` 模块：VideoCaptureWorker 和 InferenceWorker
- ✅ 新增 `constants.py` 模块：节流参数集中配置
- ✅ 进度条功能：本地视频支持时间显示和拖动跳转

### 已知限制
- RTSP 和本地视频的时间轴功能需要进一步完善
- 长时间运行时的内存占用优化（可选）
- 多摄像头同时支持（可选）

## 许可证

MIT License
