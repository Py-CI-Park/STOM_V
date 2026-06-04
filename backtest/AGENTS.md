# BACKTEST KNOWLEDGE BASE

## OVERVIEW
`backtest/` is the official STOM backtest engine surface. It owns process contracts, engine behavior, optimization, and reports; result data under this tree can be protected.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Main orchestrator | `backtest.py` | `BackTest` child protocol and report flow. |
| Engine base | `backengine_base.py` | Shared engine loop and V3K learning-load hooks. |
| Stock engine | `backengine_stock.py` | Stock-specific backtest behavior. |
| Coin engines | `backengine_coin_*.py` | Upbit/future/strategy coin variants. |
| Optimizer | `optimiz.py`, `optimiz_conditions.py` | Optuna/train-valid/condition optimization paths. |
| Walk-forward | `rolling_walk_forward_test.py` | Rolling train/validation entry. |
| Result data | `graph/`, `csv/`, `temp/` | Treat `graph/` as protected result data. |

## CONVENTIONS
- Preserve argv, queue, and multiprocessing contracts used by `stom_backtest.py`, `cli/runner.py`, and UI backtest paths.
- Backtest changes should be validated with focused unit tests plus `verify_nonrelease_sync.py` when branch contracts are touched.
- Keep diagnostic/protocol messages stable unless tests and downstream consumers are updated together.
- Result/report directories are not general scratch space.

## ANTI-PATTERNS
- Do not delete or rewrite `backtest/graph/`; it is protected result data.
- Do not silently change queue tuple shapes, process spawn signatures, or `BackTest` constructor semantics.
- Do not mix live broker side effects into backtest engines.

## COMMANDS
```powershell
pytest tests/unit/test_backtest* -q
pytest tests/unit/test_runner_helpers.py -q
python scripts/verify_nonrelease_sync.py
```

## LOCAL GOTCHAS
- CSV/report outputs can be large and historical; inspect before assuming they are disposable.
- Optimizer files may be invoked as worker processes, so import-time side effects are risky.
- If changing engine math, capture before/after metrics and explain expected drift.
