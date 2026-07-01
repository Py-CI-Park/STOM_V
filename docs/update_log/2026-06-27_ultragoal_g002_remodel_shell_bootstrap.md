# Ultragoal G002 — 리모델 namespace shell과 production bootstrap

## 목표

`/ui/remodel/`을 기존 static prototype production path에서 production React component graph를 부트스트랩하는 리모델 namespace shell로 전환한다. G002는 백테스트/리플레이/조건식 AI 기능 완전 이식의 기반이며, 기존 canonical route는 그대로 보존한다.

## 변경 파일

| 파일 | 변경 |
|---|---|
| `ai_strategy_loop/dashboard/app.py` | `/ui/remodel/{page}` deep-link route 추가, remodel index response 추가, `remodel-bootstrap.js` asset 응답 보장 |
| `ai_strategy_loop/dashboard/frontend/remodel/index.html` | static `src/app.js` renderer 대신 production `/ui/bundle/app.js`와 `/ui/bundle/stom-ui.js` 로드 |
| `ai_strategy_loop/dashboard/frontend/remodel/remodel-bootstrap.js` | `/ui/remodel/*` route seed, history push/replace remap, remodel mode flags |
| `tests/unit/test_dashboard_remodel_baseline_contract.py` | remodel deep-link, bootstrap, manifest version guard 추가 |
| `tests/unit/test_dashboard_remodel_static.py` | remodel root가 production bootstrap을 사용하도록 기대값 갱신 |

## Gate A — namespace/deep-link 결과

| route | 결과 |
|---|---|
| `/ui/remodel/condition` | 200, production condition AI surface 표시, route 유지 |
| `/ui/remodel/process` | 200, production process subpage 표시, route 유지 |
| `/ui/remodel/history` | 200, remodel index bootstrap |
| `/ui/remodel/lab` | 200, remodel index bootstrap |
| `/ui/remodel/workbench` | 200, remodel index bootstrap |
| `/ui/remodel/audit` | 200, remodel index bootstrap |
| `/ui/remodel/backtest` | 200, production BacktestTab 표시, route 유지 |
| `/ui/remodel/chart-replay` | 200, production SimulationTab 표시, route 유지 |
| `/ui/remodel/settings` | 200, remodel index bootstrap |

## Gate B — production bootstrap / bundle drift guard

- `frontend/remodel/index.html`은 `/ui/bundle/stom-ui.js?v=<manifest>`와 `/ui/bundle/app.js?v=<manifest>`를 로드한다.
- `tests/unit/test_dashboard_remodel_baseline_contract.py::test_remodel_bootstrap_uses_bundle_manifest_versions`가 `frontend/bundle/manifest.json`과 index의 query version 일치를 검증한다.
- 기존 vanilla `src/app.js`와 `src/data.js`는 아직 파일로 보존되지만 `/ui/remodel/` production root에서는 로드하지 않는다.

## Gate C — 안전

- G002는 live order, broker login, account trading, hidden export, hidden `final_approval` 경로를 추가하지 않았다.
- 기존 source safety guard가 remodel index/bootstrap/static source를 검사한다.

## Gate D — CSS scope

- remodel root는 `data-remodel="true"`와 `body.remodel-production-shell`을 설정한다.
- `styles/theme.css`는 `/ui/remodel/`에서만 추가 로드된다.
- 기존 `/ui/evolution`, `/ui/backtest`, `/ui/chart-replay` route는 그대로 `/ui/styles.css`와 production bundle을 사용한다.

## Gate E — E2E/route/API evidence

서버 `127.0.0.1:8774`에서 browser automation으로 다음을 확인했다.

| 화면 | 캡처 |
|---|---|
| remodel condition | `artifacts/ultragoal-g002-shell/condition.png` |
| remodel backtest | `artifacts/ultragoal-g002-shell/backtest.png` |
| remodel chart replay | `artifacts/ultragoal-g002-shell/chart-replay.png` |
| remodel process | `artifacts/ultragoal-g002-shell/process.png` |

서버 로그에서 production API 호출 확인:

- `/bt/health`, `/bt/strategies`, `/bt/jobs`, `/bt/data_range`
- `/sim/health`, `/sim/days`, `/sim/demo`
- `/health`, `/status`, `/runs`, `/config/spec`, `/ws`

## 검증 결과

- `python -m py_compile ai_strategy_loop/dashboard/app.py` — 통과
- `node --check ai_strategy_loop/dashboard/frontend/remodel/remodel-bootstrap.js` — 통과
- `pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q` — 10 passed
- `pytest tests/unit/test_dashboard* -q` — 330 passed
- `git diff --check` — 통과

## 남은 후속 목표

G002는 shell/bootstrap과 deep-link 기반을 완성했다. G003은 이 기반 위에서 backtest parity를 실제 workflow 단위로 닫아야 한다. 특히 전략 CRUD, run/job WS, result/analysis/report/handoff는 아직 G003의 완료 조건이다.
