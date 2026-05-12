"""测试 — commit 热力图、文件级 diff、summary CLI、heatmap CLI。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime

import git
from click.testing import CliRunner

from git_archaeologist.analyzer import Analyzer
from git_archaeologist.cli import main
from git_archaeologist.git_mining import GitMiner
from tests.helpers import create_test_repo


def _create_heatmap_repo() -> tuple[str, git.Repo]:
    """创建一个在不同时段有 commit 的仓库，用于热力图测试。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-heatmap-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")

    # 在不同星期和小时创建 commit
    # 2024-01-01 是 Monday
    commit_times = [
        datetime(2024, 1, 1, 9, 0),   # Mon 09:00
        datetime(2024, 1, 1, 9, 30),  # Mon 09:30
        datetime(2024, 1, 1, 14, 0),  # Mon 14:00
        datetime(2024, 1, 2, 10, 0),  # Tue 10:00
        datetime(2024, 1, 3, 22, 0),  # Wed 22:00
        datetime(2024, 1, 5, 9, 0),   # Fri 09:00
        datetime(2024, 1, 6, 15, 0),  # Sat 15:00
        datetime(2024, 1, 7, 9, 0),   # Sun 09:00
    ]

    for i, dt in enumerate(commit_times):
        filepath = os.path.join(tmpdir, f"file_{i}.py")
        with open(filepath, "w") as f:
            f.write(f"# Commit {i} at {dt}\nprint({i})\n")
        repo.index.add([f"file_{i}.py"])
        repo.index.commit(
            f"commit {i}",
            author=author,
            committer=author,
            commit_date=dt.isoformat(),
            author_date=dt.isoformat(),
        )

    return tmpdir, repo


# ── 热力图 Analyzer 测试 ──────────────────────────────────────────


class TestCommitHeatmap:
    """Analyzer.commit_heatmap 测试。"""

    def test_heatmap_returns_dict(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            assert isinstance(result, dict)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_has_all_days(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            expected_days = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            assert list(result.keys()) == expected_days
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_has_24_hours_per_day(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            for day_data in result.values():
                assert len(day_data) == 24
                for h in range(24):
                    assert f"{h:02d}" in day_data
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_counts_correct(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            # 注意：gitpython 存储 UTC 时间戳，fromtimestamp 转换为本地时间
            # 所以实际小时数可能有偏移
            total = sum(v for d in result.values() for v in d.values())
            assert total == 8
            # 确认 Monday 有 3 个 commit
            assert sum(result["Monday"].values()) == 3
            # 确认 Thursday 有 1 个（原本的 Wed 22:00 UTC+8 后变 Thu 06:00）
            assert sum(result["Thursday"].values()) == 1
            # Wednesday 没有 commit
            assert sum(result["Wednesday"].values()) == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_total_equals_commit_count(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            total = sum(v for d in result.values() for v in d.values())
            assert total == 8
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_with_date_filter(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            # 只取 1月2日之后
            result = analyzer.commit_heatmap(since=datetime(2024, 1, 2))
            total = sum(v for d in result.values() for v in d.values())
            assert total == 5  # 从 Tue 开始
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestCommitHeatmapMatrix:
    """Analyzer.commit_heatmap_matrix 测试。"""

    def test_matrix_returns_tuple(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap_matrix()
            assert isinstance(result, tuple)
            assert len(result) == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_matrix_dimensions(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            day_labels, hour_labels, matrix = analyzer.commit_heatmap_matrix()
            assert len(day_labels) == 7
            assert len(hour_labels) == 24
            assert len(matrix) == 7
            assert all(len(row) == 24 for row in matrix)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_matrix_values_match_heatmap(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            analyzer = Analyzer(tmpdir)
            heatmap = analyzer.commit_heatmap()
            day_labels, hour_labels, matrix = analyzer.commit_heatmap_matrix()
            for i, day in enumerate(day_labels):
                for j, hour in enumerate(hour_labels):
                    assert matrix[i][j] == heatmap[day][hour]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── 文件级 diff 测试 ──────────────────────────────────────────────


class TestFileDiffDetails:
    """GitMiner.get_file_diff_details 和 iter_commits_with_details 测试。"""

    def test_get_file_diff_details_returns_list(self):
        tmpdir, repo = create_test_repo(num_commits=3)
        try:
            miner = GitMiner(tmpdir)
            commits = list(miner.iter_commits())
            sha = commits[0].sha
            result = miner.get_file_diff_details(sha)
            assert isinstance(result, list)
            assert len(result) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_diff_has_insertions_deletions(self):
        tmpdir, repo = create_test_repo(num_commits=3)
        try:
            miner = GitMiner(tmpdir)
            commits = list(miner.iter_commits())
            for c in commits:
                changes = miner.get_file_diff_details(c.sha)
                for fc in changes:
                    assert fc.insertions >= 0
                    assert fc.deletions >= 0
                    assert isinstance(fc.path, str)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_iter_commits_with_details_returns_tuples(self):
        tmpdir, repo = create_test_repo(num_commits=3)
        try:
            miner = GitMiner(tmpdir)
            results = list(miner.iter_commits_with_details())
            assert len(results) == 3
            for info, file_changes in results:
                assert hasattr(info, "sha")
                assert isinstance(file_changes, list)
                assert len(file_changes) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_iter_commits_with_details_with_filters(self):
        tmpdir, repo = create_test_repo(num_commits=5, num_authors=2)
        try:
            miner = GitMiner(tmpdir)
            results = list(miner.iter_commits_with_details(author="Alice"))
            # Alice 是第 0, 2, 4 个 commit
            assert len(results) == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── heatmap CLI 测试 ──────────────────────────────────────────────


class TestHeatmapCLI:
    """CLI heatmap 命令测试。"""

    def test_heatmap_table_output(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "heatmap"])
            assert result.exit_code == 0
            assert "Commit 热力图" in result.output
            assert "Mon" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_json_output(self):
        tmpdir, repo = _create_heatmap_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "heatmap", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "Monday" in data
            assert "09" in data["Monday"]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── summary CLI 测试 ──────────────────────────────────────────────


class TestSummaryCLI:
    """CLI summary 命令测试。"""

    def test_summary_table_output(self):
        tmpdir, repo = create_test_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "summary"])
            assert result.exit_code == 0
            assert "仓库概览" in result.output
            assert "Commits" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_summary_json_output(self):
        tmpdir, repo = create_test_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "summary", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "stats" in data
            assert "top_authors" in data
            assert "top_hotspots" in data
            assert data["stats"]["total_commits"] == 10
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_summary_with_date_filter(self):
        tmpdir, repo = create_test_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "summary", "--since", "2024-01-05"])
            assert result.exit_code == 0
            assert "仓库概览" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── 空仓库测试 ────────────────────────────────────────────────────


class TestHeatmapEdgeCases:
    """边界情况测试。"""

    def test_heatmap_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_heatmap()
            total = sum(v for d in result.values() for v in d.values())
            assert total == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_heatmap_matrix_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            day_labels, hour_labels, matrix = analyzer.commit_heatmap_matrix()
            assert all(all(v == 0 for v in row) for row in matrix)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
