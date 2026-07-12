# Lattice Condition Generation V2 Body Generation Static Dry-Run Plan

Date: 2026-07-08

## Purpose

This page converts a small subset of the metadata-only v2 lattice candidates into executable-looking STOM buy/sell bodies, then stops at syntax/static checks and DB registration dry-run.

The output is not a trading result and does not unlock replay, OOS, portfolio, Plan D R3, or promotion by itself. It only answers whether the v2 candidate metadata can be represented as branch-local STOM condition text without name, SHA, syntax, or dry-run registration problems.

## Read-First Sources

Read these files to EOF before generating any condition body:

- `docs/update_log/2026-07-08_lattice_condition_generation_v2_candidate_dryrun_handoff.md`
- `docs/research/condition_research/generated_conditions/lattice_v2_candidate_dryrun_20260708/lattice_v2_candidate_ledger_20260708.json`
- `docs/research/condition_research/generated_conditions/lattice_v2_candidate_dryrun_20260708/lattice_v2_candidate_static_gate_receipt_20260708.json`
- `docs/research/condition_research/generated_conditions/lattice_v2_candidate_dryrun_20260708/lattice_v2_candidate_db_registration_dryrun_receipt_20260708.json`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

Record `read_scope=full_document`, line count, SHA-256, and applied section for each source in the source read receipt.

## Scope

1. Select at most 8 candidates from the 32 metadata candidates.
2. Preserve class diversity: coverage, risk-balanced, survivor-derivative, negative-control, and holdout-control should be represented when possible.
3. Generate STOM buy/sell bodies for selected candidates only.
4. Use research lane only, `hypothesis_seed` label, sanitized names, and v2 filename-safe DB mapping.
5. Create a `seed_lattice_seeds_v1` JSON suitable for `ai_strategy_loop.scripts.register_lattice_seeds`.
6. Run a local static gate:
   - unique condition IDs
   - body present
   - buy body contains `self.Buy()`
   - sell body contains `self.Sell()`
   - SHA-256 matches body text
   - forbidden token scan passes
   - strategy names are filename-safe after sanitization
   - source lineage is retained
7. Run DB registration dry-run only, without `--apply`.
8. Write source receipt, selection ledger, seed JSON, body static-gate receipt, DB dry-run receipt, ULW evidence, handoff, and next command.
9. Commit only scoped files with an explicit file list and a Korean commit message.

## Forbidden

- DB INSERT apply
- DB UPDATE/DELETE
- backtest, limited replay, OOS, portfolio, Plan D R3
- full tick 288 or full min 288 execution
- export/live/final promotion
- A3/promotion/export/live/final path modification
- `git add -A`
- staging dashboard 7 files, `.gjc`, or unrelated `.omo` residue

## Completion Criteria

This page is complete only when:

- selected candidate count is between 1 and 8
- generated seed JSON has valid `seed_lattice_seeds_v1` schema
- static gate status is `pass`
- DB registration dry-run status is `dry_run_ok`
- inserted seed count and row count are both `0`
- no replay/OOS/portfolio/Plan D R3 action was executed
- scoped verification passes or any failure is documented as a blocker
- a handoff describes the next approved page

## Expected Next Page

If this page passes, the next page should request explicit approval for one of these paths:

- DB INSERT-only apply for the generated body seeds, still with no replay
- a separately bounded limited replay preflight after DB apply
- stop and redesign the body templates before any DB apply
