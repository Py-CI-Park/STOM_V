# 2026-06-29 Ultragoal G002 V2/V3 baseline inventory

## Evidence summary
- Strict V2/V3 visual-route compare status: `PASS`; average corrected score `100.0`.
- Inventory gate status: `passed` with `81` inventoried route/function/section/button/chart/table/safety items across `audit, backtest, chart_replay, condition, history, lab, process, shell, workbench`.
- Forbidden network scan status: `PASS`; findings `0`; forbidden patterns `/bt/run, /bt/ws_job, /sim/ws, /order, /orders, /broker/login, /account/trade, /live_order`.
- V2 remains the default dashboard route family (`/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`) and loads `/ui/bundle/app.js`.
- V3 remains explicit/selectable (`/ui/remodel/*` or `?dashboard_version=v3`) and loads `/ui/remodel/src/app.js`; V2 does not silently become V3.
- Unknown remodel deep links fail closed with HTTP 404 instead of falling back into a shell that masks broken links.

## Per-page route and score matrix
| ID | Page | V2 default route | V3 explicit route | Total | Inventory | Safety/network | Status |
|---|---|---|---|---:|---:|---:|---|
| `01_condition_ai` | `condition` | `/ui/evolution` | `/ui/remodel/condition?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `02_process` | `process` | `/ui/evolution/process` | `/ui/remodel/process?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `03_history` | `history` | `/ui/evolution/records` | `/ui/remodel/history?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `04_lab` | `lab` | `/ui/evolution/lab` | `/ui/remodel/lab?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `05_workbench` | `workbench` | `/ui/evolution/workbench` | `/ui/remodel/workbench?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `06_decision_audit` | `audit` | `/ui/evolution/verdict` | `/ui/remodel/audit?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `07_backtest` | `backtest` | `/ui/backtest` | `/ui/remodel/backtest?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |
| `08_chart_replay` | `chart_replay` | `/ui/chart-replay` | `/ui/remodel/chart-replay?demo=reference` | 100.0 | 100.0 | 100.0 | `PASS` |

## Artifacts
- `compareScorecard`: `artifacts/ultragoal-g002-baseline-compare/compare-scorecard.json`
- `contactSheet`: `artifacts/ultragoal-g002-baseline-compare/side-by-side-contact-sheet.png`
- `domInventory`: `artifacts/ultragoal-g002-baseline-compare/dom-inventory.json`
- `forbiddenNetworkScan`: `artifacts/ultragoal-g002-baseline-compare/forbidden-network-scan.json`
- `routeVersionMatrix`: `artifacts/ultragoal-g002-baseline-compare/route-version-matrix.json`
- `screenshots`: eight V2/V3 screenshot pairs under `artifacts/ultragoal-g002-baseline-compare/`.

## Source change confirmed in this story
- `ai_strategy_loop/dashboard/app.py`: remodel static delivery now mounts explicit static subdirectories (`src`, `styles`, `docs`, `data`) so deep-link pages reach the FastAPI remodel route handler.
- `tests/unit/test_dashboard_route_parity.py`: coverage asserts all known `/ui/remodel/*` deep links return the V3 remodel shell and static assets still resolve.

## Commands run
```powershell
python scripts/verify_dashboard_v2_v3_compare.py --v2-base-url http://127.0.0.1:8770 --v3-base-url http://127.0.0.1:8776 --out artifacts/ultragoal-g002-baseline-compare --timeout-ms 60000
python scripts/verify_dashboard_inventory_gate.py --inventory artifacts/dashboard-v2-v3-inventory/v2-v3-inventory.json --route-matrix artifacts/ultragoal-g002-baseline-compare/route-version-matrix.json --out artifacts/ultragoal-g002-baseline-compare/inventory-gate-result.json
pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_remodel_static.py -q
python -m py_compile ai_strategy_loop/dashboard/app.py
```

## G002 conclusion
G002 baseline inventory is complete: the live worktree has direct evidence for every required route, route ownership remains selectable instead of silently replacing V2, and the V3 remodel route family is ready for the later interactive chart and UX/UI rebuild stories.
