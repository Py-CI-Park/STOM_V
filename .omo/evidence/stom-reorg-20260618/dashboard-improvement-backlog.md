# Dashboard Improvement Backlog

Generated: 2026-06-18T22:55:14+09:00  
Plan page: 12  
Input evidence: `dashboard-inventory.md`, `dashboard-duplicate-audit.md`, `dashboard-visual-error-audit.md`.

## Ranked Backlog

| Rank | Item | Severity | Risk | Research value | Action |
|---:|---|---|---|---|---|
| 1 | Governed research knowledge index | P1 | Medium | Very high | Connect Research Records, Research Wiki/docs, update logs, and `.omo` registry into one navigable research-management flow. |
| 2 | Tooling preflight for dashboard QA | P1 | Low | High | Document or script `webui-build/npm install` + build/harness/missing-import sequence; capture npm audit as tooling risk. |
| 3 | Route naming contract audit | P1 | Medium | Medium | Compare `/equity_curves` vs `/equity_curve`, `/portfolio_sim` vs `/portfolio_preview`, and mark canonical routes. |
| 4 | Research Records/Wiki navigation bridge | P1 | Medium | Very high | Add cross-links from campaign records to docs/evidence/update logs; keep panels separate initially. |
| 5 | GUI parity UX clarity | P2 | Low | High | Add clearer source labels for evolution GUI parity and backtest GUI parity while preserving shared `BtGuiParitySection`. |
| 6 | HoF purpose labels | P2 | Low | Medium | Label evolution HoF vs Research Pro HoF as different jobs to reduce perceived duplication. |
| 7 | Shared empty/loading/error micro-components | P2 | Medium | Medium | Reduce inconsistent panel states without merging domain components. |
| 8 | Near-threshold module watchlist | P2 | Low | Medium | Prevent `sim-live-chart.jsx`, `phase-detail.jsx`, `bt-equity-charts.jsx`, `chart-backtest-detail.jsx`, and `conn-backend.jsx` from absorbing unrelated logic. |
| 9 | Standalone page/cache alignment check | P2 | Low | Medium | Keep `lab/pro/verdict` standalone pages and SPA tabs in sync through Track Z and versioned bundle checks. |
| 10 | API contract docs for research dashboard | P2 | Medium | High | Document route owners, payload intent, and UI consumers for every dashboard route. |

## First Implementation Slice

Recommended first slice: **Research knowledge index and navigation bridge**.

Purpose:
- Make current and future condition-expression research easier to manage.
- Reduce confusion between evidence artifacts, update logs, Research Records, and Research Wiki.
- Avoid risky component merging while still giving the operator one research-management path.

Candidate file list:
- `ai_strategy_loop/dashboard/research_api.py`
- `ai_strategy_loop/dashboard/research_records.py`
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/research-wiki.jsx`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- `tests/unit/dashboard/test_research_records.py`
- `tests/unit/dashboard/test_research_records_frontend.py`
- New or updated dashboard route contract tests if route payloads change.
- `.omo/evidence/stom-reorg-20260618/research-registry.*` only if the registry schema is deliberately extended.

Implementation boundaries:
- Do not merge HoF surfaces in this slice.
- Do not change V3K gates, live broker runtime, `_database`, order wiring, or feature flags.
- Do not make research record indexing depend on protected runtime DB paths.
- Keep additions small enough that no frontend file crosses 800 lines.

Expected tests/manual QA:
- `pytest tests/unit/dashboard/test_research_records.py -q`
- `pytest tests/unit/dashboard/test_research_records_frontend.py -q`
- `cd ai_strategy_loop/dashboard/webui-build; node build-app.mjs`
- `cd ai_strategy_loop/dashboard/webui-build; node track-z-harness.mjs`
- `cd ai_strategy_loop/dashboard/webui-build; node check-missing-imports.mjs`
- Temporary uvicorn smoke: `/ui/`, `/research_records`, `/evolution_gui_parity?run_id=&gen_no=-1`

Rollback plan:
- Revert only the explicitly touched research dashboard files.
- Rebuild `frontend/bundle/app.js` with `node build-app.mjs` if frontend files were changed.
- Re-run the three webui gates and curl smoke.
- Leave unrelated dirty/untracked research artifacts untouched.

## User-Decision Items

| Decision | Default recommendation | Reason |
|---|---|---|
| Should HoF surfaces be merged? | No | Existing field diff shows divergent jobs and columns. Add labels instead. |
| Should standalone `lab/pro/verdict` pages remain? | Yes | Track Z V4 validates them and they preserve direct-link compatibility. |
| Should research docs use manual allowlist or generated registry? | Move toward generated/governed registry | Manual exposure is already a visibility bottleneck. |
| Should npm audit findings be fixed now? | Not in this slice | `npm audit fix --force` can introduce breaking build-tool upgrades; handle as separate tooling task. |
| Should route aliases be changed immediately? | Audit first | Dashboard consumers may depend on current route names. |

## Recommended Next Page Range

Proceed with plan pages 13~16 after user confirmation:
- Page 13: branch/PR execution template.
- Page 14: first implementation-slice checklist.
- Page 15: validation and regression gate matrix.
- Page 16: operational handoff and next research-management loop.
