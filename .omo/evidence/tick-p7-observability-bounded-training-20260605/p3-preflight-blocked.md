# P3 Preflight Blocker

Status: blocked for P4 long training

The P3 preflight produced dashboard/status evidence, but the seed warm backtest timed out:

- Run ID: `tick_p7_preflight_observable_20260605`
- Period: `2025-01-01..2025-01-31`
- Timeframe: `tick`
- Window: `09:00:00..09:30:00`
- Seed buy/sell: `C_T_900_920_U2_B` / `C_T_900_920_U2_S`
- Warm timeout: `300s`
- Backtest elapsed: `328.3s`
- CSV: not produced
- DB status: `error`

Because the bounded preflight timed out, P4 `2023-2025` long training is not started.

Next technical blocker to solve:
- reduce or segment the warm seed preflight workload, or
- add a smaller diagnostic config before any multi-year P7 training, or
- improve warm-session timeout/reset behavior so one over-firing seed does not consume the whole preflight.
