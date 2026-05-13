"""CLI 子命令 — stats, authors, hotspots, activity, filetypes 等。"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from git_archaeologist.analyzer import Analyzer

console = Console()


def _output_csv(headers: list[str], rows: list[list[str]]) -> str:
    """生成 CSV 格式输出。"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _output_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """生成 Markdown 表格输出。"""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


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
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
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

    if fmt == "csv":
        headers = ["total_commits", "total_authors", "total_files_changed",
                    "total_insertions", "total_deletions", "active_days", "avg_commits_per_day"]
        row = [s.total_commits, s.total_authors, s.total_files_changed,
               s.total_insertions, s.total_deletions, s.active_days, s.avg_commits_per_day]
        click.echo(_output_csv(headers, [row]))
        return

    if fmt == "markdown":
        headers = ["指标", "值"]
        rows = [
            ["总 Commits", str(s.total_commits)],
            ["贡献者数", str(s.total_authors)],
            ["涉及文件数", str(s.total_files_changed)],
            ["总新增行数", str(s.total_insertions)],
            ["总删除行数", str(s.total_deletions)],
            ["活跃天数", str(s.active_days)],
            ["日均 Commits", str(s.avg_commits_per_day)],
        ]
        click.echo(_output_markdown_table(headers, rows))
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
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
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

    if fmt == "csv":
        headers = ["name", "email", "commits", "insertions", "deletions", "files_touched"]
        rows = [[a.name, a.email, a.commit_count, a.insertions, a.deletions,
                 len(a.files_touched)] for a in result]
        click.echo(_output_csv(headers, rows))
        return

    if fmt == "markdown":
        headers = ["#", "作者", "Commits", "新增行", "删除行", "涉及文件"]
        rows = [[str(i), a.name, str(a.commit_count), str(a.insertions),
                 str(a.deletions), str(len(a.files_touched))]
                for i, a in enumerate(result, 1)]
        click.echo(_output_markdown_table(headers, rows))
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
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
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

    if fmt == "csv":
        headers = ["path", "changes", "authors", "last_modified"]
        rows = [[f.path, f.change_count, len(f.authors),
                 f.last_modified.strftime("%Y-%m-%d") if f.last_modified else ""]
                for f in result]
        click.echo(_output_csv(headers, rows))
        return

    if fmt == "markdown":
        headers = ["#", "文件路径", "修改次数", "贡献者数", "最后修改"]
        rows = [[str(i), f.path, str(f.change_count), str(len(f.authors)),
                 f.last_modified.strftime("%Y-%m-%d") if f.last_modified else "-"]
                for i, f in enumerate(result, 1)]
        click.echo(_output_markdown_table(headers, rows))
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
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
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

    if fmt == "csv":
        headers = ["period", "commits"]
        rows = [[k, v] for k, v in data.items()]
        click.echo(_output_csv(headers, rows))
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
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
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


# ── 新增高级分析子命令 ────────────────────────────────────────────


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=20, help="显示前 N 对")
@click.option("--min-co-change", default=2, help="最少共同修改次数")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def coupling(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    top: int,
    min_co_change: int,
    fmt: str,
) -> None:
    """🔗 文件耦合分析 — 经常一起被修改的文件对"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.coupling(
        since=_parse_since(since),
        until=_parse_since(until),
        top_n=top,
        min_co_change=min_co_change,
    )

    if fmt == "json":
        data = [
            {
                "file_a": p.file_a,
                "file_b": p.file_b,
                "co_change_count": p.co_change_count,
                "coupling_strength": p.coupling_strength,
            }
            for p in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if fmt == "csv":
        headers = ["file_a", "file_b", "co_change_count", "coupling_strength"]
        rows = [[p.file_a, p.file_b, p.co_change_count, p.coupling_strength]
                for p in result]
        click.echo(_output_csv(headers, rows))
        return

    if not result:
        console.print("[dim]无耦合数据[/]")
        return

    table = Table(title="🔗 文件耦合对", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("文件 A", style="cyan", max_width=40)
    table.add_column("文件 B", style="cyan", max_width=40)
    table.add_column("共变次数", justify="right", style="bold yellow")
    table.add_column("耦合强度", justify="right", style="green")

    for i, p in enumerate(result, 1):
        strength_bar = "█" * int(p.coupling_strength * 10)
        table.add_row(
            str(i),
            p.file_a,
            p.file_b,
            str(p.co_change_count),
            f"{p.coupling_strength:.1%} {strength_bar}",
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--entity", type=click.Choice(["file", "dir"]), default="file", help="分析粒度")
@click.option("--top", default=20, help="显示前 N 个")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def busfactor(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    entity: str,
    top: int,
    fmt: str,
) -> None:
    """🚌 Bus Factor — 关键人员依赖度分析"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.bus_factor(
        since=_parse_since(since),
        until=_parse_since(until),
        entity=entity,
        top_n=top,
    )

    if fmt == "json":
        data = [
            {
                "entity": e.entity,
                "total_changes": e.total_changes,
                "top_contributor": e.top_contributor,
                "top_contributor_pct": e.top_contributor_pct,
                "contributor_count": e.contributor_count,
                "bus_factor": e.bus_factor,
                "contributors": e.contributors,
            }
            for e in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    entity_label = "目录" if entity == "dir" else "文件"
    table = Table(title=f"🚌 Bus Factor（按{entity_label}）", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column(entity_label, style="cyan", max_width=50)
    table.add_column("主要贡献者", style="bold")
    table.add_column("占比", justify="right", style="bold yellow")
    table.add_column("贡献者数", justify="right")
    table.add_column("Bus Factor", justify="right", style="red")

    for i, e in enumerate(result, 1):
        risk = "[red]⚠ 高[/]" if e.bus_factor == 1 else "[green]✓ 安全[/]"
        table.add_row(
            str(i),
            e.entity,
            e.top_contributor,
            f"{e.top_contributor_pct:.0f}%",
            str(e.contributor_count),
            f"{e.bus_factor} {risk}",
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=20, help="显示前 N 个")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def churn(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    top: int,
    fmt: str,
) -> None:
    """🔄 Churn 分析 — 高变动率文件（反复重写）"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.churn(
        since=_parse_since(since),
        until=_parse_since(until),
        top_n=top,
    )

    if fmt == "json":
        data = [
            {
                "path": e.path,
                "total_insertions": e.total_insertions,
                "total_deletions": e.total_deletions,
                "net_lines": e.net_lines,
                "change_count": e.change_count,
                "churn_ratio": e.churn_ratio,
            }
            for e in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    table = Table(title="🔄 Churn 分析", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("文件路径", style="cyan", max_width=50)
    table.add_column("变更次数", justify="right")
    table.add_column("新增行", justify="right", style="green")
    table.add_column("删除行", justify="right", style="red")
    table.add_column("净变更", justify="right")
    table.add_column("变动率", justify="right", style="bold yellow")

    for i, e in enumerate(result, 1):
        risk = "[red]⚠ 高[/]" if e.churn_ratio > 5 else ""
        table.add_row(
            str(i),
            e.path,
            str(e.change_count),
            f"+{_format_number(e.total_insertions)}",
            f"-{_format_number(e.total_deletions)}",
            _format_number(e.net_lines),
            f"{e.churn_ratio}x {risk}",
        )
    console.print(table)


@main.command("dirs")
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--top", default=20, help="显示前 N 个目录")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def dirs_cmd(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    top: int,
    fmt: str,
) -> None:
    """📂 目录级统计"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.dir_stats(
        since=_parse_since(since),
        until=_parse_since(until),
        top_n=top,
    )

    if fmt == "json":
        data = [
            {
                "path": d.path,
                "file_count": d.file_count,
                "total_changes": d.total_changes,
                "total_insertions": d.total_insertions,
                "total_deletions": d.total_deletions,
                "authors": list(d.authors),
                "last_modified": d.last_modified.isoformat() if d.last_modified else None,
            }
            for d in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    table = Table(title="📂 目录统计", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("目录", style="cyan", max_width=50)
    table.add_column("文件数", justify="right")
    table.add_column("变更次数", justify="right", style="bold yellow")
    table.add_column("新增行", justify="right", style="green")
    table.add_column("删除行", justify="right", style="red")
    table.add_column("贡献者数", justify="right")
    table.add_column("最后修改", justify="right")

    for i, d in enumerate(result, 1):
        last_mod = d.last_modified.strftime("%Y-%m-%d") if d.last_modified else "-"
        table.add_row(
            str(i),
            d.path,
            str(d.file_count),
            str(d.total_changes),
            f"+{_format_number(d.total_insertions)}",
            f"-{_format_number(d.total_deletions)}",
            str(len(d.authors)),
            last_mod,
        )
    console.print(table)


@main.command("ages")
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option(
    "--sort",
    type=click.Choice(["stale", "oldest", "active"]),
    default="stale",
    help="排序方式",
)
@click.option("--top", default=20, help="显示前 N 个")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def ages_cmd(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    sort: str,
    top: int,
    fmt: str,
) -> None:
    """🕰️ 文件年龄分析 — 最陈旧/最早/最活跃"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.file_ages(
        since=_parse_since(since),
        until=_parse_since(until),
        sort_by=sort,
        top_n=top,
    )

    if fmt == "json":
        data = [
            {
                "path": e.path,
                "first_seen": e.first_seen.isoformat() if e.first_seen else None,
                "last_modified": e.last_modified.isoformat() if e.last_modified else None,
                "change_count": e.change_count,
                "primary_author": e.primary_author,
                "age_days": e.age_days,
                "stale_days": e.stale_days,
            }
            for e in result
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    sort_labels = {"stale": "最陈旧", "oldest": "最早出现", "active": "最近修改"}
    table = Table(title=f"🕰️ 文件年龄（{sort_labels.get(sort, sort)}）", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("文件路径", style="cyan", max_width=50)
    table.add_column("变更次数", justify="right")
    table.add_column("主要作者", style="bold")
    table.add_column("首次出现", justify="right")
    table.add_column("最后修改", justify="right")
    table.add_column("陈旧天数", justify="right", style="bold yellow")

    for i, e in enumerate(result, 1):
        first = e.first_seen.strftime("%Y-%m-%d") if e.first_seen else "-"
        last = e.last_modified.strftime("%Y-%m-%d") if e.last_modified else "-"
        stale = str(e.stale_days) if e.stale_days is not None else "-"
        stale_style = "[red]" if (e.stale_days or 0) > 365 else ""
        table.add_row(
            str(i),
            e.path,
            str(e.change_count),
            e.primary_author or "-",
            first,
            last,
            f"{stale_style}{stale}",
        )
    console.print(table)


if __name__ == "__main__":
    main()


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def heatmap(ctx: click.Context, since: str | None, until: str | None, fmt: str) -> None:
    """🗓️ Commit 热力图 — 按星期×小时分析活跃模式"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    heatmap_data = analyzer.commit_heatmap(since=_parse_since(since), until=_parse_since(until))

    if fmt == "json":
        click.echo(json.dumps(heatmap_data, ensure_ascii=False, indent=2))
        return

    if fmt == "csv":
        headers = ["day"] + [f"{h:02d}" for h in range(24)]
        rows = []
        for day in heatmap_data:
            rows.append([day] + [heatmap_data[day][f"{h:02d}"] for h in range(24)])
        click.echo(_output_csv(headers, rows))
        return

    days = list(heatmap_data.keys())
    hours = [f"{h:02d}" for h in range(24)]

    # 找到最大值用于颜色映射
    max_val = 0
    for day_data in heatmap_data.values():
        for v in day_data.values():
            max_val = max(max_val, v)
    if max_val == 0:
        console.print("[dim]无数据[/]")
        return

    # 终端热力图表格
    table = Table(title="🗓️ Commit 热力图（星期 × 小时）", show_lines=False)
    table.add_column("时段", style="dim", width=6)
    for h in hours:
        table.add_column(h, justify="center", width=3)

    intensity_styles = ["dim", "", "green", "bold green", "bold yellow", "bold red"]

    for day in days:
        row = [day[:3]]
        for h in hours:
            val = heatmap_data[day][h]
            if val == 0:
                row.append("[dim]·[/]")
            else:
                ratio = val / max_val
                level = min(int(ratio * 5), 5)
                style = intensity_styles[level]
                if style:
                    row.append(f"[{style}]{val}[/]")
                else:
                    row.append(str(val))
        table.add_row(*row)

    console.print(table)

    # 汇总统计
    total = sum(v for d in heatmap_data.values() for v in d.values())
    peak_day = max(days, key=lambda d: sum(heatmap_data[d].values()))
    peak_hour = max(hours, key=lambda h: sum(heatmap_data[d][h] for d in days))
    console.print(
        f"\n[dim]总计 {total} 个 commit"
        f" | 最活跃日: {peak_day}"
        f" | 最活跃时: {peak_hour}:00[/]"
    )


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv", "markdown"]), default="table")
@click.pass_context
def summary(ctx: click.Context, since: str | None, until: str | None, fmt: str) -> None:
    """📋 一站式仓库分析概览"""
    from git_archaeologist.core import GitArchaeologist

    repo: str = ctx.obj["repo"]
    arch = GitArchaeologist(repo)
    s = arch.summary(since=_parse_since(since), until=_parse_since(until))

    if fmt == "json":
        click.echo(json.dumps(s.to_dict(), ensure_ascii=False, indent=2))
        return

    if fmt == "csv":
        stats = s.stats
        headers = ["total_commits", "total_authors", "total_files_changed",
                    "total_insertions", "total_deletions", "active_days"]
        row = [stats.total_commits, stats.total_authors, stats.total_files_changed,
               stats.total_insertions, stats.total_deletions, stats.active_days]
        click.echo(_output_csv(headers, [row]))
        return

    # 仓库统计卡片
    stats = s.stats
    table = Table(title="📋 仓库概览", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green", justify="right")
    table.add_row("总 Commits", _format_number(stats.total_commits))
    table.add_row("贡献者数", _format_number(stats.total_authors))
    table.add_row("涉及文件数", _format_number(stats.total_files_changed))
    table.add_row("总新增行数", f"[green]+{_format_number(stats.total_insertions)}[/]")
    table.add_row("总删除行数", f"[red]-{_format_number(stats.total_deletions)}[/]")
    table.add_row("净变更行数", _format_number(stats.total_insertions - stats.total_deletions))
    if stats.first_commit_date:
        table.add_row("首次提交", stats.first_commit_date.strftime("%Y-%m-%d"))
    if stats.last_commit_date:
        table.add_row("最后提交", stats.last_commit_date.strftime("%Y-%m-%d"))
    table.add_row("活跃天数", _format_number(stats.active_days))
    table.add_row("日均 Commits", str(stats.avg_commits_per_day))
    console.print(table)

    # Top 贡献者
    if s.top_authors:
        console.print()
        authors_table = Table(title="👤 Top 贡献者", show_lines=True)
        authors_table.add_column("#", style="dim", width=4)
        authors_table.add_column("作者", style="cyan")
        authors_table.add_column("Commits", justify="right")
        authors_table.add_column("新增行", justify="right", style="green")
        authors_table.add_column("删除行", justify="right", style="red")
        for i, a in enumerate(s.top_authors[:5], 1):
            authors_table.add_row(
                str(i), a.name, str(a.commit_count),
                f"+{_format_number(a.insertions)}", f"-{_format_number(a.deletions)}",
            )
        console.print(authors_table)

    # Top 热点文件
    if s.top_hotspots:
        console.print()
        hotspots_table = Table(title="🔥 Top 热点文件", show_lines=True)
        hotspots_table.add_column("#", style="dim", width=4)
        hotspots_table.add_column("文件", style="cyan", max_width=50)
        hotspots_table.add_column("修改次数", justify="right", style="bold yellow")
        for i, f in enumerate(s.top_hotspots[:5], 1):
            hotspots_table.add_row(str(i), f.path, str(f.change_count))
        console.print(hotspots_table)

    # 文件类型
    if s.file_types:
        console.print()
        ft_table = Table(title="📁 文件类型 Top 5", show_lines=True)
        ft_table.add_column("扩展名", style="cyan")
        ft_table.add_column("文件数", justify="right")
        ft_table.add_column("变更次数", justify="right", style="bold yellow")
        for ft in s.file_types[:5]:
            ft_table.add_row(ft.extension, str(ft.file_count), str(ft.total_changes))
        console.print(ft_table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv"]), default="table")
@click.pass_context
def health(ctx: click.Context, since: str | None, until: str | None, fmt: str) -> None:
    """仓库健康评分 — 综合评估仓库质量"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.health_score(since=_parse_since(since), until=_parse_since(until))

    if fmt == "json":
        data = {
            "overall": result.overall,
            "bus_factor_score": result.bus_factor_score,
            "churn_score": result.churn_score,
            "activity_score": result.activity_score,
            "diversity_score": result.diversity_score,
            "summary": result.summary,
            "details": result.details,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if fmt == "csv":
        headers = ["overall", "bus_factor_score", "churn_score",
                    "activity_score", "diversity_score"]
        row = [result.overall, result.bus_factor_score, result.churn_score,
               result.activity_score, result.diversity_score]
        click.echo(_output_csv(headers, [row]))
        return

    table = Table(title="仓库健康评分", show_lines=True)
    table.add_column("维度", style="cyan")
    table.add_column("得分", justify="right", style="bold yellow")
    table.add_column("说明", style="dim")

    table.add_row("Bus Factor", f"{result.bus_factor_score}/30",
                   result.details.get("bus_factor", ""))
    table.add_row("Churn", f"{result.churn_score}/20",
                   result.details.get("churn", ""))
    table.add_row("Activity", f"{result.activity_score}/25",
                   result.details.get("activity", ""))
    table.add_row("Diversity", f"{result.diversity_score}/25",
                   result.details.get("diversity", ""))
    table.add_row("总分", f"[bold]{result.overall}/100[/]", result.summary)

    console.print(table)


@main.command("commit-messages")
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "csv"]), default="table")
@click.pass_context
def commit_messages(ctx: click.Context, since: str | None, until: str | None, fmt: str) -> None:
    """Commit 消息分析 — conventional commits、消息质量"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.commit_message_stats(since=_parse_since(since), until=_parse_since(until))

    if fmt == "json":
        data = {
            "total_commits": result.total_commits,
            "conventional_count": result.conventional_count,
            "conventional_pct": result.conventional_pct,
            "type_counts": result.type_counts,
            "avg_message_length": result.avg_message_length,
            "max_message_length": result.max_message_length,
            "min_message_length": result.min_message_length,
            "short_messages": result.short_messages,
            "long_messages": result.long_messages,
            "most_common_words": result.most_common_words,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if fmt == "csv":
        headers = ["total_commits", "conventional_count", "conventional_pct",
                    "avg_message_length", "short_messages", "long_messages"]
        row = [result.total_commits, result.conventional_count, result.conventional_pct,
               result.avg_message_length, result.short_messages, result.long_messages]
        click.echo(_output_csv(headers, [row]))
        return

    table = Table(title="Commit 消息分析", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green", justify="right")

    table.add_row("总 Commits", str(result.total_commits))
    table.add_row("Conventional Commits",
                   f"{result.conventional_count} ({result.conventional_pct:.1f}%)")
    table.add_row("平均消息长度", f"{result.avg_message_length:.1f} 字符")
    table.add_row("最长消息", f"{result.max_message_length} 字符")
    table.add_row("最短消息", f"{result.min_message_length} 字符")
    table.add_row("过短消息 (<10字符)", str(result.short_messages))
    table.add_row("过长消息 (>72字符)", str(result.long_messages))
    console.print(table)

    # 类型分布
    if result.type_counts:
        console.print()
        type_table = Table(title="Conventional Commit 类型分布", show_lines=True)
        type_table.add_column("类型", style="cyan")
        type_table.add_column("数量", justify="right", style="bold yellow")
        type_table.add_column("占比", justify="right")
        total_conv = sum(result.type_counts.values())
        for t, count in sorted(result.type_counts.items(), key=lambda x: -x[1]):
            pct = count / total_conv * 100 if total_conv else 0
            type_table.add_row(t, str(count), f"{pct:.1f}%")
        console.print(type_table)

    # 常见词汇
    if result.most_common_words:
        console.print()
        word_table = Table(title="常见词汇 Top 10", show_lines=True)
        word_table.add_column("词汇", style="cyan")
        word_table.add_column("出现次数", justify="right", style="bold yellow")
        for word, count in result.most_common_words[:10]:
            word_table.add_row(word, str(count))
        console.print(word_table)
