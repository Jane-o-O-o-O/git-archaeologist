"""测试仓库基础功能"""
import subprocess
import tempfile
import os
import pytest

from git_archaeologist.repo import Repo


class TestRepoValidation:
    """仓库验证测试"""

    def test_valid_git_repo(self, tmp_path):
        """测试：有效 git 仓库应能正确初始化"""
        repo_dir = tmp_path / "valid_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        assert repo.is_valid()

    def test_invalid_directory(self, tmp_path):
        """测试：非 git 目录应返回无效"""
        repo_dir = tmp_path / "not_a_repo"
        repo_dir.mkdir()
        repo = Repo(str(repo_dir))
        assert not repo.is_valid()

    def test_nonexistent_path(self):
        """测试：不存在的路径应返回无效"""
        repo = Repo("/tmp/path_that_does_not_exist_12345")
        assert not repo.is_valid()


class TestRepoInfo:
    """仓库基本信息测试"""

    def _make_repo_with_commits(self, tmp_path, num_commits=3):
        """辅助方法：创建带指定数量提交的仓库"""
        repo_dir = tmp_path / "test_repo"
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
        for i in range(num_commits):
            f = repo_dir / f"file_{i}.txt"
            f.write_text(f"content {i}")
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"提交 {i}", "--allow-empty"],
                cwd=repo_dir, capture_output=True
            )
        return repo_dir

    def test_commit_count(self, tmp_path):
        """测试：正确统计提交数量"""
        repo_dir = self._make_repo_with_commits(tmp_path, 5)
        repo = Repo(str(repo_dir))
        assert repo.commit_count() == 5

    def test_empty_repo_commit_count(self, tmp_path):
        """测试：空仓库提交数为零"""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        assert repo.commit_count() == 0

    def test_contributors_list(self, tmp_path):
        """测试：获取贡献者列表"""
        repo_dir = self._make_repo_with_commits(tmp_path, 2)
        repo = Repo(str(repo_dir))
        contributors = repo.contributors()
        assert len(contributors) >= 1
        assert "Tester <test@test.com>" in contributors
