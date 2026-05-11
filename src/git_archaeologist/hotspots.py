"""热点文件分析模块 —— 发现被修改最频繁的文件"""
from dataclasses import dataclass, field
from datetime import datetime

from git_archaeologist.utils import parse_git_date


@dataclass
class HotspotFile:
    """热点文件记录"""
    path: str
    modification_count: int
    unique_authors: int
    first_seen: datetime
    last_modified: datetime


def find_hotspots(repo, top_n: int = 20) -> list[HotspotFile]:
    """分析仓库中的热点文件

    统计每个文件被修改的次数，按修改频率降序排列。

    Args:
        repo: Repo 对象
        top_n: 返回前 N 个热点文件，默认 20

    Returns:
        热点文件列表，按修改次数降序排列
    """
    # 收集每个文件的修改历史
    file_stats = _collect_file_stats(repo)
    if not file_stats:
        return []

    # 构建 HotspotFile 列表
    hotspots = []
    for filepath, stats in file_stats.items():
        hotspots.append(HotspotFile(
            path=filepath,
            modification_count=stats["count"],
            unique_authors=len(stats["authors"]),
            first_seen=stats["first_seen"],
            last_modified=stats["last_modified"],
        ))

    # 按修改次数降序排列
    hotspots.sort(key=lambda h: h.modification_count, reverse=True)
    return hotspots[:top_n]


def _collect_file_stats(repo) -> dict:
    """收集所有文件的修改统计

    使用 git log --name-only 获取每次提交涉及的文件，
    并记录作者和日期。

    Returns:
        dict: {filepath: {"count": int, "authors": set, "first_seen": datetime, "last_modified": datetime}}
    """
    result = repo.run_git([
        "log", "--format=COMMIT|%aI|%aN <%aE>", "--name-only"
    ])
    if not result or not result.strip():
        return {}

    file_stats = {}
    current_date = None
    current_author = None

    for line in result.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("COMMIT|"):
            parts = line.split("|", 2)
            if len(parts) == 3:
                dt = parse_git_date(parts[1])
                current_date = dt
                current_author = parts[2]
        else:
            # 文件路径
            filepath = line
            if current_date is None:
                continue

            if filepath not in file_stats:
                file_stats[filepath] = {
                    "count": 0,
                    "authors": set(),
                    "first_seen": current_date,
                    "last_modified": current_date,
                }

            stats = file_stats[filepath]
            stats["count"] += 1
            if current_author:
                stats["authors"].add(current_author)
            if current_date:
                if current_date > stats["last_modified"]:
                    stats["last_modified"] = current_date
                if current_date < stats["first_seen"]:
                    stats["first_seen"] = current_date

    return file_stats
