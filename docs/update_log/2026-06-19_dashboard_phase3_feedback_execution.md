# Dashboard Phase 3 Feedback Execution

Date: 2026-06-19
Branch: `lazycodex/dashboard-ui-phase3-feedback-20260619`
Plan: `.gjc/plans/ralplan/2026-06-19-0146-569c/pending-approval.md`

## Scope

Executed the approved phase 3 dashboard feedback plan for the STOM AI condition-evolution dashboard. The change stays inside the dashboard/control-plane surface and excludes V3K/live broker/order/export/final approval/strategy DB/protected runtime path/new dependency changes.

## Implemented

- Settings/config source of truth:
  - MDD default/max set to 40.
  - `min_daily_trades` is presented as the primary frequency gate and `min_trades` as fallback.
  - Objective/fitness formulas, feedback window, date window, resource defaults, seed selectors, and DB min/max blank-date help are exposed through `/config/spec`.
  - GPT 5.5/xhigh is presented as a guarded option.
- GPT auth safety:
  - Read-only auth status/test surface reports safety and credential/proxy state.
  - Auth test does not start evolution and does not export/final-approve/order/write strategy DB.
- Dashboard IA and page ownership:
  - Route labels are horizontal and user-facing: `진화 홈`, `프로세스`, `백테스트 검증`, `차트 리플레이`, `기록 검색`, `연구실`, `분석 워크벤치`, `결정 감사`.
  - Evolution home acts as the hub and links subordinate evidence/operation surfaces without changing stable route keys.
  - Records is the governed search/index surface; Lab is wiki/context/run-analysis. Duplicate research-index presentation was removed.
- Process/observability:
  - Process page now shows current step, plain Korean explanation, live strip, timing grid, latest logs, and `/process_flow` iframe compatibility.
  - Backtest/replay/process/records/lab/pro/verdict summaries are discoverable from the main dashboard.
- Tests and bundle:
  - Bundle rebuilt as `bundle/app.js?v=089ac794`.
  - Unit/static/browser contracts were extended for config/spec, GPT auth, process, route labels, Records/Lab separation, and browser-render safety.

## Verification evidence

- `node ai_strategy_loop/dashboard/webui-build/build-app.mjs` -> `app.js v=089ac794`, HTML unchanged after rebuild.
- `python -m pytest tests/unit/dashboard tests/unit/test_dashboard*.py tests/unit/test_launch_config.py -q -k "not committed_bundle_in_sync"` -> `887 passed, 1 deselected`.
- `node check-missing-imports.mjs` -> zero missing cross-module imports.
- `node track-z-harness.mjs` -> V1/V2/V3/V4/V5/V6 all pass, `allPass: true`.
- `python scripts/verify_nonrelease_sync.py` -> all nonrelease checks passed.
- `git diff --check` -> clean except line-ending warning for `dashboard-inventory.jsx`.
- Protected runtime path status -> no dirty protected/runtime paths.
- Browser QA on `http://127.0.0.1:8875/ui/?check=phase3-current`:
  - served `bundle/app.js?v=089ac794`;
  - zero console errors;
  - all eight dashboard tabs clicked and rendered;
  - process flow/live strip/timing grid present;
  - `/config/spec`, `/status`, `/health`, `/gpt_auth/status` returned 200;
  - GPT auth status reported `safe=true` and `starts_evolution=false`.
  - screenshot: `.gjc/ultragoal/artifacts/dashboard-phase3-current-browser-qa.png`.

## 8770 handoff status

Port `8770` is currently owned by a preserved `wt-dev` process (`python -m ai_strategy_loop --port 8770`, cwd `C:\System_Trading\STOM\STOM_V.wt-dev`) and serves the older `bundle/app.js?v=b1f110fd`. The phase 3 branch was validated on exact-worktree preview port `8875`. Replacing the 8770 process requires an explicit handoff/restart of the preserved `wt-dev` runtime.

## Completion maturity

The implementation and verification surfaces are mature enough for PR review, but the whole page/release flow is not 100% until the 8770 handoff/restart and PR merge are completed.
