# Changelog

本文件记录 git-archaeologist 的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [0.6.0] - 2026-05-13

### 新增
- **代码归属分析** (`blame`)：基于 git blame 查看每行代码的作者归属，识别独占文件
- **复杂度趋势** (`complexity`)：追踪 LOC、文件数随时间的变化趋势，支持 week/month/quarter/year 周期
- **时段对比** (`diff`)：比较两个时间段的指标变化，识别新增/离开贡献者
- **`--version` 标志**：查看当前版本号
- **`--output` / `-o` 选项**：所有新命令支持输出到文件
- **3 个新 dataclass**：`BlameEntry`、`ComplexityPoint`、`PeriodDiff`
- **34 个新测试**，总计 185 个测试全部通过

### 改进
- 版本号统一为 0.6.0（pyproject.toml + __init__.py）
- CLI 子命令从 15 个增至 18 个

## [0.4.0] - 2026-05-12

### 新增
- **commit 热力图**：按星期×小时分析 commit 活跃模式，支持 CLI `heatmap` 命令
- **summary CLI 子命令**：一站式输出仓库全面分析概览
- **文件级 diff 详情**：GitMiner 现在提取每个文件的 insertions/deletions 精确数据
- **精度提升**：churn 和 dir_stats 分析从近似分配改为精确文件级统计

### 修复
- report.py footer 版本号与实际版本一致

## [0.3.0] - 2026-05-12

### 新增
- **文件耦合分析**：co-change detection，Jaccard 相似度计算
- **Bus Factor 分析**：关键人员依赖度，按文件/目录粒度
- **Churn 分析**：高变动率文件识别，反复重写检测
- **目录级统计**：按目录聚合变更、贡献者、文件数
- **文件年龄分析**：陈旧度/最早/活跃排序
- 对应 5 个 CLI 子命令：`coupling`、`busfactor`、`churn`、`dirs`、`ages`
- 43 个新测试

## [0.2.0] - 2026-05-11

### 新增
- 统一 API 入口类 `GitArchaeologist`
- HTML 报告生成器（暗色主题、CSS 图表）
- 文件类型分布分析
- `report` 和 `filetypes` CLI 子命令

## [0.1.0] - 2026-05-11

### 新增
- Git 采矿引擎（commit 遍历、数据提取）
- 仓库总体统计（stats）
- 贡献者排行（authors）
- 热点文件分析（hotspots）
- Commit 活跃度趋势（activity）
- 11 个 CLI 子命令基础框架
- Rich 终端表格输出 + JSON 输出
