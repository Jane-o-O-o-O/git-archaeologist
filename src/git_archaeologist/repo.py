"""Git 仓库考古学家 - 仓库基础模块"""
import subprocess
from pathlib import Path


class Repo:
    """Git 仓库对象，封装对 git 仓库的基础操作"""

    def __init__(self, path: str):
        self._path = Path(path).resolve()

    def is_valid(self) -> bool:
        """检查路径是否为有效 git 仓库"""
        if not self._path.is_dir():
            return False
        git_dir = self._path / ".git"
        return git_dir.is_dir()

    def commit_count(self) -> int:
        """返回仓库总提交数"""
        result = self._run_git(["rev-list", "--count", "HEAD"])
        if result is None:
            return 0
        return int(result.strip())

    def contributors(self) -> list[str]:
        """返回贡献者列表，格式为 'Name <email>'"""
        result = self._run_git([
            "log", "--format=%aN <%aE>"
        ])
        if result is None:
            return []
        unique = list(dict.fromkeys(result.strip().split("\n")))
        return unique

    def _run_git(self, args: list[str]) -> str | None:
        """执行 git 命令，返回输出或 None"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self._path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
