"""HTML 报告生成器测试。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path

import pytest

from helpers import create_test_repo
from git_archaeologist.report import generate_html_report, save_html_report


class TestReport:
    """HTML 报告测试。"""

    def setup_method(self):
        self.tmpdir, self.repo = create_test_repo(num_commits=10, num_authors=3, num_files=5)
        self.outdir = tempfile.mkdtemp(prefix="git-arch-report-")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.outdir, ignore_errors=True)

    def test_generate_html_report_returns_string(self):
        """应返回有效的 HTML 字符串。"""
        html = generate_html_report(self.tmpdir)
        assert isinstance(html, str)
        assert html.startswith("<!DOCTYPE html>")

    def test_html_contains_repo_stats(self):
        """HTML 应包含仓库统计信息。"""
        html = generate_html_report(self.tmpdir)
        assert "总 Commits" in html
        assert "10" in html

    def test_html_contains_authors(self):
        """HTML 应包含贡献者信息。"""
        html = generate_html_report(self.tmpdir)
        assert "贡献者" in html
        assert "Alice" in html or "Bob" in html

    def test_html_contains_hotspots(self):
        """HTML 应包含热点文件信息。"""
        html = generate_html_report(self.tmpdir)
        assert "热点文件" in html
        assert "module_" in html

    def test_html_contains_filetypes(self):
        """HTML 应包含文件类型分布。"""
        html = generate_html_report(self.tmpdir)
        assert "文件类型" in html
        assert ".py" in html

    def test_html_contains_activity(self):
        """HTML 应包含活跃度趋势。"""
        html = generate_html_report(self.tmpdir)
        assert "活跃度" in html

    def test_html_with_custom_title(self):
        """自定义标题应生效。"""
        html = generate_html_report(self.tmpdir, title="我的项目")
        assert "我的项目" in html

    def test_save_html_report(self):
        """应保存 HTML 文件到指定路径。"""
        out_path = os.path.join(self.outdir, "test_report.html")
        result = save_html_report(out_path, self.tmpdir)
        assert result.exists()
        assert result.suffix == ".html"
        content = result.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_html_valid_structure(self):
        """HTML 应有完整结构标签。"""
        html = generate_html_report(self.tmpdir)
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_html_has_css_styling(self):
        """HTML 应包含内联 CSS。"""
        html = generate_html_report(self.tmpdir)
        assert "<style>" in html
        assert "--bg:" in html  # CSS 变量
