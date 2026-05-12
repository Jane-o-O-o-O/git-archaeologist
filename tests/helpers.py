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


def create_coupling_repo() -> tuple[str, git.Repo]:
    """创建一个用于耦合分析的仓库 — 多个 commit 同时修改多个文件。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-coupling-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 1, 1)

    # 定义每次 commit 要修改的文件组合
    commit_files = [
        ["src/api.py", "src/models.py"],           # 0: api + models 一起改
        ["src/api.py", "src/models.py"],           # 1: api + models 又一起改
        ["src/api.py", "src/models.py"],           # 2: api + models 第三次
        ["src/utils.py", "src/models.py"],         # 3: utils + models
        ["src/utils.py", "src/api.py"],            # 4: utils + api
        ["tests/test_api.py", "src/api.py"],       # 5: test_api + api
        ["tests/test_api.py", "src/api.py"],       # 6: test_api + api
        ["src/config.py"],                         # 7: config 单独改
        ["src/config.py"],                         # 8: config 单独改
        ["src/api.py", "src/models.py", "src/utils.py"],  # 9: 三个一起改
    ]

    for i, files in enumerate(commit_files):
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i}\n'content {i}'\n")
        repo.index.add(files)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}: update {', '.join(files)}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


def create_bus_factor_repo() -> tuple[str, git.Repo]:
    """创建一个用于 Bus Factor 分析的仓库 — 某个作者贡献绝大部分。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-busfactor-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    # Alice 贡献 80%，Bob 贡献 20%
    commits = [
        ("Alice", "alice@example.com", ["src/core.py"]),
        ("Alice", "alice@example.com", ["src/core.py"]),
        ("Alice", "alice@example.com", ["src/core.py"]),
        ("Alice", "alice@example.com", ["src/core.py"]),
        ("Bob", "bob@example.com", ["src/core.py"]),
        ("Alice", "alice@example.com", ["src/utils.py"]),
        ("Alice", "alice@example.com", ["src/utils.py"]),
        ("Alice", "alice@example.com", ["src/utils.py"]),
        ("Alice", "alice@example.com", ["src/utils.py"]),
        ("Bob", "bob@example.com", ["src/utils.py"]),
    ]

    for i, (name, email, files) in enumerate(commits):
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i} by {name}\n'content {i}'\n")
        repo.index.add(files)
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}: update by {name}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo


def create_multi_dir_repo() -> tuple[str, git.Repo]:
    """创建一个有多级目录的仓库。"""
    tmpdir = tempfile.mkdtemp(prefix="git-arch-dirs-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 1, 1)

    files_per_commit = [
        ["src/main.py", "src/lib/utils.py", "tests/test_main.py"],
        ["src/main.py", "src/lib/parser.py"],
        ["src/lib/utils.py", "src/lib/parser.py"],
        ["docs/README.md", "docs/API.md"],
        ["src/main.py", "docs/README.md"],
    ]

    for i, files in enumerate(files_per_commit):
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i}\n")
        repo.index.add(files)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir, repo
