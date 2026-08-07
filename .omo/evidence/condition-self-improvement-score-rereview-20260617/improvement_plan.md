# Improvement Plan - 2026-06-17 Rereview

## Current Score Change
| Metric | 2026-06-15 | 2026-06-17 | Delta |
|---|---:|---:|---:|
| Overall completion | 56% | 68% | +12%p |
| Overall gap | 44% | 32% | -12%p |
| OOS pass count for new candidate | 0 | 0 | 0 |
| Best train-gate anchor mutation | none | +13,928,386 / MDD 9.62 | new |

## What Improved
| Area | Improvement | Evidence |
|---|---|---|
| Gate calibration | Champion positive controls pass 4/4. | `champion_diag_discovery.log` |
| Generation bottleneck diagnosis | Data ceiling ruled out; cold LLM generation identified as weak link. | `2026-06-16_champion_positive_control_diagnostic.md` |
| Mutation/autonomy | LLM-free anchor mutation hill-climb exists and produced 399 train-gate passers. | `overnight_anchor_mutation.py`, `ovn_anchor_summary.json` |
| Buy feedback | Feature-importance prefer feedback added and tested. | `feature_importance_feedback.py`, `test_feedback_toggles_on.py` |
| Sell feedback | Exit regret and false-break forensics added and tested. | `analyze.py`, `test_p5_exit_forensics.py` |
| Dashboard/runbook | Process/runbook/time-profit/run-log observability improved. | `AGENT_RESUME_RUNBOOK.md`, `dashboard/app.py` |

## What Still Blocks Completion
| Rank | Blocker | Current Number | Required Fix |
|---:|---|---:|---|
| 1 | OOS proof missing | OOS pass count = 0 | Run frozen OOS for +13.93M anchor champion. |
| 2 | Evidence drift | `ovn_t2late_summary.json` says best null, jsonl shows +10.58M | Repair summary writer and canonical run summary. |
| 3 | Typed action ledger missing | prompt hints/actions not canonicalized | Add action_id/source_metric/scope/expiry/validation_result. |
| 4 | Multi-start incomplete | seed and t2late explored; exit2/r2full pending | Queue and compare all start points before final OOS. |
| 5 | Promotion workflow incomplete | train-gate best not moved through OOS/promote/reject | Build OOS result and promotion decision artifact. |

## Revised Priority
| Phase | Priority | Work | Completion Signal |
|---|---:|---|---|
| P0 | 1 | OOS validation of `r8_4_strength_max=250` anchor champion | OOS pass/fail recorded with config and artifact paths |
| P1 | 2 | Evidence summary repair | `ovn_*_summary.json` matches jsonl canonical best |
| P2 | 3 | Multi-start queue completion | seed, t2late, r2full, exit2 compared in one table |
| P3 | 4 | Typed feedback/action ledger | Buy/sell/mutation hints become action records |
| P4 | 5 | End-to-end OOS workflow | mutation -> train gate -> OOS -> promote/reject managed |
| P5 | 6 | Dashboard/runbook panel | Shows champion, OOS status, summary drift, next action |

## Recommended Next Start-Work
| Candidate | Why |
|---|---|
| `$start-work condition-self-improvement-oos-validation-20260617` | Most important: moves proof from train-gate progress to real OOS success/failure. |
| `$start-work condition-self-improvement-evidence-summary-repair-20260617` | Needed if OOS waits; fixes summary drift and improves research management. |
