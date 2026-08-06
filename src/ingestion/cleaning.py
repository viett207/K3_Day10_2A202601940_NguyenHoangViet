from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title or not summary:
            continue

        published_timestamp = pd.to_datetime(record.published, errors="coerce", utc=True)
        if pd.isna(published_timestamp):
            continue
        published = published_timestamp.date().isoformat()
        age_days = max(0, int((run_timestamp - published_timestamp).days))

        authors = list(dict.fromkeys(
            normalized
            for value in record.authors
            if (normalized := normalize_whitespace(str(value)))
        ))
        categories = list(dict.fromkeys(
            normalized
            for value in record.categories
            if (normalized := normalize_whitespace(str(value)))
        ))
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        text_for_embedding = "\n".join(
            part
            for part in [
                f"Title: {title}",
                f"Summary: {summary}",
                f"Authors: {authors_joined}" if authors_joined else "",
                f"Categories: {categories_joined}" if categories_joined else "",
                f"Published: {published}",
            ]
            if part
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category)
                or (categories[0] if categories else ""),
                "published": published,
                "updated": normalize_whitespace(record.updated),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        raise ValueError("No valid records remained after cleaning.")
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True])
    return df.reset_index(drop=True)
