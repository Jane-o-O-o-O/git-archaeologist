"""CLI 命令行接口 —— Git 考古工具入口"""
import argparse
import sys
from datetime import datetime

from git_archaeologist.repo import Repo
from git_archaeologist.fossils import find_fossils, Fossil
from git_archaeologist.strata import analyze_strata, Stratum
from git_archaeologist.lineage import trace_lineage
from git_archaeologist.hotspots import find_hotspots, HotspotFile
from git_archaeologist.authors import get_author_stats, AuthorStats


def build_report(repo, fossils_age_days: int = 365) -> str:
    """构建完整的考古报告

    Args:
        repo: Repo 对象
        fossils_age_days: 化石最小年龄（天）

    Returns:
        格式化的报告文本
    """
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
            lines.append(format_hotspot(h))
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
            lines.append(format_fossil(f))
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
            lines.append(format_stratum(s))
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
            lines.append(format_author_stats(a))
    else:
        lines.append("   (无贡献者)")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def format_fossil(fossil: Fossil) -> str:
    """格式化单个化石记录"""
    date_str = fossil.last_modified.strftime("%Y-%m-%d")
    return (
        f"   🪨 {fossil.path}\n"
        f"      最后修改: {date_str} | 年龄: {fossil.age_days} 天"
    )


def format_stratum(stratum: Stratum) -> str:
    """格式化单个地层记录"""
    start = stratum.start_date.strftime("%Y-%m-%d")
    end = stratum.end_date.strftime("%Y-%m-%d")
    return (
        f"     时间范围: {start} → {end}\n"
        f"     提交数: {stratum.commit_count}\n"
        f"     贡献者: {stratum.contributor_count} 人"
    )


def format_hotspot(hotspot: HotspotFile) -> str:
    """格式化单个热点文件记录"""
    first = hotspot.first_seen.strftime("%Y-%m-%d")
    last = hotspot.last_modified.strftime("%Y-%m-%d")
    return (
        f"   🔥 {hotspot.path}\n"
        f"      修改次数: {hotspot.modification_count} | "
        f"作者: {hotspot.unique_authors} 人 | "
        f"活跃期: {first} → {last}"
    )


def format_author_stats(author: AuthorStats) -> str:
    """格式化单个贡献者统计"""
    first = author.first_commit.strftime("%Y-%m-%d")
    last = author.last_commit.strftime("%Y-%m-%d")
    return (
        f"   👤 {author.name} <{author.email}>\n"
        f"      提交: {author.commit_count} 次 | "
        f"修改文件: {author.files_touched} 个 | "
        f"+{author.lines_added}/-{author.lines_removed} 行\n"
        f"      活跃期: {first} → {last}"
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

    # fossils 命令
    fossils_parser = subparsers.add_parser(
        "fossils", help="查找文件化石"
    )
    fossils_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    fossils_parser.add_argument(
        "--age", type=int, default=365,
        help="化石最小年龄（天），默认 365"
    )

    # strata 命令
    strata_parser = subparsers.add_parser(
        "strata", help="分析开发活跃期"
    )
    strata_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    strata_parser.add_argument(
        "--gap", type=int, default=14,
        help="分层间隔（天），默认 14"
    )

    # lineage 命令
    lineage_parser = subparsers.add_parser(
        "lineage", help="追踪文件血统"
    )
    lineage_parser.add_argument("filepath", help="要追踪的文件路径")
    lineage_parser.add_argument(
        "--repo", "-r", default=".", help="仓库路径"
    )

    # contributors 命令
    contrib_parser = subparsers.add_parser(
        "contributors", help="显示贡献者列表"
    )
    contrib_parser.add_argument("path", nargs="?", default=".", help="仓库路径")

    # hotspots 命令
    hotspots_parser = subparsers.add_parser(
        "hotspots", help="分析热点文件（修改最频繁的文件）"
    )
    hotspots_parser.add_argument("path", nargs="?", default=".", help="仓库路径")
    hotspots_parser.add_argument(
        "--top", type=int, default=20,
        help="显示前 N 个热点文件，默认 20"
    )

    # authors 命令
    authors_parser = subparsers.add_parser(
        "authors", help="贡献者深度统计"
    )
    authors_parser.add_argument("path", nargs="?", default=".", help="仓库路径")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "excavate":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        print(build_report(repo, fossils_age_days=args.fossil_age))

    elif args.command == "fossils":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        fossils = find_fossils(repo, min_age_days=args.age)
        if fossils:
            print(f"🦴 文件化石 (未修改超过 {args.age} 天):")
            for f in fossils:
                print(format_fossil(f))
        else:
            print("未发现文件化石。")

    elif args.command == "strata":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        strata = analyze_strata(repo, gap_days=args.gap)
        if strata:
            print("📈 开发活跃期:")
            for i, s in enumerate(strata, 1):
                print(f"  地层 {i}:")
                print(format_stratum(s))
        else:
            print("无开发活跃期。")

    elif args.command == "lineage":
        repo = Repo(args.repo)
        if not repo.is_valid():
            print(f"❌ 错误: {args.repo} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        entries = trace_lineage(repo, args.filepath)
        if entries:
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
        print(f"👥 贡献者 ({len(contributors)} 人):")
        for c in contributors:
            print(f"   • {c}")

    elif args.command == "hotspots":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        hotspots = find_hotspots(repo, top_n=args.top)
        if hotspots:
            print(f"🔥 热点文件 (Top {args.top}):")
            for h in hotspots:
                print(format_hotspot(h))
        else:
            print("未发现热点文件。")

    elif args.command == "authors":
        repo = Repo(args.path)
        if not repo.is_valid():
            print(f"❌ 错误: {args.path} 不是有效的 git 仓库", file=sys.stderr)
            sys.exit(1)
        stats = get_author_stats(repo)
        if stats:
            print(f"👤 贡献者统计 ({len(stats)} 人):")
            for a in stats:
                print(format_author_stats(a))
        else:
            print("无贡献者数据。")
