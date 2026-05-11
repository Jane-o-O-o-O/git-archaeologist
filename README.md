# 🏺 Git Archaeologist

**Git 仓库考古分析工具 — 挖掘代码历史，洞察仓库演变。**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ 功能

- **📊 仓库统计** — commit 数、贡献者数、增删行数、活跃天数
- **👤 贡献者排行** — 按 commit 数排序，含增删行数、涉及文件、最后活跃时间
- **🔥 热点文件** — 被修改最多的文件，支持 glob 模式过滤
- **📅 活跃度趋势** — 按日/周/月/年统计 commit 活跃度
- **📁 文件类型分布** — 按扩展名统计变更分布
- **🌐 HTML 报告** — 生成可浏览的完整分析报告
- **🐍 Python API** — `GitArchaeologist` 统一入口类，方便编程调用

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

# 贡献者排行
git-archaeologist authors --top 10

# 热点文件分析
git-archaeologist hotspots --ignore "*.lock" --ignore "node_modules/*"

# 活跃度趋势
git-archaeologist activity --period month

# 文件类型分布
git-archaeologist filetypes --top 10

# 生成 HTML 报告
git-archaeologist report -o report.html

# 时间范围过滤（支持绝对日期和相对时间）
git-archaeologist stats --since 2024-01-01
git-archaeologist authors --since 6m
git-archaeologist hotspots --since 1y

# JSON 输出（方便管道处理）
git-archaeologist stats --format json
git-archaeologist authors --format json
```

### Python API

```python
from git_archaeologist import GitArchaeologist

# 初始化
arch = GitArchaeologist("/path/to/repo")

# 获取综合摘要
summary = arch.summary()
print(f"Commits: {summary.stats.total_commits}")
print(f"Authors: {summary.stats.total_authors}")

# 序列化为 dict（可直接 JSON 化）
data = summary.to_dict()

# 单独分析文件类型
file_types = arch.analyze_file_types()
for ft in file_types[:5]:
    print(f"{ft.extension}: {ft.file_count} files, {ft.total_changes} changes")

# 底层 Analyzer 可直接访问
stats = arch.analyzer.repo_stats()
authors = arch.analyzer.author_stats(top_n=10)
hotspots = arch.analyzer.hotspots(ignore_globs=["*.lock"])
activity = arch.analyzer.commit_activity_by_period(period="month")
```

---

## 🧱 项目结构

```
src/git_archaeologist/
├── __init__.py       # 公开 API 导出
├── core.py           # GitArchaeologist 统一入口 + 文件类型分析
├── git_mining.py     # Git 历史数据提取（GitMiner）
├── analyzer.py       # 统计分析引擎（Analyzer）
├── report.py         # HTML 报告生成器
└── cli.py            # CLI 子命令（stats/authors/hotspots/activity/filetypes/report）
```

---

## 🧪 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 带覆盖率
pytest --cov=git_archaeologist --cov-report=term-missing

# Lint
ruff check .
ruff format .
```

---

## 📝 License

MIT License — 详见 [LICENSE](LICENSE)

---

## 🤝 贡献

欢迎贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。
