"""核心分析引擎 — commit 统计、热点文件、贡献者活跃度。"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from git_archaeologist.git_mining import CommitInfo, GitMiner


@dataclass
class RepoStats:
    """仓库总体统计。"""

    total_commits: int = 0
    total_authors: int = 0
    total_files_changed: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    first_commit_date: datetime | None = None
    last_commit_date: datetime | None = None
    active_days: int = 0
    avg_commits_per_day: float = 0.0


@dataclass
class AuthorStats:
    """单个贡献者的统计。"""

    name: str
    email: str
    commit_count: int = 0
    insertions: int = 0
    deletions: int = 0
    files_touched: set[str] = field(default_factory=set)
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    avg_insertions_per_commit: float = 0.0

    @property
    def churn(self) -> int:
        """代码搅动量（insertions + deletions）。"""
        return self.insertions + self.deletions


@dataclass
class HotspotFile:
    """热点文件信息。"""

    path: str
    change_count: int = 0
    insertions: int = 0
    deletions: int = 0
    authors: set[str] = field(default_factory=set)
    last_modified: datetime | None = None


class Analyzer:
    """仓库分析器。"""

    def __init__(self, repo_path: str = ".") -> None:
        self.miner = GitMiner(repo_path)

    def repo_stats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        path: str | None = None,
    ) -> RepoStats:
        """计算仓库总体统计。"""
        commits = list(self.miner.iter_commits(since=since, until=until, author=author, path=path))
        if not commits:
            return RepoStats()

        all_files: set[str] = set()
        authors: set[str] = set()
        days: set[str] = set()
        total_ins = 0
        total_del = 0

        for c in commits:
            all_files.update(c.files_changed)
            authors.add(f"{c.author_name} <{c.author_email}>")
            days.add(c.authored_date.strftime("%Y-%m-%d"))
            total_ins += c.insertions
            total_del += c.deletions

        dates = sorted(c.authored_date for c in commits)
        span_days = max((dates[-1] - dates[0]).days, 1)

        return RepoStats(
            total_commits=len(commits),
            total_authors=len(authors),
            total_files_changed=len(all_files),
            total_insertions=total_ins,
            total_deletions=total_del,
            first_commit_date=dates[0],
            last_commit_date=dates[-1],
            active_days=len(days),
            avg_commits_per_day=round(len(commits) / span_days, 2),
        )

    def author_stats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
    ) -> list[AuthorStats]:
        """统计每个贡献者的活动。"""
        authors: dict[str, AuthorStats] = {}

        for c in self.miner.iter_commits(since=since, until=until):
            key = f"{c.author_name} <{c.author_email}>"
            if key not in authors:
                authors[key] = AuthorStats(name=c.author_name, email=c.author_email)
            a = authors[key]
            a.commit_count += 1
            a.insertions += c.insertions
            a.deletions += c.deletions
            a.files_touched.update(c.files_changed)
            if a.first_commit is None or c.authored_date < a.first_commit:
                a.first_commit = c.authored_date
            if a.last_commit is None or c.authored_date > a.last_commit:
                a.last_commit = c.authored_date

        result = sorted(authors.values(), key=lambda a: a.commit_count, reverse=True)[:top_n]
        for a in result:
            if a.commit_count > 0:
                a.avg_insertions_per_commit = round(a.insertions / a.commit_count, 1)
        return result

    def hotspots(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        ignore_globs: list[str] | None = None,
    ) -> list[HotspotFile]:
        """分析热点文件 — 被修改次数最多的文件。"""
        import fnmatch

        files: dict[str, HotspotFile] = {}

        for c in self.miner.iter_commits(since=since, until=until):
            for fname in c.files_changed:
                # 过滤忽略的文件
                if ignore_globs and any(
                    fnmatch.fnmatch(fname, g) for g in ignore_globs
                ):
                    continue
                if fname not in files:
                    files[fname] = HotspotFile(path=fname)
                f = files[fname]
                f.change_count += 1
                f.insertions += c.insertions
                f.deletions += c.deletions
                f.authors.add(c.author_name)
                if f.last_modified is None or c.authored_date > f.last_modified:
                    f.last_modified = c.authored_date

        result = sorted(files.values(), key=lambda f: f.change_count, reverse=True)[:top_n]
        return result

    def commit_activity_by_period(
        self,
        period: str = "month",
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, int]:
        """按时间段统计 commit 活跃度。

        Args:
            period: "day", "week", "month", "year"
        """
        counter: Counter[str] = Counter()
        for c in self.miner.iter_commits(since=since, until=until):
            if period == "day":
                key = c.authored_date.strftime("%Y-%m-%d")
            elif period == "week":
                key = c.authored_date.strftime("%Y-W%W")
            elif period == "month":
                key = c.authored_date.strftime("%Y-%m")
            elif period == "year":
                key = c.authored_date.strftime("%Y")
            else:
                key = c.authored_date.strftime("%Y-%m")
            counter[key] += 1
        return dict(sorted(counter.items()))
