# CSS_V7 Root Cause Before Plan B

## Scope

Run this before resuming the original Plan B path. The goal is to decide whether
the current blocker is caused by invalid CSS_V7 condition generation, by the
official backtest runtime, or by another adjacent issue.

## Constraints

- Do not run Plan B or Plan D.
- Do not touch A3, promotion-review, export, live, or final promotion paths.
- Do not mutate the main strategy DBs during diagnosis.
- Use copied strategy DBs for any variant tests.
- Do not stage or clean existing dashboard files, `.gjc`, or unrelated `.omo`
  residue.
- Do not use `git add -A`.

## R0. Scope And Evidence Setup

Acceptance:

- Create `.omo/evidence/css-v7-root-cause-before-plan-b-20260703/`.
- Record current git status, active blocker, and protected-scope constraints.
- Update `.omo/boulder.json` active work to this root-cause task.

## R1. Static Generation And Runtime Contract Audit

Acceptance:

- Compare CSS_V7 catalog conditions with DB rows by name and sha256.
- Compile buy/sell code through the same parser path used by the backtest gate.
- Inspect `self.Buy(...)` and `self.Sell(...)` call arity in CSS_V7 rows.
- Compare those calls with the official backtest engine method signatures.
- Report all affected CSS_V7 rows and any other runtime-only defects found.

## R2. Runtime Axis Isolation

Acceptance:

- Use an isolated copied strategy DB for all variant rows.
- Run the same valid tick micro-window for:
  - known comparator pair,
  - original CSS_V7 tick master pair,
  - CSS_V7 tick master with only `self.Buy(...)`/`self.Sell(...)` normalized
    to `self.Buy()`/`self.Sell()`.
- If needed, isolate buy-side and sell-side variants separately.
- Record elapsed time, CSV presence, timeout status, and captured diagnostics.

## R3. Root-Cause Report And Next-Step Decision

Acceptance:

- State whether the problem is condition generation, condition backtest runtime,
  or both.
- List related issues that can affect later plans.
- Decide whether Plan B is blocked, can proceed with exclusions, or should wait
  for a repair pass.
- Write a concise report under `docs/update_log/`.

## Verification

- `python -m py_compile` for any new Python diagnostic scripts.
- JSON parse checks for generated evidence.
- `git diff --check` on touched paths.
- `python scripts/verify_nonrelease_sync.py`.
- Confirm no lingering diagnostic backtest processes.
