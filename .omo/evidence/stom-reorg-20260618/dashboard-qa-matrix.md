# Full Dashboard QA Matrix

Generated: 2026-06-18T23:19:07+09:00  
Plan page: 15  
Status: repeatable QA matrix. Execution artifacts are captured separately in final verification.

## Required Gates

| Gate | Command/artifact |
|---|---|
| Bundle build | `cd ai_strategy_loop/dashboard/webui-build; node build-app.mjs` |
| Runtime harness | `node track-z-harness.mjs` with 7 SPA tabs and 3 standalone pages. |
| Static import guard | `node check-missing-imports.mjs` |
| API smoke | `curl -i /ui/`, `/research_records`, `/evolution_gui_parity?run_id=&gen_no=-1`, `/research_docs` |
| Browser/HTML artifact | Capture evolution, backtest, simulation, lab, pro, verdict, process. |
| Protected cleanup | Stop dashboard server, close browser process, confirm no QA process remains. |

## Viewport And Theme Matrix

| Viewport | Theme | Required check |
|---|---|---|
| 1280x800 | dark | Dense operational layout, no clipped nav or panels. |
| 1280x800 | light | Contrast and table legibility. |
| 1600x1000 | dark | Main operator desktop size. |
| 1600x1000 | light | Light mode parity. |
| 2200x1200 | dark | Wide monitor grid spacing. |
| 390x844 | dark | Mobile overflow and tab wrapping smoke. |

## Route/Tab Matrix

| Surface | Route/action | Expected artifact | Adversarial cases |
|---|---|---|---|
| evolution | `/ui/`, tab `evolution` | screenshot or DOM dump with Research Records and Evolution GUI Parity sections | long candidate name, empty backend, stale localStorage |
| backtest | `/ui/`, tab `backtest` | screenshot or DOM dump with backtest workbench | missing API, no selected run, long code label |
| simulation | `/ui/`, tab `simulation` | screenshot or DOM dump with simulation chart shell | missing chart data, narrow viewport |
| lab | `/ui/`, tab `lab`; standalone `/ui/lab.html` if served | screenshot or DOM dump | research docs missing, light/dark contrast |
| pro | `/ui/`, tab `pro`; standalone `/ui/pro.html` if served | screenshot or DOM dump | HoF overlap labels, empty portfolio payload |
| verdict | `/ui/`, tab `verdict`; standalone `/ui/verdict.html` if served | screenshot or DOM dump | no decisions, disabled actions |
| process | `/ui/`, tab `process`; `/process_flow` | screenshot or DOM dump, iframe or process HTML present | iframe load failure, stale process HTML |
| research records API | `/research_records`, `/research_records/detail` | JSON response preview | malformed campaign id, path traversal rejection |
| GUI parity API | `/evolution_gui_parity?run_id=&gen_no=-1` | graceful invalid_request JSON | invalid run/gen, missing CSV |
| docs API | `/research_docs`, `/research_doc` | JSON/doc preview | missing doc key, prompt-injection-like doc text treated as data |

## Adversarial UI Cases

| Case | Probe | PASS condition |
|---|---|---|
| long candidate | Use known long name `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full`. | Text truncates/wraps without overlapping neighboring cells. |
| missing API | Stop server or request invalid endpoints. | User-facing error/empty state, no JS crash. |
| stale localStorage | Preload invalid tab/collapse keys. | App still renders default tab or recovers. |
| light theme | Toggle or force light class if available. | Contrast remains readable. |
| dark theme | Default dark view. | Dense tables and cards readable. |
| malformed input | API query with empty `run_id`, negative `gen_no`, bad campaign. | HTTP 200 graceful payload or safe 4xx; no server crash. |
| prompt injection text | Treat doc/evidence content as inert text. | No command execution; rendered as text only. |
| hung server | Curl timeout. | QA script times out, records failure, and cleanup still runs. |

## Cleanup Receipts

Every QA run must record:

| Resource | Cleanup |
|---|---|
| temporary uvicorn server | Stop job/process, record port and stop result. |
| browser/Playwright | Close browser context, record artifact count. |
| temp files | Keep only evidence artifacts under `.omo/evidence/stom-reorg-20260618/`; remove transient temp files. |
| protected paths | Run protected status command after QA. |

## Manual QA Output Layout

Recommended artifact root:

```text
.omo/evidence/stom-reorg-20260618/manual-qa/
  curl-smoke-final.txt
  browser-capture-summary.json
  evolution.html
  backtest.html
  simulation.html
  lab.html
  pro.html
  verdict.html
  process.html
  *.png
```

## Page 15 Acceptance Mapping

- Every route/tab is listed: evolution, backtest, simulation, lab, pro, verdict, process.
- Long candidate, missing API, localStorage, light, and dark cases are explicitly included.
- Server/browser cleanup receipts are defined.
