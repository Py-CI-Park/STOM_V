# Source Inventory - Condition Self-Improvement Process Report

## Scope
- Work plan: `.omo/plans/condition-self-improvement-process-report-20260615.md`
- Report target: `docs/update_log/2026-06-15_condition_self_improvement_process_report.md`
- Purpose: capture concrete source/evidence references used to score and improve the AI condition self-improvement loop.

## Inventory
| Source | Finding | Meaning | Report Section |
|---|---|---|---|
| `ai_strategy_loop/scripts/tmap_multiband_discovery.py:87` | `build_feedback(records)` builds feedback from previous discovery records. | A stateful feedback bridge already exists, but it is text/prompt based rather than a typed policy ledger. | Current architecture, Feedback |
| `ai_strategy_loop/scripts/tmap_multiband_discovery.py:98` | Feedback separates no-go, smoke-pass overfit, and full-period survivors. | The loop already learned that smoke-pass is not success; overfit must become avoid, not prefer. | Current tests, Feedback policy |
| `ai_strategy_loop/scripts/tmap_multiband_discovery.py:133` | `generate(..., feedback_text)` writes `_discovery_feedback.txt` and passes `--feedback-file`. | Discovery can inject lessons into the next generation without changing backtest engines. | Process map |
| `ai_strategy_loop/scripts/tmap_multiband_discovery.py:212` | Evaluation escalates from q1 smoke to q2 same-coordinate smoke, full train, then OOS configs. | The validation funnel is structurally honest and blocks two-quarter overfit from becoming promotion. | Gate quality |
| `ai_strategy_loop/scripts/tmap_multiband_discovery.py:301` | `--stateful` toggles feedback; no flag means random/stateless baseline. | This supports clean A/B comparison between random and closed-loop generation. | A/B evidence |
| `ai_strategy_loop/scripts/gen_template_hypothesis.py:73` | `build_prompt(... feedback_text=...)` can append feedback to the generation prompt. | Prompt-level feedback exists, but policy semantics are not machine typed. | Feedback gap |
| `ai_strategy_loop/scripts/gen_template_hypothesis.py:449` | CLI reads `--feedback-file` into `feedback_text`. | The generation CLI is already wired for a feedback loop. | Process map |
| `ai_strategy_loop/brain/segment_feedback.py:84` | `build_segment_avoid_lines` generates buy-prompt avoid lines from losing cells. | Entry-side bad-segment avoidance is partially implemented. | Buy-Side Diagnosis |
| `ai_strategy_loop/autopsy/analyze.py:25` | B_* entry columns are enumerated for diagnosis. | Buy-side entry variables are available for quant-style failure analysis. | Buy-Side Diagnosis |
| `ai_strategy_loop/autopsy/analyze.py:136` | Entry autopsy raises on `is_holdout=True`. | The system already has a leakage guard: autopsy is train/working-only. | OOS guard |
| `ai_strategy_loop/autopsy/analyze.py:295` | `analyze_exits` evaluates exit behavior from trade CSVs. | Sell-side diagnosis exists but is not yet fully wired into typed generation actions. | Sell-Side Diagnosis |
| `ai_strategy_loop/autopsy/analyze.py:371` | Exit result computes MFE, realized return, giveback gap, MAE, hold time, sell-rule stats. | Raw exit regret/giveback metrics are available for sell-rule improvement. | Sell-Side Diagnosis |
| `backtest/backengine_base.py:546` | Buy snapshot is stored at entry. | Trade result CSV can retain entry-state features for post-trade learning. | Data capture |
| `backtest/backengine_base.py:557` | Result snapshot includes `R_매수후최고수익률`, `R_매수후최저수익률`, `R_MFE`, `R_MAE`. | MFE/MAE fields are produced by the official backtest path. | Sell-Side Diagnosis |
| `backtest/backengine_base.py:902` | `CalculationEyun` emits trade result payload including sell condition and extra data. | Buy/sell snapshots and result metrics flow into the backtest result queue. | Data capture |
| `ai_strategy_loop/config.py:340` | Exit-edge feedback rationale is documented and default-OFF. | Sell feedback is understood conceptually but not enabled as default autonomous behavior. | Config readiness |
| `ai_strategy_loop/config.py:355` | Segment feedback rationale is documented and default-OFF. | Bad cell avoidance is designed as opt-in prompt feedback. | Feedback gap |
| `ai_strategy_loop/config.py:444` | Classification generation guidance covers market-cap, change regime, and broad 09:00-09:30 time window. | Seed breadth is a known deficiency and has prompt toggles, but not a coverage ledger. | Seed Coverage |
| `ai_strategy_loop/config.py:500` | Quantile and counterfactual feedback toggles are default-OFF. | The system has analysis-to-threshold ideas, but activation and gate discipline remain future work. | Feedback policy |
| `ai_strategy_loop/config.py:514` | Prompt logging is default-OFF and described as necessary for reproducibility. | DB lineage is not complete until prompt and feedback lineage are persisted. | DB/evidence |
| `ai_strategy_loop/dashboard/analysis_snapshot.py:145` | Research analysis snapshots can persist analysis rows and payloads to SQLite. | Dashboard analysis storage exists, but it is analysis snapshot storage rather than full self-improvement lineage. | DB/evidence |
| `ai_strategy_loop/dashboard/analysis_snapshot.py:244` | Snapshot analysis includes correlation, edge ratio, feature importance, generation metrics, daily P/L. | The dashboard can explain candidate behavior, but closed-loop actions are not fully connected. | Dashboard |
| `.omo/evidence/tmap-walkforward/p1_ab_preregistration.md:14` | OOS PROMISING count is the single honest pass metric; proxy rates are progress only. | Scores and smoke rates must not be treated as real success. | Scoring |
| `.omo/evidence/tmap-walkforward/ab_result_n8.json` | Random smoke-pass rate 0.0, stateful smoke-pass rate 0.375, both OOS 0. | Feedback improves a proxy signal in pilot, but no OOS success is proven. | Test results |
| `docs/update_log/2026-06-15_multiband_overnight_results.md:8` | 40 iterations produced PROMISING 0 and only one full-period attempt, rejected as overfit. | Current discovery gate is honest, but autonomous discovery quality is still weak. | Overall score |
| `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md:16` | P0b real backtest gate passed known-good +2.17M and refused a -3M candidate. | The rebacktest safety gate is one of the strongest completed components. | Gate quality |
| `docs/update_log/2026-06-15_condition_discovery_process_research_report.md:310` | Prior review promoted rebacktest gate before feedback-on due to selection-bias risk. | In-sample feedback must stay advisory until revalidated by frozen gates. | Roadmap |

## Summary
| Area | Evidence Count | Current Read |
|---|---:|---|
| Generation and feedback plumbing | 7 | Present but mostly prompt-text based |
| Backtest and gate discipline | 5 | Strongest part of the process |
| Buy/sell diagnostic data | 6 | Raw data and analyzers exist; typed actions incomplete |
| Seed breadth | 2 | Known deficiency; toggles exist but coverage ledger missing |
| DB/dashboard lineage | 4 | Analysis storage exists; full learning lineage incomplete |
| OOS proof | 3 | Current OOS/PROMISING result is still 0 |
