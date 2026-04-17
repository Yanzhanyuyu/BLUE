# AGENTS.md - Person Tracking System

> 本文件为 AI Agent 工作规则文件，定义了项目的约束和约定。

---

## 一、项目概述

**人员检测跟踪系统** - 基于 YOLOv11 和 ByteTrack 的实时人员检测与跟踪解决方案。

### 核心能力
- 人物检测（YOLOv11）
- 多目标跟踪（ByteTrack）
- 轨迹记录与可视化
- CSV 日志导出
- PySide6 图形用户界面

### 技术栈
- Python 3.10+
- Ultralytics YOLOv11
- OpenCV
- PySide6 (GUI)
- Pydantic (配置验证)
- Loguru (日志)

---

## 二、目录结构

```
person_tracking/
├── config/               # 配置文件
│   ├── default.yaml      # 默认配置
│   └── bytetrack.yaml    # ByteTrack 配置
├── src/                  # 源代码
│   ├── main.py           # CLI 入口 + run_tracking API
│   ├── __init__.py       # 导出 run_tracking
│   ├── core/             # 核心模块
│   │   ├── detector.py   # PersonDetector
│   │   ├── tracker.py    # PersonTracker, YOLOTrackerWrapper
│   │   └── pipeline.py   # TrackingPipeline
│   ├── data/             # 数据模块
│   │   ├── types.py      # BoundingBox, Detection, TrackedObject, Frame, Trajectory
│   │   ├── loader.py     # VideoLoader, VideoWriter
│   │   └── trajectory.py # TrajectoryManager
│   ├── viz/              # 可视化
│   │   └── visualizer.py # Visualizer
│   ├── export/           # 导出
│   │   └── csv_exporter.py # CSVExporter
│   ├── infra/            # 基础设施
│   │   ├── config.py     # Config, DetectorConfig, TrackerConfig...
│   │   ├── logger.py     # setup_logger, get_logger
│   │   └── exceptions.py # TrackingSystemError, ModelLoadError...
│   └── gui/              # GUI 模块
│       ├── main_window.py # MainWindow
│       ├── workers.py    # VideoCaptureWorker, InferenceWorker
│       └── widgets/      # VideoCanvas, TrajectoryList, LogPanel
├── tests/                # 测试
├── docs/                 # 文档
├── requirements.txt      # 核心依赖
└── requirements-gui.txt  # GUI 依赖
```

---

## 三、构建与测试

### 运行测试
```bash
cd person_tracking
python -m pytest tests/ -v
```

### 测试覆盖
当前测试覆盖:
- `test_types.py`: 数据类型测试 (20 tests)
- `test_config.py`: 配置测试 (11 tests)
- `test_trajectory.py`: 轨迹管理测试 (9 tests)
- `test_csv_exporter.py`: CSV 导出测试 (6 tests)
- `test_parameter_override.py`: 参数边界值测试 (19 tests)

**总计**: 65 tests

### CLI 使用
```bash
python -m src.main --source video.mp4 --output output/tracked.mp4
python -m src.main --source 0 --show  # 摄像头
```

### GUI 使用
```bash
python -m src.gui.app
```

### Python API
```python
from src.main import run_tracking
stats = run_tracking(source="video.mp4", output="output/tracked.mp4")
```

---

## 四、架构约束

### 4.1 五层架构
1. **GUI 层** (`src/gui/`) - PySide6 用户界面
2. **应用层** (`src/main.py`) - CLI 入口、API
3. **核心层** (`src/core/`) - 检测器、跟踪器、处理管道
4. **数据层** (`src/data/`) - 视频加载、数据类型、轨迹管理
5. **基础设施层** (`src/infra/`) - 配置、日志、异常

### 4.2 关键约束
- **GUI 层不得直接访问核心层私有成员**
  - 使用公开方法如 `trajectory_manager.get_all_recent_points()`
  - 不使用 `trajectory_manager._trajectories`
  
- **Pipeline 直接调用 YOLO.track()**
  - 这是设计决策，`PersonDetector` 类存在但 Pipeline 使用 `model.track()` 进行一体化检测+跟踪
  - 修改此设计需要大规模重构

- **配置参数覆盖使用 `is not None` 判断**
  - 正确: `if confidence is not None:`
  - 错误: `if confidence:` (当 confidence=0.0 时会错误跳过)

---

## 五、已知问题与技术债

### P1 - 已在本轮修复
1. **GUI 主线程阻塞** - ✅ 已修复：Worker 线程（VideoCaptureWorker + InferenceWorker）与 MainWindow 完整集成
2. **导出功能占位** - ✅ 已修复：实现 `_on_export()` 完整逻辑（CSV导出 + 轨迹统计导出）
3. **show_progress 配置未使用** - ✅ 已修复：在 `src/main.py` 中添加配置项生效逻辑
4. **信号连接不完整** - ✅ 已修复：连接 `config_changed` 信号，实现参数热更新

### 实现细节
- **Worker 集成** (`main_window.py`):
  - `_start_worker_mode()`: 启动 VideoCaptureWorker 和 InferenceWorker
  - `_on_worker_frame_ready()`: 处理捕获的帧
  - `_on_inference_result_ready()`: 处理推理结果
  - `_on_metrics_updated()`: 更新性能指标
  - `_on_worker_error()`: 处理 Worker 错误

- **导出功能** (`main_window.py`):
  - `_on_export()`: 主导出逻辑
  - `_export_csv()`: CSV 跟踪日志导出
  - `_export_trajectory_stats()`: JSON 轨迹统计导出

- **参数热更新** (`main_window.py`):
  - `_on_config_value_changed()`: 处理配置变更
  - UI 控件绑定：置信度、IOU、设备、跟踪缓冲、可视化选项

- **show_progress 修复** (`src/main.py`):
  - 添加配置项判断逻辑：`should_show_progress = not quiet and cfg.pipeline.show_progress`

### P2 - 已在本轮修复/决策
1. **BoundingBox 无输入验证** - ✅ 已修复：添加 `__post_init__` 输入验证
2. **CSV 无原子写入** - ✅ 已修复：实现临时文件+重命名机制
3. **Pipeline 直接调用底层模型** - ⚠️ 设计决策保留：根据架构设计，Pipeline 直接使用 `model.track()` 是一体化检测+跟踪的优化设计，修改此设计需要大规模重构，暂不作为技术债处理

### 建议
- ✅ Worker 线程已完成与 MainWindow 集成
- 考虑引入 Service 层封装 Pipeline 操作（长期）
- 添加更多 GUI 集成测试（可选）

---

## 六、编码规范

### 6.1 参数判断
```python
# 正确：支持边缘值
if confidence is not None:
    cfg.detector.confidence_threshold = confidence

# 错误：当值为 0.0 或空字符串时会错误跳过
if confidence:
    cfg.detector.confidence_threshold = confidence
```

### 6.2 访问私有成员
```python
# 正确：使用公开方法
trajectories = self._pipeline.trajectory_manager.get_all_recent_points(50)

# 错误：直接访问私有成员
for track_id, traj in self._pipeline.trajectory_manager._trajectories.items():
    trajectories[track_id] = traj.points[-50:]
```

### 6.3 导入规范
```python
# 避免重复导入
# 错误
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtGui import QActionGroup, QIcon  # 重复

# 正确
from PySide6.QtGui import QAction, QActionGroup, QIcon
```

---

## 七、配置项说明

### 实际生效的配置
| 配置项 | 文件 | 是否生效 | 说明 |
|--------|------|----------|------|
| `detector.model_path` | config | ✅ | 模型加载 |
| `detector.confidence_threshold` | config | ✅ | 检测阈值 |
| `detector.device` | config | ✅ | 推理设备 |
| `tracker.track_buffer` | config | ✅ | 轨迹缓冲 |
| `pipeline.warmup` | config | ✅ | 模型预热 |
| `pipeline.skip_frames` | config | ✅ | 跳帧处理 |
| `pipeline.save_output` | config | ✅ | 保存输出 |
| `pipeline.show_progress` | config | ✅ | 进度条显示控制 |
| `logging.level` | config | ✅ | 日志级别 |

---

## 八、Agent 工作优先级

1. **P0 - 立即修复**: API 导出问题、参数判断 bug、私有成员访问
2. **P1 - 尽快修复**: 配置未生效、测试盲区
3. **P2 - 计划修复**: GUI 架构优化、Worker 集成

---

*文档版本: 1.0*
*最后更新: 2026-04-14*
