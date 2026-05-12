"""提交频率时间线分析模块 —— 按时间粒度统计提交活动"""
from dataclasses import dataclass
from datetime import datetime

from git_archaeologist.utils import parse_git_date


@dataclass
class TimelinePeriod:
    """时间线中的一个时间段"""
    period: str
    commit_count: int
    contributor_count: int
    files_changed: int
    lines_added: int
    lines_removed: int


def analyze_timeline(repo, granularity: str = "month") -> list[TimelinePeriod]:
    """分析提交频率时间线

    按 day/week/month 粒度统计每个时间段的提交活动。

    Args:
        repo: Repo 对象
        granularity: 时间粒度, "day", "week", 或 "month"

    Returns:
        时间段列表，按时间从早到晚排列
    """
    commits = _get_commits_with_stats(repo)
    if not commits:
        return []

    # 按时间排序
    commits.sort(key=lambda c: c["date"])

    # 按粒度分桶
    buckets: dict[str, list] = {}
    for c in commits:
        key = _date_to_period_key(c["date"], granularity)
        buckets.setdefault(key, []).append(c)

    # 构建结果
    result = []
    for period_key in sorted(buckets.keys()):
        bucket = buckets[period_key]
        authors = set()
        total_files = 0
        total_added = 0
        total_removed = 0
        for c in bucket:
            authors.add(c["author"])
            total_files += c["files_changed"]
            total_added += c["lines_added"]
            total_removed += c["lines_removed"]

        result.append(TimelinePeriod(
            period=period_key,
            commit_count=len(bucket),
            contributor_count=len(authors),
            files_changed=total_files,
            lines_added=total_added,
            lines_removed=total_removed,
        ))

    return result


def _date_to_period_key(dt: datetime, granularity: str) -> str:
    """将日期转换为时间段标识"""
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    elif granularity == "week":
        # ISO 周: YYYY-Wnn
        iso_year, iso_week, _ = dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    else:  # month
        return dt.strftime("%Y-%m")


def _get_commits_with_stats(repo) -> list[dict]:
    """获取所有提交的统计信息

    Returns:
        list[dict]: 每个 dict 包含 date, author, files_changed, lines_added, lines_removed
    """
    result = repo.run_git([
        "log", "--format=COMMIT|%aI|%aN", "--shortstat"
    ])
    if not result or not result.strip():
        return []

    commits = []
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
            # shortstat 行: "X files changed, Y insertions(+), Z deletions(-)"
            files_changed, added, removed = _parse_shortstat(line)
            if current_date and current_author:
                commits.append({
                    "date": current_date,
                    "author": current_author,
                    "files_changed": files_changed,
                    "lines_added": added,
                    "lines_removed": removed,
                })
                current_date = None
                current_author = None

    return commits


def _parse_shortstat(line: str) -> tuple[int, int, int]:
    """解析 git --shortstat 输出

    例: "3 files changed, 100 insertions(+), 50 deletions(-)"
    返回: (3, 100, 50)
    """
    files_changed = 0
    lines_added = 0
    lines_removed = 0

    parts = line.split(",")
    for part in parts:
        part = part.strip()
        if "file" in part:
            try:
                files_changed = int(part.split()[0])
            except (ValueError, IndexError):
                pass
        elif "insertion" in part:
            try:
                lines_added = int(part.split()[0])
            except (ValueError, IndexError):
                pass
        elif "deletion" in part:
            try:
                lines_removed = int(part.split()[0])
            except (ValueError, IndexError):
                pass

    return files_changed, lines_added, lines_removed
