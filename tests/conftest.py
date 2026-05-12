"""测试辅助工具 — 创建临时 git 仓库用于测试。"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import git


def create_test_repo(
    num_commits: int = 10,
    num_authors: int = 3,
    num_files: int = 5,
) -> tuple[str, git.Repo]:
    """创建一个包含已知 commit 历史的临时 git 仓库。

    Returns:
        (repo_path, repo) 元组
    """
    tmpdir = tempfile.mkdtemp(prefix="git-arch-test-")
    repo = git.Repo.init(tmpdir)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ]
    files = [f"src/module_{i}.py" for i in range(num_files)]

    base_date = datetime(2024, 1, 1)

    for i in range(num_commits):
        author_idx = i % num_authors
        name, email = authors[author_idx]
        file_idx = i % num_files
        filepath = os.path.join(tmpdir, files[file_idx])

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 写入内容
        content = f"# Module {file_idx}\n# Commit {i}\nprint('hello {i}')\n"
        with open(filepath, "w") as f:
            f.write(content)

        # 添加并提交
        repo.index.add([files[file_idx]])
        commit_date = base_date + timedelta(days=i)
        author = git.Actor(name, email)
        repo.index.commit(
            f"commit {i}: update {files[file_idx]}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


import pytest  # noqa: E402


@pytest.fixture
def test_repo():
    """提供一个临时测试仓库，测试后自动清理。"""
    import shutil
    tmpdir, repo = create_test_repo()
    yield tmpdir, repo
    shutil.rmtree(tmpdir, ignore_errors=True)
