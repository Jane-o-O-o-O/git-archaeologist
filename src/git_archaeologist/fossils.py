"""文件化石发现模块 —— 查找长期未修改的文件"""
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class Fossil:
    """文件化石记录"""
    path: str
    name: str
    last_modified: datetime
    age_days: int


def find_fossils(repo, min_age_days: int = 365) -> list[Fossil]:
    """查找仓库中超过指定天数未修改的文件

    Args:
        repo: Repo 对象
        min_age_days: 最小年龄（天），默认 365 天

    Returns:
        化石列表，按年龄从大到小排序
    """
    # 获取所有被跟踪的文件
    tracked = _get_tracked_files(repo)
    if not tracked:
        return []

    cutoff = datetime.now() - timedelta(days=min_age_days)
    fossils = []

    for filepath in tracked:
        last_mod = _get_last_modified(repo, filepath)
        if last_mod is None:
            continue
        if last_mod < cutoff:
            age = (datetime.now() - last_mod).days
            fossils.append(Fossil(
                path=filepath,
                name=Path(filepath).name,
                last_modified=last_mod,
                age_days=age,
            ))

    fossils.sort(key=lambda f: f.age_days, reverse=True)
    return fossils


def _get_tracked_files(repo) -> list[str]:
    """获取仓库中所有被 git 跟踪的文件"""
    result = repo._run_git(["ls-files"])
    if not result:
        return []
    return [f for f in result.strip().split("\n") if f]


def _get_last_modified(repo, filepath: str) -> datetime | None:
    """获取文件最后一次被修改的时间（基于 git log）"""
    result = repo._run_git([
        "log", "-1", "--format=%aI", "--", filepath
    ])
    if not result:
        return None
    try:
        # %aI 输出 ISO 8601 格式的时间（带时区）
        date_str = result.strip()
        dt = datetime.fromisoformat(date_str)
        # 转为 naive datetime，去掉时区信息以便与 datetime.now() 比较
        return dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        return None
