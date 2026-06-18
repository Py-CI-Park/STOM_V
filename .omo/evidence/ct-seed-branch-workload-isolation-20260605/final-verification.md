# Final Verification

Status: `complete`

## Verdict

`CT_BUY_BRANCH_WORKLOAD`

The page completed its goal. It isolated the same-window timeout to the C_T buy side, with the active window statically mapped to the pre-`09:05` buy branch.

## Runtime Evidence

| Pair | Result |
|---|---|
| C_T buy + control sell | wrapper `ok`, elapsed `177.258s`, warm backtest `error`, timeout `120s`, `csv=no` |
| control buy + C_T sell | wrapper `ok`, elapsed `51.979s`, backtest `success`, CSV path present, profit `149,567`, trades `1`, MDD `2.99` |

## Cleanup

Artifact: `.omo/evidence/ct-seed-branch-workload-isolation-20260605/final-diagnostic-row-cleanup.json`

Temporary rows deleted:

- `stockbuy.CT_DIAG_CTB_902905_20260605`
- `stocksell.CT_DIAG_CTS_902905_20260605`
- `stockbuy.CT_DIAG_CTLB_902905_20260605`
- `stocksell.CT_DIAG_CTLS_902905_20260605`

Cleanup status: `ok`, remaining rows: none.

## Verification Commands

| Command | Result |
|---|---|
| `python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q` | `22 passed in 9.61s` |
| `python -m pytest tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q` | `2 passed in 0.65s` |
| `python scripts/verify_nonrelease_sync.py` | pass |
| `git diff --check` | pass; line-ending warnings only |
| `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json` | no output |

## Boulder

- Work id: `ct-seed-branch-workload-isolation-20260605`
- Status: `completed`
- Completed at: `2026-06-05T20:00:21.0478602+09:00`

## Remaining Blocks

- No January retry yet.
- No 2023-2025 training yet.
- No 2022/2026 OOS yet.
- No human-level, seed-superior, final/export/live/V3K claim.

The next page should repair or ablate the C_T buy first-branch condition family and prove a passing bounded preflight before any larger run.
