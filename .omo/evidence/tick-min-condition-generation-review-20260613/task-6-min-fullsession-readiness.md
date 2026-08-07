# Task 6 Min 09:00~15:00 Full-Session Readiness Review

## Verdict

Min full-session infrastructure is mostly wired, but full-day condition generation is not complete. The current evidence says the engine can run min candidates; it does not say a profitable 09:00~15:00 min condition has been discovered.

## Ready Pieces

- `full_session_enabled=True` with `bt_timeframe=min` opens the warm backtest end time to `bt_min_universe_end_time=150000`.
- Tick ignores the min full-session branch, so the timeframe boundary is protected.
- `min_session_0900_1500_rotation.json` provides a min-specific template with 09:00~15:00 entry and 15:00 force exit.
- Min/tick variable scope tests and template validation tests pass.

## Time-Band Coverage Needed

The current template can express the day, but a full-day condition generation system needs evidence by band:

| band | current status | missing proof |
|---|---|---|
| 09:00~10:00 | template expressible | primitive map result and density/profit profile |
| 10:00~11:30 | template expressible | primitive map result and overfire check |
| 11:30~13:00 | template expressible | lunch/low-liquidity behavior profile |
| 13:00~14:50 | template expressible | afternoon continuation/reversal profile |
| 14:50~15:00 | template expressible | close-risk and forced-exit behavior profile |

## Current Runtime Evidence

- `min_e2e_smoke_log.txt`: prepare ok, back_count 346, but `MIN_E2E_SMOKE` ended profit -64,197 and gate false.
- `m2_smoke_log.txt`: prepare ok, back_count 448, but M2 strength combo ended profit -803,805 and gate false.

These are engine-chain evidence, not strategy-success evidence.

## LLM Guidance Gap

The current prompt system has strong tick/opening-session language. `encourage_time_dispersion` still points to 09:00~09:20 and does not guide the model across 09:00~15:00 min bands. Before more min LLM batches, the model needs a compact M1 primitive map and explicit min band instructions.

## OOS Limitation

Min data is about 11개월: 2025-04-07 through 2026-02-27. That means fixed min OOS is structurally limited to 2026-01~02 after train use. Unlike tick, min cannot claim multi-year fixed OOS robustness from the current database alone.

## Required Missing Step

The next step should be M1: 6 primitives x time bands. It should answer "which signal works at which time" before any broad LLM min generation resumes.

