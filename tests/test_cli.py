"""测试 CLI 命令行接口"""
import json
import subprocess
import pytest

from git_archaeologist.cli import build_report, _parse_format
from git_archaeologist.output import OutputFormat


class TestParseFormat:
    """格式解析测试"""

    def test_json(self):
        assert _parse_format("json") == OutputFormat.JSON

    def test_terminal(self):
        assert _parse_format("terminal") == OutputFormat.TERMINAL

    def test_default(self):
        assert _parse_format("anything") == OutputFormat.TERMINAL


class TestCLIHelpers:
    """CLI 辅助函数测试"""

    def _make_repo(self, tmp_path):
        repo_dir = tmp_path / "cli_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True)
        for i in range(3):
            (repo_dir / f"f{i}.py").write_text(f"# {i}")
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"提交{i}"], cwd=repo_dir, capture_output=True)
        return repo_dir

    def test_build_report_has_header(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo)
        assert "Git 考古报告" in report

    def test_build_report_has_commit_count(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo)
        assert "3" in report

    def test_build_report_has_contributors(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo)
        assert "Tester" in report

    def test_build_report_has_hotspots(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo)
        assert "热点文件" in report

    def test_build_report_has_author_stats(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo)
        assert "贡献者统计" in report

    def test_build_report_json_format(self, tmp_path):
        """测试：JSON 格式报告应为有效 JSON"""
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo, fmt=OutputFormat.JSON)
        data = json.loads(report)
        assert "summary" in data
        assert "hotspots" in data
        assert "fossils" in data
        assert "strata" in data
        assert "authors" in data

    def test_build_report_json_has_commit_count(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo, fmt=OutputFormat.JSON)
        data = json.loads(report)
        assert data["summary"]["commit_count"] == 3

    def test_build_report_json_has_contributors(self, tmp_path):
        repo_dir = self._make_repo(tmp_path)
        from git_archaeologist.repo import Repo
        repo = Repo(str(repo_dir))
        report = build_report(repo, fmt=OutputFormat.JSON)
        data = json.loads(report)
        assert data["summary"]["contributor_count"] >= 1
        assert any("Tester" in c for c in data["summary"]["contributors"])
