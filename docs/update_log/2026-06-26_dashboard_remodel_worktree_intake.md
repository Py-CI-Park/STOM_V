# 대시보드 리모델 워크트리 인수·구현 계획

## 기준 시점

- 작업 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
- 작업 브랜치: `feature/dashboard-remodel-20260626`
- 기준 커밋: `5a68e2ad6 프로세스 연구 중간 점검 문서화`
- 원본 개발 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dev`
- 리모델 기준 압축 파일: `C:/Users/parkc/Downloads/stom-ai-dashboard-frontend-reviewed.zip`
- 압축 파일 내부 루트: `stom-ai-dashboard-frontend/`

## 현재 프로덕션 대시보드 기능 기준

프로덕션 대시보드는 `ai_strategy_loop/dashboard/app.py`의 FastAPI 라우트와 `ai_strategy_loop/dashboard/frontend/`의 빌드된 프론트엔드가 정본이다. 현재 기능 보존 기준은 다음이다.

### 전역 셸

- 제목, Backend Base URL, 재연결, REST/WebSocket 상태 배지
- Run status, route owner/boundary strip, theme toggle
- 상위 탭: `조건식 AI`, `백테스트`, `차트 리플레이`
- 조건식 AI 하위 탭: `조건식 AI`, `프로세스`, `히스토리`, `연구실`, `분석 워크벤치`, `결정 감사`
- LIVE/archive run selector, 세대 진행률, provider, timeframe, run_id
- 시작/정지, 설정 모달, human approval gate, append-only audit cue

### 조건식 AI

- live generation, active strategy, phase timeline, process flow, phase detail
- research criteria, glossary, active config, engine summary, cost/tokens
- fitness/profit/equity/backtest detail/GUI parity/quality charts
- Hall of Fame, generation table, strategy code viewer, Best/Winner card
- final approval dialog, export status, feedback/autopsy
- hypothesis, discovery, population, lineage, meta, holdout, generation analytics

### 프로세스 / 히스토리 / 연구실 / 워크벤치 / 감사

- 프로세스 그래프, 단계 설명, 실시간 로그와 카탈로그
- run/gen archive, research records, ResultDetail, Compare, lineage search
- Edge Ratio, 변수 중요도, 상관관계, 변수 조합, 검증, 위키, AI context
- 후보 심층 분석, HoF workbench, 히트맵, history/backtest handoff
- PROMOTE checklist, OOS CI, alerts, regime, revival registry, V6/M4, append-only decisions

### 백테스트 / 차트 리플레이

- 조건식 CRUD, validate/save/delete, 변수칩, 라이브러리, BackFinder preflight
- 백테스트/최적화/WFO/스윕 실행, self.vars → sweep builder, active job, log tail
- 결과 라이브러리, tags/memo/favorite, metrics/charts/insights/MAE-MFE/orderflow/GUI parity
- A/B compare, multi-job overlay, portfolio combine, evo generation selector, HTML report
- tick/min day inventory, stock selection, strategy signal overlay, WS replay, split/overlay charts
- indicators, signal log, auto-pause learning, indicator table, variable watch

## reviewed zip 분석 결과

압축 파일은 외부 의존성이 없는 vanilla HTML/CSS/JS 정적 프로토타입이다.

- `index.html`: 실행 진입점
- `styles/theme.css`: 리모델 디자인 토큰과 레이아웃
- `src/data.js`: 더미 데이터
- `src/app.js`: 전 탭 렌더러, 모달, SVG 차트, 히트맵, 캔들 차트
- `data/stom-dummy-data.json`: API 대체 데이터
- `docs/*`: 아키텍처, 데이터 계약, UI 구현 사양, 탭 보존 체크리스트
- `tests/*`: 수동 QA 체크리스트와 캡처 스크립트 초안

핵심 제약은 프로덕션과 동일하다.

- 실거래 주문 버튼 금지
- 브로커 로그인 금지
- 계좌/자산 연동 금지
- 자동 프로덕션 export 금지
- human approval gate 유지
- decision audit append-only 유지

## 이번 커밋의 구현 방향

1. 기존 프로덕션 대시보드는 그대로 보존한다.
2. reviewed zip 전체를 `ai_strategy_loop/dashboard/frontend/remodel/`에 격리된 리모델 번들로 추가한다.
3. `/ui/remodel/`에서 새 디자인을 열 수 있게 한다. 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 변경하지 않는다.
4. 정적 더미 데이터 기반 화면을 유지하되, 같은 origin FastAPI 백엔드가 있으면 다음 live bridge를 적용한다.
   - `GET /health`
   - `GET /status`
   - `GET /runs`
   - `WS /ws`
5. live bridge는 shell 상태, run status, provider, timeframe, run_id, 세대 진행률, live message, generation table, fitness/profit/quality series, history run table을 갱신한다.
6. start/stop/export 같은 변경성 액션은 기존 프로덕션 UI의 승인 절차가 정본이다. 리모델 번들의 변경성 액션은 hidden export path를 만들지 않는다.

## 단계별 완성 계획

### Phase A — 격리형 리모델 프리뷰

- reviewed zip 산출물 보존
- live status bridge 적용
- node syntax check
- static route visual QA
- 안전 금지어/금지 UI 회귀 검사

### Phase B — 프로덕션 컴포넌트 이식

- `styles/theme.css` 토큰을 기존 `styles.css` 디자인 토큰과 병합
- GlobalShell 리디자인을 기존 React App shell에 적용
- 기존 route contract(`ui-contract.jsx`)는 유지
- 기존 panels/chart/backtest/simulation 컴포넌트를 한 번에 폐기하지 않고 페이지별로 치환

### Phase C — 기능 parity 잠금

- 모든 기존 REST/WS 엔드포인트별 프론트 소비 경로 체크
- settings, strategy inspector, approval dialog, code/diff/prompts/context 확인
- backtest CRUD/run/result/compare/portfolio/report 확인
- simulation replay WS/playback/indicators/signals 확인
- audit append-only와 final approval 분리 확인

### Phase D — 시각 검증과 PR 준비

- Chromium 캡처: `/ui/remodel/`, `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`
- 탭별 스크린샷: overview/process/history/lab/workbench/audit/backtest/replay
- `pytest tests/unit/test_dashboard* -q`
- `python scripts/smoke_offline_gui.py`
- `git diff --check`
- 금지 UI 문자열 검사: live order, broker login, account trading, automatic production export

## DB 사용 계획

- 우선 리모델 프리뷰는 DB 없이 동작한다.
- 프로덕션 기능 검증 시 새 워크트리의 `_database/`를 직접 만들지 않고, 필요하면 환경변수 또는 테스트 실행 위치를 통해 `wt-dev`의 `_database`를 읽기 전용으로 참조한다.
- 운영 DB 쓰기, live broker, 주문/계좌 UI는 이번 범위에서 금지한다.

## 구현 결과

- reviewed zip 전체를 `ai_strategy_loop/dashboard/frontend/remodel/`에 추가했다.
- `ai_strategy_loop/dashboard/app.py`에 `/ui/remodel/` 정적 마운트를 추가했다.
- `src/app.js`에 프로덕션 백엔드 live bridge를 추가했다.
  - `GET /health`, `GET /status`, `GET /runs`, `WS /ws`
  - 기존 더미 데이터는 fallback으로 유지한다.
  - 정적 프리뷰(`/health` 실패)에서는 WebSocket을 열지 않고 `백엔드 미연결 · 정적 프리뷰` 상태로 멈춘다. background job에서 확인된 `/ws` 반복 404를 제거했다.
  - hidden final approval/export 경로는 만들지 않았다.
- `index.html`에 data URI favicon을 추가해 `/favicon.ico` 자동 요청 404 로그가 반복되지 않게 했다.
- `tests/unit/test_dashboard_remodel_static.py`를 추가해 번들 존재, IA 보존, route serving, live bridge, 안전 제약을 잠근다.

## 검증 결과

- `node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js && node --check ai_strategy_loop/dashboard/frontend/remodel/src/data.js` — 통과
- `pytest tests/unit/test_dashboard_remodel_static.py -q` — 5 passed
- `pytest tests/unit/test_dashboard* -q` — 325 passed
- `python scripts/smoke_offline_gui.py --branch feature/dashboard-remodel-20260626 --version dashboard-remodel --offline` — 통과. Qt font 경고와 KHOPENAPI 후보 부재 오류 로그는 오프라인 GUI 환경 경고이며 스크립트는 `[OK] offline GUI smoke passed`를 반환했다.
- `git diff --check` — 통과
- `pytest tests/unit/ -q` — 실패. 첫 실패는 `tests/unit/test_backtest_button_contract.py::test_backtest_constructor_contract_is_small_and_queue_driven`의 기존 BackTest 생성자 계약 불일치이며, 이번 변경 파일(`ai_strategy_loop/dashboard/...`, `docs/...`, `tests/unit/test_dashboard_remodel_static.py`)과 직접 관련 없는 백테스트 레거시 계약 실패다. 관련 대시보드 테스트는 별도로 통과했다.
- `uvicorn ai_strategy_loop.dashboard.app:app --port 8772` 실서버 smoke에서 `GET /ui/remodel/` — 200 OK
- 8782 정적 서버 프리뷰에서 4초 대기 후 `백엔드 미연결 · 정적 프리뷰` 표시 확인. 서버 로그는 `/health` 1회 404와 favicon 404만 발생했고 `/ws` 반복 404는 재현되지 않았다.
- 2026-06-27 직접 실행: `python -m uvicorn ai_strategy_loop.dashboard.app:app --host 127.0.0.1 --port 8771 --app-dir C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel` — 실행 중. `GET /health`는 `200 {"status":"ok","contract_version":2}`, `GET /ui/remodel/`은 `200 text/html`을 반환했다.
- 2026-06-27 favicon 보정 후 재검증: `pytest tests/unit/test_dashboard_remodel_static.py -q` — 5 passed, `pytest tests/unit/test_dashboard* -q` — 325 passed, `git diff --check` — 통과. Chromium 재접속 후 서버 로그에서 `/ui/remodel/`, `/health`, `/status`, `/runs`, `/ws`만 확인했고 추가 `/favicon.ico` 404는 발생하지 않았다.

## 시각 확인

정적 프리뷰 서버(`python -m http.server 8781 --directory ai_strategy_loop/dashboard/frontend/remodel`)에서 Chromium 1920x1080 캡처를 수행했다.

- `artifacts/dashboard-remodel-20260626/overview.png`
- `artifacts/dashboard-remodel-20260626/process.png`
- `artifacts/dashboard-remodel-20260626/history.png`
- `artifacts/dashboard-remodel-20260626/lab.png`
- `artifacts/dashboard-remodel-20260626/workbench.png`
- `artifacts/dashboard-remodel-20260626/audit.png`
- `artifacts/dashboard-remodel-20260626/backtest.png`
- `artifacts/dashboard-remodel-20260626/replay.png`
- `artifacts/dashboard-remodel-20260626/settings-modal.png`
- `artifacts/dashboard-remodel-20260627-live-route.png`
