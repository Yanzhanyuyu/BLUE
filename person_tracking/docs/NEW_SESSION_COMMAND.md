# 新对话启动命令

## 方式一：直接粘贴启动命令

复制以下内容到新对话中：

```
请基于已完成的 GUI 设计方案，开始第一阶段的代码实现。

设计文档位置：person_tracking/docs/GUI_DESIGN_HANDOFF.md

请按以下顺序开始编码：
1. 首先创建 GUI 目录结构
2. 实现 MainWindow 主窗口框架
3. 实现 VideoCanvas 视频画布组件（先用 Mock 数据）
4. 实现三栏布局（左参数区、中视频区、右状态区）

请先输出代码，然后逐个组件实现。
```

## 方式二：使用 Handoff 命令

在新对话中执行：

```
/handoff
```

然后选择 `person_tracking/docs/GUI_DESIGN_HANDOFF.md` 文件。

## 方式三：完整任务描述

复制以下完整内容到新对话：

---

**任务背景**：

我有一个"基于 YOLOv11 与 ByteTrack 的人员检测跟踪系统"，已完成核心检测跟踪功能。现在需要为其设计并实现 PySide6 桌面 GUI。

**已完成工作**：

已完成完整的 GUI 设计方案，文档位于：
- `person_tracking/docs/GUI_DESIGN_HANDOFF.md`

**当前任务**：

请基于设计文档，开始第一阶段的代码实现：

1. **创建 GUI 目录结构**
   - 按照 `src/gui/` 目录结构创建所有必要目录

2. **实现 MainWindow 主窗口框架**
   - 包含菜单栏、工具栏、状态栏占位
   - 三栏布局（左参数区、中视频区、右状态区）

3. **实现 VideoCanvas 视频画布组件**
   - 使用 Mock 数据测试
   - 支持图像显示和缩放

4. **实现基础参数面板**
   - 左侧参数区的基础布局
   - 使用 Mock 数据填充

**实现约束**：
- 使用 Python + PySide6
- 界面文案使用中文
- 代码结构清晰，模块职责单一
- 先实现静态界面，后接入真实 Pipeline
- 使用深色科技风主题

**验收标准**：
- GUI 应用可启动并显示主窗口
- 三栏布局正确显示
- 视频画布可显示 Mock 数据
- 参数面板可显示基础配置项

请开始编码实现。

---

## 验证文档是否正确

在开始新对话前，可以执行以下命令验证：

```bash
# 检查文档是否存在
ls person_tracking/docs/GUI_DESIGN_HANDOFF.md

# 查看文档内容
cat person_tracking/docs/GUI_DESIGN_HANDOFF.md
```

---

*创建时间: 2026-04-12*
