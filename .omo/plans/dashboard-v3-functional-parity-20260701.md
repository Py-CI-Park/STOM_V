# Dashboard V3 Functional Parity and UX Completion Plan

작성일: 2026-07-01
상태: READY FOR IMPLEMENTATION
워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
브랜치: `feature/dashboard-remodel-20260626`
기준 커밋: `887c3591161e95b2d828112266dc9d34a749adab`

## Objective

`feature/dashboard-remodel-20260626`에서 기존 V2 대시보드의 주요 실기능을 V3 리모델 UI로 이전하고, 백테스트 -> 차트 리플레이 -> 조건 AI 분석 -> 의사결정 감사까지 하나의 일관된 업무 흐름으로 개발 완료한다.

완료 기준은 "보기 좋은 프리뷰"가 아니라, 명시적 `/ui/remodel/*` 경로에서 V2의 실제 기능 계약을 재사용하고, 실패/빈 데이터/실행 중/완료/오류 상태를 다루며, 안전 게이트를 유지하는 것이다.

## Non-Negotiable Constraints

- 현재 워크트리와 브랜치에서 `887c3591161e95b2d828112266dc9d34a749adab` 위에 새 커밋을 쌓는다.
- V2 기본 대시보드 경로는 유지한다. V3는 명시적 `/ui/remodel/*` 또는 기존 명시 선택자에서만 활성화한다.
- 라이브 주문, 브로커 로그인, 계좌/잔고 조작, KHOPENAPI 연결, DB 컷오버, USER_ACK 생성, V3K gate 4~6 실행은 범위 밖이다.
- `/bt/run`, `/sim/*`, `/record_decision` 같은 쓰기/실행성 액션은 사용자 명시 클릭, 확인, 기존 검증 계약을 통과해야만 호출한다.
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/v3k_gui_settings.json`는 소스 변경이나 임시 스크래치로 취급하지 않는다.
- 기존 미추적 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`는 사용자가 만든 산출물로 보고 건드리지 않는다.
- 스테이징은 항상 명시 파일만 사용한다. `git add -A` 금지.
- 커밋 메시지는 한국어 제목과 한국어 markdown 본문을 사용한다.

## Evidence Read

- `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`
  - 기존 리모델은 V2 기능 관점 약 55/100, 자체 리모델 완성도 약 71/100으로 평가됨.
  - 주요 부족분은 Backtest, Replay, Condition AI deep APIs, Audit/Decision, E2E 검증.
- `docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md`
  - V3는 프리뷰가 아니라 프로덕션 API/상태 흐름 재사용으로 완성해야 함.
  - 목업 라벨 제거, 빈 데이터/엔드포인트 실패/프리뷰 상태를 명확히 표시해야 함.
- `ai_strategy_loop/dashboard/app.py:2700`
  - 리모델 인덱스는 별도 response header `X-STOM-Dashboard-Version: v3-remodel`로 제공됨.
- `ai_strategy_loop/dashboard/app.py:2713`
  - V3 선택은 `dashboard_version`, `dashboard_profile` 명시 값으로만 처리됨.
- `ai_strategy_loop/dashboard/app.py:2803`
  - `/ui/remodel/*` deep link는 허용된 페이지만 fail-closed로 제공됨.
- `ai_strategy_loop/dashboard/app.py:3085`
  - `/decisions`, `/record_decision` append-only 계약이 이미 존재함.
- `ai_strategy_loop/dashboard/app.py:3339`
  - `/strategy_code`, `/prompts`, `/strategy_diff`, `/ai_context_pack`, `/backtest_detail` 등 조건 AI/검토 API가 존재함.
- `ai_strategy_loop/dashboard/app.py:3453`
  - `/edge_ratio`, `/feature_importance`, `/variable_correlation` 분석 API가 존재함.
- `ai_strategy_loop/dashboard/frontend/app.jsx:368`
  - 기존 V2 프로덕션 shell이 `SimulationTab`, `BacktestTab`을 실제 기능으로 렌더링함.
- `ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx:21`
  - 기존 `BacktestTab`이 백테스트 기능의 source of truth임.
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx:144`
  - 기존 백테스트는 `/bt/ws_job?job_id=...`, `/bt/run` 계약을 사용함.
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx:19`
  - 기존 `SimulationTab`은 `/sim/*` REST와 `/sim/ws` 계약을 사용함.
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
  - 현재 리모델은 mode guard, safety cue, contract matrix, inert replay status를 갖췄으나 파일이 커졌고 실기능 연결은 제한적임.
- `tests/unit/test_dashboard_remodel_static.py`
  - 현재 안전/프리뷰/계약 매트릭스 중심의 리모델 정적 계약 테스트가 있음.
- `tests/unit/test_dashboard_remodel_baseline_contract.py`
  - V2 기본 유지, V3 명시 경로, 금지 액션 guard를 검증함.
- `tests/unit/dashboard/test_backtest_ws_job.py`
  - 백테스트 job websocket과 결과 부가 분석 계약을 검증함.
- `tests/unit/dashboard/test_simulation_ws.py`
  - 차트 리플레이 websocket session/action 계약을 검증함.
- `tests/unit/dashboard/test_research_pro.py`
  - 조건 AI/전략 코드/분석 API의 safe empty behavior를 검증함.
- `tests/unit/dashboard/test_p2_structural.py`
  - 승인/의사결정 흐름과 `/record_decision` 분리를 검증함.

## Metis Gap Analysis

`ulw-plan`은 Metis 에이전트 검토를 요구하지만 현재 세션에는 `spawn_agent` 도구가 노출되어 있지 않다. 대신 아래 gap analysis를 계획에 직접 반영한다.

- Gap 1: 현재 리모델은 독립 프리뷰 성격이 강하고, V2 실기능 컴포넌트와 상태 흐름 재사용이 약하다.
  - 대응: 새 기능을 다시 만들기보다 `BacktestTab`, `SimulationTab`, 기존 분석 API client 흐름을 우선 재사용하거나 공통 adapter로 추출한다.
- Gap 2: `remodel/src/app.js`가 큰 단일 파일이므로 기능을 더 붙이면 유지보수성이 급격히 낮아진다.
  - 대응: 빌드 체계가 허용하는 범위에서 리모델 전용 modules/adapters를 분리하고, 분리 전후 bundle 계약 테스트를 잠근다.
- Gap 3: 실제 실행 액션을 연결하면 V3K 안전 게이트와 충돌할 수 있다.
  - 대응: V3 대시보드는 live order/broker/account를 다루지 않고, 기존 research/backtest/simulation 계약만 명시 클릭으로 호출한다.
- Gap 4: 정적 테스트만으로는 UX 품질과 전체 프로세스 연결을 보장하지 못한다.
  - 대응: unit/static tests 외에 browser-level smoke, API failure state, keyboard/focus, narrow viewport, whole-flow scenario를 추가한다.
- Gap 5: V2 기본 경로를 실수로 바꾸면 기존 운영자 workflow를 깨뜨린다.
  - 대응: baseline route tests를 첫 단계와 마지막 단계에서 반복하고, 리모델 deep link allowlist를 유지한다.

## Implementation Defaults

- 프론트엔드 프레임워크를 새로 도입하지 않는다.
- 현재 리모델 빌드/zip 생성 경로를 먼저 확인하고, 가능한 최소 구조 변경으로 진행한다.
- 기존 React 컴포넌트를 V3 shell에서 직접 사용할 수 있으면 직접 재사용한다.
- 직접 재사용이 빌드 구조상 불리하면, V2 컴포넌트의 API/state 로직을 공통 adapter로 추출해 V2와 V3가 같은 계약을 사용하게 한다.
- 목업 데이터는 `reference/demo` 모드에서만 보이고, `live` 모드에서는 실제 API 결과, 빈 상태, 오류 상태를 표시한다.
- UX copy는 기능 설명문보다 상태/라벨/액션 중심으로 제한한다.
- 카드 중첩, 마케팅 hero, 장식성 gradient/orb, 과도한 한 색상 팔레트는 사용하지 않는다.

## TODOs

- [x] TODO 01 - Baseline Lock And Evidence Setup
- [x] TODO 02 - Remodel Build Boundary And Module Map
- [x] TODO 03 - Unified UX System For Functional States
- [x] TODO 04 - Backtest V3 Adapter And Preflight Parity
- [x] TODO 05 - Backtest Job Progress And Result Parity
- [x] TODO 06 - Backtest Analysis, Compare, And Report Surface
- [x] TODO 07 - Chart Replay Preflight And Dataset Selection
- [x] TODO 08 - Chart Replay WebSocket Playback And Controls
- [x] TODO 09 - Chart Replay Timeline, Signals, And Visual Consistency
- [x] TODO 10 - Condition AI Detail APIs In V3
- [x] TODO 11 - Analytics And Cross-Workflow Handoffs
- [x] TODO 12 - Decision Audit And Append-Only Approval Flow
- [x] TODO 13 - Whole-Process UX Pass
- [x] TODO 14 - Test Expansion For Functional Parity
- [x] TODO 15 - Browser And Safety Verification
- [x] TODO 16 - Final Review, Scorecard, And Commit Stack Cleanup

## TODO 01 - Baseline Lock And Evidence Setup

Goal:
현재 기준 커밋에서 실제 이어서 작업 가능한 상태를 증거화하고, 기존 테스트가 어떤 상태인지 먼저 고정한다.

References:
- `AGENTS.md`
- `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`
- `tests/unit/test_dashboard_remodel_baseline_contract.py`
- `tests/unit/test_dashboard_remodel_static.py`

Steps:
- `git status --short --branch`, `git rev-parse HEAD`, `git log -1 --oneline`을 evidence에 기록한다.
- `.omo/evidence/dashboard-v3-functional-parity-20260701/` 아래에 command log를 만든다.
- 현 기준 targeted test를 실행해 baseline green/red를 기록한다.
- protected/runtime path status를 별도로 확인한다.

Acceptance Criteria:
- 기준 HEAD가 `887c3591161e95b2d828112266dc9d34a749adab`임이 evidence에 남는다.
- 기존 미추적 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`를 수정하거나 stage하지 않는다.
- baseline test 결과가 plan evidence에 남는다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q`
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

Commit Strategy:
- 이 단계만으로는 커밋하지 않는다. 다음 구조 정리 단계와 함께 `대시보드 V3 기준선과 구조를 정리` 커밋에 포함한다.

## TODO 02 - Remodel Build Boundary And Module Map

Goal:
V3 리모델 frontend의 실제 빌드 경로를 확정하고, `remodel/src/app.js`에 새 기능을 계속 누적하지 않도록 분리 가능한 경계를 만든다.

References:
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
- `ai_strategy_loop/dashboard/frontend/remodel/`
- `tests/unit/test_dashboard_remodel_static.py:15`
- `tests/unit/test_dashboard_remodel_baseline_contract.py:157`

Steps:
- remodel bundle 생성/사용 경로를 확인한다.
- 기존 tests가 zip entrypoint와 static asset 계약을 어떻게 확인하는지 읽는다.
- 분리 가능한 경우 다음 경계를 만든다:
  - `core/mode`
  - `core/api`
  - `core/state`
  - `components/status`
  - `components/layout`
  - `pages/backtest`
  - `pages/replay`
  - `pages/condition-ai`
  - `pages/audit`
- 빌드 경로가 단일 파일을 요구하면, 먼저 내부 section registry와 adapter object만 분리하고 physical split은 다음 커밋으로 미룬다.

Acceptance Criteria:
- V3 remodel route와 zip/static contract가 깨지지 않는다.
- mode guard, reference/demo/live 분기가 기존 테스트와 동일하게 유지된다.
- 새 기능을 붙일 public adapter 경계가 코드상 명확하다.

QA:
- `node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_remodel_bundle_present -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_remodel_uses_reviewed_zip_renderer_not_production_bundle -q`

Commit Strategy:
- 커밋 제목: `대시보드 V3 기준선과 구조를 정리`
- 본문: 기준 커밋, 리모델 빌드 경계, 기존 route 계약 유지, protected path 무변경을 기록한다.

## TODO 03 - Unified UX System For Functional States

Goal:
V3 리모델 전체에 동일한 상태 체계와 layout rhythm을 적용해, 백테스트/리플레이/AI/감사 화면이 서로 다른 앱처럼 보이지 않게 한다.

References:
- `docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md`
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
- `tests/unit/test_dashboard_remodel_static.py:90`
- `tests/unit/test_dashboard_remodel_static.py:494`

Steps:
- 공통 상태 vocabulary를 코드로 고정한다:
  - `reference`
  - `demo`
  - `live`
  - `empty`
  - `loading`
  - `error`
  - `stale`
  - `requires-confirmation`
- 모든 페이지에 동일한 page header, status strip, action group, evidence/provenance strip을 적용한다.
- 액션 버튼은 `disabled`, `pending`, `confirmed`, `failed` 상태를 시각적으로 구분한다.
- 금지 기능은 숨김 또는 비활성 처리하되, live order/broker/account 컨트롤을 만들지 않는다.
- 모바일/좁은 viewport에서 toolbar와 table이 겹치지 않도록 grid/flex constraints를 정한다.

Acceptance Criteria:
- 각 화면이 같은 navigation, spacing, typography, status language를 사용한다.
- `live` API 실패와 빈 데이터가 목업으로 대체되지 않는다.
- 금지된 live-trading affordance가 생기지 않는다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_remodel_provenance_and_live_payload_state -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_remodel_safety_cues_and_forbidden_controls -q`
- Browser check: `/ui/remodel/backtest`, `/ui/remodel/chart-replay`, `/ui/remodel/lab`, `/ui/remodel/audit` desktop/narrow viewport.

Commit Strategy:
- 커밋 제목: `대시보드 V3 공통 UX 상태 체계를 정리`

## TODO 04 - Backtest V3 Adapter And Preflight Parity

Goal:
V2 백테스트의 입력, 검증, 전략 선택, 실행 전 확인 흐름을 V3 리모델 백테스트 화면으로 옮긴다.

References:
- `ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx:21`
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx:266`
- `ai_strategy_loop/dashboard/frontend/backtest.jsx`
- `tests/unit/test_dashboard_remodel_static.py:282`
- `tests/unit/dashboard/test_backtest_ws_job.py`

Steps:
- 기존 `BacktestTab`/`bt-tab-run`의 API 호출, 입력 상태, 검증 규칙을 확인한다.
- V3에서 직접 React component reuse가 가능한지 확인한다.
- 직접 reuse가 가능하면 V3 page adapter에서 `BacktestTab`을 mount하거나 shell slot으로 감싼다.
- 직접 reuse가 어렵다면 backtest API/state adapter를 공통 모듈로 추출하고 V2/V3가 같이 사용하게 한다.
- V3 백테스트 화면에 다음 실기능을 연결한다:
  - 전략/run/gen 선택
  - 기간/종목/시장/프로필 선택
  - parameter/sweep 입력
  - 실행 전 validation summary
  - 명시 confirm gate
  - disabled reason display

Acceptance Criteria:
- V3 backtest page가 더 이상 static contract matrix만 보여주지 않는다.
- 입력값이 기존 `/bt/run` 계약과 동일한 shape로 생성된다.
- 유효하지 않은 입력은 `/bt/run` 호출 전 차단된다.
- reference/demo mode에서 `/bt/run`은 호출되지 않는다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_backtest_adapter_contract_matrix -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_backtest_reference_and_demo_are_inert -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_backtest_live_reads_and_mutation_gates -q`
- Browser check: invalid input, valid preflight, cancel confirm, confirm with mocked/test backend.

Commit Strategy:
- 커밋 제목: `대시보드 V3 백테스트 사전검증을 연결`

## TODO 05 - Backtest Job Progress And Result Parity

Goal:
V3 백테스트에서 실행 후 websocket 진행률, terminal state, 결과 요약, 오류 처리를 V2와 동등하게 제공한다.

References:
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx:144`
- `ai_strategy_loop/dashboard/app.py`
- `tests/unit/dashboard/test_backtest_ws_job.py:114`
- `tests/unit/dashboard/test_backtest_ws_job.py:126`
- `tests/unit/dashboard/test_backtest_ws_job.py:140`

Steps:
- `/bt/ws_job?job_id=...` 연결과 close/error/retry policy를 V3 adapter에 반영한다.
- job id가 없거나 unknown이면 사용자에게 복구 가능한 오류 상태를 표시한다.
- running -> terminal state 전환 시 result fetch와 view update를 연결한다.
- 백테스트 중복 실행, 중단, disabled 상태를 기존 V2 규칙과 맞춘다.
- network failure 시 목업 결과로 대체하지 않고 오류/재시도 상태를 보여준다.

Acceptance Criteria:
- job 진행률과 terminal state가 V3 화면에서 업데이트된다.
- missing/unknown job id 오류가 사용자에게 표시된다.
- V3에서 websocket이 자동으로 열리는 것은 실행 완료 후 job 관찰에 한정된다.
- reference/demo mode는 inert다.

QA:
- `python -m pytest tests/unit/dashboard/test_backtest_ws_job.py -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_backtest_live_reads_and_mutation_gates -q`
- Browser check: mocked running job, terminal job, unknown job, websocket close.

Commit Strategy:
- 커밋 제목: `대시보드 V3 백테스트 진행 상태를 연결`

## TODO 06 - Backtest Analysis, Compare, And Report Surface

Goal:
V2 백테스트 결과의 핵심 분석 표면을 V3에서 읽고 비교할 수 있게 한다.

References:
- `tests/unit/dashboard/test_backtest_ws_job.py`
- `ai_strategy_loop/dashboard/app.py:3416`
- `ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`

Steps:
- V3 결과 화면에 summary, equity, trades, drawdown, MAE/MFE, exit reason, range, montecarlo, orderflow, compare view를 연결한다.
- `/backtest_detail` safe empty behavior를 V3 empty state와 연결한다.
- 결과 table/chart는 같은 filter/sort/empty/error component를 사용한다.
- report/export affordance가 있다면 기존 V2 계약만 사용하고 새 운영 DB write를 만들지 않는다.

Acceptance Criteria:
- V3 백테스트 결과가 V2 테스트 계약의 핵심 분석 데이터를 표시한다.
- 결과가 없을 때 빈 상태가 명확하고 목업 수치가 나오지 않는다.
- compare 대상이 없을 때 disabled reason이 표시된다.

QA:
- `python -m pytest tests/unit/dashboard/test_backtest_ws_job.py -q`
- `python -m pytest tests/unit/dashboard/test_research_pro.py::test_backtest_detail_run_gen_available_key -q`
- Browser check: populated result, empty result, compare unavailable, API 500.

Commit Strategy:
- 커밋 제목: `대시보드 V3 백테스트 결과 분석을 보강`

## TODO 07 - Chart Replay Preflight And Dataset Selection

Goal:
V2 차트 리플레이의 데이터 선택, 전략/종목/일자/속도 사전검증을 V3 chart-replay 화면으로 이전한다.

References:
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx:19`
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx:197`
- `ai_strategy_loop/dashboard/frontend/simulation.jsx`
- `tests/unit/test_dashboard_remodel_static.py:390`
- `tests/unit/dashboard/test_simulation_ws.py`

Steps:
- 기존 `SimulationTab`의 `/sim/*` REST와 `/sim/ws` 사용 흐름을 확인한다.
- V3에서 직접 component reuse 또는 shared adapter 추출 중 하나를 확정한다.
- V3 replay 화면에 dataset/source, code, date, strategy, speed, visible range 선택을 연결한다.
- 시작 전 missing codes/date/source 등을 검증한다.
- `/sim/ws`는 사용자 시작 액션 전 자동 연결하지 않는다.

Acceptance Criteria:
- V3 replay page가 실제 session preflight를 제공한다.
- 필수 값이 없으면 `/sim/ws` 또는 start action이 호출되지 않는다.
- reference/demo mode는 inert다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_replay_adapter_contract_matrix -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_replay_reference_and_demo_are_inert -q`
- Browser check: missing code, missing date, valid preflight, cancel start.

Commit Strategy:
- 커밋 제목: `대시보드 V3 차트 리플레이 사전검증을 연결`

## TODO 08 - Chart Replay WebSocket Playback And Controls

Goal:
V3 chart-replay에서 `/sim/ws` 기반 start/pause/resume/seek/speed/stop 흐름을 완성한다.

References:
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx:197`
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js:1853`
- `tests/unit/dashboard/test_simulation_ws.py:110`
- `tests/unit/dashboard/test_simulation_ws.py:222`
- `tests/unit/dashboard/test_simulation_ws.py:244`
- `tests/unit/dashboard/test_simulation_ws.py:250`
- `tests/unit/dashboard/test_simulation_ws.py:274`

Steps:
- websocket lifecycle을 V3 adapter에 구현한다.
- start -> meta -> bars -> pause/resume -> speed/seek -> stop/done 상태를 UI 상태와 연결한다.
- unknown action, over session limit, missing codes 오류를 화면에 표시한다.
- stop/done 후 chart와 event log가 안정적으로 남도록 한다.
- session cleanup과 reconnect policy를 명확히 한다.

Acceptance Criteria:
- V3 replay controls가 실제 websocket session을 조작한다.
- 오류가 toast만으로 사라지지 않고 해당 panel 상태로 남는다.
- concurrent session limit 오류가 명확히 표시된다.
- websocket은 사용자가 replay를 시작할 때만 열린다.

QA:
- `python -m pytest tests/unit/dashboard/test_simulation_ws.py -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_replay_live_reads_and_ws_user_gate -q`
- Browser check: start, pause, resume, seek, speed change, stop, unknown action, over limit.

Commit Strategy:
- 커밋 제목: `대시보드 V3 차트 리플레이 재생 제어를 연결`

## TODO 09 - Chart Replay Timeline, Signals, And Visual Consistency

Goal:
리플레이가 단순 바 재생이 아니라 전략 신호, 거래, 포지션, 이벤트 타임라인을 함께 보여주도록 V3 UI를 완성한다.

References:
- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx`
- `tests/unit/dashboard/test_simulation_ws.py`
- `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`

Steps:
- bars, signals, trades, positions, logs payload를 시각 영역과 side panel로 나눈다.
- chart viewport, selected bar, event detail, replay cursor를 같은 state source로 묶는다.
- 데이터가 없는 signal/trade 영역은 빈 상태를 보여준다.
- 백테스트 결과에서 리플레이로 넘어온 context가 있으면 code/date/strategy를 prefill한다.
- narrow viewport에서 chart와 timeline이 서로 겹치지 않도록 constraints를 적용한다.

Acceptance Criteria:
- replay chart, event timeline, selected detail이 같은 cursor를 공유한다.
- 백테스트 결과 -> 리플레이 전환 시 context 손실이 없다.
- signal/trade 데이터가 없을 때 목업 거래가 보이지 않는다.

QA:
- `python -m pytest tests/unit/dashboard/test_simulation_ws.py -q`
- Browser check: populated replay, no-signal replay, backtest-to-replay handoff, narrow viewport.

Commit Strategy:
- 커밋 제목: `대시보드 V3 차트 리플레이 분석 화면을 보강`

## TODO 10 - Condition AI Detail APIs In V3

Goal:
조건 AI/전략 검토 화면에서 기존 deep read-only API를 V3에 연결해, 전략 코드와 변경점, prompt, context pack, backtest detail을 실제로 확인할 수 있게 한다.

References:
- `ai_strategy_loop/dashboard/app.py:3339`
- `ai_strategy_loop/dashboard/app.py:3360`
- `ai_strategy_loop/dashboard/app.py:3365`
- `ai_strategy_loop/dashboard/app.py:3411`
- `ai_strategy_loop/dashboard/app.py:3416`
- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
- `tests/unit/dashboard/test_research_pro.py:16`
- `tests/unit/dashboard/test_research_pro.py:194`
- `tests/unit/dashboard/test_research_pro.py:204`

Steps:
- V3 condition/lab/workbench 화면에서 run/gen selector를 공통화한다.
- `/strategy_code`를 연결해 source, safe empty, missing run/gen 상태를 표시한다.
- `/strategy_diff`를 연결해 변경점과 비교 기준을 보여준다.
- `/prompts`와 `/ai_context_pack`을 read-only inspector로 연결한다.
- `/backtest_detail`을 조건 AI 결과 검토 context와 연결한다.
- missing run/gen은 예외가 아니라 빈 상태로 처리한다.

Acceptance Criteria:
- V3에서 조건 AI run/gen을 선택하면 실제 strategy code/diff/prompt/context/backtest detail을 확인할 수 있다.
- API가 빈 결과를 반환해도 화면이 깨지지 않는다.
- 이 단계는 읽기 전용이며 전략 생성/실행 쓰기 경로를 새로 만들지 않는다.

QA:
- `python -m pytest tests/unit/dashboard/test_research_pro.py -q`
- Browser check: valid run/gen, missing run, missing gen, API failure, empty diff.

Commit Strategy:
- 커밋 제목: `대시보드 V3 조건 AI 상세 조회를 연결`

## TODO 11 - Analytics And Cross-Workflow Handoffs

Goal:
조건 AI 분석 결과가 백테스트와 리플레이로 이어지도록, edge/feature/correlation 분석과 화면 간 handoff를 연결한다.

References:
- `ai_strategy_loop/dashboard/app.py:3453`
- `ai_strategy_loop/dashboard/app.py:3468`
- `ai_strategy_loop/dashboard/app.py:3484`
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`
- `tests/unit/dashboard/test_research_pro.py:211`

Steps:
- `/edge_ratio`, `/feature_importance`, `/variable_correlation`를 V3 lab/workbench에 연결한다.
- 분석 결과에서 선택된 run/gen/strategy context를 백테스트 preflight로 넘긴다.
- 백테스트 결과에서 리플레이 preflight로 code/date/strategy context를 넘긴다.
- 각 handoff는 URL state 또는 in-memory state 중 현재 routing 구조에 맞는 하나로 통일한다.
- context가 불완전하면 action을 비활성화하고 missing reason을 표시한다.

Acceptance Criteria:
- 조건 AI -> 백테스트 -> 리플레이로 이어지는 최소 1개 happy path가 동작한다.
- 분석 API 실패 시 같은 UX 상태 체계로 오류가 표시된다.
- 불완전 context는 자동 실행으로 이어지지 않는다.

QA:
- `python -m pytest tests/unit/dashboard/test_research_pro.py -q`
- Browser check: condition to backtest handoff, backtest to replay handoff, incomplete context, API failure.

Commit Strategy:
- 커밋 제목: `대시보드 V3 분석 흐름과 화면 전환을 연결`

## TODO 12 - Decision Audit And Append-Only Approval Flow

Goal:
V3 audit/verdict/records 화면에서 의사결정 기록과 감사 흐름을 실제 `/decisions`, `/record_decision` 계약으로 연결한다.

References:
- `ai_strategy_loop/dashboard/app.py:3085`
- `ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx`
- `tests/unit/dashboard/test_p2_structural.py:78`
- `tests/unit/dashboard/test_p2_structural.py:92`
- `tests/unit/test_dashboard_remodel_static.py`

Steps:
- V3 audit 화면에서 `/decisions` 목록을 읽는다.
- 조건 AI/백테스트/리플레이 context를 decision draft로 연결한다.
- `/record_decision` 호출은 명시 confirm 후 append-only로만 수행한다.
- final approval websocket 또는 live approval flow와 `/record_decision`을 섞지 않는다.
- 기록 실패, 중복/누락 context, validation 오류를 상태 panel에 표시한다.

Acceptance Criteria:
- V3에서 decision 목록 조회와 decision 기록이 기존 계약으로 동작한다.
- 기록 액션은 append-only이며 운영 승인/실주문과 연결되지 않는다.
- final approval route와 `/record_decision`의 경계가 유지된다.

QA:
- `python -m pytest tests/unit/dashboard/test_p2_structural.py -q`
- `python -m pytest tests/unit/test_dashboard_remodel_static.py::test_remodel_safety_cues_and_forbidden_controls -q`
- Browser check: decision list empty/populated, record cancel, record confirm, record failure.

Commit Strategy:
- 커밋 제목: `대시보드 V3 의사결정 감사 흐름을 연결`

## TODO 13 - Whole-Process UX Pass

Goal:
각 기능을 개별 화면으로만 완성하지 않고, 운영자가 하루의 연구/검토 흐름을 끊김 없이 수행할 수 있게 전체 IA와 interaction을 정리한다.

References:
- `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`
- `docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md`
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`

Steps:
- V3 navigation을 다음 workflow 기준으로 정리한다:
  - Overview
  - Condition AI
  - Backtest
  - Chart Replay
  - Audit/Decision
  - Settings
- 각 화면에 shared context strip을 둔다: selected run/gen, strategy, symbol/date, latest decision state.
- primary action은 화면당 1개 원칙으로 정리하고 secondary actions는 icon/compact controls로 정돈한다.
- tables, charts, logs의 density를 맞추고, 반복 card 남용을 줄인다.
- keyboard focus, disabled states, hover/active affordance를 정리한다.
- 좁은 viewport에서 toolbar overflow와 table/chart clipping을 확인한다.

Acceptance Criteria:
- 사용자가 condition result를 고르고 backtest, replay, decision까지 흐름을 유지할 수 있다.
- 페이지 간 visual language가 통일된다.
- in-app 설명문 대신 상태/라벨/명확한 액션으로 기능이 드러난다.
- 텍스트 겹침, 버튼 overflow, card nesting이 없다.

QA:
- Browser check: 1440x900, 1280x720, 390x844.
- Browser check: long strategy name, long error message, empty table, dense table.
- Manual UX rubric evidence screenshot set.

Commit Strategy:
- 커밋 제목: `대시보드 V3 전체 프로세스 UX를 정리`

## TODO 14 - Test Expansion For Functional Parity

Goal:
리모델이 목업 프리뷰에 머물지 않고 실제 V2 기능 계약을 호출한다는 테스트를 추가한다.

References:
- `tests/unit/test_dashboard_remodel_static.py`
- `tests/unit/test_dashboard_remodel_baseline_contract.py`
- `tests/unit/dashboard/test_backtest_ws_job.py`
- `tests/unit/dashboard/test_simulation_ws.py`
- `tests/unit/dashboard/test_research_pro.py`
- `tests/unit/dashboard/test_p2_structural.py`

Steps:
- V3 backtest adapter가 `/bt/run` payload를 기존 shape로 만들고 confirm 전에는 호출하지 않는 테스트를 추가한다.
- V3 replay adapter가 `/sim/ws`를 user start 전에는 열지 않는 테스트를 유지/확장한다.
- V3 condition API panel이 safe empty와 API error를 구분하는 테스트를 추가한다.
- V3 decision audit이 append-only route와 final approval route를 섞지 않는 테스트를 추가한다.
- whole-flow static contract test를 추가한다:
  - condition context -> backtest prefill
  - backtest result -> replay prefill
  - replay/audit context -> decision draft

Acceptance Criteria:
- 새 테스트가 실패하면 프리뷰 fallback, 자동 실행, route default flip, unsafe action regression을 잡는다.
- 기존 baseline/remodel tests가 계속 통과한다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q`
- `python -m pytest tests/unit/dashboard/test_backtest_ws_job.py tests/unit/dashboard/test_simulation_ws.py tests/unit/dashboard/test_research_pro.py tests/unit/dashboard/test_p2_structural.py -q`

Commit Strategy:
- 테스트 변경은 관련 기능 커밋에 포함한다. 마지막에 필요하면 `대시보드 V3 기능 동등성 검증을 보강` 커밋으로 분리한다.

## TODO 15 - Browser And Safety Verification

Goal:
unit/static test가 놓치는 실제 렌더링, interaction, safety regression을 확인한다.

References:
- `scripts/smoke_offline_gui.py`
- `scripts/verify_nonrelease_sync.py`
- `scripts/verify_pyd_gui_contract.py`
- `AGENTS.md`

Steps:
- 기존 dashboard app을 test/offline mode로 띄우는 가장 작은 명령을 확인한다.
- V3 remodel deep links를 직접 열어 주요 화면이 nonblank인지 확인한다.
- desktop/mobile viewport screenshot을 evidence에 저장한다.
- 다음 negative scenario를 확인한다:
  - `/ui` 기본은 V2.
  - `/ui/remodel/unknown`은 404.
  - reference/demo mode는 실행성 API를 호출하지 않음.
  - live mode API failure는 목업으로 대체하지 않음.
  - live order/broker/account controls 없음.
- nonrelease/pyd 관련 파일을 건드렸다면 해당 verifier를 실행한다.

Acceptance Criteria:
- 실제 브라우저에서 V3 주요 화면이 비어 있지 않고 텍스트/컨트롤 겹침이 없다.
- V2 기본 경로와 V3 명시 경로가 모두 의도대로 동작한다.
- protected/runtime path 변경이 없다.

QA:
- `python scripts/smoke_offline_gui.py`
- `python scripts/verify_nonrelease_sync.py` only if nonrelease paths touched.
- `python scripts/verify_pyd_gui_contract.py` only if GUI wrapper/pyd contract touched.
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

Commit Strategy:
- 커밋 제목: `대시보드 V3 안전 검증과 브라우저 확인을 보강`

## TODO 16 - Final Review, Scorecard, And Commit Stack Cleanup

Goal:
개발 완료 상태를 스스로 검증하고, 사용자가 이어서 검토/커밋/PR 작업을 할 수 있게 변경 범위를 정리한다.

References:
- `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`
- `docs/update_log/2026-06-30_dashboard_v3_ultragoal_codex_handoff.md`
- `AGENTS.md`

Steps:
- 기존 100점 scorecard 기준으로 완료 후 재평가 문서를 추가한다.
- 각 TODO evidence와 테스트 결과를 `.omo/evidence/dashboard-v3-functional-parity-20260701/`에 정리한다.
- `git diff --stat`, `git diff --check`, target test 결과를 final evidence에 남긴다.
- 변경 파일을 직접 검토해 unrelated change가 섞이지 않았는지 확인한다.
- 커밋 스택을 기능 단위로 정리한다.

Acceptance Criteria:
- V2 기능 관점 score가 90점 이상을 목표로 재평가된다. 미달 항목은 명시적인 residual risk로 남긴다.
- 모든 target QA 명령 결과가 기록된다.
- 커밋 단위가 작고 review 가능한 범위다.
- 사용자가 바로 `git show`와 테스트 evidence로 검토할 수 있다.

QA:
- `python -m pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q`
- `python -m pytest tests/unit/dashboard/test_backtest_ws_job.py tests/unit/dashboard/test_simulation_ws.py tests/unit/dashboard/test_research_pro.py tests/unit/dashboard/test_p2_structural.py -q`
- `pytest tests/unit/ -q` if shared backend/frontend contracts were touched broadly.
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

Commit Strategy:
- 마지막 커밋 제목: `대시보드 V3 완료 점검 결과를 기록`
- 커밋 본문에는 남은 risk, 실행한 테스트, protected path 무변경 여부를 포함한다.

## Final Verification Wave

- [x] F1 - Plan Compliance And Evidence Ledger Audit
- [x] F2 - Code Quality And Safety Review
- [x] F3 - Browser And Manual QA Artifact Review
- [x] F4 - Commit Stack And Protected Path Audit

## Recommended Commit Stack

1. `대시보드 V3 기준선과 구조를 정리`
2. `대시보드 V3 공통 UX 상태 체계를 정리`
3. `대시보드 V3 백테스트 실기능을 연결`
4. `대시보드 V3 차트 리플레이 실기능을 연결`
5. `대시보드 V3 조건 AI 상세 조회를 연결`
6. `대시보드 V3 분석 흐름과 의사결정 감사를 연결`
7. `대시보드 V3 전체 프로세스 UX와 검증을 보강`
8. `대시보드 V3 완료 점검 결과를 기록`

## Definition Of Done

- `/ui` 또는 기본 dashboard entry는 V2를 계속 제공한다.
- `/ui/remodel/*`에서 Backtest, Chart Replay, Condition AI, Audit/Decision 화면이 실기능을 제공한다.
- V3에서 reference/demo/live mode가 명확하고, live mode에서 목업 수치가 실제 실패를 덮지 않는다.
- V3에서 실행성 액션은 명시 confirm 전에는 호출되지 않는다.
- V3에서 websocket은 사용자가 시작한 작업 관찰/재생에만 열린다.
- V3에서 조건 AI -> 백테스트 -> 차트 리플레이 -> 의사결정 감사 handoff가 최소 1개 happy path로 동작한다.
- live order, broker login, account/balance control, KHOPENAPI connection, DB cutover, V3K gate advancement가 추가되지 않는다.
- 주요 unit/static/dashboard tests와 browser smoke가 evidence와 함께 통과한다.
- protected/runtime path 변경이 없다.
- 커밋은 한국어 메시지로 기능 단위로 쌓여 있다.

## Start-Work Guidance

이 계획을 실행할 때는 TODO 01부터 순서대로 진행한다. 중간에 V2 component 직접 재사용이 불가능하다고 확인되면, 기능 구현을 멈추지 말고 shared API/state adapter 추출 방식으로 전환한다. 단, 그 전환은 TODO 02 evidence에 기록한다.

권장 시작 명령:

```text
$start-work .omo/plans/dashboard-v3-functional-parity-20260701.md
```

High-accuracy review를 먼저 하려면 별도 reviewer/subagent 도구가 필요하다. 현재 세션에는 `spawn_agent`가 없으므로, 현 도구 표면에서는 바로 start-work 실행이 가장 현실적인 다음 단계다.
