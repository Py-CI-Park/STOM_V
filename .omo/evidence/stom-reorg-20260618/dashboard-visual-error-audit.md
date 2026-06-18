# Dashboard Visual, Error, And Inefficiency Audit

Generated: 2026-06-18T22:55:14+09:00  
Plan page: 11  
Evidence: `dashboard-static-gates.txt`, `dashboard-curl-smoke.txt`, frontend line-count audit.

## Static And Runtime Gate Result

| Gate | Result | Evidence |
|---|---|---|
| `node build-app.mjs` | PASS | Bundle build completed with `app.js v=b1f110fd`, `stom-ui.js v=f41f5701`. |
| `node track-z-harness.mjs` | PASS after declared devDependency install | Initial `jsdom` missing; `npm install` in `webui-build` installed declared dev deps; rerun `allPass=true`. |
| `node check-missing-imports.mjs` | PASS | 65 modules scanned, zero missing cross-module imports. |
| `/ui/` curl smoke | PASS | HTTP 200, dashboard HTML served. |
| `/research_records` curl smoke | PASS | HTTP 200, 17 campaign index payload served. |
| `/evolution_gui_parity?run_id=&gen_no=-1` curl smoke | PASS | HTTP 200, graceful `invalid_request` JSON payload. |

## HTML/DOM Visual Artifacts

Screenshots were not required for this audit range because the plan accepts screenshots or HTML artifacts. The following HTML/DOM artifacts were captured:

| Surface | Artifact | Visual/error status |
|---|---|---|
| Main dashboard shell | `/ui/` HTML response, 2225 bytes | Served successfully. |
| Evolution tab | Track Z V3 jsdom DOM, rootHtmlLen 87048 | Non-empty, no error boundary, no dynamic require errors. |
| Backtest tab | Track Z V3 jsdom DOM, rootHtmlLen 12360 | Non-empty, no error boundary, no dynamic require errors. |
| Simulation tab | Track Z V3 jsdom DOM, rootHtmlLen 9700 | Non-empty, no error boundary, no dynamic require errors. |
| Lab tab | Track Z V3 jsdom DOM, rootHtmlLen 8564; V4 standalone lab rootHtmlLen 4280 | Non-empty in both modes. |
| Pro tab | Track Z V3 jsdom DOM, rootHtmlLen 7121; V4 standalone pro rootHtmlLen 2835 | Non-empty in both modes. |
| Verdict tab | Track Z V3 jsdom DOM, rootHtmlLen 5428; V4 standalone verdict rootHtmlLen 1142 | Non-empty in both modes. |
| Process tab | Track Z V3 jsdom DOM, rootHtmlLen 4457, iframePresent=true | Non-empty iframe shell, no errors. |
| Research Records panel | `/research_records` HTTP payload | Served 17 campaigns; panel contract is present in frontend tests. |
| Evolution GUI Parity panel | `/evolution_gui_parity?run_id=&gen_no=-1` HTTP payload | Graceful invalid request; panel contract is present in frontend tests. |

## Frontend File Size / Inefficiency Audit

No `ai_strategy_loop/dashboard/frontend/*.jsx` file exceeds 800 lines.

Largest files:

| Lines | File | Status |
|---:|---|---|
| 754 | `sim-live-chart.jsx` | Near threshold; monitor before adding features. |
| 737 | `phase-detail.jsx` | Near threshold; process-flow code is still under limit. |
| 733 | `bt-equity-charts.jsx` | Near threshold. |
| 707 | `chart-backtest-detail.jsx` | Near threshold. |
| 701 | `conn-backend.jsx` | Near threshold. |
| 699 | `app.jsx` | Under threshold; central shell still sizable. |
| 670 | `bt-tab-run.jsx` | Under threshold. |
| 621 | `rp-heatmap.jsx` | Under threshold after prior split. |

## Severity-Ranked Findings

| Severity | Finding | Evidence | Recommended action |
|---|---|---|---|
| P0 | No blocking render/import/API failure found in audited gates. | Build PASS, Track Z allPass=true, missing imports OK, curl smoke 200. | None. |
| P1 | Tooling dependency setup is not self-evident. | Track Z initially failed because `jsdom` was declared but not installed locally. | Add a documented preflight command or CI step for `webui-build/npm install`; also review npm audit findings. |
| P1 | Research knowledge surfaces are fragmented. | Research Records, Research Wiki/docs, update logs, and `.omo/evidence` registry all exist separately. | First implementation slice should create a governed index/navigation bridge. |
| P1 | Similar API route names can confuse operators. | `/equity_curves` and `/equity_curve`; `/portfolio_sim` and `/portfolio_preview`. | Add route contract notes and consider canonical aliases after payload audit. |
| P2 | Several frontend modules are close to 800 lines. | `sim-live-chart.jsx` 754, `phase-detail.jsx` 737, `bt-equity-charts.jsx` 733. | Avoid adding more logic to these files; extract helpers only when changing behavior. |
| P2 | Empty/loading/error states are repeated across panels. | Multiple panel-local `Demo mode`, warning, loading states. | Introduce small shared display helpers in a later UX cleanup. |
| P2 | HoF label overlap can look duplicated to users even though behavior diverges. | Field-diff docs classify HoF surfaces as divergent-by-design. | Add source/purpose labels rather than merge components. |

## Page 11 Acceptance Notes

- Required commands were run and captured.
- Live endpoint smoke was run against a temporary uvicorn server.
- `/research_records` and `/evolution_gui_parity?run_id=&gen_no=-1` returned HTTP 200.
- The audit used HTML/DOM artifacts rather than screenshots.
