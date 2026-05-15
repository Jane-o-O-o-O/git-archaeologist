"""v1.2.0 新功能测试 — stale-branches, tag-stats, inspect, largest."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest

from git_archaeologist.analyzer import (
    Analyzer,
    CommitDetail,
    LargestFile,
    StaleBranch,
    TagStatsEntry,
)
from git_archaeologist.cli import main

from click.testing import CliRunner


# ── 测试仓库 Fixtures ─────────────────────────────────────────────


@pytest.fixture
def stale_repo():
    """创建一个有陈旧分支的仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-stale-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 1, 1)

    # main 分支：10 个 commit
    for i in range(10):
        filepath = os.path.join(tmpdir, "main.py")
        with open(filepath, "w") as f:
            f.write(f"# Main {i}\nprint('main {i}')\n")
        repo.index.add(["main.py"])
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    # 创建一个旧分支（基于第 5 个 commit）
    old_commit = list(repo.iter_commits())[-5]  # 较早的 commit
    repo.create_head("feature/old", old_commit)

    # 创建另一个更旧的分支
    oldest_commit = list(repo.iter_commits())[-1]  # 最早的 commit
    repo.create_head("feature/ancient", oldest_commit)

    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def tag_repo():
    """创建一个有多个标签的仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-tags-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 1, 1)

    commits_info = []

    # 15 个 commit，每 5 个打一个标签
    for i in range(15):
        filepath = os.path.join(tmpdir, "app.py")
        with open(filepath, "w") as f:
            f.write(f"# App v{i}\nprint('version {i}')\n")
        repo.index.add(["app.py"])
        commit_date = base_date + timedelta(days=i * 7)
        commit = repo.index.commit(
            f"commit {i}: feature {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )
        commits_info.append(commit)

        # 每 5 个 commit 打一个标签
        if (i + 1) % 5 == 0:
            tag_name = f"v{(i + 1) // 5}.0"
            repo.create_tag(tag_name, message=f"Release {tag_name}")

    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def multi_file_repo():
    """创建一个有多个文件的仓库（用于 largest 测试）。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-largest-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 1, 1)

    # 创建不同大小的文件
    files = {
        "small.py": "# Small file\nprint('hello')\n",
        "medium.py": "# Medium file\n" + "\n".join(f"line_{i} = {i}" for i in range(50)) + "\n",
        "large.py": "# Large file\n" + "\n".join(f"def func_{i}():\n    return {i}" for i in range(200)) + "\n",
        "huge.py": "# Huge file\n" + "\n".join(f"x_{i} = {i} * {i}" for i in range(500)) + "\n",
        "src/module.py": "# Module\n" + "\n".join(f"class Foo{i}: pass" for i in range(100)) + "\n",
    }

    for path, content in files.items():
        filepath = os.path.join(tmpdir, path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)

    repo.index.add(list(files.keys()))
    commit_date = base_date.isoformat()
    repo.index.commit(
        "initial commit",
        author=author,
        committer=author,
        commit_date=commit_date,
        author_date=commit_date,
    )

    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def rich_repo():
    """创建一个有丰富历史的仓库（用于 inspect 测试）。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-inspect-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    # 多作者、多文件的 commit 历史
    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
    ]

    for i in range(8):
        name, email = authors[i % 2]
        author = git.Actor(name, email)
        files_to_modify = [f"src/file_{j}.py" for j in range((i % 3) + 1)]

        for f in files_to_modify:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i} by {name}\n" + f"line = {i}\n" * (i + 1))

        repo.index.add(files_to_modify)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"feat: commit {i} by {name}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── Analyzer 测试 ──────────────────────────────────────────────────


class TestStaleBranchesAnalyzer:
    """Analyzer.stale_branches 方法测试。"""

    def test_stale_branches_returns_list(self, stale_repo):
        tmpdir, _ = stale_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.stale_branches(stale_days=0)
        assert isinstance(result, list)

    def test_stale_branches_finds_old_branches(self, stale_repo):
        tmpdir, _ = stale_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.stale_branches(stale_days=0)
        # 应该找到所有分支（包括 main）
        assert len(result) >= 1

    def test_stale_branches_high_threshold(self, stale_repo):
        tmpdir, _ = stale_repo
        analyzer = Analyzer(tmpdir)
        # 用非常高的阈值，应该找不到（所有 commit 都在 2024 年）
        result = analyzer.stale_branches(stale_days=999999)
        assert len(result) == 0

    def test_stale_branches_entry_fields(self, stale_repo):
        tmpdir, _ = stale_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.stale_branches(stale_days=0)
        if result:
            entry = result[0]
            assert isinstance(entry, StaleBranch)
            assert entry.name
            assert entry.sha
            assert entry.stale_days >= 0
            assert entry.last_commit_date is not None

    def test_stale_branches_sorted_by_staleness(self, stale_repo):
        tmpdir, _ = stale_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.stale_branches(stale_days=0)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i].stale_days >= result[i + 1].stale_days


class TestTagStatsAnalyzer:
    """Analyzer.tag_stats 方法测试。"""

    def test_tag_stats_returns_list(self, tag_repo):
        tmpdir, _ = tag_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.tag_stats()
        assert isinstance(result, list)

    def test_tag_stats_has_entries(self, tag_repo):
        tmpdir, _ = tag_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.tag_stats()
        # 3 个标签 => 2 个区间
        assert len(result) == 2

    def test_tag_stats_entry_fields(self, tag_repo):
        tmpdir, _ = tag_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.tag_stats()
        if result:
            entry = result[0]
            assert isinstance(entry, TagStatsEntry)
            assert entry.from_tag
            assert entry.to_tag
            assert entry.commits > 0
            assert entry.insertions >= 0
            assert entry.deletions >= 0
            assert entry.files_changed >= 0
            assert entry.authors >= 0

    def test_tag_stats_commits_count(self, tag_repo):
        tmpdir, _ = tag_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.tag_stats()
        # 每个区间应该有 5 个 commit
        for entry in result:
            assert entry.commits == 5

    def test_tag_stats_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-tag-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.tag_stats()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tag_stats_single_tag(self):
        """只有一个标签时应返回空列表。"""
        tmpdir = tempfile.mkdtemp(prefix="git-arch-1tag-")
        try:
            repo = git.Repo.init(tmpdir)
            author = git.Actor("Dev", "dev@example.com")
            filepath = os.path.join(tmpdir, "f.py")
            with open(filepath, "w") as f:
                f.write("print('hello')\n")
            repo.index.add(["f.py"])
            repo.index.commit("initial", author=author, committer=author)
            repo.create_tag("v1.0")
            analyzer = Analyzer(tmpdir)
            result = analyzer.tag_stats()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestCommitDetailAnalyzer:
    """Analyzer.commit_detail 方法测试。"""

    def test_commit_detail_returns_object(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        # 获取最新 commit 的 SHA
        commits = list(analyzer.miner.iter_commits(max_count=1))
        sha = commits[0].sha
        result = analyzer.commit_detail(sha)
        assert isinstance(result, CommitDetail)

    def test_commit_detail_fields(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        commits = list(analyzer.miner.iter_commits(max_count=1))
        sha = commits[0].sha
        detail = analyzer.commit_detail(sha)

        assert detail.sha == sha
        assert detail.short_sha == sha[:12]
        assert detail.author_name
        assert detail.author_email
        assert detail.authored_date is not None
        assert detail.message
        assert detail.total_files > 0
        assert detail.total_insertions >= 0
        assert detail.total_deletions >= 0
        assert len(detail.files_changed) > 0

    def test_commit_detail_file_changes(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        commits = list(analyzer.miner.iter_commits(max_count=1))
        sha = commits[0].sha
        detail = analyzer.commit_detail(sha)

        for fc in detail.files_changed:
            assert fc.path
            assert fc.insertions >= 0
            assert fc.deletions >= 0

    def test_commit_detail_parents(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        commits = list(analyzer.miner.iter_commits(max_count=1))
        sha = commits[0].sha
        detail = analyzer.commit_detail(sha)

        # 非第一个 commit 应该有父 commit
        assert len(detail.parent_shas) >= 1

    def test_commit_detail_invalid_sha(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        with pytest.raises(Exception):
            analyzer.commit_detail("invalid_sha_12345")


class TestLargestFilesAnalyzer:
    """Analyzer.largest_files 方法测试。"""

    def test_largest_files_returns_list(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.largest_files()
        assert isinstance(result, list)

    def test_largest_files_sorted_by_lines(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.largest_files()
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert result[i].lines >= result[i + 1].lines

    def test_largest_files_entry_fields(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.largest_files()
        if result:
            entry = result[0]
            assert isinstance(entry, LargestFile)
            assert entry.path
            assert entry.lines > 0
            assert entry.size_bytes > 0

    def test_largest_files_top_n(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.largest_files(top_n=2)
        assert len(result) <= 2

    def test_largest_files_huge_is_first(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.largest_files()
        if result:
            # huge.py 应该是最大的
            assert result[0].path == "huge.py"

    def test_largest_files_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-largest-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.largest_files()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI 测试 ───────────────────────────────────────────────────────


class TestStaleBranchesCLI:
    """stale-branches CLI 命令测试。"""

    def test_stale_branches_table(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "stale-branches", "--days", "0"])
        assert result.exit_code == 0

    def test_stale_branches_json(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "stale-branches", "--days", "0", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_stale_branches_csv(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "stale-branches", "--days", "0", "--format", "csv"])
        assert result.exit_code == 0
        assert "name" in result.output

    def test_stale_branches_markdown(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "stale-branches", "--days", "0", "--format", "markdown"])
        assert result.exit_code == 0
        assert "|" in result.output

    def test_stale_branches_output_file(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        out_path = os.path.join(tmpdir, "stale.json")
        result = runner.invoke(main, [
            "--repo", tmpdir, "stale-branches", "--days", "0",
            "--format", "json", "--output", out_path,
        ])
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_stale_branches_no_stale(self, stale_repo):
        tmpdir, _ = stale_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "stale-branches", "--days", "999999"])
        assert result.exit_code == 0


class TestTagStatsCLI:
    """tag-stats CLI 命令测试。"""

    def test_tag_stats_table(self, tag_repo):
        tmpdir, _ = tag_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "tag-stats"])
        assert result.exit_code == 0

    def test_tag_stats_json(self, tag_repo):
        tmpdir, _ = tag_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "tag-stats", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_tag_stats_csv(self, tag_repo):
        tmpdir, _ = tag_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "tag-stats", "--format", "csv"])
        assert result.exit_code == 0
        assert "from_tag" in result.output

    def test_tag_stats_markdown(self, tag_repo):
        tmpdir, _ = tag_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "tag-stats", "--format", "markdown"])
        assert result.exit_code == 0
        assert "|" in result.output

    def test_tag_stats_output_file(self, tag_repo):
        tmpdir, _ = tag_repo
        runner = CliRunner()
        out_path = os.path.join(tmpdir, "tags.json")
        result = runner.invoke(main, [
            "--repo", tmpdir, "tag-stats", "--format", "json", "--output", out_path,
        ])
        assert result.exit_code == 0
        assert os.path.exists(out_path)

    def test_tag_stats_no_tags(self):
        """没有标签的仓库应显示提示信息。"""
        tmpdir = tempfile.mkdtemp(prefix="git-arch-notags-")
        try:
            repo = git.Repo.init(tmpdir)
            author = git.Actor("Dev", "dev@example.com")
            filepath = os.path.join(tmpdir, "f.py")
            with open(filepath, "w") as f:
                f.write("print('hello')\n")
            repo.index.add(["f.py"])
            repo.index.commit("initial", author=author, committer=author)

            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "tag-stats"])
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestInspectCLI:
    """inspect CLI 命令测试。"""

    def test_inspect_table(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        # 获取最新 commit SHA
        repo = git.Repo(tmpdir)
        sha = repo.head.commit.hexsha
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", sha])
        assert result.exit_code == 0
        assert "Commit" in result.output

    def test_inspect_json(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        repo = git.Repo(tmpdir)
        sha = repo.head.commit.hexsha
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", sha, "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["sha"] == sha
        assert "files" in data
        assert "total_insertions" in data

    def test_inspect_csv(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        repo = git.Repo(tmpdir)
        sha = repo.head.commit.hexsha
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", sha, "--format", "csv"])
        assert result.exit_code == 0
        assert "path" in result.output

    def test_inspect_markdown(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        repo = git.Repo(tmpdir)
        sha = repo.head.commit.hexsha
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", sha, "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Commit" in result.output

    def test_inspect_output_file(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        repo = git.Repo(tmpdir)
        sha = repo.head.commit.hexsha
        out_path = os.path.join(tmpdir, "inspect.json")
        result = runner.invoke(main, [
            "--repo", tmpdir, "inspect", sha, "--format", "json", "--output", out_path,
        ])
        assert result.exit_code == 0
        assert os.path.exists(out_path)

    def test_inspect_invalid_sha(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", "invalid_sha"])
        assert result.exit_code != 0

    def test_inspect_head(self, rich_repo):
        tmpdir, _ = rich_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "inspect", "HEAD"])
        assert result.exit_code == 0


class TestLargestCLI:
    """largest CLI 命令测试。"""

    def test_largest_table(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest"])
        assert result.exit_code == 0
        assert "最大文件" in result.output

    def test_largest_json(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "path" in data[0]
        assert "lines" in data[0]

    def test_largest_csv(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest", "--format", "csv"])
        assert result.exit_code == 0
        assert "path" in result.output

    def test_largest_markdown(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest", "--format", "markdown"])
        assert result.exit_code == 0
        assert "|" in result.output

    def test_largest_top_n(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest", "--top", "2", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) <= 2

    def test_largest_output_file(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        out_path = os.path.join(tmpdir, "largest.json")
        result = runner.invoke(main, [
            "--repo", tmpdir, "largest", "--format", "json", "--output", out_path,
        ])
        assert result.exit_code == 0
        assert os.path.exists(out_path)

    def test_largest_sorted_descending(self, multi_file_repo):
        tmpdir, _ = multi_file_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "largest", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for i in range(len(data) - 1):
            assert data[i]["lines"] >= data[i + 1]["lines"]
