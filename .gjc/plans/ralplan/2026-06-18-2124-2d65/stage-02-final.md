# RALPLAN Final Plan — STOM 대시보드 개선 브랜치

Status: pending approval  
Run: 2026-06-18-2124-2d65  
Consensus: Planner revision stage 2 + Architect CLEAR/APPROVE + Critic OKAY

## 1. 목표

`STOM_Version_2U_C-ai-strategy-loop` 최신 anchor에서 새 clean branch/worktree를 만들고, 첫 실행 범위를 대시보드 개선으로 제한한다. 우선순위는 전수검사/기록 조회 개선, 중복처럼 보이는 기능의 안전한 정리, 사용자 편의성, 모든 연구 기록 조회, 프로세스 시각화 강화, 실시간 프로세스 노드 흐름도 반영, 속도 개선이다.

## 2. 핵심 원칙

1. 실행 전 anchor SHA를 검증하고 불일치하면 중단한다.
2. dirty `wt-dev`는 보호한다. reset/stash/clean/checkout/stage 없이 별도 clean worktree에서만 실행한다.
3. 이번 branch의 "전수검사 기능 개선"은 governed all-record / evidence-lineage lookup으로 정의한다.
4. 중복 제거는 의미가 같은 부분만 라벨/작은 helper로 줄인다. Evolution HoF와 Research Pro HoF는 divergent-by-design이라 병합하지 않는다.
5. V3K, live broker, final approval/export, strategy DB, protected runtime path, dependency 추가는 범위 밖이다.

## 3. 결정 드라이버

1. 운영자 가치: 캠페인, 문서, update_log, registry/evidence를 한 곳에서 찾는 기능이 가장 큰 병목을 해결한다.
2. 회귀 위험: 기존 `/research_records`, `/research_docs`, Lab/Pro/Verdict standalone page, HoF 분리 테스트가 있으므로 기존 route와 surface를 보존해야 한다.
3. 리뷰 가능성: dirty `wt-dev` 상태가 크므로 clean worktree + bounded branch가 필수다.

## 4. 선택지와 결정

### Option A — 선택: governed research-index-first dashboard branch

- 내용: `/research_index`와 `/research_index/detail` 또는 동등한 governed index helper를 추가하고, all-record lookup UI, source/canonicality badge, 관련 기록 링크, process-flow 개선, 작은 성능 개선을 순차 구현한다.
- 장점: 사용자 기록 조회 문제를 직접 해결하고, 기존 route를 보존하며, rollback이 쉽다.
- 단점: broad route naming audit, 전역 empty/error/loading component 정리, 전체 UI 통합은 뒤로 미룬다.

### Option B — broad dashboard consolidation branch

- 장점: 겉으로 보이는 중복과 UI 상태를 한 번에 많이 줄일 수 있다.
- 단점: HoF/Research Pro/Process 등 의도적으로 다른 surface를 잘못 합칠 위험이 크고 파일 범위가 넓다.

### Option C — process-flow-only branch

- 장점: 작고 시각적으로 명확하다.
- 단점: 사용자가 요청한 전체 기록 조회/전수검사/연구 관리 개선을 해결하지 못한다.

Decision: Option A.

## 5. 실행 전 branch/worktree preflight

실행 승인 후에만 수행한다.

```powershell
git fetch origin STOM_Version_2U_C-ai-strategy-loop
git rev-parse --short STOM_Version_2U_C-ai-strategy-loop
git rev-parse --short origin/STOM_Version_2U_C-ai-strategy-loop
```

현재 계획 기준 expected SHA는 `7d7187f7`이다. local anchor 또는 remote anchor가 이 값과 다르면 worktree 생성 전에 중단하고 계획을 갱신한다. `.omo/evidence/stom-reorg-20260618/branch-map.md`와 `pr-restart-strategy.md`는 과거 스냅샷이므로 현재 branch truth로 쓰지 않는다.

승인 후 clean worktree 예시:

```powershell
git worktree add ../STOM_V.wt-dashboard-next -b lazycodex/dashboard-research-index-flow-20260619 origin/STOM_Version_2U_C-ai-strategy-loop
git -C ../STOM_V.wt-dashboard-next status --short --branch
```

## 6. 구현 범위

### 6.1 Governed research index backend

Candidate files:
- `ai_strategy_loop/dashboard/research_api.py`
- `ai_strategy_loop/dashboard/research_records.py`
- new candidate: `ai_strategy_loop/dashboard/research_index.py`
- tests: `tests/unit/dashboard/test_research_records.py`

Contract:
- Existing `/research_records`, `/research_records/detail`, `/research_docs`, `/research_doc` remain backwards-compatible.
- Add `/research_index` and `/research_index/detail` unless implementation proves an equivalent route name is better; if route name changes, tests and smoke commands must be updated before implementation proceeds.
- Stable namespaced IDs:
  - `campaign:<name>`
  - `doc:<repo-rel-path>`
  - `update_log:<repo-rel-path>`
  - `registry:<machine_name>`
- Required fields: `id`, `kind`, `source_path`, `title`, `updated_at`, `canonicality`, `source_authority`, `detail_available`, `tags`, `related_ids`.
- `canonicality` and `source_authority` must be closed constants/enums, not free-form strings.
- Detail lookup rejects path traversal, malformed namespaces, missing files, disallowed stale entries, and unknown kinds.

`.omo/evidence/stom-reorg-20260618` exposure rule:
- Do not expose the directory wholesale.
- Prefer machine-readable `research-registry.json` and selected source-inventory/registry rows.
- Do not index screenshots, browser captures, smoke logs, safety snapshots, dirty status dumps, stale branch maps, split strategy files, or planning files as authoritative facts.

### 6.2 All-record lookup frontend

Candidate files:
- `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`
- `ai_strategy_loop/dashboard/frontend/research-wiki.jsx`
- `ai_strategy_loop/dashboard/frontend/app.jsx`
- optional new helper/panel: `research-index-panel.jsx` or `research-index-utils.jsx`
- tests: `tests/unit/dashboard/test_research_records_frontend.py`, `tests/unit/test_dashboard_wiki_frontend.py`

Acceptance:
- One dashboard path can search campaign records, docs, selected update logs, and allowlisted registry entries.
- Results show source/canonicality badges and related IDs.
- Large detail payloads are lazy-loaded.
- Markdown remains inert; do not use `dangerouslySetInnerHTML`.
- Search is debounced/memoized and initial visible rows are capped.

### 6.3 Duplicate handling and usability labels

Candidate files:
- `ai_strategy_loop/dashboard/frontend/chart-hall-of-fame.jsx`
- `ai_strategy_loop/dashboard/frontend/rp-heatmap.jsx`
- `tests/unit/dashboard/test_p3_consolidation.py`
- `tests/unit/dashboard/test_no_duplicate_globals.py`

Acceptance:
- Evolution HoF and Research Pro HoF remain separate.
- Add purpose/source labels only.
- Do not merge fields, table bodies, routes, or workflows.
- Keep duplicate-global guard green.

### 6.4 Realtime process node flowchart

Candidate files:
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`
- optional new helper: `ai_strategy_loop/dashboard/frontend/process-flow-diagram.jsx`
- `ai_strategy_loop/scripts/build_process_flow_html.py`
- `docs/process_flow.html`
- tests: `tests/unit/test_dashboard_phase_mapping.py`, `tests/unit/dashboard/test_p11_process_flow.py`

Acceptance:
- Flow reflects current node, elapsed time, completed step timing, phase timing, and recent logs.
- Use current live state fields such as `latest.current_step`, `step_timings`, `phase_started_at`, `gen_started_at`, and recent logs.
- Preserve public panel/export contracts.
- Extract helpers if realtime additions would bloat `phase-detail.jsx`; do not grow near-threshold files unnecessarily.

### 6.5 Speed/performance

Backend:
- Metadata-only initial index response.
- Lazy detail endpoints.
- Optional process-local cache only; no persistent cache writes.
- Cache key includes root path + included source file path + `mtime_ns` + size.
- Invalidate on allowlisted file add/remove/mtime/size changes.
- Test root isolation.

Frontend:
- Debounce search.
- Abort stale fetches.
- Memoize filtered rows.
- Cap initial visible rows.
- Reuse loaded index metadata instead of re-fetching wiki/records unnecessarily.

Speed claims must include observable before/after or at least captured response size/latency/harness timing.

## 7. Verification plan

Focused commands for execution branch:

```powershell
pytest tests/unit/dashboard/test_research_records.py -q
pytest tests/unit/dashboard/test_research_records_frontend.py -q
pytest tests/unit/test_dashboard_wiki_frontend.py -q
pytest tests/unit/test_dashboard_phase_mapping.py tests/unit/dashboard/test_p11_process_flow.py -q
pytest tests/unit/dashboard/test_no_duplicate_globals.py -q
cd ai_strategy_loop/dashboard/webui-build
node build-app.mjs
node check-missing-imports.mjs
node track-z-harness.mjs
```

Manual/API smoke:
- `/ui/`
- `/research_records`
- `/research_records/detail?campaign=<known>`
- `/research_docs`
- `/research_doc?id=<known>`
- `/research_index`
- `/research_index/detail?id=<known>`
- `/evolution_gui_parity?run_id=&gen_no=-1`
- process tab iframe

Also capture protected-path status before PR:

```powershell
git status --short -- _database/ _database_v3k_shadow/ _log/ backup/ ':(glob)**/*.db' backtest/graph/ .omx/reports/ ':(glob)v3k_settings*.json' _v3k_sidecar/v3k_gui_settings.json
```

## 8. Rollback

- Revert only feature-branch commits; never reset dirty `wt-dev`.
- If index breaks discovery, hide new lookup entry and keep legacy `/research_records` and `/research_docs` active.
- If `.omo` allowlist is too broad, remove `.omo` rows rather than widening authority labels.
- If process extraction breaks bundle/tests, revert extraction and keep current `ProcessFlowPanel` behavior.
- If HoF labels confuse users, revert labels only; never merge HoF surfaces as rollback.

## 9. Non-goals

- No official OOS in this dashboard branch.
- No V3K gate changes.
- No KHOPENAPI/login/live order/live exit wiring.
- No strategy DB or final approval/export writes.
- No protected runtime paths.
- No dependency additions without explicit approval.
- No broad route naming audit unless separately approved.
- No whole-dashboard component consolidation.

## 10. ADR

### Decision

Proceed, after explicit approval, with Option A: a clean-worktree dashboard branch from verified `STOM_Version_2U_C-ai-strategy-loop @ 7d7187f7`, focused on governed research index, all-record lookup, source/canonicality labels, safe duplicate labeling, realtime process-flow improvements, and incremental speed work.

### Drivers

- Operators need one path to find research records, docs, selected update logs, and registry/evidence lineage.
- Existing routes and panels have meaningful separation and regression coverage.
- Dirty `wt-dev` makes isolated branch/worktree execution mandatory.

### Alternatives considered

- Broad dashboard consolidation: rejected for first branch due regression and semantic-merge risk.
- Process-flow-only branch: rejected because it does not solve all-record lookup/research governance.

### Why chosen

Option A gives the highest near-term user value while keeping changes reviewable, reversible, and compatible with the current dashboard architecture.

### Consequences

- Adds a new governed index contract that must be kept stable and tested.
- Defers broad route naming audit and general UI consolidation.
- Requires strict allowlisting so stale planning artifacts do not become authoritative dashboard facts.

### Follow-ups

1. Route naming contract audit.
2. Shared empty/loading/error micro-components.
3. Dashboard tooling preflight/npm audit handling.
4. Official OOS work remains separate from dashboard branch.

## 11. Consensus receipts

- Planner stage 1: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-01-planner.md`
- Architect stage 1: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-01-architect.md` — BLOCK, fixed by revision.
- Planner revision stage 2: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-02-revision.md`
- Architect stage 2: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-02-architect.md` — CLEAR/APPROVE.
- Critic stage 2: `.gjc/plans/ralplan/2026-06-18-2124-2d65/stage-02-critic.md` — OKAY.

## 12. Status

Pending approval. This plan does not authorize source edits, branch/worktree creation, commit, push, PR, tests/builds, or execution delegation until the user explicitly approves execution.
