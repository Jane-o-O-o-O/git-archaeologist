# Changelog

本文件记录 git-archaeologist 的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [1.2.0] - 2026-05-15

### 新增
- **🕰️ 陈旧分支检测**：`stale-branches` 子命令找出长期未更新的分支，支持 `--days` 自定义阈值
- **📊 标签间统计**：`tag-stats` 子命令分析相邻标签之间的变更统计（发布分析），含 commits/增删行/文件数/作者数
- **🔍 Commit 详情**：`inspect` 子命令详细分析单个 commit，含文件级 diff、父 commit、完整消息
- **📏 最大文件**：`largest` 子命令查找仓库中行数最多的文件，支持 `--top` 限制数量

### 改进
- Analyzer 类新增 4 个分析方法：`stale_branches`、`tag_stats`、`commit_detail`、`largest_files`
- 新增 4 个数据类：`StaleBranch`、`TagStatsEntry`、`CommitDetail`、`LargestFile`
- 从 333 个测试增至 381 个，全部通过

## [1.1.0] - 2026-05-15

### 新增
- **🤖 CI/CD 集成命令**：`ci` 子命令支持 `--min-health-score` 阈值检查，不达标时退出码为 1
- **🚫 全局 --exclude 过滤**：`hotspots`、`coupling`、`busfactor`、`churn`、`dirs` 均支持 `--exclude` glob 排除模式
- **🔀 --sort 排序选项**：`hotspots`（changes/name/insertions/deletions）、`coupling`（strength/count/name）、`busfactor`（risk/changes/name/contributors）、`churn`（ratio/changes/name/insertions）
- **🌿 --branch 分支分析**：全局 `--branch` 选项，分析指定分支而非默认 HEAD
- **🔇 --no-color 选项**：全局 `--no-color` 禁用彩色输出，适合 CI 和脚本环境

### 改进
- Analyzer 类所有文件分析方法统一支持 `exclude_globs` 参数
- GitMiner 支持 `branch` 参数，可遍历指定分支的 commit 历史
- 从 313 个测试增至 333 个，全部通过

## [1.0.0] - 2026-05-15

### 新增
- **`python -m git_archaeologist` 支持**：新增 `__main__.py`，可直接通过 `python -m` 运行
- **PEP 561 类型标记**：新增 `py.typed` 标记文件，支持类型检查工具发现类型信息
- **HTML 报告版本号动态化**：报告页脚版本号从硬编码改为使用 `__version__`

### 修复
- **HTML 报告版本号错误**：修复报告页脚始终显示 "v0.7.0" 的问题，现使用实际版本号
- **版本号统一为 1.0.0**（pyproject.toml + `__init__.py`）

## [0.9.0] - 2026-05-14

### 新增
- **仓库基本信息** (`repo-info`)：显示 remote URL、HEAD、分支数、标签数、工作区状态
- **分支列表** (`branches`)：列出所有分支，含最后 commit 日期、作者、消息、commit 数
- **RepoInfo / BranchEntry dataclass**：新增两个数据结构用于仓库元数据和分支信息
- **格式统一**：所有 26 个 CLI 子命令均完整支持 `--format table/json/csv/markdown` 四种输出格式
- **`filetypes` 命令 `--output` 支持**：补齐 `--output/-o` 文件输出选项
- **`diff` 命令 `--format markdown`**：时段对比新增 Markdown 格式输出
- **41 个新测试**，总计 305 个测试全部通过

### 改进
- CLI 子命令从 23 个增至 25 个（新增 `repo-info`、`branches`）
- `busfactor`/`churn`/`dirs`/`ages` 命令补齐 csv 和 markdown 格式
- `coupling`/`heatmap`/`summary`/`activity` 命令补齐 markdown 格式
- 版本号统一为 0.9.0（pyproject.toml + __init__.py）

## [0.8.0] - 2026-05-14

### 新增
- **贡献者协作网络** (`contributors-network`)：分析哪些作者经常修改相同文件，发现协作模式，支持 `--min-shared` 过滤
- **CoAuthorPair dataclass**：协作对数据结构，含 `collaboration_strength` 属性（Jaccard 相似度）
- **全命令 `--output` 支持**：所有 24 个 CLI 子命令均支持 `-o` 输出到文件
- **Markdown 格式补全**：`health` 和 `commit-messages` 命令新增 `--format markdown` 输出
- **28 个新测试**，总计 264 个测试全部通过

### 改进
- CLI 子命令从 22 个增至 23 个（新增 `contributors-network`）
- 所有命令的 JSON/CSV 输出统一使用 `_write_output()` 支持文件输出
- 版本号统一为 0.8.0（pyproject.toml + __init__.py）

## [0.7.0] - 2026-05-14

### 新增
- **标签列表** (`tags`)：列出仓库标签/版本，含日期、作者、说明，支持 annotated/lightweight 标签
- **文件修改历史** (`file-history`)：查看指定文件的 commit 变更记录，支持 glob 路径
- **Commit 消息搜索** (`search`)：正则表达式搜索 commit 消息，支持时间过滤
- **贡献者时间线** (`contributors-timeline`)：按时间维度统计贡献者数量变化、新增贡献者
- **Activity 命令增强**：`activity` 新增 `--filter-path` 和 `--filter-author` 过滤选项
- **HTML 报告增强**：新增健康评分、Churn 分析、Bus Factor、文件耦合、Commit 热力图共 5 个章节
- **3 个新 dataclass**：`TagEntry`、`SearchMatch`、`ContributorTimelinePoint`
- **公共选项装饰器**：`time_filter_options`、`format_option`、`output_option` 等复用装饰器
- **51 个新测试**，总计 236 个测试全部通过

### 改进
- 版本号统一为 0.7.0（pyproject.toml + __init__.py）
- CLI 子命令从 18 个增至 22 个
- HTML 报告从 5 个章节扩展到 10 个章节

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
