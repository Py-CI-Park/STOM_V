# 진화 대시보드 연구 기록 복구 및 OOS 후속 실행 계획

작성일: 2026-06-18  
상태: 실행 전 계획 완료  
모드: `$ulw-plan` 산출물. 이 턴에서는 구현/백테스트를 실행하지 않는다.

## 목표

1. 연구 기록과 백테스트 기록을 `.omo/evidence/tmap-walkforward` 증거 파일 기준으로 체계적으로 색인한다.
2. 진화 대시보드에서 과거 연구 캠페인, 후보, 요약, 로그, 산출물을 확인할 수 있게 한다.
3. 백테스트 탭에 이미 있는 GUI parity 차트 중 시간별/요일별 수익률 그래프를 현재 진화 테스트 조건식에도 표시한다.
4. 추천 후속 작업 3개를 같은 실행 흐름에 포함한다.
   - `exit2` 균형 후보 OOS 2022/2026
   - `r2full` MDD 후보 OOS 2022/2026
   - `r8_4`, `exit2 balance`, `r2full MDD` 포트폴리오 비교
5. 마지막에 완료 결과를 표로 보고한다.

## TODOs

- [x] 연구 기록 색인 API와 테스트를 추가한다.
- [x] 진화 generation GUI parity API와 테스트를 추가한다.
- [x] 진화 대시보드 연구 기록 패널과 시간별/요일별 차트 패널을 추가하고 번들을 재빌드한다.
- [x] OOS pair JSON을 생성하고 `exit2`/`r2full` 2022/2026 OOS를 실행한다.
- [x] `r8_4`, `exit2 balance`, `r2full MDD` 포트폴리오 비교 산출물을 생성한다.
- [x] 2026-06-18 완료 보고 문서를 작성한다.

## Final Verification Wave

- [x] 계획 검증 명령, 수동 QA, 보호 경로 점검, ledger 정리를 완료한다.

## 읽은 근거

| 구분 | 확인 위치 | 계획에 반영한 내용 |
|---|---|---|
| 대시보드 상세 백테스트 | `ai_strategy_loop/dashboard/app.py` | `/backtest_detail`, `/time_profit`, `/run_log`, `_csv_by_buy_name()`가 이미 있음 |
| GUI parity 분석 | `ai_strategy_loop/dashboard/backtest_analysis.py` | `full_analysis().gui_parity`에 `hourly`, `weekday`가 이미 포함됨 |
| GUI parity UI | `ai_strategy_loop/dashboard/frontend/bt-gui-parity.jsx` | `BtGuiParitySection`, `BtHourlyPnlChart`, `BtWeekdayPnlChart` 재사용 가능 |
| 진화 탭 UI | `ai_strategy_loop/dashboard/frontend/app.jsx` | `BacktestDetailChart`, `ResearchLabPanel`, generation 선택 흐름이 이미 있음 |
| OOS 실행기 | `ai_strategy_loop/scripts/claude_candidate_batch_eval.py` | `--pairs-json`, `--config-json`, `--run-id` 방식으로 실행 |
| 후보 pair 파일 | `.omo/evidence/tmap-walkforward/*.json` | 실행할 buy/sell 이름 확인 완료 |

Metis/subagent 도구는 현재 환경에서 사용할 수 없어 별도 호출하지 못했다. 대신 기존 코드, 테스트, 증거 파일을 직접 읽고 아래의 self gap analysis를 반영했다.

## 실행 범위

포함:
- 진화 대시보드 연구 기록 색인 API 추가
- 진화 탭 연구 기록 패널 추가
- 현재 선택된 generation의 GUI parity 차트 API/패널 추가
- `exit2`/`r2full` OOS 2022/2026 실행
- `r8_4 + exit2 + r2full` 포트폴리오 비교 결과 생성
- 문서화 및 완료 표 작성

제외:
- 실거래 연결, KHOPENAPI 로그인, 주문/청산 배선
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/` 수정
- V3K gate 4~6 완료 처리
- 새 프론트엔드 의존성 추가
- 조건식 실전 승격

## 후보 고정

| 작업 | 후보 | Buy | Sell | 원본 파일 |
|---|---|---|---|---|
| `exit2` 균형 OOS | `r4_7_be_floor=0.5` | `GATE_r4_7_be_floor_0_5_B` | `GATE_r4_7_be_floor_0_5_S` | `.omo/evidence/tmap-walkforward/ovn_exit2_r4_pairs.json` |
| `r2full` MDD OOS | `r4_9_burst_b=1.5` | `GATE_r4_9_burst_b_1_5_B` | `GATE_r4_9_burst_b_1_5_S` | `.omo/evidence/tmap-walkforward/ovn_r2full_r4_pairs.json` |
| 포트폴리오 비교 기준 | `r8_4` | 기존 `pairs-ovn-r8-oos.json` 기준 | 기존 `pairs-ovn-r8-oos.json` 기준 | `.omo/evidence/tmap-walkforward/pairs-ovn-r8-oos.json` |

## 작업 순서

### 1. 테스트 기준 먼저 고정

예상 소요: 20~30분

- Python/JS 변경 전 `programming` 스킬의 Python/TypeScript 지침을 다시 읽는다.
- 새 기능의 기대 응답 구조를 테스트로 먼저 고정한다.
- 추가 테스트 후보:
  - `tests/unit/dashboard/test_research_records.py`
  - `tests/unit/dashboard/test_evolution_gui_parity.py`
  - 기존 `tests/unit/dashboard/test_backtest_analysis.py`에 regression 보강
  - 프론트엔드 정적 검증 테스트에 `ResearchRecordsPanel`, `BtGuiParitySection` 노출 확인

완료 기준:
- 연구 기록 API의 정렬, 파일 제한, 누락 파일 처리 테스트가 실패 상태로 준비된다.
- 진화 generation CSV가 없을 때 빈 차트를 무예외로 반환하는 테스트가 준비된다.

### 2. 연구 기록 색인 모듈 추가

예상 소요: 40~60분

- 새 모듈 후보: `ai_strategy_loop/dashboard/research_records.py`
- `.omo/evidence/tmap-walkforward` 아래만 읽는다.
- 읽을 파일:
  - `*_summary.json`
  - `*.jsonl`
  - `pairs-*.json`
  - `*_run.log`
  - OOS config/result 파일
  - 관련 `docs/update_log/2026-06-17_*`, `2026-06-18_*`
- 반환 모델 예:
  - campaign name
  - candidate label
  - profit, MDD, trades, daily trades, gate
  - train/OOS 구분
  - source files
  - last modified time
  - available logs/reports

완료 기준:
- 누락되거나 깨진 JSON이 있어도 API 전체가 죽지 않는다.
- 임의 경로 읽기가 불가능하다.
- 최신 연구 캠페인이 먼저 보인다.

### 3. 대시보드 연구 기록 API 연결

예상 소요: 25~40분

- `app.py`에는 최소 라우트만 추가한다.
- 가능한 라우트:
  - `GET /research_records`
  - `GET /research_records/detail?campaign=<name>`
- `app.py`가 이미 크므로, 로직은 새 모듈에 둔다.
- 기존 `/run_log`는 그대로 유지하고, 연구 기록 API에서 로그 이름을 알려준다.

완료 기준:
- `Invoke-WebRequest http://127.0.0.1:<port>/research_records`가 JSON을 반환한다.
- `exit2`, `r2full`, `r8` 캠페인이 최소 1개 이상 표시된다.

### 4. 진화 탭 연구 기록 패널 추가

예상 소요: 45~70분

- 새 프론트엔드 컴포넌트 후보:
  - `ai_strategy_loop/dashboard/frontend/research-records-panel.jsx`
- `app.jsx`의 Evolution 탭 또는 `Research Lab` 근처에 추가한다.
- 보여줄 정보:
  - 최근 연구 캠페인
  - 최고 성과 후보
  - OOS 완료 여부
  - 관련 증거 파일/로그 상태
  - 클릭 시 상세 후보 표
- 새 의존성을 추가하지 않는다.

완료 기준:
- 대시보드에서 연구 기록을 표로 확인할 수 있다.
- 기록이 없거나 API가 실패해도 빈 상태가 깨지지 않는다.

### 5. 진화 대상 GUI parity API 추가

예상 소요: 35~50분

- 새 helper 후보: `ai_strategy_loop/dashboard/evolution_gui_parity.py`
- 기존 흐름을 재사용한다.
  - generation에서 `csv_path`, `buy_name` 조회
  - 없으면 `_csv_by_buy_name(buy_name)` fallback
  - CSV가 있으면 `full_analysis(csv_path)["gui_parity"]` 반환
- 가능한 라우트:
  - `GET /evolution_gui_parity?run_id=<run>&gen_no=<n>`
- 응답 예:
  - `run_id`, `gen_no`, `csv_path_found`, `gate_passed`, `summary`, `gui_parity`

완료 기준:
- 현재 선택된 generation에 대해 `hourly`, `weekday` 데이터가 반환된다.
- CSV가 없으면 HTTP 200 + 빈 구조로 반환된다.

### 6. 진화 탭에 시간별/요일별 차트 표시

예상 소요: 45~70분

- `bt-gui-parity.jsx`의 `BtGuiParitySection` 또는 최소 `BtHourlyPnlChart`/`BtWeekdayPnlChart`를 재사용한다.
- `BacktestDetailChart` 아래 또는 Research 분석 그룹에 배치한다.
- 현재 선택된 generation 기준으로 30초마다 갱신한다.
- 백테스트 탭의 차트와 같은 데이터 구조를 사용한다.

완료 기준:
- GUI 백테스트 이미지에 있던 시간별/요일별 손익 막대 차트가 진화 탭에서도 보인다.
- 실시간 테스트 중인 조건식의 generation 선택이 바뀌면 차트도 바뀐다.

### 7. 프론트엔드 번들 재빌드

예상 소요: 5~10분

```powershell
cd ai_strategy_loop/dashboard/webui-build
node build-app.mjs
```

완료 기준:
- 번들 파일이 갱신된다.
- 정적 테스트가 새 컴포넌트 import/export 누락 없이 통과한다.

### 8. OOS pair JSON 생성

예상 소요: 5~10분

```powershell
$pairs = Get-Content .omo\evidence\tmap-walkforward\ovn_exit2_r4_pairs.json -Raw | ConvertFrom-Json
$selected = @($pairs | Where-Object { $_.label -eq "r4_7_be_floor=0.5" })
ConvertTo-Json -InputObject $selected -Depth 4 | Set-Content -Encoding UTF8 .omo\evidence\tmap-walkforward\pairs-ovn-exit2-balance-oos.json
```

```powershell
$pairs = Get-Content .omo\evidence\tmap-walkforward\ovn_r2full_r4_pairs.json -Raw | ConvertFrom-Json
$selected = @($pairs | Where-Object { $_.label -eq "r4_9_burst_b=1.5" })
ConvertTo-Json -InputObject $selected -Depth 4 | Set-Content -Encoding UTF8 .omo\evidence\tmap-walkforward\pairs-ovn-r2full-mdd-oos.json
```

완료 기준:
- 각 JSON은 1개 후보만 포함한다.
- buy/sell 이름이 위 후보 고정 표와 일치한다.

### 9. OOS 2022/2026 실행

예상 소요: 총 20~35분

```powershell
$env:PYTHONUTF8 = "1"
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval --pairs-json .omo\evidence\tmap-walkforward\pairs-ovn-exit2-balance-oos.json --config-json .omo\evidence\tmap-walkforward\oos-2022-e32-config.json --run-id ovn_exit2_balance_oos_2022
```

```powershell
$env:PYTHONUTF8 = "1"
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval --pairs-json .omo\evidence\tmap-walkforward\pairs-ovn-exit2-balance-oos.json --config-json .omo\evidence\tmap-walkforward\oos-2026-e32-config.json --run-id ovn_exit2_balance_oos_2026
```

```powershell
$env:PYTHONUTF8 = "1"
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval --pairs-json .omo\evidence\tmap-walkforward\pairs-ovn-r2full-mdd-oos.json --config-json .omo\evidence\tmap-walkforward\oos-2022-e32-config.json --run-id ovn_r2full_mdd_oos_2022
```

```powershell
$env:PYTHONUTF8 = "1"
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval --pairs-json .omo\evidence\tmap-walkforward\pairs-ovn-r2full-mdd-oos.json --config-json .omo\evidence\tmap-walkforward\oos-2026-e32-config.json --run-id ovn_r2full_mdd_oos_2026
```

완료 기준:
- 각 실행 결과의 profit, MDD, trade count, daily trades, gate 여부가 저장된다.
- 실패 시 실패 로그와 원인을 결과표에 그대로 남긴다.

### 10. 포트폴리오 비교

예상 소요: 40~70분

- 비교 대상:
  - `r8_4`
  - `exit2 balance`
  - `r2full MDD`
- 우선순위:
  1. OOS 2022/2026 결과가 모두 있으면 OOS 기준 비교
  2. 일부 누락 시 train + available OOS를 분리 표기
- 산출물 후보:
  - `.omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-20260618.json`
  - `docs/update_log/2026-06-18_dashboard_research_records_oos_followup.md`
- 계산 항목:
  - 총수익
  - MDD
  - 거래 수
  - 승률
  - 하루 평균 거래 수
  - 연평균 수익률 추정
  - 후보 간 상관 또는 같은 날 손익 겹침 가능성

완료 기준:
- 단일 후보별 표와 3후보 조합 표가 모두 있다.
- 연평균 수익률은 투자금 기준을 명시한다. 기본 기준은 500만원과 1000만원을 함께 적는다.

### 11. 문서화와 최종 보고

예상 소요: 25~40분

- 새 문서:
  - `docs/update_log/2026-06-18_dashboard_research_records_oos_followup.md`
- 포함할 표:
  - 기능 구현 완료 표
  - OOS 결과 표
  - 포트폴리오 비교 표
  - 남은 위험/보류 표
  - 재현 명령 표

완료 기준:
- 사용자가 대시보드에서 무엇을 확인할 수 있는지 한국어로 설명되어 있다.
- 어떤 파일이 새 기록 원장 역할을 하는지 명확하다.

## 검증 명령

예상 소요: 15~30분

```powershell
pytest tests/unit/dashboard/test_backtest_analysis.py -q
```

```powershell
pytest tests/unit/test_dashboard* -q
```

```powershell
pytest tests/unit/dashboard/test_backtest_jobs.py -q
```

```powershell
pytest tests/unit/ -q
```

```powershell
git diff --check
```

```powershell
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

선택 검증:

```powershell
python scripts/verify_nonrelease_sync.py
```

```powershell
python scripts/smoke_offline_gui.py
```

## 예상 전체 소요

| 구간 | 예상 시간 |
|---|---:|
| 테스트 기준 고정 | 20~30분 |
| 연구 기록 색인/API | 65~100분 |
| 진화 탭 연구 기록 UI | 45~70분 |
| GUI parity API/UI | 80~120분 |
| 번들 재빌드/정적 검증 | 10~20분 |
| OOS pair 생성/4회 실행 | 25~45분 |
| 포트폴리오 비교 | 40~70분 |
| 문서/최종 보고 | 25~40분 |
| 검증 | 15~30분 |
| 합계 | 약 5.5~8.5시간 |

## 최종 보고 표 형식

### 기능 완료 표

| 항목 | 상태 | 확인 위치 | 결과 |
|---|---|---|---|
| 연구 기록 색인 API | 완료/보류 | `/research_records` | 캠페인 수, 후보 수 |
| 진화 탭 기록 패널 | 완료/보류 | Evolution 탭 | 최신 연구 표시 여부 |
| 시간별/요일별 차트 | 완료/보류 | Evolution 탭 선택 generation | `hourly`, `weekday` 표시 여부 |
| 백테스트 기록 대시보드 표시 | 완료/보류 | 연구 기록 패널 | OOS/summary/log 연결 여부 |

### OOS 결과 표

| 후보 | 구간 | 수익 | MDD | 거래 수 | 하루 평균 거래 | Gate | 연평균 수익률 추정 |
|---|---:|---:|---:|---:|---:|---|---:|
| `exit2 balance` | 2022 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `exit2 balance` | 2026 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `r2full MDD` | 2022 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `r2full MDD` | 2026 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |

### 포트폴리오 비교 표

| 조합 | 기준 구간 | 수익 | MDD | 연평균 수익률 | 장점 | 위험 |
|---|---|---:|---:|---:|---|---|
| `r8_4` 단독 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `r8_4 + exit2` | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `r8_4 + r2full` | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |
| `r8_4 + exit2 + r2full` | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 | 실행 후 기입 |

## 진행 중 1시간 체크 방식

실행 단계로 넘어가면 매 1시간마다 다음 표로 보고한다.

| 시각 | 완료 작업 | 진행률 | 남은 작업 | 남은 예상 시간 | 위험/막힘 |
|---|---|---:|---|---:|---|
| HH:MM | 실행 중 기입 | 실행 중 기입 | 실행 중 기입 | 실행 중 기입 | 실행 중 기입 |

## 중단 조건

- OOS 실행이 보호 경로에 쓰기를 시도하면 중단한다.
- 실거래/브로커 연결이 요구되면 중단한다.
- `_database/` 운영 DB 쓰기가 필요해지면 중단한다.
- 생성된 차트가 CSV 누락을 오류로 터뜨리면 구현을 되돌리지 말고 빈 상태 처리로 수정한다.
- 테스트가 기존 unrelated 실패인지 새 실패인지 구분되지 않으면 실패 로그를 보존하고 보고한다.
