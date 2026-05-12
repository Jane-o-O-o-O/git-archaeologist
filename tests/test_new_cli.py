"""测试新增 CLI 功能 — health, commit-messages, CSV/Markdown 输出。"""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.cli import main


def _create_test_repo(num_commits: int = 10, num_authors: int = 3) -> str:
    """创建测试仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-cli-new-")
    repo = git.Repo.init(tmpdir)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ]
    base_date = datetime(2024, 1, 1)

    for i in range(num_commits):
        author_idx = i % num_authors
        name, email = authors[author_idx]
        filepath = os.path.join(tmpdir, f"file_{i % 3}.py")
        with open(filepath, "w") as f:
            f.write(f"# File {i % 3}\n# Commit {i}\nprint('hello {i}')\n")
        repo.index.add([f"file_{i % 3}.py"])
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}: update file_{i % 3}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir


@pytest.fixture
def runner():
    """CLI 测试 runner。"""
    return CliRunner()


@pytest.fixture
def repo_path():
    """提供测试仓库路径。"""
    path = _create_test_repo()
    yield path
    shutil.rmtree(path, ignore_errors=True)


# ── Health Command Tests ────────────────────────────────────────────


class TestHealthCommand:
    """health 子命令测试。"""

    def test_health_table(self, runner: CliRunner, repo_path: str):
        """health 命令 table 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "health"])
        assert result.exit_code == 0
        assert "健康评分" in result.output or "Overall" in result.output

    def test_health_json(self, runner: CliRunner, repo_path: str):
        """health 命令 JSON 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "health", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "overall" in data
        assert 0 <= data["overall"] <= 100

    def test_health_csv(self, runner: CliRunner, repo_path: str):
        """health 命令 CSV 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "health", "--format", "csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 1
        assert "overall" in rows[0]


# ── Commit Messages Command Tests ────────────────────────────────────


class TestCommitMessagesCommand:
    """commit-messages 子命令测试。"""

    def test_commit_messages_table(self, runner: CliRunner, repo_path: str):
        """commit-messages 命令 table 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "commit-messages"])
        assert result.exit_code == 0
        assert "Commit" in result.output or "消息" in result.output

    def test_commit_messages_json(self, runner: CliRunner, repo_path: str):
        """commit-messages 命令 JSON 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "commit-messages", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_commits" in data
        assert data["total_commits"] == 10

    def test_commit_messages_csv(self, runner: CliRunner, repo_path: str):
        """commit-messages 命令 CSV 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "commit-messages", "--format", "csv"]
        )
        assert result.exit_code == 0


# ── CSV Output Format Tests ─────────────────────────────────────────


class TestCSVOutput:
    """CSV 输出格式测试。"""

    def test_stats_csv(self, runner: CliRunner, repo_path: str):
        """stats 命令 CSV 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "stats", "--format", "csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) == 1
        assert "total_commits" in rows[0]

    def test_authors_csv(self, runner: CliRunner, repo_path: str):
        """authors 命令 CSV 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "authors", "--format", "csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) > 0
        assert "name" in rows[0]

    def test_hotspots_csv(self, runner: CliRunner, repo_path: str):
        """hotspots 命令 CSV 输出。"""
        result = runner.invoke(main, ["--repo", repo_path, "hotspots", "--format", "csv"])
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) > 0

    def test_activity_csv(self, runner: CliRunner, repo_path: str):
        """activity 命令 CSV 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "activity", "--format", "csv"]
        )
        assert result.exit_code == 0
        reader = csv.DictReader(io.StringIO(result.output))
        rows = list(reader)
        assert len(rows) > 0

    def test_coupling_csv(self, runner: CliRunner, repo_path: str):
        """coupling 命令 CSV 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "coupling", "--format", "csv"]
        )
        assert result.exit_code == 0

    def test_heatmap_csv(self, runner: CliRunner, repo_path: str):
        """heatmap 命令 CSV 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "heatmap", "--format", "csv"]
        )
        assert result.exit_code == 0

    def test_summary_csv(self, runner: CliRunner, repo_path: str):
        """summary 命令 CSV 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "summary", "--format", "csv"]
        )
        assert result.exit_code == 0


# ── Markdown Output Format Tests ─────────────────────────────────────


class TestMarkdownOutput:
    """Markdown 输出格式测试。"""

    def test_stats_markdown(self, runner: CliRunner, repo_path: str):
        """stats 命令 Markdown 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "stats", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "|" in result.output  # Markdown 表格
        assert "---" in result.output

    def test_authors_markdown(self, runner: CliRunner, repo_path: str):
        """authors 命令 Markdown 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "authors", "--format", "markdown"]
        )
        assert result.exit_code == 0
        assert "|" in result.output

    def test_hotspots_markdown(self, runner: CliRunner, repo_path: str):
        """hotspots 命令 Markdown 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "hotspots", "--format", "markdown"]
        )
        assert result.exit_code == 0

    def test_summary_markdown(self, runner: CliRunner, repo_path: str):
        """summary 命令 Markdown 输出。"""
        result = runner.invoke(
            main, ["--repo", repo_path, "summary", "--format", "markdown"]
        )
        assert result.exit_code == 0
