"""HTML 报告生成器 — 生成可浏览的仓库分析报告。"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from git_archaeologist.core import GitArchaeologist, RepoSummary


def _esc(text: str) -> str:
    """HTML 转义。"""
    return html.escape(str(text))


def _format_number(n: int) -> str:
    """千分位格式化。"""
    return f"{n:,}"


def _build_bar(value: int, max_value: int, width: int = 200) -> str:
    """生成一个简单的 CSS 横条。"""
    if max_value == 0:
        pct = 0
    else:
        pct = min(value / max_value * 100, 100)
    return (
        f'<div style="background:#2d333b;border-radius:4px;width:{width}px;height:18px;">'
        f'<div style="background:#3fb950;height:100%;width:{pct:.1f}%;border-radius:4px;"></div>'
        f"</div>"
    )


_CSS = """\
:root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
        --dim: #8b949e; --accent: #58a6ff; --green: #3fb950; --red: #f85149; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont,
         'Segoe UI', Helvetica, Arial, sans-serif;
       background: var(--bg); color: var(--text); padding: 24px;
       max-width: 1200px; margin: 0 auto; }
h1 { font-size: 1.8em; margin-bottom: 8px; }
h2 { font-size: 1.3em; margin: 24px 0 12px;
     border-bottom: 1px solid var(--border);
     padding-bottom: 6px; }
.subtitle { color: var(--dim); margin-bottom: 24px; }
.cards { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 24px; }
.card { background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; text-align: center; }
.card .value { font-size: 1.8em; font-weight: 700; color: var(--accent); }
.card .label { color: var(--dim); font-size: 0.85em; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--dim); font-weight: 600; font-size: 0.85em; text-transform: uppercase; }
tr:hover { background: rgba(88,166,255,0.05); }
.green { color: var(--green); } .red { color: var(--red); } .dim { color: var(--dim); }
.chart-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.chart-label { width: 80px; text-align: right; color: var(--dim); font-size: 0.85em; }
.chart-bar { flex: 1; }
footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--border);
         color: var(--dim); font-size: 0.8em; text-align: center; }
"""


def _render_stats_cards(summary: RepoSummary) -> str:
    """渲染统计卡片区域。"""
    s = summary.stats
    cards = [
        (_format_number(s.total_commits), "总 Commits"),
        (_format_number(s.total_authors), "贡献者"),
        (_format_number(s.total_files_changed), "涉及文件"),
        (f"+{_format_number(s.total_insertions)}", "新增行"),
        (f"-{_format_number(s.total_deletions)}", "删除行"),
        (_format_number(s.active_days), "活跃天数"),
        (str(s.avg_commits_per_day), "日均 Commits"),
    ]
    inner = "\n".join(
        f'<div class="card">'
        f'<div class="value">{_esc(val)}</div>'
        f'<div class="label">{_esc(label)}</div>'
        f'</div>'
        for val, label in cards
    )
    return f'<div class="cards">{inner}</div>'


def _render_authors_table(summary: RepoSummary) -> str:
    """渲染贡献者表格。"""
    if not summary.top_authors:
        return "<p class='dim'>无贡献者数据</p>"
    rows = []
    for i, a in enumerate(summary.top_authors, 1):
        last = a.last_commit.strftime("%Y-%m-%d") if a.last_commit else "-"
        rows.append(
            f"<tr><td>{i}</td><td>{_esc(a.name)}</td>"
            f"<td>{a.commit_count}</td>"
            f"<td class='green'>+{_format_number(a.insertions)}</td>"
            f"<td class='red'>-{_format_number(a.deletions)}</td>"
            f"<td>{len(a.files_touched)}</td>"
            f"<td class='dim'>{last}</td></tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>#</th><th>作者</th><th>Commits</th><th>新增行</th><th>删除行</th><th>涉及文件</th><th>最后活跃</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _render_hotspots_table(summary: RepoSummary) -> str:
    """渲染热点文件表格。"""
    if not summary.top_hotspots:
        return "<p class='dim'>无热点文件数据</p>"
    max_changes = summary.top_hotspots[0].change_count if summary.top_hotspots else 1
    rows = []
    for i, f in enumerate(summary.top_hotspots, 1):
        last = f.last_modified.strftime("%Y-%m-%d") if f.last_modified else "-"
        bar = _build_bar(f.change_count, max_changes, 120)
        rows.append(
            f"<tr><td>{i}</td><td>{_esc(f.path)}</td>"
            f"<td>{f.change_count}</td><td>{bar}</td>"
            f"<td>{len(f.authors)}</td>"
            f"<td class='dim'>{last}</td></tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>#</th><th>文件路径</th><th>修改次数</th><th>趋势</th><th>贡献者数</th><th>最后修改</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _render_filetypes_table(summary: RepoSummary) -> str:
    """渲染文件类型表格。"""
    if not summary.file_types:
        return "<p class='dim'>无文件类型数据</p>"
    max_changes = summary.file_types[0].total_changes if summary.file_types else 1
    rows = []
    for ft in summary.file_types[:15]:
        bar = _build_bar(ft.total_changes, max_changes, 120)
        rows.append(
            f"<tr><td>{_esc(ft.extension)}</td>"
            f"<td>{ft.file_count}</td>"
            f"<td>{ft.total_changes}</td><td>{bar}</td>"
            f"<td class='green'>+{_format_number(ft.total_insertions)}</td>"
            f"<td class='red'>-{_format_number(ft.total_deletions)}</td></tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>扩展名</th><th>文件数</th><th>变更次数</th><th>趋势</th><th>新增行</th><th>删除行</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _render_activity_chart(summary: RepoSummary) -> str:
    """渲染活跃度趋势图（纯 CSS 横条）。"""
    if not summary.activity_monthly:
        return "<p class='dim'>无活跃度数据</p>"
    max_val = max(summary.activity_monthly.values()) or 1
    rows = []
    for period, count in summary.activity_monthly.items():
        bar = _build_bar(count, max_val, 300)
        rows.append(
            f'<div class="chart-row">'
            f'<span class="chart-label">{_esc(period)}</span>'
            f'<span class="chart-bar">{bar}</span>'
            f'<span style="width:40px;text-align:right;font-size:0.85em;">{count}</span>'
            f"</div>"
        )
    return "\n".join(rows)


def generate_html_report(
    repo_path: str = ".",
    since: datetime | None = None,
    until: datetime | None = None,
    title: str | None = None,
) -> str:
    """生成完整的 HTML 分析报告。

    Args:
        repo_path: 仓库路径
        since: 起始时间
        until: 结束时间
        title: 报告标题（默认使用仓库路径）

    Returns:
        完整的 HTML 字符串
    """
    arch = GitArchaeologist(repo_path)
    summary = arch.summary(since=since, until=until)

    repo_name = title or Path(repo_path).resolve().name
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    first = summary.stats.first_commit_date
    last = summary.stats.last_commit_date
    date_range = ""
    if first and last:
        date_range = f" ({first.strftime('%Y-%m-%d')} → {last.strftime('%Y-%m-%d')})"

    body = f"""
<h1>🏺 {_esc(repo_name)}</h1>
<p class="subtitle">Git Archaeologist 分析报告 — 生成于 {now}{_esc(date_range)}</p>

{_render_stats_cards(summary)}

<h2>👤 贡献者排行</h2>
{_render_authors_table(summary)}

<h2>🔥 热点文件</h2>
{_render_hotspots_table(summary)}

<h2>📁 文件类型分布</h2>
{_render_filetypes_table(summary)}

<h2>📅 活跃度趋势（按月）</h2>
{_render_activity_chart(summary)}

<footer>Generated by <strong>Git Archaeologist</strong> v0.4.0</footer>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🏺 {_esc(repo_name)} — Git Archaeologist Report</title>
<style>{_CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def save_html_report(
    output_path: str,
    repo_path: str = ".",
    since: datetime | None = None,
    until: datetime | None = None,
    title: str | None = None,
) -> Path:
    """生成并保存 HTML 报告到文件。"""
    html_content = generate_html_report(repo_path=repo_path, since=since, until=until, title=title)
    out = Path(output_path)
    out.write_text(html_content, encoding="utf-8")
    return out
