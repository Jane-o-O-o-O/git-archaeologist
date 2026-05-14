"""v0.9.0 新功能测试 — repo-info, branches, 格式统一, --output 补全。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.analyzer import Analyzer, BranchEntry, RepoInfo
from git_archaeologist.cli import main


# ── 测试辅助 ──────────────────────────────────────────────────


def _create_rich_repo() -> tuple[str, git.Repo]:
    """创建一个包含多分支、多作者、多文件的测试仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-v090-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
    ]
    files_list = [
        ["src/main.py", "src/utils.py"],
        ["src/main.py", "docs/README.md"],
        ["src/api.py", "src/models.py"],
        ["docs/README.md"],
        ["src/main.py", "src/api.py"],
        ["src/utils.py", "tests/test_main.py"],
        ["src/models.py"],
        ["src/main.py"],
        ["docs/guide.md", "src/api.py"],
        ["src/main.py", "src/utils.py", "src/models.py"],
    ]

    for i, files in enumerate(files_list):
        author_idx = i % len(authors)
        name, email = authors[author_idx]
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i}\nprint('v{i}')\n")
        repo.index.add(files)
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i * 3)
        repo.index.commit(
            f"commit {i}: update {' '.join(files)}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


@pytest.fixture
def rich_repo():
    """提供一个丰富的测试仓库。"""
    tmpdir, repo = _create_rich_repo()
    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def runner():
    """Click CLI 测试 runner。"""
    return CliRunner()


# ── RepoInfo 数据类测试 ──────────────────────────────────────


class TestRepoInfo:
    """RepoInfo 数据类测试。"""

    def test_repo_info_defaults(self):
        info = RepoInfo()
        assert info.path == ""
        assert info.remote_url == ""
        assert info.total_branches == 0
        assert info.branches == []

    def test_repo_info_fields(self):
        info = RepoInfo(
            path="/tmp/test",
            remote_url="https://github.com/test/test.git",
            head_branch="main",
            total_branches=3,
            total_tags=5,
            is_dirty=False,
        )
        assert info.path == "/tmp/test"
        assert info.remote_url == "https://github.com/test/test.git"
        assert info.head_branch == "main"
        assert info.total_branches == 3
        assert info.total_tags == 5
        assert info.is_dirty is False


# ── BranchEntry 数据类测试 ────────────────────────────────────


class TestBranchEntry:
    """BranchEntry 数据类测试。"""

    def test_branch_entry_defaults(self):
        entry = BranchEntry()
        assert entry.name == ""
        assert entry.sha == ""
        assert entry.is_active is False
        assert entry.commit_count == 0

    def test_branch_entry_fields(self):
        entry = BranchEntry(
            name="main",
            sha="abc123def456",
            is_active=True,
            last_commit_author="Alice <alice@example.com>",
            last_commit_message="initial commit",
            commit_count=10,
        )
        assert entry.name == "main"
        assert entry.sha == "abc123def456"
        assert entry.is_active is True
        assert entry.commit_count == 10


# ── Analyzer.repo_info() 测试 ────────────────────────────────


class TestAnalyzerRepoInfo:
    """Analyzer.repo_info() 方法测试。"""

    def test_repo_info_basic(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        info = analyzer.repo_info()
        assert isinstance(info, RepoInfo)
        assert info.path == tmpdir
        assert info.head_branch in ("main", "master")  # git default
        assert info.total_commits == 10
        assert info.total_branches >= 1
        assert info.is_dirty is False

    def test_repo_info_has_dates(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        info = analyzer.repo_info()
        assert info.first_commit_date is not None
        assert info.last_commit_date is not None
        assert info.first_commit_date <= info.last_commit_date

    def test_repo_info_branches_list(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        info = analyzer.repo_info()
        assert isinstance(info.branches, list)
        assert len(info.branches) >= 1


# ── Analyzer.list_branches() 测试 ────────────────────────────


class TestAnalyzerListBranches:
    """Analyzer.list_branches() 方法测试。"""

    def test_list_branches_basic(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        branches = analyzer.list_branches()
        assert isinstance(branches, list)
        assert len(branches) >= 1
        assert all(isinstance(b, BranchEntry) for b in branches)

    def test_list_branches_has_main(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        branches = analyzer.list_branches()
        names = [b.name for b in branches]
        assert "master" in names or "main" in names

    def test_list_branches_active_flag(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        branches = analyzer.list_branches()
        active = [b for b in branches if b.is_active]
        assert len(active) == 1
        assert active[0].name in ("main", "master")

    def test_list_branches_commit_info(self, rich_repo):
        tmpdir, _ = rich_repo
        analyzer = Analyzer(tmpdir)
        branches = analyzer.list_branches()
        main_branch = [b for b in branches if b.is_active][0]
        assert main_branch.commit_count > 0
        assert main_branch.last_commit_date is not None
        assert main_branch.last_commit_author != ""
        assert main_branch.sha != ""


# ── repo-info CLI 命令测试 ───────────────────────────────────


class TestRepoInfoCLI:
    """repo-info CLI 命令测试。"""

    def test_repo_info_table(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "repo-info"])
        assert result.exit_code == 0
        assert "仓库信息" in result.output or "仓库路径" in result.output

    def test_repo_info_json(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "repo-info", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "path" in data
        assert "head_branch" in data
        assert data["total_commits"] == 10

    def test_repo_info_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "repo-info", "--format", "csv"])
        assert result.exit_code == 0
        assert "key,value" in result.output

    def test_repo_info_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "repo-info", "--format", "markdown"])
        assert result.exit_code == 0
        assert "属性" in result.output
        assert "值" in result.output

    def test_repo_info_output_file(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        out_path = os.path.join(tmpdir, "info.json")
        result = runner.invoke(
            main, ["--repo", tmpdir, "repo-info", "--format", "json", "-o", out_path]
        )
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert data["total_commits"] == 10


# ── branches CLI 命令测试 ─────────────────────────────────────


class TestBranchesCLI:
    """branches CLI 命令测试。"""

    def test_branches_table(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "branches"])
        assert result.exit_code == 0
        assert "分支列表" in result.output or "master" in result.output or "main" in result.output

    def test_branches_json(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "branches", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "name" in data[0]
        assert "commit_count" in data[0]

    def test_branches_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "branches", "--format", "csv"])
        assert result.exit_code == 0
        assert "name,sha" in result.output

    def test_branches_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "branches", "--format", "markdown"])
        assert result.exit_code == 0
        assert "分支" in result.output

    def test_branches_output_file(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        out_path = os.path.join(tmpdir, "branches.json")
        result = runner.invoke(
            main, ["--repo", tmpdir, "branches", "--format", "json", "-o", out_path]
        )
        assert result.exit_code == 0
        assert os.path.exists(out_path)


# ── 格式统一测试：busfactor csv/markdown ──────────────────────


class TestBusfactorFormats:
    """busfactor 命令的 csv/markdown 格式测试。"""

    def test_busfactor_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "busfactor", "--format", "csv"]
        )
        assert result.exit_code == 0
        assert "entity,total_changes" in result.output

    def test_busfactor_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "busfactor", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "实体" in result.output or "主要贡献者" in result.output


# ── 格式统一测试：churn csv/markdown ──────────────────────────


class TestChurnFormats:
    """churn 命令的 csv/markdown 格式测试。"""

    def test_churn_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "churn", "--format", "csv"])
        assert result.exit_code == 0
        assert "path,total_insertions" in result.output

    def test_churn_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "churn", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "文件路径" in result.output


# ── 格式统一测试：dirs csv/markdown ───────────────────────────


class TestDirsFormats:
    """dirs 命令的 csv/markdown 格式测试。"""

    def test_dirs_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "dirs", "--format", "csv"])
        assert result.exit_code == 0
        assert "path,file_count" in result.output

    def test_dirs_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "dirs", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "目录" in result.output


# ── 格式统一测试：ages csv/markdown ───────────────────────────


class TestAgesFormats:
    """ages 命令的 csv/markdown 格式测试。"""

    def test_ages_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, ["--repo", tmpdir, "ages", "--format", "csv"])
        assert result.exit_code == 0
        assert "path,change_count" in result.output

    def test_ages_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "ages", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "文件路径" in result.output


# ── 格式统一测试：filetypes csv/markdown/output ───────────────


class TestFiletypesFormats:
    """filetypes 命令的 csv/markdown/output 测试。"""

    def test_filetypes_csv(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "filetypes", "--format", "csv"]
        )
        assert result.exit_code == 0
        assert "extension,file_count" in result.output

    def test_filetypes_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "filetypes", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "扩展名" in result.output

    def test_filetypes_output(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        out_path = os.path.join(tmpdir, "types.json")
        result = runner.invoke(
            main, ["--repo", tmpdir, "filetypes", "--format", "json", "-o", out_path]
        )
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        with open(out_path) as f:
            data = json.load(f)
        assert isinstance(data, list)


# ── 格式统一测试：coupling markdown ───────────────────────────


class TestCouplingFormats:
    """coupling 命令的 markdown 格式测试。"""

    def test_coupling_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "coupling", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "文件 A" in result.output or "共变次数" in result.output


# ── 格式统一测试：heatmap markdown ────────────────────────────


class TestHeatmapFormats:
    """heatmap 命令的 markdown 格式测试。"""

    def test_heatmap_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "heatmap", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "时段" in result.output


# ── 格式统一测试：summary markdown ────────────────────────────


class TestSummaryFormats:
    """summary 命令的 markdown 格式测试。"""

    def test_summary_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "summary", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "总 Commits" in result.output


# ── 格式统一测试：activity markdown ───────────────────────────


class TestActivityFormats:
    """activity 命令的 markdown 格式测试。"""

    def test_activity_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(
            main, ["--repo", tmpdir, "activity", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "时间段" in result.output or "Commits" in result.output


# ── 格式统一测试：diff markdown ───────────────────────────────


class TestDiffFormats:
    """diff 命令的 markdown 格式测试。"""

    def test_diff_markdown(self, rich_repo, runner):
        tmpdir, _ = rich_repo
        result = runner.invoke(main, [
            "--repo", tmpdir, "diff",
            "--a-since", "2024-01-01", "--a-until", "2024-03-01",
            "--b-since", "2024-03-01", "--b-until", "2024-06-01",
            "--format", "markdown",
        ])
        assert result.exit_code == 0
        assert "指标" in result.output or "Commits" in result.output


# ── __init__.py 导出测试 ──────────────────────────────────────


class TestExports:
    """测试新增的导出符号。"""

    def test_repo_info_exported(self):
        import git_archaeologist
        assert hasattr(git_archaeologist, "RepoInfo")

    def test_branch_entry_exported(self):
        import git_archaeologist
        assert hasattr(git_archaeologist, "BranchEntry")

    def test_repo_info_in_all(self):
        assert "RepoInfo" in __import__("git_archaeologist").__all__

    def test_branch_entry_in_all(self):
        assert "BranchEntry" in __import__("git_archaeologist").__all__
