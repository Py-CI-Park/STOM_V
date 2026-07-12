# 대시보드 리모델 100점 기준 상세 채점표와 전체 페이지 개선안

## 목적

현재 `/ui/remodel/` 리모델 프리뷰를 기존 프로덕션 대시보드와 비교해 페이지·기능 단위로 재채점하고, **기존 대비 100점 패리티**와 **리모델 자체 완성도 100점**에 도달하기 위한 구체적 개발 지침을 정리한다.

## 점수 기준

| 점수 종류 | 의미 | 100점 조건 |
|---|---|---|
| 기존 대비 패리티 점수 | 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`가 가진 실제 기능을 리모델이 얼마나 이전했는지 | 기존 API, 상태머신, 저장/실행/분석/캡처 동작이 모두 리모델 shell 안에서 동일하게 동작 |
| 리모델 자체 완성도 점수 | 기존과 비교하지 않고 현재 리모델 UI 자체가 얼마나 완성된 제품처럼 보이고 동작하는지 | mock/preview와 실제 기능 구분이 명확하고, 모든 버튼이 의도한 동작 또는 명시적 disabled 상태를 가짐 |

## 전체 정밀 재채점

이전 요약 채점은 기존 대비 `56/100`, 자체 완성도 `72/100`이었다. 페이지별 기능 세부 항목을 더 엄격히 분해하면 다음과 같다.

| 페이지/영역 | 가중치 | 기존 대비 패리티 | 가중 점수 | 자체 완성도 | 가중 점수 | 핵심 판단 |
|---|---:|---:|---:|---:|---:|---|
| 공통 셸/라우팅/안전 | 8 | 84 | 6.72 | 86 | 6.88 | 디자인과 안전 문구는 좋고 서버 연결도 됨 |
| 조건식 AI Overview | 18 | 70 | 12.60 | 78 | 14.04 | `/status`, `/runs`, `/ws`는 연결됐지만 세부 분석은 정적 |
| 프로세스 | 6 | 62 | 3.72 | 74 | 4.44 | 프로세스 맵은 보이나 실제 pipeline/status depth 부족 |
| 히스토리 | 7 | 62 | 4.34 | 73 | 5.11 | run list 일부 매핑, compare/detail lineage는 부족 |
| 연구실 | 8 | 58 | 4.64 | 72 | 5.76 | heatmap/importance/correlation은 시각 mock 중심 |
| 분석 워크벤치 | 7 | 55 | 3.85 | 72 | 5.04 | HoF/candidate 분석은 보이나 실제 handoff 부족 |
| 결정 감사 | 8 | 52 | 4.16 | 70 | 5.60 | append-only UI는 있으나 `/decisions`, `/record_decision` 미이식 |
| 백테스트 | 20 | 35 | 7.00 | 62 | 12.40 | 기존 production 대비 가장 큰 결손 |
| 차트 리플레이 | 15 | 38 | 5.70 | 64 | 9.60 | 기존 WS replay 상태머신 결손 |
| 설정/모달/보조 | 3 | 75 | 2.25 | 80 | 2.40 | 설정 모달은 보기 좋지만 실제 config contract 일부만 |
| **총점** | **100** |  | **54.98 ≈ 55/100** |  | **71.27 ≈ 71/100** | 현재는 프리뷰 단계 |

## 결론 점수

| 평가 기준 | 점수 | 판정 |
|---|---:|---|
| 기존 대시보드 대비 기능 완전 이전 | **55/100** | 기존 대시보드 대체 불가. 기능 로직 이식 필요 |
| 현재 리모델 자체 완성도 | **71/100** | 디자인 프리뷰로는 양호. 실제 제품 기능은 미완 |
| 100점까지 남은 핵심 | **45점** | 백테스트, 리플레이, 조건식 AI 세부 API, 감사/결정, E2E 검증 |

## 공통 셸 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 100점 개선 조건 |
|---|---|---|---:|---:|---|
| Header/title | STOM AI dashboard title | 구현 | 100 | 95 | 유지 |
| Backend Base URL | baseUrl 입력과 연결 | 구현, localStorage 저장 | 90 | 90 | 연결 오류 상세 표시 추가 |
| REST/WS badge | 실제 상태 표시 | `/health`, `/ws` 연결 | 85 | 88 | 백테스트/리플레이 별도 health도 함께 표시 |
| Route owner/boundary | owner/boundary 명시 | 구현 | 90 | 90 | 페이지별 owner contract hover 추가 |
| Top tabs | 조건식/백테스트/리플레이 | 구현 | 95 | 90 | 기존 URL deep-link와 동기화 |
| LIVE/ARCHIVE selector | run selector와 archive mode | UI만 부분 | 55 | 70 | 실제 run selector와 `/run_state` 연결 |
| Start/Stop | 루프 control과 연결 | WS control fallback만 | 50 | 65 | 실제 control action 결과/권한/에러 표시 |
| Settings modal | config spec, GPT auth test | 정적 preview 중심 | 55 | 75 | `/config/spec`, `/gpt_auth/status`, `/gpt_auth/test` 실제 연결 |
| Safety cues | 연구 전용, no live order | 구현 | 95 | 95 | 유지 |

## 조건식 AI 전체 상세 채점

| 기능 | 기존 API/컴포넌트 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| 현재 loop 상태 | `/status`, `/ws` | 연결됨 | 85 | 85 | phase별 raw payload drilldown 추가 |
| 세대 진행률 | LoopState current/target | 일부 매핑 | 75 | 80 | 목표/현재/elapsed/ETA 정확 매핑 |
| 활성 전략 카드 | current/best/winner strategy | 일부 매핑 + mock | 65 | 78 | 실제 best/winner source 분리 |
| 세대 테이블 | generations rows | 일부 live 매핑 | 75 | 80 | 정렬, 필터, 클릭 상세, code/backtest action 연결 |
| phase timeline | process/phase detail | 정적 timeline | 55 | 75 | 실제 phase status와 duration 연결 |
| research criteria | `/research_criteria` | 정적 | 35 | 70 | API mode별 criteria 표시 |
| glossary/config | `/config/spec`, glossary | 정적 | 35 | 72 | config schema 기반 렌더 |
| engine/cost/tokens | loop metadata/cost | 대부분 정적 | 45 | 75 | 실제 provider/model/token/cost 반영 |
| fitness/profit/equity charts | `/equity_curves`, `/equity_curve` | 일부 series, 대부분 mock | 55 | 78 | run/gen selector 기반 실제 시계열 |
| backtest detail | `/backtest_detail` | mock chart | 35 | 72 | daily profit/cumulative/drawdown fetch |
| GUI parity | `/evolution_gui_parity` | mock | 30 | 70 | 시간대/요일/품질 실제 분석 |
| Hall of Fame | `/hall_of_fame` | 정적 | 35 | 75 | human/AI HoF 통합 fetch |
| strategy inspector | `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack` | 정적 modal | 35 | 78 | 코드/diff/prompt/context 탭 실제 연결 |
| approval/export | 기존 승인 분리 | 안전 문구는 있음, 실제 흐름 미이식 | 55 | 75 | hidden export 없이 human approval dialog contract 재사용 |
| analysis tiles | hypothesis/discovery/autopsy/population/lineage/meta/holdout/gen analytics | 값 대부분 정적 | 45 | 78 | 각 endpoint 연결 및 unavailable 상태 명시 |

### 조건식 AI 100점 목표

- `/status`, `/ws`, `/runs` 외에 다음 read-only API를 실제 연결한다.
  - `/run_state`, `/generation_durations`, `/run_yearly`
  - `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack`
  - `/equity_curves`, `/equity_curve`, `/backtest_detail`, `/evolution_gui_parity`
  - `/hall_of_fame`, `/reference_screenshots`
  - `/autopsy`, `/selector_preview`, `/counterfactual`, `/freeze_mc`
  - `/tmap_grid`, `/tmap_map`, `/edge_ratio`, `/feature_importance`, `/variable_correlation`
- 세대 테이블 row click이 inspector, backtest handoff, workbench handoff를 실제 수행한다.
- mock card는 `Preview only` 또는 `연결 대기`로 표시한다.

## 프로세스 페이지 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| Process map | pipeline/progress 시각화 | React Flow 스타일 mock | 60 | 82 | `/pipeline_status`, `/ops_status` 연결 |
| live logs | 실행 로그/카탈로그 | 정적 로그 | 45 | 70 | 실제 loop/event log tail 연결 |
| route contract | boundary contract | 표시됨 | 75 | 82 | pageOwnerContract 기반 동적 contract 표시 |
| node catalog | process catalog | 정적 | 55 | 72 | catalog source 문서/API 연결 |
| metadata | run metadata | 정적 | 55 | 72 | 선택 run에 따라 metadata 교체 |

### 프로세스 100점 목표

- 각 phase node가 실제 status/duration/error를 표시한다.
- node 클릭 시 해당 단계 로그, 입력/출력 artifact, 재시도 가능 여부를 표시한다.
- process map export는 실제 JSON/PNG를 생성하거나 preview-only로 명확히 표시한다.

## 히스토리 페이지 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| run archive | `/runs` | 일부 매핑 | 70 | 78 | 필터/정렬/페이지네이션 추가 |
| run detail | `/run_state` | 정적 detail | 45 | 70 | 선택 run detail fetch |
| compare | `/runs/compare`, `/bt/compare` | launcher mock | 40 | 68 | 다중 run compare 실제 연결 |
| lineage search | docs/update_log/registry lineage | 정적 검색 | 45 | 72 | client index 또는 API 연결 |
| research records | research index/records | 정적 | 55 | 72 | 기존 ResearchIndexPanel 이식 |
| ResultDetail | result preview | 정적 metrics | 55 | 75 | 선택 run/gen 결과 fetch |

### 히스토리 100점 목표

- run 선택 → detail → compare → backtest result handoff가 끊기지 않아야 한다.
- archive table에서 label/status/gate/score/pf/mdd/pnl/date를 실제 값으로 표시한다.
- lineage search는 `docs/update_log`, `CARRY_FORWARD_REGISTRY`, campaign id를 찾아야 한다.

## 연구실 페이지 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| active/stalled runs | `/ops_status` | mock sidebar | 45 | 70 | active/stalled/batch queue 실제 연결 |
| freeze verdict | `/freeze_verdict` | 정적 요약 | 45 | 72 | verdict lines/alerts 실제 표시 |
| Edge Ratio | `/edge_ratio` | mock heatmap | 45 | 78 | run/gen/mode별 heatmap fetch |
| Feature importance | `/feature_importance` | mock bar | 45 | 75 | permutation/axis options 연결 |
| Correlation | `/variable_correlation` | mock heatmap | 45 | 75 | method 선택, missing 표시 |
| Validation/Holdout | holdout/freeze endpoints | mock | 50 | 75 | holdout result와 OOS 신뢰구간 연결 |
| Wiki/AI context | ResearchWikiPanel, AIContextPanel | 정적 card | 55 | 75 | 기존 패널 이식 |

### 연구실 100점 목표

- 기존 `ResearchLabPanel`, `ResearchWikiPanel`, `AIContextPanel`, `VisualQualityPanel` 기능을 유지한 채 리모델 디자인만 적용한다.
- 모든 heatmap은 실제 fetch 실패 시 빈 mock이 아니라 `데이터 없음/endpoint 실패`를 표시한다.

## 분석 워크벤치 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| candidate selector | run/generation 후보 선택 | mock candidates | 45 | 75 | HoF/selected generation 연결 |
| candidate deep analysis | equity, IC, risk/return, distribution | mock charts | 50 | 78 | `/equity_curve`, `/autopsy`, `/counterfactual` 연결 |
| heatmap | year/month heatmap | mock | 55 | 78 | run 결과 기반 heatmap |
| evidence notes | evidence handoff | 정적 notes | 50 | 72 | artifact/doc links 연결 |
| backtest handoff | history/backtest handoff | 버튼 모양 | 35 | 65 | localStorage/event 기반 실제 handoff |
| review queue | review queue | 정적 | 45 | 70 | decision audit와 연결 |

### 워크벤치 100점 목표

- 후보 선택 기준, 증거 링크, 백테스트 전송, 결정 감사 전송이 실제 동작해야 한다.
- 후보별 `왜 선택/보류/폐기`가 audit trail로 이어져야 한다.

## 결정 감사 상세 채점

| 기능 | 기존 기능 | 리모델 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| decision ledger | `/decisions` | 정적 table | 40 | 70 | 실제 append-only ledger fetch |
| decision submit | `/record_decision` | 버튼 모양 | 30 | 65 | 실제 submit + validation + result 표시 |
| PROMOTE checklist | freeze/portfolio/oos evidence | 정적 checklist | 55 | 75 | 실제 evidence readiness 반영 |
| OOS CI | OOS confidence table | mock | 45 | 72 | freeze/oos payload 연결 |
| regime/revival | `/regime_report`, `/revival_registry` | mock | 45 | 72 | 실제 report 연결 |
| portfolio verdict | `/portfolio_verdict` | mock | 45 | 72 | V6/M4 baseline 연결 |
| separation from export | final export와 decision audit 분리 | 문구 구현 | 90 | 90 | 유지 |

### 결정 감사 100점 목표

- `PROMOTE/COMPLEMENT/HOLD/REJECT` 제출은 실제 `/record_decision`을 호출하되, V3K/live order와 혼동하지 않게 연구 결정으로 제한한다.
- 제출 후 ledger가 즉시 refresh되고 hash/verified 상태를 보여야 한다.
- 최종 export approval과 decision audit는 계속 분리한다.

## 백테스트 상세 채점

| 기능 | 기존 API/컴포넌트 | 리모델 현재 | 패리티 | 자체 완성도 | 100점 개선 조건 |
|---|---|---|---:|---:|---|
| health/data range | `/bt/health`, `/bt/data_range` | health OK 배지 mock | 25 | 60 | 실제 health와 DB range 표시 |
| strategy list | `/bt/strategies?kind=buy/sell` | select mock | 25 | 60 | buy/sell 목록 실제 로드 |
| strategy read | `/bt/strategy` | static code | 25 | 60 | 선택 전략 전문 로드 |
| validate/save/delete | `/bt/strategy/validate`, `/bt/strategy`, `/bt/strategy/delete` | 버튼만 있음 | 20 | 55 | 검증 결과/저장/삭제 confirm 구현 |
| variable chips | `/bt/variables`, `/bt/extract_vars` | 없음 또는 텍스트 | 15 | 50 | SSOT 변수칩과 추출 결과 표시 |
| legacy self.vars | `/bt/legacy/self_vars` | self.vars 빌더 mock | 25 | 55 | legacy self.vars preview + sweep 변환 |
| BackFinder preflight | `/bt/backfinder/preflight` | 없음 | 10 | 45 | 실행 전 preflight 패널 이식 |
| run modes | `/bt/run` mode backtest/optimize/wfo/sweep | 실행 카드 mock | 30 | 62 | 실제 payload 구성 및 job_id 반환 |
| job list/status | `/bt/jobs`, `/bt/job` | 고정 job | 25 | 60 | 최신 job list와 선택 job detail |
| job WS | `/bt/ws_job` | 없음 | 15 | 50 | live progress/log tail/cancel |
| job cancel/meta | `/bt/job/cancel`, `/bt/job/meta` | 취소 버튼 mock | 20 | 55 | cancel, tags, memo, favorite 동작 |
| result summary | `/bt/result`, `/bt/analysis/summary` | mock metrics | 40 | 70 | 실제 result CSV 기반 metrics |
| charts | `/bt/analysis/equity`, distribution, heatmap, underwater | SVG mock | 35 | 70 | 실제 차트 데이터 렌더 |
| insights | `/bt/analysis/insights`, exit_reasons, montecarlo | 없음/일부 mock | 25 | 60 | 분석 탭 패널 이식 |
| MAE/MFE | `/bt/analysis/mae_mfe` | 없음 | 15 | 55 | scatter chart와 filter |
| orderflow | `/bt/analysis/orderflow` | 없음 | 15 | 55 | 진입 체결강도/호가불균형 분석 |
| GUI parity | `/bt/analysis/gui_parity` | 품질 mock | 20 | 60 | STOM GUI PlotShow parity |
| compare/overlay | `/bt/compare`, `/bt/overlay` | 타일 mock | 30 | 65 | A/B, multi-job overlay 실제 렌더 |
| portfolio | `/bt/portfolio` | 타일 mock | 25 | 60 | 전략 조합 분석 |
| report | `/bt/report` | 버튼 mock | 30 | 65 | standalone HTML report 열기/저장 |
| evo handoff | `/bt/evo_gens`, localStorage handoff | 없음/약함 | 25 | 60 | 조건식 AI → 백테스트 선택 연동 |

### 백테스트 100점 목표 페이지 구성

| 영역 | 100점 UI 구조 |
|---|---|
| 상단 | API status, data range, mode selector, selected buy/sell, date range, timeframe, engine count, run button |
| 좌측 | buy/sell strategy library, variable chips, BackFinder preflight, self.vars/sweep builder |
| 중앙 | dual editor, validation result, compile error, save/delete confirmation |
| 우측 | active job card, WS progress, log tail, cancel, result preview |
| 하단 | result library, summary metrics, equity/underwater/distribution/heatmap, MAE/MFE, orderflow, GUI parity, insights |
| 확장 | A/B compare, multi-job overlay, portfolio combine, evo generation selector, HTML report |

## 차트 리플레이 상세 채점

| 기능 | 기존 API/컴포넌트 | 리모델 현재 | 패리티 | 자체 완성도 | 100점 개선 조건 |
|---|---|---|---:|---:|---|
| health | `/sim/health` | mock status | 30 | 65 | 실제 module/api version 표시 |
| source selector | tick/min src | 구현 모양 | 50 | 75 | src 변경 시 days reload |
| days inventory | `/sim/days` | 정적 달력 | 25 | 65 | 실제 DB 날짜 목록 |
| demo preset | `/sim/demo` | 정적 preset | 35 | 70 | latest/top mover 자동 선택/재생 |
| stocks | `/sim/stocks` | 정적 stock list | 30 | 70 | 선택일 종목·등락·거래대금 로드 |
| strategy selectors | `/bt/strategies` | 정적 | 35 | 68 | buy/sell strategy 목록 공유 |
| signals | `/sim/signals` | static signal log | 30 | 65 | 종목별 신호 로드와 차트 overlay |
| replay WS | `/sim/ws` | 없음, 버튼 mock | 20 | 55 | start/meta/bars/history/done/error 처리 |
| playback controls | play/pause/resume/stop/speed/seek | 버튼만 | 35 | 70 | WS command와 상태 동기화 |
| keyboard shortcuts | Space/Arrow/Esc | 없음 | 10 | 45 | 기존 shortcuts 이식 |
| chart engines | live/LWC/SVG | static SVG candle | 45 | 72 | `SimChartByEngine` 이식 |
| split/overlay | split columns/rows, overlay normalized | badge/mock | 40 | 70 | localStorage 보존 포함 |
| indicators | MA/VWAP/Bollinger/RSI/orderflow | badge/mock | 40 | 70 | indicator toggle 실제 반영 |
| minimap | market minimap | mock heatmap | 45 | 72 | stocks/date 기반 minimap |
| learning mode | auto-pause at signal | card mock | 30 | 65 | signal time seek + auto pause |
| signal log | trade/signal table | static | 35 | 65 | current time highlight, click seek |
| indicator table | live values | static | 40 | 70 | bars 기반 live compute |
| variable watch | watched vars | static | 35 | 65 | selected vars/bars 기반 refresh |
| error handling | wsErr/signalErr panels | mock warning | 45 | 70 | protocol error/fetch error 노출 |
| performance | render budget, max code, dense layout | 일부 시각 | 50 | 72 | 기존 render budget 재사용 |

### 차트 리플레이 100점 목표 페이지 구성

| 영역 | 100점 UI 구조 |
|---|---|
| 좌측 상단 | src(tick/min), days inventory, stock search, selected stock chips, strategy buy/sell selector |
| 좌측 중단 | market minimap, indicator table, variable watch, learning auto-pause, signal log |
| 중앙 상단 | playback bar, speed, seek slider, current time, session range, WS status/error |
| 중앙 본문 | split/overlay chart grid, live/LWC/SVG engine, indicator overlays, signal markers |
| 우측/하단 | session metadata, replay notes, dropped/error frames, protocol diagnostics |
| E2E | date→stock→strategy→play→pause→seek→speed→signal click→stop |

## 설정/모달/보조 기능 상세 채점

| 기능 | 기존 기능 | 현재 | 패리티 | 자체 완성도 | 개선 방향 |
|---|---|---|---:|---:|---|
| config spec | `/config/spec` | 정적 설정 | 50 | 75 | spec 기반 dynamic form |
| GPT auth status | `/gpt_auth/status` | 정적 문구 | 40 | 70 | read-only status 표시 |
| GPT auth test | `/gpt_auth/test` | 버튼 없음/정적 | 35 | 65 | mutation 없는 test action |
| theme | dark/light CSS variable | 구현 | 90 | 90 | system preference 저장 |
| modals | inspector/approval/settings | 구현 | 70 | 80 | 실제 데이터 연결과 validation |
| favicon/noise | data URI favicon | 구현 | 100 | 100 | 유지 |

## 100점 리모델 개발 원칙

| 원칙 | 내용 |
|---|---|
| 기능 로직 재사용 | 기존 production React 컴포넌트와 API client/state machine을 버리지 않는다. 리모델은 shell/layout/design layer로 입힌다. |
| 정적 mock 제거 | 실제 API 연결 전까지는 `Preview only`, `데이터 없음`, `endpoint 실패`를 명시한다. |
| safety 유지 | 실거래 주문, 브로커 로그인, 계좌/자산 연동은 계속 금지한다. |
| write action 보호 | save/delete/run/record_decision은 기존 confirm, validation, append-only contract를 재사용한다. |
| DB 검증 | wt-dev `_database`를 read-only로 참조하거나 fixture DB를 복사해 실제 데이터 경로를 검증한다. |
| E2E 기준 | 화면이 예쁘게 보이는 것뿐 아니라 버튼 클릭 후 API 호출·상태 변화·오류 표시까지 확인한다. |

## 개발 단계 제안

### Phase 1 — Hybrid Shell 이식

| 작업 | 산출물 | 완료 기준 |
|---|---|---|
| remodel shell 안에 기존 React bundle mount 영역 확보 | `/ui/remodel/`에서 기존 탭 컴포넌트 mount 가능 | 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` 유지 + remodel 안에서도 동작 |
| CSS token bridge | 기존 `styles.css` token과 remodel `theme.css` mapping | 기존 기능 깨지지 않고 remodel 디자인 적용 |
| mock/real 표시 체계 | `data-live="true/false"`, Preview badge | 사용자가 mock과 실제를 구분 가능 |

### Phase 2 — 백테스트 완전 패리티

| 작업 | 연결 대상 | 완료 기준 |
|---|---|---|
| `BacktestTab` 이식 | `bt-tab-root.jsx` | 전략 CRUD/실행/결과 탭이 remodel에서 동작 |
| run/job WS 이식 | `/bt/run`, `/bt/jobs`, `/bt/job`, `/bt/ws_job` | job progress/log/cancel 실동작 |
| 분석 패널 이식 | `/bt/analysis/*`, `/bt/compare`, `/bt/overlay`, `/bt/portfolio`, `/bt/report` | 결과 분석 전체 확인 |
| 테스트 | API mock + fixture/live DB | backtest E2E pass, screenshot capture |

### Phase 3 — 차트 리플레이 완전 패리티

| 작업 | 연결 대상 | 완료 기준 |
|---|---|---|
| `SimulationTab` 이식 | `sim-tab-root.jsx` | 날짜/종목/전략 선택 동작 |
| replay WS 이식 | `/sim/ws` | play/pause/resume/seek/speed/stop 동작 |
| chart engine 이식 | `SimChartByEngine`, live/LWC/SVG | split/overlay/indicator/signal marker 정상 |
| 테스트 | fixture DB + browser E2E | replay E2E pass, 영상/스크린샷 캡처 |

### Phase 4 — 조건식 AI 세부 API 연결

| 작업 | 연결 대상 | 완료 기준 |
|---|---|---|
| inspector 실제화 | `/strategy_code`, `/strategy_diff`, `/prompts`, `/ai_context_pack` | row click → 실제 code/diff/context |
| 분석 패널 실제화 | `/backtest_detail`, `/equity_curve`, `/edge_ratio`, `/feature_importance`, `/variable_correlation` | mock chart 제거 |
| research/lab/workbench 실제화 | 기존 Lab/Pro/Index 패널 | 기존 분석 depth 유지 |

### Phase 5 — 감사/결정/승인 정리

| 작업 | 연결 대상 | 완료 기준 |
|---|---|---|
| decision ledger | `/decisions` | ledger 실제 표시 |
| append-only submit | `/record_decision` | submit 후 refresh, hash/verified 표시 |
| export approval 분리 | 기존 human gate contract | export와 audit 혼동 없음 |

### Phase 6 — 최종 검증

| 검증 | 완료 기준 |
|---|---|
| 단위 테스트 | `pytest tests/unit/test_dashboard* -q` 통과 |
| 백테스트 E2E | 전략 선택→검증→실행→결과→보고서 |
| 리플레이 E2E | 날짜→종목→재생→pause/seek/speed→signal log |
| 조건식 AI E2E | run 선택→gen 선택→inspector→backtest handoff |
| 시각 캡처 | overview/process/history/lab/workbench/audit/backtest/replay/settings 전체 |
| 안전 검사 | no live order/broker/account, no hidden export |

## PR 완료 기준

리모델 PR을 `wt-dev`로 반영하려면 다음이 모두 충족되어야 한다.

1. 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay`는 그대로 동작한다.
2. `/ui/remodel/`은 기존 기능을 모두 포함하되 remodel 디자인을 적용한다.
3. 백테스트와 차트 리플레이는 static mock이 아니라 production API/state machine으로 동작한다.
4. 조건식 AI는 최소 현재 loop/status/run/history/code/backtest detail/analysis/audit read-only 경로를 실제 연결한다.
5. 모든 write/run action은 기존 confirm/validation/safety contract를 따른다.
6. 기능 E2E, dashboard unit tests, screenshot QA가 통과한다.

## 최종 판정

현재 리모델은 **디자인 초안으로는 쓸 수 있지만, 완전한 대체 대시보드로는 아직 55점**이다. 100점에 도달하려면 새로 정적 화면을 더 그리는 것이 아니라, 기존 production 컴포넌트의 기능 로직을 리모델 shell 안으로 이식하고, mock 영역을 실제 API 연결 또는 명시적 preview 상태로 바꿔야 한다.
