# P6 Root-Cause Decision Card

Status: `complete`

## Chosen Category

`INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE`

Observed form: wrapper-level evidence narrowed the blocker to exact-window no-metrics after data load, but it cannot prove whether the cause is C_T seed logic, too-small/inactive window selection, or official engine result-generation behavior.

Confidence: `medium-low`

## Evidence Table

| Evidence | Result | Category Impact |
|---|---|---|
| P0 safety | no conflicting process, no protected-path status output, high free RAM | reduces `ENV_RESOURCE_OR_ORPHAN_PROCESS_PRESSURE` likelihood |
| P1 seed audit | C_T buy/sell exist, hashes stable, expected `self.Buy`/`self.Sell` present | refutes `SEED_CODE_MISSING_OR_STALE` |
| P3 exact window audit | `2025-01-02 09:00..09:05` empty; corrected first exact covered day is `2025-01-03` | records data-window trap but does not explain corrected W1R failure |
| P3 W1R warm | data loads, `back_count=41`, but no CSV/metrics | supports exact-window no-metrics |
| P4 plan-bound cold W1R | cold also loads data, `back_count=41`, planned `--timeout 120`, wall cap `240s`, but no CSV/metrics | refutes warm-only regression |
| P5 same-window control | known control seed also fails no-metrics in `09:00..09:01` | prevents overclaiming seed-only proof for the tiny window |
| P5 active-window control | known control seed succeeds in intended `09:02..09:05`, CSV and metrics produced | sanity-checks that the warm stack can produce results on the same day |

## Decision Tree

1. Data/seed missing?
   - No. Seed exists, and the corrected exact day has usable early tick data.
2. Warm-only path regression?
   - No. Cold and warm both fail no-metrics for C_T W1R under the plan-bound cold rerun.
3. Environment/process pressure?
   - Not proven. P0 is clean enough and P5 active-window control succeeds, but same-window control also fails.
4. Engine internals required?
   - Yes for a stronger root cause. Wrapper evidence cannot distinguish C_T no-trade logic from a too-small/inactive window or official engine no-result behavior.
5. Selected category:
   - `INCONCLUSIVE_NEEDS_ENGINE_INTERNAL_EVIDENCE`, with the precise subtype `exact_window_no_metrics_after_data_load`.

## What This Means

- The previous tiny warm timeout blocker should not be treated as proof that the dashboard or warm engine is generally broken.
- A real data-window issue existed in the initial one-day probe: `2025-01-02 09:00..09:05` is empty.
- After correcting to `2025-01-03`, the C_T seed still fails to produce CSV/metrics in both warm and cold paths.
- The same-window `Tick_B_902_905_Update_2/S` control also fails no-metrics, so the tiny `09:00..09:01` window is not a clean seed-only discriminator.
- The known `Tick_B_902_905_Update_2/S` control can produce CSV/metrics on the same day in its intended `09:02..09:05` window, so the broader warm stack is not generally broken.

## Page Progress

| Page Step | Status | Evidence |
|---|---|---|
| P0 Safety | complete | `p0-safety-baseline.md` |
| P1 Seed/config/data audit | complete | `p1-seed-config-data-audit.md` |
| P2 Probe harness | complete | `p2-probe-harness-contract.md` |
| P3 Warm tiny ladder | complete | `p3-warm-tiny-ladder.md` |
| P4 Cold/warm compare | complete | `p4-cold-warm-compare.md` |
| P5 Control baseline | complete | `p5-control-baseline.md` |
| P6 Root cause | complete | this file |
| P7 Training gate | complete | `p7-training-gate.md` |
| Final verification | pending | focused tests, nonrelease sync, diff/protected checks |

## Allowed Next Steps

- Do not start 2023-2025 training or 2022/2026 OOS with `C_T_900_920_U2_B/S` until a seed preflight produces CSV/metrics.
- Build a preflight gate that checks exact per-day time-window coverage before running tick studies.
- Use control seed windows as environment sanity checks, not as performance proof.
- Repair or replace the C_T seed/window pairing, or choose a same-window active control, then rerun the smallest passing preflight.

## Blocked Claims

- No human-level or seed-superior performance claim is allowed.
- No OOS claim is allowed.
- No `final_approval`, `export_winner`, live broker, V3K gate, official engine edit, or hard-gate relaxation is allowed.

## Direction Review Alignment

`docs/update_log/2026-06-05_direction_review_through_84acb6cb.md` says the project must stop treating train-only wins or selector-only wins as proof. This P6 follows that rule: it classifies a runtime blocker only and keeps long training/OOS blocked until a passing preflight exists.
