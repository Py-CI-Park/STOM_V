# Ultragoal G001 — 대시보드 리모델 기준선·인벤토리

## 목표

G001은 승인된 pending plan을 실행하기 전 기준선을 고정한다. 이번 단계는 구현 본편이 아니라, 100% 대체 개발 중 누락·회귀를 잡기 위한 route, mock, API, 화면 증거 기준선이다.

## 기준 문서

- 승인 대기 계획: `.gjc/_session-019f05e9-d676-7000-9c61-3c206a2d4031/plans/ralplan/019f05e9-d676-7000-9c61-3c206a2d4031/pending-approval.md`
- 상세 점수표: `docs/update_log/2026-06-27_dashboard_remodel_detailed_100_point_scorecard.md`
- 패리티 평가: `docs/update_log/2026-06-27_dashboard_remodel_parity_assessment.md`
- 인수/구현 계획: `docs/update_log/2026-06-26_dashboard_remodel_worktree_intake.md`

## 현재 route 기준선

| route | 상태 | 기준 의미 |
|---|---|---|
| `/ui/evolution` | 200 OK | 기존 조건식 AI route 보존 기준 |
| `/ui/backtest` | 200 OK | 기존 백테스트 route 보존 기준 |
| `/ui/chart-replay` | 200 OK | 기존 차트 리플레이 route 보존 기준 |
| `/ui/remodel/` | 200 OK | 현재 리모델 preview root |
| `/ui/remodel/backtest` | 404 baseline gap | Gate A에서 구현해야 할 remodel deep-link |
| `/ui/remodel/chart-replay` | 404 baseline gap | Gate A에서 구현해야 할 remodel deep-link |

## 현재 리모델 mock/static 인벤토리

현재 `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`는 production replacement가 아니라 static prototype + 일부 live bridge다.

| 영역 | 현재 source | 실제 연결 | gap |
|---|---|---|---|
| 공통 shell | `DATA.shell` + `/health` | 일부 연결 | backtest/replay health 미표시 |
| 조건식 overview | `DATA.overview`, `mapLoopState()` | `/status`, `/runs`, `/ws` 일부 | inspector/code/diff/prompts/context mock |
| 프로세스 | `DATA.process` | 없음 | `/pipeline_status`, `/ops_status` 연결 필요 |
| 히스토리 | `DATA.history` + `mapRuns()` | `/runs` 일부 | `/run_state`, compare, lineage 부족 |
| 연구실 | `DATA.lab` | 없음 | edge/importance/correlation/TMAP mock |
| 워크벤치 | `DATA.workbench` | 없음 | 후보 분석/handoff mock |
| 결정 감사 | `DATA.audit` | 없음 | `/decisions`, `/record_decision` 미연결 |
| 백테스트 | `renderBacktest()` + `DATA.backtest` | 없음 | production `BacktestTab`과 `/bt/*` 전체 이식 필요 |
| 차트 리플레이 | `renderReplay()` + `DATA.replay` | 없음 | production `SimulationTab`과 `/sim/*` 전체 이식 필요 |
| 설정/모달 | static modal | 없음 | `/config/spec`, GPT auth 상태/테스트 연결 필요 |

## production contract 기준선

### 백테스트 production sources

- `ai_strategy_loop/dashboard/frontend/bt-tab-root.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-run.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-library.jsx`
- `ai_strategy_loop/dashboard/frontend/bt-tab-analysis.jsx`
- `ai_strategy_loop/dashboard/backtest_api.py`

필수 API markers:

- `@backtest_router.get("/health")`
- `@backtest_router.post("/run")`
- `@backtest_router.get("/result")`
- `@backtest_router.websocket("/ws_job")`

### 차트 리플레이 production sources

- `ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-tab-controls.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-chart-engines.jsx`
- `ai_strategy_loop/dashboard/frontend/sim-live-chart.jsx`
- `ai_strategy_loop/dashboard/simulation_api.py`

필수 API markers:

- `@simulation_router.get("/health")`
- `@simulation_router.get("/days")`
- `@simulation_router.get("/signals")`
- `@simulation_router.websocket("/ws")`

## 추가 baseline guard test

추가 파일:

- `tests/unit/test_dashboard_remodel_baseline_contract.py`

검증 내용:

1. 기존 canonical route가 `/ui/remodel`과 분리되어 200 OK로 유지된다.
2. `/ui/remodel/` 현재 static preview root가 명시적으로 source/data/app script와 fallback bridge를 포함한다.
3. production backtest/replay source와 핵심 API route marker가 존재한다.
4. remodel source에는 live-order/broker/account/hidden export/final_approval action marker가 없다.
5. remodel source에는 research-only safety cue가 존재한다.

## 시각 기준선 캡처

서버: `python -m uvicorn ai_strategy_loop.dashboard.app:app --host 127.0.0.1 --port 8774`

| 화면 | 캡처 |
|---|---|
| 기존 조건식 AI | `artifacts/ultragoal-g001-baseline/evolution.png` |
| 기존 백테스트 | `artifacts/ultragoal-g001-baseline/backtest.png` |
| 기존 차트 리플레이 | `artifacts/ultragoal-g001-baseline/chart-replay.png` |
| 현재 리모델 | `artifacts/ultragoal-g001-baseline/remodel.png` |

## 검증 결과

- `pytest tests/unit/test_dashboard_remodel_baseline_contract.py -q` — 4 passed
- `pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q` — 9 passed
- `pytest tests/unit/test_dashboard* -q` — 329 passed
- `git diff --check` — 통과

## 다음 goal로 넘기는 확인 사항

G002는 이 기준선을 기반으로 `/ui/remodel/` namespace shell과 shared bootstrap을 구현해야 한다. 특히 현재 404인 `/ui/remodel/backtest`와 `/ui/remodel/chart-replay`는 Gate A의 명시적 gap이다.
