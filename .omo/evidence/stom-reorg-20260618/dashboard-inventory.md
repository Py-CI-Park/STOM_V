# Dashboard Inventory

Generated: 2026-06-18T22:55:14+09:00  
Plan page: 9  
Scope: `ai_strategy_loop/dashboard` backend routes and `ai_strategy_loop/dashboard/frontend` SPA tabs/panels.

## STOM_TABS Coverage

Source check: `ai_strategy_loop/dashboard/frontend/app.jsx` defines 7 `STOM_TABS` entries.

| Tab key | Label | Inventory status | Notes |
|---|---|---:|---|
| `evolution` | 진화 대시보드 | Covered | Main AI condition evolution cockpit. |
| `backtest` | 백테스트 | Covered | Backtest workbench. |
| `simulation` | 차트 시뮬레이션 | Covered | Chart replay/simulation shell. |
| `lab` | 연구실 | Covered | In-SPA Research Lab page. |
| `pro` | 분석 프로 | Covered | In-SPA Research Pro page. |
| `verdict` | 결정 이력 | Covered | In-SPA decision/verdict page. |
| `process` | 프로세스 흐름 | Covered | Iframe-backed process flow page. |

Result: 7/7 tabs have inventory rows below. Required route coverage explicitly includes `/research_records` and `/evolution_gui_parity`.

## Tab And Major Panel Inventory

| Surface | Owner file | Endpoint/data source | Known test/docs | Status |
|---|---|---|---|---|
| SPA shell/tab nav | `frontend/app.jsx` | `/ui/` static mount, `STOM_TABS` | `tests/unit/dashboard/test_track_z_pr1_harness.py`, Track Z harness | Active |
| Evolution: run monitor | `frontend/app.jsx`, `frontend/panels-status.jsx`, `frontend/phase-detail.jsx`, `frontend/engine.jsx` | `/status`, WebSocket `/ws`, `/config/spec`, `/research_criteria` | `tests/unit/test_dashboard_integrated_layout.py`, `tests/unit/test_dashboard_live_demo_split.py` | Active |
| Evolution: Research Records | `frontend/research-records-panel.jsx` | `/research_records`, `/research_records/detail` | `tests/unit/dashboard/test_research_records.py`, `tests/unit/dashboard/test_research_records_frontend.py` | Active; required coverage present |
| Evolution: fitness/profit/equity | `frontend/chart.jsx`, `frontend/chart-equity.jsx`, `frontend/chart-primitives.jsx` | `/equity_curves`, `/equity_curve`, `/status` generations | `tests/unit/test_dashboard_integrated_layout.py` | Active |
| Evolution: backtest detail | `frontend/chart-backtest-detail.jsx` | `/backtest_detail`, selected run/gen | dashboard unit coverage through layout/harness | Active |
| Evolution: GUI parity | `frontend/evolution-gui-parity-panel.jsx`, `frontend/bt-gui-parity.jsx` | `/evolution_gui_parity?run_id=&gen_no=` | `tests/unit/dashboard/test_evolution_gui_parity.py`, `tests/unit/dashboard/test_research_records_frontend.py` | Active; required coverage present |
| Evolution: Hall of Fame | `frontend/chart-hall-of-fame.jsx`, `frontend/chart.jsx` | `/hall_of_fame`, `/reference_screenshots` | `tests/unit/test_dashboard_hall_of_fame.py`, `docs/web_dashboard_expansion/PROG_P7_FIELD_DIFF.md` | Active; divergent from Research Pro HoF by design |
| Evolution: strategy/prompt/code | `frontend/table.jsx`, `frontend/code-viewer.jsx`, `frontend/strategy-inspector.jsx`, `frontend/ai-context.jsx` | `/strategy_code`, `/prompts`, `/strategy_diff`, `/ai_context_pack` | layout/harness coverage | Active |
| Evolution: run compare | `frontend/run-compare.jsx` | `/runs`, `/runs/compare` | `tests/unit/test_dashboard_live_demo_split.py`, `tests/unit/dashboard/test_no_duplicate_globals.py` | Active canonical implementation |
| Evolution: analysis pack | `frontend/analysis.jsx`, `frontend/evolution-analysis.jsx`, `frontend/panels-analysis.jsx` | `/autopsy`, `/selector_preview`, `/counterfactual`, `/freeze_mc`, `/adaptive_timing`, `/edge_ratio`, `/feature_importance`, `/time_profit`, `/run_log`, `/variable_correlation` | dashboard layout/harness tests | Active |
| Evolution: embedded Research Lab | `frontend/rl-panel.jsx`, `frontend/research-lab.jsx`, `frontend/rl-analysis.jsx`, `frontend/rl-validation.jsx` | `/tmap_grid`, `/tmap_map`, `/pipeline_status`, `/research_docs`, `/research_doc`, `/index_compare` | `tests/unit/dashboard/test_research_pro.py`, docs expansion records | Active |
| Evolution: embedded Research Pro | `frontend/rp-panel.jsx`, `frontend/research-pro.jsx`, `frontend/rp-heatmap.jsx`, `frontend/rp-utils.jsx` | `/niche_compare`, `/portfolio_sim`, `/portfolio_preview`, `/regime_report`, `/revival_registry`, `/pipeline_status` | `tests/unit/dashboard/test_research_pro.py`, `tests/unit/dashboard/test_p3_consolidation.py` | Active |
| Backtest tab | `frontend/backtest.jsx`, `frontend/bt-tab-root.jsx`, `frontend/bt-tab-*.jsx` | router from `dashboard/backtest_api.py`, `/backtest_detail`, GUI parity payloads | backtest dashboard unit tests, Track Z V3 | Active |
| Backtest charts/parity | `frontend/backtest-charts.jsx`, `frontend/bt-*.jsx`, `frontend/bt-gui-parity.jsx` | backtest analysis payloads, GUI parity section | `tests/unit/dashboard/test_evolution_gui_parity.py` indirectly for shared section | Active shared helper |
| Simulation tab | `frontend/simulation.jsx`, `frontend/sim-tab-root.jsx`, `frontend/sim-*.jsx` | router from `dashboard/simulation_api.py`, simulation chart state | Track Z V3 | Active |
| Lab standalone/In-SPA page | `frontend/dashboard-pages.jsx`, `frontend/index/lab.html`, `frontend/lab.html` | `/research_docs`, `/research_doc`, `/index_compare`, research state | Track Z V4 standalone lab | Active |
| Pro standalone/In-SPA page | `frontend/dashboard-pages.jsx`, `frontend/index/pro.html`, `frontend/pro.html` | `/niche_compare`, `/portfolio_*`, `/run_yearly`, `/hall_of_fame` subset | Track Z V4 standalone pro | Active |
| Verdict standalone/In-SPA page | `frontend/dashboard-pages.jsx`, `frontend/index/verdict.html`, `frontend/verdict.html` | `/decisions`, `/record_decision`, `/freeze_verdict`, `/portfolio_verdict` | Track Z V4 standalone verdict | Active |
| Process tab/page | `frontend/phase-detail.jsx`, `docs/process_flow.html`, `ai_strategy_loop/scripts/build_process_flow_html.py` | `/process_flow`, live `/status` state | `tests/unit/dashboard/test_p11_process_flow.py`, Track Z V3 process iframe | Active |

## Backend Route Inventory

| Route group | Owner file | Routes observed | Status |
|---|---|---|---|
| App shell/static | `dashboard/app.py` | `/`, `/ui`, `/health`, `/process_flow`, WebSocket `/ws` | Active |
| Evolution core | `dashboard/app.py` | `/status`, `/config/spec`, `/research_criteria`, `/equity_curves`, `/equity_curve`, `/runs`, `/runs/compare`, `/run_state`, `/generation_durations`, `/run_yearly` | Active |
| Evaluation/decision | `dashboard/app.py` | `/hall_of_fame`, `/reference_screenshots`, `/freeze_verdict`, `/portfolio_verdict`, `/decisions`, `/record_decision` | Active |
| Research analytics | `dashboard/app.py` | `/ops_status`, `/portfolio_sim`, `/portfolio_preview`, `/regime_report`, `/revival_registry`, `/pipeline_status`, `/niche_compare`, `/tmap_grid`, `/tmap_map` | Active |
| Generation analysis | `dashboard/app.py` | `/autopsy`, `/selector_preview`, `/counterfactual`, `/freeze_mc`, `/strategy_code`, `/prompts`, `/strategy_diff`, `/ai_context_pack`, `/backtest_detail`, `/adaptive_timing`, `/edge_ratio`, `/feature_importance`, `/time_profit`, `/run_log`, `/variable_correlation` | Active |
| Research docs/records | `dashboard/research_api.py` | `/research_docs`, `/research_doc`, `/research_records`, `/research_records/detail`, `/evolution_gui_parity`, `/index_compare` | Active; required coverage present |

## Immediate Inventory Findings

1. Research Records and Evolution GUI Parity are not separate top-level tabs; both are major panels inside the `evolution` tab.
2. HoF has two active surfaces: canonical evolution HoF and Research Pro HoF. Existing field-diff evidence classifies this as divergent-by-design, not a blind duplicate.
3. Frontend file size audit found no `.jsx` file above 800 lines. Largest files: `sim-live-chart.jsx` 754, `phase-detail.jsx` 737, `bt-equity-charts.jsx` 733, `chart-backtest-detail.jsx` 707, `conn-backend.jsx` 701.
4. Research docs, research records, and update logs are related but not yet a single governed knowledge index.
