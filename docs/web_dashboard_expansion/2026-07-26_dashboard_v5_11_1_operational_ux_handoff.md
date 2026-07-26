# 대시보드 v5.11.1 운영 UX 후속 작업 상세 핸드오프

## 0. 문서 목적과 우선순위

이 문서는 `2026-07-25_dashboard_v5_11_0_handoff_and_next_execution.md` 이후 수행한 대시보드 운영 UX 개선을 인계한다. 이번 작업의 핵심은 새 기능 수를 늘리는 것이 아니라 다음 실제 사용자 불편을 닫는 것이었다.

- Live와 Backtest 결과 차트를 그룹 상자 안에 다시 묶지 않고, 차트 하나를 증거 단위 하나로 취급하는 동일 크기 매트릭스로 정리한다.
- Backtest 결과 라이브러리가 선택되지 않는 이유를 UI 상태 문제가 아닌 실제 산출물 상태까지 추적한다.
- 서버 재시작 또는 세션 만료 후 Replay가 `4401 session_required`로 종료되는 경로를 실제 브라우저에서 재현하고 수정한다.
- History를 결정 추적 중심이 아니라 연구 선택과 상세 검토 중심으로 재구성한다.
- Reports, 성과, 설정, 용어 화면을 넓은 화면에 맞게 확장하고 데이터가 없는 값을 꾸며내지 않는다.
- 조건식 검증 401, 조건식 코드 조회 시간 초과, 에디터 높이, CPU 기본 엔진 수 등 운영 마찰을 함께 정리한다.

다음 작업자는 아래 순서로 문맥을 읽는다.

1. 루트 `AGENTS.md`
2. `docs/AGENTS.md`
3. 이 문서
4. `docs/web_dashboard_expansion/2026-07-25_dashboard_v5_11_0_handoff_and_next_execution.md`
5. `docs/web_dashboard_expansion/2026-07-23_dashboard_v5_11_0_recovery_development_and_release_report.md`

이 문서는 V3K 승인 상태를 변경하지 않는다. V3K는 계속 `3/6`이며, 실거래·브로커·USER_ACK·보호 DB 전환을 허가하는 문서가 아니다.

---

## 1. 인계 시점의 기준 상태

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 작업 브랜치 | `codex/dashboard-v5111-ux-acceptance` |
| 작업 시작 HEAD | `b2f15855` |
| 시작 커밋 제목 | `대시보드 v5.11 후속 작업을 인계` |
| 대시보드 release | `v5.11.0` |
| 최종 frontend/backend build | `e8587698` |
| 최종 CSS build | `4ae93c01` |
| API contract | `2` |
| 기본 배치 파일 | `stom_dashboard.bat` |
| 최신 검증 주소 | `http://127.0.0.1:8771/ui/v4/` |
| 데이터 진실성 | 미발행 값은 `미발행/사용 불가`로 표시하며 추정값을 만들지 않음 |
| 성능 증명 | `performance_proved=false` 유지 |
| V3K gate | `3/6` 유지 |

### 1.1 실행 중 서버를 반드시 구분할 것

인계 시점에는 두 서버가 동시에 존재한다.

| 포트 | PID | 상태 | 조치 |
|---|---:|---|---|
| `8770` | `124704` | 이전 관리자 권한 프로세스. 현재 셸의 `Stop-Process`가 `Access denied`로 거부됨 | 해당 관리자 명령창에서 `Ctrl+C` 또는 창 닫기로 종료한 뒤 최신 배치를 기본 포트로 재실행해야 함 |
| `8771` | `133944` | 이번 변경의 최신 build `e8587698`로 직접 배치 실행됨 | 현재 검증용 정본. `/health`에서 frontend/backend build 일치 확인됨 |

모든 Python 프로세스를 일괄 종료하지 않는다. 특히 `taskkill /F /IM python.exe`는 금지한다.

### 1.2 작업 트리 범위

이번 커밋 범위는 `ai_strategy_loop/dashboard/`, 대시보드 단위 테스트, 이 핸드오프 문서와 생성 번들이다. 다음 항목은 기존 사용자/연구 산출물이므로 스테이징·삭제·정리하지 않는다.

- `.gjc/`, `.omo/`와 그 하위 evidence
- `docs/research/condition_research/reports/`의 별도 삭제 상태
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`
- `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`

---

## 2. 사용자 요구와 반영 결과

### 2.1 Live 탭

| 요구 | 반영 |
|---|---|
| best fitness, best MDD, token cost가 차지하던 공간 활용 | 손익·거래·gate·완료 세대를 추가한 8개 밀도형 KPI로 재구성 |
| 프로세스가 작고 현재 상황이 불명확 | 파이프라인 벨트와 단계 상태를 확대하고 현재 단계·게이트·진행률을 한 줄 상태로 유지 |
| 상세 로그가 보이지 않음 | 접힌 단일 로그 대신 최근 14건을 단계 번호와 함께 보여주는 `role=log` 콘솔 추가 |
| 생성·백테스트·채점·반복 카드 폭이 다름 | 각 단계에 공통 `v59-matrix` 계약 적용 |
| 조건식 코드 조회 `TimeoutError` | 2.5초 제한을 10초로 늘리고 코드 조회 실패와 diff 조회 지연을 분리 |
| 조건식 코드가 성공했는데 diff 실패로 전체가 실패처럼 보임 | 코드 오류와 비교 오류 상태를 분리하고 diff 지연은 경고로만 표시 |

주요 파일:

- `frontend/v4-research.jsx`
- `frontend/panels-config.jsx`
- `frontend/code-viewer.jsx`
- `frontend/v4.css`

### 2.2 Live·Backtest 공통 결과 차트

이번 변경의 중심 원칙은 **차트 하나 = 독립 증거 카드 하나**이다.

- MDD를 별도 “위험 증거” 그룹으로 감싸지 않고 Underwater와 독립 카드로 배치했다.
- GUI parity의 위험·타이밍·보유 그룹 래퍼를 제거했다.
- 퀀트 인사이트의 회귀·보유시간·자기상관·연속 손익을 각각 독립 카드로 분리했다.
- 일별 손익과 거래 rolling처럼 기존 차트와 실질적으로 중복되는 parity 차트는 공통 매트릭스에서 제외했다.
- 전체 분석 차트는 `.bt-analysis-matrix` 하나에서 배치된다.
- 기본 카드 높이는 `520px`이며, 모든 직접 자식 카드의 최소·최대 높이를 동일하게 고정했다.
- 누적 거래/손익 차트의 전폭 강제를 제거했다.
- 월별 수익 캘린더 셀을 `64×44px`로 확대하고 표의 최소 폭을 확보했다.
- 전체 화면 분석도 동일한 평면 매트릭스를 사용한다.
- 데이터가 없으면 빈 차트를 그리지 않고 해당 카드에서 이유를 표시한다.

주요 파일:

- `frontend/bt-result-area.jsx`
- `frontend/bt-gui-parity.jsx`
- `frontend/bt-quant.jsx`
- `frontend/bt-distribution-charts.jsx`
- `frontend/v4.css`

### 2.3 Backtest 탭

| 요구 | 반영 |
|---|---|
| 기본 결과 3열과 2·3·4열 선택 복구 | 저장 키 `stom_v511_result_layout`, 기본 `3`, 버튼 `2/3/4` 유지 |
| 넓은 화면에서도 실제 열 수가 과도하게 줄어듦 | 열 계산 단위를 `432px`에서 `360px`로 조정 |
| 결과 라이브러리가 선택되지 않음 | 실행 기록과 분석 가능한 결과를 구분하고 진화 세대 결과 라이브러리를 상단에 항상 펼침 |
| 취소·실패 잡이 결과처럼 보임 | 기본 목록은 `open_result` 가능한 잡만 표시하고 종료 기록은 별도 토글 |
| 결과가 없는데 클릭 장애처럼 보임 | “분석 산출물이 남아 있는 잡 결과가 없음”과 재실행 안내를 명시 |
| 최신 유효 진화 세대를 수동으로 찾아야 함 | 최신 성공/CSV 세대를 자동 선택 |
| 매수·매도 에디터가 작음 | 기본 `500px`, 집중 모드 `720px`로 확대 |
| 기본 엔진 수 | `navigator.hardwareConcurrency`의 25%, 최소 1·최대 16 |
| 조건식 검증 401 | `/bt/strategy/validate`를 쓰기 권한이 아닌 `SAFE_BACKTEST`로 분류 |

중요한 진단 결과:

- `/bt/jobs`는 327건을 반환했다.
- 그중 실제 `open_result` 가능한 분석 산출물은 0건이었다.
- 따라서 공통 선택 상태가 깨진 것이 아니라, 종료된 실행 기록만 남아 있었던 것이 직접 원인이었다.
- 진화 세대 선택은 정상이며 최신 `g14` 결과를 열 수 있었다.

즉, UI는 결과가 없는 상태를 정직하게 설명하도록 수정했지만 **공식 완료 Backtest artifact 1건을 생성한 뒤 잡 결과 선택 경로를 검증하는 작업은 아직 남아 있다.**

### 2.4 History 탭

결정 추적 원장과 verdict 중심 흐름을 제거하고 다음 4단계로 재구성했다.

1. `연구 선택`: 캠페인과 연구 ID를 고정한다.
2. `결과 비교`: run과 winner 세대를 같은 기준으로 비교한다.
3. `결과 상세`: 조건식, 반복 성과, 공통 Backtest 차트를 검토한다.
4. `근거 · 문서`: 계보, A/B, heatmap, funnel, 연구 색인을 조회한다.

선택만으로 임의 단계가 자동 전환되지 않게 해 사용자가 현재 위치를 유지한다. 상세 화면에서 `다시 비교`, `보고서 열기` 경로를 제공한다.

주요 파일:

- `frontend/v4-history.jsx`
- `tests/unit/dashboard/test_shell_wiring_parity.py`
- `tests/unit/dashboard/test_v4_replay_history_ui.py`

### 2.5 Reports 탭과 생성 HTML

- `결과 Summary`, `HTML 보고서`, `정본 · 출처` 3개 보기를 추가했다.
- Summary를 기본 보기로 설정했다.
- 연평균 수익률, 누적 수익률, MDD, 일평균 거래 횟수, 하루 최대 보유 종목, 총 거래 수를 KPI와 표로 표시한다.
- 연평균 수익률·일평균 거래·최대 보유는 다음 실제 발행 필드만 탐색한다.
  - `annual_return_pct`, `cagr`, `cagr_pct`
  - `daily_avg_trades`, `avg_trades_per_day`
  - `max_hold_count`, `max_holdings`, `max_concurrent_positions`
- 값이 발행되지 않았으면 `미발행`으로 표시한다. 0이나 추정값으로 대체하지 않는다.
- 생성 Backtest HTML에도 동일한 어두운 Summary 카드·막대·표를 추가했다.
- Python 렌더링 책임은 새 `backtest_report_summary.py`로 분리했다.

주요 파일:

- `frontend/v4-reports.jsx`
- `frontend/report-summary-board.jsx`
- `backtest_report.py`
- `backtest_report_summary.py`

### 2.6 성과 탭

기존 상세 표 위에 데이터 기반 시각화를 추가했다.

- 수익률 × MDD 산점도
- AI 결과 상태 분포
- gate 통과, 양수 수익, 평균 일거래, 인간 벤치마크 수 KPI
- 반복 성과 분석의 세대별 gate 누적 통과율
- `score ÷ (1 + MDD/100)` advisory 효율 추이

효율 값은 연구 비교용이며 성능 증명으로 표시하지 않는다.

주요 파일:

- `frontend/hof-performance-overview.jsx`
- `frontend/chart-hall-of-fame.jsx`
- `frontend/evolution-analysis.jsx`

### 2.7 Replay 탭

원인:

- Replay 서버 세션은 프로세스 로컬이며 TTL이 있다.
- 이미 열린 브라우저 페이지는 서버 재시작이나 세션 만료 후에도 곧바로 `/sim/ws`를 열었다.
- 새 서버에 유효한 세션이 없으므로 WebSocket이 `4401 session_required`로 닫혔다.

수정:

- Replay 시작 직전에 `/ui/chart-replay`를 same-origin credentials, no-store, 6초 제한으로 조회한다.
- 세션 갱신 성공 후에만 `new WebSocket(...)`을 실행한다.
- 세션 준비 실패는 날짜·종목 문제가 아니라 세션 준비 실패로 구분해 안내한다.

실제 토글 검증:

1. 8771 Replay 페이지를 연 상태로 유지했다.
2. 서버 PID `105436`을 종료했다.
3. 같은 배치로 새 서버 PID `133944`를 시작했다.
4. 페이지 새로고침 없이 `최근 거래일`을 클릭했다.
5. 서버 로그에서 `GET /ui/chart-replay 200` 후 `WebSocket /sim/ws [accepted]`를 확인했다.
6. UI는 `playing`, `수신 봉 1/376`, OHLC 범위를 표시했다.
7. `정지` 후 `idle`로 복귀했다.

주요 파일:

- `frontend/sim-tab-root.jsx`
- `frontend/sim-tab-utils.jsx`

### 2.8 설정·용어·연구 자산

- 설정 화면을 넓은 화면 2열 전체 캔버스로 확장했다.
- 설정과 용어 카드 높이를 공통 `460px`로 맞추고 내부 본문만 스크롤한다.
- 용어는 2열을 사용하고 900px 이하에서 1열로 전환한다.
- 연구 자산은 현재 보기 설명, 표 글자 크기, 셀 패딩을 확대했다.
- Reports 정본 상세는 작은 연속 텍스트 대신 반응형 데이터 카드로 정리했다.

---

## 3. 구현 파일 지도

| 책임 | 파일 |
|---|---|
| Live KPI·단계 매트릭스·로그 | `frontend/v4-research.jsx`, `frontend/panels-config.jsx` |
| 조건식 조회 시간 제한 | `frontend/panels-config.jsx`, `frontend/code-viewer.jsx` |
| Backtest 실행 기본값·잡 결과 상태 | `frontend/bt-tab-run.jsx` |
| 진화 결과 자동 선택 | `frontend/bt-tab-analysis.jsx`, `frontend/bt-tab-root.jsx` |
| 에디터 높이 | `frontend/bt-tab-library.jsx` |
| 결과 차트 평면 매트릭스 | `frontend/bt-result-area.jsx`, `frontend/bt-gui-parity.jsx`, `frontend/bt-quant.jsx` |
| 월별 캘린더 | `frontend/bt-distribution-charts.jsx` |
| History 4단계 | `frontend/v4-history.jsx` |
| Report Summary UI | `frontend/v4-reports.jsx`, `frontend/report-summary-board.jsx` |
| Report Summary HTML | `backtest_report.py`, `backtest_report_summary.py` |
| 성과 시각화 | `frontend/chart-hall-of-fame.jsx`, `frontend/hof-performance-overview.jsx`, `frontend/evolution-analysis.jsx` |
| Replay 세션 사전 갱신 | `frontend/sim-tab-root.jsx`, `frontend/sim-tab-utils.jsx` |
| 검증 401 권한 | `security_capabilities.py` |
| 공통 레이아웃·가독성 | `frontend/v4.css` |
| 생성 번들 | `frontend/bundle/app.js`, `frontend/bundle/manifest.json`, HTML entry pin |
| 신규 운영 UX 계약 | `tests/unit/dashboard/test_v5111_operational_ux.py` |

---

## 4. 검증 증거

### 4.1 Red → Green

초기 회귀 계약:

```text
python -m pytest tests/unit/dashboard/test_v5111_operational_ux.py tests/unit/dashboard/test_backtest_report.py -q
7 failed, 20 passed
```

실패 항목은 Replay 세션 사전 갱신 부재, 잡 결과/종료 기록 미분리, 평면 차트 매트릭스 부재, History 결정 원장 잔존, Report/성과 Summary 부재, 설정/용어 동일 높이 부재였다.

수정 후 집중 검증:

```text
36 passed in 17.75s
```

### 4.2 전체 대시보드 테스트

```text
pytest tests/unit/dashboard -q
899 passed, 2 skipped in 455.82s
```

### 4.3 프런트 빌드

```text
npm run build
[runtime-jsx] PASS 92 JSX / 542 graph files
[build-app][bundle] app.js v=e8587698
[build-app][bundle] v4.css v=4ae93c01
```

### 4.4 실행 서버

최신 8771 서버의 `/health` 응답:

- `status=ok`
- shell build `e8587698`
- backend build `e8587698`
- process PID `133944`

### 4.5 실제 브라우저/Computer Use 검토

완료:

- 실제 브라우저에서 Backtest의 공통 결과 매트릭스 20개 카드가 동일 높이 `520px`를 사용함을 확인했다.
- Reports의 Summary/HTML/정본 탭과 요구 지표를 확인했다.
- History 4단계와 결정 원장 제거를 확인했다.
- 성과 시각화 3종을 확인했다.
- Settings 카드 6개가 동일 높이 `460px`를 사용함을 확인했다.
- Replay stale-session 재시작 시나리오를 실제로 통과했다.
- Computer Use로 3440px급 Chrome 창에서 Live 탭을 직접 열어 파이프라인, 8개 KPI, 상세 로그, 하단 차트 배치를 확인했다.

미완료:

- Computer Use가 Backtest 탭 이동 시 현재 브라우저 URL을 안전하게 판별하지 못해 해당 턴의 Windows 제어를 중단했다.
- 최종 CSS 이후 Backtest, History, Reports, 성과, Replay, 설정, 용어의 **Computer Use 육안 스크린샷 재검토**가 남아 있다.
- 이 미완료는 단위/브라우저 계약 실패가 아니라 Windows 제어 안전 중단이다.

---

## 5. 재실행 절차

### 5.1 권장: 8770 정리 후 기본 주소 복구

1. 관리자 권한으로 열려 있는 기존 STOM Dashboard 명령창을 찾는다.
2. 그 창에서 `Ctrl+C`로 PID `124704`를 종료한다.
3. 포트가 비었는지 확인한다.

```powershell
Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue
```

4. 작업 루트에서 배치 파일을 실행한다.

```bat
stom_dashboard.bat
```

5. `/health`의 frontend/backend build가 모두 `e8587698`인지 확인한다.

```powershell
Invoke-RestMethod http://127.0.0.1:8770/health
```

### 5.2 8771 검증 인스턴스를 계속 사용할 때

```bat
set STOM_DASHBOARD_PORT=8771
set STOM_DASHBOARD_NO_BROWSER=1
set STOM_DASHBOARD_NO_PAUSE=1
stom_dashboard.bat
```

### 5.3 소스 수정 후 필수 빌드

```powershell
Set-Location ai_strategy_loop/dashboard/webui-build
npm run build
```

프런트 소스만 바꾸고 `bundle/app.js`, manifest, HTML pin을 갱신하지 않은 상태를 완료로 보고하지 않는다.

---

## 6. 다음 작업 우선순위

### P0. 운영 주소와 육안 검토 닫기

1. 관리자 8770 프로세스를 정상 종료한다.
2. 최신 배치를 8770으로 다시 실행한다.
3. `/health`에서 frontend/backend build `e8587698` 일치를 확인한다.
4. Computer Use를 새 턴에서 다시 연결한다.
5. 아래 화면을 1920px와 3440px 기준으로 직접 확인한다.

| 탭 | 확인할 것 |
|---|---|
| Live | 8개 KPI가 과도한 높이를 차지하지 않는지, 단계 로그 14건이 읽히는지, 단계별 매트릭스 폭이 같은지 |
| Backtest | 진화 결과가 상단에서 선택되는지, 잡 결과 0건 안내가 명확한지, 기본 3열인지 |
| Backtest 결과 | 모든 차트가 독립 카드인지, 카드 높이 520px인지, 월별 캘린더가 읽히는지, 누적 차트가 전폭이 아닌지 |
| History | 4단계가 순서대로 작동하고 선택이 임의로 건너뛰지 않는지 |
| Reports | Summary가 기본인지, HTML/정본 전환이 명확한지, 미발행 값이 정직한지 |
| 성과 | 산점도·분포·운영 KPI가 표를 가리지 않는지 |
| Replay | 최근 거래일 재생, 일시정지, seek, 정지와 4401 미발생 |
| 설정·용어 | 넓은 화면 2열, 동일 높이, 내부 스크롤, 작은 글자 문제 없음 |

Computer Use가 다시 중단되면 Windows 입력을 다른 자동화로 우회하지 말고, 브라우저 검증 증거와 중단 이유를 분리해서 기록한다.

### P1. 실제 Backtest 완료 artifact 인수 테스트

현재 가장 중요한 기능 공백이다.

1. 보호 DB나 V3K gate를 건드리지 않는 공식 offline Backtest profile을 선택한다.
2. 최소 1건을 `success` 또는 `no_trades`가 아니라 실제 분석 파일을 가진 openable 결과로 완료한다.
3. `/bt/jobs`에서 `open_result` action과 artifact 상태를 확인한다.
4. 잡 결과를 클릭해 다음을 확인한다.
   - 결과 identity와 source hash
   - Summary, Equity, Distribution, Underwater
   - monthly calendar, rolling, MAE/MFE, exit/orderflow
   - GUI parity 개별 카드
   - 2·3·4열 전환과 새로고침 후 저장
   - Monte Carlo 미지원 시 명확한 unavailable 카드
5. 같은 결과로 Report Summary를 열어 연평균 수익률·일평균 거래·최대 보유 필드가 실제로 발행되는지 확인한다.
6. 테스트용 결과를 demo로 위장하거나 누락 값을 0으로 채우지 않는다.

### P1. 조건식 운영 경로 재확인

1. 매수·매도 에디터가 기본 500px, 집중 720px로 보이는지 확인한다.
2. 조건식 검증 버튼이 401이 아니라 200과 실제 검증 결과를 반환하는지 확인한다.
3. 느린 조건식 코드 조회에서 10초까지 기다린 뒤 명확한 실패 문구가 나오는지 확인한다.
4. strategy code 성공 + diff 실패 조합에서 코드가 계속 표시되는지 확인한다.

### P2. 시각 품질 미세 조정

P0/P1 인수 테스트에서 실제 결함이 발견될 때만 수정한다.

- 520px 고정 높이가 작은 노트북에서 과도하면 모바일/태블릿 전용 높이 토큰만 조정한다.
- 월별 캘린더는 읽기 가능성을 우선하며 셀을 다시 축소하지 않는다.
- 차트를 새로운 그룹 상자 안에 다시 묶지 않는다.
- 새로운 유사 차트를 추가하기 전에 기존 데이터·목적 중복을 검사한다.
- 넓은 화면에서 카드 폭을 늘리되 본문 글자를 축소해 해결하지 않는다.

---

## 7. 다음 작업자 검증 명령

```powershell
# 프런트 그래프와 번들
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev/ai_strategy_loop/dashboard/webui-build
npm run build

# 집중 계약
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev
pytest tests/unit/dashboard/test_v5111_operational_ux.py tests/unit/dashboard/test_backtest_report.py tests/unit/dashboard/test_backtest_phase5.py tests/unit/dashboard/test_v4_replay_history_ui.py -q

# 전체 대시보드
pytest tests/unit/dashboard -q

# 비릴리스·diff 안전성
python scripts/verify_nonrelease_sync.py
git diff --check

# 보호 런타임 경로 오염 확인
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

---

## 8. 변경 금지 경계

- `performance_proved=true`로 변경하지 않는다.
- 실제 발행되지 않은 연평균 수익률, 일평균 거래 수, 최대 보유 수를 계산해 정본처럼 표시하지 않는다.
- Replay 4401을 날짜·종목 오류로만 포장하지 않는다.
- 실행 기록과 분석 가능한 결과를 다시 같은 목록 의미로 섞지 않는다.
- History에 결정 원장/verdict 중심 흐름을 다시 추가하지 않는다.
- 차트들을 “위험”, “진단”, “퀀트” 그룹 상자 안에 재중첩하지 않는다.
- Reports의 CSP, sandbox, script-free, provenance 경계를 약화하지 않는다.
- V3K gate 4~6, live broker/order, protected DB cutover를 승인 없이 진행하지 않는다.
- 기존 `.gjc`, `.omo`, 연구 evidence, 보호 런타임 파일을 정리 대상으로 취급하지 않는다.
- `git add -A`, `git reset --hard`, 광범위 stash/clean을 사용하지 않는다.

---

## 9. 인수 완료 기준

다음 조건을 모두 만족할 때 이 후속 작업을 완전히 닫을 수 있다.

- [ ] 8770이 최신 build `e8587698`로 단일 실행된다.
- [ ] Computer Use로 주요 8개 탭의 최종 육안 검토가 완료된다.
- [ ] 실제 openable Backtest artifact 최소 1건이 결과 라이브러리에서 선택된다.
- [ ] 기본 3열과 2·3·4열 전환이 실제 데이터로 확인된다.
- [ ] 모든 분석 차트가 독립 동일 높이 매트릭스이며 중복 그룹이 없다.
- [ ] Replay stale-session 시나리오에서 4401이 재발하지 않는다.
- [ ] Reports Summary에 실제 발행 지표 또는 정직한 `미발행` 상태가 표시된다.
- [ ] 전체 dashboard test, runtime JSX, bundle sync, nonrelease sync, diff check가 통과한다.
- [ ] V3K `3/6`, `performance_proved=false`, 보호 경계가 유지된다.

## 10. 최종 인계 문장

이번 변경은 Live와 Backtest의 시각 구조를 “그룹 안의 여러 차트”에서 “독립 증거 카드의 동일 매트릭스”로 전환하고, Replay 세션 만료·조건식 검증 권한·결과 라이브러리의 상태 오해를 실제 원인에 맞춰 수정했다. 자동 검증과 stale-session 실제 재현은 통과했지만, 관리자 권한으로 남은 8770 서버를 최신 build로 교체하는 작업과 실제 openable Backtest artifact를 이용한 최종 인수 테스트, Computer Use의 나머지 탭 육안 검토는 다음 실행의 P0/P1이다.
