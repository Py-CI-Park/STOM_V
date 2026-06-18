# P0 Safety Baseline

Status: `complete`

## Scope

- Plan: `.omo/plans/ct-seed-branch-workload-isolation-20260605.md`
- Evidence root: `.omo/evidence/ct-seed-branch-workload-isolation-20260605/`
- Date/time: `2026-06-05 KST`

## Git / Boulder

| Field | Value |
|---|---|
| HEAD | `84acb6cb` |
| Branch | `lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| Boulder active work | `ct-seed-branch-workload-isolation-20260605` |
| Previous page verdict | `CT_SEED_WINDOW_BLOCKER` |

## Dirty Worktree Boundary

The worktree was already broadly dirty before this page, mainly from prior dashboard/research work and evidence files. This page only intends to add:

- `.omo/plans/ct-seed-branch-workload-isolation-20260605.md`
- `.omo/evidence/ct-seed-branch-workload-isolation-20260605/*`
- `.omo/boulder.json` work-state metadata
- temporary runtime rows in `ai_strategy_loop/state/loop_strategies.db`, cleaned in Final

No staging or commit is planned in this page.

## Protected / Runtime Paths

Protected path status command was checked at P0. No protected source path is intentionally edited. Runtime DB writes are limited to temporary diagnostic strategy rows in the loop strategy DB and must not be staged.

## Process Boundary

Existing Python processes were present, including Hermes/dashboard/web services and unrelated user runtimes. No process was killed. Runtime probes in this page must use owned subprocesses through `ai_strategy_loop/scripts/tick_seed_timeout_probe.py` and its owned-tree cleanup only.

## Hard Blocks Kept

- No official backtest engine or hard-gate edits.
- No `backtest/graph` edits.
- No `final_approval`, `export_winner`, live broker/KHOPENAPI, or V3K path.
- No 2023-2025 training or 2022/2026 OOS until a repaired C_T preflight passes.
