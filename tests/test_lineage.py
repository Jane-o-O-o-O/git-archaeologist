"""测试文件血统追踪功能"""
import subprocess
import pytest

from git_archaeologist.repo import Repo
from git_archaeologist.lineage import trace_lineage, LineageEntry


class TestTraceLineage:

    def _make_repo_with_renames(self, tmp_path):
        repo_dir = tmp_path / "lineage_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=repo_dir, capture_output=True)

        # 创建文件
        (repo_dir / "original_name.py").write_text("v1")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "创建原始文件"], cwd=repo_dir, capture_output=True)

        # 重命名
        subprocess.run(["git", "mv", "original_name.py", "renamed.py"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "重命名文件"], cwd=repo_dir, capture_output=True)

        # 移动到子目录
        (repo_dir / "src").mkdir()
        subprocess.run(["git", "mv", "renamed.py", "src/renamed.py"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "移动到子目录"], cwd=repo_dir, capture_output=True)

        return repo_dir

    def test_traces_current_path(self, tmp_path):
        repo_dir = self._make_repo_with_renames(tmp_path)
        repo = Repo(str(repo_dir))
        lineage = trace_lineage(repo, "src/renamed.py")
        assert lineage is not None
        assert len(lineage) >= 1

    def test_traces_renames(self, tmp_path):
        repo_dir = self._make_repo_with_renames(tmp_path)
        repo = Repo(str(repo_dir))
        lineage = trace_lineage(repo, "src/renamed.py")
        paths = [e.path for e in lineage]
        assert "src/renamed.py" in paths
        assert "renamed.py" in paths
        assert "original_name.py" in paths

    def test_nonexistent_file_returns_none(self, tmp_path):
        repo_dir = tmp_path / "lineage_repo2"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        lineage = trace_lineage(repo, "nonexistent.py")
        assert lineage is None

    def test_lineage_entry_has_commit_info(self, tmp_path):
        repo_dir = self._make_repo_with_renames(tmp_path)
        repo = Repo(str(repo_dir))
        lineage = trace_lineage(repo, "src/renamed.py")
        entry = lineage[0]
        assert entry.commit_hash is not None
        assert entry.commit_message is not None
        assert entry.date is not None
