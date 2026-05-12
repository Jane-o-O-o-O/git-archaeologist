"""测试输出格式化模块 —— JSON 和终端格式化"""
import json
import pytest
from datetime import datetime

from git_archaeologist.output import (
    OutputFormat,
    format_fossil,
    format_stratum,
    format_hotspot,
    format_author_stats,
    format_fossils_list,
    format_hotspots_list,
    format_author_stats_list,
    format_strata_list,
)
from git_archaeologist.fossils import Fossil
from git_archaeologist.strata import Stratum
from git_archaeologist.hotspots import HotspotFile
from git_archaeologist.authors import AuthorStats


class TestOutputFormat:
    """输出格式枚举测试"""

    def test_has_terminal_format(self):
        assert OutputFormat.TERMINAL == "terminal"

    def test_has_json_format(self):
        assert OutputFormat.JSON == "json"


class TestFormatFossil:
    """化石格式化测试"""

    def _make_fossil(self):
        return Fossil(
            path="old/file.py",
            name="file.py",
            last_modified=datetime(2023, 1, 15, 10, 30, 0),
            age_days=1200,
        )

    def test_terminal_format(self):
        fossil = self._make_fossil()
        result = format_fossil(fossil, OutputFormat.TERMINAL)
        assert "file.py" in result
        assert "1200" in result
        assert "2023-01-15" in result

    def test_json_format(self):
        fossil = self._make_fossil()
        result = format_fossil(fossil, OutputFormat.JSON)
        data = json.loads(result)
        assert data["path"] == "old/file.py"
        assert data["name"] == "file.py"
        assert data["age_days"] == 1200
        assert data["last_modified"] == "2023-01-15T10:30:00"


class TestFormatHotspot:
    """热点文件格式化测试"""

    def _make_hotspot(self):
        return HotspotFile(
            path="src/main.py",
            modification_count=42,
            unique_authors=5,
            first_seen=datetime(2023, 3, 1, 8, 0, 0),
            last_modified=datetime(2024, 6, 15, 14, 30, 0),
        )

    def test_terminal_format(self):
        h = self._make_hotspot()
        result = format_hotspot(h, OutputFormat.TERMINAL)
        assert "src/main.py" in result
        assert "42" in result
        assert "5" in result

    def test_json_format(self):
        h = self._make_hotspot()
        result = format_hotspot(h, OutputFormat.JSON)
        data = json.loads(result)
        assert data["path"] == "src/main.py"
        assert data["modification_count"] == 42
        assert data["unique_authors"] == 5
        assert data["first_seen"] == "2023-03-01T08:00:00"
        assert data["last_modified"] == "2024-06-15T14:30:00"


class TestFormatAuthorStats:
    """贡献者统计格式化测试"""

    def _make_author(self):
        return AuthorStats(
            name="Alice",
            email="alice@test.com",
            commit_count=10,
            first_commit=datetime(2023, 1, 1),
            last_commit=datetime(2024, 6, 1),
            files_touched=15,
            lines_added=500,
            lines_removed=200,
        )

    def test_terminal_format(self):
        a = self._make_author()
        result = format_author_stats(a, OutputFormat.TERMINAL)
        assert "Alice" in result
        assert "alice@test.com" in result
        assert "+500" in result
        assert "-200" in result

    def test_json_format(self):
        a = self._make_author()
        result = format_author_stats(a, OutputFormat.JSON)
        data = json.loads(result)
        assert data["name"] == "Alice"
        assert data["email"] == "alice@test.com"
        assert data["commit_count"] == 10
        assert data["lines_added"] == 500
        assert data["lines_removed"] == 200
        assert data["files_touched"] == 15
        assert data["first_commit"] == "2023-01-01T00:00:00"
        assert data["last_commit"] == "2024-06-01T00:00:00"


class TestFormatStratum:
    """地层格式化测试"""

    def _make_stratum(self):
        return Stratum(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 1),
            commit_count=50,
            contributor_count=3,
            contributors=["A", "B", "C"],
        )

    def test_terminal_format(self):
        s = self._make_stratum()
        result = format_stratum(s, OutputFormat.TERMINAL)
        assert "50" in result
        assert "3" in result

    def test_json_format(self):
        s = self._make_stratum()
        result = format_stratum(s, OutputFormat.JSON)
        data = json.loads(result)
        assert data["commit_count"] == 50
        assert data["contributor_count"] == 3
        assert data["contributors"] == ["A", "B", "C"]
        assert data["start_date"] == "2024-01-01T00:00:00"
        assert data["end_date"] == "2024-03-01T00:00:00"


class TestFormatList:
    """列表格式化测试"""

    def _make_fossils(self):
        return [
            Fossil(path="a.py", name="a.py", last_modified=datetime(2020, 1, 1), age_days=2000),
            Fossil(path="b.py", name="b.py", last_modified=datetime(2021, 6, 1), age_days=1500),
        ]

    def test_fossils_list_json(self):
        fossils = self._make_fossils()
        result = format_fossils_list(fossils, OutputFormat.JSON)
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["path"] == "a.py"
        assert data[1]["path"] == "b.py"

    def test_fossils_list_terminal(self):
        fossils = self._make_fossils()
        result = format_fossils_list(fossils, OutputFormat.TERMINAL)
        assert "a.py" in result
        assert "b.py" in result

    def test_hotspots_list_json(self):
        hotspots = [
            HotspotFile(
                path="main.py", modification_count=10,
                unique_authors=2, first_seen=datetime(2023, 1, 1),
                last_modified=datetime(2024, 1, 1),
            ),
        ]
        result = format_hotspots_list(hotspots, OutputFormat.JSON)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["path"] == "main.py"

    def test_author_stats_list_json(self):
        authors = [
            AuthorStats(
                name="Bob", email="b@t.com", commit_count=5,
                first_commit=datetime(2023, 1, 1), last_commit=datetime(2024, 1, 1),
                files_touched=10, lines_added=100, lines_removed=50,
            ),
        ]
        result = format_author_stats_list(authors, OutputFormat.JSON)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["name"] == "Bob"

    def test_strata_list_json(self):
        strata = [
            Stratum(
                start_date=datetime(2024, 1, 1), end_date=datetime(2024, 3, 1),
                commit_count=50, contributor_count=3, contributors=["A", "B", "C"],
            ),
        ]
        result = format_strata_list(strata, OutputFormat.JSON)
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["commit_count"] == 50


class TestEmptyLists:
    """空列表格式化测试"""

    def test_empty_fossils_json(self):
        result = format_fossils_list([], OutputFormat.JSON)
        data = json.loads(result)
        assert data == []

    def test_empty_hotspots_json(self):
        result = format_hotspots_list([], OutputFormat.JSON)
        data = json.loads(result)
        assert data == []

    def test_empty_authors_json(self):
        result = format_author_stats_list([], OutputFormat.JSON)
        data = json.loads(result)
        assert data == []

    def test_empty_strata_json(self):
        result = format_strata_list([], OutputFormat.JSON)
        data = json.loads(result)
        assert data == []
