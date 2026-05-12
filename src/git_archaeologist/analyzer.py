"""核心分析引擎 — commit 统计、热点文件、贡献者活跃度、高级分析。"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path

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


class Analyzer:
    """仓库分析器。"""

    def __init__(self, repo_path: str = ".") -> None:
        self.miner = GitMiner(repo_path)

    def _collect_file_change_sets(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> tuple[list[set[str]], dict[str, int], dict[str, dict[str, int]], dict[str, list[tuple[str, int, int]]]]:
        """一次遍历收集所有 commit 的文件变更信息，供多个分析方法复用。

        Returns:
            (commit_file_sets, file_change_counts, co_change_counts, file_author_changes)
        """
        commit_file_sets: list[set[str]] = []
        file_change_counts: Counter[str] = Counter()
        # co_change tracking: file -> {other_file: count}
        co_change_counts: dict[str, Counter[str]] = defaultdict(Counter)
        # file -> [(author_name, insertions, deletions)]
        file_author_changes: dict[str, list[tuple[str, int, int]]] = defaultdict(list)

        for c in self.miner.iter_commits(since=since, until=until):
            files = set(c.files_changed)
            commit_file_sets.append(files)
            for f in files:
                file_change_counts[f] += 1
                file_author_changes[f].append((c.author_name, c.insertions, c.deletions))
            # co-change: every pair of files in this commit
            if len(files) >= 2:
                for fa, fb in combinations(sorted(files), 2):
                    co_change_counts[fa][fb] += 1
                    co_change_counts[fb][fa] += 1

        return commit_file_sets, file_change_counts, dict(co_change_counts), dict(file_author_changes)

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

    # ── 新增高级分析方法 ──────────────────────────────────────────

    def coupling(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        top_n: int = 20,
        min_co_change: int = 2,
    ) -> list[CouplingPair]:
        """文件耦合分析 — 找出经常一起被修改的文件对。

        Args:
            since: 起始时间
            until: 结束时间
            top_n: 返回前 N 对
            min_co_change: 最少共同修改次数
        """
        _, file_change_counts, co_change_counts, _ = self._collect_file_change_sets(since, until)

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
    ) -> list[BusFactorEntry]:
        """Bus Factor 分析 — 评估关键人员依赖度。

        Args:
            entity: "file" 或 "dir"（按文件或按目录分析）
            top_n: 返回前 N 个
        """
        _, _, _, file_author_changes = self._collect_file_change_sets(since, until)

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
    ) -> list[ChurnEntry]:
        """Churn 分析 — 找出变动率最高的文件。

        变动率 = (总新增 + 总删除) / |净变更|。越高说明代码反复重写。
        """
        file_data: dict[str, dict[str, int]] = defaultdict(lambda: {"ins": 0, "del": 0, "count": 0})

        for c in self.miner.iter_commits(since=since, until=until):
            # 需要文件级别的 ins/del，但 CommitInfo 只有 commit 级别的
            # 这里用 commit 级别近似分配给每个文件
            n_files = len(c.files_changed) or 1
            per_file_ins = c.insertions / n_files
            per_file_del = c.deletions / n_files
            for f in c.files_changed:
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
    ) -> list[DirStats]:
        """目录级统计聚合。"""
        dirs: dict[str, DirStats] = {}

        for c in self.miner.iter_commits(since=since, until=until):
            n_files = len(c.files_changed) or 1
            per_file_ins = c.insertions / n_files
            per_file_del = c.deletions / n_files

            seen_dirs: set[str] = set()
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
