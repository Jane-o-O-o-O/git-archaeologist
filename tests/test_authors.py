"""测试贡献者统计功能"""
import subprocess
import pytest

from git_archaeologist.repo import Repo
from git_archaeologist.authors import get_author_stats, AuthorStats


class TestGetAuthorStats:
    """贡献者统计测试"""

    def _make_repo_with_authors(self, tmp_path):
        """创建一个含有多个贡献者的仓库"""
        repo_dir = tmp_path / "authors_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)

        # 作者 A: 3 次提交
        subprocess.run(["git", "config", "user.email", "alice@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Alice"], cwd=repo_dir, capture_output=True)
        for i in range(3):
            f = repo_dir / f"alice_file_{i}.py"
            f.write_text(f"# alice code {i}\n" * (i + 1))
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Alice 提交 {i}"], cwd=repo_dir, capture_output=True)

        # 作者 B: 2 次提交
        subprocess.run(["git", "config", "user.email", "bob@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Bob"], cwd=repo_dir, capture_output=True)
        for i in range(2):
            f = repo_dir / f"bob_file_{i}.py"
            f.write_text(f"# bob code {i}\n" * (i + 1))
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Bob 提交 {i}"], cwd=repo_dir, capture_output=True)

        return repo_dir

    def test_returns_author_list(self, tmp_path):
        """测试：应返回贡献者列表"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        assert len(stats) == 2

    def test_sorted_by_commit_count(self, tmp_path):
        """测试：应按提交数降序排列"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        counts = [s.commit_count for s in stats]
        assert counts == sorted(counts, reverse=True)

    def test_commit_counts_correct(self, tmp_path):
        """测试：提交数应正确"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        by_name = {s.name: s for s in stats}
        assert by_name["Alice"].commit_count == 3
        assert by_name["Bob"].commit_count == 2

    def test_has_email(self, tmp_path):
        """测试：应包含邮箱信息"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        by_name = {s.name: s for s in stats}
        assert by_name["Alice"].email == "alice@test.com"
        assert by_name["Bob"].email == "bob@test.com"

    def test_has_date_range(self, tmp_path):
        """测试：应包含首次和最后提交日期"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        for s in stats:
            assert s.first_commit is not None
            assert s.last_commit is not None
            assert s.first_commit <= s.last_commit

    def test_has_files_touched(self, tmp_path):
        """测试：应包含修改过的文件数"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        by_name = {s.name: s for s in stats}
        assert by_name["Alice"].files_touched == 3
        assert by_name["Bob"].files_touched == 2

    def test_has_lines_added_removed(self, tmp_path):
        """测试：应包含增删行数"""
        repo_dir = self._make_repo_with_authors(tmp_path)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        for s in stats:
            assert s.lines_added >= 1
            # lines_removed 可能为 0（首次创建文件没有删除行）

    def test_empty_repo_returns_empty(self, tmp_path):
        """测试：空仓库应返回空列表"""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        stats = get_author_stats(repo)
        assert stats == []
