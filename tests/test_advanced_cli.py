"""测试 — 新增 CLI 子命令 (coupling, busfactor, churn, dirs, ages)。"""

from __future__ import annotations

import json
import shutil

import pytest
from click.testing import CliRunner

from git_archaeologist.cli import main
from tests.helpers import (
    create_coupling_repo,
    create_bus_factor_repo,
    create_multi_dir_repo,
    create_test_repo,
)


@pytest.fixture
def runner():
    return CliRunner()


class TestCouplingCLI:
    """coupling 子命令测试。"""

    def test_coupling_table(self, runner):
        tmpdir, _ = create_coupling_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "coupling"])
            assert result.exit_code == 0
            assert "耦合" in result.output or "文件" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_json(self, runner):
        tmpdir, _ = create_coupling_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "coupling", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "file_a" in data[0]
                assert "coupling_strength" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_coupling_min_co_change(self, runner):
        tmpdir, _ = create_coupling_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "coupling", "--min-co-change", "10", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            # 高阈值应该返回更少结果
            assert isinstance(data, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestBusfactorCLI:
    """busfactor 子命令测试。"""

    def test_busfactor_table(self, runner):
        tmpdir, _ = create_bus_factor_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "busfactor"])
            assert result.exit_code == 0
            assert "Bus Factor" in result.output or "贡献者" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_busfactor_json(self, runner):
        tmpdir, _ = create_bus_factor_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "busfactor", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "top_contributor" in data[0]
                assert "bus_factor" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_busfactor_by_dir(self, runner):
        tmpdir, _ = create_bus_factor_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "busfactor", "--entity", "dir", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "src" in data[0]["entity"]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestChurnCLI:
    """churn 子命令测试。"""

    def test_churn_table(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "churn"])
            assert result.exit_code == 0
            assert "Churn" in result.output or "变动" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_churn_json(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "churn", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "churn_ratio" in data[0]
                assert "path" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestDirsCLI:
    """dirs 子命令测试。"""

    def test_dirs_table(self, runner):
        tmpdir, _ = create_multi_dir_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "dirs"])
            assert result.exit_code == 0
            assert "目录" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_dirs_json(self, runner):
        tmpdir, _ = create_multi_dir_repo()
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "dirs", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "path" in data[0]
                assert "file_count" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestAgesCLI:
    """ages 子命令测试。"""

    def test_ages_table(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "ages"])
            assert result.exit_code == 0
            assert "文件年龄" in result.output or "陈旧" in result.output
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_ages_json(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "ages", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            if data:
                assert "stale_days" in data[0]
                assert "primary_author" in data[0]
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_ages_sort_oldest(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "ages", "--sort", "oldest", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_ages_sort_active(self, runner):
        tmpdir, _ = create_test_repo(num_commits=5)
        try:
            result = runner.invoke(main, ["--repo", tmpdir, "ages", "--sort", "active", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
