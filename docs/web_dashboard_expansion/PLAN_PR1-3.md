# 웹 대시보드 확장 계획 — 백테스트 워크벤치 + 차트 시뮬레이션 (PR1~PR3)

> 작성: 2026-06-11 · 워크트리: `STOM_V.wt-webbt` · 기준 커밋: `e4de2825` (lazycodex/tick-sparse-positive-generation-improvement-20260604)
> 목표: 기존 조건식 진화 대시보드(`http://127.0.0.1:8770/ui/`)에 상단 탭 3개 체계를 도입하고,
> GUI 백테스트 전체 기능을 웹으로 옮긴 **백테스트 워크벤치 탭**과 일일 tick/min DB 기반
> **차트 시뮬레이션 탭**을 추가한다.

---

## 0. 배경 사실 (탐사 결과)

| 항목 | 사실 |
|------|------|
| 서버 | FastAPI `create_app()` — `ai_strategy_loop/dashboard/app.py` (2,970줄). `python -m ai_strategy_loop --port <p>` 로 기동 (기본 8770) |
| 라우터 컨벤션 | `research_api.py` 의 `APIRouter` → `app.include_router(research_router)` (app.py 1줄). 신규 기능도 동일 패턴 사용 |
| 프론트 | in-browser Babel JSX SPA. `frontend/index.html` 이 jsx 파일들을 script 태그로 로드, `window` 전역으로 컴포넌트 공유. 차트는 순수 SVG 자작(chart.jsx 1,658줄) |
| 탭 | 현재 탭 시스템 없음 — `app.jsx` 의 `App()` 이 전체 패널을 한 페이지에 렌더 |
| 백테스트 CLI | `stom_backtest.py` (subcommand: formula/strategy/optimize/sweep/wfo/…). 진화 루프는 `controller/loop.py` 의 검증된 subprocess 패턴으로 호출. 반복 실행용 `cli/warm_session.py` 존재 |
| 조건식 저장소 | `_database/strategy.db` — `stockbuy` / `stocksell` / `formula` 테이블. 경로는 `cli/paths.py` (`STOM_CLI_DATABASE_DIR`, `STOM_CLI_DB_*` env 오버라이드 지원) |
| 시세 DB | `_database/stock_tick_YYYYMMDD.db`, `stock_min_YYYYMMDD.db` (일일, 8~42MB), 통합본 `stock_tick_back.db`(28G)/`stock_min_back.db`(1.4G). **총 61GB → 복사 금지, 하드링크 공유** |
| 루프 상태 | `ai_strategy_loop/state/` (패키지 상대 — 워크트리별 자동 격리). `loop_runs.db`(WAL), `current_state.json`, 파생 서브셋 `tick_subset*.db`/`min_subset.db`(2.4G, 읽기전용) |
| 동시 개발 | wt-dev 에서 자율 개선 루프 개발이 활발히 커밋 중 (app.py 가 최다 수정 파일). **본 작업은 app.py 접점을 라우터 등록 줄 수준으로 최소화해야 머지가 안전** |

## 1. 환경 구성 (PR0 — 워크트리/DB, 코드 외 인프라)

- 워크트리: `C:/System_Trading/STOM/STOM_V.wt-webbt`, 브랜치 `feature/web-backtest-dashboard` (기준 `e4de2825`)
- 포트: **8771** (8770 은 wt-dev 의 라이브 진화 대시보드가 점유)
- DB: `scripts/setup_webbt_database.py` 로 구성
  - 하드링크(디스크 0): 일일 tick/min DB 전부, `stock_tick_back.db`, `stock_min_back.db`, `tick_subset*.db`, `min_subset.db`
  - SQLite online-backup 복사(활성 쓰기 안전): `strategy.db`, `setting.db`, `backtest.db`, `backtest_history.db`, `loop_runs.db`, 기타 소형 DB
  - 미반입: `current_state.json`, `STOP` (새 대시보드는 idle 시작)
- **하드링크 주의**: 링크된 시세 DB 에 쓰면 원본도 변경된다. 본 확장 기능은 시세 DB 를 읽기 전용(`mode=ro`)으로만 연다.

## 2. 아키텍처 원칙 (3 PR 공통)

1. **app.py 비대화 금지**: 신규 백엔드는 `dashboard/backtest_api.py`, `dashboard/simulation_api.py` (+ 보조 모듈)로 분리. app.py 에는 `include_router` 2줄만 추가. → wt-dev 와의 머지 접점 최소화 + 파일 800줄 규칙 준수.
2. **프론트 파일 분리**: 신규 탭은 `frontend/backtest.jsx`, `frontend/simulation.jsx` (+ 분할 파일). `app.jsx` 에는 탭 네비게이션 + 탭 분기 렌더만 추가.
3. **무예외 계약 유지**: 기존 엔드포인트 컨벤션(데이터 없으면 빈 구조 반환, 절대 500 으로 대시보드를 깨지 않음)을 신규 엔드포인트에도 적용.
4. **읽기/쓰기 경계**: 시세 DB·결과 데이터(`backtest/graph/`)는 읽기 전용. 쓰기는 `strategy.db`(조건식 CRUD)와 신규 잡 레지스트리에 한정.
5. **검증된 실행 경로 재사용**: 백테스트 실행은 `controller/loop.py` 의 subprocess 계약(`python -m cli.stom_backtest …`)을 그대로 따른다(Windows spawn 이슈 회피가 검증된 경로).

## 3. PR1 — 탭 셸 (작게, 빨리 머지해 충돌면 고정)

### 범위
- `frontend/app.jsx`: 상단 탭 네비게이션 `[진화 대시보드] [백테스트] [차트 시뮬레이션]`
  - 기존 콘텐츠 전체를 "진화 대시보드" 탭으로 래핑(동작 변화 0, JSX 이동 최소화)
  - 활성 탭은 localStorage 유지, 기본값 = 진화 대시보드
  - `useBackend`(WS) 는 App 레벨에 유지 — 다른 탭에 있어도 진화 상태 수신 지속
- `frontend/backtest.jsx` / `frontend/simulation.jsx`: 플레이스홀더 탭 컴포넌트(헬스 체크 표시)
- `frontend/index.html`: script 태그 2개 추가
- `dashboard/backtest_api.py`: `APIRouter(prefix="/bt")` 골격 + `GET /bt/health`
- `dashboard/simulation_api.py`: `APIRouter(prefix="/sim")` 골격 + `GET /sim/health`
- `app.py`: `include_router` 2줄
- 본 계획 문서 + `scripts/setup_webbt_database.py` 커밋

### 테스트 (DoD)
- 신규: `tests/unit/dashboard/test_tab_shell.py` — TestClient 로 `/bt/health`·`/sim/health` 200, `/ui/` 200, 기존 `/health`·`/status`·`/runs` 무영향
- 기존 `tests/unit/` 전체 통과, `scripts/verify_nonrelease_sync.py` 통과
- 서버 8771 기동 → 3탭 전환 수동 스모크

## 4. PR2 — 백테스트 워크벤치 (GUI 백테스트의 웹 이관 + 분석 강화)

### 백엔드 (신규 모듈 3개)
`dashboard/backtest_api.py` (라우트), `dashboard/backtest_jobs.py` (잡 매니저), `dashboard/backtest_analysis.py` (분석 함수 — 순수함수 위주로 단위테스트 용이하게)

| 엔드포인트 | 기능 |
|---|---|
| `GET /bt/strategies?kind=buy\|sell\|formula` | strategy.db 목록 (이름/활성/요약) |
| `GET /bt/strategy?kind&name` | 조건식 코드 전문 |
| `POST /bt/strategy` | 생성/수정 — `compile()` 문법 검증, 이름 규칙, 덮어쓰기 명시 플래그 |
| `POST /bt/strategy/validate` | 저장 없이 문법/금지 패턴 검증 |
| `DELETE /bt/strategy` | 삭제(확인 토큰 필수) |
| `GET /bt/data_range` | 백테 가능 날짜 범위·일일 DB 인벤토리 |
| `POST /bt/run` | 백테스트 잡 시작(subprocess, loop.py 계약 재사용) → job_id |
| `GET /bt/jobs` / `GET /bt/job?id` | 잡 목록/상태/진행률/로그 테일 |
| `POST /bt/job/cancel` | 잡 중지(프로세스 트리 회수 — loop manager 패턴 재사용) |
| `GET /bt/result?job_id` | 메트릭 + 자본곡선 + 일별손익 + 트레이드 목록 |
| `GET /bt/analysis/*` | 아래 분석 묶음 |

### 분석 묶음 (인사이트 강화 — 본 목표의 핵심)
- `summary`: 수익률·MDD·승률·payoff·profit factor·Sharpe/Calmar·연속 승/패·일평균 거래
- `distribution`: 트레이드 PnL 히스토그램, 보유시간 분포, 종목별 기여 Top/Bottom
- `heatmap`: 요일×시간대 손익 히트맵 (매수 시각 기준)
- `drawdown`: 언더워터 곡선 + 최대 낙폭 구간 표시
- `orderflow` (기본형): 진입/청산 시점 tick 기반 체결강도·거래량 프로파일 (tick 일일 DB 읽기 전용; 무거우면 샘플링)
- `insights`: 위 분석에서 규칙 기반 자동 인사이트 텍스트(최다 손실 시간대, 손실 상위 패턴, MDD 발생 구간 등)

### 프론트 (`backtest.jsx` + `backtest-analysis.jsx`, 파일당 800줄 이내 분할)
- 3-구역 워크벤치: ① 조건식 브라우저+코드 에디터(목록/검색/저장/검증) ② 실행 설정(기간·tick/min·수수료·범위) + 진행률(폴링) ③ 결과: 메트릭 카드 + 차트(자본곡선/일별손익/히스토그램/히트맵/언더워터 — 기존 SVG 차트 패턴 재사용·확장) + 인사이트 패널

### 테스트 (DoD)
- 분석 순수함수: 합성 트레이드 데이터로 단위테스트 (summary/distribution/heatmap/drawdown)
- CRUD: 임시 strategy.db 픽스처로 왕복 테스트 (생성→조회→수정→삭제, 검증 실패 케이스)
- 잡: 가짜 단명 커맨드로 라이프사이클(시작→상태→완료/취소)
- 실데이터 스모크: 짧은 기간 실제 백테스트 1회 실행 → result/analysis 엔드포인트 응답 확인
- 기존 `tests/unit/` 전체 통과

## 5. PR3 — 차트 시뮬레이션 (일일 DB 리플레이)

### 백엔드 (`dashboard/simulation_api.py` + `dashboard/replay_engine.py`)
| 엔드포인트 | 기능 |
|---|---|
| `GET /sim/days?src=tick\|min` | `_database` 의 일일 DB 인벤토리(날짜 목록) |
| `GET /sim/stocks?date&src` | 그날 존재 종목(테이블 목록) + 종목명(code_info.db) + 당일 등락 요약 |
| `WS /sim/ws` | 리플레이 세션 — `{action:start, date, codes[], src, speed, buy_name?, sell_name?}` → 서버가 시간순 bar/tick 이벤트 + 신호 이벤트 스트리밍. pause/resume/seek/speed 지원 |

- `replay_engine.py`: 일일 DB 를 읽기 전용으로 열어 시간순 병합 스트림 생성(다종목 동시), 배속 스케줄링, 다운샘플(tick 과밀 구간), 조건식 신호 평가기 연결
- 신호 평가: 1차 = 백테스트 엔진의 평가 프리미티브 재사용 가능 범위 조사 후 결정. 불가 시 명시된 단순화 계약(min bar 기준 평가)으로 시작하고 한계를 UI 에 표기 — **정직 우선**

### 프론트 (`simulation.jsx`)
- 날짜 선택(인벤토리에서) → 종목 선택(단일/복수, 당일 등락 정렬) → 재생 컨트롤(재생/일시정지/배속 1~100x/시킹)
- 캔들차트: **lightweight-charts standalone 번들 vendored** (`frontend/vendor-lightweight-charts.js`) — 캔들+거래량+매수/매도 마커+실시간 갱신은 자작 SVG 로 무리, 기존 vendor 방식과 동일하게 도입
- 다종목 동시 재생: 2×2 그리드, 종목별 신호 마커·체결 로그 패널

### 테스트 (DoD)
- 픽스처 일일 DB(소형 합성)로 replay_engine 단위테스트: 시간순 보장, 다종목 병합, seek, 다운샘플
- `/sim/days`·`/sim/stocks` 픽스처 테스트
- WS 세션 테스트(TestClient websocket): start→이벤트 수신→pause→stop
- 실데이터 스모크: 실제 일일 DB 1개로 재생 시작→이벤트 수신 확인

## 6. 브랜치/PR 전략

- 작업 브랜치: `feature/web-backtest-dashboard` (wt-webbt 단일 워크트리에서 순차 진행)
- 마일스톤마다 브랜치 포인터 생성 → **stacked PR 3개**:
  - `feature/web-bt-pr1-tab-shell` → base: `lazycodex/tick-sparse-positive-generation-improvement-20260604`
  - `feature/web-bt-pr2-workbench` → base: pr1
  - `feature/web-bt-pr3-simulation` → base: pr2
- **push / PR 생성은 사용자 허락 후에만** 수행한다(완료 보고에서 요청).

## 7. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| wt-dev 의 app.py/app.jsx 활발한 변경과 머지 충돌 | 신규 코드는 신규 파일로, 접점은 include_router·탭 등록 몇 줄. PR1 을 최소로 빨리 |
| 활성 쓰기 중 DB 복사 손상 | sqlite online-backup API 사용(완료: setup 스크립트) |
| 하드링크 시세 DB 오염 | 모든 시세 접근 `mode=ro` URI. 코드리뷰 체크 항목화 |
| Windows subprocess 특이점 | loop.py 의 검증된 호출 계약 그대로 재사용 |
| tick 일일 DB 과밀(42MB/일) 리플레이 렌더 부하 | 서버측 다운샘플 + 배속별 배치 전송 + min 모드 기본 |
| 조건식 평가 의미 차이(백테 엔진 vs 리플레이) | 엔진 프리미티브 재사용 우선, 불가 시 한계를 UI·문서에 명시 |
| in-browser babel 로딩 증가 | 파일 분할 유지(개당 수백 줄), 캐시 무력화는 기존 no-cache 미들웨어가 처리 |

## 8. 검증 게이트 (전 PR 공통, 머지 전)

1. `python -m pytest tests/unit/ -q` 전체 통과
2. `python scripts/verify_nonrelease_sync.py` 통과
3. 서버 8771 기동 스모크: `/health`, `/bt/health`, `/sim/health`, `/ui/` + 3탭 전환
4. wt-dev(8770) 라이브 대시보드 무영향(프로세스·DB 락 충돌 없음) 확인
5. `backtest/graph/` 무변경 (`git status` 검사)
