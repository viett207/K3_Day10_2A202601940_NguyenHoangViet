# Corruption and Repair Comparison

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery delta |
|---|---:|---:|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 0.6667 | 1.0000 | -0.3333 | 0.3333 |
| `mean_token_f1` | 1.0000 | 0.5712 | 1.0000 | -0.4288 | 0.4288 |
| `judge_accuracy` | 1.0000 | 0.5556 | 1.0000 | -0.4444 | 0.4444 |
| `mean_judge_score` | 5 | 3.2222 | 5 | -1.7778 | 1.7778 |

## Data quality and freshness

| State | Quality | Failed checks | Freshness | Stale rows |
|---|---|---:|---|---:|
| Corrupted | FAIL | 2 | fresh | 1 |
| Repaired | PASS | 0 | fresh | 0 |

## Evidence-based observations

- `retrieval_hit_rate` decreased by 0.3333 after corruption and recovered after repair.
- `mean_token_f1` decreased by 0.4288 after corruption and recovered after repair.
- `judge_accuracy` decreased by 0.4444 after corruption and recovered after repair.
- `mean_judge_score` decreased by 1.7778 after corruption and recovered after repair.

> Interpret metric changes together with the corruption log, answer artifacts, and quality signals. A correlation in this small evaluation set is evidence for this run, not a universal causal claim.
