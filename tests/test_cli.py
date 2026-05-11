"""测试 CLI 命令行接口"""
import subprocess
import pytest

from git_archaeologist.cli import build_report, format_fossil, format_stratum, format_hotspot, format_author_stats


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
        assert "3" in report  # 3 commits

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

    def test_format_fossil(self):
        from git_archaeologist.fossils import Fossil
        from datetime import datetime
        fossil = Fossil(
            path="old/file.py",
            name="file.py",
            last_modified=datetime(2020, 1, 1),
            age_days=2000,
        )
        result = format_fossil(fossil)
        assert "file.py" in result
        assert "2000" in result

    def test_format_stratum(self):
        from git_archaeologist.strata import Stratum
        from datetime import datetime
        s = Stratum(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 1),
            commit_count=50,
            contributor_count=3,
            contributors=["A", "B", "C"],
        )
        result = format_stratum(s)
        assert "50" in result
        assert "3" in result

    def test_format_hotspot(self):
        from git_archaeologist.hotspots import HotspotFile
        from datetime import datetime
        h = HotspotFile(
            path="src/main.py",
            modification_count=42,
            unique_authors=5,
            first_seen=datetime(2023, 1, 1),
            last_modified=datetime(2024, 6, 1),
        )
        result = format_hotspot(h)
        assert "src/main.py" in result
        assert "42" in result
        assert "5" in result

    def test_format_author_stats(self):
        from git_archaeologist.authors import AuthorStats
        from datetime import datetime
        a = AuthorStats(
            name="Alice",
            email="alice@test.com",
            commit_count=10,
            first_commit=datetime(2023, 1, 1),
            last_commit=datetime(2024, 6, 1),
            files_touched=15,
            lines_added=500,
            lines_removed=200,
        )
        result = format_author_stats(a)
        assert "Alice" in result
        assert "alice@test.com" in result
        assert "10" in result
        assert "+500" in result
        assert "-200" in result
