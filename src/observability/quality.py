from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _nonempty_mask(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data-quality checks and persist their structured results.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "text_for_embedding",
        "published",
        "age_days",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    total_rows = len(df)

    def missing_count(column: str) -> int:
        if column not in df.columns:
            return total_rows
        return int((~_nonempty_mask(df[column])).sum())

    duplicate_ids = (
        int(df.loc[_nonempty_mask(df["paper_id"]), "paper_id"].astype(str).str.lower().duplicated().sum())
        if "paper_id" in df.columns
        else total_rows
    )
    invalid_age_rows = 0
    stale_rows = 0
    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        invalid_age_rows = int((ages.isna() | (ages < 0)).sum())
        stale_rows = int((ages > settings.freshness_threshold_days).sum())
    else:
        invalid_age_rows = total_rows

    check_specs = [
        ("required_columns_present", not missing_columns, missing_columns, "no required columns missing"),
        ("row_count_positive", total_rows > 0, total_rows, "row_count > 0"),
        ("paper_id_complete", missing_count("paper_id") == 0, missing_count("paper_id"), "missing == 0"),
        ("paper_id_unique", duplicate_ids == 0, duplicate_ids, "duplicates == 0"),
        ("title_complete", missing_count("title") == 0, missing_count("title"), "missing == 0"),
        ("summary_complete", missing_count("summary") == 0, missing_count("summary"), "missing == 0"),
        (
            "text_for_embedding_complete",
            missing_count("text_for_embedding") == 0,
            missing_count("text_for_embedding"),
            "missing == 0",
        ),
        ("age_days_valid", invalid_age_rows == 0, invalid_age_rows, "invalid == 0"),
    ]
    checks = [
        {"name": name, "passed": bool(passed), "value": value, "expected": expected}
        for name, passed, value, expected in check_specs
    ]
    payload = {
        "report_name": report_name,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    output_path = settings.paths.quality_dir / f"{report_name}_quality.json"
    write_json(output_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize dataset freshness and persist the report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    if "published" not in df.columns or "age_days" not in df.columns:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "latest_age_days": None,
            "stale_rows": len(df),
            "total_rows": len(df),
            "threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
            "status": "unknown",
        }
        write_json(report_path, payload)
        return payload

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    valid_published = published.dropna()
    valid_ages = ages.dropna()
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    latest_age_days = int(valid_ages.min()) if not valid_ages.empty else None
    is_fresh = latest_age_days is not None and latest_age_days <= settings.freshness_threshold_days
    payload = {
        "latest_published": valid_published.max().date().isoformat() if not valid_published.empty else None,
        "oldest_published": valid_published.min().date().isoformat() if not valid_published.empty else None,
        "latest_age_days": latest_age_days,
        "stale_rows": stale_rows,
        "total_rows": len(df),
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(is_fresh),
        "status": "fresh" if is_fresh else "stale" if latest_age_days is not None else "unknown",
    }
    write_json(report_path, payload)
    return payload
