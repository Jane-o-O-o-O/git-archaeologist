"""v1.0.0 功能测试 — __main__.py、py.typed、版本号。"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestMainModule:
    """python -m git_archaeologist 支持测试。"""

    def test_main_module_exists(self):
        """__main__.py 应存在且可导入。"""
        spec = importlib.util.find_spec("git_archaeologist.__main__")
        assert spec is not None, "__main__.py 模块应可被发现"

    def test_main_module_executable(self):
        """python -m git_archaeologist --version 应正常输出版本号。"""
        result = subprocess.run(
            [sys.executable, "-m", "git_archaeologist", "--version"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0, f"命令失败: {result.stderr}"
        assert "1.1.0" in result.stdout


class TestPyTypedMarker:
    """PEP 561 py.typed 标记测试。"""

    def test_py_typed_exists(self):
        """py.typed 标记文件应存在于包目录中。"""
        import git_archaeologist

        pkg_dir = os.path.dirname(git_archaeologist.__file__)
        py_typed = os.path.join(pkg_dir, "py.typed")
        assert os.path.exists(py_typed), "py.typed 文件应存在于包目录中"

    def test_py_typed_is_file(self):
        """py.typed 应为普通文件。"""
        import git_archaeologist

        pkg_dir = os.path.dirname(git_archaeologist.__file__)
        py_typed = os.path.join(pkg_dir, "py.typed")
        assert os.path.isfile(py_typed)


class TestVersionConsistency:
    """版本号一致性测试。"""

    def test_version_is_1_0_0(self):
        """版本号应为 1.0.0。"""
        from git_archaeologist import __version__

        assert __version__ == "1.1.0"

    def test_pyproject_version_matches(self):
        """pyproject.toml 版本号应与 __version__ 一致。"""
        import tomllib

        from git_archaeologist import __version__

        pyproject_path = os.path.join(
            os.path.dirname(__file__), "..", "pyproject.toml"
        )
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        assert data["project"]["version"] == __version__

    def test_all_exports_present(self):
        """__all__ 应导出所有公开 API。"""
        import git_archaeologist

        expected = {
            "Analyzer",
            "AuthorStats",
            "BlameEntry",
            "BranchEntry",
            "BusFactorEntry",
            "ChurnEntry",
            "CoAuthorPair",
            "CommitInfo",
            "CommitMessageStats",
            "ComplexityPoint",
            "ContributorTimelinePoint",
            "CouplingPair",
            "DirStats",
            "FileAgeEntry",
            "FileChange",
            "GitArchaeologist",
            "GitMiner",
            "HealthScore",
            "HotspotFile",
            "PeriodDiff",
            "RepoInfo",
            "RepoStats",
            "RepoSummary",
            "SearchMatch",
            "TagEntry",
        }
        actual = set(git_archaeologist.__all__)
        assert expected == actual, f"缺少: {expected - actual}, 多余: {actual - expected}"
