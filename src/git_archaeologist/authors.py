"""贡献者统计模块 —— 深度分析每位贡献者的活动"""
from dataclasses import dataclass
from datetime import datetime

from git_archaeologist.utils import parse_git_date


@dataclass
class AuthorStats:
    """贡献者统计数据"""
    name: str
    email: str
    commit_count: int
    first_commit: datetime
    last_commit: datetime
    files_touched: int
    lines_added: int
    lines_removed: int


def get_author_stats(repo) -> list[AuthorStats]:
    """获取仓库中所有贡献者的统计信息

    Args:
        repo: Repo 对象

    Returns:
        贡献者统计列表，按提交数降序排列
    """
    stats = _collect_author_data(repo)
    if not stats:
        return []

    result = []
    for key, data in stats.items():
        name, email = key
        result.append(AuthorStats(
            name=name,
            email=email,
            commit_count=data["commit_count"],
            first_commit=data["first_commit"],
            last_commit=data["last_commit"],
            files_touched=len(data["files"]),
            lines_added=data["lines_added"],
            lines_removed=data["lines_removed"],
        ))

    result.sort(key=lambda a: a.commit_count, reverse=True)
    return result


def _collect_author_data(repo) -> dict:
    """收集每位贡献者的提交数据

    使用 git log --numstat 获取每次提交的增删行数和涉及的文件。

    Returns:
        dict: {(name, email): {"commit_count": int, "first_commit": dt, "last_commit": dt,
                               "files": set, "lines_added": int, "lines_removed": int}}
    """
    result = repo.run_git([
        "log", "--format=COMMIT|%aI|%aN|%aE", "--numstat"
    ])
    if not result or not result.strip():
        return {}

    author_data = {}
    current_name = None
    current_email = None
    current_date = None

    for line in result.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("COMMIT|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                _, date_str, name, email = parts
                dt = parse_git_date(date_str)
                current_name = name
                current_email = email
                current_date = dt

                key = (name, email)
                if key not in author_data:
                    author_data[key] = {
                        "commit_count": 0,
                        "first_commit": dt,
                        "last_commit": dt,
                        "files": set(),
                        "lines_added": 0,
                        "lines_removed": 0,
                    }

                data = author_data[key]
                data["commit_count"] += 1
                if dt:
                    if dt > data["last_commit"]:
                        data["last_commit"] = dt
                    if dt < data["first_commit"]:
                        data["first_commit"] = dt
        else:
            # numstat 行: added\tremoved\tfilepath
            parts = line.split("\t")
            if len(parts) == 3 and current_name and current_email:
                added_str, removed_str, filepath = parts
                key = (current_name, current_email)
                if key in author_data:
                    data = author_data[key]
                    data["files"].add(filepath)
                    try:
                        if added_str != "-":
                            data["lines_added"] += int(added_str)
                        if removed_str != "-":
                            data["lines_removed"] += int(removed_str)
                    except ValueError:
                        pass

    return author_data
