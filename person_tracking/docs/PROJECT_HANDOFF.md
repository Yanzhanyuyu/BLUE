# 人员检测跟踪系统 - 项目交接文档

> 文档版本: 1.0  
> 创建日期: 2026-04-12  
> 用途: 跨对话传递项目状态、问题分析和改进建议

---

## 一、项目概览

### 1.1 项目信息
- **项目名称**: 基于 YOLOv11 与 ByteTrack 的人员检测跟踪系统
- **当前状态**: 核心功能完成 + GUI Phase 1 完成
- **技术栈**: Python 3.10+, PySide6, YOLOv11, ByteTrack, OpenCV

### 1.2 核心功能
- ✅ 人物检测（基于 YOLOv11）
- ✅ 多目标跟踪（基于 ByteTrack）
- ✅ 轨迹记录与可视化
- ✅ CSV 日志导出
- ✅ 支持视频文件和摄像头
- ✅ PySide6 图形用户界面

### 1.3 项目结构

```
person_tracking/
├── config/                      # 配置文件
│   ├── default.yaml             # 默认配置
│   └── bytetrack.yaml           # ByteTrack 配置
├── src/                         # 源代码
│   ├── gui/                     # GUI 模块 (新增)
│   │   ├── __init__.py
│   │   ├── app.py               # 应用入口
│   │   ├── main_window.py       # 主窗口 (1345+ 行)
│   │   ├── widgets/             # 可复用组件
│   │   │   ├── video_canvas.py  # 视频画布
│   │   │   ├── trajectory_list.py # 轨迹列表
│   │   │   └── log_panel.py     # 日志面板
│   │   └── resources/styles/
│   │       └── dark.qss         # 深色主题
│   ├── core/                    # 核心模块
│   │   ├── detector.py          # 检测器
│   │   ├── tracker.py           # 跟踪器
│   │   └── pipeline.py          # 处理管道
│   ├── data/                    # 数据模块
│   │   ├── loader.py            # 视频加载
│   │   ├── types.py             # 数据类型
│   │   └── trajectory.py        # 轨迹管理
│   ├── viz/                     # 可视化模块
│   │   └── visualizer.py
│   ├── export/                  # 导出模块
│   │   └── csv_exporter.py
│   ├── infra/                   # 基础设施
│   │   ├── config.py            # 配置管理
│   │   ├── logger.py            # 日志配置
│   │   └── exceptions.py        # 异常定义
│   └── main.py                  # CLI 主入口
├── tests/                       # 测试
├── docs/                        # 文档
│   └── GUI_DESIGN_HANDOFF.md    # GUI 设计文档
├── requirements.txt             # 核心依赖
└── requirements-gui.txt         # GUI 依赖
```

---

## 二、架构分析

### 2.1 五层架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GUI 层 (PySide6)                            │
│  MainWindow → VideoCanvas / TrajectoryList / LogPanel              │
├─────────────────────────────────────────────────────────────────────┤
│                         应用层 (CLI)                                │
│  main.py → run_tracking() / argparse                               │
├─────────────────────────────────────────────────────────────────────┤
│                         核心层                                      │
│  TrackingPipeline → YOLO + ByteTrack + TrajectoryManager           │
├─────────────────────────────────────────────────────────────────────┤
│                         数据层                                      │
│  VideoLoader / Frame / Detection / TrackedObject / Trajectory      │
├─────────────────────────────────────────────────────────────────────┤
│                       基础设施层                                    │
│  Config (Pydantic) / Logger (Loguru) / Exceptions                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流图

```
视频源 (文件/摄像头)
    │
    ▼
VideoLoader.read_frame()
    │
    ▼
Frame (frame_id, timestamp, image)
    │
    ▼
YOLO.track() → 检测 + 跟踪一体化
    │
    ▼
TrackedObject (track_id, detection, frame_id)
    │
    ├──────────────────┐
    ▼                  ▼
TrajectoryManager   Visualizer.render()
    │                  │
    │                  ▼
    │          渲染后的帧图像
    │
    ▼
CSVExporter → 日志文件
```

### 2.3 GUI 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MainWindow                                   │
├───────────────┬─────────────────────────────────┬───────────────────┤
│   左侧面板    │         中央区域                │    右侧面板        │
│  (参数设置)   │      (VideoCanvas)              │   (状态信息)       │
├───────────────┼─────────────────────────────────┼───────────────────┤
│ 视频源参数    │                                 │ 统计卡片          │
│ - 源类型选择  │      ┌─────────────────────┐    │ - FPS             │
│ - 文件路径    │      │                     │    │ - 帧数            │
│ - 选择按钮    │      │   视频显示区域       │    │ - 检测数          │
├───────────────┤      │                     │    ├───────────────────┤
│ 检测参数      │      │  ┌───┐ ID:5 0.92   │    │ 目标列表          │
│ - 置信度      │      │  └───┘             │    │ ID │置信│位置     │
│ - IOU 阈值    │      │                     │    │ 5  │0.92│...     │
│ - 设备选择    │      │  ●━━●━━●━━●         │    │ 12 │0.87│...     │
├───────────────┤      │     轨迹线          │    ├───────────────────┤
│ 跟踪参数      │      │                     │    │ 轨迹历史          │
│ - 跟踪器类型  │      └─────────────────────┘    │ 选择ID: [5▼]      │
│ - 轨迹缓冲    │                                 │ 点数: 152        │
├───────────────┤  ┌──────────────────────────┐  ├───────────────────┤
│ 可视化设置    │  │ 播放控制栏               │  │ 日志面板          │
│ ☑ 边框       │  │ ▶ ▮▮ ■ ═══○═══ 00:00   │  │ [INFO] ...        │
│ ☑ 轨迹       │  └──────────────────────────┘  │ [DEBUG] ...       │
│ ☑ ID 标签    │                                 │                   │
└───────────────┴─────────────────────────────────┴───────────────────┘
```

---

## 三、核心模块分析

### 3.1 核心层 (src/core/)

#### detector.py
| 类/方法 | 职责 |
|---------|------|
| `PersonDetector.__init__` | 初始化，加载 YOLO 模型 |
| `PersonDetector.detect()` | 执行推理，返回 Detection 列表 |
| `PersonDetector.warmup()` | 模型预热 |
| `PersonDetector._convert_results()` | YOLO 结果转换为 Detection |

**关键依赖**: `DetectorConfig`, `YOLO`, `BoundingBox`, `Detection`

#### tracker.py
| 类/方法 | 职责 |
|---------|------|
| `PersonTracker.__init__` | 初始化，构建跟踪器配置 |
| `PersonTracker.update()` | 将 Detection 转换为 TrackedObject |
| `YOLOTrackerWrapper.track()` | 使用 YOLO track() 进行检测+跟踪 |

**关键依赖**: `TrackerConfig`, `TrackedObject`, `Detection`

#### pipeline.py
| 类/方法 | 职责 |
|---------|------|
| `TrackingPipeline.__init__` | 初始化所有组件 |
| `TrackingPipeline.process_frame()` | 处理单帧 (检测+跟踪+轨迹更新) |
| `TrackingPipeline.run()` | 完整处理流程入口 |
| `TrackingPipeline._convert_results()` | 转换为 TrackedObject |

**关键依赖**: `Config`, `VideoLoader`, `Visualizer`, `TrajectoryManager`, `CSVExporter`

### 3.2 数据层 (src/data/)

#### types.py - 核心数据类型
| 类型 | 字段 | 用途 |
|------|------|------|
| `BoundingBox` | x, y, w, h, confidence | 边界框定义 |
| `Detection` | bbox, class_id, class_name, track_id | 检测结果 |
| `TrackedObject` | track_id, detection, frame_id, timestamp | 跟踪对象 |
| `Frame` | frame_id, timestamp, image, detections, tracked_objects | 帧数据 |
| `Trajectory` | track_id, points[], max_length | 轨迹历史 |
| `PerformanceMetrics` | fps, total_frames, avg_*_time_ms | 性能指标 |

#### trajectory.py
| 类/方法 | 职责 |
|---------|------|
| `TrajectoryManager.update()` | 更新轨迹历史 |
| `TrajectoryManager.cleanup_inactive()` | 清理失效轨迹 |
| `TrajectoryManager.get_trajectory()` | 获取指定 ID 轨迹 |

### 3.3 GUI 层 (src/gui/)

#### main_window.py (1345+ 行)
| 组件/方法 | 职责 |
|-----------|------|
| `MainWindow.__init__` | 初始化窗口、状态、信号连接 |
| `MainWindow._init_ui()` | 创建三栏布局 |
| `MainWindow._create_left_panel()` | 参数面板 (5个参数组) |
| `MainWindow._create_center_panel()` | 视频区域 + 播放控制 |
| `MainWindow._create_right_panel()` | 状态面板 + 轨迹历史 + 日志 |
| `MainWindow._on_open_camera()` | 打开摄像头并启动预览 |
| `MainWindow._update_camera_frame()` | 摄像头帧处理 + Pipeline 集成 |
| `MainWindow._show_idle_screen()` | 显示待机画面 |

#### video_canvas.py
| 方法 | 职责 |
|------|------|
| `VideoCanvas.set_frame()` | 设置并显示帧图像 |
| `VideoCanvas.set_overlay()` | 设置检测框、轨迹叠加 |
| `VideoCanvas._draw_overlay()` | 绘制检测框、轨迹线、ID 标签 |
| `MockFrameGenerator.generate()` | 生成 Mock 测试数据 |

---

## 四、已发现的问题

### 4.1 高优先级问题 (Oracle 验证确认)

#### 问题 H1: Pipeline 在 GUI 主线程阻塞 [严重]
- **位置**: `main_window.py:1250-1275` (证据：`_update_camera_frame()`)
- **证据代码**:
  ```python
  # main_window.py:1250-1275
  if self._is_running:
      if self._pipeline is None:
          self._pipeline = TrackingPipeline(config)  # 初始化
          self._pipeline.warmup()                     # 预热
      processed_frame, tracked_objects = self._pipeline.process_frame(data_frame)  # 阻塞
  ```
- **描述**: `TrackingPipeline.process_frame()` 在 GUI 主线程中执行，YOLO 推理会阻塞 UI
- **影响**: 实际检测时界面卡顿，用户体验极差
- **解决方案**: 创建 `DetectionWorker(QThread)` 将推理移至后台线程

#### 问题 H2: 直接访问私有成员破坏封装 [严重]
- **位置**: `main_window.py:1293-1295`
- **证据代码**:
  ```python
  # main_window.py:1294
  for track_id, traj in self._pipeline.trajectory_manager._trajectories.items():
      trajectories[track_id] = traj.points[-50:]
  ```
- **描述**: GUI 直接访问 `TrajectoryManager._trajectories` 私有字典
- **影响**: 破坏封装性，增加耦合风险，重构困难
- **解决方案**: 在 `TrajectoryManager` 添加公开方法:
  ```python
  def get_recent_trajectory_points(self, n: int = 50) -> dict[int, list]:
      return {track_id: traj.get_recent_points(n) for track_id, traj in self._trajectories.items()}
  ```

#### 问题 H3: 信号定义但未使用 [严重]
- **位置**: `main_window.py:66-71` (定义), `main_window.py:958-966` (连接), `main_window.py:1045-1046` (发送)
- **证据代码**:
  ```python
  # 定义但未完整连接的信号 (main_window.py:66-71)
  start_requested = Signal()       # 发出但无接收者
  pause_requested = Signal()       # 发出但无接收者
  stop_requested = Signal()        # 发出但无接收者
  config_changed = Signal(dict)    # 从未使用
  
  # 发送信号 (main_window.py:1045-1046)
  self.start_requested.emit()  # 无连接者
  ```
- **描述**: `config_changed` 等信号定义后未被有效连接使用
- **影响**: 参数热更新功能缺失，配置变更需重启
- **解决方案**: 完善 `_init_connections()` 连接所有信号

#### 问题 H4: Detector/Tracker 职责边界不清 [严重]
- **位置**: `pipeline.py:141-151`
- **证据代码**:
  ```python
  # pipeline.py:141-151
  if enable_tracking:
      results = self.model.track(...)  # 直接调用 YOLO，未使用 PersonDetector
  ```
- **描述**: Pipeline 直接调用 `YOLO.track()`，未复用已封装的 `PersonDetector` 类
- **影响**: 模块化程度低，`detector.py` 形同虚设
- **解决方案**: Pipeline 通过 `PersonDetector` 接口调用检测

### 4.2 中优先级问题

#### 问题 M1: 配置加载无降级机制
- **位置**: `config.py:291-318`
- **证据代码**:
  ```python
  # config.py:291-294 - 无配置文件时返回默认配置
  if config_path is None:
      return Config()
  
  # config.py:316-318 - 配置错误时直接抛异常
  try:
      return Config(**config_dict)
  except Exception as e:
      raise ConfigurationError(...)  # 无降级
  ```
- **描述**: 配置加载失败时直接抛异常，无默认配置降级机制
- **影响**: 用户配置错误时系统无法启动
- **解决方案**: 添加 `load_config_safe()` 提供降级逻辑

#### 问题 M2: 导出功能未实现
- **位置**: `main_window.py:1121-1127`
- **证据代码**:
  ```python
  # main_window.py:1121-1127
  # TODO: 实际导出逻辑将在后续阶段实现
  QMessageBox.information(self, "导出", f"导出功能将在后续阶段实现...")
  ```
- **描述**: 导出按钮仅显示占位消息，实际功能未实现
- **影响**: 用户无法导出检测结果
- **解决方案**: 实现 `_on_export()` 完整逻辑

#### 问题 6: 重复导入
- **位置**: `main_window.py:39,41` (原文档行号，实际是 `main_window.py:45-46`)
- **证据代码**:
  ```python
  # main_window.py:45-46
  from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QIcon
  from PySide6.QtGui import QActionGroup, QKeySequence, QIcon  # 重复导入
  ```
- **描述**: `QActionGroup, QKeySequence, QIcon` 在两行重复导入
- **影响**: 代码冗余，降低代码质量
- **解决方案**: 合并导入，清理重复

### 4.3 低优先级问题

#### 问题 L1: BoundingBox 缺少输入验证
- **位置**: `types.py:23-45`
- **证据代码**:
  ```python
  # types.py:23-45 - BoundingBox 定义，无字段校验
  @dataclass
  class BoundingBox:
      x: float  # 可为负值
      y: float  # 可为负值
      w: float  # 可为负值
      h: float  # 可为负值
      confidence: float = 1.0
  ```
- **描述**: x, y, w, h 可为负值，无边界校验
- **影响**: 无效输入可能导致渲染错误或崩溃
- **解决方案**: 添加 `__post_init__` 或 Pydantic 验证

#### 问题 L2: CSV 导出无原子性保证
- **位置**: `csv_exporter.py:89-146`
- **证据代码**:
  ```python
  # csv_exporter.py:89-101 - 直接打开文件写入
  self._file = open(self._path, 'w', newline='', encoding='utf-8')
  self._writer = csv.DictWriter(self._file, ...)
  # 无原子写入策略，崩溃时文件损坏
  ```
- **描述**: 写入中断可能损坏文件
- **影响**: 系统崩溃时数据丢失风险
- **解决方案**: 使用临时文件 + 原子重命名

#### 问题 L3: 颜色生成可能冲突
- **位置**: `video_canvas.py:219-226` (原 `visualizer.py`)
- **证据代码**:
  ```python
  # 使用 track_id 作为随机种子
  random.seed(track_id)
  color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
  ```
- **描述**: 使用哈希生成颜色，可能产生相似颜色
- **影响**: 多目标时难以区分
- **解决方案**: 使用预定义调色板（如 colorcet、glasbey）

---

## 四点五、问题对照表 (Oracle 验证)

| ID | 问题 | 文件 | 行号 | 优先级 | 状态 | 影响 |
|----|------|------|------|--------|------|------|
| **H1** | Pipeline 阻塞 GUI 线程 | main_window.py | 1250-1275 | **高** | 待修复 | 界面卡顿 |
| **H2** | 访问私有成员 `_trajectories` | main_window.py | 1293-1295 | **高** | 待修复 | 破坏封装 |
| **H3** | `config_changed` 信号未连接 | main_window.py | 66-71, 958-966 | **高** | 待修复 | 热更新失效 |
| **H4** | 未使用 `PersonDetector` 封装 | pipeline.py | 141-151 | **高** | 待修复 | 职责混乱 |
| **M1** | 配置加载无降级 | config.py | 291-318 | 中 | 待修复 | 配置错误崩溃 |
| **M2** | 导出功能未实现 | main_window.py | 1121-1127 | 中 | 待修复 | 功能缺失 |
| **L1** | BoundingBox 无校验 | types.py | 23-45 | 低 | 待修复 | 潜在崩溃 |
| **L2** | CSV 无原子写入 | csv_exporter.py | 89-146 | 低 | 待修复 | 文件损坏 |
| **L3** | 颜色生成可能冲突 | video_canvas.py | 219-226 | 低 | 待修复 | 难以区分 |

---

## 五、改进建议

### 5.1 架构改进

#### 建议 1: 实现后台工作线程
```
现状:
  GUI 主线程 → Pipeline.process_frame() → 阻塞

目标:
  GUI 主线程 ←→ 信号/槽 ←→ DetectionWorker(QThread)
                                        ↓
                                  Pipeline.process_frame()
```

**涉及的文件**:
- `src/gui/workers/detection_worker.py` (新建)
- `src/gui/main_window.py` (修改)

#### 建议 2: 引入服务层抽象
```
新增接口:
  - PipelineService: 封装 Pipeline 操作
  - ConfigService: 配置管理和热更新
  - TrajectoryService: 轨迹数据访问

GUI 只通过 Service 层访问核心功能
```

**涉及的文件**:
- `src/gui/services/pipeline_service.py` (新建)
- `src/gui/services/config_service.py` (新建)
- `src/gui/main_window.py` (修改)

#### 建议 3: 完善 MVC 分层
```
Model 层:
  - TrackingModel: 跟踪状态
  - ConfigModel: 配置状态

View 层:
  - VideoCanvas, TrajectoryList, LogPanel

Controller 层:
  - DetectionController: 检测流程控制
  - PlaybackController: 播放控制
```

### 5.2 功能改进

#### 改进 1: 摄像头索引选择
- **当前**: 固定使用摄像头 0
- **目标**: 支持多摄像头选择
- **方案**: 添加摄像头枚举和选择 UI

#### 改进 2: 参数实时生效
- **当前**: 参数变更需重启
- **目标**: 实时更新 Pipeline 配置
- **方案**: 实现 `config_changed` 信号处理

#### 改进 3: 异常恢复机制
- **当前**: 异常时直接崩溃
- **目标**: 自动恢复或降级运行
- **方案**: 添加异常捕获和重试逻辑

---

## 六、代码关系图

### 6.1 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUI 层                                   │
│  main_window.py ───────────────────────────────────────────────┐│
│       │                                                         ││
│       ├── video_canvas.py ─────────────────────────────────────┤│
│       ├── trajectory_list.py ──────────────────────────────────┤│
│       └── log_panel.py ────────────────────────────────────────┤│
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
                              │                                    │
                              ▼                                    │
┌─────────────────────────────────────────────────────────────────┐│
│                         核心层                                   ││
│  pipeline.py ───────────────────────────────────────────────────┤│
│       │                                                         ││
│       ├── detector.py (PersonDetector - 当前未被直接使用)        ││
│       └── tracker.py (PersonTracker / YOLOTrackerWrapper)       ││
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
                              │                                    │
                              ▼                                    │
┌─────────────────────────────────────────────────────────────────┐│
│                         数据层                                   ││
│  types.py (BoundingBox, Detection, TrackedObject, Frame)        ││
│  loader.py (VideoLoader, VideoWriter)                           ││
│  trajectory.py (TrajectoryManager)                              ││
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
                              │                                    │
                              ▼                                    │
┌─────────────────────────────────────────────────────────────────┐│
│                       基础设施层                                 ││
│  config.py (Config, DetectorConfig, TrackerConfig...)          ││
│  logger.py (get_logger, setup_logger)                          ││
│  exceptions.py (ModelLoadError, InferenceError...)              ││
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
                                                                   │
┌─────────────────────────────────────────────────────────────────┐│
│                       可视化层                                   ││
│  visualizer.py (Visualizer)                                     ││
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
                                                                   │
┌─────────────────────────────────────────────────────────────────┐│
│                         导出层                                   ││
│  csv_exporter.py (CSVExporter)                                  ││
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 GUI 与核心集成点

```python
# main_window.py 中的关键集成代码

# 1. 延迟初始化 Pipeline
if self._pipeline is None:
    from ..infra.config import load_config
    from ..core.pipeline import TrackingPipeline
    config = load_config()
    self._pipeline = TrackingPipeline(config)
    self._pipeline.warmup()

# 2. 处理摄像头帧
data_frame = DataFrame(
    frame_id=self._frame_count,
    timestamp=timestamp,
    image=frame
)
processed_frame, tracked_objects = self._pipeline.process_frame(data_frame)

# 3. 更新 UI
self._video_canvas.set_frame(processed_frame.image)
self._video_canvas.set_overlay(detections, trajectories, info_text)
```

---

## 七、后续工作建议

### 7.1 短期任务 (1-2 周)

| 任务 | 优先级 | 涉及文件 | 预估工时 |
|------|--------|----------|----------|
| 清理重复导入 | 高 | main_window.py | 0.5h |
| 添加 TrajectoryManager 公开 API | 高 | trajectory.py, main_window.py | 2h |
| 实现摄像头索引选择 | 中 | main_window.py | 2h |
| 添加配置验证和降级 | 中 | config.py | 2h |

### 7.2 中期任务 (2-4 周)

| 任务 | 优先级 | 涉及文件 | 预估工时 |
|------|--------|----------|----------|
| 实现 DetectionWorker (QThread) | 高 | 新建 workers/, main_window.py | 8h |
| 实现 PipelineService | 高 | 新建 services/, main_window.py | 6h |
| 完善 config_changed 信号处理 | 中 | main_window.py, pipeline.py | 4h |
| 添加异常恢复机制 | 中 | main_window.py, pipeline.py | 4h |

### 7.3 长期任务 (4+ 周)

| 任务 | 优先级 | 涉及文件 | 预估工时 |
|------|--------|----------|----------|
| 重构 MVC 分层 | 中 | 整个 GUI 模块 | 16h |
| 统一 Detector/Tracker 接口 | 中 | core/*.py | 8h |
| 添加 GUI 集成测试 | 低 | tests/test_gui/ | 8h |
| 性能优化 (轨迹简化等) | 低 | visualizer.py | 4h |

---

## 八、测试覆盖

### 8.1 现有测试 (tests/)

| 测试文件 | 测试数量 | 覆盖内容 |
|----------|----------|----------|
| test_types.py | ~15 | BoundingBox, Detection, TrackedObject, Frame, Trajectory |
| test_config.py | ~10 | Config 加载/保存 |
| test_trajectory.py | ~12 | TrajectoryManager |
| test_csv_exporter.py | ~7 | CSVExporter |

### 8.2 缺失测试

- GUI 组件测试
- Pipeline 集成测试
- 端到端流程测试
- 性能基准测试

---

## 九、环境与依赖

### 9.1 核心依赖 (requirements.txt)
```
ultralytics>=8.3.0
opencv-python>=4.8.0
numpy>=1.24.0
pydantic>=2.0.0
pyyaml>=6.0
loguru>=0.7.0
pytest>=8.0.0
pytest-cov>=4.0.0
```

### 9.2 GUI 依赖 (requirements-gui.txt)
```
PySide6>=6.5.0
opencv-python>=4.8.0
numpy>=1.24.0
```

### 9.3 系统要求
- Python 3.10+
- CUDA 兼容 GPU (可选)
- 摄像头设备 (可选)

---

## 十、附录

### 10.1 启动方式

**CLI 方式**:
```bash
cd person_tracking
python -m src.main --source video.mp4 --output output/tracked.mp4
python -m src.main --source 0 --show  # 摄像头实时检测
```

**GUI 方式**:
```bash
cd person_tracking
python -m src.gui.app
```

**Python API**:
```python
from src import run_tracking
from src.gui import run_gui

# CLI API
stats = run_tracking(source="video.mp4", output="output.mp4")

# GUI API
run_gui()
```

### 10.2 配置示例 (config/default.yaml)

```yaml
detector:
  model_path: "yolo11n.pt"
  confidence_threshold: 0.5
  device: "cuda"

tracker:
  tracker_type: "bytetrack"
  track_buffer: 30

visualizer:
  trajectory_length: 50
  show_center_point: true

pipeline:
  warmup: true
  save_output: true
```

### 10.3 关键接口定义

```python
# Pipeline 核心接口
class TrackingPipeline:
    def process_frame(self, frame: Frame) -> tuple[Frame, list[TrackedObject]]
    def run(self, source, output_path, csv_path, show, progress_callback) -> dict
    def get_metrics(self) -> PerformanceMetrics

# GUI 核心接口
class MainWindow(QMainWindow):
    # 信号
    video_source_selected = Signal(str)
    start_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    config_changed = Signal(dict)
    
    # 方法
    def _on_open_camera() -> None
    def _update_camera_frame() -> None
    def _show_idle_screen() -> None
```

---

## 十一、交接检查清单

在开始新对话前，请确认：

- [ ] 已理解五层架构设计
- [ ] 已理解数据流和模块依赖关系
- [ ] 已理解 GUI 与核心的集成方式
- [ ] 已理解已发现的问题和优先级
- [ ] 已理解改进建议和涉及文件
- [ ] 已理解后续工作计划

---

*文档版本: 1.0*  
*创建时间: 2026-04-12*  
*用途: 跨对话传递项目完整状态*
