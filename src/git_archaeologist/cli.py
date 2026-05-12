"""CLI 命令行接口 —— Git 考古工具入口"""
import argparse
import json
import sys
from datetime import datetime

from git_archaeologist.repo import Repo
from git_archaeologist.fossils import find_fossils, Fossil
from git_archaeologist.strata import analyze_strata, Stratum
from git_archaeologist.lineage import trace_lineage
from git_archaeologist.hotspots import find_hotspots, HotspotFile
from git_archaeologist.authors import get_author_stats, AuthorStats
from git_archaeologist.output import (
    OutputFormat,
    format_fossil, format_fossils_list,
    format_hotspot, format_hotspots_list,
    format_stratum, format_strata_list,
    format_author_stats, format_author_stats_list,
)


def _parse_format(fmt_str: str) -> OutputFormat:
    """解析格式字符串为 OutputFormat 枚举"""
    if fmt_str == "json":
        return OutputFormat.JSON
    return OutputFormat.TERMINAL


def build_report(repo, fossils_age_days: int = 365,
                 fmt: OutputFormat = OutputFormat.TERMINAL) -> str:
    """构建完整的考古报告

    Args:
        repo: Repo 对象
        fossils_age_days: 化石最小年龄（天）
        fmt: 输出格式

    Returns:
        格式化的报告文本
    """
    if fmt == OutputFormat.JSON:
        return _build_report_json(repo, fossils_age_days)

    lines = []
    lines.append("=" * 60)
    lines.append("  ⛏️  Git 考古报告 🔍")
    lines.append("=" * 60)
    lines.append("")

    # 基本信息
    count = repo.commit_count()
    contributors = repo.contributors()
    lines.append(f"📊 提交总数: {count}")
    lines.append(f"👥 贡献者数量: {len(contributors)}")
    for c in contributors:
        lines.append(f"   • {c}")
    lines.append("")

    # 热点文件
    lines.append("─" * 60)
    lines.append("🔥 热点文件 (修改最频繁 Top 10):")
    lines.append("─" * 60)
    hotspots = find_hotspots(repo, top_n=10)
    if hotspots:
        for h in hotspots:
            lines.append(format_hotspot(h, fmt))
    else:
        lines.append("   (无热点文件)")
    lines.append("")

    # 化石
    lines.append("─" * 60)
    lines.append(f"🦴 文件化石 (未修改超过 {fossils_age_days} 天):")
    lines.append("─" * 60)
    fossils = find_fossils(repo, min_age_days=fossils_age_days)
    if fossils:
        for f in fossils:
            lines.append(format_fossil(f, fmt))
    else:
        lines.append("   (无化石)")
    lines.append("")

    # 地层
    lines.append("─" * 60)
    lines.append("📈 开发活跃期 (地层):")
    lines.append("─" * 60)
    strata = analyze_strata(repo)
    if strata:
        for i, s in enumerate(strata, 1):
            lines.append(f"  地层 {i}:")
            lines.append(format_stratum(s, fmt))
    else:
        lines.append("   (无活跃期)")
    lines.append("")

    # 贡献者统计
    lines.append("─" * 60)
    lines.append("👤 贡献者统计:")
    lines.append("─" * 60)
    author_stats = get_author_stats(repo)
    if author_stats:
        for a in author_stats:
            lines.append(format_author_stats(a, fmt))
    else:
        lines.append("   (无贡献者)")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def _build_report_json(repo, fossils_age_days: int) -> str:
    """构建 JSON 格式的完整考古报告"""
    count = repo.commit_count()
    contributors = repo.contributors()
    hotspots = find_hotspots(repo, top_n=10)
    fossils = find_fossils(repo, min_age_days=fossils_age_days)
    strata = analyze_strata(repo)
    author_stats = get_author_stats(repo)

    report = {
        "summary": {
            "commit_count": count,
            "contributor_count": len(contributors),
            "contributors": contributors,
        },
        "hotspots": [
            json.loads(format_hotspot(h, OutputFormat.JSON)) for h in hotspots
        ],
        "fossils": [
            json.loads(format_fossil(f, OutputFormat.JSON)) for f in fossils
        ],
        "strata": [
            json.loads(format_stratum(s, OutputFormat.JSON)) for s in strata
        ],
        "authors": [
            json.loads(format_author_stats(a, OutputFormat.JSON)) for a in author_stats
        ],
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def _add_format_arg(parser):
    """为子命令添加 --format 参数"""
    parser.add_argument(
        "--format", "-f", choices=["terminal", "json"], default="terminal",
        help="输出格式: terminal (默认) 或 json"
    )


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="git-archaeologist",
        description="Git 仓库考古工具 —— 深入挖掘仓库的历史地层",
    )
    subparsers = parser.add_subparsers(dest="command")

    # excavate 命令
    excavate_parser = subparsers.add_parser(
        "excavate", help="挖掘仓库，生成完整考古报告"
    )
    excavate_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    excavate_parser.add_argument(
        "--fossil-age", type=int, default=365,
        help="化石最小年龄（天），默认 365"
    )
    _add_format_arg(excavate_parser)

    # fossils 命令
    fossils_parser = subparsers.add_parser(
        "fossils", help="查找文件化石"
    )
    fossils_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    fossils_parser.add_argument(
        "--age", type=int, default=365,
        help="化石最小年龄（天），默认 365"
    )
    _add_format_arg(fossils_parser)

    # strata 命令
    strata_parser = subparsers.add_parser(
        "strata", help="分析开发活跃期"
    )
    strata_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    strata_parser.add_argument(
        "--gap", type=int, default=14,
        help="分层间隔（天），默认 14"
    )
    _add_format_arg(strata_parser)

    # lineage 命令
    lineage_parser = subparsers.add_parser(
        "lineage", help="追踪文件血统"
    )
    lineage_parser.add_argument("filepath", help="要追踪的文件路径")
    lineage_parser.add_argument(
        "--repo", "-r", default=".", help="仓库路径"
    )
    _add_format_arg(lineage_parser)

    # contributors 命令
    contrib_parser = subparsers.add_parser(
        "contributors", help="显示贡献者列表"
    )
    contrib_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    _add_format_arg(contrib_parser)

    # hotspots 命令
    hotspots_parser = subparsers.add_parser(
        "hotspots", help="分析热点文件（修改最频繁的文件）"
    )
    hotspots_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    hotspots_parser.add_argument(
        "--top", type=int, default=20,
        help="显示前 N 个热点文件，默认 20"
    )
    _add_format_arg(hotspots_parser)

    # authors 命令
    authors_parser = subparsers.add_parser(
        "authors", help="贡献者深度统计"
    )
    authors_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    _add_format_arg(authors_parser)

    # timeline 命令
    timeline_parser = subparsers.add_parser(
        "timeline", help="提交频率时间线分析"
    )
    timeline_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    timeline_parser.add_argument(
        "--granularity", choices=["day", "week", "month"], default="month",
        help="时间粒度: day/week/month (默认 month)"
    )
    _add_format_arg(timeline_parser)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    fmt = _parse_format(getattr(args, "format", "terminal"))

    if args.command == "excavate":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        print(build_report(repo, fossils_age_days=args.fossil_age, fmt=fmt))

    elif args.command == "fossils":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        fossils = find_fossils(repo, min_age_days=args.age)
        if fmt == OutputFormat.JSON:
            print(format_fossils_list(fossils, fmt))
        elif fossils:
            print(f"🦴 文件化石 (未修改超过 {args.age} 天):")
            for f in fossils:
                print(format_fossil(f, fmt))
        else:
            print("未发现文件化石。")

    elif args.command == "strata":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        strata = analyze_strata(repo, gap_days=args.gap)
        if fmt == OutputFormat.JSON:
            print(format_strata_list(strata, fmt))
        elif strata:
            print("📈 开发活跃期:")
            for i, s in enumerate(strata, 1):
                print(f"  地层 {i}:")
                print(format_stratum(s, fmt))
        else:
            print("无开发活跃期。")

    elif args.command == "lineage":
        repo = Repo(args.repo)
        if not repo.is_valid():
            print(f"❌ 错误: {args.repo} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        entries = trace_lineage(repo, args.filepath)
        if fmt == OutputFormat.JSON:
            if entries:
                data = [{
                    "path": e.path,
                    "commit_hash": e.commit_hash,
                    "commit_message": e.commit_message,
                    "date": e.date.isoformat(),
                    "action": e.action,
                } for e in entries]
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print("[]")
        elif entries:
            print(f"🔬 文件血统: {args.filepath}")
            for e in entries:
                print(f"   [{e.action}] {e.path} ({e.commit_hash[:8]}) - {e.commit_message}")
        else:
            print(f"未找到文件 {args.filepath} 的血统记录。")

    elif args.command == "contributors":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        contributors = repo.contributors()
        if fmt == OutputFormat.JSON:
            print(json.dumps(contributors, ensure_ascii=False, indent=2))
        else:
            print(f"👥 贡献者 ({len(contributors)} 人):")
            for c in contributors:
                print(f"   • {c}")

    elif args.command == "hotspots":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        hotspots = find_hotspots(repo, top_n=args.top)
        if fmt == OutputFormat.JSON:
            print(format_hotspots_list(hotspots, fmt))
        elif hotspots:
            print(f"🔥 热点文件 (Top {args.top}):")
            for h in hotspots:
                print(format_hotspot(h, fmt))
        else:
            print("未发现热点文件。")

    elif args.command == "authors":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        stats = get_author_stats(repo)
        if fmt == OutputFormat.JSON:
            print(format_author_stats_list(stats, fmt))
        elif stats:
            print(f"👤 贡献者统计 ({len(stats)} 人):")
            for a in stats:
                print(format_author_stats(a, fmt))
        else:
            print("无贡献者数据。")

    elif args.command == "timeline":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        from git_archaeologist.timeline import analyze_timeline
        periods = analyze_timeline(repo, granularity=args.granularity)
        if fmt == OutputFormat.JSON:
            data = [{
                "period": p.period,
                "commit_count": p.commit_count,
                "contributor_count": p.contributor_count,
                "files_changed": p.files_changed,
                "lines_added": p.lines_added,
                "lines_removed": p.lines_removed,
            } for p in periods]
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif periods:
            print(f"📈 提交频率时间线 (粒度: {args.granularity}):")
            print(f"   {'时间段':<15} {'提交':>6} {'贡献者':>6} {'文件':>6} {'+行':>8} {'-行':>8}")
            print("   " + "─" * 58)
            for p in periods:
                print(f"   {p.period:<15} {p.commit_count:>6} {p.contributor_count:>6} "
                      f"{p.files_changed:>6} {p.lines_added:>8} {p.lines_removed:>8}")
        else:
            print("无时间线数据。")
