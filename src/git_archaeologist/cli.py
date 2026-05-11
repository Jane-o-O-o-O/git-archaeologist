"""CLI 子命令 — stats, authors, hotspots, activity, filetypes, report。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from git_archaeologist.analyzer import Analyzer

console = Console()


def _parse_since(value: str | None) -> datetime | None:
    """解析 --since 参数，支持相对时间和绝对日期。"""
    if not value:
        return None
    # 尝试绝对日期
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # 相对时间：1y, 6m, 30d
    value = value.strip().lower()
    if value.endswith("y"):
        return datetime.now() - timedelta(days=int(value[:-1]) * 365)
    if value.endswith("m"):
        return datetime.now() - timedelta(days=int(value[:-1]) * 30)
    if value.endswith("d"):
        return datetime.now() - timedelta(days=int(value[:-1]))
    raise click.BadParameter(f"无法解析时间: {value}，支持格式: YYYY-MM-DD, 1y, 6m, 30d")


def _format_number(n: int) -> str:
    """格式化数字，添加千分位。"""
    return f"{n:,}"


@click.group()
@click.option("--repo", default=".", help="仓库路径", envvar="GIT_ARCH_REPO")
@click.pass_context
def main(ctx: click.Context, repo: str) -> None:
    """🏺 Git Archaeologist — Git 仓库考古分析工具"""
    ctx.ensure_object(dict)
    ctx.obj["repo"] = repo
    ctx.obj["analyzer"] = Analyzer(repo)


@main.command()
@click.option("--since", default=None, help="起始时间 (YYYY-MM-DD 或 1y/6m/30d)")
@click.option("--until", default=None, help="结束时间")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def stats(ctx: click.Context, since: str | None, until: str | None, fmt: str) -> None:
    """📊 仓库总体统计"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    s = analyzer.repo_stats(since=_parse_since(since), until=_parse_since(until))

    if fmt == "json":
        data = {
            "total_commits": s.total_commits,
            "total_authors": s.total_authors,
            "total_files_changed": s.total_files_changed,
            "total_insertions": s.total_insertions,
            "total_deletions": s.total_deletions,
            "first_commit": s.first_commit_date.isoformat() if s.first_commit_date else None,
            "last_commit": s.last_commit_date.isoformat() if s.last_commit_date else None,
            "active_days": s.active_days,
            "avg_commits_per_day": s.avg_commits_per_day,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    table = Table(title="🏺 仓库统计", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green", justify="right")
    table.add_row("总 Commits", _format_number(s.total_commits))
    table.add_row("贡献者数", _format_number(s.total_authors))
    table.add_row("涉及文件数", _format_number(s.total_files_changed))
    table.add_row("总新增行数", f"[green]+{_format_number(s.total_insertions)}[/]")
    table.add_row("总删除行数", f"[red]-{_format_number(s.total_deletions)}[/]")
    table.add_row("净变更行数", _format_number(s.total_insertions - s.total_deletions))
    if s.first_commit_date:
        table.add_row("首次提交", s.first_commit_date.strftime("%Y-%m-%d"))
    if s.last_commit_date:
        table.add_row("最后提交", s.last_commit_date.strftime("%Y-%m-%d"))
    table.add_row("活跃天数", _format_number(s.active_days))
    table.add_row("日均 Commits", str(s.avg_commits_per_day))
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=20, help="显示前 N 位贡献者")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def authors(
    ctx: click.Context, since: str | None, until: str | None, top: int, fmt: str
) -> None:
    """👤 贡献者统计"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.author_stats(since=_parse_since(since), until=_parse_since(until), top_n=top)

    if fmt == "json":
        data = [
            {
                "name": a.name,
                "email": a.email,
                "commits": a.commit_count,
                "insertions": a.insertions,
                "deletions": a.deletions,
                "files_touched": len(a.files_touched),
                "first_commit": a.first_commit.isoformat() if a.first_commit else None,
                "last_commit": a.last_commit.isoformat() if a.last_commit else None,
            }
            for a in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    table = Table(title="👤 贡献者排行", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("作者", style="cyan")
    table.add_column("Commits", justify="right")
    table.add_column("新增行", justify="right", style="green")
    table.add_column("删除行", justify="right", style="red")
    table.add_column("涉及文件", justify="right")
    table.add_column("最后活跃", justify="right")

    for i, a in enumerate(result, 1):
        last_active = a.last_commit.strftime("%Y-%m-%d") if a.last_commit else "-"
        table.add_row(
            str(i),
            a.name,
            _format_number(a.commit_count),
            f"+{_format_number(a.insertions)}",
            f"-{_format_number(a.deletions)}",
            str(len(a.files_touched)),
            last_active,
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=20, help="显示前 N 个热点文件")
@click.option("--ignore", multiple=True, help="忽略的文件 glob 模式")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def hotspots(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    top: int,
    ignore: tuple[str, ...],
    fmt: str,
) -> None:
    """🔥 热点文件分析"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.hotspots(
        since=_parse_since(since),
        until=_parse_since(until),
        top_n=top,
        ignore_globs=list(ignore) if ignore else None,
    )

    if fmt == "json":
        data = [
            {
                "path": f.path,
                "changes": f.change_count,
                "insertions": f.insertions,
                "deletions": f.deletions,
                "authors": list(f.authors),
                "last_modified": f.last_modified.isoformat() if f.last_modified else None,
            }
            for f in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    table = Table(title="🔥 热点文件", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("文件路径", style="cyan", max_width=60)
    table.add_column("修改次数", justify="right", style="bold yellow")
    table.add_column("贡献者数", justify="right")
    table.add_column("最后修改", justify="right")

    for i, f in enumerate(result, 1):
        last_mod = f.last_modified.strftime("%Y-%m-%d") if f.last_modified else "-"
        table.add_row(
            str(i),
            f.path,
            str(f.change_count),
            str(len(f.authors)),
            last_mod,
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option(
    "--period",
    type=click.Choice(["day", "week", "month", "year"]),
    default="month",
    help="统计周期",
)
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def activity(
    ctx: click.Context, since: str | None, until: str | None, period: str, fmt: str
) -> None:
    """📅 Commit 活跃度趋势"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    data = analyzer.commit_activity_by_period(
        period=period, since=_parse_since(since), until=_parse_since(until)
    )

    if fmt == "json":
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not data:
        console.print("[dim]无数据[/]")
        return

    max_val = max(data.values()) or 1
    table = Table(title=f"📅 Commit 活跃度（按{period}）", show_lines=True)
    table.add_column("时间段", style="cyan")
    table.add_column("Commits", justify="right")
    table.add_column("趋势", style="green")

    for period_key, count in data.items():
        bar_len = int(count / max_val * 30)
        bar = "█" * bar_len
        table.add_row(period_key, str(count), bar)
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=15, help="显示前 N 种文件类型")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def filetypes(
    ctx: click.Context, since: str | None, until: str | None, top: int, fmt: str
) -> None:
    """📁 文件类型分布"""
    from git_archaeologist.core import GitArchaeologist

    repo: str = ctx.obj["repo"]
    arch = GitArchaeologist(repo)
    result = arch.analyze_file_types(since=_parse_since(since), until=_parse_since(until))[:top]

    if fmt == "json":
        from dataclasses import asdict
        click.echo(json.dumps([asdict(ft) for ft in result], ensure_ascii=False, indent=2))
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    table = Table(title="📁 文件类型分布", show_lines=True)
    table.add_column("扩展名", style="cyan")
    table.add_column("文件数", justify="right")
    table.add_column("变更次数", justify="right", style="bold yellow")
    table.add_column("新增行", justify="right", style="green")
    table.add_column("删除行", justify="right", style="red")

    for ft in result:
        table.add_row(
            ft.extension,
            str(ft.file_count),
            str(ft.total_changes),
            f"+{_format_number(ft.total_insertions)}",
            f"-{_format_number(ft.total_deletions)}",
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--output", "-o", default="report.html", help="输出文件路径")
@click.option("--title", default=None, help="报告标题")
@click.pass_context
def report(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    output: str,
    title: str | None,
) -> None:
    """🌐 生成 HTML 分析报告"""
    from git_archaeologist.report import save_html_report

    repo: str = ctx.obj["repo"]
    out = save_html_report(
        output_path=output,
        repo_path=repo,
        since=_parse_since(since),
        until=_parse_since(until),
        title=title,
    )
    console.print(f"[green]✅ 报告已生成: {out.resolve()}[/]")


if __name__ == "__main__":
    main()
