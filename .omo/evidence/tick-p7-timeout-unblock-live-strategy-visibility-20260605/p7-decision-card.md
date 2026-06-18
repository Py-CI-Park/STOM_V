# P7 Decision Card

Terminal verdict: `BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS`

## Summary

The dashboard/route visibility part of this page is complete. The main dashboard now has an Active Strategy panel, `/strategy_code` and `/strategy_diff` return HTTP 200 dashboard-safe payloads for missing/stale/empty cases, and focused tests plus an owned-server smoke proved the current source does not reproduce the stale 404 route issue.

The research execution part remains blocked. The smallest planned seed diagnostic, `2025-01-01..2025-01-03` tick `09:00:00..09:05:00` warm mode with `C_T_900_920_U2_B/S`, timed out at the backtest layer and produced no CSV. Because the first diagnostic gate failed, 10m diagnostic, January retry, 2023-2025 training, and 2022/2026 OOS were not started.

## Page Progress

| Page | Status | Result |
|---|---|---|
| P0 Safety Snapshot And Route Baseline | done | Source routes existed; no 8770 listener during baseline; protected path status clean. |
| P1 Additive Strategy Route Contract Hardening | done | `/strategy_code` and `/strategy_diff` expose `ok`, `code_status`, `diff_status`, and `reason`; no dashboard 404 for missing states. |
| P2 Active Strategy Identity Contract | done | Active source order is winner, best, newest finalized generation, streaming partial, then no strategy. |
| P3 Main-Page Active Strategy Panel | done | Main Run Monitor shows active buy/sell names, bounded code preview, status labels, and code viewer action. |
| P4 Previous Diff And AI Context Linkage | done | Previous diff fetch and stale/empty/missing states are visible and tested. |
| P5 Seed Timeout Diagnostic Ladder | blocked | First 5m seed diagnostic failed: warm timeout `120s`, backtest elapsed `133.2s`, CSV `no`, DB status `error`. |
| P6 Training Retry Gate | blocked | 10m, January, 2023-2025 training, and 2022/2026 OOS are not allowed until a smaller seed preflight passes. |
| P7 Decision Card And Page Progress | done | This card separates dashboard success from performance proof and records the next command. |
| Final Verification Wave | done | Focused tests, nonrelease verifier, protected-path check, and diff whitespace check completed. |

## Honest Performance State

No human-level, seed-superior, or OOS superiority claim is supported by this page.

What is supported:

- dashboard visibility and route resilience improved;
- missing strategy code/diff states are explicit instead of failing as dashboard 404;
- the current blocker is now narrower than before: seed warm TICK can timeout even on a 3-day, 5-minute window.

What is not yet supported:

- 2023-2025 full training;
- fixed 2022/2026 OOS comparison;
- promotion candidate freeze;
- final approval or export.

## Forbidden Action Checklist

| Action | Status |
|---|---|
| Official backtest engine edits | not done |
| Hard-gate relaxation | not done |
| `final_approval` | not invoked |
| `export_winner` | not invoked |
| Live broker/KHOPENAPI connect/login/order path | not invoked |
| V3K gate action | not invoked |
| Protected path source edit/staging | not done |
| 2022/2026 OOS | not run |

## Next Recommended Command

```text
$ulw-plan tick seed warm timeout root-cause plan: use .omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md as primary evidence. Diagnose why C_T_900_920_U2_B/S times out even on 2025-01-01..2025-01-03 tick 09:00-09:05 warm mode, compare smaller window and cold/warm behavior if safe, preserve official backtest engines and hard gates, and do not start 2023-2025 training or OOS until a passing preflight exists.
```
