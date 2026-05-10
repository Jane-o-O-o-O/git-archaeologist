"""通用工具函数"""
from datetime import datetime


def parse_git_date(date_str: str) -> datetime | None:
    """解析 git 日期字符串为朴素 datetime

    Args:
        date_str: ISO 8601 格式的日期字符串

    Returns:
        朴素 datetime（无时区信息），解析失败返回 None
    """
    try:
        return datetime.fromisoformat(date_str).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None
