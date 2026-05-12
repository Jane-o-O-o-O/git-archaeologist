"""输出格式化模块 —— 统一处理终端和 JSON 输出格式"""
import json
from datetime import datetime
from enum import Enum
from typing import Any

from git_archaeologist.fossils import Fossil
from git_archaeologist.strata import Stratum
from git_archaeologist.hotspots import HotspotFile
from git_archaeologist.authors import AuthorStats


class OutputFormat(str, Enum):
    """输出格式枚举"""
    TERMINAL = "terminal"
    JSON = "json"


def _dt_to_str(dt: datetime) -> str:
    """将 datetime 转为 ISO 格式字符串"""
    return dt.isoformat()


# ── 化石 ──────────────────────────────────────────────

def format_fossil(fossil: Fossil, fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化单个化石记录"""
    if fmt == OutputFormat.JSON:
        return json.dumps({
            "path": fossil.path,
            "name": fossil.name,
            "last_modified": _dt_to_str(fossil.last_modified),
            "age_days": fossil.age_days,
        }, ensure_ascii=False)

    date_str = fossil.last_modified.strftime("%Y-%m-%d")
    return (
        f"   🪨 {fossil.path}\n"
        f"      最后修改: {date_str} | 年龄: {fossil.age_days} 天"
    )


def format_fossils_list(fossils: list[Fossil], fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化化石列表"""
    if fmt == OutputFormat.JSON:
        items = [json.loads(format_fossil(f, OutputFormat.JSON)) for f in fossils]
        return json.dumps(items, ensure_ascii=False, indent=2)
    return "\n".join(format_fossil(f, fmt) for f in fossils)


# ── 热点文件 ──────────────────────────────────────────

def format_hotspot(hotspot: HotspotFile, fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化单个热点文件记录"""
    if fmt == OutputFormat.JSON:
        return json.dumps({
            "path": hotspot.path,
            "modification_count": hotspot.modification_count,
            "unique_authors": hotspot.unique_authors,
            "first_seen": _dt_to_str(hotspot.first_seen),
            "last_modified": _dt_to_str(hotspot.last_modified),
        }, ensure_ascii=False)

    first = hotspot.first_seen.strftime("%Y-%m-%d")
    last = hotspot.last_modified.strftime("%Y-%m-%d")
    return (
        f"   🔥 {hotspot.path}\n"
        f"      修改次数: {hotspot.modification_count} | "
        f"作者: {hotspot.unique_authors} 人 | "
        f"活跃期: {first} → {last}"
    )


def format_hotspots_list(hotspots: list[HotspotFile], fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化热点文件列表"""
    if fmt == OutputFormat.JSON:
        items = [json.loads(format_hotspot(h, OutputFormat.JSON)) for h in hotspots]
        return json.dumps(items, ensure_ascii=False, indent=2)
    return "\n".join(format_hotspot(h, fmt) for h in hotspots)


# ── 贡献者统计 ────────────────────────────────────────

def format_author_stats(author: AuthorStats, fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化单个贡献者统计"""
    if fmt == OutputFormat.JSON:
        return json.dumps({
            "name": author.name,
            "email": author.email,
            "commit_count": author.commit_count,
            "first_commit": _dt_to_str(author.first_commit),
            "last_commit": _dt_to_str(author.last_commit),
            "files_touched": author.files_touched,
            "lines_added": author.lines_added,
            "lines_removed": author.lines_removed,
        }, ensure_ascii=False)

    first = author.first_commit.strftime("%Y-%m-%d")
    last = author.last_commit.strftime("%Y-%m-%d")
    return (
        f"   👤 {author.name} <{author.email}>\n"
        f"      提交: {author.commit_count} 次 | "
        f"修改文件: {author.files_touched} 个 | "
        f"+{author.lines_added}/-{author.lines_removed} 行\n"
        f"      活跃期: {first} → {last}"
    )


def format_author_stats_list(authors: list[AuthorStats], fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化贡献者统计列表"""
    if fmt == OutputFormat.JSON:
        items = [json.loads(format_author_stats(a, OutputFormat.JSON)) for a in authors]
        return json.dumps(items, ensure_ascii=False, indent=2)
    return "\n".join(format_author_stats(a, fmt) for a in authors)


# ── 地层 ──────────────────────────────────────────────

def format_stratum(stratum: Stratum, fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化单个地层记录"""
    if fmt == OutputFormat.JSON:
        return json.dumps({
            "start_date": _dt_to_str(stratum.start_date),
            "end_date": _dt_to_str(stratum.end_date),
            "commit_count": stratum.commit_count,
            "contributor_count": stratum.contributor_count,
            "contributors": stratum.contributors,
        }, ensure_ascii=False)

    start = stratum.start_date.strftime("%Y-%m-%d")
    end = stratum.end_date.strftime("%Y-%m-%d")
    return (
        f"     时间范围: {start} → {end}\n"
        f"     提交数: {stratum.commit_count}\n"
        f"     贡献者: {stratum.contributor_count} 人"
    )


def format_strata_list(strata: list[Stratum], fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """格式化地层列表"""
    if fmt == OutputFormat.JSON:
        items = [json.loads(format_stratum(s, OutputFormat.JSON)) for s in strata]
        return json.dumps(items, ensure_ascii=False, indent=2)
    lines = []
    for i, s in enumerate(strata, 1):
        lines.append(f"  地层 {i}:")
        lines.append(format_stratum(s, fmt))
    return "\n".join(lines)
