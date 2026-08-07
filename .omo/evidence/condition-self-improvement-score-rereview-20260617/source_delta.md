# Source Delta - Condition Self-Improvement Score Rereview (2026-06-17)

## Baseline
| Baseline Report | Previous Score | Previous Gap |
|---|---:|---:|
| `docs/update_log/2026-06-15_condition_self_improvement_process_report.md` | 56% | 44% |

## New Evidence Since 2026-06-15
| Source | New Finding | Score Impact |
|---|---|---|
| `docs/update_log/2026-06-16_champion_positive_control_diagnostic.md` | Verified champions 4/4 passed discovery gate with +9.55M to +10.97M profit. | Confirms data ceiling is not the main blocker; gate is calibrated; generation is the bottleneck. |
| `.omo/evidence/tmap-walkforward/champion_diag_discovery.log` | FROZEN_THETA, T2C1, T2C2, T2C3 all gate=True under discovery config. | Raises gate confidence and validates positive-control process. |
| `docs/update_log/2026-06-17_session_handoff_anchor_mutation_research.md` | Records P0-P5 implemented/verified and anchor mutation switch from cold LLM generation. | Raises end-to-end process maturity, but OOS still pending. |
| `docs/update_log/2026-06-17_anchor_mutation_convergence_structural_analogy.md` | Anchor mutation hill-climb converged by round 8 with +13.93M train profit, then plateau. | Raises mutation/grid/autonomy score; also flags local optimum and train-only limitation. |
| `.omo/evidence/tmap-walkforward/ovn_anchor_summary.json` | 19 rounds, 399 adopted, best `r8_4_strength_max=250`, profit +13,928,386, MDD 9.62. | Strong train-gate discovery result; not OOS proof. |
| `.omo/evidence/tmap-walkforward/ovn_anchor.jsonl` | Round ledger shows adopted_total=399 and final best remains r8_4. | Confirms summary with per-candidate evidence. |
| `.omo/evidence/tmap-walkforward/full_stateful_n40_summary.json` | Full stateful n=40 still has `promising: []`. | Keeps OOS proof score low. |
| `.omo/evidence/tmap-walkforward/full_stateful_n40.md` | 40 cold/stateful LLM candidates mostly no-go; no PROMISING. | Confirms cold LLM generation remains weak. |
| `.omo/evidence/tmap-walkforward/ovn_t2late.jsonl` | t2late multistart reached best +10,582,342 / MDD 11.5 by r4_4 and adopted_total=30 by round 9. | Supports multistart idea and generation diversity improvement. |
| `.omo/evidence/tmap-walkforward/ovn_t2late_summary.json` | Current summary says rounds=2, adopted_total=0, best=null, conflicting with `ovn_t2late.jsonl`. | Lowers DB/evidence lineage score due to summary drift. |
| `docs/update_log/2026-06-17_AGENT_RESUME_RUNBOOK.md` | Documents run state, dashboard, tests, P0-P5 files, and next OOS step. | Raises runbook/research management score. |
| `ai_strategy_loop/brain/feature_importance_feedback.py:86` | Adds feature-importance prefer lines from segment B_* signals. | Raises buy-side diagnosis and feedback score. |
| `ai_strategy_loop/autopsy/analyze.py:380` | Adds exit regret and false-break fields. | Raises sell-side diagnosis score. |
| `ai_strategy_loop/autopsy/summarize.py:396` | Exit forensics lines are appended only when toggle is enabled. | Raises feedback policy while preserving default-OFF guard. |
| `ai_strategy_loop/fitness/lift.py:138` | Adds in-sample EV/lift/payoff forensic helper. | Raises forensic analysis score, but still advisory. |
| `ai_strategy_loop/tmap/mutator.py:43` | Adds pure adjacent-anchor mutation proposals. | Raises mutation/grid and autonomy score. |
| `ai_strategy_loop/scripts/tmap_autopsy_loop.py:79` | Orchestrates mutation candidates through P0b gate; only passed candidates adopted. | Raises end-to-end autonomy score. |
| `ai_strategy_loop/scripts/overnight_anchor_mutation.py:73` | Runs LLM-free anchor mutation hill-climb with materialize + batch eval + gate adoption. | Major improvement over cold generation. |
| `ai_strategy_loop/fitness/backtest_timeseries.py:54` | Adds concurrent holdings analysis. | Raises dashboard/runbook observability. |
| `ai_strategy_loop/fitness/backtest_timeseries.py:109` | Adds time-of-day profit buckets. | Raises dashboard/runbook observability. |
| `ai_strategy_loop/dashboard/app.py:1468` | Adds CSV fallback by buy-name for warm-batch/anchor runs. | Raises dashboard reliability for live research runs. |
| `ai_strategy_loop/dashboard/app.py:3233` | Adds `/time_profit` endpoint. | Raises dashboard/runbook score. |
| `ai_strategy_loop/dashboard/app.py:3273` | Adds `/run_log` endpoint. | Raises monitoring/runbook score. |
| `tests/unit/test_feedback_toggles_on.py` | Verifies research presets enable feedback toggles while defaults stay OFF; FDR behavior tested. | Raises test-backed feedback confidence. |
| `tests/unit/test_mutator.py` | Verifies adjacent mutation, no new identifiers, render consistency. | Raises mutation reliability. |
| `tests/unit/test_tmap_autopsy_loop.py` | Verifies gate-passed-only adoption and no bypass. | Raises process safety. |
| `tests/unit/test_lift.py` | Verifies EV/lift/payoff and graceful behavior. | Raises forensic helper reliability. |
| `tests/unit/test_p5_exit_forensics.py` | Verifies exit regret/false-break and toggle-off byte identity. | Raises sell-side feedback confidence. |
| `tests/unit/test_backtest_timeseries.py` | Verifies concurrent holdings/time-profit helpers. | Raises dashboard analysis confidence. |

## Evidence Interpretation
| Category | 2026-06-15 State | 2026-06-17 State |
|---|---|---|
| Cold LLM discovery | Proxy smoke-pass improved but OOS 0. | Still weak; full n=40 PROMISING remains 0. |
| Gate calibration | P0b known-good/bad tested. | Stronger: champion positive control 4/4 passes discovery gate. |
| Mutation/autonomy | Mostly roadmap. | P4/P5 modules and LLM-free anchor mutation driver exist; train gate produces many passers. |
| Research output | Score report and plan existed. | Runbook, convergence report, dashboard/process-flow updates, anchor mutation evidence exist. |
| OOS proof | 0. | Still 0 for new candidates; anchor champion OOS pending. |
| Evidence hygiene | Mostly coherent. | Improved volume, but `ovn_t2late_summary.json` conflicts with `ovn_t2late.jsonl`; lineage needs repair. |
