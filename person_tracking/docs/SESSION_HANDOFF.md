# 会话交接文档 - 工程审计与增量改造

> 文档版本: 1.0  
> 创建日期: 2026-04-14  
> 用途: 记录本轮工程审计、问题修复与测试补充的完整状态

---

## 一、本轮工作概览

### 1.1 审计目标
作为首席架构师完成"理解项目 → 审计问题 → 设计改进 → 实施高价值修复 → 补测试 → 更新文档 → 输出总结"的完整闭环。

### 1.2 完成状态
| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1: 理解项目 | ✅ 完成 | 阅读了所有关键文件，建立心智模型 |
| Phase 2: 审计问题 | ✅ 完成 | 输出差异表和问题清单 |
| Phase 3: 实施修复 | ✅ 完成 | 修复 6 个 P0 问题 |
| Phase 4: 验证 | ✅ 完成 | 65 个测试全部通过 |
| Phase 5: 交付 | ✅ 完成 | 输出完整总结报告 |

---

## 二、已修复的 P0 问题

### 2.1 修复清单

| ID | 问题 | 文件 | 行号 | 修复方式 |
|----|------|------|------|----------|
| P0-1 | `src/__init__.py` 未导出 `run_tracking` | `src/__init__.py` | 全文 | 添加导出和文档 |
| P0-2 | 参数覆盖使用 truthy 判断 | `src/main.py` | 174-178 | 改为 `is not None` |
| P0-3 | GUI 直接访问 `_trajectories` 私有成员 | `src/gui/main_window.py` | 1365 | 使用公开方法 |
| P0-4 | workers.py 同样访问私有成员 | `src/gui/workers.py` | 375 | 使用公开方法 |
| P0-5 | 重复导入 `QActionGroup, QKeySequence, QIcon` | `src/gui/main_window.py` | 44-46 | 合并导入 |
| P0-6 | Pipeline CLI 模式未实现 skip_frames | `src/core/pipeline.py` | 321 | 添加跳帧逻辑 |

### 2.2 修复详情

#### P0-1: API 导出修复
```python
# src/__init__.py - 修复后
from .main import run_tracking

__all__ = ["run_tracking"]
```

#### P0-2: 参数判断修复
```python
# src/main.py - 修复后
# 使用 is not None 判断，支持 confidence=0.0 等边缘值
if model is not None:
    cfg.detector.model_path = model
if device is not None:
    cfg.detector.device = device
if confidence is not None:
    cfg.detector.confidence_threshold = confidence
```

#### P0-3/P0-4: 私有成员访问修复
```python
# src/data/trajectory.py - 新增公开方法
def get_all_recent_points(self, n: int = 50) -> dict[int, list[tuple[float, float, float]]]:
    """获取所有轨迹的最近 N 个点"""
    return {
        track_id: traj.get_recent_points(n)
        for track_id, traj in self._trajectories.items()
    }
```

#### P0-6: skip_frames 实现
```python
# src/core/pipeline.py - 新增跳帧逻辑
frame_counter = 0
skip_frames = self.config.pipeline.skip_frames

for frame in loader:
    frame_counter += 1
    
    # 跳帧逻辑：每 (skip_frames + 1) 帧处理一次
    if skip_frames > 0 and frame_counter % (skip_frames + 1) != 0:
        if writer:
            writer.write(frame.image)
        if progress_callback and total_frames > 0:
            progress_callback(frame.frame_id + 1, total_frames)
        continue
    
    # 处理帧...
```

---

## 三、新增文件与测试

### 3.1 新增文件

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | 项目规则文件，定义架构约束和编码规范 |
| `scripts/verify_api_export.py` | API 导出验证脚本，用于 CI/CD |
| `tests/test_parameter_override.py` | 参数边界值测试（19 个测试） |

### 3.2 新增测试

| 测试文件 | 测试数量 | 覆盖内容 |
|----------|----------|----------|
| `test_parameter_override.py` | 19 | 参数边界值、truthy vs is not None、配置验证 |
| `test_trajectory.py` (新增) | 2 | `get_all_recent_points()` 方法 |

### 3.3 测试状态
```
============================= test session starts =============================
collected 65 items

tests/test_config.py ........... [ 16%]
tests/test_csv_exporter.py ...... [ 26%]
tests/test_parameter_override.py ................... [ 55%]
tests/test_trajectory.py ......... [ 69%]
tests/test_types.py .................... [100%]

============================== 65 passed in 4.00s ==============================
```

---

## 四、文档更新

### 4.1 更新的文件

| 文件 | 更新内容 |
|------|----------|
| `README.md` | 更新测试数量、新增章节 |
| `AGENTS.md` | 新建项目规则文件 |

### 4.2 AGENTS.md 摘要

包含以下内容：
- 项目概述与目录结构
- 构建与测试命令
- 架构约束（禁止访问私有成员等）
- 已知问题与技术债清单
- 编码规范（参数判断、导入规范）
- 配置项生效状态说明
- Agent 工作优先级

---

## 五、仍存在的技术债

### 5.1 P1 级别（需尽快处理）

| ID | 问题 | 文件 | 影响 |
|----|------|------|------|
| P1-1 | Worker 线程未与 MainWindow 集成 | `main_window.py` | GUI 主线程阻塞 |
| P1-2 | 导出功能占位 | `main_window.py:1171` | 功能不完整 |
| P1-3 | `show_progress` 配置冗余 | `config.py`, `pipeline.py` | 配置项无效 |
| P1-4 | `config_changed` 信号未连接 | `main_window.py` | 参数热更新失效 |

### 5.2 P2 级别（计划处理）

| ID | 问题 | 影响 |
|----|------|------|
| P2-1 | GUI 主线程执行推理 | 界面卡顿 |
| P2-2 | BoundingBox 无输入验证 | 潜在崩溃风险 |
| P2-3 | CSV 无原子写入 | 文件损坏风险 |
| P2-4 | Pipeline 直接调用底层模型 | 职责边界不清 |

---

## 六、12 个潜在问题核实结果

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | README/API 与实际代码导出不一致 | ✅ 已修复 | 添加了 `run_tracking` 导出 |
| 2 | 可选参数覆盖时用 truthy 判断 | ✅ 已修复 | 改为 `is not None` |
| 3 | tracker 配置未接线 | ✅ 不成立 | ByteTrack 参数已正确传递 |
| 4 | pipeline 直接调用底层模型 | ⚠️ 设计决策 | 这是故意的设计，非 bug |
| 5 | GUI 在主线程里做推理 | ⚠️ P2 问题 | Worker 已实现但未集成 |
| 6 | GUI 直接访问核心层私有属性 | ✅ 已修复 | 添加了公开方法 |
| 7 | export 功能只是占位提示 | ⚠️ P1 问题 | 需后续实现 |
| 8 | 配置项存在"假参数" | ⚠️ 部分成立 | `show_progress` 未使用 |
| 9 | 日志配置不完整 | ✅ 不成立 | Loguru 配置正确生效 |
| 10 | 测试集中在数据类/工具类 | ⚠️ 部分成立 | 已新增系统行为测试 |
| 11 | 代码中存在 TODO/FIXME | ⚠️ 存在 | 主要是 GUI 相关 |
| 12 | 文档与实际目录不一致 | ✅ 不成立 | 目录结构一致 |

---

## 七、配置项生效状态

| 配置项 | 是否生效 | 说明 |
|--------|----------|------|
| `detector.model_path` | ✅ | 模型加载 |
| `detector.confidence_threshold` | ✅ | 检测阈值 |
| `detector.device` | ✅ | 推理设备 |
| `tracker.track_buffer` | ✅ | 轨迹缓冲 |
| `pipeline.warmup` | ✅ | 模型预热 |
| `pipeline.skip_frames` | ✅ | 跳帧处理（本次新增） |
| `pipeline.save_output` | ✅ | 保存输出 |
| `pipeline.show_progress` | ❌ | 仅作为进度回调参数 |
| `logging.level` | ✅ | 日志级别 |

---

## 八、API 导出验证

### 8.1 验证脚本
```bash
python scripts/verify_api_export.py
```

### 8.2 验证结果
```
============================================================
API 导出验证
============================================================

[1] 验证 src 模块导出...
  ✅ src 模块导出验证通过

[2] 验证 src.gui 模块导出...
  ✅ src.gui 模块导出验证通过

[3] 验证 CLI 入口...
  ✅ CLI 入口验证通过

============================================================
所有验证通过 ✅
============================================================
```

---

## 九、下一阶段路线图

### 9.1 短期（1-2 周）
- [ ] 将 Worker 线程与 MainWindow 集成
- [ ] 实现导出功能完整逻辑
- [ ] 连接 `config_changed` 信号

### 9.2 中期（2-4 周）
- [ ] GUI 架构优化，引入 Service 层
- [ ] 补充 Pipeline 集成测试
- [ ] 添加 GUI smoke test

### 9.3 长期（4+ 周）
- [ ] MVC 分层重构
- [ ] 性能优化（异步处理、帧预解码）
- [ ] 功能扩展（多摄像头支持）

---

## 十、交接检查清单

在开始新会话前，请确认：

- [x] 已理解本轮修复的 6 个 P0 问题
- [x] 已理解新增的测试覆盖
- [x] 已理解配置项生效状态
- [x] 已理解仍存在的技术债
- [x] 已理解 12 个潜在问题的核实结果
- [x] 已理解下一阶段路线图

---

## 十一、关键代码位置

| 功能 | 文件 | 关键行/方法 |
|------|------|-------------|
| CLI 入口 | `src/main.py` | `run_tracking()` |
| API 导出 | `src/__init__.py` | `__all__` |
| 参数覆盖 | `src/main.py:174-180` | CLI 覆盖逻辑 |
| 跳帧处理 | `src/core/pipeline.py:320+` | `run()` 方法 |
| 轨迹公开方法 | `src/data/trajectory.py:119+` | `get_all_recent_points()` |
| API 验证 | `scripts/verify_api_export.py` | 全文件 |

---

*文档版本: 1.0*  
*创建时间: 2026-04-14*  
*用途: 跨会话传递工程审计与增量改造状态*
