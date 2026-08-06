# Baseline Pipeline Report

## Source and dataset

| Field | Value |
|---|---|
| `source` | Crossref REST API |
| `query` | agentic retrieval augmented generation large language model |
| `filter` | from-pub-date:2026-02-07,has-abstract:true |
| `raw_records` | 24 |
| `clean_records` | 24 |
| `run_date_utc` | 2026-08-06T10:20:10.383406+00:00 |
| `embedding_model` | sentence-transformers/all-MiniLM-L6-v2 |
| `collection_name` | papers-baseline |

## Evaluation metrics

| Metric | Baseline |
|---|---:|
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`

## Data quality

Overall status: **PASS**

| Check | Status | Value | Expected |
|---|---|---|---|
| `required_columns_present` | PASS | [] | no required columns missing |
| `row_count_positive` | PASS | 24 | row_count > 0 |
| `paper_id_complete` | PASS | 0 | missing == 0 |
| `paper_id_unique` | PASS | 0 | duplicates == 0 |
| `title_complete` | PASS | 0 | missing == 0 |
| `summary_complete` | PASS | 0 | missing == 0 |
| `text_for_embedding_complete` | PASS | 0 | missing == 0 |
| `age_days_valid` | PASS | 0 | invalid == 0 |

## Freshness

| Signal | Value |
|---|---|
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `latest_age_days` | 5 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `threshold_days` | 180 |
| `is_fresh` | True |
| `status` | fresh |
