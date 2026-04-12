# GUI 设计方案传递文档

> 本文档用于跨对话传递 GUI 设计方案，便于在新会话中继续开发实现。

---

## 一、任务背景

### 项目信息
- **项目名称**：基于 YOLOv11 与 ByteTrack 的人员检测跟踪系统
- **当前状态**：已完成核心检测跟踪功能，具备 CLI 入口
- **新需求**：设计并实现 PySide6 桌面 GUI

### 设计目标
打造一个"人员检测跟踪可视化分析平台 / 智能视觉实验台"，既适合日常调试，也适合毕业设计展示与答辩演示。

### 核心原则
1. GUI 层与核心算法层解耦
2. 不破坏现有项目目录结构
3. 复用已有配置、日志、异常处理、轨迹管理和导出能力
4. 界面文案以中文为主
5. 视觉风格偏深色科技风

---

## 二、架构设计

### 2.1 四层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PySide6 GUI 应用层                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │   Views     │  │ Controllers │  │  Services   │  │  Workers  │  │
│  │  (视图层)   │◄─│  (控制层)   │◄─│  (服务层)   │◄─│ (工作线程)│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         核心算法层（不修改）                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ core/pipeline.py - TrackingPipeline                         │   │
│  │  ├── __init__(config: Config)                               │   │
│  │  ├── process_frame(frame) → (Frame, list[TrackedObject])    │   │
│  │  ├── run(source, output_path, csv_path, ...)               │   │
│  │  └── get_metrics() → PerformanceMetrics                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                       数据与基础设施层（不修改）                       │
│  config.py │ logger.py │ exceptions.py │ loader.py │ visualizer.py │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 目录 | 职责 |
|-----|------|------|
| **View 层** | `views/` | 纯 UI 渲染，不包含业务逻辑 |
| **Controller 层** | `controllers/` | 连接 View 与 Service，处理 UI 事件 |
| **Service 层** | `services/` | 封装对核心 pipeline/config/logger 的调用 |
| **Worker 层** | `workers/` | 后台线程执行耗时操作 |

### 2.3 线程设计

**主线程职责**：
- 所有 UI 渲染和事件处理
- 接收 Worker 信号并更新界面
- 用户交互响应

**工作线程职责**：
- 视频帧读取和预解码
- 模型推理和跟踪计算
- 轨迹更新和可视化渲染
- CSV 日志写入

### 2.4 核心信号定义

```python
# Worker -> 主线程的信号
frame_ready = Signal(np.ndarray, list)      # 处理完成的帧 + 跟踪对象
progress_updated = Signal(int, int)          # 当前进度
status_changed = Signal(str)                 # 状态变更
error_occurred = Signal(str, str)            # 错误类型 + 详情
metrics_updated = Signal(dict)               # 性能指标

# 主线程 -> Worker 的控制信号
start_requested = Signal()
stop_requested = Signal()
pause_requested = Signal()
config_changed = Signal(dict)
```

---

## 三、页面设计

### 3.1 页面清单

| 页面 | 文件 | 功能描述 |
|-----|------|---------|
| 首页 | `home_page.py` | 快速启动、最近使用、系统状态 |
| 实时检测页 | `detection_page.py` | 三栏布局：左参数/中视频/右状态 |
| 参数配置页 | `config_page.py` | 完整配置管理，支持导入导出 |
| 历史回放页 | `replay_page.py` | 回放已处理视频，分析历史轨迹 |
| 结果分析页 | `analysis_page.py` | 统计分析检测跟踪结果 |
| 日志与异常页 | `log_page.py` | 系统日志查看和异常追踪 |

### 3.2 实时检测页布局

```
┌─────────────────────────────────────────────────────────────────────┐
│ 菜单栏: [文件] [编辑] [视图] [工具] [帮助]                           │
├─────────────────────────────────────────────────────────────────────┤
│ 工具栏: [打开视频] [打开摄像头] [开始] [暂停] [停止] [导出] [设置]   │
├───────────────┬─────────────────────────────────┬───────────────────┤
│ 左侧参数区    │     中间视频显示区              │ 右侧状态区        │
│ ┌───────────┐ │ ┌─────────────────────────────┐ │ ┌───────────────┐ │
│ │ 视频源    │ │ │                             │ │ │ 统计信息      │ │
│ │ - 源类型  │ │ │   ┌─────────────┐           │ │ │ 当前帧: 1254  │ │
│ │ - 路径    │ │ │   │ ID:5 0.92   │           │ │ │ FPS: 28.5     │ │
│ ├───────────┤ │ │   └─────────────┘           │ │ │ 检测数: 3     │ │
│ │ 检测参数  │ │ │   ┌───────────────┐         │ │ ├───────────────┤ │
│ │ - 置信度  │ │ │   │ ID:12 0.87    │         │ │ │ 目标列表      │ │
│ │ - IOU     │ │ │   └───────────────┘         │ │ │ ID│置信│位置 │ │
│ │ - 设备    │ │ │                             │ │ │ 5 │0.92│...  │ │
│ ├───────────┤ │ │   ●━━━●━━━●━━━●             │ │ │12 │0.87│...  │ │
│ │ 跟踪参数  │ │ │   轨迹线                    │ │ │23 │0.78│...  │ │
│ │ - 类型    │ │ │                             │ │ ├───────────────┤ │
│ │ - 缓冲    │ │ │   视频画面区域              │ │ │ 轨迹历史      │ │
│ ├───────────┤ │ │                             │ │ │ 选择ID: [5▼]  │ │
│ │ 可视化    │ │ │                             │ │ │ 点数: 152     │ │
│ │ ☑ 边框   │ │ │                             │ │ │ 持续: 5.2s    │ │
│ │ ☑ 轨迹   │ │ │                             │ │ ├───────────────┤ │
│ │ ☑ ID标签 │ │ └─────────────────────────────┘ │ │ 日志面板      │ │
│ ├───────────┤ │ Frame: 1254 | FPS: 28.5       │ │ │ [INFO] ...    │ │
│ │ 导出设置  │ │ Persons: 3 | 2024-01-15       │ │ │ [DEBUG] ...   │ │
│ │ ☑ 保存   │ │                                 │ │ └───────────────┘ │
│ └───────────┘ │                                 │                   │
├───────────────┴─────────────────────────────────┴───────────────────┤
│ 播放控制: ▶ [播放] ▮▮ [暂停] ■ [停止] ═══════○────────── 00:00/01:30 │
├─────────────────────────────────────────────────────────────────────┤
│ 状态栏: 状态: ● 运行中 │ FPS: 28.5 │ 检测数: 3 │ 轨迹: 5 │ GPU: CUDA │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 四、核心组件清单

### 4.1 组件分类

| 类别 | 组件 | 文件 | 职责 |
|-----|------|------|------|
| **容器组件** | MainWindow | `main_window.py` | 主窗口容器 |
| | CentralWidget | `main_window.py` | 中央布局容器 |
| **显示组件** | VideoCanvas | `video_canvas.py` | 视频画面显示 |
| | OverlayLayer | `overlay_layer.py` | 检测框/轨迹叠加 |
| | InfoOverlay | `overlay_layer.py` | 帧信息叠加 |
| **参数组件** | SourcePanel | `param_panel.py` | 视频源选择 |
| | DetectorPanel | `param_panel.py` | 检测参数配置 |
| | TrackerPanel | `param_panel.py` | 跟踪参数配置 |
| | VisualizerPanel | `param_panel.py` | 可视化参数配置 |
| | ExportPanel | `param_panel.py` | 导出设置配置 |
| **状态组件** | StatsCard | `stats_card.py` | 统计卡片 |
| | TargetTable | `target_table.py` | 目标列表表格 |
| | TrajectoryList | `trajectory_list.py` | 轨迹历史列表 |
| | LogPanel | `log_panel.py` | 日志显示面板 |
| **控制组件** | PlaybackControls | `playback_controls.py` | 播放控制栏 |
| | StatusBar | `status_bar.py` | 状态栏 |
| | MainToolBar | `tool_bar.py` | 工具栏 |
| | MenuBar | `menu_bar.py` | 菜单栏 |

### 4.2 组件协作关系

```
MainWindow
├── MenuBar
│   └── FileMenu, EditMenu, ViewMenu, ToolsMenu, HelpMenu
├── MainToolBar
│   └── SourceBtn, StartBtn, PauseBtn, StopBtn, ExportBtn, SettingsBtn
├── CentralWidget (三栏布局)
│   ├── LeftPanel
│   │   └── SourcePanel, DetectorPanel, TrackerPanel, VisualizerPanel, ExportPanel
│   ├── CentralArea
│   │   └── VideoCanvas
│   │       └── OverlayLayer (BBoxes, Trajectories, Labels)
│   └── RightPanel
│       └── StatsCard, TargetTable, TrajectoryList, LogPanel
├── PlaybackControls
│   └── PlayBtn, PauseBtn, StopBtn, ProgressBar, TimeDisplay
└── StatusBar
    └── StatusLabel, FPSLabel, CountLabel, TrajectoryLabel, GPULabel
```

---

## 五、状态管理

### 5.1 系统状态定义

| 状态 | 标识 | 颜色 | 状态栏提示 | 可用操作 |
|-----|------|------|-----------|---------|
| 未加载 | UNLOADED | 灰色 ● | 状态: 未加载 | 打开视频、配置设置 |
| 已加载 | LOADED | 蓝色 ● | 状态: 已就绪 | 开始、配置设置 |
| 正在运行 | RUNNING | 绿色 ● | 状态: 运行中 | 暂停、停止 |
| 已暂停 | PAUSED | 黄色 ● | 状态: 已暂停 | 继续、停止 |
| 已停止 | STOPPED | 灰色 ● | 状态: 已停止 | 重新开始、导出 |
| 导出中 | EXPORTING | 蓝色 ◐ | 状态: 导出中... | 取消导出 |
| 导出完成 | EXPORTED | 绿色 ✓ | 状态: 导出完成 | 打开目录、关闭 |
| 推理失败 | ERROR_INFERENCE | 红色 ✕ | 状态: 推理失败 | 重试、查看日志 |
| 视频源错误 | ERROR_VIDEO | 红色 ✕ | 状态: 视频源错误 | 重选视频、查看日志 |
| 模型错误 | ERROR_MODEL | 红色 ✕ | 状态: 模型错误 | 重选模型、查看日志 |
| 参数错误 | ERROR_CONFIG | 红色 ✕ | 状态: 参数错误 | 修改参数、恢复默认 |

### 5.2 状态转换图

```
UNLOADED ──打开视频──> LOADED ──点击开始──> RUNNING
                                              │
                      ┌───────────────────────┤
                      │                       │
                      ▼                       ▼
                   PAUSED <───点击暂停───  (处理完成)
                      │                       │
                      │                       ▼
                      └───点击停止──────> STOPPED
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                         ▼                    ▼                    ▼
                    EXPORTING            重新开始              关闭
                         │                    │
                         ▼                    ▼
                    EXPORTED            ──> LOADED

错误分支 (任意状态可转入):
ERROR_MODEL / ERROR_VIDEO / ERROR_INFERENCE / ERROR_CONFIG
         │
         ▼
    显示错误对话框 ──> 重试 / 查看日志
```

---

## 六、开发迭代计划

### 6.1 三阶段规划

```
第一阶段 (Week 1-2)          第二阶段 (Week 3-4)          第三阶段 (Week 5-6)
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│ 最小可运行版本    │       │ 完善配置与工程    │       │ 增强分析与展示    │
│                   │       │                   │       │                   │
│ • 基础窗口框架    │       │ • 配置管理页      │       │ • 结果分析页      │
│ • 视频源选择      │       │ • 配置导入导出    │       │ • 历史回放功能    │
│ • 实时检测页框架  │       │ • 参数实时生效    │       │ • 轨迹可视化分析  │
│ • 视频画布显示    │       │ • 异常提示完善    │       │ • 统计图表        │
│ • 基础检测流程    │       │ • 日志面板        │       │ • 报告导出        │
│ • 目标列表展示    │       │ • 状态管理完善    │       │ • 演示模式        │
│ • 播放控制基础    │       │ • 参数面板完善    │       │ • 截图/录屏       │
│                   │       │                   │       │                   │
│ 里程碑: 可演示    │       │ 里程碑: 可配置    │       │ 里程碑: 可交付    │
└───────────────────┘       └───────────────────┘       └───────────────────┘
```

### 6.2 第一阶段详细任务清单

| 序号 | 任务 | 组件/模块 | 依赖 | 验收标准 | 预计工时 |
|-----|------|----------|------|---------|---------|
| 1.1 | 创建主窗口框架 | MainWindow | 无 | 窗口可显示，包含菜单栏、工具栏、状态栏占位 | 2h |
| 1.2 | 实现三栏布局 | CentralWidget | 1.1 | 左侧参数区、中间视频区、右侧状态区布局正确 | 2h |
| 1.3 | 实现视频画布组件 | VideoCanvas | 1.2 | 可显示OpenCV图像，支持缩放 | 3h |
| 1.4 | 实现叠加层渲染 | OverlayLayer | 1.3 | 可绘制检测框、ID标签、轨迹线 | 4h |
| 1.5 | 创建PipelineService | PipelineService | 无 | 可初始化TrackingPipeline，封装核心接口 | 3h |
| 1.6 | 创建ConfigService | ConfigService | 无 | 可读取默认配置，提供参数访问接口 | 2h |
| 1.7 | 创建DetectionWorker | DetectionWorker | 1.5 | 后台线程可执行帧处理，通过信号返回结果 | 4h |
| 1.8 | 实现开始/暂停/停止控制 | PlaybackController | 1.7 | 可控制处理流程启停 | 3h |
| 1.9 | 实现目标列表组件 | TargetTable | 1.2 | 可显示当前帧检测目标，实时更新 | 2h |
| 1.10 | 实现统计卡片 | StatsCard | 1.2 | 可显示FPS、检测数等关键指标 | 1h |
| 1.11 | 实现状态栏 | StatusBar | 1.1 | 显示状态、FPS、进度等信息 | 1h |
| 1.12 | 实现视频源选择 | SourceDialog | 无 | 可选择本地文件或摄像头 | 2h |
| 1.13 | 实现播放控制栏 | PlaybackControls | 1.2 | 播放/暂停/停止按钮，进度条 | 2h |
| 1.14 | 集成配置系统 | 整体 | 1.6 | 参数面板可读取并显示当前配置 | 2h |
| 1.15 | 端到端测试 | 整体系统 | 1.1-1.14 | 可打开视频并实时检测显示 | 3h |

**第一阶段总工时预估**：约 36 小时（约 5 个工作日）

---

## 七、项目目录结构

### 7.1 新增 GUI 目录结构

```
person_tracking/
├── src/
│   ├── main.py                 # CLI入口（保留）
│   │
│   ├── gui/                    # 【新增】GUI模块根目录
│   │   ├── __init__.py
│   │   ├── main_window.py      # 主窗口
│   │   ├── app.py              # QApplication封装
│   │   │
│   │   ├── views/              # 视图层
│   │   │   ├── __init__.py
│   │   │   ├── home_page.py    # 首页/启动页
│   │   │   ├── detection_page.py   # 实时检测页
│   │   │   ├── config_page.py  # 参数配置页
│   │   │   ├── replay_page.py  # 历史回放页
│   │   │   ├── analysis_page.py    # 结果分析页
│   │   │   └── log_page.py     # 日志与异常页
│   │   │
│   │   ├── widgets/            # 可复用组件
│   │   │   ├── __init__.py
│   │   │   ├── video_canvas.py # 视频画布组件
│   │   │   ├── overlay_layer.py    # 叠加层组件
│   │   │   ├── target_table.py # 目标列表组件
│   │   │   ├── trajectory_list.py  # 轨迹列表组件
│   │   │   ├── log_panel.py    # 日志面板组件
│   │   │   ├── stats_card.py   # 统计卡片组件
│   │   │   ├── param_panel.py  # 参数面板基类
│   │   │   └── playback_controls.py
│   │   │
│   │   ├── dialogs/            # 对话框
│   │   │   ├── __init__.py
│   │   │   ├── source_dialog.py    # 视频源选择
│   │   │   ├── export_dialog.py    # 导出配置
│   │   │   └── error_dialog.py # 错误提示
│   │   │
│   │   ├── controllers/        # 控制层
│   │   │   ├── __init__.py
│   │   │   ├── main_controller.py
│   │   │   ├── detection_controller.py
│   │   │   └── playback_controller.py
│   │   │
│   │   ├── services/           # 服务层
│   │   │   ├── __init__.py
│   │   │   ├── pipeline_service.py # Pipeline封装
│   │   │   ├── config_service.py   # 配置管理
│   │   │   ├── logger_service.py   # 日志服务
│   │   │   └── export_service.py   # 导出服务
│   │   │
│   │   ├── workers/            # 工作线程
│   │   │   ├── __init__.py
│   │   │   ├── detection_worker.py
│   │   │   ├── export_worker.py
│   │   │   └── base_worker.py
│   │   │
│   │   ├── models/             # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── target_model.py
│   │   │   ├── trajectory_model.py
│   │   │   └── log_model.py
│   │   │
│   │   └── resources/          # 资源文件
│   │       ├── styles/
│   │       │   └── dark.qss    # 深色主题
│   │       └── icons/
│   │
│   ├── core/                   # 核心算法层（保留，不修改）
│   ├── data/                   # 数据层（保留，不修改）
│   ├── infra/                  # 基础设施层（保留，不修改）
│   ├── viz/                    # 可视化层（保留，不修改）
│   └── export/                 # 导出层（保留，不修改）
│
├── tests/
│   └── test_gui/               # 【新增】GUI测试
│
├── config/
│   └── demo.yaml               # 【新增】演示配置
│
└── requirements-gui.txt        # 【新增】GUI专用依赖
```

### 7.2 新增依赖文件

**requirements-gui.txt**:
```
PySide6>=6.5.0
opencv-python>=4.8.0
numpy>=1.24.0
```

---

## 八、后续编码建议

### 8.1 开发顺序

**优先级从高到低**：

1. **静态界面框架**（先不连接后端）
   - MainWindow 骨架
   - CentralWidget 三栏布局
   - VideoCanvas 占位
   - LeftPanel/RightPanel 占位

2. **核心组件原型**
   - VideoCanvas（使用Mock数据测试）
   - OverlayLayer（绘制固定矩形框测试）
   - TargetTable（显示Mock数据）

3. **服务层集成**
   - PipelineService（封装现有Pipeline）
   - ConfigService（读取默认配置）
   - LoggerService（集成现有Logger）

4. **Worker线程**
   - DetectionWorker（后台执行Pipeline.process_frame）
   - 信号槽连接测试

5. **控制逻辑**
   - PlaybackController
   - 状态管理

6. **联调测试**
   - 端到端流程测试

### 8.2 Mock数据联调示例

```python
class MockDetectionWorker(QObject):
    """模拟检测Worker，用于前端开发阶段"""
    frame_ready = Signal(np.ndarray, list)
    progress_updated = Signal(int, int)
    
    def __init__(self):
        super().__init__()
        self._running = False
        self._frame_id = 0
    
    def start(self):
        self._running = True
        self._frame_id = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._generate_mock_frame)
        self._timer.start(33)  # ~30 FPS
    
    def _generate_mock_frame(self):
        if not self._running:
            return
        
        # 生成Mock帧
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # 生成Mock检测
        mock_objects = [
            MockTrackedObject(track_id=1, bbox=BoundingBox(100, 100, 50, 80, 0.95)),
            MockTrackedObject(track_id=2, bbox=BoundingBox(300, 200, 60, 90, 0.87))
        ]
        
        self.frame_ready.emit(frame, mock_objects)
        self.progress_updated.emit(self._frame_id, 1000)
        self._frame_id += 1
```

### 8.3 接入真实Pipeline时机

**切换时机判断**：
- ✓ 静态界面完成
- ✓ Mock数据联调通过
- ✓ 信号槽连接稳定
- ✓ 状态管理验证完成

**接入步骤**：
1. 替换MockDetectionWorker为真实DetectionWorker
2. 初始化PipelineService，加载Config
3. 连接真实Worker信号到界面
4. 验证帧处理流程
5. 测试异常处理

---

## 九、视觉设计规范

### 9.1 配色方案

| 用途 | 颜色代码 | 说明 |
|-----|---------|------|
| 背景深 | #1E1E1E | 主背景色 |
| 背景中 | #2D2D30 | 面板背景 |
| 背景浅 | #3E3E42 | 悬停背景 |
| 边框 | #4E4E52 | 分割线 |
| 主强调 | #007ACC | 按钮、高亮 |
| 成功 | #4EC9B0 | 运行状态 |
| 警告 | #DC8C6A | 暂停状态 |
| 错误 | #CE9178 | 错误状态 |
| 标题文字 | #FFFFFF | 标题 |
| 正文文字 | #D4D4D4 | 正文 |
| 次要文字 | #808080 | 提示 |

### 9.2 中文文案风格

| 元素类型 | 风格 | 示例 |
|---------|------|------|
| 菜单项 | 简洁动词 | 文件、编辑、视图 |
| 按钮 | 动作动词 | 开始、暂停、导出 |
| 标签 | 名词短语 | 检测参数、跟踪设置 |
| 提示 | 完整句子 | 请选择视频文件 |
| 错误 | 问题+建议 | 模型加载失败，请检查路径 |
| 状态 | 状态描述 | 正在处理帧 1254/15000 |

---

## 十、关键接口定义

### 10.1 PipelineService 接口

```python
class PipelineService:
    """Pipeline封装服务"""
    
    def __init__(self, config: Config):
        """初始化服务"""
        pass
    
    def initialize(self) -> None:
        """初始化Pipeline"""
        pass
    
    def process_frame(self, frame: np.ndarray) -> tuple[Frame, list[TrackedObject]]:
        """处理单帧"""
        pass
    
    def get_metrics(self) -> PerformanceMetrics:
        """获取性能指标"""
        pass
    
    def get_trajectories(self) -> dict[int, Trajectory]:
        """获取所有轨迹"""
        pass
    
    def cleanup(self) -> None:
        """清理资源"""
        pass
```

### 10.2 ConfigService 接口

```python
class ConfigService:
    """配置管理服务"""
    
    def __init__(self):
        """初始化服务"""
        pass
    
    def load(self, path: str | Path | None = None) -> Config:
        """加载配置"""
        pass
    
    def save(self, config: Config, path: str | Path) -> None:
        """保存配置"""
        pass
    
    def get_detector_config(self) -> DetectorConfig:
        """获取检测器配置"""
        pass
    
    def get_tracker_config(self) -> TrackerConfig:
        """获取跟踪器配置"""
        pass
    
    def get_visualizer_config(self) -> VisualizerConfig:
        """获取可视化配置"""
        pass
    
    def update_detector_config(self, **kwargs) -> None:
        """更新检测器配置"""
        pass
    
    def validate(self, config: Config) -> bool:
        """验证配置"""
        pass
```

---

## 十一、传递检查清单

在开始新对话前，请确认以下内容：

- [ ] 已理解四层架构设计
- [ ] 已理解线程模型和信号槽机制
- [ ] 已理解6个页面的布局和功能
- [ ] 已理解核心组件职责和协作关系
- [ ] 已理解11种系统状态及转换
- [ ] 已理解三阶段开发计划
- [ ] 已理解项目目录结构
- [ ] 已理解后续编码顺序

---

*文档版本: 1.0*
*创建时间: 2026-04-12*
*用途: 跨对话传递 GUI 设计方案*
