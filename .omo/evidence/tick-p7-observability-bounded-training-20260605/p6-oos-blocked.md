# P6 OOS Blocked

Status: blocked

Fixed 2022/2026 OOS was not run.

## Reason

`p5-candidate-pools.json` has:

- `status=blocked_not_run`
- `promotion_gate_v2.promotion_allowed=false`
- `promotion_candidate=null`

No frozen promotion candidate exists because P4 long training was not started after the P3 preflight timeout.

## Guardrail

- No AI candidate was evaluated on 2022 or 2026.
- No OOS-after-the-fact reselection occurred.
- No `final_approval`, `export_winner`, production DB write, live broker action, V3K action, or blanket `taskkill` was used.

## Next Requirement Before OOS

Resolve the P3 seed warm-backtest timeout blocker, then produce a P4 training run with frozen `promotion_gate_v2` identity before any fixed 2022/2026 comparison.
