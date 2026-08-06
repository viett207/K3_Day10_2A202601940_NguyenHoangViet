from __future__ import annotations

from typing import Any

from core.utils import write_text


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "N/A"
    return str(value)


def _metric_table(states: list[tuple[str, dict[str, Any]]]) -> list[str]:
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    lines = [
        "| Metric | " + " | ".join(name for name, _ in states) + " |",
        "|---|" + "---:|" * len(states),
    ]
    for metric in metric_names:
        lines.append(
            f"| `{metric}` | "
            + " | ".join(_format_value(metrics.get(metric)) for _, metrics in states)
            + " |"
        )
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline pipeline report as Markdown.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines = [
        "# Baseline Pipeline Report",
        "",
        "## Source and dataset",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for key, value in source_summary.items():
        lines.append(f"| `{key}` | {_format_value(value)} |")
    lines.extend(["", "## Evaluation metrics", ""])
    lines.extend(_metric_table([("Baseline", metrics)]))
    lines.extend(
        [
            "",
            f"Ragas: `{_format_value(metrics.get('ragas'))}`",
            "",
            "## Data quality",
            "",
            f"Overall status: **{'PASS' if quality.get('passed') else 'FAIL'}**",
            "",
            "| Check | Status | Value | Expected |",
            "|---|---|---|---|",
        ]
    )
    for check in quality.get("checks", []):
        lines.append(
            f"| `{check.get('name')}` | {'PASS' if check.get('passed') else 'FAIL'} | "
            f"{_format_value(check.get('value'))} | {_format_value(check.get('expected'))} |"
        )
    lines.extend(
        [
            "",
            "## Freshness",
            "",
            "| Signal | Value |",
            "|---|---|",
        ]
    )
    for key, value in freshness.items():
        lines.append(f"| `{key}` | {_format_value(value)} |")
    lines.append("")
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the baseline/corrupted/repaired comparison report."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    lines = [
        "# Corruption and Repair Comparison",
        "",
        "## Evaluation metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for metric in metric_names:
        baseline = baseline_metrics.get(metric)
        corrupted = corrupted_metrics.get(metric)
        repaired = repaired_metrics.get(metric)
        corruption_delta = corrupted - baseline if isinstance(corrupted, (int, float)) and isinstance(baseline, (int, float)) else None
        recovery_delta = repaired - corrupted if isinstance(repaired, (int, float)) and isinstance(corrupted, (int, float)) else None
        lines.append(
            f"| `{metric}` | {_format_value(baseline)} | {_format_value(corrupted)} | "
            f"{_format_value(repaired)} | {_format_value(corruption_delta)} | {_format_value(recovery_delta)} |"
        )

    lines.extend(
        [
            "",
            "## Data quality and freshness",
            "",
            "| State | Quality | Failed checks | Freshness | Stale rows |",
            "|---|---|---:|---|---:|",
        ]
    )
    for name, quality, freshness in [
        ("Corrupted", corrupted_quality, corrupted_freshness),
        ("Repaired", repaired_quality, repaired_freshness),
    ]:
        failed_checks = sum(not check.get("passed", False) for check in quality.get("checks", []))
        lines.append(
            f"| {name} | {'PASS' if quality.get('passed') else 'FAIL'} | {failed_checks} | "
            f"{_format_value(freshness.get('status'))} | {_format_value(freshness.get('stale_rows'))} |"
        )

    lines.extend(["", "## Evidence-based observations", ""])
    for metric in metric_names:
        baseline = baseline_metrics.get(metric)
        corrupted = corrupted_metrics.get(metric)
        repaired = repaired_metrics.get(metric)
        if all(isinstance(value, (int, float)) for value in (baseline, corrupted, repaired)):
            if corrupted < baseline:
                recovery = "recovered" if repaired >= baseline else "partially recovered" if repaired > corrupted else "did not recover"
                lines.append(
                    f"- `{metric}` decreased by {baseline - corrupted:.4f} after corruption and {recovery} after repair."
                )
            else:
                lines.append(f"- `{metric}` did not decrease after the configured corruption scenario.")
    lines.extend(
        [
            "",
            "> Interpret metric changes together with the corruption log, answer artifacts, and quality signals. "
            "A correlation in this small evaluation set is evidence for this run, not a universal causal claim.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))
