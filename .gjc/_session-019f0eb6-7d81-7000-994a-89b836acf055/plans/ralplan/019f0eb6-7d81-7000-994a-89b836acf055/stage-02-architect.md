# Architect Stage 2 Rereview — Revised V2/V3 selectable dashboard rollout plan

## Summary
The stage-02 revision resolves the prior Critic-required fixes: route/version ownership is explicit, visual verification is corrected to V3-on-8776 versus V2-on-8770 with `--out`, the inventory gate is machine-readable, and preview acceptance is separated from promotion/100% acceptance. I recommend APPROVE for execution after explicit human approval; the remaining notes are low-risk execution hardening, not blockers.

## Analysis
Evidence inspected: `stage-02-revision.md`; prior `stage-01-planner.md`, `stage-01-architect.md`, and `stage-01-critic.md`; root `AGENTS.md`; `ai_strategy_loop/AGENTS.md`; `ai_strategy_loop/dashboard/app.py`; V2 and V3 index files; `scripts/verify_dashboard_remodel_visual_gate.py`; `tests/unit/test_dashboard_route_parity.py`; `tests/unit/test_dashboard_remodel_baseline_contract.py`; V3 remodel `TAB_CHECKLIST.md`, `DATA_CONTRACT.md`, and `src/app.js`.

Spec compliance: CLEAR. The revision directly answers all four required fixes. Fix 1 defines selector priority for HTML routes only, enumerates V2 canonical routes, V3 hard `/ui/remodel/*` allowlist routes, alias redirects, bad-route behavior, cache/title/asset expectations, test ownership, and rollback. Fix 2 corrects the earlier non-runnable visual command: the existing script has `--base-url` and required `--out` (`scripts/verify_dashboard_remodel_visual_gate.py:165-166`) and no compare option, so the revision specifies either extending it or adding `verify_dashboard_v2_v3_compare.py` with `--v2-base-url`, `--v3-base-url`, and `--out`. Fix 3 defines top-level and per-item inventory fields with stable IDs and safety/failure rules. Fix 4 separates selectable-preview acceptance from promotion/100% acceptance and blocks promotion on inventory/safety/audit/export evidence plus later human approval.

Architecture evidence: current code contains both shell sources: V2 `_dashboard_index_response()` at `ai_strategy_loop/dashboard/app.py:2692` and V3 `_dashboard_remodel_index_response()` at `app.py:2700`, with V3 no-store/no-cache headers at `app.py:2705-2707`. Current canonical handlers still return V3 (`/ui/evolution` at `app.py:2731-2739`, `/ui/backtest` at `app.py:2742-2744`, `/ui/chart-replay` at `app.py:2746-2748`) and invalid remodel pages currently redirect (`app.py:2727-2728`). The revision gives executors an unambiguous source contract to invert those defaults, preserve V2 by default, hard-allowlist V3 preview, and change invalid remodel routes to 404.

Product/safety evidence: V2 and V3 have distinct observable markers: V2 title `STOM AI · 조건식 자율 진화 대시보드` and `/ui/bundle/app.js` (`frontend/index.html:6,43`), while V3 title/assets are `STOM AI · 조건식 AI 연구 대시보드` plus `/ui/remodel/*20260628canonical` (`frontend/remodel/index.html:6,8,13-14`). The V3 source exposes safety cues and manual gates: `BacktestContracts` classifies POSTs and `/bt/ws_job` as manual/not auto-invoked (`frontend/remodel/src/app.js:58-84`), `ReplayContracts` marks `/sim/ws` user-gated (`src/app.js:90-112`), reference/demo modes are inert, and current static tests assert `final_approval` is absent from the remodel app. The revision keeps preview local-only/research-only and prevents any promotion claim until forbidden network, append-only audit, export separation, and inventory artifacts pass.

Code/verification evidence: current tests intentionally pin the old/current V3-on-canonical behavior (`test_dashboard_route_parity.py:100-111`; `test_dashboard_remodel_baseline_contract.py:17-26`). The revision explicitly moves those assertions to selector/profile coverage and assigns the matrix to `test_dashboard_route_parity.py`, while keeping hard-remodel assertions in the baseline contract test. The launch surfaces currently default to 8770 (`ai_strategy_loop/__main__.py:26`; `stom_dashboard.bat:14-15`), matching the revision requirement that the default profile stay V2.

## Root Cause
The root defect was not a rendering problem; it was the absence of a formal ownership and evidence contract for two dashboard generations sharing one backend. Stage 2 fixes that by making route ownership, selector priority, asset/cache identity, visual proof, inventory closure, and safety/promotion gates explicit instead of relying on screenshots or prose parity claims.

## Findings
- LOW — `stage-02-revision.md` Fix 1 and File-level changes: the preview profile is specified as 8776-only with an example `STOM_DASHBOARD_DEFAULT_VERSION=v3`, while the current launchers only expose host/port defaults. Impact: an executor could implement the env knob too broadly and accidentally let 8770 boot V3 by profile. Fix: centralize profile parsing in the route/version manifest and add tests for default 8770 V2, explicit 8776 V3 profile, explicit query override, and no accidental persistent selector. This is non-blocking because the revision already states default V2, 8776 preview profile, and the owning test file.
- LOW — `stage-02-revision.md` Fix 1 matrix: root `/` says query/profile may affect the target, and aliases preserve accepted `dashboard_version`, but execution should test root query preservation explicitly. Impact: `/?dashboard_version=v3` could lose the one-response selector during redirect. Fix: include `/` in the alias/query preservation matrix or explicitly document root query as unsupported. This is not a blocker because canonical V2 default and hard V3 routes remain protected.

## Recommendations
1. Approve the revised plan for execution after explicit human approval; do not treat that as promotion or 100% parity approval.
2. Implement route/version dispatch from a single manifest/helper consumed by tests, not scattered conditionals.
3. Keep preview selectors non-persistent: no localStorage, cookie, or session selector for preview acceptance.
4. Add the 8770/8776 two-base compare script and inventory gate before any promotion/100% statement.
5. Preserve the rollback path: force V2 default, remove passive V3 preview link, and keep or disable `/ui/remodel/*` until route, visual, inventory, and safety artifacts pass.

## Architectural Status
CLEAR

## Product Status
CLEAR

## Code Status
WATCH

## Code Review Recommendation
APPROVE

## Trade-offs
| Option | Strongest argument | Weakness | Verdict |
| --- | --- | --- | --- |
| Antithesis: separate-port-only V3 preview | Safest V2 protection; avoids selector/cache contamination in the stable 8770 surface | Fails the user goal of selectable V3 in the main surface and delays route-level integration evidence | Valid rollback fallback, not the preferred plan |
| Revised Option A: V2 default + explicit V3 preview selectors | Preserves V2, makes V3 visible/reversible, and binds execution to route, visual, inventory, and safety gates | Requires disciplined manifest/tests and profile scoping | Best synthesis; approved for execution |
| Immediate canonical V3 replacement | Simplest final routing once parity is proven | Violates V2 preservation and would bypass current inventory/safety gaps | Rejected until later explicit approval and complete promotion evidence |
