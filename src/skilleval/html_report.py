"""HTML report generation for SkillEval results.

This module renders self-contained HTML (inline CSS/JS) for different run modes:
- run: per-model bars, cost table, trial details
- matrix: creator x executor heatmap, best pair
- chain: grouped by meta-skill, variant comparison
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

from skilleval.models import ChainCell, MatrixCell, ModelResult, RunSummary


def generate_html_report(summary: RunSummary, output_path: Path) -> Path:
    """Generate a self-contained HTML report for a run summary.

    Args:
        summary: The complete run summary to render.
        output_path: Where to write the resulting HTML file.

    Returns:
        The path to the generated HTML file.
    """
    html = _render_full_html(summary)
    out = Path(output_path)
    out.write_text(html, encoding="utf-8")
    return out


# ── Rendering helpers ─────────────────────────────────────────────────────


def _render_full_html(summary: RunSummary) -> str:
    body_sections: list[str] = []

    body_sections.append(_render_header(summary))

    mode = summary.mode.lower()
    if mode == "run":
        body_sections.append(_render_run_mode(summary.model_results, summary.recommendation))
    elif mode == "matrix":
        body_sections.append(_render_matrix_mode(summary.matrix_results))
    elif mode == "chain":
        body_sections.append(_render_chain_mode(summary.chain_results))
    else:
        body_sections.append(
            f"<p class=warning>Unknown mode: {escape(summary.mode)}. Nothing to render.</p>"
        )

    body_html = "\n".join(body_sections)

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SkillEval Report</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --panel: #111317;
      --text: #e6edf3;
      --muted: #9aa7b2;
      --green: #1f883d;
      --red: #d1242f;
      --yellow: #d29922;
      --soft-green: #d1e7dd;
      --soft-red: #f8d7da;
      --soft-yellow: #fff3cd;
      --border: #22262c;
      --accent: #3b82f6;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text); }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Inter, Arial, 
                   Noto Sans, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif; }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}

    header.report-header {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }}
    header.report-header h1 {{ font-size: 22px; margin: 0 0 6px; }}
    header.report-header .meta {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; color: var(--muted); }}
    header.report-header .meta span {{ background: #0e1116; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border); }}
    header.report-header .rec {{ margin-top: 10px; color: var(--soft-yellow); }}

    section {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; margin-bottom: 20px; }}
    section h2 {{ font-size: 18px; margin: 0 0 12px; }}
    .warning {{ color: var(--soft-yellow); }}

    /* Bars */
    .bar {{ height: 14px; background: #1f2937; border-radius: 7px; overflow: hidden; }}
    .bar .fill {{ height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b 50%, #22c55e); }}
    .bar .fill.green {{ background: #22c55e; }}
    .bar .fill.yellow {{ background: #f59e0b; }}
    .bar .fill.red {{ background: #ef4444; }}
    .bar-label {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-top: 6px; }}

    /* Tables */
    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ text-align: left; font-weight: 600; color: var(--muted); font-size: 13px; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    tbody tr:hover td {{ background: #0e1116; }}
    td.num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}

    /* Details */
    details {{ border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin: 10px 0; background: #0e1116; }}
    details summary {{ cursor: pointer; user-select: none; outline: none; }}
    details[open] summary {{ color: var(--accent); }}
    .badge {{ display: inline-block; padding: 2px 6px; border-radius: 999px; font-size: 12px; color: #0b0c10; margin-left: 8px; }}
    .badge.pass {{ background: var(--soft-green); }}
    .badge.fail {{ background: var(--soft-red); }}
    .badge.partial {{ background: var(--soft-yellow); }}

    /* Heatmap */
    .heatmap table {{ table-layout: fixed; }}
    .heatmap td, .heatmap th {{ text-align: center; }}
    .heatmap .cell {{ border-radius: 6px; border: 1px solid var(--border); padding: 6px 4px; }}
    .heatmap .best {{ outline: 2px solid var(--accent); outline-offset: 0; }}

    /* Responsive */
    @media (max-width: 640px) {{
      .container {{ padding: 12px; }}
      header.report-header h1 {{ font-size: 18px; }}
      section h2 {{ font-size: 16px; }}
      th, td {{ padding: 6px 8px; }}
    }}
  </style>
  <script>
  // Minimal helper to toggle all <details>
  function toggleAll(open) {{
    document.querySelectorAll('details').forEach(d => d.open = open);
  }}
  </script>
</head>
<body>
  <div class="container">
    {body_html}
  </div>
</body>
</html>
"""


def _render_header(summary: RunSummary) -> str:
    rec_html = (
        f"<div class=rec><strong>Recommendation:</strong> {escape(summary.recommendation)}</div>"
        if summary.recommendation
        else ""
    )
    return (
        "<header class=report-header>"
        "<h1>SkillEval Report</h1>"
        "<div class=meta>"
        f"<span><strong>Task:</strong> {escape(summary.task_path)}</span>"
        f"<span><strong>Timestamp:</strong> {escape(summary.timestamp)}</span>"
        f"<span><strong>Mode:</strong> {escape(summary.mode)}</span>"
        "</div>"
        f"{rec_html}"
        "</header>"
    )


# ── Mode: run ────────────────────────────────────────────────────────────


def _render_run_mode(results: list[ModelResult], recommendation: str | None) -> str:
    if not results:
        return "<section><h2>Run Results</h2><p class=warning>No results.</p></section>"

    parts: list[str] = ["<section>", "<h2>Run Results</h2>"]

    # Bar chart of pass rates per model (CSS bars)
    parts.append("<div>")
    for r in sorted(results, key=lambda x: (-x.pass_rate, x.avg_cost, x.model)):
        width_pct = max(0.0, min(100.0, r.pass_rate * 100.0))
        label = f"{r.model} — {r.pass_rate * 100:.0f}%"
        cls = "green" if r.pass_rate == 1.0 else "yellow" if r.pass_rate >= 0.8 else "red"
        badge = (
            '<span class="badge pass">100%</span>'
            if r.pass_rate == 1.0
            else '<span class="badge partial">80%+</span>'
            if r.pass_rate >= 0.8
            else '<span class="badge fail">&lt;80%</span>'
        )
        parts.append(
            '<div style="margin:10px 0;">'
            f'<div class="bar"><div class="fill {cls}" style="width:{width_pct:.0f}%;"></div></div>'
            f'<div class="bar-label"><span>{escape(label)}</span>'
            f"<span>${r.avg_cost:.6f}/run{badge}</span></div>"
            "</div>"
        )
    parts.append("</div>")

    # Cost comparison table
    parts.append('<h3 style="margin-top:16px;">Cost Comparison</h3>')
    parts.append('<div style="overflow:auto;">')
    parts.append(
        "<table>"
        "<thead><tr>"
        '<th>Model</th><th>Pass Rate</th><th class="num">Avg Cost</th>'
        '<th class="num">Avg Latency</th><th class="num">Total Cost</th>'
        "</tr></thead><tbody>"
    )
    for r in results:
        parts.append(
            "<tr>"
            f"<td>{escape(r.model)}</td>"
            f"<td>{r.pass_rate * 100:.0f}%</td>"
            f'<td class="num">${r.avg_cost:.6f}</td>'
            f'<td class="num">{r.avg_latency:.2f}s</td>'
            f'<td class="num">${r.total_cost:.6f}</td>'
            "</tr>"
        )
    parts.append("</tbody></table></div>")

    # Per-model trial details (collapsible)
    parts.append(
        '<div style="display:flex; gap:8px; margin:12px 0 6px;">'
        '<button onclick="toggleAll(true)">Expand all</button>'
        '<button onclick="toggleAll(false)">Collapse all</button>'
        "</div>"
    )
    parts.append("<h3>Per-Model Trials</h3>")
    for r in results:
        parts.append(_render_trials_block(r))

    parts.append("</section>")
    return "".join(parts)


def _render_trials_block(r: ModelResult) -> str:
    header = (
        f"{escape(r.model)} — {r.pass_rate * 100:.0f}% | "
        f"avg ${r.avg_cost:.6f}/run, {r.avg_latency:.2f}s avg latency, "
        f"${r.total_cost:.6f} total"
    )
    rows = [
        "<table>",
        "<thead><tr><th>#</th><th>Status</th><th>Cost</th><th>Latency</th><th>Output</th><th>Error</th></tr></thead>",
        "<tbody>",
    ]
    for t in r.trials:
        status = "PASS" if t.passed else "FAIL"
        status_color = "var(--soft-green)" if t.passed else "var(--soft-red)"
        output_snippet = escape((t.output_text or "").strip())
        if len(output_snippet) > 120:
            output_snippet = output_snippet[:117] + "…"
        rows.append(
            "<tr>"
            f'<td class="num">{t.trial_number}</td>'
            f'<td><span class="badge" style="background:{status_color}">{status}</span></td>'
            f'<td class="num">${t.cost:.6f}</td>'
            f'<td class="num">{t.latency_seconds:.2f}s</td>'
            f'<td style="max-width:420px; overflow:hidden; text-overflow:ellipsis;">{output_snippet}</td>'
            f"<td>{escape(t.error) if t.error else ''}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    inner = "".join(rows)
    return f"<details><summary>{header}</summary>{inner}</details>"


# ── Mode: matrix ─────────────────────────────────────────────────────────


def _render_matrix_mode(cells: list[MatrixCell]) -> str:
    if not cells:
        return "<section><h2>Creator × Executor Heatmap</h2><p class=warning>No data.</p></section>"

    creators = sorted({c.creator for c in cells})
    executors = sorted({c.executor for c in cells})
    lookup: dict[tuple[str, str], MatrixCell] = {(c.creator, c.executor): c for c in cells}

    best = max(cells, key=lambda c: (c.result.pass_rate, -c.result.avg_cost))

    parts: list[str] = ["<section class=heatmap>", "<h2>Creator × Executor Heatmap</h2>"]
    parts.append(
        f"<p><strong>Best Pair:</strong> {escape(best.creator)} → {escape(best.executor)} "
        f"({best.result.pass_rate * 100:.0f}% @ ${best.result.avg_cost:.6f}/run)</p>"
    )

    parts.append('<div style="overflow:auto;"><table>')
    # Header row
    parts.append("<thead><tr><th>Creator \\ Executor</th>")
    for ex in executors:
        parts.append(f"<th>{escape(ex)}</th>")
    parts.append("</tr></thead><tbody>")

    for cr in creators:
        parts.append(f"<tr><th>{escape(cr)}</th>")
        for ex in executors:
            cell = lookup.get((cr, ex))
            if cell is None:
                parts.append("<td>-</td>")
                continue
            rate = cell.result.pass_rate
            pct = f"{rate * 100:.0f}%"
            hue = int(rate * 120)  # 0 -> red, 60 -> yellow, 120 -> green
            # Soft, readable background color using HSL
            bg = f"hsl({hue}, 65%, 85%)"
            is_best = cr == best.creator and ex == best.executor
            cls = "cell best" if is_best else "cell"
            parts.append(
                f'<td data-creator="{escape(cr)}" data-executor="{escape(ex)}">'
                f'<div class="{cls}" style="background:{bg}">{pct}</div>'
                "</td>"
            )
        parts.append("</tr>")

    parts.append("</tbody></table></div>")
    parts.append("</section>")
    return "".join(parts)


# ── Mode: chain ──────────────────────────────────────────────────────────


def _render_chain_mode(cells: list[ChainCell]) -> str:
    if not cells:
        return "<section><h2>Chain Results</h2><p class=warning>No data.</p></section>"

    parts: list[str] = ["<section>", "<h2>Chain Results</h2>"]

    # Variant comparison across meta-skill names (average pass rate)
    by_meta: dict[str, list[ChainCell]] = {}
    for c in cells:
        by_meta.setdefault(c.meta_skill_name, []).append(c)

    parts.append("<h3>Pass Rate by Variant</h3>")
    for meta, items in sorted(by_meta.items()):
        avg = _avg([i.result.pass_rate for i in items])
        width_pct = max(0.0, min(100.0, avg * 100.0))
        cls = "green" if avg == 1.0 else "yellow" if avg >= 0.8 else "red"
        parts.append(
            '<div style="margin:10px 0;">'
            f'<div class="bar"><div class="fill {cls}" style="width:{width_pct:.0f}%;"></div></div>'
            f'<div class="bar-label"><span>{escape(meta)}</span>'
            f"<span>{avg * 100:.1f}% avg</span></div>"
            "</div>"
        )

    # Grouped results by meta-skill variant
    parts.append('<h3 style="margin-top:16px;">Variant Details</h3>')
    for meta, items in sorted(by_meta.items()):
        parts.append(f"<details><summary>{escape(meta)}</summary>")
        parts.append("<table>")
        parts.append(
            "<thead><tr><th>Creator</th><th>Executor</th><th>Pass Rate</th>"
            '<th class="num">Avg Cost</th><th class="num">Avg Latency</th></tr></thead><tbody>'
        )
        for c in items:
            r = c.result
            parts.append(
                "<tr>"
                f"<td>{escape(c.creator)}</td>"
                f"<td>{escape(c.executor)}</td>"
                f"<td>{r.pass_rate * 100:.0f}%</td>"
                f'<td class="num">${r.avg_cost:.6f}</td>'
                f'<td class="num">{r.avg_latency:.2f}s</td>'
                "</tr>"
            )
        parts.append("</tbody></table>")
        parts.append("</details>")

    parts.append("</section>")
    return "".join(parts)


# ── Utilities ────────────────────────────────────────────────────────────


def _avg(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0
