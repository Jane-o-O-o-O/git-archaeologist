"""测试热点文件分析功能 —— 发现被修改最频繁的文件"""
import subprocess
import pytest

from git_archaeologist.repo import Repo
from git_archaeologist.hotspots import find_hotspots, HotspotFile


class TestFindHotspots:
    """热点文件分析测试"""

    def _make_repo_with_hotspots(self, tmp_path):
        """创建一个含有热点文件的仓库"""
        repo_dir = tmp_path / "hotspot_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True)

        # 创建多个文件，对某个文件做多次修改
        for i in range(5):
            # 每次都修改 hot_file.py（热点文件）
            (repo_dir / "hot_file.py").write_text(f"# version {i}\n")
            # 只修改一次 cold_file.py
            if i == 0:
                (repo_dir / "cold_file.py").write_text("# rarely touched\n")
            # medium_file.py 修改3次
            if i < 3:
                (repo_dir / "medium_file.py").write_text(f"# medium {i}\n")
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"提交 {i}"], cwd=repo_dir, capture_output=True)

        return repo_dir

    def test_returns_hotspot_files(self, tmp_path):
        """测试：应返回热点文件列表"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        assert len(hotspots) >= 1

    def test_hotspot_sorted_by_modification_count(self, tmp_path):
        """测试：热点文件应按修改次数降序排列"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        counts = [h.modification_count for h in hotspots]
        assert counts == sorted(counts, reverse=True)

    def test_most_modified_file_is_top(self, tmp_path):
        """测试：修改次数最多的文件应在最前面"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        assert hotspots[0].path == "hot_file.py"
        assert hotspots[0].modification_count == 5

    def test_hotspot_has_unique_authors(self, tmp_path):
        """测试：热点文件应包含唯一作者数量"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        for h in hotspots:
            assert h.unique_authors >= 1

    def test_hotspot_has_date_range(self, tmp_path):
        """测试：热点文件应包含首次和最后修改日期"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        for h in hotspots:
            assert h.first_seen is not None
            assert h.last_modified is not None
            assert h.first_seen <= h.last_modified

    def test_top_n_limits_results(self, tmp_path):
        """测试：top_n 参数应限制返回数量"""
        repo_dir = self._make_repo_with_hotspots(tmp_path)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo, top_n=2)
        assert len(hotspots) <= 2

    def test_empty_repo_returns_empty(self, tmp_path):
        """测试：空仓库应返回空列表"""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        assert hotspots == []

    def test_multiple_authors_counted(self, tmp_path):
        """测试：多作者修改同一文件时应正确统计"""
        repo_dir = tmp_path / "multi_author_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)

        # 作者 A 修改
        subprocess.run(["git", "config", "user.email", "a@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Alice"], cwd=repo_dir, capture_output=True)
        (repo_dir / "shared.py").write_text("v1")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Alice 提交"], cwd=repo_dir, capture_output=True)

        # 作者 B 修改
        subprocess.run(["git", "config", "user.email", "b@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Bob"], cwd=repo_dir, capture_output=True)
        (repo_dir / "shared.py").write_text("v2")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Bob 提交"], cwd=repo_dir, capture_output=True)

        repo = Repo(str(repo_dir))
        hotspots = find_hotspots(repo)
        shared = [h for h in hotspots if h.path == "shared.py"][0]
        assert shared.unique_authors == 2
        assert shared.modification_count == 2
