"""测试 — 耦合分析、Bus Factor、Churn、目录统计、文件年龄。"""

from __future__ import annotations

import shutil

from git_archaeologist.analyzer import Analyzer
from tests.helpers import (
    create_bus_factor_repo,
    create_coupling_repo,
    create_multi_dir_repo,
    create_test_repo,
)


class TestCoupling:
    """文件耦合分析测试。"""

    def test_coupling_returns_list(self, tmp_path):
        tmpdir, repo = create_coupling_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.coupling()
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_finds_api_models_pair(self, tmp_path):
        """api.py 和 models.py 应该是耦合最强的对。"""
        tmpdir, repo = create_coupling_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.coupling(min_co_change=1)
            assert len(result) > 0
            # api.py 和 models.py 在 4 个 commit 中一起修改（commit 0,1,2,9）
            top = result[0]
            files = {top.file_a, top.file_b}
            assert "src/api.py" in files
            assert "src/models.py" in files
            assert top.co_change_count >= 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_strength_calculation(self, tmp_path):
        """耦合强度应该在 0~1 之间。"""
        tmpdir, repo = create_coupling_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.coupling(min_co_change=1)
            for pair in result:
                assert 0.0 <= pair.coupling_strength <= 1.0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_min_co_change_filter(self, tmp_path):
        """min_co_change 应该过滤掉低频对。"""
        tmpdir, repo = create_coupling_repo()
        try:
            a = Analyzer(tmpdir)
            result_strict = a.coupling(min_co_change=5)
            result_loose = a.coupling(min_co_change=1)
            assert len(result_strict) <= len(result_loose)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_top_n(self, tmp_path):
        tmpdir, repo = create_coupling_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.coupling(top_n=2, min_co_change=1)
            assert len(result) <= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_empty_repo(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=1, num_files=1)
        try:
            a = Analyzer(tmpdir)
            result = a.coupling(min_co_change=1)
            # 1 commit with 1 file = no pairs
            assert result == []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestBusFactor:
    """Bus Factor 分析测试。"""

    def test_bus_factor_returns_list(self, tmp_path):
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor()
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bus_factor_alice_dominates(self, tmp_path):
        """Alice 贡献 80%，应该是 top contributor。"""
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor()
            assert len(result) > 0
            # core.py 应该有 Alice 作为 top contributor
            core_entries = [e for e in result if e.entity == "src/core.py"]
            assert len(core_entries) == 1
            assert core_entries[0].top_contributor == "Alice"
            assert core_entries[0].top_contributor_pct >= 70
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bus_factor_high_pct_for_dominant(self, tmp_path):
        """主要贡献者占比应该反映实际分布。"""
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor()
            for entry in result:
                assert 0 <= entry.top_contributor_pct <= 100
                assert entry.contributor_count >= 1
                assert entry.bus_factor >= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bus_factor_by_dir(self, tmp_path):
        """按目录分析应该返回目录路径。"""
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor(entity="dir")
            assert len(result) > 0
            paths = [e.entity for e in result]
            assert "src" in paths
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bus_factor_contributors_dict(self, tmp_path):
        """contributors 字典应该包含贡献者及其 commit 数。"""
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor()
            for entry in result:
                assert isinstance(entry.contributors, dict)
                total_in_dict = sum(entry.contributors.values())
                assert total_in_dict > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_bus_factor_top_n(self, tmp_path):
        tmpdir, repo = create_bus_factor_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.bus_factor(top_n=1)
            assert len(result) <= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestChurn:
    """Churn 分析测试。"""

    def test_churn_returns_list(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.churn()
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_churn_entries_have_fields(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.churn()
            assert len(result) > 0
            entry = result[0]
            assert hasattr(entry, "path")
            assert hasattr(entry, "total_insertions")
            assert hasattr(entry, "total_deletions")
            assert hasattr(entry, "net_lines")
            assert hasattr(entry, "change_count")
            assert hasattr(entry, "churn_ratio")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_churn_ratio_non_negative(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=10)
        try:
            a = Analyzer(tmpdir)
            result = a.churn()
            for entry in result:
                assert entry.churn_ratio >= 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_churn_sorted_by_ratio(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=10)
        try:
            a = Analyzer(tmpdir)
            result = a.churn()
            ratios = [e.churn_ratio for e in result]
            assert ratios == sorted(ratios, reverse=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_churn_top_n(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=10, num_files=5)
        try:
            a = Analyzer(tmpdir)
            result = a.churn(top_n=3)
            assert len(result) <= 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestDirStats:
    """目录级统计测试。"""

    def test_dir_stats_returns_list(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats()
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dir_stats_finds_subdirs(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats()
            paths = [d.path for d in result]
            assert "src" in paths
            assert "src/lib" in paths
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dir_stats_has_required_fields(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats()
            assert len(result) > 0
            d = result[0]
            assert hasattr(d, "path")
            assert hasattr(d, "file_count")
            assert hasattr(d, "total_changes")
            assert hasattr(d, "total_insertions")
            assert hasattr(d, "total_deletions")
            assert hasattr(d, "authors")
            assert hasattr(d, "last_modified")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dir_stats_sorted_by_changes(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats()
            changes = [d.total_changes for d in result]
            assert changes == sorted(changes, reverse=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dir_stats_authors_populated(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats()
            for d in result:
                assert len(d.authors) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dir_stats_top_n(self, tmp_path):
        tmpdir, repo = create_multi_dir_repo()
        try:
            a = Analyzer(tmpdir)
            result = a.dir_stats(top_n=2)
            assert len(result) <= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestFileAges:
    """文件年龄分析测试。"""

    def test_file_ages_returns_list(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages()
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_ages_has_required_fields(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages()
            assert len(result) > 0
            entry = result[0]
            assert hasattr(entry, "path")
            assert hasattr(entry, "first_seen")
            assert hasattr(entry, "last_modified")
            assert hasattr(entry, "change_count")
            assert hasattr(entry, "primary_author")
            assert hasattr(entry, "age_days")
            assert hasattr(entry, "stale_days")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_ages_primary_author_set(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=6, num_authors=2)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages()
            for entry in result:
                assert entry.primary_author != ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_ages_sort_stale(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages(sort_by="stale")
            stale_days = [e.stale_days or 0 for e in result]
            assert stale_days == sorted(stale_days, reverse=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_ages_sort_oldest(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=5)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages(sort_by="oldest")
            # oldest first = ascending
            dates = [e.first_seen for e in result if e.first_seen]
            assert dates == sorted(dates)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_file_ages_top_n(self, tmp_path):
        tmpdir, repo = create_test_repo(num_commits=10, num_files=5)
        try:
            a = Analyzer(tmpdir)
            result = a.file_ages(top_n=2)
            assert len(result) <= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
