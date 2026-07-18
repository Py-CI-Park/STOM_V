# V5.5 IA 통합 실행 계약

## 목적

정본 대시보드 목적지를 **Live · Backtest · Replay · History · 성과 · Reports** 여섯 개로 고정하고, Lab/Workbench/Context에 흩어진 기존 읽기 전용 연구 근거를 새 소유자에 손실 없이 이관한다. 새 API·publisher·집계 경로를 만들지 않으며 Audit 거버넌스, human approval/export 경계, prototype 비권위 상태를 유지한다.

## 실행 소유권

| 원본 표면 | 정본 소유자 | 재사용 컴포넌트/입력 | 이관 상태 계약 | 비대상 |
|---|---|---|---|---|
| Lab 팩터 히트맵 | Live 백테스트 단계 | `ResearchHeatmapPanel(baseUrl, wsStatus, runId)` · 기존 `GET /edge_ratio` | 같은 값·축·단위·tooltip·loading/empty/error | 신규 endpoint, 클라이언트 재계산 |
| Lab Edge/변수 분석 | History | `ResearchLabPanel(baseUrl, wsStatus, runId)`의 기존 읽기 전용 탭 | `loop_run:`에서만 정확한 run ID를 사용하고 campaign/선택 없음은 명시적 unavailable | campaign ID 추측, 새 publisher |
| Workbench 후보 분석·비교 | History | `ResearchProPanel`, `RunComparePanel` | History의 별도 legacy run/gen 비교 영역에 배치; governed identity와 혼합 금지 | 승급·운영 반영 |
| Workbench 명예의 전당 | 성과 | `HallOfFamePanel`, `HofInventoryGate` | 성과 정본은 Hall-of-Fame 전용 | 후보 분석·비교 중복 |
| Lab Wiki | History + Reports | `ResearchWikiPanel(baseUrl, wsStatus, runId)` · 기존 `/research_docs`, `/research_doc` | 원문 inert 표시, reference-only 경고, Reports iframe CSP/sandbox 불변 | HTML 실행, 문서 쓰기 |
| Context 탭 | 셸 개발자 drawer | `AIContextPanel(baseUrl, wsStatus, runId, genNo)` | 기본 닫힘, URL/뒤로가기/Escape/포커스 복귀, current run/gen | Live 연구 상세 drawer와 ID/상태 공유 |
| Audit/Verdict | History | 기존 `AuditDecisionTrace`, `VerdictPanel` | append-only 결정·human gate 그대로 유지 | 감사 삭제·자동 판정 |
| Alpha/Catalog | 내부 prototype | 기존 rollback 컴포넌트 | 명시적 rollback에서만 복구; V5.7 전 비권위 | 정본 승격 |

## 대상 파일과 경계

| 구분 | 대상 | 계약 |
|---|---|---|
| 셸/라우팅 | `frontend/dashboard-v4-shell.jsx`, `frontend/dashboard-inventory.jsx`, `frontend/v4.css` | 여섯 레일, canonical query rewrite, localStorage 1회 migration, popstate, keyboard, developer drawer, 명시적 default-OFF rollback |
| Live | `frontend/v4-research.jsx` | 기존 백테스트 단계에 Lab 히트맵 dual-mount; 기존 필드와 fetch 경로 재사용 |
| History | `frontend/v4-history.jsx` | legacy run/gen 선택과 governed `selectedResearchId`를 분리한 채 분석·비교·Wiki를 이관 |
| 성과 | `frontend/v4-workbench.jsx` | Hall-of-Fame-only |
| Reports | `frontend/v4-reports.jsx` | Wiki sibling section 추가, sandboxed report iframe 불변 |
| 호환 표면 | `frontend/v4-lab.jsx`, `frontend/dashboard-pages.jsx`, `lab.html`, `pro.html` | 삭제하지 않고 explicit rollback/standalone 호환 유지 |
| 테스트 | `tests/unit/dashboard/test_v4_ui_foundation.py`, `test_v4_lab_workbench_contract.py`, `test_v4_replay_history_ui.py`, `test_shell_wiring_parity.py`, Reports/Wiki 관련 테스트 | source 계약 + runtime JSX + 브라우저 evidence |

## 라우팅·상태 계약

| 입력 | rollback OFF 결과 | rollback ON (`v4_legacy_extras=1`) |
|---|---|---|
| canonical six-tab query/path | 동일 정본 목적지 | 동일 정본 목적지 |
| `audit`, `records`, `verdict`, `governance` | `history`로 canonical rewrite | `history` |
| `lab` | `history`로 migration | legacy Lab 복구 |
| `context` | 기존 정본 목적지를 유지하고 developer drawer 열기 | legacy Context 탭 복구 |
| `alpha` | `research` 내부 prototype 표식으로 rewrite | legacy Alpha 복구 |
| `catalog` | `reports` 내부 prototype 표식으로 rewrite | legacy Catalog 복구 |
| stale `stom_active_tab` / `stom_active_evolution_tab` | URL이 없을 때 한 번만 소비해 정본 목적지로 전환하고 retired 값 제거 | rollback을 영속 활성화하지 않음 |
| unknown | Live로 fail-closed | Context catch-all 금지 |

URL/query가 localStorage보다 우선한다. canonical rewrite는 관련 없는 `base`, `run_id`, `dashboard_version` 쿼리를 보존한다. 사용자의 탭 이동은 `pushState`, migration은 `replaceState`, `popstate`는 탭·drawer 상태와 포커스를 복구한다.

## 수용 fixture와 검증

| 영역 | fixture/행동 | 통과 기준 |
|---|---|---|
| Dual mount | 동일 `/edge_ratio`, `/feature_importance`, `/variable_correlation`, Wiki 응답 | 원본/정본 값·단위·상태·interaction field parity |
| Identity | `loop_run:run-1`, `campaign:campaign-1`, 늦은 응답 | loop_run만 분석 run ID로 사용; campaign은 unavailable; 늦은 응답 덮어쓰기 없음 |
| IA | 정상 URL, retired query/path, malformed/unknown, rollback 0/1 | 정상은 6개, rollback 1만 legacy extras 복구, unknown fail-closed |
| Navigation | 탭→drawer open/close→History→뒤/앞 | URL·활성 패널·drawer·포커스 일치 |
| Keyboard | ArrowLeft/Right, Home/End, Enter/Space, Escape | roving tab, 44px target, drawer trigger/close/포커스 복귀 |
| 성과 | HOF payload와 빈/오류 응답 | HOF + inventory만 존재, compare/analysis 없음 |
| Reports/Wiki | allowlisted docs와 악성 markdown/HTML | Wiki inert, report CSP `default-src 'none'`, `sandbox=""` 불변 |
| Browser | 1920×1080, 2560×1440, 3440×1440 | 가로 overflow 0, 여섯 rail, retired rail 없음, zero console/page error |

## Feature flag와 rollback

- 기존 query flag `v4_legacy_extras=1`만 사용한다.
- 기본값은 OFF이며 localStorage, API, 서버 설정으로 영속하지 않는다.
- rollback ON에서 Lab/Context/Alpha/Catalog 기존 컴포넌트와 키보드 순서를 복구한다.
- parity·redirect·back/forward·localStorage·keyboard 증거가 없으면 legacy 소스/standalone/CSS를 삭제하지 않는다.

## 완료 증거

1. focused IA/History/Reports tests와 runtime JSX/typecheck/build.
2. bundle/manifest content hash 갱신.
3. 세 viewport browser transcript·스크린샷·DOM metrics.
4. ai-slop-cleaner zero blocker.
5. architect 3-lane `CLEAR/APPROVE`와 executor QA/e2e/red-team `passed`.
6. protected/runtime/trading 경로 무변경과 명시적 staging/Korean commit.
