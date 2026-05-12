"""CLI 测试。"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path

from click.testing import CliRunner
from helpers import create_test_repo

from git_archaeologist.cli import main


class TestCLI:
    """CLI 子命令测试。"""

    def setup_method(self):
        self.tmpdir, self.repo = create_test_repo(num_commits=10, num_authors=3, num_files=5)
        self.runner = CliRunner()
        self.outdir = tempfile.mkdtemp(prefix="git-arch-cli-")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.outdir, ignore_errors=True)

    def test_stats_table(self):
        """stats 子命令 table 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "stats"])
        assert result.exit_code == 0
        assert "总 Commits" in result.output
        assert "10" in result.output

    def test_stats_json(self):
        """stats 子命令 JSON 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "stats", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_commits"] == 10
        assert data["total_authors"] == 3

    def test_authors_table(self):
        """authors 子命令 table 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "authors"])
        assert result.exit_code == 0
        assert "贡献者排行" in result.output

    def test_authors_json(self):
        """authors 子命令 JSON 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "authors", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 3
        assert "name" in data[0]

    def test_hotspots_table(self):
        """hotspots 子命令 table 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "hotspots"])
        assert result.exit_code == 0
        assert "热点文件" in result.output

    def test_hotspots_json(self):
        """hotspots 子命令 JSON 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "hotspots", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) > 0
        assert "path" in data[0]

    def test_activity_table(self):
        """activity 子命令 table 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "activity"])
        assert result.exit_code == 0
        assert "活跃度" in result.output

    def test_activity_json(self):
        """activity 子命令 JSON 输出。"""
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "activity", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_stats_with_since(self):
        """--since 参数应影响结果。"""
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "stats", "--since", "2024-01-05", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_commits"] < 10

    def test_authors_top_n(self):
        """--top 参数应限制结果数量。"""
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "authors", "--top", "2", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_help(self):
        """--help 应正常输出。"""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Git Archaeologist" in result.output

    def test_filetypes_table(self):
        """filetypes 子命令 table 输出。"""
        result = self.runner.invoke(main, ["--repo", self.tmpdir, "filetypes"])
        assert result.exit_code == 0
        assert "文件类型" in result.output
        assert ".py" in result.output

    def test_filetypes_json(self):
        """filetypes 子命令 JSON 输出。"""
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "filetypes", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "extension" in data[0]
        assert "file_count" in data[0]

    def test_report_generates_html(self):
        """report 子命令应生成 HTML 文件。"""
        out_path = os.path.join(self.outdir, "output.html")
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "report", "-o", out_path]
        )
        assert result.exit_code == 0
        assert "报告已生成" in result.output
        assert Path(out_path).exists()
        content = Path(out_path).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_report_with_title(self):
        """report 子命令应支持自定义标题。"""
        out_path = os.path.join(self.outdir, "titled.html")
        result = self.runner.invoke(
            main, ["--repo", self.tmpdir, "report", "-o", out_path, "--title", "测试标题"]
        )
        assert result.exit_code == 0
        content = Path(out_path).read_text(encoding="utf-8")
        assert "测试标题" in content
