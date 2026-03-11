"""Post-evaluation failure analysis for SkillsEval runs.

Reads trial outputs across models, categorizes failures, and generates
bilingual (中文/English) analysis reports with actionable fix suggestions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

from skilleval.models import RunSummary


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TrialDetail:
    """Rich detail for a single trial, including the on-disk output."""

    model: str
    trial_number: int
    passed: bool
    output_text: str
    diff_text: str
    cost: float
    latency: float
    error: str | None
    input_tokens: int
    output_tokens: int


@dataclass
class FailureInstance:
    """A single failed trial with context."""

    model: str
    trial_number: int
    output_text: str
    diff_text: str
    category: str  # "label_precision" | "count_sum_ambiguity" | "format_error" | "api_error"
    explanation: str


@dataclass
class CaseAnalysis:
    """Analysis of one test case across all models."""

    case_name: str
    total_trials: int
    passed_trials: int
    model_pass_rates: dict[str, float]  # model -> pass_rate
    failures: list[FailureInstance]
    difficulty: str  # "easy" | "medium" | "hard"


@dataclass
class AnalysisReport:
    """Complete analysis report across all cases and models."""

    task_name: str
    timestamp: str
    total_models: int
    total_cases: int
    total_trials: int
    cases: list[CaseAnalysis]
    model_rankings: list[dict]  # sorted by pass rate then cost
    failure_taxonomy: dict[str, int]  # category -> count
    insights: list[str]
    fix_suggestions: list[str]


# ---------------------------------------------------------------------------
# Core analysis logic
# ---------------------------------------------------------------------------


def _load_trial_details(run_dir: Path, model: str) -> list[TrialDetail]:
    """Load all trial details for a model from on-disk files."""
    model_dir = run_dir / model
    if not model_dir.is_dir():
        return []

    trials: list[TrialDetail] = []
    for trial_dir in sorted(model_dir.iterdir()):
        if not trial_dir.is_dir() or not trial_dir.name.startswith("trial-"):
            continue

        trial_num = int(trial_dir.name.split("-")[1])

        output_path = trial_dir / "output.txt"
        output_text = output_path.read_text(encoding="utf-8") if output_path.exists() else ""

        diff_path = trial_dir / "diff.txt"
        diff_text = diff_path.read_text(encoding="utf-8") if diff_path.exists() else ""

        meta_path = trial_dir / "meta.json"
        meta: dict = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        trials.append(
            TrialDetail(
                model=model,
                trial_number=trial_num,
                passed=meta.get("passed", False),
                output_text=output_text,
                diff_text=diff_text,
                cost=meta.get("cost", 0.0),
                latency=meta.get("latency", 0.0),
                error=meta.get("error"),
                input_tokens=meta.get("input_tokens", 0),
                output_tokens=meta.get("output_tokens", 0),
            )
        )
    return trials


def _classify_failure(trial: TrialDetail, expected_text: str) -> FailureInstance:
    """Classify a failed trial into a failure category."""
    if trial.error:
        return FailureInstance(
            model=trial.model,
            trial_number=trial.trial_number,
            output_text=trial.output_text[:500],
            diff_text=trial.diff_text[:500],
            category="api_error",
            explanation=f"API error: {trial.error}",
        )

    output = trial.output_text.strip()
    diff = trial.diff_text.strip()

    # Check for count vs sum ambiguity: expected an integer, got a float
    category = "format_error"
    explanation = diff if diff else "Output did not match expected"

    # Heuristic: if diff mentions a numeric mismatch where expected is int and got float
    try:
        expected_json = json.loads(expected_text) if expected_text else {}
        output_json = json.loads(output) if output else {}
        mismatches = _find_field_mismatches(expected_json, output_json)
        if mismatches:
            for field_name, exp_val, got_val in mismatches:
                if isinstance(exp_val, int) and isinstance(got_val, float):
                    category = "count_sum_ambiguity"
                    explanation = (
                        f'Field "{field_name}": expected count {exp_val}, '
                        f"got sum {got_val}. Model interpreted count field as monetary total."
                    )
                    break
                elif isinstance(exp_val, str) and isinstance(got_val, str) and exp_val in got_val:
                    category = "label_precision"
                    explanation = (
                        f'Field "{field_name}": expected "{exp_val}", '
                        f'got "{got_val}". Model added extra context to label.'
                    )
                    break
    except (json.JSONDecodeError, TypeError):
        pass

    return FailureInstance(
        model=trial.model,
        trial_number=trial.trial_number,
        output_text=output[:500],
        diff_text=trial.diff_text[:500],
        category=category,
        explanation=explanation,
    )


def _find_field_mismatches(
    expected: dict | list, actual: dict | list, prefix: str = ""
) -> list[tuple[str, object, object]]:
    """Recursively find mismatched fields between expected and actual JSON."""
    mismatches: list[tuple[str, object, object]] = []

    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, exp_val in expected.items():
            act_val = actual.get(key)
            path = f"{prefix}.{key}" if prefix else key

            if isinstance(exp_val, dict) and isinstance(act_val, dict):
                mismatches.extend(_find_field_mismatches(exp_val, act_val, path))
            elif isinstance(exp_val, list) and isinstance(act_val, list):
                mismatches.extend(_find_field_mismatches(exp_val, act_val, path))
            elif act_val != exp_val:
                mismatches.append((path, exp_val, act_val))

    elif isinstance(expected, list) and isinstance(actual, list):
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            path = f"{prefix}[{i}]"
            if isinstance(exp_item, dict) and isinstance(act_item, dict):
                mismatches.extend(_find_field_mismatches(exp_item, act_item, path))
            elif exp_item != act_item:
                mismatches.append((path, exp_item, act_item))

    return mismatches


def analyze_skill_test(test_cases_dir: Path) -> AnalysisReport:
    """Analyze a skill-test run across multiple test cases.

    Expects: test_cases_dir containing case-N/ subdirs, each with .skilleval/ results.
    """
    test_dir = Path(test_cases_dir)
    case_dirs = sorted(d for d in test_dir.iterdir() if d.is_dir() and d.name.startswith("case-"))

    all_cases: list[CaseAnalysis] = []
    all_models: set[str] = set()
    model_total_pass: dict[str, int] = {}
    model_total_cases: dict[str, int] = {}
    failure_taxonomy: dict[str, int] = {
        "label_precision": 0,
        "count_sum_ambiguity": 0,
        "format_error": 0,
        "api_error": 0,
    }
    total_trials = 0

    for case_dir in case_dirs:
        skilleval_dir = case_dir / ".skilleval"
        if not skilleval_dir.is_dir():
            continue

        # Find the latest run
        runs = sorted(
            (d for d in skilleval_dir.iterdir() if d.name.startswith("run-")),
            reverse=True,
        )
        if not runs:
            continue

        run_dir = runs[0]
        results_file = run_dir / "results.json"
        if not results_file.exists():
            continue

        data = json.loads(results_file.read_text(encoding="utf-8"))
        summary = RunSummary(**data)

        # Load expected text for failure classification
        expected_dir = case_dir / "expected"
        expected_text = ""
        if expected_dir.is_dir():
            for f in sorted(expected_dir.iterdir()):
                if f.is_file():
                    expected_text = f.read_text(encoding="utf-8")
                    break

        model_pass_rates: dict[str, float] = {}
        failures: list[FailureInstance] = []
        case_total = 0
        case_passed = 0

        for mr in summary.model_results:
            all_models.add(mr.model)
            model_pass_rates[mr.model] = mr.pass_rate

            # Track overall pass rates
            if mr.model not in model_total_pass:
                model_total_pass[mr.model] = 0
                model_total_cases[mr.model] = 0
            model_total_cases[mr.model] += 1
            if mr.pass_rate >= 1.0:
                model_total_pass[mr.model] += 1

            # Load on-disk trial details for failed trials
            trial_details = _load_trial_details(run_dir, mr.model)
            for td in trial_details:
                case_total += 1
                total_trials += 1
                if td.passed:
                    case_passed += 1
                else:
                    fi = _classify_failure(td, expected_text)
                    failures.append(fi)
                    failure_taxonomy[fi.category] = failure_taxonomy.get(fi.category, 0) + 1

        # Determine difficulty
        pass_pct = (case_passed / case_total * 100) if case_total > 0 else 0
        if pass_pct >= 80:
            difficulty = "easy"
        elif pass_pct >= 50:
            difficulty = "medium"
        else:
            difficulty = "hard"

        all_cases.append(
            CaseAnalysis(
                case_name=case_dir.name,
                total_trials=case_total,
                passed_trials=case_passed,
                model_pass_rates=model_pass_rates,
                failures=failures,
                difficulty=difficulty,
            )
        )

    # Build model rankings
    model_rankings = []
    for model in sorted(all_models):
        cases_passing = model_total_pass.get(model, 0)
        total = model_total_cases.get(model, 0)
        model_rankings.append(
            {"model": model, "cases_passing": cases_passing, "total_cases": total}
        )
    model_rankings.sort(key=lambda x: (-x["cases_passing"], x["model"]))

    # Generate insights
    insights = _generate_insights(all_cases, failure_taxonomy)
    fix_suggestions = _generate_fix_suggestions(all_cases, failure_taxonomy)

    return AnalysisReport(
        task_name=test_dir.name,
        timestamp="",
        total_models=len(all_models),
        total_cases=len(all_cases),
        total_trials=total_trials,
        cases=all_cases,
        model_rankings=model_rankings,
        failure_taxonomy=failure_taxonomy,
        insights=insights,
        fix_suggestions=fix_suggestions,
    )


def _generate_insights(cases: list[CaseAnalysis], taxonomy: dict[str, int]) -> list[str]:
    """Generate bilingual insights from the analysis."""
    insights: list[str] = []

    total_failures = sum(taxonomy.values())
    if total_failures == 0:
        insights.append("All trials passed across all models / 所有模型的所有试验均通过")
        return insights

    # Dominant failure mode
    top_category = max(taxonomy, key=lambda k: taxonomy[k])
    top_count = taxonomy[top_category]
    pct = top_count / total_failures * 100

    category_names = {
        "label_precision": "Label Over-Explanation / 标签过度解释",
        "count_sum_ambiguity": "Count vs. Sum Confusion / 计数与求和混淆",
        "format_error": "Output Format Mismatch / 输出格式不匹配",
        "api_error": "API Error / API 错误",
    }

    insights.append(
        f"Dominant failure mode: {category_names.get(top_category, top_category)} "
        f"({top_count}/{total_failures} failures, {pct:.0f}%) / "
        f"主要失败模式：{category_names.get(top_category, top_category)} "
        f"（{top_count}/{total_failures} 次失败，{pct:.0f}%）"
    )

    # Hardest case
    hard_cases = [c for c in cases if c.difficulty == "hard"]
    if hard_cases:
        names = ", ".join(c.case_name for c in hard_cases)
        insights.append(f"Hardest test cases: {names} / 最难的测试用例：{names}")

    # Label precision insight
    if taxonomy.get("label_precision", 0) > 0:
        insights.append(
            "Models correctly identify concepts but embellish labels with extra context "
            "(e.g., adding suffix explanations or dollar amounts). "
            "This is a prompt design issue, not a reasoning failure. / "
            "模型正确识别了概念，但在标签中添加了额外上下文"
            "（如后缀说明或金额）。这是提示设计问题，不是推理失败。"
        )

    # Count vs sum insight
    if taxonomy.get("count_sum_ambiguity", 0) > 0:
        insights.append(
            "Fields named 'total' or 'total_X' are interpreted as monetary sums "
            "instead of record counts. In financial contexts, LLMs default to "
            "monetary aggregation. / "
            "名为 'total' 或 'total_X' 的字段被解释为金额之和"
            "而非记录计数。在财务语境中，LLM 默认进行金额聚合。"
        )

    return insights


def _generate_fix_suggestions(cases: list[CaseAnalysis], taxonomy: dict[str, int]) -> list[str]:
    """Generate actionable fix suggestions."""
    suggestions: list[str] = []

    if taxonomy.get("label_precision", 0) > 0:
        suggestions.append(
            'Add explicit format instruction: "Use ONLY the label text, no amounts or '
            'trigger explanations" / '
            '添加明确的格式指令："仅使用标签文本，不要添加金额或触发条件说明"'
        )
        suggestions.append(
            "Include a negative example in the prompt showing what NOT to output / "
            "在提示中包含反面示例，展示不应输出的内容"
        )

    if taxonomy.get("count_sum_ambiguity", 0) > 0:
        suggestions.append(
            'Use unambiguous field names: "total" → "item_count", '
            '"total_surcharges" → "surcharge_count" / '
            '使用无歧义字段名："total" → "item_count"，'
            '"total_surcharges" → "surcharge_count"'
        )

    if taxonomy.get("format_error", 0) > 0:
        suggestions.append(
            "Add an example of the exact expected JSON structure in the prompt / "
            "在提示中添加精确的预期 JSON 结构示例"
        )

    if taxonomy.get("api_error", 0) > 0:
        suggestions.append(
            "Check API keys and rate limits for failing providers / "
            "检查失败供应商的 API 密钥和速率限制"
        )

    return suggestions


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

_DIFFICULTY_LABELS = {"easy": "Easy 简单", "medium": "Medium 中等", "hard": "Hard 困难"}
_CATEGORY_LABELS = {
    "label_precision": "Label Over-Explanation / 标签过度解释",
    "count_sum_ambiguity": "Count vs. Sum Confusion / 计数与求和混淆",
    "format_error": "Output Format Mismatch / 输出格式不匹配",
    "api_error": "API Error / API 错误",
}


def generate_markdown_report(report: AnalysisReport) -> str:
    """Generate a bilingual Markdown analysis report."""
    lines: list[str] = []

    lines.append("# Skill Evaluation Analysis / 技能评估分析")
    lines.append("")
    lines.append(f"> Task 任务: `{report.task_name}`")
    lines.append(
        f"> Models 模型: {report.total_models} | Cases 用例: {report.total_cases} | Trials 试验: {report.total_trials}"
    )
    lines.append("")

    # --- Model Rankings ---
    lines.append("## Model Rankings / 模型排名")
    lines.append("")
    lines.append("| Rank 排名 | Model 模型 | Cases Passing 通过用例 | Score 得分 |")
    lines.append("|:---:|---|:---:|:---:|")
    for i, mr in enumerate(report.model_rankings, 1):
        score = f"{mr['cases_passing']}/{mr['total_cases']}"
        passing = mr["cases_passing"]
        total = mr["total_cases"]
        pct = "100%" if passing == total else f"{passing / total * 100:.0f}%"
        lines.append(f"| {i} | {mr['model']} | {score} | {pct} |")
    lines.append("")

    # --- Heatmap ---
    lines.append("## Pass/Fail Heatmap / 通过率热力图")
    lines.append("")
    models = [mr["model"] for mr in report.model_rankings]
    header = "| Model 模型 | " + " | ".join(c.case_name for c in report.cases) + " |"
    sep = "|---|" + "|".join(":---:" for _ in report.cases) + "|"
    lines.append(header)
    lines.append(sep)
    for model in models:
        cells = []
        for case in report.cases:
            rate = case.model_pass_rates.get(model, 0)
            if rate >= 1.0:
                cells.append("✅ 100%")
            elif rate > 0:
                cells.append(f"⚠️ {rate * 100:.0f}%")
            else:
                cells.append("❌ 0%")
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- Failure Taxonomy ---
    lines.append("## Failure Taxonomy / 失败分类")
    lines.append("")
    total_f = sum(report.failure_taxonomy.values())
    if total_f == 0:
        lines.append("No failures detected / 未检测到失败")
    else:
        lines.append("| Category 类别 | Count 数量 | Percentage 占比 |")
        lines.append("|---|:---:|:---:|")
        for cat, count in sorted(report.failure_taxonomy.items(), key=lambda x: -x[1]):
            if count > 0:
                label = _CATEGORY_LABELS.get(cat, cat)
                lines.append(f"| {label} | {count} | {count / total_f * 100:.0f}% |")
    lines.append("")

    # --- Per-Case Analysis ---
    lines.append("## Case-by-Case Analysis / 逐用例分析")
    lines.append("")
    for case in report.cases:
        diff_label = _DIFFICULTY_LABELS.get(case.difficulty, case.difficulty)
        lines.append(f"### {case.case_name} — {diff_label}")
        lines.append(f"Pass rate 通过率: {case.passed_trials}/{case.total_trials} trials")
        lines.append("")

        if case.failures:
            # Group failures by model
            by_model: dict[str, list[FailureInstance]] = {}
            for fi in case.failures:
                by_model.setdefault(fi.model, []).append(fi)

            lines.append("| Model 模型 | Trial | Category 类别 | Explanation 说明 |")
            lines.append("|---|:---:|---|---|")
            for model, fis in sorted(by_model.items()):
                for fi in fis:
                    cat_label = _CATEGORY_LABELS.get(fi.category, fi.category)
                    expl = fi.explanation.replace("\n", " ").replace("|", "\\|")[:200]
                    lines.append(f"| {model} | {fi.trial_number} | {cat_label} | {expl} |")
            lines.append("")

            # Show sample outputs for failed trials
            lines.append("<details>")
            lines.append(
                f"<summary>Sample failed outputs / 失败输出示例 ({len(case.failures)} failures)</summary>"
            )
            lines.append("")
            shown: set[str] = set()
            for fi in case.failures:
                if fi.model in shown or fi.category == "api_error":
                    continue
                shown.add(fi.model)
                lines.append(f"**{fi.model}** (trial {fi.trial_number}):")
                lines.append("```json")
                lines.append(fi.output_text[:800])
                lines.append("```")
                lines.append("")
            lines.append("</details>")
            lines.append("")
        else:
            lines.append("All trials passed / 所有试验通过 ✅")
            lines.append("")

    # --- Insights ---
    lines.append("## Key Insights / 关键洞察")
    lines.append("")
    for insight in report.insights:
        lines.append(f"- {insight}")
    lines.append("")

    # --- Fix Suggestions ---
    lines.append("## Fix Suggestions / 修复建议")
    lines.append("")
    for i, suggestion in enumerate(report.fix_suggestions, 1):
        lines.append(f"{i}. {suggestion}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by `skilleval analyze` / 由 `skilleval analyze` 生成*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------


def generate_html_analysis(report: AnalysisReport) -> str:
    """Generate a self-contained bilingual HTML analysis report."""
    models = [mr["model"] for mr in report.model_rankings]
    total_f = sum(report.failure_taxonomy.values())

    # Build heatmap rows
    heatmap_rows = []
    for model in models:
        cells = []
        for case in report.cases:
            rate = case.model_pass_rates.get(model, 0)
            if rate >= 1.0:
                cls = "pass"
                text = "100%"
            elif rate > 0:
                cls = "partial"
                text = f"{rate * 100:.0f}%"
            else:
                cls = "fail"
                text = "0%"
            cells.append(f'<td class="{cls}">{text}</td>')
        heatmap_rows.append(f"<tr><td>{escape(model)}</td>{''.join(cells)}</tr>")

    # Build ranking rows
    ranking_rows = []
    for i, mr in enumerate(report.model_rankings, 1):
        score = f"{mr['cases_passing']}/{mr['total_cases']}"
        cls = (
            "pass"
            if mr["cases_passing"] == mr["total_cases"]
            else ("partial" if mr["cases_passing"] > 0 else "fail")
        )
        ranking_rows.append(
            f'<tr><td>{i}</td><td>{escape(mr["model"])}</td><td class="{cls}">{score}</td></tr>'
        )

    # Build taxonomy rows
    taxonomy_rows = []
    for cat, count in sorted(report.failure_taxonomy.items(), key=lambda x: -x[1]):
        if count > 0:
            label = escape(_CATEGORY_LABELS.get(cat, cat))
            pct = count / total_f * 100 if total_f > 0 else 0
            taxonomy_rows.append(f"<tr><td>{label}</td><td>{count}</td><td>{pct:.0f}%</td></tr>")

    # Build case detail sections
    case_sections = []
    for case in report.cases:
        diff_label = _DIFFICULTY_LABELS.get(case.difficulty, case.difficulty)
        failure_rows = []
        sample_outputs = []
        shown: set[str] = set()

        for fi in case.failures:
            cat_label = escape(_CATEGORY_LABELS.get(fi.category, fi.category))
            expl = escape(fi.explanation[:200])
            failure_rows.append(
                f"<tr><td>{escape(fi.model)}</td><td>{fi.trial_number}</td>"
                f"<td>{cat_label}</td><td>{expl}</td></tr>"
            )
            if fi.model not in shown and fi.category != "api_error":
                shown.add(fi.model)
                sample_outputs.append(
                    f"<h4>{escape(fi.model)} (trial {fi.trial_number})</h4>"
                    f"<pre>{escape(fi.output_text[:800])}</pre>"
                )

        if failure_rows:
            table = (
                "<table><tr><th>Model 模型</th><th>Trial</th>"
                "<th>Category 类别</th><th>Explanation 说明</th></tr>"
                + "\n".join(failure_rows)
                + "</table>"
            )
            samples_html = (
                (
                    f"<details><summary>Sample outputs / 失败输出示例 ({len(case.failures)})</summary>"
                    + "\n".join(sample_outputs)
                    + "</details>"
                )
                if sample_outputs
                else ""
            )
        else:
            table = '<p class="pass">All trials passed / 所有试验通过 ✅</p>'
            samples_html = ""

        case_sections.append(f"""
        <div class="card">
          <h3>{escape(case.case_name)} — {escape(diff_label)}</h3>
          <p class="meta">Pass rate 通过率: {case.passed_trials}/{case.total_trials} trials</p>
          {table}
          {samples_html}
        </div>
        """)

    # Build insights list
    insights_html = "\n".join(f"<li>{escape(i)}</li>" for i in report.insights)
    suggestions_html = "\n".join(f"<li>{escape(s)}</li>" for s in report.fix_suggestions)

    case_headers = "".join(f"<th>{escape(c.case_name)}</th>" for c in report.cases)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SkillsEval Analysis / 技能评估分析 — {escape(report.task_name)}</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --border: #334155; --text: #e2e8f0;
           --muted: #94a3b8; --green: #22c55e; --red: #ef4444; --yellow: #eab308;
           --blue: #3b82f6; --purple: #a855f7; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'SF Mono','Fira Code',monospace; background: var(--bg);
          color: var(--text); padding: 2rem; max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.15rem; margin: 1.5rem 0 0.75rem; color: var(--blue); }}
  h3 {{ font-size: 0.95rem; margin-bottom: 0.5rem; }}
  h4 {{ font-size: 0.85rem; color: var(--muted); margin: 0.5rem 0 0.25rem; }}
  .subtitle {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 1.5rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border);
           border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }}
  .meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 0.5rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; margin-bottom: 0.75rem; }}
  th, td {{ padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; }}
  .pass {{ color: var(--green); font-weight: 700; }}
  .fail {{ color: var(--red); font-weight: 700; }}
  .partial {{ color: var(--yellow); font-weight: 700; }}
  pre {{ background: #0b0c10; padding: 0.75rem; border-radius: 4px; overflow-x: auto;
         font-size: 0.75rem; margin: 0.5rem 0; white-space: pre-wrap; word-break: break-all; }}
  details {{ margin: 0.5rem 0; }}
  summary {{ cursor: pointer; color: var(--blue); font-size: 0.8rem; }}
  ul, ol {{ padding-left: 1.5rem; margin: 0.5rem 0; }}
  li {{ margin: 0.4rem 0; font-size: 0.85rem; line-height: 1.5; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }}
  .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
           padding: 1rem; text-align: center; }}
  .stat .value {{ font-size: 1.75rem; font-weight: 700; }}
  .stat .label {{ color: var(--muted); font-size: 0.7rem; margin-top: 0.25rem; }}
  .verdict {{ background: linear-gradient(135deg, #1e1b4b, #312e81); border: 1px solid #6366f1;
              border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; }}
  .verdict h2 {{ color: #a5b4fc; margin: 0 0 0.5rem; }}
  footer {{ margin-top: 2rem; color: var(--muted); font-size: 0.7rem; text-align: center; }}
</style>
</head>
<body>

<h1>SkillsEval Analysis / 技能评估分析</h1>
<p class="subtitle">Task 任务: {escape(report.task_name)} · {report.total_models} models · {report.total_cases} cases · {report.total_trials} trials</p>

<div class="grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 1.5rem;">
  <div class="stat"><div class="value">{report.total_models}</div><div class="label">Models 模型</div></div>
  <div class="stat"><div class="value">{report.total_cases}</div><div class="label">Test Cases 测试用例</div></div>
  <div class="stat"><div class="value">{report.total_trials}</div><div class="label">Total Trials 总试验数</div></div>
  <div class="stat"><div class="value" style="color: var(--red)">{total_f}</div><div class="label">Failures 失败数</div></div>
</div>

<div class="verdict">
  <h2>Key Insights / 关键洞察</h2>
  <ul>
    {insights_html}
  </ul>
</div>

<h2>Model Rankings / 模型排名</h2>
<div class="card">
  <table>
    <tr><th>Rank 排名</th><th>Model 模型</th><th>Cases Passing 通过用例</th></tr>
    {"".join(ranking_rows)}
  </table>
</div>

<h2>Pass/Fail Heatmap / 通过率热力图</h2>
<div class="card">
  <table>
    <tr><th>Model 模型</th>{case_headers}</tr>
    {"".join(heatmap_rows)}
  </table>
</div>

<h2>Failure Taxonomy / 失败分类</h2>
<div class="card">
  <table>
    <tr><th>Category 类别</th><th>Count 数量</th><th>Percentage 占比</th></tr>
    {"".join(taxonomy_rows)}
  </table>
</div>

<h2>Case-by-Case Analysis / 逐用例分析</h2>
{"".join(case_sections)}

<h2>Fix Suggestions / 修复建议</h2>
<div class="card">
  <ol>
    {suggestions_html}
  </ol>
</div>

<footer>Generated by <code>skilleval analyze</code> · SkillsEval</footer>

</body>
</html>"""
