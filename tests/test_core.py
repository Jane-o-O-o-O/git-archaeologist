"""GitArchaeologist 统一 API 测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime

import pytest
from helpers import create_test_repo

from git_archaeologist.core import FileTypeInfo, GitArchaeologist, RepoSummary


class TestGitArchaeologist:
    """GitArchaeologist 统一 API 测试。"""

    def setup_method(self):
        self.tmpdir, self.repo = create_test_repo(num_commits=12, num_authors=3, num_files=5)
        self.arch = GitArchaeologist(self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_path_property(self):
        """path 应返回绝对路径。"""
        assert os.path.isabs(self.arch.path)
        assert self.arch.path == os.path.abspath(self.tmpdir)

    def test_miner_property(self):
        """miner 应返回 GitMiner 实例。"""
        from git_archaeologist.git_mining import GitMiner
        assert isinstance(self.arch.miner, GitMiner)

    def test_analyzer_property(self):
        """analyzer 应返回 Analyzer 实例。"""
        from git_archaeologist.analyzer import Analyzer
        assert isinstance(self.arch.analyzer, Analyzer)

    def test_summary_returns_repo_summary(self):
        """summary 应返回 RepoSummary。"""
        result = self.arch.summary()
        assert isinstance(result, RepoSummary)
        assert result.stats.total_commits == 12
        assert result.stats.total_authors == 3

    def test_summary_has_all_fields(self):
        """summary 应包含所有必要字段。"""
        result = self.arch.summary()
        assert len(result.top_authors) > 0
        assert len(result.top_hotspots) > 0
        assert len(result.file_types) > 0
        assert len(result.activity_monthly) > 0

    def test_summary_to_dict(self):
        """to_dict 应返回可序列化的 dict。"""
        import json
        result = self.arch.summary()
        d = result.to_dict()
        # 应能 JSON 序列化
        json_str = json.dumps(d, ensure_ascii=False)
        assert "total_commits" in json_str
        assert "top_authors" in json_str

    def test_summary_with_date_filter(self):
        """日期过滤应影响 summary 结果。"""
        all_summary = self.arch.summary()
        filtered = self.arch.summary(since=datetime(2024, 1, 5))
        assert filtered.stats.total_commits < all_summary.stats.total_commits

    def test_analyze_file_types(self):
        """应返回文件类型统计列表。"""
        result = self.arch.analyze_file_types()
        assert len(result) > 0
        assert isinstance(result[0], FileTypeInfo)
        # .py 文件应存在
        extensions = [ft.extension for ft in result]
        assert ".py" in extensions

    def test_analyze_file_types_sorted_by_changes(self):
        """文件类型应按变更次数降序排列。"""
        result = self.arch.analyze_file_types()
        for i in range(len(result) - 1):
            assert result[i].total_changes >= result[i + 1].total_changes

    def test_invalid_repo_raises_value_error(self):
        """无效仓库路径应抛出 ValueError。"""
        with pytest.raises(ValueError, match="不是有效的 Git 仓库"):
            GitArchaeologist("/tmp/nonexistent_repo_abc123")

    def test_empty_repo_summary(self):
        """空仓库应返回零值 summary。"""
        tmpdir = tempfile.mkdtemp()
        try:
            import git
            git.Repo.init(tmpdir)
            arch = GitArchaeologist(tmpdir)
            result = arch.summary()
            assert result.stats.total_commits == 0
            assert result.stats.total_authors == 0
            assert len(result.top_authors) == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

# [2026-04-08] Tests for test_core
class TestTestCore:
    """Test suite for test_core — hotspot detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.fixture = {}
        self.config = {"enabled": True, "debug": False}

    def test_basic_hotspot_detection(self):
        """Test basic hotspot detection functionality."""
        result = process(self.fixture, config=self.config)
        assert result is not None
        assert result.get("status") == "success"

    def test_hotspot_detection_with_empty_input(self):
        """Test hotspot detection with empty input."""
        result = process({}, config=self.config)
        assert result is not None

    def test_hotspot_detection_error_handling(self):
        """Test hotspot detection error handling."""
        with pytest.raises(ValueError):
            process(None, config=self.config)

    def test_hotspot_detection_caching(self):
        """Test hotspot detection caching behavior."""
        result1 = process(self.fixture, config=self.config)
        result2 = process(self.fixture, config=self.config)
        assert result1 == result2
