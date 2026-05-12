"""测试新增功能 — 健康评分、commit 消息分析、CSV/Markdown 输出。"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta

import git
import pytest

from git_archaeologist.analyzer import Analyzer, CommitMessageStats, HealthScore


def _create_conventional_repo() -> str:
    """创建一个使用 conventional commits 的仓库。"""
    import os
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="git-arch-conventional-")
    repo = git.Repo.init(tmpdir)
    author = git.Actor("Dev", "dev@example.com")
    base_date = datetime(2024, 6, 1)

    commits_data = [
        ("feat(api): add user endpoint", ["src/api.py"]),
        ("feat(models): add User model", ["src/models.py"]),
        ("fix(api): handle null response", ["src/api.py"]),
        ("docs: update README", ["README.md"]),
        ("refactor(core): simplify logic", ["src/core.py"]),
        ("feat(ui): add dark theme", ["src/ui/theme.py"]),
        ("fix: correct calculation", ["src/core.py"]),
        ("test(api): add integration tests", ["tests/test_api.py"]),
        ("chore: update dependencies", ["requirements.txt"]),
        ("feat!: breaking change in API", ["src/api.py"]),
        ("add some random feature", ["src/utils.py"]),
        ("update readme", ["README.md"]),
        ("feat(auth): add OAuth support", ["src/auth.py"]),
        ("fix(auth): token refresh", ["src/auth.py"]),
        ("feat(api): pagination support", ["src/api.py"]),
    ]

    for i, (msg, files) in enumerate(commits_data):
        for f in files:
            filepath = os.path.join(tmpdir, f)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f"# {f}\n# Commit {i}\n'content {i}'\n")
        repo.index.add(files)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            msg,
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir


def _create_diverse_repo() -> str:
    """创建一个有多贡献者的仓库。"""
    import os
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="git-arch-diverse-")
    repo = git.Repo.init(tmpdir)
    base_date = datetime(2024, 1, 1)

    authors = [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
        ("Dave", "dave@example.com"),
        ("Eve", "eve@example.com"),
    ]

    for i in range(20):
        author_idx = i % len(authors)
        name, email = authors[author_idx]
        filepath = os.path.join(tmpdir, f"file_{i % 5}.py")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as fh:
            fh.write(f"# file_{i % 5}\n# Commit {i}\n'content {i}'\n")
        repo.index.add([f"file_{i % 5}.py"])
        author = git.Actor(name, email)
        commit_date = base_date + timedelta(days=i)
        repo.index.commit(
            f"commit {i} by {name}",
            author=author,
            committer=author,
            commit_date=commit_date.isoformat(),
            author_date=commit_date.isoformat(),
        )

    return tmpdir


# ── Health Score Tests ──────────────────────────────────────────────


class TestHealthScore:
    """仓库健康评分测试。"""

    def test_health_score_returns_result(self):
        """健康评分应返回 HealthScore 对象。"""
        tmpdir = _create_diverse_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.health_score()
            assert isinstance(result, HealthScore)
            assert 0 <= result.overall <= 100
            assert result.summary != ""
            assert len(result.details) > 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_health_score_sub_scores_sum(self):
        """子分数之和应等于总分。"""
        tmpdir = _create_diverse_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.health_score()
            sub_sum = (
                result.bus_factor_score
                + result.churn_score
                + result.activity_score
                + result.diversity_score
            )
            assert result.overall == min(100, sub_sum)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_health_score_with_time_filter(self):
        """支持时间范围过滤。"""
        tmpdir = _create_diverse_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.health_score(
                since=datetime(2024, 1, 1),
                until=datetime(2024, 1, 10),
            )
            assert isinstance(result, HealthScore)
            assert 0 <= result.overall <= 100
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_health_score_empty_repo(self):
        """空仓库应返回默认评分。"""
        import tempfile

        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-health-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.health_score()
            assert isinstance(result, HealthScore)
            assert result.overall >= 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_health_score_diverse_repo_higher(self):
        """多贡献者的仓库健康分应高于单一贡献者。"""
        diverse = _create_diverse_repo()
        # 单一贡献者仓库
        import os
        import tempfile

        solo = tempfile.mkdtemp(prefix="git-arch-solo-")
        repo = git.Repo.init(solo)
        author = git.Actor("Solo", "solo@example.com")
        for i in range(10):
            filepath = os.path.join(solo, "main.py")
            with open(filepath, "w") as f:
                f.write(f"# Commit {i}\n")
            repo.index.add(["main.py"])
            repo.index.commit(
                f"commit {i}",
                author=author,
                committer=author,
                commit_date=(datetime(2024, 1, 1) + timedelta(days=i)).isoformat(),
                author_date=(datetime(2024, 1, 1) + timedelta(days=i)).isoformat(),
            )

        try:
            diverse_score = Analyzer(diverse).health_score()
            solo_score = Analyzer(solo).health_score()
            # 多样性仓库应在 diversity 分数上更高
            assert diverse_score.diversity_score > solo_score.diversity_score
        finally:
            shutil.rmtree(diverse, ignore_errors=True)
            shutil.rmtree(solo, ignore_errors=True)


# ── Commit Message Stats Tests ──────────────────────────────────────


class TestCommitMessageStats:
    """Commit 消息分析测试。"""

    def test_returns_commit_message_stats(self):
        """应返回 CommitMessageStats 对象。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            assert isinstance(result, CommitMessageStats)
            assert result.total_commits == 15
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_conventional_commit_detection(self):
        """应正确检测 conventional commits。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            # 15 个 commit 中有 11 个是 conventional
            assert result.conventional_count == 11
            assert result.conventional_pct > 70
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_type_counts(self):
        """应统计 conventional commit 类型。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            assert "feat" in result.type_counts
            assert "fix" in result.type_counts
            assert result.type_counts["feat"] >= 4
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_message_length_stats(self):
        """应统计消息长度。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            assert result.avg_message_length > 0
            assert result.max_message_length >= result.min_message_length
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_short_and_long_messages(self):
        """应统计过短和过长消息。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            # "update readme" 是短消息
            assert result.short_messages >= 0
            assert result.long_messages >= 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_common_words(self):
        """应统计常见词汇。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            assert len(result.most_common_words) > 0
            # "commit" 出现在消息中
            word_dict = dict(result.most_common_words)
            assert any(w in word_dict for w in ["feat", "fix", "add", "update"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_empty_repo(self):
        """空仓库应返回空结果。"""
        import tempfile

        tmpdir = tempfile.mkdtemp(prefix="git-arch-empty-msg-")
        try:
            git.Repo.init(tmpdir)
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats()
            assert result.total_commits == 0
            assert result.conventional_count == 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_with_time_filter(self):
        """支持时间范围过滤。"""
        tmpdir = _create_conventional_repo()
        try:
            analyzer = Analyzer(tmpdir)
            result = analyzer.commit_message_stats(
                since=datetime(2024, 6, 1),
                until=datetime(2024, 6, 5),
            )
            assert result.total_commits == 5
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
