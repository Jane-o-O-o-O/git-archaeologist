"""测试文件化石功能 —— 发现长期未修改的文件"""
import subprocess
import pytest
from datetime import datetime, timedelta

from git_archaeologist.repo import Repo
from git_archaeologist.fossils import find_fossils


class TestFindFossils:
    """文件化石发现测试"""

    def _make_repo_with_old_file(self, tmp_path, old_days=400):
        """创建一个含有'古老'文件的仓库"""
        repo_dir = tmp_path / "fossil_repo"
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
        # 创建一个旧文件
        old_file = repo_dir / "ancient_module.py"
        old_file.write_text("# 很久很久以前写的代码")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        # 使用 --date 设置旧日期
        old_date = (datetime.now() - timedelta(days=old_days)).strftime("%Y-%m-%dT12:00:00")
        subprocess.run(
            ["git", "commit", "-m", "远古提交", f"--date={old_date}"],
            cwd=repo_dir, capture_output=True
        )
        # 创建一个新文件
        new_file = repo_dir / "fresh_module.py"
        new_file.write_text("# 刚刚写的新代码")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "最新提交"],
            cwd=repo_dir, capture_output=True
        )
        return repo_dir

    def test_finds_old_files(self, tmp_path):
        """测试：能找到超过指定天数未修改的文件"""
        repo_dir = self._make_repo_with_old_file(tmp_path, old_days=400)
        repo = Repo(str(repo_dir))
        fossils = find_fossils(repo, min_age_days=365)
        fossil_names = [f.name for f in fossils]
        assert "ancient_module.py" in fossil_names

    def test_excludes_recent_files(self, tmp_path):
        """测试：不应包含近期修改的文件"""
        repo_dir = self._make_repo_with_old_file(tmp_path, old_days=400)
        repo = Repo(str(repo_dir))
        fossils = find_fossils(repo, min_age_days=365)
        fossil_names = [f.name for f in fossils]
        assert "fresh_module.py" not in fossil_names

    def test_returns_empty_for_new_repo(self, tmp_path):
        """测试：全新仓库应返回空列表"""
        repo_dir = tmp_path / "new_repo"
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
        f = repo_dir / "file.txt"
        f.write_text("content")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "初始提交"],
            cwd=repo_dir, capture_output=True
        )
        repo = Repo(str(repo_dir))
        fossils = find_fossils(repo, min_age_days=365)
        assert fossils == []

    def test_fossil_has_metadata(self, tmp_path):
        """测试：化石对象应包含文件路径和最后修改日期"""
        repo_dir = self._make_repo_with_old_file(tmp_path, old_days=400)
        repo = Repo(str(repo_dir))
        fossils = find_fossils(repo, min_age_days=365)
        fossil = [f for f in fossils if f.name == "ancient_module.py"][0]
        assert fossil.path is not None
        assert fossil.last_modified is not None
        assert fossil.age_days >= 365
