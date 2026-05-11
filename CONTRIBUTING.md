# Contributing to Git Archaeologist

感谢你对 Git Archaeologist 的兴趣！我们欢迎各种形式的贡献。

## 🚀 快速开始

```bash
# Fork 并克隆仓库
git clone https://github.com/your-username/git-archaeologist.git
cd git-archaeologist

# 创建开发环境
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 运行测试
pytest

# 运行 linter
ruff check .
ruff format .
```

## 📋 开发流程

1. **Fork** 仓库
2. 从 `main` 创建特性分支：`git checkout -b feat/your-feature`
3. 编写代码和测试
4. 确保所有测试通过：`pytest`
5. 确保代码符合规范：`ruff check . && ruff format .`
6. 提交更改：`git commit -m 'feat: 添加某功能'`
7. 推送并创建 Pull Request

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_analyzer.py

# 带覆盖率
pytest --cov=git_archaeologist --cov-report=term-missing
```

## 📝 Commit 规范

使用中文 commit message，格式：

```
<类型>: <描述>

feat: 新功能
fix: 修复 bug
docs: 文档更新
test: 测试相关
refactor: 重构
chore: 杂项
```

## 🏗 项目结构

```
src/git_archaeologist/
├── __init__.py       # 公开 API
├── core.py           # GitArchaeologist 统一入口
├── git_mining.py     # Git 历史数据提取
├── analyzer.py       # 统计分析引擎
├── report.py         # HTML 报告生成
└── cli.py            # CLI 子命令
```

## 🐛 报告 Bug

请在 GitHub Issues 中报告，包含：

- Python 版本
- 操作系统
- 复现步骤
- 期望行为 vs 实际行为
- 相关错误日志

## 💡 功能建议

欢迎在 Issues 中提出功能建议！请描述：

- 你的使用场景
- 期望的功能行为
- 是否愿意参与实现
