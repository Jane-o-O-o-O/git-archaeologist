"""文件血统追踪模块 —— 追踪文件的重命名和移动历史"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LineageEntry:
    """文件血统记录条目"""
    path: str
    commit_hash: str
    commit_message: str
    date: datetime
    action: str  # "created", "renamed", "modified"


def trace_lineage(repo, filepath: str) -> list[LineageEntry] | None:
    """追踪文件的完整血统历史

    使用 git log --follow 追踪文件的重命名和移动历史。

    Args:
        repo: Repo 对象
        filepath: 要追踪的文件路径

    Returns:
        血统记录列表（从新到旧），文件不存在则返回 None
    """
    result = repo._run_git([
        "log", "--follow", "--name-status", "--format=COMMIT|%H|%s|%aI",
        "--diff-filter=ADRCM", "--", filepath
    ])

    if not result or not result.strip():
        # 文件不存在或没有历史
        return None

    entries = []
    current_commit = None

    for line in result.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("COMMIT|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                current_commit = {
                    "hash": parts[1],
                    "message": parts[2],
                    "date_str": parts[3],
                }
        elif current_commit and "\t" in line:
            status_parts = line.split("\t")
            status_code = status_parts[0][0]  # 取状态首字母

            action = _parse_status(status_code)
            try:
                dt = datetime.fromisoformat(
                    current_commit["date_str"]
                ).replace(tzinfo=None)
            except (ValueError, TypeError):
                dt = datetime.min

            # 重命名/复制有两个路径：old\tnew
            if status_code in ("R", "C") and len(status_parts) == 3:
                old_path, new_path = status_parts[1], status_parts[2]
                # 记录旧路径（重命名前）
                entries.append(LineageEntry(
                    path=old_path,
                    commit_hash=current_commit["hash"],
                    commit_message=current_commit["message"],
                    date=dt,
                    action=action,
                ))
                # 记录新路径（重命名后）
                entries.append(LineageEntry(
                    path=new_path,
                    commit_hash=current_commit["hash"],
                    commit_message=current_commit["message"],
                    date=dt,
                    action=action,
                ))
            elif len(status_parts) >= 2:
                entries.append(LineageEntry(
                    path=status_parts[1],
                    commit_hash=current_commit["hash"],
                    commit_message=current_commit["message"],
                    date=dt,
                    action=action,
                ))
            current_commit = None

    return entries if entries else None


def _parse_status(code: str) -> str:
    """将 git 状态码转换为可读动作"""
    mapping = {
        "A": "created",
        "R": "renamed",
        "C": "copied",
        "M": "modified",
        "D": "deleted",
    }
    return mapping.get(code, "modified")
