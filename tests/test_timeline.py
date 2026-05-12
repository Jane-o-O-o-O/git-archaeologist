"""测试提交频率时间线分析功能"""
import subprocess
import pytest
from datetime import datetime, timedelta

from git_archaeologist.repo import Repo
from git_archaeologist.timeline import analyze_timeline, TimelinePeriod, _parse_shortstat


class TestParseShortstat:
    """shortstat 解析测试"""

    def test_full_stat(self):
        line = "3 files changed, 100 insertions(+), 50 deletions(-)"
        files, added, removed = _parse_shortstat(line)
        assert files == 3
        assert added == 100
        assert removed == 50

    def test_insertions_only(self):
        line = "1 file changed, 10 insertions(+)"
        files, added, removed = _parse_shortstat(line)
        assert files == 1
        assert added == 10
        assert removed == 0

    def test_deletions_only(self):
        line = "2 files changed, 5 deletions(-)"
        files, added, removed = _parse_shortstat(line)
        assert files == 2
        assert added == 0
        assert removed == 5

    def test_empty_line(self):
        files, added, removed = _parse_shortstat("")
        assert files == 0
        assert added == 0
        assert removed == 0


class TestAnalyzeTimeline:
    """时间线分析测试"""

    def _make_repo_with_timeline(self, tmp_path):
        """创建含有不同时间提交的仓库"""
        repo_dir = tmp_path / "timeline_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "a@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Alice"], cwd=repo_dir, capture_output=True)

        # 3 个月前的提交
        for i in range(3):
            (repo_dir / f"old_{i}.py").write_text(f"# old {i}\n" * (i + 1))
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            date = (datetime.now() - timedelta(days=90 - i)).strftime("%Y-%m-%dT12:00:00")
            subprocess.run(
                ["git", "commit", "-m", f"old {i}", f"--date={date}"],
                cwd=repo_dir, capture_output=True
            )

        # 上个月的提交
        for i in range(2):
            (repo_dir / f"recent_{i}.py").write_text(f"# recent {i}\n" * (i + 1))
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            date = (datetime.now() - timedelta(days=20 - i)).strftime("%Y-%m-%dT12:00:00")
            subprocess.run(
                ["git", "commit", "-m", f"recent {i}", f"--date={date}"],
                cwd=repo_dir, capture_output=True
            )

        return repo_dir

    def test_returns_periods(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        assert len(periods) >= 1

    def test_month_granularity(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo, granularity="month")
        # 月份格式 YYYY-MM
        for p in periods:
            assert len(p.period) == 7  # YYYY-MM
            assert p.period[4] == "-"

    def test_day_granularity(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo, granularity="day")
        for p in periods:
            assert len(p.period) == 10  # YYYY-MM-DD

    def test_week_granularity(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo, granularity="week")
        for p in periods:
            assert "-W" in p.period  # YYYY-Wnn

    def test_periods_sorted_chronologically(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        keys = [p.period for p in periods]
        assert keys == sorted(keys)

    def test_commit_count_positive(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        for p in periods:
            assert p.commit_count >= 1

    def test_contributor_count_positive(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        for p in periods:
            assert p.contributor_count >= 1

    def test_has_file_stats(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        total_files = sum(p.files_changed for p in periods)
        assert total_files >= 1

    def test_has_line_stats(self, tmp_path):
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        total_added = sum(p.lines_added for p in periods)
        assert total_added >= 1

    def test_empty_repo_returns_empty(self, tmp_path):
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        assert periods == []

    def test_total_commits_match(self, tmp_path):
        """所有时间段的提交数之和应等于仓库总提交数"""
        repo_dir = self._make_repo_with_timeline(tmp_path)
        repo = Repo(str(repo_dir))
        periods = analyze_timeline(repo)
        total_commits = sum(p.commit_count for p in periods)
        assert total_commits == repo.commit_count()
