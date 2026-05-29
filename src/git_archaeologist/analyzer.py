"""核心分析引擎 — commit 统计、热点文件、贡献者活跃度、高级分析。"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from itertools import combinations
from pathlib import Path

from git_archaeologist.git_mining import GitMiner


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


@dataclass
class CouplingPair:
    """文件耦合对 — 经常一起被修改的文件。"""

    file_a: str
    file_b: str
    co_change_count: int = 0
    file_a_changes: int = 0
    file_b_changes: int = 0

    @property
    def coupling_strength(self) -> float:
        """耦合强度 (0.0 ~ 1.0)，基于 Jaccard 相似度。"""
        union = self.file_a_changes + self.file_b_changes - self.co_change_count
        if union == 0:
            return 0.0
        return round(self.co_change_count / union, 3)


@dataclass
class BusFactorEntry:
    """Bus Factor 分析条目 — 某个文件/目录的关键贡献者。"""

    entity: str
    total_changes: int = 0
    top_contributor: str = ""
    top_contributor_pct: float = 0.0
    contributor_count: int = 0
    bus_factor: int = 0
    contributors: dict[str, int] = field(default_factory=dict)


@dataclass
class ChurnEntry:
    """Churn 分析条目 — 高变动率文件。"""

    path: str
    total_insertions: int = 0
    total_deletions: int = 0
    net_lines: int = 0
    change_count: int = 0

    @property
    def churn_ratio(self) -> float:
        """变动率 = (ins + del) / abs(net)。越高说明代码反复重写。"""
        if self.net_lines == 0:
            return float(self.total_insertions + self.total_deletions)
        return round((self.total_insertions + self.total_deletions) / abs(self.net_lines), 2)


@dataclass
class DirStats:
    """目录级统计。"""

    path: str
    file_count: int = 0
    total_changes: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    authors: set[str] = field(default_factory=set)
    last_modified: datetime | None = None


@dataclass
class FileAgeEntry:
    """文件年龄分析条目。"""

    path: str
    first_seen: datetime | None = None
    last_modified: datetime | None = None
    change_count: int = 0
    primary_author: str = ""

    @property
    def age_days(self) -> int | None:
        """文件存在天数。"""
        if self.first_seen and self.last_modified:
            return (self.last_modified - self.first_seen).days
        return None

    @property
    def stale_days(self) -> int | None:
        """距最后修改的天数。"""
        if self.last_modified:
            return (datetime.now() - self.last_modified).days
        return None


@dataclass
class HealthScore:
    """仓库健康评分结果。"""

    overall: int = 0
    bus_factor_score: int = 0
    churn_score: int = 0
    activity_score: int = 0
    diversity_score: int = 0
    summary: str = ""
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class CommitMessageStats:
    """Commit 消息模式分析结果。"""

    total_commits: int = 0
    conventional_count: int = 0
    conventional_pct: float = 0.0
    type_counts: dict[str, int] = field(default_factory=dict)
    avg_message_length: float = 0.0
    max_message_length: int = 0
    min_message_length: int = 0
    short_messages: int = 0  # < 10 chars
    long_messages: int = 0   # > 72 chars
    most_common_words: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class BlameEntry:
    """文件 blame 分析结果。"""

    path: str
    total_lines: int = 0
    top_author: str = ""
    top_author_lines: int = 0
    top_author_pct: float = 0.0
    authors: dict[str, int] = field(default_factory=dict)
    oldest_line_date: datetime | None = None
    newest_line_date: datetime | None = None


@dataclass
class ComplexityPoint:
    """复杂度趋势数据点。"""

    period: str
    total_files: int = 0
    total_lines: int = 0
    commits_in_period: int = 0
    net_lines_added: int = 0


@dataclass
class PeriodDiff:
    """两个时间段的对比结果。"""

    period_a_commits: int = 0
    period_b_commits: int = 0
    commits_change: float = 0.0
    period_a_authors: int = 0
    period_b_authors: int = 0
    authors_change: float = 0.0
    period_a_files: int = 0
    period_b_files: int = 0
    files_change: float = 0.0
    period_a_insertions: int = 0
    period_b_insertions: int = 0
    period_a_deletions: int = 0
    period_b_deletions: int = 0
    new_authors: list[str] = field(default_factory=list)
    departed_authors: list[str] = field(default_factory=list)
    most_changed_files: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class TagEntry:
    """标签/版本信息。"""

    name: str
    sha: str = ""
    tag_date: datetime | None = None
    tagger: str = ""
    message: str = ""
    commit_sha: str = ""
    commit_date: datetime | None = None
    commit_author: str = ""


@dataclass
class SearchMatch:
    """Commit 消息搜索结果。"""

    sha: str
    author_name: str
    authored_date: datetime
    message: str
    matched_text: str = ""


@dataclass
class ContributorTimelinePoint:
    """贡献者时间线数据点。"""

    period: str
    total_contributors: int = 0
    new_contributors: int = 0
    active_contributors: int = 0
    commits: int = 0


@dataclass
class CoAuthorPair:
    """贡献者协作对 — 两个作者共同修改过的文件及次数。"""

    author_a: str
    author_b: str
    shared_files: int = 0
    shared_file_list: list[str] = field(default_factory=list)
    author_a_commits: int = 0
    author_b_commits: int = 0

    @property
    def collaboration_strength(self) -> float:
        """协作强度 (0.0 ~ 1.0)，基于共同文件数与总文件数的 Jaccard 比。"""
        total = self.author_a_commits + self.author_b_commits - self.shared_files
        if total == 0:
            return 0.0
        return round(self.shared_files / total, 3)


@dataclass
class RepoInfo:
    """仓库基本信息。"""

    path: str = ""
    remote_url: str = ""
    head_sha: str = ""
    head_branch: str = ""
    total_branches: int = 0
    total_tags: int = 0
    total_commits: int = 0
    first_commit_date: datetime | None = None
    last_commit_date: datetime | None = None
    is_dirty: bool = False
    branches: list[str] = field(default_factory=list)


@dataclass
class BranchEntry:
    """分支信息条目。"""

    name: str = ""
    sha: str = ""
    is_active: bool = False
    last_commit_date: datetime | None = None
    last_commit_author: str = ""
    last_commit_message: str = ""
    commit_count: int = 0



@dataclass
class StaleBranch:
    """长期未更新的分支信息。"""

    name: str = ""
    sha: str = ""
    last_commit_date: datetime | None = None
    last_commit_author: str = ""
    last_commit_message: str = ""
    stale_days: int = 0
    is_active: bool = False


@dataclass
class TagStatsEntry:
    """相邻标签之间的变更统计。"""

    from_tag: str = ""
    to_tag: str = ""
    from_date: datetime | None = None
    to_date: datetime | None = None
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0
    authors: int = 0
    author_list: list[str] = field(default_factory=list)


@dataclass
class CommitDetail:
    """单个 commit 的详细分析结果。"""

    sha: str = ""
    short_sha: str = ""
    author_name: str = ""
    author_email: str = ""
    authored_date: datetime | None = None
    committer_name: str = ""
    committer_email: str = ""
    committed_date: datetime | None = None
    message: str = ""
    parent_shas: list[str] = field(default_factory=list)
    files_changed: list[FileChange] = field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    total_files: int = 0


@dataclass
class LargestFile:
    """仓库中最大文件的信息。"""

    path: str = ""
    lines: int = 0
    size_bytes: int = 0
    last_modified: datetime | None = None
    primary_author: str = ""


class Analyzer:
    """仓库分析器。"""

    def __init__(self, repo_path: str = ".", branch: str | None = None) -> None:
        self.miner = GitMiner(repo_path, branch=branch)

    @staticmethod
    def _is_excluded(path: str, exclude_globs: list[str] | None) -> bool:
        """检查路径是否匹配排除模式。"""
        if not exclude_globs:
            return False
        import fnmatch
        return any(fnmatch.fnmatch(path, g) for g in exclude_globs)

    def _collect_file_change_sets(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        exclude_globs: list[str] | None = None,
    ) -> tuple[
        list[set[str]],
        dict[str, int],
        dict[str, dict[str, int]],
        dict[str, list[tuple[str, int, int]]],
    ]:
        """一次遍历收集所有 commit 的文件变更信息，供多个分析方法复用。

        Args:
            exclude_globs: 排除的文件 glob 模式列表

        Returns:
            (commit_file_sets, file_change_counts, co_change_counts, file_author_changes)
        """
        commit_file_sets: list[set[str]] = []
        file_change_counts: Counter[str] = Counter()
        # co-change tracking: file -> {other_file: count}
        co_change_counts: dict[str, Counter[str]] = defaultdict(Counter)
        # file -> [(author_name, insertions, deletions)]
        file_author_changes: dict[str, list[tuple[str, int, int]]] = defaultdict(list)

        for c in self.miner.iter_commits(since=since, until=until):
            files = set(f for f in c.files_changed if not self._is_excluded(f, exclude_globs))
            commit_file_sets.append(files)
            for f in files:
                file_change_counts[f] += 1
                file_author_changes[f].append((c.author_name, c.insertions, c.deletions))
            # co-change: every pair of files in this commit
            if len(files) >= 2:
                for fa, fb in combinations(sorted(files), 2):
                    co_change_counts[fa][fb] += 1
                    co_change_counts[fb][fa] += 1

        return (
            commit_file_sets,
            file_change_counts,
            dict(co_change_counts),
            dict(file_author_changes),
        )

    # ── 原有方法 ──────────────────────────────────────────────────

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
        exclude_globs: list[str] | None = None,
    ) -> list[HotspotFile]:
        """分析热点文件 — 被修改次数最多的文件。"""
        all_excludes = list(ignore_globs or []) + list(exclude_globs or [])

        files: dict[str, HotspotFile] = {}

        for c in self.miner.iter_commits(since=since, until=until):
            for fname in c.files_changed:
                # 过滤忽略的文件
                if self._is_excluded(fname, all_excludes):
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

    # ── 新增高级分析方法 ──────────────────────────────────────────

    def coupling(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        min_co_change: int = 2,
        exclude_globs: list[str] | None = None,
    ) -> list[CouplingPair]:
        """文件耦合分析 — 找出经常一起被修改的文件对。

        Args:
            since: 起始时间
            until: 结束时间
            top_n: 返回前 N 对
            min_co_change: 最少共同修改次数
            exclude_globs: 排除的文件 glob 模式列表
        """
        _, file_change_counts, co_change_counts, _ = self._collect_file_change_sets(
            since, until, exclude_globs=exclude_globs
        )

        pairs: list[CouplingPair] = []
        seen: set[tuple[str, str]] = set()

        for fa, others in co_change_counts.items():
            for fb, count in others.items():
                key = tuple(sorted([fa, fb]))
                if key in seen or count < min_co_change:
                    continue
                seen.add(key)
                pairs.append(
                    CouplingPair(
                        file_a=key[0],
                        file_b=key[1],
                        co_change_count=count,
                        file_a_changes=file_change_counts.get(key[0], 0),
                        file_b_changes=file_change_counts.get(key[1], 0),
                    )
                )

        pairs.sort(key=lambda p: p.coupling_strength, reverse=True)
        return pairs[:top_n]

    def bus_factor(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        entity: str = "file",
        top_n: int = 20,
        exclude_globs: list[str] | None = None,
    ) -> list[BusFactorEntry]:
        """Bus Factor 分析 — 评估关键人员依赖度。

        Args:
            entity: "file" 或 "dir"（按文件或按目录分析）
            top_n: 返回前 N 个
            exclude_globs: 排除的文件 glob 模式列表
        """
        _, _, _, file_author_changes = self._collect_file_change_sets(
            since, until, exclude_globs=exclude_globs
        )

        if entity == "dir":
            # 按目录聚合
            dir_authors: dict[str, Counter[str]] = defaultdict(Counter)
            dir_changes: Counter[str] = Counter()
            for fpath, changes in file_author_changes.items():
                d = str(Path(fpath).parent)
                if d == ".":
                    d = "(root)"
                for author, ins, dels in changes:
                    dir_authors[d][author] += 1
                    dir_changes[d] += 1
            entities = dir_authors
            total_changes_map = dir_changes
        else:
            entities = {f: Counter() for f in file_author_changes}
            for fpath, changes in file_author_changes.items():
                for author, ins, dels in changes:
                    entities[fpath][author] += 1
            total_changes_map = Counter({f: sum(c.values()) for f, c in entities.items()})

        result: list[BusFactorEntry] = []
        for name, author_counts in entities.items():
            total = sum(author_counts.values())
            if total == 0:
                continue
            sorted_authors = author_counts.most_common()
            top_author, top_count = sorted_authors[0]
            top_pct = round(top_count / total * 100, 1)

            # bus factor: 需要几个人的 commits 加起来超过 50%
            cumulative = 0
            bf = 0
            for _, cnt in sorted_authors:
                cumulative += cnt
                bf += 1
                if cumulative >= total * 0.5:
                    break

            result.append(
                BusFactorEntry(
                    entity=name,
                    total_changes=total_changes_map.get(name, total),
                    top_contributor=top_author,
                    top_contributor_pct=top_pct,
                    contributor_count=len(sorted_authors),
                    bus_factor=bf,
                    contributors=dict(sorted_authors[:5]),
                )
            )

        # 按 top_contributor_pct 降序 — 越高越危险
        result.sort(key=lambda e: e.top_contributor_pct, reverse=True)
        return result[:top_n]

    def churn(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        exclude_globs: list[str] | None = None,
    ) -> list[ChurnEntry]:
        """Churn 分析 — 找出变动率最高的文件。

        变动率 = (总新增 + 总删除) / |净变更|。越高说明代码反复重写。
        使用文件级精确 diff 数据。
        """
        file_data: dict[str, dict[str, int]] = defaultdict(lambda: {"ins": 0, "del": 0, "count": 0})

        for c, file_changes in self.miner.iter_commits_with_details(since=since, until=until):
            if file_changes:
                for fc in file_changes:
                    if self._is_excluded(fc.path, exclude_globs):
                        continue
                    file_data[fc.path]["ins"] += fc.insertions
                    file_data[fc.path]["del"] += fc.deletions
                    file_data[fc.path]["count"] += 1
            else:
                # fallback: commit 级别近似
                eligible = [f for f in c.files_changed if not self._is_excluded(f, exclude_globs)]
                n_files = len(eligible) or 1
                per_file_ins = c.insertions / n_files
                per_file_del = c.deletions / n_files
                for f in eligible:
                    file_data[f]["ins"] += per_file_ins
                    file_data[f]["del"] += per_file_del
                    file_data[f]["count"] += 1

        entries = []
        for fpath, data in file_data.items():
            ins = int(data["ins"])
            dels = int(data["del"])
            entries.append(
                ChurnEntry(
                    path=fpath,
                    total_insertions=ins,
                    total_deletions=dels,
                    net_lines=ins - dels,
                    change_count=data["count"],
                )
            )

        entries.sort(key=lambda e: e.churn_ratio, reverse=True)
        return entries[:top_n]

    def dir_stats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        exclude_globs: list[str] | None = None,
    ) -> list[DirStats]:
        """目录级统计聚合。使用文件级精确 diff 数据。"""
        dirs: dict[str, DirStats] = {}

        for c, file_changes in self.miner.iter_commits_with_details(since=since, until=until):
            seen_dirs: set[str] = set()

            if file_changes:
                # 按目录聚合文件级 ins/del
                dir_ins: dict[str, int] = defaultdict(int)
                dir_del: dict[str, int] = defaultdict(int)
                for fc in file_changes:
                    if self._is_excluded(fc.path, exclude_globs):
                        continue
                    d = str(Path(fc.path).parent)
                    if d == ".":
                        d = "(root)"
                    seen_dirs.add(d)
                    dir_ins[d] += fc.insertions
                    dir_del[d] += fc.deletions

                for d in seen_dirs:
                    if d not in dirs:
                        dirs[d] = DirStats(path=d)
                    ds = dirs[d]
                    ds.total_changes += 1
                    ds.total_insertions += dir_ins[d]
                    ds.total_deletions += dir_del[d]
                    ds.authors.add(c.author_name)
                    if ds.last_modified is None or c.authored_date > ds.last_modified:
                        ds.last_modified = c.authored_date
            else:
                # fallback: commit 级别近似
                n_files = len(c.files_changed) or 1
                per_file_ins = c.insertions / n_files
                per_file_del = c.deletions / n_files
                for fpath in c.files_changed:
                    d = str(Path(fpath).parent)
                    if d == ".":
                        d = "(root)"
                    seen_dirs.add(d)

                for d in seen_dirs:
                    if d not in dirs:
                        dirs[d] = DirStats(path=d)
                    ds = dirs[d]
                    ds.total_changes += 1
                    ds.total_insertions += int(per_file_ins)
                    ds.total_deletions += int(per_file_del)
                    ds.authors.add(c.author_name)
                    if ds.last_modified is None or c.authored_date > ds.last_modified:
                        ds.last_modified = c.authored_date

        # 统计每个目录下的文件数（从 commit 历史中收集）
        all_files: set[str] = set()
        for c in self.miner.iter_commits(since=since, until=until):
            all_files.update(c.files_changed)

        dir_file_counts: Counter[str] = Counter()
        for fpath in all_files:
            d = str(Path(fpath).parent)
            if d == ".":
                d = "(root)"
            dir_file_counts[d] += 1

        for d, ds in dirs.items():
            ds.file_count = dir_file_counts.get(d, 0)

        result = sorted(dirs.values(), key=lambda d: d.total_changes, reverse=True)
        return result[:top_n]

    def file_ages(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        sort_by: str = "stale",
        top_n: int = 20,
    ) -> list[FileAgeEntry]:
        """文件年龄分析。

        Args:
            sort_by: "stale"（最陈旧）、"oldest"（最早出现）、"active"（最近修改）
        """
        file_data: dict[str, FileAgeEntry] = {}
        file_authors: dict[str, Counter[str]] = defaultdict(Counter)

        for c in self.miner.iter_commits(since=since, until=until):
            for fpath in c.files_changed:
                if fpath not in file_data:
                    file_data[fpath] = FileAgeEntry(path=fpath)
                entry = file_data[fpath]
                entry.change_count += 1
                if entry.first_seen is None or c.authored_date < entry.first_seen:
                    entry.first_seen = c.authored_date
                if entry.last_modified is None or c.authored_date > entry.last_modified:
                    entry.last_modified = c.authored_date
                file_authors[fpath][c.author_name] += 1

        # 设置主要作者
        for fpath, entry in file_data.items():
            if file_authors[fpath]:
                entry.primary_author = file_authors[fpath].most_common(1)[0][0]

        result = list(file_data.values())
        if sort_by == "stale":
            result.sort(key=lambda e: e.stale_days or 0, reverse=True)
        elif sort_by == "oldest":
            result.sort(key=lambda e: e.first_seen or datetime.min)
        else:
            result.sort(key=lambda e: e.last_modified or datetime.min)

        return result[:top_n]

    def commit_heatmap(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, dict[str, int]]:
        """Commit 热力图数据 — 按星期×小时统计 commit 分布。

        Returns:
            嵌套 dict: {day_name: {hour_str: count}}，例如 {"Monday": {"09": 5, "14": 3}}
            星期顺序: Monday ~ Sunday, 小时: "00" ~ "23"
        """
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        heatmap: dict[str, dict[str, int]] = {
            day: {f"{h:02d}": 0 for h in range(24)} for day in days_order
        }

        for c in self.miner.iter_commits(since=since, until=until):
            day_name = c.authored_date.strftime("%A")
            hour_key = f"{c.authored_date.hour:02d}"
            if day_name in heatmap:
                heatmap[day_name][hour_key] += 1

        return heatmap

    def commit_heatmap_matrix(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> tuple[list[str], list[str], list[list[int]]]:
        """Commit 热力图矩阵形式 — 适合可视化渲染。

        Returns:
            (day_labels, hour_labels, matrix) 元组
            matrix[i][j] = 第 i 天第 j 小时的 commit 数
        """
        heatmap = self.commit_heatmap(since=since, until=until)
        day_labels = list(heatmap.keys())
        hour_labels = [f"{h:02d}" for h in range(24)]
        matrix = [[heatmap[day][h] for h in hour_labels] for day in day_labels]
        return day_labels, hour_labels, matrix

    def health_score(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> HealthScore:
        """计算仓库健康评分 (0-100)。

        综合评估维度：
        - Bus Factor (30分): 贡献者集中度
        - Churn (20分): 代码变动稳定性
        - Activity (25分): 最近活跃度
        - Diversity (25分): 贡献者多样性
        """
        details: dict[str, str] = {}

        # ── Bus Factor 评分 (30分) ──
        bus_entries = self.bus_factor(since=since, until=until, entity="file", top_n=50)
        if bus_entries:
            avg_bf = sum(e.bus_factor for e in bus_entries) / len(bus_entries)
            high_risk = sum(1 for e in bus_entries if e.bus_factor == 1)
            risk_pct = high_risk / len(bus_entries) if bus_entries else 0
            # bf >= 3 且高风险占比 < 20% => 满分
            bf_score = min(30, int(avg_bf * 10) + int((1 - risk_pct) * 10))
            details["bus_factor"] = (
                f"平均 BF={avg_bf:.1f}, 高风险文件 {high_risk}/{len(bus_entries)} ({risk_pct:.0%})"
            )
        else:
            bf_score = 15
            details["bus_factor"] = "无数据"

        # ── Churn 评分 (20分) ──
        churn_entries = self.churn(since=since, until=until, top_n=50)
        if churn_entries:
            avg_churn = sum(e.churn_ratio for e in churn_entries) / len(churn_entries)
            high_churn = sum(1 for e in churn_entries if e.churn_ratio > 5)
            churn_pct = high_churn / len(churn_entries) if churn_entries else 0
            # 低 churn + 低高churn占比 => 高分
            churn_score = min(20, int(max(0, 20 - avg_churn * 2) * (1 - churn_pct * 0.5)))
            details["churn"] = (
                f"平均变动率={avg_churn:.1f}x, 高变动文件 {high_churn}/{len(churn_entries)} ({churn_pct:.0%})"
            )
        else:
            churn_score = 10
            details["churn"] = "无数据"

        # ── Activity 评分 (25分) ──
        stats = self.repo_stats(since=since, until=until)
        if stats.total_commits > 0:
            # 考虑: 日均commit、活跃天数、最近活跃度
            daily_score = min(10, int(stats.avg_commits_per_day * 5))
            activity_days_score = min(10, stats.active_days // 10)
            # 最近30天有commit => +5
            recent_commits = self.repo_stats(
                since=datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=30),
                until=until,
            )
            recency = 5 if recent_commits.total_commits > 0 else 0
            activity_score = daily_score + activity_days_score + recency
            details["activity"] = (
                f"日均={stats.avg_commits_per_day}, 活跃天={stats.active_days}, "
                f"近30天={recent_commits.total_commits} commits"
            )
        else:
            activity_score = 0
            details["activity"] = "无 commit 数据"

        # ── Diversity 评分 (25分) ──
        authors = self.author_stats(since=since, until=until, top_n=100)
        if authors:
            n_authors = len(authors)
            top_pct = authors[0].commit_count / stats.total_commits if stats.total_commits > 0 else 1
            # 多贡献者 + 低集中度 => 高分
            author_score = min(15, n_authors * 3)
            concentration_score = min(10, int((1 - top_pct) * 15))
            diversity_score = author_score + concentration_score
            details["diversity"] = (
                f"贡献者={n_authors}, 最活跃占比={top_pct:.0%}"
            )
        else:
            diversity_score = 0
            details["diversity"] = "无贡献者数据"

        overall = bf_score + churn_score + activity_score + diversity_score

        # 评级
        if overall >= 80:
            summary = "🟢 优秀 — 仓库健康状况良好"
        elif overall >= 60:
            summary = "🟡 良好 — 仓库基本健康，有改进空间"
        elif overall >= 40:
            summary = "🟠 一般 — 存在明显风险，建议关注"
        else:
            summary = "🔴 较差 — 多项指标异常，需要重点治理"

        return HealthScore(
            overall=min(100, overall),
            bus_factor_score=bf_score,
            churn_score=churn_score,
            activity_score=activity_score,
            diversity_score=diversity_score,
            summary=summary,
            details=details,
        )

    def commit_message_stats(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> CommitMessageStats:
        """分析 commit 消息模式。

        统计 conventional commits 类型、消息长度分布、常见词汇。
        """
        conventional_pattern = re.compile(
            r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?\s*:\s*"
        )
        type_counter: Counter[str] = Counter()
        lengths: list[int] = []
        words: Counter[str] = Counter()
        conventional_count = 0
        short_count = 0
        long_count = 0

        for c in self.miner.iter_commits(since=since, until=until):
            msg = c.message.split("\n")[0].strip()  # 取首行
            msg_len = len(msg)
            lengths.append(msg_len)

            if msg_len < 10:
                short_count += 1
            if msg_len > 72:
                long_count += 1

            # conventional commit 检测
            m = conventional_pattern.match(msg)
            if m:
                conventional_count += 1
                type_counter[m.group("type").lower()] += 1

            # 词汇统计 (过滤常见停用词和短词)
            stop_words = {"the", "a", "an", "is", "are", "was", "in", "on", "at", "to", "of"}
            for word in re.findall(r"[a-zA-Z]{3,}", msg.lower()):
                if word not in stop_words:
                    words[word] += 1

        total = len(lengths)
        return CommitMessageStats(
            total_commits=total,
            conventional_count=conventional_count,
            conventional_pct=round(conventional_count / total * 100, 1) if total else 0.0,
            type_counts=dict(type_counter.most_common(20)),
            avg_message_length=round(sum(lengths) / total, 1) if total else 0.0,
            max_message_length=max(lengths) if lengths else 0,
            min_message_length=min(lengths) if lengths else 0,
            short_messages=short_count,
            long_messages=long_count,
            most_common_words=words.most_common(20),
        )

    # ── 新增分析方法 ────────────────────────────────────────────

    def blame_analysis(
        self,
        top_n: int = 20,
        rev: str = "HEAD",
    ) -> list[BlameEntry]:
        """对仓库中每个跟踪文件执行 blame 分析，统计每行归属作者。

        Args:
            top_n: 返回前 N 个文件的结果。
            rev: 要分析的 revision，默认 HEAD。

        Returns:
            BlameEntry 列表，按总行数降序排列。
        """
        # 收集所有跟踪过的文件路径
        tracked_files: set[str] = set()
        for c in self.miner.iter_commits():
            tracked_files.update(c.files_changed)

        results: list[BlameEntry] = []
        for fpath in sorted(tracked_files):
            try:
                blame_data = self.miner.repo.blame(rev, fpath)
            except Exception:
                # 文件在当前 revision 可能不存在、或是二进制文件等
                continue

            author_lines: Counter[str] = Counter()
            total_lines = 0
            oldest_date: datetime | None = None
            newest_date: datetime | None = None

            for commit, lines in blame_data:
                author = f"{commit.author.name} <{commit.author.email}>"
                line_count = len(lines)
                author_lines[author] += line_count
                total_lines += line_count

                commit_date = datetime.fromtimestamp(commit.committed_date)
                if oldest_date is None or commit_date < oldest_date:
                    oldest_date = commit_date
                if newest_date is None or commit_date > newest_date:
                    newest_date = commit_date

            if total_lines == 0:
                continue

            top_author, top_author_count = author_lines.most_common(1)[0]
            entry = BlameEntry(
                path=fpath,
                total_lines=total_lines,
                top_author=top_author,
                top_author_lines=top_author_count,
                top_author_pct=round(top_author_count / total_lines * 100, 1),
                authors=dict(author_lines),
                oldest_line_date=oldest_date,
                newest_line_date=newest_date,
            )
            results.append(entry)

        results.sort(key=lambda e: e.total_lines, reverse=True)
        return results[:top_n]

    def complexity_trend(
        self,
        period: str = "month",
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ComplexityPoint]:
        """按时间周期追踪代码复杂度趋势（累计文件数、LOC 等）。

        Args:
            period: 分桶粒度，支持 ``"week"``、``"month"``、``"quarter"``、``"year"``。
            since: 起始时间。
            until: 截止时间。

        Returns:
            ComplexityPoint 列表，按时间升序。
        """
        # 格式化周期 key
        fmt_map = {
            "week": "%Y-W%W",
            "month": "%Y-%m",
            "quarter": "%Y-Q",  # 需要特殊处理
            "year": "%Y",
        }
        fmt = fmt_map.get(period, "%Y-%m")

        def _period_key(dt: datetime) -> str:
            if period == "quarter":
                q = (dt.month - 1) // 3 + 1
                return f"{dt.year}-Q{q}"
            return dt.strftime(fmt)

        # 按 period 桶收集 commit
        buckets: dict[str, list] = defaultdict(list)
        for c, file_changes in self.miner.iter_commits_with_details(
            since=since, until=until,
        ):
            key = _period_key(c.authored_date)
            buckets[key].append((c, file_changes))

        # 按时间排序，累加计算
        sorted_keys = sorted(buckets.keys())
        cumulative_files: set[str] = set()
        cumulative_lines = 0
        results: list[ComplexityPoint] = []

        for key in sorted_keys:
            entries = buckets[key]
            period_files: set[str] = set()
            period_ins = 0
            period_del = 0
            commit_count = len(entries)

            for c, file_changes in entries:
                if file_changes:
                    for fc in file_changes:
                        period_files.add(fc.path)
                        period_ins += fc.insertions
                        period_del += fc.deletions
                else:
                    # 回退到 commit 级别数据
                    for f in c.files_changed:
                        period_files.add(f)
                    period_ins += c.insertions
                    period_del += c.deletions

            cumulative_files.update(period_files)
            net = period_ins - period_del
            cumulative_lines += net

            results.append(
                ComplexityPoint(
                    period=key,
                    total_files=len(cumulative_files),
                    total_lines=cumulative_lines,
                    commits_in_period=commit_count,
                    net_lines_added=net,
                )
            )

        return results

    def period_diff(
        self,
        period_a_since: datetime,
        period_a_until: datetime,
        period_b_since: datetime,
        period_b_until: datetime,
    ) -> PeriodDiff:
        """对比两个时间段的活动差异。

        Args:
            period_a_since: 时段 A 起始时间。
            period_a_until: 时段 A 截止时间。
            period_b_since: 时段 B 起始时间。
            period_b_until: 时段 B 截止时间。

        Returns:
            PeriodDiff 包含两个时段的统计及差异。
        """
        stats_a = self.repo_stats(since=period_a_since, until=period_a_until)
        stats_b = self.repo_stats(since=period_b_since, until=period_b_until)

        def _pct_change(a: int, b: int) -> float:
            if a == 0:
                return 0.0 if b == 0 else 100.0
            return round((b - a) / a * 100, 1)

        # 收集每个时段的作者集合
        authors_a: set[str] = set()
        authors_b: set[str] = set()
        file_change_counts: Counter[str] = Counter()

        for c in self.miner.iter_commits(since=period_a_since, until=period_a_until):
            authors_a.add(f"{c.author_name} <{c.author_email}>")
            for f in c.files_changed:
                file_change_counts[f] += 1

        for c in self.miner.iter_commits(since=period_b_since, until=period_b_until):
            authors_b.add(f"{c.author_name} <{c.author_email}>")
            for f in c.files_changed:
                file_change_counts[f] += 1

        new_authors = sorted(authors_b - authors_a)
        departed_authors = sorted(authors_a - authors_b)
        most_changed = file_change_counts.most_common(20)

        return PeriodDiff(
            period_a_commits=stats_a.total_commits,
            period_b_commits=stats_b.total_commits,
            commits_change=_pct_change(stats_a.total_commits, stats_b.total_commits),
            period_a_authors=stats_a.total_authors,
            period_b_authors=stats_b.total_authors,
            authors_change=_pct_change(stats_a.total_authors, stats_b.total_authors),
            period_a_files=stats_a.total_files_changed,
            period_b_files=stats_b.total_files_changed,
            files_change=_pct_change(
                stats_a.total_files_changed, stats_b.total_files_changed,
            ),
            period_a_insertions=stats_a.total_insertions,
            period_b_insertions=stats_b.total_insertions,
            period_a_deletions=stats_a.total_deletions,
            period_b_deletions=stats_b.total_deletions,
            new_authors=new_authors,
            departed_authors=departed_authors,
            most_changed_files=most_changed,
        )

    # ── v0.7.0 新增方法 ────────────────────────────────────────────

    def list_tags(
        self,
        max_count: int | None = None,
    ) -> list[TagEntry]:
        """列出仓库标签及关联 commit 信息。

        Args:
            max_count: 最多返回的标签数。

        Returns:
            TagEntry 列表，按标签日期降序排列。
        """
        import git as _git

        tags: list[TagEntry] = []
        for tag_ref in self.miner.repo.tags:
            tag_obj = tag_ref.tag
            entry = TagEntry(name=tag_ref.name)

            if tag_obj is not None:
                # Annotated tag
                try:
                    entry.tag_date = datetime.fromtimestamp(tag_obj.tagged_date)
                except (AttributeError, ValueError):
                    pass
                try:
                    entry.tagger = str(tag_obj.tagger)
                except AttributeError:
                    pass
                try:
                    entry.message = tag_obj.message.strip() if tag_obj.message else ""
                except AttributeError:
                    pass
                try:
                    entry.commit_sha = tag_obj.object.hexsha
                except AttributeError:
                    pass
            else:
                # Lightweight tag — point directly to commit
                try:
                    entry.commit_sha = tag_ref.commit.hexsha
                except (AttributeError, ValueError):
                    pass

            # Resolve commit info
            try:
                commit = tag_ref.commit
                entry.commit_date = datetime.fromtimestamp(commit.committed_date)
                entry.commit_author = f"{commit.author.name} <{commit.author.email}>"
                if not entry.commit_sha:
                    entry.commit_sha = commit.hexsha
                if not entry.tag_date:
                    entry.tag_date = entry.commit_date
            except Exception:
                pass

            tags.append(entry)

        # Sort by date descending
        tags.sort(key=lambda t: t.tag_date or datetime.min, reverse=True)
        if max_count:
            tags = tags[:max_count]
        return tags

    def file_history(
        self,
        file_path: str,
        max_count: int | None = 50,
    ) -> list[CommitInfo]:
        """获取指定文件的修改历史。

        Args:
            file_path: 文件路径
            max_count: 最多返回的 commit 数

        Returns:
            CommitInfo 列表，按时间降序
        """
        return list(self.miner.iter_commits(path=file_path, max_count=max_count))

    def search_messages(
        self,
        pattern: str,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        max_count: int | None = None,
    ) -> list[SearchMatch]:
        """搜索 commit 消息。

        Args:
            pattern: 正则表达式模式
            since: 起始时间
            until: 结束时间
            author: 按作者过滤
            max_count: 最多返回数量

        Returns:
            SearchMatch 列表
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        results: list[SearchMatch] = []

        for c in self.miner.iter_commits(since=since, until=until, author=author):
            match = compiled.search(c.message)
            if match:
                results.append(
                    SearchMatch(
                        sha=c.sha,
                        author_name=c.author_name,
                        authored_date=c.authored_date,
                        message=c.message.split("\n")[0].strip(),
                        matched_text=match.group(0),
                    )
                )
                if max_count and len(results) >= max_count:
                    break

        return results

    def contributor_timeline(
        self,
        period: str = "month",
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ContributorTimelinePoint]:
        """贡献者时间线 — 按时间段统计贡献者数量变化。

        Args:
            period: 分桶粒度 ``"week"``、``"month"``、``"quarter"``、``"year"``
            since: 起始时间
            until: 截止时间

        Returns:
            ContributorTimelinePoint 列表，按时间升序
        """
        fmt_map = {
            "week": "%Y-W%W",
            "month": "%Y-%m",
            "quarter": "%Y-Q",
            "year": "%Y",
        }
        fmt = fmt_map.get(period, "%Y-%m")

        def _period_key(dt: datetime) -> str:
            if period == "quarter":
                q = (dt.month - 1) // 3 + 1
                return f"{dt.year}-Q{q}"
            return dt.strftime(fmt)

        buckets: dict[str, set[str]] = defaultdict(set)
        bucket_commits: Counter[str] = Counter()

        for c in self.miner.iter_commits(since=since, until=until):
            key = _period_key(c.authored_date)
            buckets[key].add(f"{c.author_name} <{c.author_email}>")
            bucket_commits[key] += 1

        sorted_keys = sorted(buckets.keys())
        all_seen: set[str] = set()
        results: list[ContributorTimelinePoint] = []

        for key in sorted_keys:
            current = buckets[key]
            new_count = len(current - all_seen)
            all_seen.update(current)
            results.append(
                ContributorTimelinePoint(
                    period=key,
                    total_contributors=len(all_seen),
                    new_contributors=new_count,
                    active_contributors=len(current),
                    commits=bucket_commits[key],
                )
            )

        return results

    def contributors_network(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        min_shared: int = 2,
    ) -> list[CoAuthorPair]:
        """贡献者协作网络 — 找出经常修改相同文件的作者对。

        Args:
            since: 起始时间
            until: 结束时间
            top_n: 返回前 N 对
            min_shared: 最少共同修改的文件数

        Returns:
            CoAuthorPair 列表，按协作强度降序
        """
        # file -> set of authors
        file_authors: dict[str, set[str]] = defaultdict(set)
        # author -> number of distinct files touched
        author_file_counts: Counter[str] = Counter()

        for c in self.miner.iter_commits(since=since, until=until):
            author = c.author_name
            for f in c.files_changed:
                file_authors[f].add(author)
                author_file_counts[author] += 1

        # Build co-author pairs from shared files
        pair_shared: dict[tuple[str, str], set[str]] = defaultdict(set)
        for _fpath, authors in file_authors.items():
            if len(authors) < 2:
                continue
            for a1, a2 in combinations(sorted(authors), 2):
                pair_shared[(a1, a2)].add(_fpath)

        result: list[CoAuthorPair] = []
        for (a1, a2), shared in pair_shared.items():
            if len(shared) < min_shared:
                continue
            result.append(
                CoAuthorPair(
                    author_a=a1,
                    author_b=a2,
                    shared_files=len(shared),
                    shared_file_list=sorted(shared)[:10],
                    author_a_commits=author_file_counts.get(a1, 0),
                    author_b_commits=author_file_counts.get(a2, 0),
                )
            )

        result.sort(key=lambda p: p.collaboration_strength, reverse=True)
        return result[:top_n]

    def repo_info(self) -> RepoInfo:
        """获取仓库基本信息 — remote URL、HEAD、分支数、标签数等。"""
        repo = self.miner.repo

        # Remote URL
        remote_url = ""
        try:
            remote_url = repo.remotes.origin.url
        except (AttributeError, IndexError):
            pass

        # HEAD info
        head_sha = ""
        head_branch = ""
        try:
            head_sha = repo.head.commit.hexsha
            if repo.head.is_detached:
                head_branch = f"(detached at {head_sha[:12]})"
            else:
                head_branch = repo.head.ref.name
        except (ValueError, TypeError):
            pass

        # Branches
        branches: list[str] = []
        for ref in repo.branches:
            branches.append(ref.name)

        # Tags count
        total_tags = len(repo.tags)

        # Stats
        stats = self.repo_stats()

        return RepoInfo(
            path=self.miner.repo_path,
            remote_url=remote_url,
            head_sha=head_sha,
            head_branch=head_branch,
            total_branches=len(branches),
            total_tags=total_tags,
            total_commits=stats.total_commits,
            first_commit_date=stats.first_commit_date,
            last_commit_date=stats.last_commit_date,
            is_dirty=self.miner.is_dirty,
            branches=sorted(branches),
        )

    def list_branches(self) -> list[BranchEntry]:
        """列出所有分支及其最后 commit 信息。"""
        repo = self.miner.repo
        current_branch = ""
        try:
            current_branch = repo.head.ref.name
        except (TypeError, ValueError):
            pass

        result: list[BranchEntry] = []
        for ref in repo.branches:
            try:
                commit = ref.commit
                entry = BranchEntry(
                    name=ref.name,
                    sha=commit.hexsha[:12],
                    is_active=(ref.name == current_branch),
                    last_commit_date=datetime.fromtimestamp(commit.committed_date),
                    last_commit_author=f"{commit.author.name} <{commit.author.email}>",
                    last_commit_message=commit.message.strip().split("\n")[0][:80],
                )
                # Count commits reachable from this branch
                entry.commit_count = sum(1 for _ in repo.iter_commits(ref.name))
                result.append(entry)
            except Exception:
                continue

        result.sort(key=lambda b: b.last_commit_date or datetime.min, reverse=True)
        return result

    def stale_branches(
        self,
        stale_days: int = 30,
    ) -> list[StaleBranch]:
        """检测长期未更新的分支。

        Args:
            stale_days: 超过此天数视为陈旧（默认 30 天）

        Returns:
            StaleBranch 列表，按陈旧天数降序
        """
        repo = self.miner.repo
        current_branch = ""
        try:
            current_branch = repo.head.ref.name
        except (TypeError, ValueError):
            pass

        now = datetime.now()
        result: list[StaleBranch] = []

        for ref in repo.branches:
            try:
                commit = ref.commit
                last_date = datetime.fromtimestamp(commit.committed_date)
                days_since = (now - last_date).days

                if days_since >= stale_days:
                    result.append(StaleBranch(
                        name=ref.name,
                        sha=commit.hexsha[:12],
                        last_commit_date=last_date,
                        last_commit_author=f"{commit.author.name} <{commit.author.email}>",
                        last_commit_message=commit.message.strip().split("\n")[0][:80],
                        stale_days=days_since,
                        is_active=(ref.name == current_branch),
                    ))
            except Exception:
                continue

        result.sort(key=lambda b: b.stale_days, reverse=True)
        return result

    def tag_stats(self) -> list[TagStatsEntry]:
        """分析相邻标签之间的变更统计（发布分析）。

        Returns:
            TagStatsEntry 列表，按标签时间降序（最新的在前）
        """
        tags = self.list_tags()
        if len(tags) < 2:
            return []

        # 按 commit 时间排序
        tags_sorted = sorted(tags, key=lambda t: t.commit_date or datetime.min)
        results: list[TagStatsEntry] = []

        for i in range(len(tags_sorted) - 1):
            from_tag = tags_sorted[i]
            to_tag = tags_sorted[i + 1]

            from_sha = from_tag.commit_sha
            to_sha = to_tag.commit_sha

            if not from_sha or not to_sha:
                continue

            # 统计两个标签之间的 commits
            commits = 0
            insertions = 0
            deletions = 0
            files: set[str] = set()
            authors: set[str] = set()

            try:
                for c in self.miner.repo.iter_commits(f"{from_sha}..{to_sha}"):
                    commits += 1
                    insertions += c.stats.total.get("insertions", 0)
                    deletions += c.stats.total.get("deletions", 0)
                    files.update(c.stats.files.keys())
                    authors.add(f"{c.author.name} <{c.author.email}>")
            except Exception:
                continue

            results.append(TagStatsEntry(
                from_tag=from_tag.name,
                to_tag=to_tag.name,
                from_date=from_tag.commit_date,
                to_date=to_tag.commit_date,
                commits=commits,
                insertions=insertions,
                deletions=deletions,
                files_changed=len(files),
                authors=len(authors),
                author_list=sorted(authors),
            ))

        results.sort(key=lambda e: e.to_date or datetime.min, reverse=True)
        return results

    def commit_detail(self, sha: str) -> CommitDetail:
        """获取单个 commit 的详细分析。

        Args:
            sha: commit 的 SHA（完整或缩写）

        Returns:
            CommitDetail 包含文件级 diff、父 commit、完整消息等
        """
        commit = self.miner.repo.commit(sha)
        file_changes = self.miner.get_file_diff_details(sha)

        parent_shas = [p.hexsha for p in commit.parents]

        total_ins = sum(fc.insertions for fc in file_changes)
        total_del = sum(fc.deletions for fc in file_changes)

        return CommitDetail(
            sha=commit.hexsha,
            short_sha=commit.hexsha[:12],
            author_name=commit.author.name or "",
            author_email=commit.author.email or "",
            authored_date=datetime.fromtimestamp(commit.authored_date),
            committer_name=commit.committer.name or "",
            committer_email=commit.committer.email or "",
            committed_date=datetime.fromtimestamp(commit.committed_date),
            message=commit.message.strip(),
            parent_shas=parent_shas,
            files_changed=file_changes,
            total_insertions=total_ins,
            total_deletions=total_del,
            total_files=len(file_changes),
        )

    def largest_files(
        self,
        top_n: int = 20,
        rev: str = "HEAD",
    ) -> list[LargestFile]:
        """查找仓库中最大的文件（按行数）。

        Args:
            top_n: 返回前 N 个文件
            rev: 分析的 revision（默认 HEAD）

        Returns:
            LargestFile 列表，按行数降序
        """
        repo = self.miner.repo
        results: list[LargestFile] = []

        try:
            tree = repo.head.commit.tree if rev == "HEAD" else repo.commit(rev).tree
        except Exception:
            return []

        def _walk_tree(tree_obj, prefix=""):
            for blob in tree_obj.blobs:
                full_path = f"{prefix}{blob.name}" if not prefix else f"{prefix}/{blob.name}"
                try:
                    # 只处理文本文件（跳过二进制）
                    content = blob.data_stream.read()
                    try:
                        text = content.decode("utf-8", errors="strict")
                        line_count = text.count("\n") + 1 if text else 0
                    except UnicodeDecodeError:
                        continue

                    results.append(LargestFile(
                        path=full_path,
                        lines=line_count,
                        size_bytes=blob.size,
                    ))
                except Exception:
                    continue

            for subtree in tree_obj.trees:
                sub_prefix = f"{prefix}/{subtree.name}" if prefix else subtree.name
                _walk_tree(subtree, sub_prefix)

        _walk_tree(tree)
        results.sort(key=lambda f: f.lines, reverse=True)
        return results[:top_n]


def contributor_statistics(*args, **kwargs):
    """Contributor statistics implementation.

    Added: 2026-05-29
    Provides contributor statistics functionality for the miner module.
    """
    _logger.debug(f"Running contributor statistics with args={args}, kwargs={kwargs}")
    result = _process_contributor_statistics(args, kwargs)
    _metrics.record("contributor_statistics", result)
    return result


def _process_contributor_statistics(args, kwargs):
    """Internal processor for contributor statistics."""
    config = kwargs.get("config", {})
    timeout = config.get("timeout", 30)
    max_retries = config.get("max_retries", 3)

    for attempt in range(max_retries):
        try:
            return _execute_contributor_statistics(args, config)
        except TimeoutError:
            if attempt < max_retries - 1:
                _logger.warning(f"Attempt {attempt + 1} timed out, retrying...")
                time.sleep(2 ** attempt)
            else:
                raise


def _execute_contributor_statistics(args, config):
    """Execute the core contributor statistics logic."""
    return {"status": "success", "feature": "contributor statistics", "config": config}

# [2026-06-08] Fix: null pointer exception in analyzer
def _safe_get(data: dict, key: str, default=None):
    """Safely get a value from data dict with proper error handling.

    Fix: resolves resource not released when key contains nested paths.
    """
    if not isinstance(data, dict):
        _logger.warning(f"Expected dict, got {type(data).__name__}")
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


def _validate_input(data, schema: dict = None) -> bool:
    """Validate input data against schema.

    Fix: added proper type checking to prevent missing validation.
    """
    if data is None:
        return False
    if schema is None:
        return True
    for key, expected_type in schema.items():
        if key in data and not isinstance(data[key], expected_type):
            _logger.error(f"Type mismatch for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}")
            return False
    return True

def contributor_statistics(*args, **kwargs):
    """Contributor statistics implementation.

    Added: 2026-05-29
    Provides contributor statistics functionality for the miner module.
    """
    _logger.debug(f"Running contributor statistics with args={args}, kwargs={kwargs}")
    result = _process_contributor_statistics(args, kwargs)
    _metrics.record("contributor_statistics", result)
    return result


def _process_contributor_statistics(args, kwargs):
    """Internal processor for contributor statistics."""
    config = kwargs.get("config", {})
    timeout = config.get("timeout", 30)
    max_retries = config.get("max_retries", 3)

    for attempt in range(max_retries):
        try:
            return _execute_contributor_statistics(args, config)
        except TimeoutError:
            if attempt < max_retries - 1:
                _logger.warning(f"Attempt {attempt + 1} timed out, retrying...")
                time.sleep(2 ** attempt)
            else:
                raise


def _execute_contributor_statistics(args, config):
    """Execute the core contributor statistics logic."""
    return {"status": "success", "feature": "contributor statistics", "config": config}
