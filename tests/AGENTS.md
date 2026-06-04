# TESTS KNOWLEDGE BASE

## OVERVIEW
`tests/` locks branch contracts for CLI/backtest, GUI/pyd parity, nonrelease sync, research loops, dashboard behavior, and V3K gate safety.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Nonrelease sync | `unit/test_verify_nonrelease_sync.py` | Mirrors `scripts/verify_nonrelease_sync.py`. |
| pyd GUI contract | `unit/test_verify_pyd_gui_contract.py` | MainWindow/import/alias parity. |
| Offline GUI smoke | `unit/test_smoke_offline_gui.py` | Smoke log and GUI probe behavior. |
| CLI runner | `unit/test_runner_helpers.py` | Queue/config handoff contracts. |
| Backtest protocol | `unit/test_backtest_*` | Process diagnostics and spawn contracts. |
| Dashboard | `unit/test_dashboard_*` | AI loop UI/API state behavior. |
| Research | `unit/test_research_*` | candidate generation, optimizer, V3/V4/V5 logic. |
| Worktree policy | `unit/test_worktree_policy.py` | Serial/worktree boundaries. |

## CONVENTIONS
- Prefer focused tests for changed contracts, then run `pytest tests/unit/ -q` for branch propagation/sync work.
- Keep fixtures minimal and deterministic; avoid depending on live broker state or mutable production DBs.
- Do not edit `__pycache__` or generated cache directories.
- If a script contract changes, update the matching unit tests in the same change.

## COMMANDS
```powershell
pytest tests/unit/ -q
pytest tests/unit/test_verify_nonrelease_sync.py tests/unit/test_verify_pyd_gui_contract.py tests/unit/test_smoke_offline_gui.py -q
pytest tests/integration/ -q
```

## LOCAL GOTCHAS
- Several tests assert text markers and script output; update expected strings deliberately.
- Avoid depending on external market sessions, broker logins, or live DB contents.
- Prefer `tmp_path`/fixtures over writing runtime directories.
- If a test needs sample strategy text, keep it minimal and local to the test.
- Contract tests are documentation for branch behavior; read them before changing verifiers.
