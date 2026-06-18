# P7 Decision Card

Verdict: `BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS`

## Executive Verdict

The dashboard/engine observability part advanced meaningfully, but the bounded P7 training path is blocked before long 2023-2025 execution.

P3 preflight showed that the system can now report the active period, tick timeframe, engine mode/count, CPU count, timeout, progress source, status phase, and recent logs through `/status` and the dashboard panel. It also showed the real blocker: the seed warm backtest timed out at `300s` and produced no CSV.

Because the preflight timed out, P4 long training and P6 fixed 2022/2026 OOS were not run.

## Source Documents Used

- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-06-05_direction_review_through_84acb6cb.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md`
- `.omo/evidence/tick-research-direction-realignment-20260605/p7-train-log.txt`
- `.omo/evidence/tick-research-direction-realignment-20260605/p9-decision-card.md`
- `.omo/evidence/tick-dashboard-observability-research-ux-20260604/final-verification.md`

## Observability Changes Summary

Backend contract:
- Added explicit `progress_source`, `timeout_sec`, and `timeout_deadline_epoch` to `latest.backtest_progress`.
- Added timeout, period, timeframe, time-window, CPU, engine-count fields to `latest.engine_state`.
- Kept old `source=loop_generation` for backward compatibility.

Dashboard:
- Engine panel now displays `Timeout`, `Deadline`, `Progress Source`, `Period`, `bt_timeout`, and `bt_warm_run_timeout`.
- It labels wrapper progress as `generation_level`, not `engine_internal`.

## Preflight Result

| Item | Value |
|---|---|
| Run ID | `tick_p7_preflight_observable_20260605` |
| Period | `2025-01-01..2025-01-31` |
| Timeframe | `tick` |
| Window | `09:00:00..09:30:00` |
| Engine | `warm`, 8 engines |
| Warm prepare | completed, `back_count=400` |
| gen0 seed | `C_T_900_920_U2_B` / `C_T_900_920_U2_S` |
| Backtest result | timeout |
| Backtest elapsed | `328.3s` |
| CSV | no |
| DB row | `status=error`, `score=0.0`, `trade_count=0` |

## P7 Training Result Or Blocker

P4 long training run `tick_p7_train_2023_2025_observable_20260605` was not started.

Reason:
- P3 seed warm backtest exceeded the configured `300s` timeout.
- Starting a 2023-2025 `max_generations=10` run after a failing preflight would hide the actual bottleneck behind a multi-hour job.

## Candidate Pool Table

| Pool | Count | Status |
|---|---:|---|
| `exploration_pool_v2` | 0 | blocked |
| `research_pool_v2` | 0 | blocked |
| `promotion_gate_v2` | 0 | denied |
| `promotion_candidate` | 0 | null |

## Promotion Gate Summary

`promotion_gate_v2.promotion_allowed=false`

Reason:
- No P4 training rows exist.
- No candidate identity can be frozen.
- OOS must remain blocked.

## OOS Result Or Blocker

Fixed 2022/2026 OOS was not run.

Reason:
- No frozen promotion candidate exists.
- No OOS-after-the-fact reselection is allowed.

## PBO / DSR / Slippage Status

| Diagnostic | Status |
|---|---|
| PBO | not run |
| DSR | not run |
| Slippage | not run |
| Promotion | blocked |

## Human / Seed-Level Claim Status

No human-level, seed-superior, or promotion-ready claim is supported.

What improved:
- The system is now better at explaining where a long run is stuck.
- The dashboard can show active engine settings and timeout state before trusting a long run.

What is not proven:
- No 2023-2025 training pool.
- No fixed 2022/2026 OOS.
- No PBO/DSR/slippage promotion proof.

## Full Page Progress Table

| Stage | Page / Area | Status | Evidence |
|---|---|---|---|
| P0 | Safety snapshot | done | `p0-safety-snapshot.txt` |
| P1 | Backend progress and engine-state contract | done | `p1-observability-contract.md` |
| P2 | Dashboard engine panel and status smoke | done | `p2-dashboard-observability-smoke.md` |
| P3 | Bounded preflight smoke | blocked after execution | `p3-preflight-smoke-summary.md` |
| P4 | 2023-2025 P7 training | not started | `p4-train-blocked.md` |
| P5 | Candidate pools | blocked artifact written | `p5-candidate-pools.json` |
| P6 | 2022/2026 OOS | blocked | `p6-oos-blocked.md` |
| P7 | Decision card | done | this file |
| Final | Verification wave | done | `final-verification.md` |

## Forbidden Action Check

- `final_approval`: not invoked.
- `export_winner`: not invoked.
- Production strategy DB write: not invoked.
- Live broker/KHOPENAPI: not invoked.
- V3K gate action: not invoked.
- Blanket `taskkill`: not used.
- Official backtest engines: not edited.
- Hard-gate fitness: not edited.

## Current Page Outcome

The current execution page has achieved the observability objective, not the human-condition proof objective.

The next work should target the seed warm-backtest timeout before retrying long training.

## Next Recommended Command

```text
$ulw-plan tick P7 preflight timeout unblock plan: reduce or segment the seed warm backtest workload before retrying 2023-2025 training. Use .omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-blocked.md and p4-train-blocked.md as the primary evidence, preserve official engines and hard gates, and do not run OOS until a frozen promotion candidate exists.
```
