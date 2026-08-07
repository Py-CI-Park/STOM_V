## Summary
G001 is clear for inventory/prep completion only: the baseline is clean, the focused dashboard tests passed, and the route/static/read-only risk map is grounded in source without product behavior changes. The review finds no blockers to closing G001 as an inventory quality gate; the mapped write/read-only risks must remain blockers for later implementation stories until fixed and tested.

Quality gate verdict: architectureStatus=CLEAR, productStatus=CLEAR, codeStatus=CLEAR, recommendation=APPROVE for G001 inventory completion.

## Analysis
- Baseline/evidence: the assignment records the branch fast-forward to `origin/STOM_Version_2U_C-ai-strategy-loop` at `f8f58d11f40ff43a37ea49d3ccc42ac1ee77b6aa`, restored `docs/process_flow.html` timestamp drift, and `git status --short` containing only untracked `.gjc/` runtime artifacts. I did not mutate product source or run build/lint/formatter gates.
- Test evidence: artifact 752 contains the focused baseline command result: `python -m pytest tests/unit/dashboard/test_loopstate_readonly.py tests/unit/test_dashboard_route_parity.py tests/unit/dashboard/test_p11_process_flow.py -q` => `16 passed in 13.03s`.
- Static/route contract: `ai_strategy_loop/dashboard/app.py` registers API/WS routes before static mounts and mounts `/reference_img` only when `docs/reference/STOM_Good_Results` exists, then mounts `/ui` only when the frontend directory exists (`app.py:3336-3354`). This avoids `/ui` shadowing `/health`, `/status`, `/config/spec`, `/ws`, or `/process_flow`. `app.py:2698-2701` redirects `/` to `/ui/`.
- Process route contract: frontend `app.jsx:296-297` embeds `baseUrl + "/process_flow"`; backend `app.py:2707-2727` serves `/process_flow`. The current implementation regenerates on GET by calling `ai_strategy_loop.scripts.build_process_flow_html.main()` and then reads `docs/process_flow.html`.
- Read-only foundation: `ai_strategy_loop/controller/state.py:72-103` adds `LoopState(readonly=True)`, opening `file:...?mode=ro`, skipping mkdir/PRAGMA/schema migration, and relying on SQLite to reject writes. `tests/unit/dashboard/test_loopstate_readonly.py:1-112` covers existing-data reads, write-attempt failure, no snapshot dir/schema mutation, missing DB not created, and unchanged default write mode.
- Existing safe read-path examples: `ai_strategy_loop/dashboard/backtest_api.py:723-790` uses `LoopState(readonly=True)` for evolution generation reads; `ai_strategy_loop/dashboard/evolution_gui_parity.py:74-75` does the same. `replay_engine.py:89-97`, `simulation_api.py:244-245`, and `backtest_api.py:92-99` use `file:...?mode=ro` for market/code DB reads.
- Remaining dashboard read-path risk inventory: `ai_strategy_loop/dashboard/app.py` still has many read endpoints/helpers that call `LoopState()` in default write-capable mode (search hits at app.py:236, 556, 641, 867, 977, 1057, 1218, 1404, 1534, 1602, 1670, 1743, 1800, 3251). Direct `sqlite3.connect(str(_S.LOOP_RUNS_DB))` read helpers also appear at `app.py:309`, `366`, `451`, and `portfolio_preview` around `app.py:3020`, so these are mapped as later no-write hardening targets.
- Protected/write surface inventory: `/process_flow` GET is the main read-looking mutation because `build_process_flow_html.py:181-183` creates the parent directory and writes `docs/process_flow.html`. Other write/control surfaces are intentional and should stay out of read-only probe scope: WS `start/stop/final_approval` (`app.py:93-144`, `_handle_control`), `POST /record_decision` append-only `.omo/evidence/decisions.jsonl` (`app.py:2431-2477`), `/bt/strategy`, `/bt/strategy/delete`, `/bt/run`, `/bt/job/*` (`backtest_api.py:391-465`, `523+`), optional `/analysis_snapshot?persist=true` (`analysis_snapshot.py:144-184`), and simulation/backtest job execution paths.
- Current route/process/read-only test scope: `tests/unit/test_dashboard_route_parity.py:15-71` probes a focused frontend-called read-only route subset and openapi/route presence; `tests/unit/dashboard/test_p11_process_flow.py:1-139` covers process-flow SVG source contracts and optional JSX transform; `tests/unit/dashboard/test_loopstate_readonly.py:1-112` covers the storage-level read-only contract. This is sufficient for G001 inventory/prep, but not sufficient to certify all dashboard read endpoints as no-write.
- Runtime `.gjc/ultragoal` note: the checked `.gjc/ultragoal/goals.json` currently describes a different completed proxy-OOS G001. Because the assignment explicitly defines the dashboard G001 contract and forbids subagent `.gjc/ultragoal` mutation, I treated the prompt contract and inspected source/test evidence as the scope for this review, not the stale untracked runtime artifact.

## Root Cause
The dashboard evolved read endpoints before `LoopState(readonly=True)` existed, so many helpers still use the default write-capable storage constructor or direct non-URI SQLite opens despite being documented as read-only. Separately, the explanatory process-flow page couples freshness to a GET request, so a display route invokes a generator that writes the tracked `docs/process_flow.html` artifact.

## Findings
1. MEDIUM — `ai_strategy_loop/dashboard/app.py:2707-2727` plus `ai_strategy_loop/scripts/build_process_flow_html.py:181-183`: `/process_flow` is a GET route but calls a generator that writes `docs/process_flow.html`. Impact: browsing the process tab can dirty a tracked docs file and violates a strict read-only dashboard route contract. Fix: make GET serve an existing artifact only, move regeneration to an explicit CLI/admin action, or write generated cache to an ignored runtime path with tests proving GET is non-mutating.
2. MEDIUM — `ai_strategy_loop/dashboard/app.py` search hits at `LoopState()` lines 236/556/641/867/977/1057/1218/1404/1534/1602/1670/1743/1800/3251 and direct `sqlite3.connect(str(_S.LOOP_RUNS_DB))` helpers around 309/366/451/3020: read-labeled endpoints can open `loop_runs.db` in write-capable mode. Impact: reads can create WAL files, run schema migrations, or create state directories depending on call path, undermining protected-path/no-write claims. Fix: convert dashboard read helpers to `LoopState(readonly=True)` or `file:...?mode=ro`, preserving graceful empty responses on missing DB.
3. LOW — `tests/unit/test_dashboard_route_parity.py:15-71`: route parity tests cover only a small frontend-called subset and do not assert no-write side effects for `/process_flow`, `/runs`, `/run_state`, `/generation_durations`, `/equity_curves`, `/bt/evo_gens`, `/reference_screenshots`, or `/analysis_snapshot` default mode. Impact: G001 inventory is complete, but later implementation could regress route coverage unless the test scope is expanded. Fix: add a no-write fixture that snapshots protected paths/mtime and monkeypatches state paths, then probes the full read route list.

## Recommendations
1. Close G001 as inventory/prep with no product source changes; do not claim the dashboard read surface is fully hardened yet.
2. In the next implementation story, first sever `/process_flow` GET from tracked-file regeneration, then add a regression test that a GET does not touch `docs/process_flow.html` or runtime protected paths.
3. Convert all app.py read helpers from default `LoopState()`/plain sqlite opens to `readonly=True` or ro URI; keep intentional write/control routes in a separate allowlist.
4. Expand route parity/no-write tests to cover the actual frontend surfaces and router prefixes: core `/`, `/health`, `/status`, `/config/spec`, `/process_flow`, read analytics routes, `/bt/evo_gens`/read-only `/bt/*`, `/sim/days`/`/sim/stocks`, `/reference_screenshots`, and `/analysis_snapshot` with `persist=false`.
5. Preserve static mount order: API/WS routes first, `/reference_img` and `/ui` mounts last.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Benefit | Cost/Risk | Fit |
|---|---|---|---|
| Serve existing `docs/process_flow.html` on GET only | Strict read-only web route, no tracked drift | Manual/explicit regeneration needed | Best next-step default |
| Regenerate on GET but write ignored runtime cache | Fresh display without tracked drift | More cache invalidation/path policy | Acceptable if freshness is required |
| Keep current regenerate-on-GET | Always latest page | Dirty tracked docs/protected-path surprise | Not acceptable for a no-write contract |
| Use `LoopState(readonly=True)` everywhere read-only | Single storage boundary, tested behavior | Missing DB opens raise and must be caught | Best consistency |
| Keep direct sqlite read opens | Small diff, simple queries | Easy to forget ro URI; WAL/mutation risk | Only acceptable with ro URI wrapper |
