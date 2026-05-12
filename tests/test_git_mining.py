"""Git 采矿引擎测试。"""

from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime

from helpers import create_test_repo

from git_archaeologist.git_mining import CommitInfo, GitMiner


class TestGitMiner:
    """GitMiner 测试套件。"""

    def setup_method(self):
        self.tmpdir, self.repo = create_test_repo(num_commits=10, num_authors=3, num_files=5)
        self.miner = GitMiner(self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_iter_commits_returns_all(self):
        """应返回所有 commits。"""
        commits = list(self.miner.iter_commits())
        assert len(commits) == 10

    def test_iter_commits_returns_commit_info(self):
        """返回值应为 CommitInfo 实例。"""
        commits = list(self.miner.iter_commits())
        for c in commits:
            assert isinstance(c, CommitInfo)
            assert len(c.sha) == 40
            assert c.author_name in ("Alice", "Bob", "Charlie")
            assert "@" in c.author_email

    def test_iter_commits_with_since_filter(self):
        """since 过滤应生效。"""
        since = datetime(2024, 1, 5)
        commits = list(self.miner.iter_commits(since=since))
        assert all(c.authored_date >= since for c in commits)
        assert len(commits) < 10

    def test_iter_commits_with_until_filter(self):
        """until 过滤应生效。"""
        until = datetime(2024, 1, 3)
        commits = list(self.miner.iter_commits(until=until))
        assert all(c.authored_date <= until for c in commits)
        assert len(commits) < 10

    def test_iter_commits_with_author_filter(self):
        """author 过滤应生效。"""
        commits = list(self.miner.iter_commits(author="Alice"))
        assert all("Alice" in c.author_name for c in commits)

    def test_iter_commits_with_max_count(self):
        """max_count 应限制返回数量。"""
        commits = list(self.miner.iter_commits(max_count=3))
        assert len(commits) == 3

    def test_commit_has_files_changed(self):
        """每个 commit 应包含变更的文件列表。"""
        commits = list(self.miner.iter_commits())
        for c in commits:
            assert len(c.files_changed) > 0

    def test_commit_has_insertions_deletions(self):
        """每个 commit 应有插入/删除行数。"""
        commits = list(self.miner.iter_commits())
        for c in commits:
            assert c.insertions >= 0
            assert c.deletions >= 0

    def test_commit_message(self):
        """commit message 应正确提取。"""
        commits = list(self.miner.iter_commits())
        for c in commits:
            assert c.message.startswith("commit ")

    def test_get_commit_count(self):
        """应返回正确的 commit 数量。"""
        assert self.miner.get_commit_count() == 10

    def test_get_all_authors(self):
        """应返回所有作者及 commit 数。"""
        authors = self.miner.get_all_authors()
        assert len(authors) == 3
        total = sum(count for _, _, count in authors)
        assert total == 10

    def test_get_file_history(self):
        """应返回指定文件的修改历史。"""
        commits = list(self.miner.iter_commits())
        test_file = commits[0].files_changed[0]
        history = self.miner.get_file_history(test_file)
        assert len(history) > 0
        for c in history:
            assert test_file in c.files_changed

    def test_is_dirty_property(self):
        """is_dirty 应返回布尔值。"""
        assert isinstance(self.miner.is_dirty, bool)
