"""核心分析引擎测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime

from helpers import create_test_repo

from git_archaeologist.analyzer import Analyzer, AuthorStats, HotspotFile


class TestAnalyzer:
    """Analyzer 测试套件。"""

    def setup_method(self):
        self.tmpdir, self.repo = create_test_repo(num_commits=10, num_authors=3, num_files=5)
        self.analyzer = Analyzer(self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_repo_stats_basic(self):
        """应返回正确的仓库统计。"""
        s = self.analyzer.repo_stats()
        assert s.total_commits == 10
        assert s.total_authors == 3
        assert s.total_insertions > 0
        assert s.first_commit_date is not None
        assert s.last_commit_date is not None
        assert s.active_days > 0

    def test_repo_stats_with_date_filter(self):
        """日期过滤应影响统计结果。"""
        s_all = self.analyzer.repo_stats()
        s_filtered = self.analyzer.repo_stats(since=datetime(2024, 1, 5))
        assert s_filtered.total_commits < s_all.total_commits

    def test_repo_stats_empty(self):
        """无 commit 时应返回零值统计。"""
        tmpdir = tempfile.mkdtemp()
        try:
            import git
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            s = analyzer.repo_stats()
            assert s.total_commits == 0
            assert s.total_authors == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_author_stats_returns_sorted_list(self):
        """应返回按 commit 数排序的贡献者列表。"""
        result = self.analyzer.author_stats()
        assert len(result) == 3
        assert isinstance(result[0], AuthorStats)
        for i in range(len(result) - 1):
            assert result[i].commit_count >= result[i + 1].commit_count

    def test_author_stats_correct_fields(self):
        """每个 AuthorStats 应有正确的字段。"""
        result = self.analyzer.author_stats()
        for a in result:
            assert a.commit_count > 0
            assert a.insertions >= 0
            assert a.first_commit is not None
            assert a.last_commit is not None
            assert a.avg_insertions_per_commit >= 0

    def test_hotspots_returns_sorted_list(self):
        """应返回按修改次数排序的热点文件列表。"""
        result = self.analyzer.hotspots()
        assert len(result) > 0
        assert isinstance(result[0], HotspotFile)
        for i in range(len(result) - 1):
            assert result[i].change_count >= result[i + 1].change_count

    def test_hotspots_with_ignore_globs(self):
        """ignore_globs 应过滤文件。"""
        result_all = self.analyzer.hotspots()
        result_filtered = self.analyzer.hotspots(ignore_globs=["*module_0*"])
        total_all = sum(f.change_count for f in result_all)
        total_filtered = sum(f.change_count for f in result_filtered)
        assert total_filtered < total_all

    def test_commit_activity_by_month(self):
        """按月统计应返回正确格式。"""
        data = self.analyzer.commit_activity_by_period(period="month")
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "2024-01" in data

    def test_commit_activity_by_day(self):
        """按天统计应返回更多条目。"""
        by_day = self.analyzer.commit_activity_by_period(period="day")
        by_month = self.analyzer.commit_activity_by_period(period="month")
        assert len(by_day) >= len(by_month)
