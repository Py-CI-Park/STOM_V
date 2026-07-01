# 대시보드 리모델 기능 패리티 평가

## 기준

- 작업 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
- 리모델 URL: `http://127.0.0.1:8771/ui/remodel/`
- 비교 기준 기존 UI: `ai_strategy_loop/dashboard/frontend/*.jsx`와 FastAPI 라우트
- 리모델 구현 기준: `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`

## 결론

리모델 대시보드는 현재 **Phase A 격리형 시각 프리뷰 + 조건식 AI 일부 live bridge** 상태다. 기존 프로덕션 대시보드의 기능을 완전히 이전한 상태가 아니다. 특히 백테스트와 차트 리플레이는 기존 React 컴포넌트의 API/상태머신/실행 제어를 가져오지 않고 정적 카드·더미 데이터 중심으로 재현되어 기능 깊이가 크게 낮다.

## 왜 백테스트와 차트 리플레이가 약해 보이는가

| 영역 | 기존 대시보드 | 리모델 현재 상태 | 차이 원인 |
|---|---|---|---|
| 백테스트 데이터 연결 | `/bt/*` REST와 `/bt/ws_job` 사용 | `/bt/*` 미연결, 정적 `DATA.backtest` 표시 | 리모델 zip은 무빌드 static prototype이며 production BacktestTab을 이식하지 않음 |
| 조건식 CRUD | 전략 목록/전문 조회/검증/저장/삭제/변수 추출 | 코드 박스와 검증/저장/삭제 버튼 모양만 있음 | 실제 `BtDualEditor`, `BtLibraryPanel` 미사용 |
| 실행 제어 | `/bt/run`, `/bt/jobs`, `/bt/job`, cancel, job log, WS progress | 진행 중 작업 카드가 고정 더미 값 | `BtRunPanel`과 job manager contract 미이식 |
| 결과 분석 | result CSV 기반 summary/equity/distribution/heatmap/underwater/insights/MAE-MFE/orderflow/gui parity | 주요 지표와 차트가 SVG 예시 | `BtResultArea`, `bt-tab-analysis`, analysis endpoints 미연결 |
| 비교/포트폴리오 | A/B compare, overlay, portfolio combine, evo generation selector, HTML report | 타일 텍스트로만 표시 | production 분석 컴포넌트 미이식 |
| 차트 리플레이 데이터 | `/sim/days`, `/sim/stocks`, `/sim/signals`, `/sim/ws` | 정적 종목/캔들/신호 표시 | `SimulationTab` 상태머신 미이식 |
| 리플레이 제어 | WS start/pause/resume/speed/seek/stop, keyboard shortcut | 버튼 모양과 progress만 있음 | `/sim/ws` 프로토콜 미연결 |
| 차트 엔진 | live/LWC/SVG 엔진, split/overlay, 열/행 보존, render budget | 자체 SVG 캔들 mock | `SimChartByEngine`, `sim-live-chart`, localStorage 설정 미사용 |
| 학습/신호 | 신호 로드, 자동 일시정지, 신호 클릭 seek, signal log | 정적 로그와 auto pause 카드 | `SimLearningPanel`, `SimSignalLog` 미이식 |

## 조건식 AI에도 같은 문제가 있는가

조건식 AI는 백테스트/리플레이보다 낫지만, 완전 패리티는 아니다. 현재 live bridge는 `/health`, `/status`, `/runs`, `/ws` 중심이다. 기존 조건식 AI 대시보드의 많은 세부 라우트는 아직 정적 카드로 남아 있다.

| 조건식 AI 항목 | 기존 기능 | 리모델 현재 | 평가 |
|---|---|---|---|
| 현재 loop 상태 | `/status`, `/ws` | 연결됨 | 양호 |
| run 목록/history | `/runs` | 일부 매핑 | 부분 양호 |
| 세대 테이블 | LoopState generations 매핑 | 일부 매핑 | 부분 양호 |
| strategy code/diff/prompts | `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack` | inspector modal은 정적 코드 | 부족 |
| equity/backtest detail | `/equity_curves`, `/equity_curve`, `/backtest_detail` | chart mock 또는 일부 status 기반 | 부족 |
| HoF/reference | `/hall_of_fame`, `/reference_screenshots` | 정적 HoF | 부족 |
| 연구 기준/config | `/research_criteria`, `/config/spec` | 정적 criteria/config | 부족 |
| 운영/동결/포트폴리오 | `/ops_status`, `/freeze_verdict`, `/portfolio_sim`, `/portfolio_verdict` | 정적 패널 | 부족 |
| 레짐/부검/반사실/MC | `/regime_report`, `/autopsy`, `/counterfactual`, `/freeze_mc` | 정적 autopsy/tiles | 부족 |
| TMAP/feature 분석 | `/tmap_grid`, `/tmap_map`, `/edge_ratio`, `/feature_importance`, `/variable_correlation` | 연구실/워크벤치 시각 mock | 부족 |
| 결정 감사 | `/decisions`, `/record_decision` | append-only UI 모양만 있음 | 기능 미완 |
| 승인/export | human gate visible | hidden export 없음, 실제 승인 흐름 미이식 | 안전은 양호, 기능은 부분 |

## 점수 평가

### 기존 대시보드 대비 패리티 점수

| 영역 | 가중치 | 점수 | 근거 |
|---|---:|---:|---|
| 조건식 AI / 연구 루프 | 40% | 68/100 | live status/runs/ws는 연결됐지만 분석·코드·감사·연구실 API 상당수는 정적 |
| 백테스트 | 25% | 35/100 | 기존 `/bt/*` 실행·CRUD·결과분석·WS job 기능 대부분 미연결 |
| 차트 리플레이 | 20% | 38/100 | 기존 `/sim/*` inventory/signals/ws 상태머신 미연결, SVG mock 중심 |
| 공통 셸/안전/시각 IA | 15% | 82/100 | 레이아웃·탭·배지·안전 문구는 좋고 기존 route도 보존 |
| **총점** | **100%** | **56/100** | 시각 보존은 강하지만 기능 이전은 아직 절반 수준 |

### 현재 리모델 대시보드 자체 완성도 점수

| 평가 항목 | 점수 | 근거 |
|---|---:|---|
| 시각 디자인 | 88/100 | 밀도 높은 quant terminal 디자인과 탭 구조는 우수 |
| 정보 구조 | 80/100 | 주요 영역은 빠짐없이 배치됐지만 백테스트/리플레이는 실제 workflow depth 부족 |
| 안정성/실행성 | 84/100 | `/ui/remodel/` 실행, fallback, favicon, WS 연결 안정화 완료 |
| 백엔드 연동 | 45/100 | core status bridge만 있고 `/bt/*`, `/sim/*`, 다수 research API 미연결 |
| 상호작용 완성도 | 52/100 | 버튼/모달은 있으나 실제 저장·실행·seek·분석 동작 대부분 미구현 |
| 테스트/검증 | 76/100 | route/static/safety/dashboard tests와 캡처는 있음. 기능 E2E는 아직 없음 |
| **총점** | **72/100** | 독립 프리뷰로는 완성도 높지만 production replacement로는 미완 |

## 100점까지 부족한 점

| 부족 항목 | 패리티 감점 | 설명 |
|---|---:|---|
| `/bt/*` production 기능 미이식 | -18 | 백테스트 실행·CRUD·분석·비교·포트폴리오·리포트가 실제 동작하지 않음 |
| `/sim/*` production 기능 미이식 | -14 | 차트 리플레이의 핵심인 WS replay/seek/speed/signals가 mock임 |
| 조건식 AI 세부 분석 API 미연결 | -8 | code/diff/prompts/equity/autopsy/tmap/feature/correlation/decision API가 카드 표시로만 존재 |
| 기능 E2E 부족 | -6 | 실제 API를 누르고 결과가 변하는 브라우저 E2E가 없음 |
| 접근성/사용 흐름 | -3 | mock 버튼과 실제 버튼 구분이 부족해 사용자가 완성 기능으로 오인 가능 |
| DB 기반 검증 | -3 | wt-dev DB 또는 read-only DB로 실제 run/job/replay 데이터 검증이 아직 부족 |
| 문구 정확성 | -2 | 일부 card가 `상세 패널 구현`처럼 구현 완료로 오해될 수 있음 |

## 개선안

### P0 — 기능 패리티 회복

| 대상 | 개선안 | 완료 기준 |
|---|---|---|
| 백테스트 | 기존 `BacktestTab`을 remodel shell 안으로 이식하거나, 기존 컴포넌트를 유지한 채 CSS token만 remodel 디자인으로 매핑 | `/ui/remodel/`의 백테스트 탭에서 `/bt/health`, `/bt/strategies`, `/bt/run`, `/bt/jobs`, `/bt/result`, `/bt/ws_job` 실제 호출 확인 |
| 차트 리플레이 | 기존 `SimulationTab`을 remodel shell 안으로 이식하고 `SimControlBar`, `SimPlaybackBar`, `SimChartByEngine`, `SimSignalLog` 유지 | `/sim/days`, `/sim/stocks`, `/sim/signals`, `/sim/ws` 실제 replay 확인 |
| 조건식 AI | overview 정적 카드들을 기존 API 소비로 치환 | `/strategy_code`, `/strategy_diff`, `/backtest_detail`, `/edge_ratio`, `/feature_importance`, `/decisions` 등 최소 read-only 연결 |

### P1 — 기능 깊이와 검증

| 대상 | 개선안 | 완료 기준 |
|---|---|---|
| 백테스트 E2E | 전략 선택→validate→run→job progress→result→report 흐름 자동 테스트 | Playwright/Puppeteer smoke와 API mock/live 테스트 |
| 리플레이 E2E | 날짜→종목→전략→재생→pause/seek/speed→signal auto pause 검증 | 실제 또는 fixture DB 기반 캡처 |
| 시각 회귀 | 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`, `/ui/remodel` 캡처 비교 | tab별 screenshot baseline 갱신 |
| 기능 checklist | mock-only/real-connected 상태를 UI에 명시 | 실제 연결되지 않은 버튼에 `Preview only` 표시 |

### P2 — 완성도 향상

| 대상 | 개선안 |
|---|---|
| UX | 좌측 작업 흐름 wizard와 우측 결과 패널을 고정해 백테스트/리플레이 depth를 복구 |
| 데이터 | wt-dev `_database` read-only 참조 또는 fixture DB 복사로 realistic demo 제공 |
| 성능 | 기존 LWC/live chart render budget 재사용, 대량 종목 split/overlay 최적화 유지 |
| 안전 | 실거래/브로커/계좌 금지 문구 유지, write action은 기존 승인·확인 contract 재사용 |

## 판정

- 현재 리모델은 **좋은 디자인 초안이자 안전한 프리뷰**다.
- 그러나 현재 상태를 기존 대시보드의 대체물로 판단하면 **아직 부족하다**.
- 핵심 전략은 새로 다 만들기보다 기존 production 컴포넌트의 기능 로직을 유지하고, remodel shell·CSS·정보 구조를 입히는 방향이 맞다.
