from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a reproducible evaluation set from a cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing test-set columns: {sorted(missing_columns)}")
    if df.empty:
        raise ValueError("Cannot build an evaluation set from an empty dataframe.")

    candidates = df.copy()
    candidates = candidates[
        candidates["paper_id"].fillna("").astype(str).str.strip().ne("")
        & candidates["title"].fillna("").astype(str).str.strip().ne("")
    ]
    if candidates.empty:
        raise ValueError("No cleaned documents have both paper_id and title.")

    selected = candidates.head(min(6, len(candidates)))
    samples: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(selected.iterrows(), start=1):
        paper_id = str(row["paper_id"]).strip()
        title = str(row["title"]).strip().replace("'", "’")
        question_specs = [
            ("summary", f"What is '{title}' about?", first_sentence(str(row["summary"]))),
            ("authors", f"Who authored '{title}'?", str(row["authors_joined"]).strip()),
            ("date", f"When was '{title}' published?", str(row["published"]).strip()),
            (
                "categories",
                f"What categories are associated with '{title}'?",
                str(row["categories_joined"]).strip(),
            ),
        ]
        for question_type, question, ground_truth in question_specs:
            if not ground_truth or ground_truth.lower() == "nan":
                continue
            samples.append(
                {
                    "id": f"{question_type}-{position:03d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not samples:
        raise ValueError("No valid evaluation samples could be generated.")
    write_json(output_path, samples)
    return samples
