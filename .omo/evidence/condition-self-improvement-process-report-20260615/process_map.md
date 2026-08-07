# Process Map - Condition Self-Improvement Loop

## Current Flow
| Step | Current Status | Evidence | What Works | Missing Bridge |
|---|---|---|---|---|
| 1. Historical DB/result data | Partial | `backtest/backengine_base.py:546`, `:902` | Trade result payload includes entry snapshot, sell condition, MFE/MAE. | DB lineage does not yet connect every prompt, feedback action, seed, run, and promotion decision. |
| 2. Seed/template selection | Partial | `ai_strategy_loop/config.py:444` | Broad generation guidance exists for time/cap/change axes. | No coverage ledger ensuring unexplored tick/min cells are systematically sampled. |
| 3. Generator prompt | Partial | `ai_strategy_loop/scripts/gen_template_hypothesis.py:73` | Prompt can include principles, registry, lessons, feedback text. | Feedback is natural-language context, not typed action records with measurable intent. |
| 4. Schema/syntax gate | Present | `ai_strategy_loop/scripts/gen_template_hypothesis.py:111` | Generation enforces JSON schema in prompt and retries prior errors. | Report did not validate every downstream schema gate; this remains support evidence, not final pass proof. |
| 5. Stateful discovery | Present | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:301` | `--stateful` cleanly separates random vs feedback arms. | Feedback categories are narrow: flood, overfit, survivor; no fine action taxonomy. |
| 6. Smoke validation | Present | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:218` | q1 then q2 same-coordinate smoke gate prevents one-slice wins. | Smoke pass is still a proxy and must never become success. |
| 7. Full train validation | Present | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:237` | Full-period validation catches two-quarter overfit. | Full train remains in-sample; promotion must still require OOS/WF. |
| 8. OOS escalation | Present | `ai_strategy_loop/scripts/tmap_multiband_discovery.py:249` | OOS config loop can set PROMISING only after all OOS positive. | Existing pilot and overnight runs still produce OOS/PROMISING 0. |
| 9. Entry autopsy | Partial | `ai_strategy_loop/autopsy/analyze.py:25` | B_* variables support entry discrimination. | Findings are not fully converted into typed tighten/relax/mutate actions. |
| 10. Exit autopsy | Partial | `ai_strategy_loop/autopsy/analyze.py:295` | MFE/MAE/giveback/hold/sell-rule diagnostics exist. | Exit regret does not yet drive systematic sell-rule mutation. |
| 11. Segment feedback | Partial | `ai_strategy_loop/brain/segment_feedback.py:84` | Losing time/cap/change cells can become avoid lines. | Avoid lines need lifecycle: source, expiry, validation, collision handling. |
| 12. Dashboard/report | Partial | `ai_strategy_loop/dashboard/analysis_snapshot.py:244` | Dashboard can compute edge ratio, feature importance, generation metrics, daily P/L. | Dashboard is not yet a closed-loop action console with typed feedback decisions. |

## Target Self-Improvement Flow
| Target Step | Required Behavior | Data Needed | Gate Needed | Output |
|---|---|---|---|---|
| 1. Seed coverage planner | Select tick/min, time bucket, cap bucket, change regime, entry family, exit family by coverage debt. | Coverage ledger and prior trial outcomes. | No duplicate over-sampling unless anchor quota. | Seed batch plan. |
| 2. Candidate generation | Generate branches from selected coverage cells and known anchors. | Prompt lineage, principle set, allowed variables. | Syntax/schema/cost gate. | Candidate template + prompt id. |
| 3. Backtest funnel | Run q1/q2 same-coordinate, full train, OOS/WF. | Frozen configs and artifact paths. | PROMISING only if OOS/WF passes. | Verdict with metrics. |
| 4. Trade autopsy | Split losses by entry failure and exit failure. | B_* snapshots, MFE/MAE, hold, sell rule, daily P/L. | Train-only analysis guard. | Diagnostic facts. |
| 5. Typed feedback decision | Convert facts to action: reject, avoid_segment, tighten_threshold, relax_threshold, mutate_seed, revise_exit, preserve_anchor, promote_candidate. | Diagnostic facts and prior action history. | No in-sample-only promotion. | Feedback action ledger row. |
| 6. Mutation or reseed | Apply the action in the next generation batch. | Seed/action ledger and prompt builder. | Budget and duplicate guard. | New candidate family. |
| 7. Revalidation | Compare against baseline and prior action intent. | Frozen baseline and trial id. | OOS/WF, C3 stop rule, P0b rebacktest gate. | Keep/drop/promote. |
| 8. Dashboard/runbook | Show what was tried, why it changed, and whether it generalized. | Full lineage, artifacts, report snapshot. | No hidden success metric. | Human-readable research status. |

## Partial or Missing Bridges
| Bridge | Current State | Why It Matters | Required Update |
|---|---|---|---|
| Seed coverage ledger | Missing | Without coverage accounting, the loop can repeatedly mine the same 09:00-09:05 or THETA-like area. | Add coverage debt tracking for timeframe x time x cap x change x entry x exit. |
| Typed feedback action ledger | Missing | Natural-language feedback is hard to audit and cannot measure whether a change did what it intended. | Store action type, source metric, intended mutation, leakage guard, next validation result. |
| Buy/sell cause split | Partial | Bad P/L can come from entry noise or exit giveback; improving the wrong side creates overfit. | Produce separate buy-side and sell-side diagnosis before mutation. |
| OOS promotion discipline | Present but fragile | Proxy rate improved in n=8, but OOS stayed 0. | Keep OOS/WF count as the only success metric. |
| Prompt lineage | Partial/default-OFF | Without prompt/action lineage, a good or bad candidate is not reproducible. | Enable or design prompt/action logging under research-safe storage. |
| Dashboard action visibility | Partial | Current dashboard explains metrics but not enough "why next generation changed". | Add runbook panels for action ledger and coverage debt. |
