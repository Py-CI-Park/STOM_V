# P4 Bounded C_T Warm/Cold Preflight

Status: `complete`

## Same-Window Candidate

- Date: `2025-01-03`
- Window: `09:02:00..09:05:00`
- Timeframe: `tick`
- Engines: `1`
- Seed: `C_T_900_920_U2_B/S`
- Control reference: `ct_preflight_control_902_905_warm_20260605` passed on the same date/window.

## Warm Result

Artifacts:

- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-902-905-warm-config.json`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-902-905-warm-result.json`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-902-905-warm-result.stdout.txt`

Observed:

| Field | Value |
|---|---:|
| run id | `ct_preflight_ct_902_905_warm_20260605` |
| wrapper status | `ok` |
| wrapper timeout | `false` |
| wall cap | `240s` |
| wrapper elapsed | `174.767s` |
| warm prepare | `completed` |
| back_count | `43` |
| backtest status | `error` |
| backtest elapsed | `133.5s` |
| reason | warm backtest timeout at `120s`, `csv=no` |
| CSV/metrics | no |

## Cold Result

Artifacts:

- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-902-905-cold-result.json`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p4-ct-902-905-cold-result.stdout.txt`

Observed:

| Field | Value |
|---|---:|
| wrapper status | `error` |
| wrapper timeout | `false` |
| CLI return code | `3` |
| command timeout | `120s` |
| wall cap | `240s` |
| wrapper elapsed | `161.469s` |
| moneytop rows | `181` |
| back_count | `43` |
| last checkpoint | `backtest_process_started` |
| checkpoint status | `timeout` |
| cleanup status | `process_killed` |
| CSV/metrics | no |

## Decision

`CT_SEED_WINDOW_BLOCKER`

The same date/window is active enough for the control strategy to complete with CSV/metrics, but C_T times out in both warm and cold bounded preflight after data load. This is not a performance rejection and not an OOS result. It is a runtime preflight blocker tied to the C_T seed/window workload.

Larger January, 2023-2025 training, and 2022/2026 OOS remain blocked.

## QA

| Scenario | Result |
|---|---|
| C_T passing preflight | fail; C_T produced no CSV/metrics |
| C_T fails despite active control | pass; same-window control passed, C_T warm/cold timed out |

## Adversarial Notes

- Hung/long command: warm and cold had inner `120s` timeout and outer `240s` wall cap.
- Misleading success: wrapper `ok` for warm is not counted as preflight pass because backtest status is error and CSV/metrics are absent.
- Cleanup: cold timeout path reports `process_killed` for the owned backtest process; no blanket process kill was used.
