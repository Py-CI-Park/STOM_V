# UI KNOWLEDGE BASE

## OVERVIEW
`ui/` owns the PyQt desktop UI, MainWindow wiring, dialogs, charts, and pyd-derived wrapper parity. It is the highest-risk area for accidental runtime contract drift.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Main desktop class | `ui_mainwindow.py` | `stom.py` instantiates `MainWindow`. |
| Strategy activation | `ui_activated_stg.py` | shared stock/coin activation wrapper logic. |
| Backtest activation | `ui_activated_back.py` | UI backtest path and DB/process wiring. |
| Misc activation | `ui_activated_etc.py` | order/dialog/helper activation actions. |
| Backtest UI process | `ui_backtest_engine.py` | mirrors CLI queue/process contracts. |
| Charts | `ui_chart.py` | charting and visualization surface. |
| Process alive | `ui_process_alive.py` | runtime child-process status checks. |

## CONVENTIONS
- Treat upstream pyd behavior as a Python wrapper contract, not as permission to add `.pyd` files.
- Preserve `ui_mainwindow.py` imports and MainWindow parity fields expected by `verify_pyd_gui_contract.py`.
- `sactivated_*` and `cactivated_*` aliases should resolve through common `activated_XX(self, 'stock'/'coin')` style behavior where applicable.
- Keep shutdown, dialog geometry, child cleanup, and Telegram/WebCrawling runtime contracts stable.

## ANTI-PATTERNS
- Do not add serial-key UI or settings behavior in this branch family.
- Do not add unapproved KHOPENAPI connect/login or live-order wiring as part of GUI changes.
- Do not remove legacy bindings without updating contract tests and verification scripts.

## COMMANDS
```powershell
pytest tests/unit/test_verify_pyd_gui_contract.py tests/unit/test_smoke_offline_gui.py -q
python scripts/verify_pyd_gui_contract.py
python scripts/smoke_offline_gui.py
python scripts/verify_nonrelease_sync.py
```

## LOCAL GOTCHAS
- Many files are legacy handler splits; search for paired stock/coin behavior before changing only one side.
- GUI changes can break smoke tests without syntax errors, so run the contract verifier.
- Avoid broad formatting passes in large UI files.
