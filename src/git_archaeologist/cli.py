"""CLI 子命令 — stats, authors, hotspots, activity, filetypes 等。"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from git_archaeologist.analyzer import Analyzer
from git_archaeologist import __version__

console = Console()


def _write_output(content: str, output: str | None) -> None:
    """输出到文件或 stdout。"""
    if output:
        Path(output).write_text(content, encoding="utf-8")
        console.print(f"[green]✅ 已写入: {output}[/]")
    else:
        click.echo(content)


def output_option(f):
    """为命令添加 --output/-o 选项的装饰器。"""
    return click.option(
        "--output", "-o", default=None, help="输出到文件（默认 stdout）"
    )(f)


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


# ── 公共选项装饰器 ─────────────────────────────────────────────────

def time_filter_options(f):
    """为命令添加 --since/--until 时间过滤选项。"""
    f = click.option("--since", default=None, help="起始时间 (YYYY-MM-DD 或 1y/6m/30d)")(f)
    f = click.option("--until", default=None, help="结束时间")(f)
    return f


def author_filter_option(f):
    """为命令添加 --author 过滤选项。"""
    return click.option("--author", default=None, help="按作者过滤（匹配 name 或 email）")(f)


def path_filter_option(f):
    """为命令添加 --path 过滤选项。"""
    return click.option("--path", "filter_path", default=None, help="按文件路径过滤")(f)


def format_option(f):
    """为命令添加 --format 选项。"""
    return click.option(
        "--format", "fmt",
        type=click.Choice(["table", "json", "csv", "markdown"]),
        default="table",
    )(f)


@click.group()
@click.version_option(version=__version__, prog_name="git-archaeologist")
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


# (activity 命令已移至下方 v0.7.0 区域，支持 --path/--author 过滤)


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


# ── v0.6.0 新增子命令 ────────────────────────────────────────────


@main.command()
@click.option("--top", default=20, help="显示前 N 个文件")
@click.option("--rev", default="HEAD", help="Git revision（默认 HEAD）")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv", "markdown"]),
    default="table",
)
@output_option
@click.pass_context
def blame(ctx: click.Context, top: int, rev: str, fmt: str, output: str | None) -> None:
    """🔍 代码归属分析 — 基于 git blame 查看每行代码的作者"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.blame_analysis(top_n=top, rev=rev)

    if fmt == "json":
        data = [
            {
                "path": e.path,
                "total_lines": e.total_lines,
                "top_author": e.top_author,
                "top_author_lines": e.top_author_lines,
                "top_author_pct": e.top_author_pct,
                "authors": e.authors,
                "oldest_line": e.oldest_line_date.isoformat() if e.oldest_line_date else None,
                "newest_line": e.newest_line_date.isoformat() if e.newest_line_date else None,
            }
            for e in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["path", "total_lines", "top_author", "top_author_lines", "top_author_pct"]
        rows = [
            [e.path, e.total_lines, e.top_author, e.top_author_lines, e.top_author_pct]
            for e in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if fmt == "markdown":
        headers = ["#", "文件路径", "总行数", "主要作者", "行数", "占比"]
        rows = [
            [
                str(i),
                e.path,
                str(e.total_lines),
                e.top_author,
                str(e.top_author_lines),
                f"{e.top_author_pct:.0f}%",
            ]
            for i, e in enumerate(result, 1)
        ]
        _write_output(_output_markdown_table(headers, rows), output)
        return

    if not result:
        console.print("[dim]无 blame 数据[/]")
        return

    table = Table(title="🔍 代码归属（git blame）", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("文件路径", style="cyan", max_width=50)
    table.add_column("总行数", justify="right")
    table.add_column("主要作者", style="bold")
    table.add_column("行数", justify="right", style="bold yellow")
    table.add_column("占比", justify="right")
    table.add_column("作者数", justify="right")

    for i, e in enumerate(result, 1):
        risk = "[red]⚠ 独占[/]" if e.top_author_pct > 80 else ""
        table.add_row(
            str(i),
            e.path,
            str(e.total_lines),
            e.top_author,
            str(e.top_author_lines),
            f"{e.top_author_pct:.0f}% {risk}",
            str(len(e.authors)),
        )
    console.print(table)


@main.command()
@click.option("--since", default=None, help="起始时间")
@click.option("--until", default=None, help="结束时间")
@click.option(
    "--period",
    type=click.Choice(["week", "month", "quarter", "year"]),
    default="month",
    help="统计周期",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv", "markdown"]),
    default="table",
)
@output_option
@click.pass_context
def complexity(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    period: str,
    fmt: str,
    output: str | None,
) -> None:
    """📈 代码复杂度趋势 — 追踪 LOC、文件数随时间变化"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.complexity_trend(
        period=period, since=_parse_since(since), until=_parse_since(until)
    )

    if fmt == "json":
        data = [
            {
                "period": p.period,
                "total_files": p.total_files,
                "total_lines": p.total_lines,
                "commits_in_period": p.commits_in_period,
                "net_lines_added": p.net_lines_added,
            }
            for p in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["period", "total_files", "total_lines", "commits", "net_lines"]
        rows = [
            [p.period, p.total_files, p.total_lines, p.commits_in_period, p.net_lines_added]
            for p in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if not result:
        console.print("[dim]无复杂度数据[/]")
        return

    max_lines = max(p.total_lines for p in result) or 1
    table = Table(title=f"📈 代码复杂度趋势（按{period}）", show_lines=True)
    table.add_column("时间段", style="cyan")
    table.add_column("文件数", justify="right")
    table.add_column("总行数", justify="right", style="bold yellow")
    table.add_column("趋势", style="green")
    table.add_column("Commits", justify="right")
    table.add_column("净增行数", justify="right")

    for p in result:
        bar_len = int(p.total_lines / max_lines * 30)
        bar = "█" * bar_len
        net_style = "green" if p.net_lines_added >= 0 else "red"
        table.add_row(
            p.period,
            str(p.total_files),
            _format_number(p.total_lines),
            bar,
            str(p.commits_in_period),
            f"[{net_style}]{p.net_lines_added:+d}[/]",
        )
    console.print(table)


@main.command("diff")
@click.option("--a-since", required=True, help="时间段 A 起始")
@click.option("--a-until", required=True, help="时间段 A 结束")
@click.option("--b-since", required=True, help="时间段 B 起始")
@click.option("--b-until", required=True, help="时间段 B 结束")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
)
@output_option
@click.pass_context
def diff_cmd(
    ctx: click.Context,
    a_since: str,
    a_until: str,
    b_since: str,
    b_until: str,
    fmt: str,
    output: str | None,
) -> None:
    """⚖️ 时段对比 — 比较两个时间段的指标变化"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.period_diff(
        period_a_since=_parse_since(a_since),
        period_a_until=_parse_since(a_until),
        period_b_since=_parse_since(b_since),
        period_b_until=_parse_since(b_until),
    )

    if fmt == "json":
        data = {
            "period_a_commits": result.period_a_commits,
            "period_b_commits": result.period_b_commits,
            "commits_change": result.commits_change,
            "period_a_authors": result.period_a_authors,
            "period_b_authors": result.period_b_authors,
            "authors_change": result.authors_change,
            "period_a_files": result.period_a_files,
            "period_b_files": result.period_b_files,
            "files_change": result.files_change,
            "period_a_insertions": result.period_a_insertions,
            "period_b_insertions": result.period_b_insertions,
            "period_a_deletions": result.period_a_deletions,
            "period_b_deletions": result.period_b_deletions,
            "new_authors": result.new_authors,
            "departed_authors": result.departed_authors,
            "most_changed_files": result.most_changed_files,
        }
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["metric", "period_a", "period_b", "change_pct"]
        rows = [
            ["commits", result.period_a_commits, result.period_b_commits, f"{result.commits_change:.1f}%"],
            ["authors", result.period_a_authors, result.period_b_authors, f"{result.authors_change:.1f}%"],
            ["files", result.period_a_files, result.period_b_files, f"{result.files_change:.1f}%"],
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    def _pct_str(pct: float) -> str:
        if pct > 0:
            return f"[green]+{pct:.1f}%[/]"
        elif pct < 0:
            return f"[red]{pct:.1f}%[/]"
        return f"{pct:.1f}%"

    table = Table(title="⚖️ 时段对比", show_lines=True)
    table.add_column("指标", style="cyan")
    table.add_column("时段 A", justify="right")
    table.add_column("时段 B", justify="right")
    table.add_column("变化", justify="right")

    table.add_row("Commits", str(result.period_a_commits), str(result.period_b_commits),
                   _pct_str(result.commits_change))
    table.add_row("贡献者", str(result.period_a_authors), str(result.period_b_authors),
                   _pct_str(result.authors_change))
    table.add_row("涉及文件", str(result.period_a_files), str(result.period_b_files),
                   _pct_str(result.files_change))
    table.add_row("新增行", _format_number(result.period_a_insertions),
                   _format_number(result.period_b_insertions), "")
    table.add_row("删除行", _format_number(result.period_a_deletions),
                   _format_number(result.period_b_deletions), "")
    console.print(table)

    if result.new_authors:
        console.print(f"\n[green]🆕 新增贡献者: {', '.join(result.new_authors)}[/]")
    if result.departed_authors:
        console.print(f"[red]👋 离开贡献者: {', '.join(result.departed_authors)}[/]")
    if result.most_changed_files:
        console.print("\n[bold]📊 变化最大的文件:[/]")
        for fpath, count in result.most_changed_files[:5]:
            console.print(f"  {fpath} ({count} 次变更)")


# ── v0.7.0 新增子命令 ────────────────────────────────────────────


@main.command("tags")
@click.option("--top", default=30, help="显示前 N 个标签")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv", "markdown"]),
    default="table",
)
@output_option
@click.pass_context
def tags_cmd(ctx: click.Context, top: int, fmt: str, output: str | None) -> None:
    """🏷️ 标签/版本列表 — 显示仓库标签及关联 commit"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.list_tags(max_count=top)

    if fmt == "json":
        data = [
            {
                "name": t.name,
                "sha": t.sha,
                "tag_date": t.tag_date.isoformat() if t.tag_date else None,
                "tagger": t.tagger,
                "message": t.message,
                "commit_sha": t.commit_sha,
                "commit_date": t.commit_date.isoformat() if t.commit_date else None,
                "commit_author": t.commit_author,
            }
            for t in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["name", "commit_sha", "tag_date", "commit_author", "message"]
        rows = [
            [t.name, t.commit_sha[:12] if t.commit_sha else "",
             t.tag_date.strftime("%Y-%m-%d") if t.tag_date else "",
             t.commit_author, t.message[:60]]
            for t in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if fmt == "markdown":
        headers = ["#", "标签", "Commit", "日期", "作者", "说明"]
        rows = [
            [str(i), t.name, t.commit_sha[:12] if t.commit_sha else "-",
             t.tag_date.strftime("%Y-%m-%d") if t.tag_date else "-",
             t.commit_author.split(" <")[0] if t.commit_author else "-",
             t.message[:50] if t.message else "-"]
            for i, t in enumerate(result, 1)
        ]
        _write_output(_output_markdown_table(headers, rows), output)
        return

    if not result:
        console.print("[dim]无标签数据[/]")
        return

    table = Table(title="🏷️ 标签/版本列表", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("标签", style="bold cyan")
    table.add_column("Commit", style="dim")
    table.add_column("日期", justify="right")
    table.add_column("作者", style="bold")
    table.add_column("说明", max_width=40)

    for i, t in enumerate(result, 1):
        commit_short = t.commit_sha[:12] if t.commit_sha else "-"
        date_str = t.tag_date.strftime("%Y-%m-%d") if t.tag_date else "-"
        author_str = t.commit_author.split(" <")[0] if t.commit_author else "-"
        msg = t.message[:50] if t.message else "-"
        table.add_row(str(i), t.name, commit_short, date_str, author_str, msg)
    console.print(table)

    console.print(f"\n[dim]共 {len(result)} 个标签[/]")


@main.command("file-history")
@click.argument("filepath")
@click.option("--top", default=30, help="显示前 N 条记录")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "json", "csv", "markdown"]),
    default="table",
)
@output_option
@click.pass_context
def file_history_cmd(
    ctx: click.Context, filepath: str, top: int, fmt: str, output: str | None
) -> None:
    """📜 文件修改历史 — 查看指定文件的变更记录"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.file_history(file_path=filepath, max_count=top)

    if fmt == "json":
        data = [
            {
                "sha": c.sha,
                "author": c.author_name,
                "date": c.authored_date.isoformat(),
                "message": c.message.split("\n")[0].strip(),
                "insertions": c.insertions,
                "deletions": c.deletions,
            }
            for c in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["sha", "author", "date", "message", "insertions", "deletions"]
        rows = [
            [c.sha[:12], c.author_name,
             c.authored_date.strftime("%Y-%m-%d %H:%M"),
             c.message.split("\n")[0].strip()[:60],
             c.insertions, c.deletions]
            for c in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if fmt == "markdown":
        headers = ["#", "SHA", "作者", "日期", "说明", "变更"]
        rows = [
            [str(i), c.sha[:12], c.author_name,
             c.authored_date.strftime("%Y-%m-%d"),
             c.message.split("\n")[0].strip()[:60],
             f"+{c.insertions}/-{c.deletions}"]
            for i, c in enumerate(result, 1)
        ]
        _write_output(_output_markdown_table(headers, rows), output)
        return

    if not result:
        console.print(f"[dim]文件 {filepath} 无修改历史[/]")
        return

    table = Table(title=f"📜 文件历史: {filepath}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("SHA", style="dim", width=12)
    table.add_column("作者", style="cyan")
    table.add_column("日期", justify="right")
    table.add_column("说明", max_width=50)
    table.add_column("变更", justify="right")

    for i, c in enumerate(result, 1):
        date_str = c.authored_date.strftime("%Y-%m-%d %H:%M")
        msg = c.message.split("\n")[0].strip()[:50]
        changes = f"[green]+{c.insertions}[/]/[red]-{c.deletions}[/]"
        table.add_row(str(i), c.sha[:12], c.author_name, date_str, msg, changes)
    console.print(table)

    console.print(f"\n[dim]共 {len(result)} 条记录[/]")


@main.command("search")
@click.argument("pattern")
@time_filter_options
@format_option
@output_option
@click.pass_context
def search_cmd(
    ctx: click.Context,
    pattern: str,
    since: str | None,
    until: str | None,
    fmt: str,
    output: str | None,
) -> None:
    """🔍 搜索 commit 消息 — 支持正则表达式"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.search_messages(
        pattern=pattern, since=_parse_since(since), until=_parse_since(until)
    )

    if fmt == "json":
        data = [
            {
                "sha": m.sha,
                "author": m.author_name,
                "date": m.authored_date.isoformat(),
                "message": m.message,
                "matched_text": m.matched_text,
            }
            for m in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["sha", "author", "date", "message"]
        rows = [
            [m.sha[:12], m.author_name,
             m.authored_date.strftime("%Y-%m-%d"),
             m.message[:60]]
            for m in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if fmt == "markdown":
        headers = ["#", "SHA", "作者", "日期", "说明"]
        rows = [
            [str(i), m.sha[:12], m.author_name,
             m.authored_date.strftime("%Y-%m-%d"),
             m.message[:60]]
            for i, m in enumerate(result, 1)
        ]
        _write_output(_output_markdown_table(headers, rows), output)
        return

    if not result:
        console.print(f"[dim]未找到匹配 \'{pattern}\' 的 commit[/]")
        return

    table = Table(title=f"🔍 搜索: {pattern}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("SHA", style="dim", width=12)
    table.add_column("作者", style="cyan")
    table.add_column("日期", justify="right")
    table.add_column("说明", max_width=60)

    for i, m in enumerate(result, 1):
        date_str = m.authored_date.strftime("%Y-%m-%d")
        msg = m.message[:55]
        table.add_row(str(i), m.sha[:12], m.author_name, date_str, msg)
    console.print(table)

    console.print(f"\n[dim]共 {len(result)} 条匹配[/]")


@main.command("contributors-timeline")
@time_filter_options
@click.option(
    "--period",
    type=click.Choice(["week", "month", "quarter", "year"]),
    default="month",
    help="统计周期",
)
@format_option
@output_option
@click.pass_context
def contributors_timeline_cmd(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    period: str,
    fmt: str,
    output: str | None,
) -> None:
    """📈 贡献者时间线 — 按时间段统计贡献者数量变化"""
    analyzer: Analyzer = ctx.obj["analyzer"]
    result = analyzer.contributor_timeline(
        period=period, since=_parse_since(since), until=_parse_since(until)
    )

    if fmt == "json":
        data = [
            {
                "period": p.period,
                "total_contributors": p.total_contributors,
                "new_contributors": p.new_contributors,
                "active_contributors": p.active_contributors,
                "commits": p.commits,
            }
            for p in result
        ]
        _write_output(json.dumps(data, ensure_ascii=False, indent=2), output)
        return

    if fmt == "csv":
        headers = ["period", "total_contributors", "new_contributors", "active_contributors", "commits"]
        rows = [
            [p.period, p.total_contributors, p.new_contributors, p.active_contributors, p.commits]
            for p in result
        ]
        _write_output(_output_csv(headers, rows), output)
        return

    if not result:
        console.print("[dim]无数据[/]")
        return

    max_contrib = max(p.total_contributors for p in result) or 1
    table = Table(title=f"📈 贡献者时间线（按{period}）", show_lines=True)
    table.add_column("时间段", style="cyan")
    table.add_column("总贡献者", justify="right", style="bold yellow")
    table.add_column("新增", justify="right", style="green")
    table.add_column("活跃", justify="right")
    table.add_column("Commits", justify="right")
    table.add_column("趋势", style="green")

    for p in result:
        bar_len = int(p.total_contributors / max_contrib * 30)
        bar = "█" * bar_len
        table.add_row(
            p.period,
            str(p.total_contributors),
            f"[green]+{p.new_contributors}[/]" if p.new_contributors else "0",
            str(p.active_contributors),
            str(p.commits),
            bar,
        )
    console.print(table)


# ── 恢复 activity 命令（带 --path/--author 过滤） ─────────────────

@main.command("activity")
@time_filter_options
@click.option("--filter-path", "filter_path", default=None, help="按文件路径过滤")
@click.option("--filter-author", "filter_author", default=None, help="按作者过滤")
@click.option(
    "--period",
    type=click.Choice(["day", "week", "month", "year"]),
    default="month",
    help="统计周期",
)
@format_option
@click.pass_context
def activity_cmd(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    filter_path: str | None,
    filter_author: str | None,
    period: str,
    fmt: str,
) -> None:
    """📅 Commit 活跃度趋势"""
    from collections import Counter as _Counter

    analyzer: Analyzer = ctx.obj["analyzer"]
    counter: _Counter[str] = _Counter()
    for c in analyzer.miner.iter_commits(
        since=_parse_since(since),
        until=_parse_since(until),
        author=filter_author,
        path=filter_path,
    ):
        if period == "day":
            key = c.authored_date.strftime("%Y-%m-%d")
        elif period == "week":
            key = c.authored_date.strftime("%Y-W%W")
        elif period == "month":
            key = c.authored_date.strftime("%Y-%m")
        elif period == "year":
            key = c.authored_date.strftime("%Y")
        else:
            key = c.authored_date.strftime("%Y-%m")
        counter[key] += 1

    data = dict(sorted(counter.items()))

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
