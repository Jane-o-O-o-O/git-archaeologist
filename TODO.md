# TODO - 2026-05-11 开发计划

## 目标：热点文件分析 + 贡献者统计

### 1. 实现 hotspot 模块 (hotspots.py)
- 数据结构：HotspotFile (path, modification_count, unique_authors, first_seen, last_modified)
- 核心函数：find_hotspots(repo, top_n=20) → 按修改次数排序的热点文件
- 使用 `git log --format=COMMIT --name-only` 统计每个文件的修改频率

### 2. 实现 authors 模块 (authors.py)  
- 数据结构：AuthorStats (name, email, commit_count, first_commit, last_commit, files_touched, lines_added, lines_removed)
- 核心函数：get_author_stats(repo) → 按提交数排序的贡献者统计
- 使用 `git log --format --numstat` 获取每次提交的增删行数

### 3. CLI 集成
- 添加 `hotspots` 子命令 (top_n 参数)
- 添加 `authors` 子命令
- 更新 excavate 报告，加入热点文件和贡献者统计

### 4. 测试
- test_hotspots.py - 热点文件分析测试
- test_authors.py - 贡献者统计测试

### 5. 提交 & 推送
