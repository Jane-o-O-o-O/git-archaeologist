"""测试地层分析功能 —— 分析开发活跃期"""
import subprocess
import pytest
from datetime import datetime, timedelta

from git_archaeologist.repo import Repo
from git_archaeologist.strata import analyze_strata, Stratum


class TestAnalyzeStrata:
    """开发活跃期分析测试"""

    def _make_repo_with_commits_in_periods(self, tmp_path):
        """创建一个含有不同时间段提交的仓库"""
        repo_dir = tmp_path / "strata_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Tester"],
            cwd=repo_dir, capture_output=True
        )

        # 创建一个空提交序列（模拟不同时期的开发）
        # 第一阶段：100天前，3次提交
        for i in range(3):
            f = repo_dir / f"file_a_{i}.txt"
            f.write_text(f"content a {i}")
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            date = (datetime.now() - timedelta(days=100 - i)).strftime("%Y-%m-%dT12:00:00")
            subprocess.run(
                ["git", "commit", "-m", f"阶段A-{i}", f"--date={date}", "--allow-empty"],
                cwd=repo_dir, capture_output=True
            )

        # 第二阶段：50天前，2次提交
        for i in range(2):
            f = repo_dir / f"file_b_{i}.txt"
            f.write_text(f"content b {i}")
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            date = (datetime.now() - timedelta(days=50 - i)).strftime("%Y-%m-%dT12:00:00")
            subprocess.run(
                ["git", "commit", "-m", f"阶段B-{i}", f"--date={date}", "--allow-empty"],
                cwd=repo_dir, capture_output=True
            )

        return repo_dir

    def test_strata_returns_periods(self, tmp_path):
        """测试：应返回多个开发活跃期"""
        repo_dir = self._make_repo_with_commits_in_periods(tmp_path)
        repo = Repo(str(repo_dir))
        strata = analyze_strata(repo)
        assert len(strata) >= 1

    def test_stratum_has_dates(self, tmp_path):
        """测试：每个地层应包含开始和结束日期"""
        repo_dir = self._make_repo_with_commits_in_periods(tmp_path)
        repo = Repo(str(repo_dir))
        strata = analyze_strata(repo)
        for s in strata:
            assert s.start_date is not None
            assert s.end_date is not None
            assert s.start_date <= s.end_date

    def test_stratum_has_commit_count(self, tmp_path):
        """测试：每个地层应包含提交数量"""
        repo_dir = self._make_repo_with_commits_in_periods(tmp_path)
        repo = Repo(str(repo_dir))
        strata = analyze_strata(repo)
        for s in strata:
            assert s.commit_count >= 1

    def test_stratum_has_contributor_count(self, tmp_path):
        """测试：每个地层应包含贡献者数量"""
        repo_dir = self._make_repo_with_commits_in_periods(tmp_path)
        repo = Repo(str(repo_dir))
        strata = analyze_strata(repo)
        for s in strata:
            assert s.contributor_count >= 1

    def test_empty_repo_returns_empty(self, tmp_path):
        """测试：空仓库应返回空列表"""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        strata = analyze_strata(repo)
        assert strata == []
