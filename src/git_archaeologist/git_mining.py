"""Git 采矿引擎 — 从仓库历史中提取 commit、文件变更、贡献者数据。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

import git


@dataclass
class CommitInfo:
    """单个 commit 的结构化信息。"""

    sha: str
    author_name: str
    author_email: str
    authored_date: datetime
    committer_name: str
    committer_email: str
    committed_date: datetime
    message: str
    files_changed: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class FileChange:
    """文件级别的变更记录。"""

    path: str
    insertions: int = 0
    deletions: int = 0
    change_type: str = "M"  # A(dd), M(odify), D(elete), R(ename)


class GitMiner:
    """从 Git 仓库中挖掘历史数据。"""

    def __init__(self, repo_path: str = ".") -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.repo = git.Repo(self.repo_path)

    @property
    def is_dirty(self) -> bool:
        """仓库是否有未提交的变更。"""
        return self.repo.is_dirty()

    @property
    def has_commits(self) -> bool:
        """仓库是否至少有一个 commit。"""
        try:
            _ = self.repo.head.commit
            return True
        except (ValueError, TypeError):
            return False

    def iter_commits(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        path: str | None = None,
        max_count: int | None = None,
    ) -> Iterator[CommitInfo]:
        """遍历 commit 历史。

        Args:
            since: 起始时间（包含）
            until: 结束时间（包含）
            author: 按作者过滤（name 或 email 包含即可）
            path: 按文件路径过滤
            max_count: 最大返回数量
        """
        if not self.has_commits:
            return

        kwargs: dict = {}
        if since:
            kwargs["since"] = since.isoformat()
        if until:
            kwargs["until"] = until.isoformat()
        if author:
            kwargs["author"] = author
        if path:
            kwargs["paths"] = path
        if max_count:
            kwargs["max_count"] = max_count

        for commit in self.repo.iter_commits(**kwargs):
            yield self._parse_commit(commit)

    def _parse_commit(self, commit: git.Commit) -> CommitInfo:
        """解析单个 git.Commit 对象为 CommitInfo。"""
        stats = commit.stats.total
        files = list(commit.stats.files.keys())
        return CommitInfo(
            sha=commit.hexsha,
            author_name=commit.author.name or "",
            author_email=commit.author.email or "",
            authored_date=datetime.fromtimestamp(commit.authored_date),
            committer_name=commit.committer.name or "",
            committer_email=commit.committer.email or "",
            committed_date=datetime.fromtimestamp(commit.committed_date),
            message=commit.message.strip(),
            files_changed=files,
            insertions=stats.get("insertions", 0),
            deletions=stats.get("deletions", 0),
        )

    def get_file_diff_details(self, commit_sha: str) -> list[FileChange]:
        """获取单个 commit 中每个文件的精确 insertions/deletions。

        Args:
            commit_sha: commit 的 SHA 值

        Returns:
            FileChange 列表，每个文件一个条目
        """
        commit = self.repo.commit(commit_sha)
        changes: list[FileChange] = []
        for fpath, detail in commit.stats.files.items():
            changes.append(
                FileChange(
                    path=fpath,
                    insertions=detail.get("insertions", 0),
                    deletions=detail.get("deletions", 0),
                    change_type=detail.get("change_type", "M"),
                )
            )
        return changes

    def iter_commits_with_details(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        path: str | None = None,
        max_count: int | None = None,
    ) -> Iterator[tuple[CommitInfo, list[FileChange]]]:
        """遍历 commit 历史并附带每个文件的精确 diff 详情。

        Yields:
            (CommitInfo, [FileChange, ...]) 元组
        """
        if not self.has_commits:
            return

        kwargs: dict = {}
        if since:
            kwargs["since"] = since.isoformat()
        if until:
            kwargs["until"] = until.isoformat()
        if author:
            kwargs["author"] = author
        if path:
            kwargs["paths"] = path
        if max_count:
            kwargs["max_count"] = max_count

        for commit in self.repo.iter_commits(**kwargs):
            info = self._parse_commit(commit)
            file_changes: list[FileChange] = []
            for fpath, detail in commit.stats.files.items():
                file_changes.append(
                    FileChange(
                        path=fpath,
                        insertions=detail.get("insertions", 0),
                        deletions=detail.get("deletions", 0),
                    )
                )
            yield info, file_changes

    def get_file_history(
        self, file_path: str, max_count: int | None = None
    ) -> list[CommitInfo]:
        """获取指定文件的修改历史。"""
        return list(self.iter_commits(path=file_path, max_count=max_count))

    def get_all_authors(self) -> list[tuple[str, str, int]]:
        """获取所有作者及其 commit 数量。

        Returns:
            [(name, email, commit_count), ...]
        """
        if not self.has_commits:
            return []
        authors: dict[tuple[str, str], int] = {}
        for commit in self.repo.iter_commits():
            key = (commit.author.name or "", commit.author.email or "")
            authors[key] = authors.get(key, 0) + 1
        result = [(name, email, count) for (name, email), count in authors.items()]
        result.sort(key=lambda x: x[2], reverse=True)
        return result

    def get_commit_count(self) -> int:
        """获取仓库总 commit 数量。"""
        if not self.has_commits:
            return 0
        return sum(1 for _ in self.repo.iter_commits())
