"""测试 v0.6.0 新功能 — blame, complexity, diff, --version, --output。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.analyzer import Analyzer, BlameEntry, ComplexityPoint, PeriodDiff
from git_archaeologist.cli import main


# ── 辅助工具 ──────────────────────────────────────────────────


def _create_blame_repo() -> str:
    """创建用于 blame 测试的仓库 — 多作者修改同一文件。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-blame-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    # Alice 写初始代码
    filepath = os.path.join(tmpdir, "src/main.py")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write("# Alice's code\nline1\nline2\nline3\nline4\nline5\n")
    repo.index.add(["src/main.py"])
    author_a = git.Actor("Alice", "alice@example.com")
    repo.index.commit(
        "initial commit",
        author=author_a,
        committer=author_a,
        commit_date=(base_date).isoformat(),
        author_date=(base_date).isoformat(),
    )

    # Bob 修改部分行
    with open(filepath, "w") as f:
        f.write("# Alice's code\nline1\n# Bob's edit\nline3\nline4\nline5\n# Bob added\n")
    repo.index.add(["src/main.py"])
    author_b = git.Actor("Bob", "bob@example.com")
    repo.index.commit(
        "bob edits",
        author=author_b,
        committer=author_b,
        commit_date=(base_date + timedelta(days=1)).isoformat(),
        author_date=(base_date + timedelta(days=1)).isoformat(),
    )

    # Alice 再加一个文件
    filepath2 = os.path.join(tmpdir, "src/utils.py")
    with open(filepath2, "w") as f:
        f.write("# Utils by Alice\nimport os\nimport sys\n")
    repo.index.add(["src/utils.py"])
    repo.index.commit(
        "add utils",
        author=author_a,
        committer=author_a,
        commit_date=(base_date + timedelta(days=2)).isoformat(),
        author_date=(base_date + timedelta(days=2)).isoformat(),
    )

    return tmpdir


def _create_growing_repo() -> str:
    """创建用于复杂度趋势测试的仓库 — 文件和代码逐渐增长。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-complexity-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)
    author = git.Actor("Dev", "dev@example.com")

    for i in range(6):
        # 每月添加一些代码
        filepath = os.path.join(tmpdir, f"src/module_{i % 3}.py")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        lines = [f"# line {j}" for j in range((i + 1) * 10)]
        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")
        repo.index.add([f"src/module_{i % 3}.py"])
        commit_date = base_date + timedelta(days=i * 30)
        repo.index.commit(
            f"month {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir


def _create_diff_repo() -> str:
    """创建用于时段对比测试的仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-diff-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    # 时段 A: Alice 主导 (Jan-Mar)
    for i in range(5):
        filepath = os.path.join(tmpdir, f"src/file_{i}.py")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(f"# file {i}\nprint('hello {i}')\n")
        repo.index.add([f"src/file_{i}.py"])
        author = git.Actor("Alice", "alice@example.com")
        commit_date = base_date + timedelta(days=i * 15)
        repo.index.commit(
            f"alice commit {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    # 时段 B: Bob 和 Charlie 加入 (Apr-Jun)
    new_authors = [
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ]
    for i in range(5):
        filepath = os.path.join(tmpdir, f"src/newfile_{i}.py")
        with open(filepath, "w") as f:
            f.write(f"# new file {i}\nprint('world {i}')\n")
        repo.index.add([f"src/newfile_{i}.py"])
        name, email = new_authors[i % 2]
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=90 + i * 15)
        repo.index.commit(
            f"{name} commit {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir


# ── Blame 分析测试 ────────────────────────────────────────────


class TestBlameAnalysis:
    def test_blame_returns_entries(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(e, BlameEntry) for e in result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_entry_has_correct_fields(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            entry = result[0]
            assert entry.path
            assert entry.total_lines > 0
            assert entry.top_author
            assert entry.top_author_lines > 0
            assert 0 < entry.top_author_pct <= 100
            assert isinstance(entry.authors, dict)
            assert len(entry.authors) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_multiple_authors(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            # 找到 main.py 的条目
            main_entry = next(e for e in result if "main.py" in e.path)
            assert len(main_entry.authors) >= 2  # Alice 和 Bob 都有贡献
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_sorted_by_lines(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            # 应该按 total_lines 降序
            for i in range(len(result) - 1):
                assert result[i].total_lines >= result[i + 1].total_lines
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_top_n_limit(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis(top_n=1)
            assert len(result) <= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-blame-empty-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_date_fields(self):
        tmpdir = _create_blame_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.blame_analysis()
            main_entry = next(e for e in result if "main.py" in e.path)
            # 应该有日期信息
            assert main_entry.oldest_line_date is not None
            assert main_entry.newest_line_date is not None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── 复杂度趋势测试 ────────────────────────────────────────────


class TestComplexityTrend:
    def test_complexity_returns_points(self):
        tmpdir = _create_growing_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.complexity_trend(period="month")
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(p, ComplexityPoint) for p in result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_fields_populated(self):
        tmpdir = _create_growing_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.complexity_trend(period="month")
            for p in result:
                assert p.period  # 非空
                assert p.total_files >= 0
                assert p.total_lines >= 0
                assert p.commits_in_period >= 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_trend_increasing(self):
        tmpdir = _create_growing_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.complexity_trend(period="month")
            # 总行数应该是非递减的（因为我们在持续添加代码）
            if len(result) >= 2:
                # 后面的月份应该有更多行
                last = result[-1]
                first = result[0]
                assert last.total_lines >= first.total_lines
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_with_time_filter(self):
        tmpdir = _create_growing_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result_all = analyzer.complexity_trend(period="month")
            result_filtered = analyzer.complexity_trend(
                period="month",
                since=datetime(2024, 3, 1),
            )
            assert len(result_filtered) <= len(result_all)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_different_periods(self):
        tmpdir = _create_growing_repo()
        try:
            analyzer = Analyzer(tmpdir)
            monthly = analyzer.complexity_trend(period="month")
            yearly = analyzer.complexity_trend(period="year")
            # 年度应该比月度条目少
            assert len(yearly) <= len(monthly)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_empty_repo(self):
        tmpdir = tempfile.mkdtemp(prefix="git-arch-complexity-empty-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.complexity_trend()
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── 时段对比测试 ──────────────────────────────────────────────


class TestPeriodDiff:
    def test_period_diff_returns_result(self):
        tmpdir = _create_diff_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.period_diff(
                period_a_since=datetime(2024, 1, 1),
                period_a_until=datetime(2024, 3, 31),
                period_b_since=datetime(2024, 4, 1),
                period_b_until=datetime(2024, 6, 30),
            )
            assert isinstance(result, PeriodDiff)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_period_diff_commit_counts(self):
        tmpdir = _create_diff_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.period_diff(
                period_a_since=datetime(2024, 1, 1),
                period_a_until=datetime(2024, 3, 31),
                period_b_since=datetime(2024, 4, 1),
                period_b_until=datetime(2024, 6, 30),
            )
            assert result.period_a_commits > 0
            assert result.period_b_commits > 0
            assert isinstance(result.commits_change, float)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_period_diff_new_authors(self):
        tmpdir = _create_diff_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.period_diff(
                period_a_since=datetime(2024, 1, 1),
                period_a_until=datetime(2024, 3, 31),
                period_b_since=datetime(2024, 4, 1),
                period_b_until=datetime(2024, 6, 30),
            )
            # Bob 和 Charlie 应该是新贡献者
            assert len(result.new_authors) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_period_diff_departed_authors(self):
        tmpdir = _create_diff_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.period_diff(
                period_a_since=datetime(2024, 1, 1),
                period_a_until=datetime(2024, 3, 31),
                period_b_since=datetime(2024, 4, 1),
                period_b_until=datetime(2024, 6, 30),
            )
            # Alice 可能是离开的贡献者
            assert isinstance(result.departed_authors, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_period_diff_most_changed_files(self):
        tmpdir = _create_diff_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.period_diff(
                period_a_since=datetime(2024, 1, 1),
                period_a_until=datetime(2024, 3, 31),
                period_b_since=datetime(2024, 4, 1),
                period_b_until=datetime(2024, 6, 30),
            )
            assert isinstance(result.most_changed_files, list)
            if result.most_changed_files:
                assert isinstance(result.most_changed_files[0], tuple)
                assert len(result.most_changed_files[0]) == 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── CLI 测试 ──────────────────────────────────────────────────


class TestBlameCommand:
    def test_blame_table(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "blame"])
            assert result.exit_code == 0
            assert "代码归属" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_json(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "blame", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) > 0
            assert "path" in data[0]
            assert "total_lines" in data[0]
            assert "top_author" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_csv(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "blame", "--format", "csv"])
            assert result.exit_code == 0
            assert "path" in result.output
            assert "total_lines" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_blame_markdown(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "blame", "--format", "markdown"])
            assert result.exit_code == 0
            assert "|" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestComplexityCommand:
    def test_complexity_table(self):
        tmpdir = _create_growing_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["--repo", tmpdir, "complexity"])
            assert result.exit_code == 0
            assert "复杂度趋势" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_json(self):
        tmpdir = _create_growing_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "complexity", "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert "period" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_csv(self):
        tmpdir = _create_growing_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "complexity", "--format", "csv"]
            )
            assert result.exit_code == 0
            assert "period" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_complexity_period_option(self):
        tmpdir = _create_growing_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main, ["--repo", tmpdir, "complexity", "--period", "year"]
            )
            assert result.exit_code == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestDiffCommand:
    def test_diff_table(self):
        tmpdir = _create_diff_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--repo", tmpdir, "diff",
                    "--a-since", "2024-01-01", "--a-until", "2024-03-31",
                    "--b-since", "2024-04-01", "--b-until", "2024-06-30",
                ],
            )
            assert result.exit_code == 0
            assert "时段对比" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_diff_json(self):
        tmpdir = _create_diff_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--repo", tmpdir, "diff",
                    "--a-since", "2024-01-01", "--a-until", "2024-03-31",
                    "--b-since", "2024-04-01", "--b-until", "2024-06-30",
                    "--format", "json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "period_a_commits" in data
            assert "period_b_commits" in data
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_diff_csv(self):
        tmpdir = _create_diff_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--repo", tmpdir, "diff",
                    "--a-since", "2024-01-01", "--a-until", "2024-03-31",
                    "--b-since", "2024-04-01", "--b-until", "2024-06-30",
                    "--format", "csv",
                ],
            )
            assert result.exit_code == 0
            assert "metric" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_diff_shows_new_authors(self):
        tmpdir = _create_diff_repo()
        try:
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--repo", tmpdir, "diff",
                    "--a-since", "2024-01-01", "--a-until", "2024-03-31",
                    "--b-since", "2024-04-01", "--b-until", "2024-06-30",
                ],
            )
            assert result.exit_code == 0
            assert "新增贡献者" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ── --version 和 --output 测试 ────────────────────────────────


class TestVersion:
    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        from git_archaeologist import __version__
        assert __version__ in result.output


class TestOutputFlag:
    def test_output_writes_to_file(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            outfile = os.path.join(tmpdir, "output.json")
            result = runner.invoke(
                main,
                ["--repo", tmpdir, "blame", "--format", "json", "--output", outfile],
            )
            assert result.exit_code == 0
            assert os.path.exists(outfile)
            with open(outfile) as f:
                data = json.load(f)
            assert isinstance(data, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_output_short_flag(self):
        tmpdir = _create_blame_repo()
        try:
            runner = CliRunner()
            outfile = os.path.join(tmpdir, "out.json")
            result = runner.invoke(
                main,
                ["--repo", tmpdir, "blame", "--format", "json", "-o", outfile],
            )
            assert result.exit_code == 0
            assert os.path.exists(outfile)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_output_complexity(self):
        tmpdir = _create_growing_repo()
        try:
            runner = CliRunner()
            outfile = os.path.join(tmpdir, "complexity.csv")
            result = runner.invoke(
                main,
                ["--repo", tmpdir, "complexity", "--format", "csv", "-o", outfile],
            )
            assert result.exit_code == 0
            assert os.path.exists(outfile)
            with open(outfile) as f:
                content = f.read()
            assert "period" in content
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
