# P4 Training Blocked

Verdict: `blocked_with_timeout_evidence_no_oos`

P4 `2023-01-01..2025-12-31` long TICK training was not started.

## Blocking Evidence

- P3 preflight run: `tick_p7_preflight_observable_20260605`
- P3 period: `2025-01-01..2025-01-31`
- P3 timeframe/window: `tick`, `09:00:00..09:30:00`
- P3 max generations: `1`
- P3 warm timeout: `300s`
- P3 outcome: gen0 seed warm backtest timed out after `328.3s`, CSV not produced.
- P3 DB row: `status=error`, `score=0.0`, `trade_count=0`.

## Why P4 Did Not Run

The plan requires a bounded preflight before long P7. Since that preflight timed out, running a 2023-2025 `max_generations=10` job would likely burn hours without producing a promotion-ready pool and would hide the blocker behind a longer run.

## Next Blocker Target

Before retrying P4:

- use a smaller seed diagnostic config, or
- segment the seed warm backtest window/universe, or
- revise warm-session timeout/reset handling so a known over-firing seed does not consume the entire preflight.

Guardrail:
- No OOS.
- No final approval/export.
- No official engine or hard-gate edits.
