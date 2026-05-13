"""v0.7.0 新功能测试 — tags, file-history, search, contributors-timeline, activity 过滤。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.analyzer import (
    Analyzer,
    ContributorTimelinePoint,
    SearchMatch,
    TagEntry,
)
from git_archaeologist.cli import main


# ── 测试辅助：创建带标签的仓库 ──────────────────────────────────


def _create_tagged_repo() -> tuple[str, git.Repo]:
    """创建包含标签的测试仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-tags-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)
    author = git.Actor("Alice", "alice@example.com")

    # commit 1
    filepath = os.path.join(tmpdir, "main.py")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("print('v1.0')\\n")
    repo.index.add(["main.py"])
    d1 = base_date
    c1 = repo.index.commit(
        "initial commit",
        author=author,
        committer=author,
        commit_date=d1.isoformat(),
        author_date=d1.isoformat(),
    )
    repo.create_tag("v1.0", message="Release v1.0")

    # commit 2
    with open(filepath, "w") as f:
        f.write("print('v1.1')\\n# new feature\\n")
    repo.index.add(["main.py"])
    d2 = base_date + timedelta(days=30)
    c2 = repo.index.commit(
        "feat: add new feature",
        author=author,
        committer=author,
        commit_date=d2.isoformat(),
        author_date=d2.isoformat(),
    )
    repo.create_tag("v1.1", message="Release v1.1 with new feature")

    # commit 3 — lightweight tag
    with open(filepath, "w") as f:
        f.write("print('v2.0-beta')\\n# new feature\\n# beta\\n")
    repo.index.add(["main.py"])
    d3 = base_date + timedelta(days=60)
    c3 = repo.index.commit(
        "feat!: breaking change",
        author=git.Actor("Bob", "bob@example.com"),
        committer=author,
        commit_date=d3.isoformat(),
        author_date=d3.isoformat(),
    )
    repo.create_tag("v2.0-beta")  # lightweight tag

    return tmpdir, repo


def _create_multi_author_repo() -> tuple[str, git.Repo]:
    """创建多作者仓库用于贡献者时间线测试。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-timeline-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ]

    commits_data = [
        (0, 0, "src/a.py"),    # Jan Alice
        (1, 1, "src/b.py"),    # Feb Bob
        (2, 0, "src/a.py"),    # Mar Alice
        (3, 2, "src/c.py"),    # Apr Charlie (new)
        (4, 0, "src/a.py"),    # May Alice
        (5, 1, "src/b.py"),    # Jun Bob
        (6, 2, "src/c.py"),    # Jul Charlie
        (7, 0, "src/a.py"),    # Aug Alice
        (8, 1, "src/b.py"),    # Sep Bob
        (9, 0, "src/a.py"),    # Oct Alice
    ]

    for i, author_idx, filepath in commits_data:
        full_path = os.path.join(tmpdir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(f"# {filepath}\\n# commit {i}\\nprint({i})\\n")
        repo.index.add([filepath])
        name, email = authors[author_idx]
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i * 30)
        repo.index.commit(
            f"commit {i}: update {filepath}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


# ── Tags 测试 ────────────────────────────────────────────────────


class TestTagsAnalyzer:
    """Analyzer.list_tags() 测试。"""

    def test_list_tags_returns_entries(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            assert len(tags) >= 2  # at least v1.0 and v1.1
            assert all(isinstance(t, TagEntry) for t in tags)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_names(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            tag_names = [t.name for t in tags]
            assert "v1.0" in tag_names
            assert "v1.1" in tag_names
            assert "v2.0-beta" in tag_names
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_annotated_have_message(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            v10 = next(t for t in tags if t.name == "v1.0")
            assert "v1.0" in v10.message
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_have_commit_date(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            for t in tags:
                assert t.commit_date is not None
                assert t.commit_author != ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_max_count(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags(max_count=2)
            assert len(tags) <= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_sorted_by_date_desc(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            dates = [t.tag_date for t in tags if t.tag_date]
            assert dates == sorted(dates, reverse=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_list_tags_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-")
        try:
            repo = git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            tags = analyzer.list_tags()
            assert tags == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── File History 测试 ────────────────────────────────────────────


class TestFileHistory:
    """Analyzer.file_history() 测试。"""

    def test_file_history_returns_commits(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            history = analyzer.file_history("main.py")
            assert len(history) >= 2
            from git_archaeologist.git_mining import CommitInfo
            assert all(isinstance(c, CommitInfo) for c in history)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_max_count(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            history = analyzer.file_history("main.py", max_count=2)
            assert len(history) <= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_nonexistent_file(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            history = analyzer.file_history("nonexistent.py")
            assert history == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── Search Messages 测试 ─────────────────────────────────────────


class TestSearchMessages:
    """Analyzer.search_messages() 测试。"""

    def test_search_basic(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages("feat")
            assert len(results) >= 2  # "feat: add new feature" and "feat!: breaking change"
            assert all(isinstance(r, SearchMatch) for r in results)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_regex(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages(r"feat!?:")
            assert len(results) >= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_case_insensitive(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages("FEAT")
            assert len(results) >= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_no_match(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages("nonexistent_pattern_xyz")
            assert results == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_with_time_filter(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            # Only search in first month
            results = analyzer.search_messages(
                "commit",
                since=datetime(2024, 1, 1),
                until=datetime(2024, 1, 31),
            )
            assert len(results) >= 1
            for r in results:
                assert r.authored_date <= datetime(2024, 2, 1)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_max_count(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages("commit", max_count=1)
            assert len(results) == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_matched_text(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            analyzer = Analyzer(tmpdir)
            results = analyzer.search_messages("feat")
            for r in results:
                assert "feat" in r.matched_text.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── Contributor Timeline 测试 ────────────────────────────────────


class TestContributorTimeline:
    """Analyzer.contributor_timeline() 测试。"""

    def test_timeline_returns_points(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            analyzer = Analyzer(tmpdir)
            timeline = analyzer.contributor_timeline()
            assert len(timeline) >= 1
            assert all(isinstance(p, ContributorTimelinePoint) for p in timeline)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_total_monotonic(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            analyzer = Analyzer(tmpdir)
            timeline = analyzer.contributor_timeline()
            # total_contributors should be monotonically non-decreasing
            totals = [p.total_contributors for p in timeline]
            for i in range(1, len(totals)):
                assert totals[i] >= totals[i - 1]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_has_new_contributors(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            analyzer = Analyzer(tmpdir)
            timeline = analyzer.contributor_timeline()
            # First month should have new contributors
            assert timeline[0].new_contributors >= 1
            # Charlie joins in month 4
            assert any(p.new_contributors >= 1 for p in timeline)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_total_commits(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            analyzer = Analyzer(tmpdir)
            timeline = analyzer.contributor_timeline()
            total_commits = sum(p.commits for p in timeline)
            assert total_commits == 10  # we created 10 commits
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_period_week(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            analyzer = Analyzer(tmpdir)
            timeline = analyzer.contributor_timeline(period="week")
            assert len(timeline) >= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI Tags 命令测试 ────────────────────────────────────────────


class TestCLITags:
    """CLI tags 命令测试。"""

    def test_tags_table(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tags"])
            assert result.exit_code == 0
            assert "标签" in result.output or "v1.0" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tags_json(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tags", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) >= 2
            assert "name" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tags_csv(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tags", "--format", "csv"])
            assert result.exit_code == 0
            assert "name" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tags_markdown(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tags", "--format", "markdown"])
            assert result.exit_code == 0
            assert "---" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tags_output_file(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            out_file = os.path.join(tmpdir, "tags.json")
            result = runner.invoke(
                main, ["--repo", tmpdir, "tags", "--format", "json", "--output", out_file]
            )
            assert result.exit_code == 0
            assert os.path.exists(out_file)
            with open(out_file) as f:
                data = json.load(f)
            assert isinstance(data, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tags_top(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tags", "--top", "1", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) <= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI File History 命令测试 ────────────────────────────────────


class TestCLIFileHistory:
    """CLI file-history 命令测试。"""

    def test_file_history_table(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "file-history", "main.py"])
            assert result.exit_code == 0
            assert "main.py" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_json(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "file-history", "main.py", "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) >= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_csv(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "file-history", "main.py", "--format", "csv"]
            )
            assert result.exit_code == 0
            assert "sha" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_markdown(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "file-history", "main.py", "--format", "markdown"]
            )
            assert result.exit_code == 0
            assert "---" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_history_nonexistent(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "file-history", "nonexistent.py"]
            )
            assert result.exit_code == 0
            assert "无修改历史" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI Search 命令测试 ──────────────────────────────────────────


class TestCLISearch:
    """CLI search 命令测试。"""

    def test_search_table(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "search", "feat"])
            assert result.exit_code == 0
            assert "feat" in result.output.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_json(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "search", "feat", "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) >= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_no_match(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "search", "xyz_nonexistent"])
            assert result.exit_code == 0
            assert "未找到" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_with_time_filter(self):
        tmpdir, repo = _create_tagged_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "search", "commit", "--since", "2024-01-01", "--until", "2024-01-31"]
            )
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI Contributors Timeline 测试 ───────────────────────────────


class TestCLIContributorsTimeline:
    """CLI contributors-timeline 命令测试。"""

    def test_timeline_table(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "contributors-timeline"])
            assert result.exit_code == 0
            assert "贡献者" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_json(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "contributors-timeline", "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert "total_contributors" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_csv(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "contributors-timeline", "--format", "csv"]
            )
            assert result.exit_code == 0
            assert "total_contributors" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_timeline_period_week(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "contributors-timeline", "--period", "week"]
            )
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI Activity 过滤测试 ────────────────────────────────────────


class TestCLIActivityFilter:
    """CLI activity 命令 --filter-path/--filter-author 测试。"""

    def test_activity_with_filter_author(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "activity", "--filter-author", "Alice"]
            )
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_activity_with_filter_path(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "activity", "--filter-path", "src/a.py"]
            )
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_activity_json(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "activity", "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, dict)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_activity_csv(self):
        tmpdir, repo = _create_multi_author_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "activity", "--format", "csv"]
            )
            assert result.exit_code == 0
            assert "period" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── 新增数据类测试 ───────────────────────────────────────────────


class TestNewDataclasses:
    """测试新增的 dataclass。"""

    def test_tag_entry_fields(self):
        t = TagEntry(name="v1.0")
        assert t.name == "v1.0"
        assert t.sha == ""
        assert t.tag_date is None
        assert t.tagger == ""
        assert t.message == ""
        assert t.commit_sha == ""
        assert t.commit_date is None
        assert t.commit_author == ""

    def test_search_match_fields(self):
        dt = datetime(2024, 1, 1)
        s = SearchMatch(sha="abc123", author_name="Alice", authored_date=dt, message="test")
        assert s.sha == "abc123"
        assert s.author_name == "Alice"
        assert s.authored_date == dt
        assert s.matched_text == ""

    def test_contributor_timeline_point_fields(self):
        p = ContributorTimelinePoint(period="2024-01")
        assert p.period == "2024-01"
        assert p.total_contributors == 0
        assert p.new_contributors == 0
        assert p.active_contributors == 0
        assert p.commits == 0


# ── __init__.py 导出测试 ─────────────────────────────────────────


class TestExports:
    """测试新类型是否正确导出。"""

    def test_tag_entry_exported(self):
        from git_archaeologist import TagEntry
        assert TagEntry is not None

    def test_search_match_exported(self):
        from git_archaeologist import SearchMatch
        assert SearchMatch is not None

    def test_contributor_timeline_point_exported(self):
        from git_archaeologist import ContributorTimelinePoint
        assert ContributorTimelinePoint is not None
