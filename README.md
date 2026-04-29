# 人员检测跟踪系统（YOLOv11 + ByteTrack）

基于 YOLOv11 与 ByteTrack 的人物检测、跟踪与轨迹分析系统，提供 CLI、GUI 与 Python API，适用于课程设计、毕业设计与视频分析实验场景。

## 主要特性

- 人物检测与多目标跟踪
- 轨迹记录、可视化渲染与统计导出
- 视频文件 / 摄像头 / RTSP 输入
- PySide6 桌面 GUI
- YAML 配置驱动，模块化架构

## 快速开始

### 1) 环境要求

- Python 3.10+
- Windows/macOS/Linux
- 可选：CUDA 兼容 GPU（加速推理）

### 2) 安装依赖

```bash
cd person_tracking

# 核心依赖
pip install -r requirements.txt

# GUI 依赖（如需 GUI）
pip install -r requirements-gui.txt
```

### 3) 命令行运行

```bash
# 视频文件
python -m src.main --source video.mp4 --output output/tracked.mp4

# 摄像头
python -m src.main --source 0 --show

# CSV 导出
python -m src.main --source video.mp4 --csv output/tracks.csv

# 指定配置文件
python -m src.main --source video.mp4 --config config/default.yaml
```

### 4) 图形界面运行

```bash
# 推荐入口（从项目根目录）
python run_gui.py

# Windows 可用
run_gui.bat
```

### 5) Python API

```python
from src.main import run_tracking

stats = run_tracking(
    source="video.mp4",
    output="output/tracked.mp4",
    csv="output/tracks.csv",
)

print(stats["total_frames"], stats["avg_fps"])
```

## 模型权重

默认使用 `yolo11n.pt`。项目内已提供该权重，也可替换为其他 YOLOv11 权重文件，并在配置中同步更新 `detector.model_path`。

## 配置与参数

默认配置位于 `config/default.yaml`，ByteTrack 参数位于 `config/bytetrack.yaml`。

常用配置项：

| 模块 | 关键配置 | 说明 |
| --- | --- | --- |
| detector | model_path, confidence_threshold, iou_threshold, device | 模型路径与推理阈值 |
| tracker | tracker_type, track_buffer, match_thresh | 跟踪策略与缓冲 |
| visualizer | show_bbox, show_trajectory, show_id | GUI 显示开关 |
| pipeline | skip_frames, output_fps, warmup | 处理管道参数 |
| logging | level, file | 日志等级与输出 |

> 建议在 `person_tracking` 目录运行命令，确保相对路径与模型文件生效。

## 输出与数据格式

- 输出视频：由 `--output` 指定路径
- CSV 跟踪日志：由 `--csv` 指定路径
- GUI 导出：`tracks.csv` + `trajectory_stats.json`

CSV 字段：

| 字段 | 说明 |
| --- | --- |
| track_id | 跟踪 ID |
| frame_id | 帧编号 |
| timestamp | 时间戳 |
| x, y, w, h | 边界框坐标 |
| confidence | 置信度 |
| class_name | 类别名 |

## 项目结构（核心部分）

```
person_tracking/
├── config/               # 配置
├── src/                  # 源码
│   ├── core/             # 检测/跟踪/管道
│   ├── data/             # 数据结构与轨迹管理
│   ├── export/           # CSV 导出
│   ├── gui/              # GUI
│   ├── infra/            # 配置/日志/异常
│   ├── viz/              # 可视化
│   └── main.py           # CLI + API
├── tests/                # 测试
├── docs/                 # 文档
├── run_gui.py            # GUI 入口
├── requirements.txt
└── requirements-gui.txt
```

## 测试

```bash
cd person_tracking
python -m pytest tests/ -v
```

## 架构概览

系统采用五层架构：GUI 层 / 应用层 / 核心层 / 数据层 / 基础设施层。核心处理流程为：视频输入 → 检测与跟踪 → 轨迹管理 → 可视化 → 导出。

## 研究与工程说明

- 已覆盖 90+ 个自动化测试，包含数据类型、配置加载、导出与 Worker 集成等关键路径。
- GUI 与核心算法层解耦，便于教学展示与后续扩展。
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
