# Git Archaeologist 🔍⛏️

Git 仓库考古工具 —— 深入挖掘仓库的历史地层，发现隐藏的开发故事。

## 功能特性

- 📊 仓库总览：年龄、提交频率、贡献者统计
- 🦴 文件化石：长期未被修改的"活化石"文件
- 👤 贡献者化石：早已离开项目的历史贡献者
- 🔀 文件血统追踪：追踪文件的重命名和移动历史
- 📈 提交活跃期分析：发现开发的"地质年代"
- 🏷️ 提交信息模式检测

## 安装

```bash
pip install git-archaeologist
```

## 使用

```bash
# 挖掘当前仓库
git-archaeologist excavate .

# 查找长期未修改的文件化石
git-archaeologist fossils . --age 365

# 追踪文件血统
git-archaeologist lineage path/to/file.py

# 贡献者分析
git-archaeologist contributors .

# 活跃期分析
git-archaeologist strata .
```

## 开发

```bash
python -m pytest tests/ -v
```
