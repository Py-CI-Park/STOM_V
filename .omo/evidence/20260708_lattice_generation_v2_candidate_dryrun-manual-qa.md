# Manual QA: 20260708 Lattice Generation V2 Candidate Dry-Run

Status: PASS

Checked at: 2026-07-08T11:16:38+09:00

## Outcome

- Candidate ledger has 32 metadata-only records.
- Class counts are coverage_composite=8, risk_balanced_composite=8, survivor_seed_derivative=8, negative_control=4, holdout_control=4.
- No condition body, buy code, or sell code is present in the candidate metadata.
- Static gate receipt is pass.
- DB registration dry-run receipt is dry_run_ok with inserted_row_count=0.
- Protected path status is clean.
- DB apply, replay, OOS, portfolio, and Plan D R3 were not executed.

## Commands Reflected In C003

- python -m pytest tests/unit/test_register_lattice_seeds.py -q
- python scripts/verify_nonrelease_sync.py
- git diff --check -- <candidate dry-run scoped paths>
- git diff --cached --name-only
- git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
- PowerShell ConvertFrom-Json parse of ULW goals.json
