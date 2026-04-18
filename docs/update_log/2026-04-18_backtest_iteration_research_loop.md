# 2026-04-18 Backtest Iteration Research Loop v1

## 목적

`discovery research`에서 후보 N개를 한 라운드로 실행하고, 후보별 백테스트/비교/승격 평가를 수집해 `best_candidate`를 선택하는 빠른 연구 루프를 검증했다.

이번 Task 6의 범위는 구현 변경이 아니라 검증, 실제 파일럿 시도, 후보 전략 cleanup 확인, 업데이트 로그 기록이다.

## 변경 사항 요약

- `--run-candidates` 다중 후보 실행 모드 검증
- 후보별 전략명 `{name}__candNNN` 생성 경로 검증
- 후보별 단일 expression 필터 적용 경로 검증
- baseline CSV 분석 1회와 후보 N개 실행 경로 검증
- 후보별 comparison/promotion 결과 수집 경로 검증
- deterministic ranking과 `best_candidate` 선택 경로 검증
- loser/failed 후보 cleanup 정책 검증
- `--cleanup-best-candidate`, `--keep-loser-candidates` 옵션 경로 검증
- `iteration_plan`, `candidates`, `best_candidate`, `cleanup_summary` 리포트 필드 검증

## 검증

### focused tests

명령:

```powershell
python -m pytest tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_subcommands.py tests/unit/test_ai_controller.py -q
```

결과:

```text
152 passed in 13.38s
```

### full unit tests

명령:

```powershell
python -m pytest tests/unit/ -q
```

첫 실행 결과:

```text
2 failed, 958 passed, 1 skipped, 7 warnings in 81.73s (0:01:21)
```

실패 원인:

- `_database/strategy.db`가 0바이트라 `--list-strategies` 경로에서 `no such table: stockbuy` 발생
- `_database/setting.db`가 0바이트라 `ui.ui_mainwindow` import 경로에서 `no such table: main` 발생

회복 조치:

```powershell
python -c "from utility.database_check import database_check; print(database_check())"
```

결과:

```text
(True, None)
```

실패했던 테스트 재확인:

```powershell
python -m pytest tests/unit/test_exit_codes.py::TestExitCodes::test_success_returns_zero tests/unit/test_ui_jisu_cleanup.py::test_ui_mainwindow_import_succeeds_without_deleted_jisu_module -q
```

결과:

```text
2 passed, 3 warnings in 11.00s
```

full unit tests 재실행 결과:

```text
960 passed, 1 skipped, 10 warnings in 77.46s (0:01:17)
```

### non-release sync

명령:

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
[OK] 워크트리에 .pyd 파일이 없습니다.
[OK] 텔레그램 qlist 계약이 현재 MainWindow 순서와 일치합니다.
[OK] MainWindow가 텔레그램 런타임을 시작합니다.
[OK] 설정 변경 전파가 TelegramProcessAlive 경로를 사용합니다.
[OK] 텔레그램 alive helper가 존재합니다.
[OK] Jisu cleanup matches V2.70 removal.
[OK] Shutdown cleanup matches current MainWindow runtime.
[OK] WebCrawling runtime wiring matches QThread contract.
[OK] static.py compatibility exports match runtime contract.
[OK] WebCrawling stop contract includes timeout and cancellation guards.
[OK] Key loading safety guard is present.
[OK] Kiwoom P/L rounding matches expected loss math.
[OK] 비정식 워크트리에서 시리얼키 UI 생성이 차단됩니다.
[OK] 설정 저장이 워크트리 시리얼키 정책을 따릅니다.
[OK] dict_set 적재가 비정식 워크트리 시리얼키 정책을 따릅니다.
[OK] legacy utility/setting.py도 비정식 워크트리 시리얼키 정책을 따릅니다.

모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 파일럿

### 명령

```powershell
$env:STOM_ALLOW_MINIMAL_SETTING='1'
python stom_backtest.py discovery research AutoResearchIterationPilot_20260418_T6 `
  --input backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv `
  --base-buy-strategy Min_B_Study_251227 `
  --sell Min_S_Study_251227 `
  --start 20250407 `
  --end 20250418 `
  --timeframe min `
  --run-candidates `
  --candidate-count 3 `
  --candidate-start 20250407 `
  --candidate-end 20250407 `
  --candidate-timeout 120 `
  --cleanup-best-candidate
```

### 실제 핵심 결과

결과:

```json
{
  "status": "error",
  "phase": "research_loop",
  "message": "[Errno 2] No such file or directory: 'backtest\\\\csv\\\\stock_bt_Min_B_Study_251227_20260415220536.csv'"
}
```

핵심 필드:

```text
status: error
phase: research_loop
candidates count: 0 (후보 생성 전 실패)
best_candidate: 없음 (응답에 미포함)
cleanup_summary: 없음 (후보 생성 전 실패)
```

실패 원인:

- 지정된 입력 CSV `backtest/csv/stock_bt_Min_B_Study_251227_20260415220536.csv`가 이 checkout에 존재하지 않는다.
- 로컬 ignored `strategy.db`도 `database_check()` 직후의 빈 스키마 상태라 `Min_B_Study_251227`, `Min_S_Study_251227` 전략이 들어 있지 않다.
- 따라서 파일럿은 후보 생성 및 후보 백테스트 단계에 도달하지 못했다.

## candidate strategy cleanup 확인

확인 명령:

```powershell
@'
import sqlite3
from cli.paths import DB_STRATEGY
names = [f'AutoResearchIterationPilot_20260418_T6__cand{i:03d}' for i in range(1, 4)]
with sqlite3.connect(DB_STRATEGY) as con:
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stockbuy'")
    has_stockbuy = cur.fetchone() is not None
    print('DB_STRATEGY', DB_STRATEGY)
    print('stockbuy_table', has_stockbuy)
    for name in names:
        if has_stockbuy:
            cur.execute('SELECT COUNT(*) FROM stockbuy WHERE "index"=?', (name,))
            count = cur.fetchone()[0]
        else:
            count = 'table_missing'
        print(name, count)
'@ | python -
```

결과:

```text
DB_STRATEGY C:\System_Trading\STOM\STOM_V.wt-backtest-iteration\_database\strategy.db
stockbuy_table True
AutoResearchIterationPilot_20260418_T6__cand001 0
AutoResearchIterationPilot_20260418_T6__cand002 0
AutoResearchIterationPilot_20260418_T6__cand003 0
```

`--cleanup-best-candidate`를 사용한 파일럿은 후보 생성 전 실패했지만, 확인 대상 후보 전략명 `AutoResearchIterationPilot_20260418_T6__cand001`부터 `__cand003`까지는 `strategy.db`에 남아 있지 않다.

## 남은 리스크

- 이 checkout에는 요청된 파일럿 입력 CSV와 기준 전략 DB 데이터가 없어 실제 후보 3개 백테스트, ranking, `best_candidate`, `cleanup_summary`의 런타임 성공 사례는 확인하지 못했다.
- 단위 테스트는 다중 후보 루프의 정상/실패/cleanup/report 경로를 통과했지만, 실제 장기간 데이터 품질 검증을 대체하지 않는다.
- `best_candidate`는 promotion 통과 후보가 아닐 수 있으며, 최종 채택 전 `discovery promote` 또는 별도 WFO 검증이 필요하다.
- 1일 후보 구간은 런타임 smoke 검증에는 적합하지만 전략 품질 판단에는 표본이 작다.
- 결과 CSV와 `_database`는 로컬 ignored 런타임 산출물이라 작업 커밋에는 포함하지 않았다.
