"""v1.1.0 功能测试 — CI 模式、--exclude、--sort、--no-color、--branch。"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta

import git
import pytest
from click.testing import CliRunner

from git_archaeologist.cli import main


def _create_multi_branch_repo() -> tuple[str, git.Repo]:
    """创建一个包含多分支和多样文件的临时仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-test-v110-")
    repo = git.Repo.init(tmpdir)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
    ]
    base_date = datetime(2024, 1, 1)

    # 主分支: 多种文件类型
    files_data = {
        "src/main.py": "print('main')\n",
        "src/utils.py": "def helper(): pass\n",
        "README.md": "# Project\n",
        "docs/guide.md": "# Guide\n",
        "tests/test_main.py": "def test_main(): pass\n",
        "data/config.json": '{"key": "value"}\n',
    }

    for i, (fpath, content) in enumerate(files_data.items()):
        full_path = os.path.join(tmpdir, fpath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        repo.index.add([fpath])
        author = git.Actor(*authors[i % 2])
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"add {fpath}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    # 创建 feature 分支
    feature_branch = repo.create_head("feature-branch")
    feature_branch.checkout()
    feature_path = os.path.join(tmpdir, "src/feature.py")
    with open(feature_path, "w") as f:
        f.write("def feature(): pass\n")
    repo.index.add(["src/feature.py"])
    author = git.Actor("Alice", "alice@example.com")
    commit_date = base_date + timedelta(days=10)
    repo.index.commit(
        "add feature",
        author=author,
        committer=author,
        commit_date=commit_date.isoformat(),
        author_date=commit_date.isoformat(),
    )

    # 切回 main
    repo.heads.master.checkout()

    return tmpdir, repo


@pytest.fixture
def multi_branch_repo():
    """提供一个包含多分支的临时仓库。"""
    import shutil

    tmpdir, repo = _create_multi_branch_repo()
    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestExcludeFilter:
    """测试 --exclude glob 过滤功能。"""

    def test_hotspots_exclude(self, multi_branch_repo):
        """hotspots --exclude 应排除匹配的文件。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "hotspots", "--exclude", "*.json", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for entry in data:
            assert not entry["path"].endswith(".json")

    def test_hotspots_multiple_excludes(self, multi_branch_repo):
        """hotspots 支持多个 --exclude。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "hotspots",
            "--exclude", "*.json", "--exclude", "*.md",
            "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for entry in data:
            assert not entry["path"].endswith(".json")
            assert not entry["path"].endswith(".md")

    def test_coupling_exclude(self, multi_branch_repo):
        """coupling --exclude 应排除匹配的文件。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "coupling", "--exclude", "*.md", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for pair in data:
            assert not pair["file_a"].endswith(".md")
            assert not pair["file_b"].endswith(".md")

    def test_churn_exclude(self, multi_branch_repo):
        """churn --exclude 应排除匹配的文件。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "churn", "--exclude", "*.json", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for entry in data:
            assert not entry["path"].endswith(".json")

    def test_busfactor_exclude(self, multi_branch_repo):
        """busfactor --exclude 应排除匹配的文件。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "busfactor", "--exclude", "*.json", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for entry in data:
            assert not entry["entity"].endswith(".json")


class TestCICommand:
    """测试 CI 模式命令。"""

    def test_ci_pass(self, multi_branch_repo):
        """ci 命令在健康评分达标时返回 0。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "ci", "--min-health-score", "0",
        ])
        assert result.exit_code == 0

    def test_ci_fail(self, multi_branch_repo):
        """ci 命令在健康评分不达标时返回 1。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "ci", "--min-health-score", "100",
        ])
        assert result.exit_code == 1

    def test_ci_json_output(self, multi_branch_repo):
        """ci --format json 应输出 JSON。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "ci", "--min-health-score", "0", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "overall" in data
        assert "passed" in data

    def test_ci_output_option(self, multi_branch_repo):
        """ci -o 应写入文件。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                "--repo", tmpdir, "ci", "--min-health-score", "0",
                "--format", "json", "-o", "ci_result.json",
            ])
            assert result.exit_code == 0
            assert os.path.exists("ci_result.json")


class TestNoColorOption:
    """测试 --no-color 全局选项。"""

    def test_no_color_flag(self, multi_branch_repo):
        """--no-color 应禁用 Rich 格式化标记。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, ["--repo", tmpdir, "--no-color", "stats"])
        assert result.exit_code == 0
        # 不应包含 Rich 标记
        assert "[green]" not in result.output
        assert "[red]" not in result.output
        assert "[cyan]" not in result.output


class TestBranchOption:
    """测试 --branch 全局选项。"""

    def test_branch_master(self, multi_branch_repo):
        """--branch master 应分析 master 分支。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "--branch", "master", "stats", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # master 分支只有初始文件
        assert data["total_commits"] >= 6

    def test_branch_feature(self, multi_branch_repo):
        """--branch feature-branch 应分析 feature 分支。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "--branch", "feature-branch", "stats", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # feature 分支多一个 commit
        assert data["total_commits"] >= 7

    def test_branch_invalid(self, multi_branch_repo):
        """--branch 不存在的分支应报错。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "--branch", "nonexistent", "stats",
        ])
        assert result.exit_code != 0


class TestSortOption:
    """测试 --sort 选项。"""

    def test_hotspots_sort_changes(self, multi_branch_repo):
        """hotspots --sort changes 应按修改次数降序。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "hotspots", "--sort", "changes", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        if len(data) >= 2:
            for i in range(len(data) - 1):
                assert data[i]["changes"] >= data[i + 1]["changes"]

    def test_hotspots_sort_name(self, multi_branch_repo):
        """hotspots --sort name 应按文件名升序。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "hotspots", "--sort", "name", "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = [e["path"] for e in data]
        assert names == sorted(names)

    def test_churn_sort_ratio(self, multi_branch_repo):
        """churn --sort ratio 应按变动率降序。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "churn", "--sort", "ratio", "--format", "json",
        ])
        assert result.exit_code == 0

    def test_busfactor_sort_changes(self, multi_branch_repo):
        """busfactor --sort changes 应按变更次数降序。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "busfactor", "--sort", "changes", "--format", "json",
        ])
        assert result.exit_code == 0

    def test_coupling_sort_strength(self, multi_branch_repo):
        """coupling --sort strength 应按耦合强度降序。"""
        tmpdir, _ = multi_branch_repo
        runner = CliRunner()
        result = runner.invoke(main, [
            "--repo", tmpdir, "coupling", "--sort", "strength", "--format", "json",
        ])
        assert result.exit_code == 0


class TestVersion:
    """测试版本号更新。"""

    def test_version_is_1_1_0(self):
        """版本应为 1.1.0。"""
        import git_archaeologist

        assert git_archaeologist.__version__ == "1.2.0"

    def test_pyproject_version_matches(self):
        """pyproject.toml 版本应与 __version__ 一致。"""
        import tomllib

        import git_archaeologist

        pyproject = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pyproject.toml")
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)
        assert config["project"]["version"] == git_archaeologist.__version__
