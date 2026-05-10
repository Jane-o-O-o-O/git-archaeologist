"""地层分析模块 —— 分析开发活跃期的'地质年代'"""
from dataclasses import dataclass
from datetime import datetime

from git_archaeologist.utils import parse_git_date


@dataclass
class Stratum:
    """开发活跃期（地层）"""
    start_date: datetime
    end_date: datetime
    commit_count: int
    contributor_count: int
    contributors: list[str]


def analyze_strata(repo, gap_days: int = 14) -> list[Stratum]:
    """分析仓库的开发活跃期

    将提交历史按时间间隔分成多个"地层"，
    间隔超过 gap_days 天的提交被视为不同地层。

    Args:
        repo: Repo 对象
        gap_days: 分层间隔天数，默认 14 天

    Returns:
        地层列表，按时间从早到晚排序
    """
    commits = _get_commits_with_dates(repo)
    if not commits:
        return []

    # 按时间排序
    commits.sort(key=lambda c: c["date"])

    # 分层
    strata = []
    current_batch = [commits[0]]

    for commit in commits[1:]:
        gap = (commit["date"] - current_batch[-1]["date"]).days
        if gap >= gap_days:
            strata.append(_build_stratum(current_batch))
            current_batch = [commit]
        else:
            current_batch.append(commit)

    # 最后一批
    if current_batch:
        strata.append(_build_stratum(current_batch))

    return strata


def _get_commits_with_dates(repo) -> list[dict]:
    """获取所有提交及其日期和作者"""
    result = repo.run_git(["log", "--format=%aI|%aN <%aE>"])
    if not result or not result.strip():
        return []

    commits = []
    for line in result.strip().split("\n"):
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        date_str, author = parts
        dt = parse_git_date(date_str)
        if dt is not None:
            commits.append({"date": dt, "author": author})

    return commits


def _build_stratum(commits: list[dict]) -> Stratum:
    """从一批提交构建地层对象"""
    authors = list(dict.fromkeys(c["author"] for c in commits))
    return Stratum(
        start_date=commits[0]["date"],
        end_date=commits[-1]["date"],
        commit_count=len(commits),
        contributor_count=len(authors),
        contributors=authors,
    )
