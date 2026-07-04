# Process Research Benchmark-First Execution

Status: execution evidence note for approved Ralplan `019f030b-4f0c-7000-90be-527a9ee32aec`.

## 핵심 결론

| 항목 | 결론 |
|---|---|
| 32/64 결정 | **32 유지** |
| 근거 artifact | `artifacts/process-research-engine-benchmark.json` |
| 최종 benchmark input | `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2`, tick, `20250101~20251231`, `09:00:00~09:28:00`, repeat 3 |
| 64 결과 | run p50/p95는 개선됐지만 기준선 20%에 미달했고 prepare 비용 때문에 amortized p50은 악화 |
| 안전 정책 | 연구를 막지 않는다. 운영 승격/export/live/final promotion만 차단한다. |

## 32 vs 64 benchmark 결과

| Engine | prepare sec | run p50 sec | run p95 sec | amortized p50 sec | success | timeout/recovery |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | 113.030 | 36.305 | 36.418 | 73.982 | 3/3 | 0/0 |
| 64 | 143.066 | 29.256 | 29.587 | 76.945 | 3/3 | 0/0 |

| 비교 | 값 | 판정 |
|---|---:|---|
| amortized_total_p50_improvement | -4.01% | 악화 |
| run_p50_improvement | 19.42% | 20% 기준 미달 |
| run_p95_improvement | 18.76% | 20% 기준 미달 |
| success_rate_delta | 0.00 | 동일 |
| timeout_delta / recovery_delta | 0 / 0 | 동일 |

따라서 현재 승인 기준에서는 64를 기본값으로 바꾸지 않는다. 64는 순수 run 단계에서는 빨랐지만, prepare 비용까지 포함한 연구 루프 전체 기준에서는 이득이 부족하다.

## 프로세스 번호 안내

| 번호 | 코드명 | 사용 목적 | 연구에서 허용 | 계속 차단 |
|---:|---|---|---|---|
| 1 | `fast-discovery` | 빠르게 후보 생성 후 즉시 연구 | candidate generation, smoke/full-period backtest, Edge Ratio analysis, condition improvement loop | production promote, export, live |
| 2 | `process-research` | 전체기간 분석과 evidence 보존 중심 연구 | full-period validation, candidate generation, evidence preservation, segment/Edge Ratio analysis, improvement loop | clean OOS promotion claim, production promote, export, live |
| 3 | `promotion-review` | 동결 후보 운영 승격 전 검토 | frozen candidate review, evidence health review, hard gate review | final promotion/export/live without separate human approval |

## Fast full-period research 루틴

| 단계 | 설명 |
|---:|---|
| 1 | `fast-discovery` 또는 `process-research` 선택 |
| 2 | 이번 benchmark 기준으로 engine 32 사용 |
| 3 | 전체기간 백테스트/분석을 먼저 수행 |
| 4 | Edge Ratio, 시간대×시총, segment weakness, 변수 중요도 분석 |
| 5 | 조건식을 생성 또는 개선 |
| 6 | 다시 전체기간 분석으로 반복 |
| 7 | 운영 승격 후보로 다루려면 별도 `promotion-review`에서 동결 검토 |

## 페이지별 현재 작업 방향

| 페이지 | URL | 작업 내용 |
|---|---|---|
| 조건식 AI 개요 | `/ui/evolution` | 루프 상태/시작 표면 유지, 생산 승인처럼 보이지 않게 유지 |
| 프로세스 | `/ui/evolution/process` | 1/2/3 번호, 연구 허용, 운영 차단을 명확히 표시하고 카드 클릭/키보드 선택으로 각 프로세스 안내를 전환 |
| 연구실 | `/ui/evolution/lab` | Edge Ratio 히트맵 cross label 파싱을 보강하고 no-cross 상태를 숨기지 않음 |
| 분석 워크벤치 | `/ui/evolution/workbench` | Research Pro heatmap 셀 크기를 제한하고 scroll container로 큰 heatmap을 제어 |
| 백테스트 | `/ui/backtest` | 전체기간 결과 분석 표면 유지 |
| 히스토리 | `/ui/evolution/records` | run/gen/detail/compare evidence 접근 유지 |
| 결정 감사 | `/ui/evolution/verdict` | 연구 결과와 운영 승격 판단을 분리 |
| 차트 리플레이 | `/ui/chart-replay` | 공유 레이아웃 회귀 smoke만 확인 |

## 추천 명령어

### Benchmark first

```sh
python -m ai_strategy_loop.scripts.benchmark_warm_engines --timeframe tick --engines 32 64 --repeat 3 --out artifacts/process-research-engine-benchmark.json
```

### Dashboard

```bat
cmd.exe /c start "" stom_dashboard.bat
```

```sh
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8770/health', timeout=5).read().decode())"
```

### Focused tests

```sh
python -m pytest tests/unit/test_benchmark_warm_engines.py tests/unit/test_condition_discovery_policy.py tests/unit/dashboard/test_p11_process_flow.py tests/unit/dashboard/test_dashboard_ui_remodel.py -q
```

### Frontend bundle

Run from `ai_strategy_loop/dashboard/webui-build`:

```sh
npm run build:app
npm run harness
```

### Final checks

```sh
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## Evidence

| Evidence | Result |
|---|---|
| Benchmark harness unit tests | `python -m pytest tests/unit/test_benchmark_warm_engines.py -q` → `7 passed` |
| Focused backend/frontend unit suite | `python -m pytest tests/unit/test_benchmark_warm_engines.py tests/unit/test_launch_config.py tests/unit/test_condition_discovery_policy.py tests/unit/test_dashboard_validation_views.py tests/unit/test_warm_session_window.py tests/unit/dashboard/test_dashboard_ui_remodel.py tests/unit/dashboard/test_p11_process_flow.py -q` → `110 passed` |
| Frontend bundle | `npm run build:app` → `app.js v=ea4b6150`, `stom-ui.js v=f41f5701` |
| Frontend harness | `npm run harness` → `allPass: true` |
| Dashboard health | `GET /health` → `{"status":"ok","contract_version":2}` |
| Browser page pass | `artifacts/process-research-v4-browser-verification.json` → overview/process/lab/workbench/backtest/records/verdict/chartReplay pass |
| Screenshots | `artifacts/process-research-v4-process-page.png`, `artifacts/process-research-v4-lab-page.png`, `artifacts/process-research-v4-workbench-page.png` |
| Nonrelease safety | `python scripts/verify_nonrelease_sync.py` → OK |
| Diff whitespace | `git diff --check` → OK |
| Protected runtime paths | `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json` → no output |

Final quality review, commit, and push are tracked by the active Ultragoal ledger.
