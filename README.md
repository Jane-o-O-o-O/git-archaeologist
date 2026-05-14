# 🏺 Git Archaeologist

**Git 仓库考古分析工具 — 挖掘代码历史，洞察仓库演变。**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ 功能

### 基础分析
- **📊 仓库统计** — commit 数、贡献者数、增删行数、活跃天数
- **👤 贡献者排行** — 按 commit 数排序，含增删行数、涉及文件、最后活跃时间
- **🔥 热点文件** — 被修改最多的文件，支持 glob 模式过滤
- **📅 活跃度趋势** — 按日/周/月/年统计 commit 活跃度
- **📁 文件类型分布** — 按扩展名统计变更分布
- **📋 一站式概览** — `summary` 命令汇总所有关键数据

### 高级分析
- **🔗 文件耦合分析** — 找出经常一起被修改的文件对（co-change detection）
- **🚌 Bus Factor** — 关键人员依赖度分析，按文件或目录粒度
- **🔄 Churn 分析** — 高变动率文件，识别反复重写的代码
- **📂 目录级统计** — 按目录聚合变更、贡献者、文件数
- **🕰️ 文件年龄分析** — 最陈旧/最早出现/最活跃的文件排序
- **🗓️ Commit 热力图** — 按星期×小时分析提交活跃模式
- **🏥 健康评分** — Bus Factor/Churn/Activity/Diversity 四维评估
- **💬 Commit 消息分析** — conventional commits 检测、消息质量统计

### v0.6.0 新增
- **🔍 代码归属分析** — 基于 git blame 查看每行代码的作者归属
- **📈 复杂度趋势** — 追踪 LOC、文件数随时间的变化趋势
- **⚖️ 时段对比** — 比较两个时间段的指标变化，识别新增/离开贡献者

### v0.7.0 新增
- **🏷️ 标签/版本列表** — 列出仓库标签及关联 commit，支持 annotated/lightweight 标签
- **📜 文件修改历史** — 查看指定文件的 commit 变更记录
- **🔍 Commit 消息搜索** — 正则表达式搜索 commit 消息
- **📈 贡献者时间线** — 按时间维度统计贡献者数量变化、新增贡献者
- **📅 Activity 增强** — 新增 `--filter-path` 和 `--filter-author` 过滤选项
- **🌐 HTML 报告增强** — 健康评分、Churn、Bus Factor、耦合分析、热力图 5 个新章节

### v0.8.0 新增
- **🤝 贡献者协作网络** — 分析哪些作者经常修改相同文件，发现协作模式
- **📤 全命令 `--output`** — 所有 24 个子命令均支持 `-o` 输出到文件
- **📝 Markdown 格式补全** — `health` 和 `commit-messages` 命令新增 `--format markdown`

### 输出
- **🌐 HTML 报告** — 暗色主题的可浏览完整分析报告
- **📋 终端表格** — Rich 美化输出
- **📄 JSON** — 所有命令支持 `--format json` 管道输出
- **📊 CSV / Markdown** — 所有命令支持 `--format csv` 和 `--format markdown`
- **📁 文件输出** — 所有命令支持 `--output` / `-o` 写入文件
- **🐍 Python API** — `GitArchaeologist` 统一入口类

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/Jane-o-O-o-O/git-archaeologist.git
cd git-archaeologist
pip install -e .
```

### CLI 使用

```bash
# 查看版本
git-archaeologist --version

# 仓库总体统计
git-archaeologist stats

# 一站式仓库概览
git-archaeologist summary

# 贡献者排行
git-archaeologist authors --top 10

# 热点文件分析
git-archaeologist hotspots --ignore "*.lock" --ignore "node_modules/*"

# 活跃度趋势
git-archaeologist activity --period month

# 文件类型分布
git-archaeologist filetypes --top 10

# Commit 热力图（星期 × 小时）
git-archaeologist heatmap

# 文件耦合分析（经常一起修改的文件对）
git-archaeologist coupling --min-co-change 3 --top 10

# Bus Factor — 关键人员依赖度
git-archaeologist busfactor --entity file
git-archaeologist busfactor --entity dir

# Churn 分析 — 高变动率文件
git-archaeologist churn --top 10

# 目录级统计
git-archaeologist dirs --top 10

# 文件年龄分析
git-archaeologist ages --sort stale --top 20

# 代码归属分析（git blame）
git-archaeologist blame --top 20

# 复杂度趋势
git-archaeologist complexity --period month

# 时段对比
git-archaeologist diff \
    --a-since 2024-01-01 --a-until 2024-06-30 \
    --b-since 2024-07-01 --b-until 2024-12-31

# 健康评分
git-archaeologist health

# Commit 消息分析
git-archaeologist commit-messages

# v0.7.0 新增命令

# 标签/版本列表
git-archaeologist tags

# 文件修改历史
git-archaeologist file-history src/main.py

# 搜索 commit 消息（支持正则）
git-archaeologist search "feat!?:"
git-archaeologist search "fix.*bug" --since 6m

# 贡献者时间线
git-archaeologist contributors-timeline --period month

# 活跃度趋势（带过滤）
git-archaeologist activity --filter-author "Alice"
git-archaeologist activity --filter-path "src/api.py"

# 生成 HTML 报告（含健康评分、Churn、Bus Factor、耦合、热力图）
git-archaeologist report -o report.html

# 贡献者协作网络
git-archaeologist contributors-network --top 10
git-archaeologist contributors-network --min-shared 3 --format json

# 输出到文件（所有命令支持 -o）
git-archaeologist stats --format json -o stats.json
git-archaeologist authors --format csv -o authors.csv
git-archaeologist health --format markdown -o health.md
```

### Python API

```python
from git_archaeologist import GitArchaeologist

arch = GitArchaeologist("/path/to/repo")
summary = arch.summary()
print(summary.stats.total_commits)

# 底层分析器
analyzer = arch.analyzer
coupling = analyzer.coupling(top_n=10)
bus_factor = analyzer.bus_factor(entity="dir")
churn = analyzer.churn(top_n=10)

# 代码归属分析
blame = analyzer.blame_analysis(top_n=10)
for entry in blame:
    print(f"{entry.path}: {entry.top_author} ({entry.top_author_pct:.0f}%)")

# 复杂度趋势
trend = analyzer.complexity_trend(period="month")
for point in trend:
    print(f"{point.period}: {point.total_lines} LOC, {point.total_files} files")

# 时段对比
diff = analyzer.period_diff(
    period_a_since=datetime(2024, 1, 1),
    period_a_until=datetime(2024, 6, 30),
    period_b_since=datetime(2024, 7, 1),
    period_b_until=datetime(2024, 12, 31),
)
print(f"Commits: {diff.period_a_commits} → {diff.period_b_commits}")

# Commit 热力图
day_labels, hours, matrix = analyzer.commit_heatmap_matrix()

# 标签列表
tags = analyzer.list_tags()
for t in tags:
    print(f"{t.name}: {t.commit_date}")

# 文件修改历史
history = analyzer.file_history("src/main.py", max_count=10)

# 搜索 commit 消息
results = analyzer.search_messages(r"feat!?:")
for r in results:
    print(f"{r.sha[:12]}: {r.message}")

# 贡献者时间线
timeline = analyzer.contributor_timeline(period="month")
for p in timeline:
    print(f"{p.period}: {p.total_contributors} contributors (+{p.new_contributors} new)")

# 贡献者协作网络
network = analyzer.contributors_network(top_n=10)
for pair in network:
    print(f"{pair.author_a} ↔ {pair.author_b}: {pair.shared_files} 共同文件 ({pair.collaboration_strength:.1%})")

# 文件级 diff 详情
for commit, file_changes in miner.iter_commits_with_details():
    for fc in file_changes:
        print(f"{fc.path}: +{fc.insertions} -{fc.deletions}")
```

---

## 📁 项目结构

```
src/git_archaeologist/
├── __init__.py      # 包导出
├── git_mining.py    # Git 采矿引擎 — commit 遍历、数据提取、文件级 diff
├── analyzer.py      # 核心分析引擎 — 统计、热点、耦合、Bus Factor、Churn、热力图、blame、复杂度
├── core.py          # 统一 API 入口类 (GitArchaeologist)
├── report.py        # HTML 报告生成器
└── cli.py           # CLI 子命令（24 个）
```

---

## 📜 License

MIT
