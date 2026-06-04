# STRATEGY KNOWLEDGE BASE

## OVERVIEW
`strategy/` contains strategy adapters and V3K analyzer bridge code that translates analysis-side capabilities into strategy-facing contracts. Keep this layer thin and gate-aware.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| V3K analyzer adapter | `v3k_analyzer_adapter.py` | feature flags, analyzer contracts, learning DB preload/load boundaries. |
| Strategy bridge files | `*.py` in this directory | adapter/helper surfaces around STOM strategy behavior. |

## CONVENTIONS
- Feature flags stay default-OFF unless an approved gate says otherwise.
- Adapter code may expose offline/analyzer data, but live decision consumption is a later gate.
- Preserve Kiwoom runtime compatibility and avoid LS direct broker dependency.
- Keep strategy-facing contracts explicit and testable; avoid hidden DB reads.

## ANTI-PATTERNS
- Do not create live order/exit wiring from adapter availability alone.
- Do not make operating `_database/` writes from this layer before Gate 5 approval.
- Do not mark learning/analyzer features complete without documented evidence.

## LOCAL GOTCHAS
- This directory is a boundary layer; avoid moving heavy analyzer logic here.
- Keep adapter inputs explicit so dashboard/backtest code can reason about provenance.
- If adding strategy-facing fields, update tests and docs that describe feature flags.
- Prefer compatibility shims over breaking old strategy names or DB keys.
- Do not assume V3K sidecar settings are committed source.
- Treat missing learning DBs as expected in this environment.
- Keep bridge code import-safe; no runtime side effects at import time.
- Avoid serial-key or broker-login concerns here.
- Preserve deterministic fallback behavior when analyzers are disabled.
- Document new adapter contracts in `docs/update_log/` when gate-adjacent.
- Never promote advisory analyzer output directly to live decisions.
- Use focused tests around adapter contract changes.
- Keep LS-direct code out of this branch family.
