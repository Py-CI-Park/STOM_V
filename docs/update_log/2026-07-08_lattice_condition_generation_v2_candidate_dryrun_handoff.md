# Lattice Condition Generation V2 Candidate Dry-Run Handoff

????: 2026-07-08T11:01:22+09:00

## Scope

This page executed only the v2 candidate metadata dry-run. It did not generate STOM buy/sell bodies, did not apply DB inserts, and did not run any replay/OOS/portfolio/Plan D R3 path.

## Results

| Item | Result |
|---|---:|
| Candidate count | 32 |
| coverage_composite | 8 |
| risk_balanced_composite | 8 |
| survivor_seed_derivative | 8 |
| negative_control | 4 |
| holdout_control | 4 |
| Static gate | pass |
| DB registration dry-run | dry_run_ok |
| DB inserted rows | 0 |
| Backtest/OOS/portfolio | not executed |

## Artifacts

- Source read receipt: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_source_read_receipt_20260708.json`
- Candidate ledger JSONL: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_ledger_20260708.jsonl`
- Candidate ledger JSON: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_ledger_20260708.json`
- Pairs dry-run JSON: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\pairs_lattice_v2_candidate_dryrun_20260708.json`
- Name mapping dry-run JSONL: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_strategy_name_mapping_dryrun_20260708.jsonl`
- Static gate receipt: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_static_gate_receipt_20260708.json`
- DB registration dry-run receipt: `docs\research\condition_research\generated_conditions\lattice_v2_candidate_dryrun_20260708\lattice_v2_candidate_db_registration_dryrun_receipt_20260708.json`
- ULW C001 evidence: `.omo\ulw-loop\evidence\20260708_lattice_generation_v2_candidate_dryrun\C001_candidate_ledger_receipt.json`
- ULW C002 evidence: `.omo\ulw-loop\evidence\20260708_lattice_generation_v2_candidate_dryrun\C002_static_db_dryrun_boundary_receipt.json`
- ULW C003 evidence: `.omo\ulw-loop\evidence\20260708_lattice_generation_v2_candidate_dryrun\C003_final_verification_receipt.json`
- Manual QA note: `.omo\evidence\20260708_lattice_generation_v2_candidate_dryrun-manual-qa.md`
- Slop/programming no-op note: `.omo\evidence\20260708_lattice_generation_v2_candidate_dryrun-slop-noop.md`

## Boundary Decision

No next execution is unlocked by this page. The candidates are metadata-only. A separate approved page is required before any of the following: STOM condition body generation, DB INSERT apply, limited replay, OOS, portfolio, Plan D R3, export/live/final promotion.

## Recommended Next Command

```text
$ulw-loop docs/research/condition_research/plans/lattice_condition_generation_v2_body_generation_static_dryrun_20260708.md
```

Recommended next scope: select a small subset from this 32-candidate metadata ledger, generate STOM buy/sell bodies for that subset only, run syntax/static gate and DB registration dry-run only. Do not apply DB inserts until that page passes and receives explicit approval.
