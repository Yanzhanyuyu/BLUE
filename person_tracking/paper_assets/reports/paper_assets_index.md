# 论文素材索引报告

## 实验环境

**日期**: 2026-04-25

**项目**: BLUE - 人物检测跟踪系统

**位置**: `C:\Users\YanYu\Desktop\data\BLUE\person_tracking`

**系统**:
- 操作系统: Windows
- Python版本: 3.13.11
- GPU: CUDA可用
- 模型: YOLOv11n
- 跟踪器: ByteTrack

## 测试视频

### 视频来源

1. **single_person.mp4**
   - 位置: `C:\Users\YanYu\Desktop\data\BLUE\input\single_person.mp4`
   - 分辨率: 1440x2560
   - 帧率: 23.98
   - 时长: 12.51秒
   - 帧数: 300
   - 用途: 单人检测与跟踪实验

2. **multi_person.mp4**
   - 位置: `C:\Users\YanYu\Desktop\data\BLUE\input\multi_person.mp4`
   - 分辨率: 1920x1080
   - 帧率: 25.00
   - 时长: 60.00秒
   - 帧数: 1500
   - 用途: 多人检测与跟踪实验

3. **occlusion.mp4**
   - 位置: `C:\Users\YanYu\Desktop\data\BLUE\input\occlusion.mp4`
   - 分辨率: 1920x1080
   - 帧率: 25.00
   - 时长: 15.72秒
   - 帧数: 393
   - 用途: 遮挡与ID保持实验

4. **camera_test**
   - 来源: 摄像头索引0
   - 用途: 摄像头实时测试
   - 状态: 已跳过（需要手动交互）

## CSV文件

### 原始CSV文件

1. **single_person_tracks.csv**
   - 位置: `paper_assets/raw/csv/single_person_tracks.csv`
   - 行数: 279
   - 字段: track_id, frame_id, timestamp, x, y, w, h, confidence, class_name
   - 说明: 单人视频的跟踪结果

2. **multi_person_tracks.csv**
   - 位置: `paper_assets/raw/csv/multi_person_tracks.csv`
   - 行数: 10,124
   - 字段: track_id, frame_id, timestamp, x, y, w, h, confidence, class_name
   - 说明: 多人视频的跟踪结果

3. **occlusion_tracks.csv**
   - 位置: `paper_assets/raw/csv/occlusion_tracks.csv`
   - 行数: 951
   - 字段: track_id, frame_id, timestamp, x, y, w, h, confidence, class_name
   - 说明: 遮挡视频的跟踪结果

4. **video_info.csv**
   - 位置: `paper_assets/raw/video_info.csv`
   - 说明: 测试视频的基本信息

### 汇总CSV文件

1. **performance_summary.csv**
   - 位置: `paper_assets/tables/performance_summary.csv`
   - 说明: 所有视频的性能指标汇总
   - 字段: video_name, total_frames, avg_fps, avg_processing_time_ms, total_detections, total_unique_tracks, avg_confidence等

2. **tracking_summary.csv**
   - 位置: `paper_assets/tables/tracking_summary.csv`
   - 说明: 所有视频的跟踪结果汇总
   - 字段: video_name, total_detections, total_unique_tracks, avg_confidence, track_length_avg_frames, possible_id_switch_count等

## 图片

### 样本帧

1. **single_person_1.png**
   - 位置: `paper_assets/processed/frames/single_person_1.png`
   - 说明: 单人视频早期帧（10%）
   - 论文位置: 图5.1 实验测试场景样例

2. **single_person_2.png**
   - 位置: `paper_assets/processed/frames/single_person_2.png`
   - 说明: 单人视频中期帧（50%）
   - 论文位置: 图4.2 YOLOv11人物检测效果示例

3. **single_person_3.png**
   - 位置: `paper_assets/processed/frames/single_person_3.png`
   - 说明: 单人视频后期帧（90%）
   - 论文位置: 图4.4 人物运动轨迹可视化效果

4. **multi_person_1.png**
   - 位置: `paper_assets/processed/frames/multi_person_1.png`
   - 说明: 多人检测帧（25%）
   - 论文位置: 图5.2 不同场景下的人物检测效果

5. **multi_person_2.png**
   - 位置: `paper_assets/processed/frames/multi_person_2.png`
   - 说明: 稳定跟踪帧（50%）
   - 论文位置: 图4.3 ByteTrack多目标跟踪效果示例

6. **multi_person_tracking_sequence.png**
   - 位置: `paper_assets/processed/frames/multi_person_tracking_sequence.png`
   - 说明: 显示ID连续性的三帧
   - 论文位置: 图5.3 多目标跟踪连续帧效果

7. **occlusion_1.png**
   - 位置: `paper_assets/processed/frames/occlusion_1.png`
   - 说明: 遮挡前（20%）
   - 论文位置: 图5.4 人物轨迹定位结果

8. **occlusion_2.png**
   - 位置: `paper_assets/processed/frames/occlusion_2.png`
   - 说明: 遮挡中（50%）
   - 论文位置: 图5.6 典型误差案例分析

9. **occlusion_3.png**
   - 位置: `paper_assets/processed/frames/occlusion_3.png`
   - 说明: 遮挡后（80%）
   - 论文位置: 图5.6 典型误差案例分析

### 统计图

1. **fps_comparison.png**
   - 位置: `paper_assets/figures/chapter5/fps_comparison.png`
   - 说明: 不同测试场景的平均FPS对比
   - 论文位置: 图5.5 不同测试场景下系统实时性对比

2. **processing_time_comparison.png**
   - 位置: `paper_assets/figures/chapter5/processing_time_comparison.png`
   - 说明: 不同测试场景的平均处理时间对比
   - 论文位置: 表5.2 系统实时性测试结果

3. **person_count_over_time_multi.png**
   - 位置: `paper_assets/figures/chapter5/person_count_over_time_multi.png`
   - 说明: 多人场景中的人数随时间变化
   - 论文位置: 图5.3 多目标跟踪连续帧效果

4. **confidence_distribution.png**
   - 位置: `paper_assets/figures/chapter5/confidence_distribution.png`
   - 说明: 所有视频的检测置信度分布
   - 论文位置: 表5.4 检测与跟踪结果统计表

5. **trajectory_example.png**
   - 位置: `paper_assets/figures/chapter5/trajectory_example.png`
   - 说明: 轨迹可视化示例
   - 论文位置: 图4.4 人物运动轨迹可视化效果

6. **resource_usage.png**
   - 位置: `paper_assets/figures/chapter5/resource_usage.png`
   - 说明: 不同测试场景的系统资源使用
   - 论文位置: 表5.3 系统资源占用统计

## 表格

1. **system_environment.csv**
   - 位置: `paper_assets/tables/system_environment.csv`
   - 说明: 系统开发与测试环境
   - 论文位置: 表4.1 系统开发与测试环境

2. **key_parameters.csv**
   - 位置: `paper_assets/tables/key_parameters.csv`
   - 说明: 系统关键参数设置
   - 论文位置: 表4.3 系统关键参数设置

3. **csv_field_description.csv**
   - 位置: `paper_assets/tables/csv_field_description.csv`
   - 说明: CSV字段说明
   - 论文位置: 表4.2 跟踪结果CSV字段说明

4. **experiment_video_info.csv**
   - 位置: `paper_assets/tables/experiment_video_info.csv`
   - 说明: 实验视频基本信息
   - 论文位置: 表5.1 实验测试视频基本信息表

5. **performance_summary.csv**
   - 位置: `paper_assets/tables/performance_summary.csv`
   - 说明: 系统实时性测试结果
   - 论文位置: 表5.2 系统实时性测试结果

6. **tracking_summary.csv**
   - 位置: `paper_assets/tables/tracking_summary.csv`
   - 说明: 检测与跟踪结果统计
   - 论文位置: 表5.4 检测与跟踪结果统计表

## 数据真实性

### 真实数据来源

本报告中的所有数据都是**100%真实的**，来源于：

1. **真实视频处理**: 所有跟踪结果都来自实际视频处理运行
2. **真实CSV导出**: 所有CSV文件都由系统的CSVExporter生成
3. **真实性能指标**: 所有性能数据都从实际运行中收集
4. **真实截图**: 所有图像都从实际跟踪结果视频中提取

### 无伪造数据

- 无合成或伪造数据
- 无手动编辑跟踪结果
- 无人工性能指标
- 无生成或模拟统计数据

## 无法直接计算的指标

### 标准MOT指标

以下指标**无法计算**，需要人工标注数据：

1. **精确度（Precision）**: 需要真实边界框标注
2. **召回率（Recall）**: 需要真实边界框标注
3. **mAP（平均精度）**: 需要真实标注
4. **MOTA（多目标跟踪准确度）**: 需要真实轨迹标注
5. **IDF1（身份F1分数）**: 需要真实身份分配

### ID切换检测

当前的ID切换检测使用**启发式规则**，**不等同于**标准MOT指标：

- **规则1**: 同一目标在相邻帧中消失并以不同ID重新出现
- **规则2**: 消失和重新出现之间的时间间隔短
- **规则3**: 空间邻近性

**注意**: 这是一个估计值，可能不准确。对于精确的ID切换指标，需要真实标注数据。

## 标准MOT指标的要求

要计算标准MOT指标（Precision、Recall、mAP、MOTA、IDF1），需要以下真实标注数据：

1. **边界框标注**: 每一帧的所有人员的真实边界框
2. **身份分配**: 每个边界框的正确人员身份
3. **遮挡标签**: 每一帧中哪些人员被遮挡
4. **帧级标注**: 视频中所有帧的完整标注

**格式**: 标准MOTChallenge格式（MOT16、MOT17、MOT20）或类似格式。

## 项目功能一致性

### 已确认功能

1. ✅ **CLI视频输出**: CLI支持`--output`参数进行视频导出
2. ✅ **CLI CSV导出**: CLI支持`--csv`参数进行CSV导出
3. ✅ **CSV稳定导出**: CSVExporter使用原子写入机制
4. ✅ **参数热更新**: GUI支持实时参数更新
5. ✅ **性能指标**: MetricsCollector提供统一的性能计算

### 已知限制

1. **摄像头视频导出**: 摄像头测试需要手动交互（按'q'退出）
2. **trajectory_stats.json**: 系统当前未导出
3. **GUI视频导出**: GUI视频导出已禁用（如README中所述）

### 论文描述一致性

以下论文描述应根据实际结果**验证**：

1. **实时性能**: 验证FPS值是否与声称的性能匹配
2. **跟踪准确度**: 验证ID切换计数是否与声称的准确度匹配
3. **检测置信度**: 验证置信度分布是否与声称的性能匹配
4. **资源使用**: 验证资源使用是否与声称的效率匹配

## 创建的脚本

所有脚本位于`paper_assets/scripts/`：

1. **collect_video_info.py**: 收集视频基本信息
2. **collect_performance.py**: 收集性能数据
3. **update_performance.py**: 使用日志数据更新性能汇总
4. **analyze_tracking_results.py**: 分析跟踪结果
5. **export_sample_frames.py**: 为论文导出样本帧
6. **generate_paper_figures.py**: 生成统计图
7. **generate_paper_tables.py**: 生成论文表格

## 总结

本报告提供了为论文生成的所有论文素材的综合索引。所有数据都是真实的，来自实际实验。系统功能完整，已准备好进行论文数据收集。

**生成的资产总数**:
- CSV文件: 8
- PNG图像: 15
- 报告: 4
- 脚本: 7

**所有资产都准备好用于论文。**
