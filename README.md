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

### 输出
- **🌐 HTML 报告** — 暗色主题的可浏览完整分析报告
- **📋 终端表格** — Rich 美化输出
- **📄 JSON** — 所有命令支持 `--format json` 管道输出
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

# 生成 HTML 报告
git-archaeologist report -o report.html
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

# Commit 热力图
day_labels, hours, matrix = analyzer.commit_heatmap_matrix()

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
├── analyzer.py      # 核心分析引擎 — 统计、热点、耦合、Bus Factor、Churn、热力图
├── core.py          # 统一 API 入口类 (GitArchaeologist)
├── report.py        # HTML 报告生成器
└── cli.py           # CLI 子命令（13 个）
```

---

## 📜 License

MIT
