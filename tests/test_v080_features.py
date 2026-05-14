"""v0.8.0 新功能测试 — contributors-network, --output, --format markdown。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.analyzer import Analyzer, CoAuthorPair
from git_archaeologist.cli import main


# ── 测试辅助：创建多作者协作仓库 ──────────────────────────────


def _create_collab_repo() -> tuple[str, git.Repo]:
    """创建一个多作者协作仓库，用于测试 contributors_network。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-collab-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    # Alice 和 Bob 经常一起修改相同的文件
    # Charlie 独立工作
    commits = [
        # Alice 和 Bob 共同修改 src/api.py 和 src/models.py
        ("Alice", "alice@example.com", ["src/api.py", "src/models.py"]),
        ("Bob", "bob@example.com", ["src/api.py", "src/models.py"]),
        ("Alice", "alice@example.com", ["src/api.py"]),
        ("Bob", "bob@example.com", ["src/models.py"]),
        ("Alice", "alice@example.com", ["src/api.py", "src/models.py"]),
        ("Bob", "bob@example.com", ["src/api.py", "src/models.py"]),
        # Charlie 独立修改 docs/
        ("Charlie", "charlie@example.com", ["docs/README.md"]),
        ("Charlie", "charlie@example.com", ["docs/README.md"]),
        # Alice 和 Charlie 偶尔共同修改
        ("Alice", "alice@example.com", ["src/utils.py"]),
        ("Charlie", "charlie@example.com", ["src/utils.py"]),
    ]

    for i, (name, email, files) in enumerate(commits):
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i} by {name}\n'content {i}'\n")
        repo.index.add(files)
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}: update by {name}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


@pytest.fixture
def collab_repo():
    """提供一个多作者协作测试仓库。"""
    tmpdir, repo = _create_collab_repo()
    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── CoAuthorPair 数据类测试 ──────────────────────────────────


class TestCoAuthorPair:
    """CoAuthorPair 数据类测试。"""

    def test_collaboration_strength_basic(self):
        """测试协作强度计算。"""
        pair = CoAuthorPair(
            author_a="Alice",
            author_b="Bob",
            shared_files=5,
            author_a_commits=10,
            author_b_commits=8,
        )
        # Jaccard: 5 / (10 + 8 - 5) = 5/13 ≈ 0.385
        assert pair.collaboration_strength == round(5 / 13, 3)

    def test_collaboration_strength_zero(self):
        """测试零贡献时的协作强度。"""
        pair = CoAuthorPair(
            author_a="Alice",
            author_b="Bob",
            shared_files=0,
            author_a_commits=0,
            author_b_commits=0,
        )
        assert pair.collaboration_strength == 0.0

    def test_collaboration_strength_perfect(self):
        """测试完全重叠时的协作强度。"""
        pair = CoAuthorPair(
            author_a="Alice",
            author_b="Bob",
            shared_files=10,
            author_a_commits=10,
            author_b_commits=10,
        )
        # Jaccard: 10 / (10 + 10 - 10) = 10/10 = 1.0
        assert pair.collaboration_strength == 1.0


# ── Analyzer.contributors_network 测试 ──────────────────────


class TestContributorsNetwork:
    """contributors_network 分析方法测试。"""

    def test_basic_network(self, collab_repo):
        """测试基本的协作网络分析。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.contributors_network()

        assert len(result) > 0
        # 所有结果应该是 CoAuthorPair
        for pair in result:
            assert isinstance(pair, CoAuthorPair)
            assert pair.author_a < pair.author_b  # 排序保证

    def test_alice_bob_collaboration(self, collab_repo):
        """Alice 和 Bob 应该有最强的协作关系。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.contributors_network(top_n=5)

        # 找到 Alice-Bob 对
        alice_bob = None
        for pair in result:
            if {pair.author_a, pair.author_b} == {"Alice", "Bob"}:
                alice_bob = pair
                break

        assert alice_bob is not None
        assert alice_bob.shared_files >= 2
        assert "src/api.py" in alice_bob.shared_file_list
        assert "src/models.py" in alice_bob.shared_file_list

    def test_min_shared_filter(self, collab_repo):
        """测试最少共同文件数过滤。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)

        # 高阈值应该过滤掉弱关系
        result = analyzer.contributors_network(min_shared=5)
        for pair in result:
            assert pair.shared_files >= 5

    def test_top_n_limit(self, collab_repo):
        """测试 top_n 限制。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.contributors_network(top_n=1)
        assert len(result) <= 1

    def test_time_filter(self, collab_repo):
        """测试时间过滤。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)

        # 只看前5天
        result = analyzer.contributors_network(
            since=datetime(2024, 1, 1),
            until=datetime(2024, 1, 5),
        )
        # 应该有数据但比全量少
        assert isinstance(result, list)

    def test_empty_repo(self):
        """测试空仓库。"""
        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-")
        try:
            repo = git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.contributors_network()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_single_author_repo(self):
        """测试单作者仓库（无协作对）。"""
        tmpdir = tempfile.mkdtemp(prefix="git-arch-single-")
        try:
            repo = git.Repo.init(tmpdir)
            author = git.Actor("Solo", "solo@example.com")
            filepath = os.path.join(tmpdir, "main.py")
            with open(filepath, "w") as f:
                f.write("print('hello')\n")
            repo.index.add(["main.py"])
            repo.index.commit(
                "initial",
                author=author,
                committer=author,
                author_date=datetime(2024, 1, 1).isoformat(),
                commit_date=datetime(2024, 1, 1).isoformat(),
            )
            analyzer = Analyzer(tmpdir)
            result = analyzer.contributors_network()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_shared_file_list_limited(self, collab_repo):
        """测试 shared_file_list 最多返回10个文件。"""
        tmpdir, _ = collab_repo
        analyzer = Analyzer(tmpdir)
        result = analyzer.contributors_network()
        for pair in result:
            assert len(pair.shared_file_list) <= 10


# ── CLI contributors-network 命令测试 ──────────────────────


class TestContributorsNetworkCLI:
    """contributors-network CLI 子命令测试。"""

    def test_table_output(self, collab_repo):
        """测试表格输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "contributors-network"])
        assert result.exit_code == 0
        assert "贡献者协作网络" in result.output

    def test_json_output(self, collab_repo):
        """测试 JSON 输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "contributors-network", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        if data:
            assert "author_a" in data[0]
            assert "author_b" in data[0]
            assert "shared_files" in data[0]
            assert "collaboration_strength" in data[0]

    def test_csv_output(self, collab_repo):
        """测试 CSV 输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "contributors-network", "--format", "csv"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0] == "author_a,author_b,shared_files,collaboration_strength"

    def test_markdown_output(self, collab_repo):
        """测试 Markdown 输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "contributors-network", "--format", "markdown"])
        assert result.exit_code == 0
        assert "作者 A" in result.output
        assert "---" in result.output

    def test_top_option(self, collab_repo):
        """测试 --top 选项。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "contributors-network", "--top", "1", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) <= 1

    def test_min_shared_option(self, collab_repo):
        """测试 --min-shared 选项。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(
            main, ["--repo", tmpdir, "contributors-network", "--min-shared", "100", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 0  # 阈值太高，无结果

    def test_time_filter(self, collab_repo):
        """测试时间过滤选项。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(
            main, ["--repo", tmpdir, "contributors-network", "--since", "2024-01-01", "--until", "2024-01-05"]
        )
        assert result.exit_code == 0


# ── --output 选项测试 ──────────────────────────────────────


class TestOutputOption:
    """测试各命令的 --output 选项。"""

    def test_stats_output_to_file(self, collab_repo):
        """测试 stats 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "stats", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            assert "已写入" in result.output
            with open(outpath) as f:
                data = json.load(f)
            assert "total_commits" in data
        finally:
            os.unlink(outpath)

    def test_authors_output_to_file(self, collab_repo):
        """测试 authors 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "authors", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                data = json.load(f)
            assert isinstance(data, list)
        finally:
            os.unlink(outpath)

    def test_hotspots_output_to_file(self, collab_repo):
        """测试 hotspots 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "hotspots", "--format", "csv", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                content = f.read()
            assert "path" in content
        finally:
            os.unlink(outpath)

    def test_summary_output_to_file(self, collab_repo):
        """测试 summary 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "summary", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                data = json.load(f)
            assert "stats" in data
        finally:
            os.unlink(outpath)

    def test_heatmap_output_to_file(self, collab_repo):
        """测试 heatmap 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "heatmap", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                data = json.load(f)
            assert isinstance(data, dict)
        finally:
            os.unlink(outpath)

    def test_activity_output_to_file(self, collab_repo):
        """测试 activity 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "activity", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                data = json.load(f)
            assert isinstance(data, dict)
        finally:
            os.unlink(outpath)

    def test_contributors_network_output_to_file(self, collab_repo):
        """测试 contributors-network 命令输出到文件。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            outpath = f.name
        try:
            result = runner.invoke(
                main, ["--repo", tmpdir, "contributors-network", "--format", "json", "-o", outpath]
            )
            assert result.exit_code == 0
            with open(outpath) as f:
                data = json.load(f)
            assert isinstance(data, list)
        finally:
            os.unlink(outpath)


# ── --format markdown 新增测试 ──────────────────────────────


class TestMarkdownFormat:
    """测试新增的 markdown 输出格式。"""

    def test_health_markdown(self, collab_repo):
        """测试 health 命令的 markdown 输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "health", "--format", "markdown"])
        assert result.exit_code == 0
        assert "维度" in result.output
        assert "得分" in result.output
        assert "---" in result.output
        assert "Bus Factor" in result.output

    def test_commit_messages_markdown(self, collab_repo):
        """测试 commit-messages 命令的 markdown 输出。"""
        tmpdir, _ = collab_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "commit-messages", "--format", "markdown"])
        assert result.exit_code == 0
        assert "指标" in result.output
        assert "值" in result.output
        assert "---" in result.output


# ── __init__.py 导出测试 ──────────────────────────────────


class TestExports:
    """测试新类是否正确导出。"""

    def test_co_author_pair_exported(self):
        """CoAuthorPair 应该可以从包中导入。"""
        from git_archaeologist import CoAuthorPair as CAP

        assert CAP is CoAuthorPair
