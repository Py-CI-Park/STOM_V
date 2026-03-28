# STOM V2.51 CLI 종합 검토 및 개발 계획서

- 작성일: 2026-03-05
- 기준 브랜치: `STOM_Version_2U-cli-research-v251`
- 기준 커밋: `f111343` (STOM V2.51.U1.5.CLI-R1)
- 목적: 현재 CLI 구현 상태의 종합 평가, 미완성/품질 미달 항목 식별, TDD 기반 개발 계획 수립

---

## 1. 결론 요약

현재 CLI 구현은 **구조적 설계는 우수하나, 실행 품질이 미달**입니다.

- **CRITICAL 결함 3건**: DICT_SET 미동기화, join() 무한 블로킹, 큐 미배수 후 프로세스 Kill
- **HIGH 결함 5건**: DB 연결 누수, 한종목 모드 불능, 날짜 검증 부재, signal 처리 미비, 미사용 코드
- **테스트 코드 0줄**: 686줄 구현에 테스트가 전무
- **실행 검증 이력 없음**: 실제 백테스트 1회 성공 증거가 없음

---

## 2. 현재 브랜치 구현 현황

### 2.1 파일 구조

| 파일 | 줄수 | 역할 | 상태 |
|------|------|------|------|
| `stom_backtest.py` | 37 | CLI 진입점 | 구현 완료 |
| `stom_backtest.bat` | 2 | Windows 배치 런처 | 구현 완료 |
| `cli/__init__.py` | 0 | 패키지 마커 | 구현 완료 |
| `cli/config.py` | 173 | 인자 파싱, 검증, 전략 목록 | 부분 완료 |
| `cli/runner.py` | 326 | 핵심 백테스트 오케스트레이터 | 부분 완료 (결함 존재) |
| `cli/output.py` | 109 | 결과 포매팅 (JSON/텍스트) | 구현 완료 (데드코드 존재) |
| `cli/queue_drain.py` | 41 | windowQ 소비자 | 구현 완료 |
| `docs/research/...review.md` | 300 | V2.51 CLI 리서치 보고서 | 문서 완료 |

**총 688줄 구현 / 0줄 테스트**

### 2.2 Phase 0 (PyQt5 의존성 격리) 수정 파일

| 파일 | 변경 | 상태 |
|------|------|------|
| `research/auxiliary_indicator/smart_vwap_bands.py` | PyQt5/pyqtgraph try/except | 완료, 정상 |
| `utility/static.py` | QTest try/except + time.sleep fallback | 완료, 정상 |
| `backtest/back_static.py` | optuna_dashboard try/except + None guard | 완료, 정상 |

---

## 3. GUI 백테스트 워크플로우 (CLI가 재현해야 할 전체 과정)

### 3.1 사용자 관점 워크플로우

```
[1] 백테스트 엔진 다이얼로그 열기
    ├── 시작일/종료일 선택
    ├── 시작시간/종료시간 설정
    ├── 평균 틱수 입력 (쉼표 구분 다중 값)
    ├── CPU 멀티 수 설정
    ├── 데이터 분류 모드 선택 (종목코드별/일자별/한종목)
    └── [한종목 모드] 특정 종목 선택

[2] 엔진 시작 버튼 클릭 → backengine_start() 실행
    ├── BackSubTotal 프로세스 20개 생성
    ├── BackEngine 프로세스 N개 생성 (엔진 클래스 자동 선택)
    ├── DB에서 종목정보 로딩 (stockinfo/codename)
    ├── moneytop 테이블에서 거래대금순위 파싱
    ├── 종목코드/일자 매핑 생성
    ├── 엔진에 종목명/데이터로딩/공유데이터 메시지 전송
    └── 엔진 대기 상태 진입

[3] 매수/매도 전략 편집기에서 전략 선택
    ├── strategy.db의 stockbuy/stocksell 테이블에서 전략 목록 표시
    ├── 매수전략 콤보박스에서 선택
    ├── 매도전략 콤보박스에서 선택
    ├── 배팅금액 입력 (백만원 단위)
    └── 평균 틱수 확인

[4] 백테스트 시작 버튼 클릭 → stock_backtest_start() 실행
    ├── Guard 체크 (프로세스 생존, 엔진 로딩 상태, 취소 진행 여부)
    ├── GUI에서 파라미터 수집 (13개)
    ├── backQ 클리어
    ├── 엔진에 '백테유형' 메시지 전송
    ├── backQ에 13-tuple 전송
    └── BackTest 프로세스 생성/시작

[5] BackTest 프로세스 내부
    ├── backQ에서 13-tuple 수신
    ├── moneytop 재조회 (시간 범위 필터링)
    ├── BackSubTotal 20개에 '백테정보' 전송
    ├── strategy.db에서 매수/매도 전략 코드 로딩
    ├── 전략 코드 compile() (GetBuyStg, GetSellStg)
    ├── Total 프로세스 생성
    ├── Total에 '백테정보' 16-tuple 전송
    ├── shared_cnt 리셋
    ├── BackSubTotal에 '백테시작' 전송
    ├── BackEngine에 전략 정보 전송
    └── mq.get()으로 완료 대기

[6] BackEngine 프로세스 (N개 병렬)
    ├── '백테정보' 메시지 수신
    ├── 전략 코드 compile + exec 준비
    ├── GetArrayData()로 데이터 블록 원자적 클레임
    ├── 틱/분봉 데이터 순회하며 전략 실행
    │   ├── exec(buystg) → 매수 조건 평가
    │   ├── exec(sellstg) → 매도 조건 평가
    │   ├── Buy()/Sell() → 모의 체결
    │   └── CalculationEyun() → 손익 계산 → BackSubTotal로 전송
    └── 모든 블록 처리 후 '백테완료' 전송

[7] BackSubTotal → Total → 결과 집계
    ├── BackSubTotal 5개가 거래결과 수집
    ├── Total이 '백테완료' 카운트
    ├── 5개 SubTotal에서 결과 병합
    ├── GetResult() (numba JIT): 승률, MDD, CAGR, TPI 계산
    ├── bootstrap_test(): 10,000회 부트스트랩 통계 검정
    ├── backtest.db에 결과 저장 (stock_bt 테이블)
    ├── PlotShow(): matplotlib 차트 생성
    └── mq.put('완료') → BackTest에 알림

[8] 결과 표시
    ├── windowQ를 통해 결과 텍스트 표시
    ├── 텔레그램 그래프 전송
    └── 사운드 알림
```

### 3.2 프로세스 아키텍처

```
MainWindow (GUI Thread)
    │
    ├── BackEngine × N (CPU 병렬, daemon)
    │   └── 데이터 로딩 + 전략 exec + 매매 시뮬레이션
    │
    ├── BackSubTotal × 20 (중간 집계, daemon)
    │   └── 거래 결과 수집 + 일괄 집계
    │
    ├── BackTest × 1 (오케스트레이터)
    │   └── 전략 로딩 + 엔진 신호 + 완료 대기
    │
    └── Total × 1 (최종 집계)
        └── 통계 계산 + DB 저장 + 차트 생성
```

### 3.3 핵심 큐 통신 구조

```
backQ:     GUI/CLI → BackTest (13-tuple 전달)
back_eques[i]: BackTest/GUI → BackEngine[i] (전략 정보, 데이터 로딩 명령)
back_sques[i]: BackEngine → BackSubTotal[i] (거래 결과)
totalQ:    BackEngine/BackSubTotal → Total (완료 신호, 집계 결과)
windowQ:   모든 프로세스 → GUI/CLI (로그 메시지)
soundQ:    Total → GUI (완료 알림)
teleQ:     Total → 텔레그램 봇 (그래프 파일)
liveQ:     Total → STOM Live (리포트)
```

---

## 4. CRITICAL 결함 (즉시 수정 필요)

### C-1. DICT_SET 미동기화 (runner.py 전체)

**문제:** CLI에서 `config.is_tick`으로 타임프레임을 지정하지만, `BackTest.Start()` 내부 (`backtest.py:290-296`)에서는 `DICT_SET['주식타임프레임']`을 사용하여 DB를 선택합니다. `DICT_SET`은 `utility/setting.py`에서 로드되는 전역 설정이며, CLI의 `config.is_tick` 값과 동기화되지 않습니다.

**영향:** 잘못된 DB에서 moneytop을 조회하여 **무결과 또는 잘못된 결과** 발생.

**수정 방향:**
```python
# runner.py run_backtest() 시작부에 추가
DICT_SET['주식타임프레임'] = config.is_tick
DICT_SET['백테스트엔진수'] = config.engine_count
DICT_SET['증권사'] = '키움증권'
# ... 기타 필요한 DICT_SET 키 동기화
```

**필요한 DICT_SET 키 전수 조사:**

| DICT_SET 키 | 사용 위치 | CLI 동기화 필요 | 현재 상태 |
|-------------|-----------|----------------|-----------|
| `주식타임프레임` | backtest.py:290 (DB 선택) | 필수 | 미동기화 |
| `백테매수시간기준` | runner.py:81 (BackSubTotal 인자) | 사용 중 (직접 전달) | OK |
| `backtest_oms_apply` | ui_backtest_engine.py:108 (엔진 선택) | 필수 | 미동기화 (config.oms로 대체) |
| `증권사` | ui_button_clicked_editer_stock.py:684 (ui_gubun 결정) | 필수 | 미동기화 |
| `blacklist_add` | ui_button_clicked_editer_stock.py:660 (블랙리스트) | 필수 | 미동기화 (config.blacklist로 대체) |
| `백테일괄로딩` | backengine_base.py:308 (SharedMemory vs pickle) | 선택 | 미동기화 |
| `timeframe` 관련 | 다수 엔진 파일 | 조사 필요 | 미동기화 |

### C-2. proc_backtest.join() 무한 블로킹 (runner.py:253)

**문제:** `proc_backtest.join()` 에 타임아웃이 없습니다. `BackTest.Start()` 내부에서 `mq.get()` (backtest.py:361)이 무한 대기하므로, Total 프로세스가 실패하면 CLI가 영구 행(hang) 상태에 빠집니다.

**영향:** CLI 프로세스가 영원히 종료되지 않음. Ctrl+C로만 탈출 가능.

**수정 방향:**
```python
proc_backtest.join(timeout=config.timeout or 3600)
if proc_backtest.is_alive():
    proc_backtest.kill()
    result['message'] = '백테스트 시간 초과 (timeout)'
```

### C-3. finally 블록에서 큐 미배수 후 프로세스 Kill (runner.py:280-283)

**문제:** `_cleanup_procs()` 가 프로세스를 즉시 kill하지만, multiprocessing.Queue 내부의 미소비 데이터를 drain하지 않습니다. Windows에서 Queue의 내부 feeder thread가 파이프 버퍼에 쓰기 도중 프로세스가 kill되면 **데드락 또는 리소스 누수** 발생.

**영향:** Windows에서 간헐적 행(hang) 또는 좀비 프로세스 발생.

**수정 방향:**
```python
finally:
    # 1. 큐 drain
    for q in [backQ, totalQ, soundQ, liveQ, teleQ] + back_sques + back_eques:
        while not q.empty():
            try: q.get_nowait()
            except: break
    # 2. drainer 종료
    drainer.stop()
    drainer.join(timeout=2)
    # 3. 프로세스 kill
    _cleanup_procs()
```

---

## 5. HIGH 결함 (조기 수정 권장)

### H-1. DB 연결 누수 (runner.py:112-124)

**문제:** `sqlite3.connect(db)` 이후 `pd.read_sql()` 호출에서 예외 발생 시 `con.close()`가 호출되지 않습니다. 동일한 문제가 `_extract_metrics()` (runner.py:299-301)에도 존재.

**수정:** `with` 컨텍스트 매니저 또는 `try/finally` 사용.

### H-2. `한종목 로딩` 모드 사용 불가 (runner.py:156)

**문제:** `one_code = ''`가 하드코딩되어 있고, `--one-code` CLI 인자가 없습니다. `config.py:72-74`에서 `--divid-mode '한종목 로딩'` 선택은 가능하지만 종목 코드를 지정할 방법이 없어 항상 검증 실패.

**수정:** `config.py`에 `--one-code` 인자 추가, `BacktestConfig`에 `one_code` 필드 추가.

### H-3. 날짜 형식 검증 부재 (config.py:130-158)

**문제:** `validate()`에서 `start_date == 0`과 `start_date > end_date`만 검사. `--start 99999999` 또는 `--start 20251301` (13월) 같은 무효 날짜가 통과됨. DB 쿼리 시 빈 결과 또는 예외 발생.

**수정:**
```python
from datetime import datetime
def _valid_date(d):
    try:
        datetime.strptime(str(d), '%Y%m%d')
        return True
    except ValueError:
        return False
```

### H-4. Windows SIGBREAK 미처리 (runner.py:44-45)

**문제:** `signal.SIGTERM`은 Windows에서 직접 발생하지 않음. `taskkill` (without /F) 또는 Ctrl+Break 시 프로세스 정리가 되지 않음.

**수정:**
```python
if sys.platform == 'win32':
    signal.signal(signal.SIGBREAK, _signal_handler)
```

### H-5. 미사용 코드 (output.py:7-29, runner.py:7)

| 위치 | 내용 | 상태 |
|------|------|------|
| `output.py:7-29` | `BacktestResult` dataclass | 정의만 존재, 사용처 없음 (데드코드) |
| `runner.py:7` | `import numpy as np` | 미사용 import |

---

## 6. MEDIUM 결함 및 개선 사항

### M-1. _child_procs 글로벌 상태 오염 (runner.py:26)

모듈 레벨 리스트 `_child_procs`가 `run_backtest()` 호출 간 누적됨. 반복 호출 시 죽은 프로세스 참조가 쌓임.

**수정:** `run_backtest()` 시작부에 `_child_procs.clear()` 추가.

### M-2. signal 핸들러 import 부작용 (runner.py:44-45)

`import cli.runner`만으로 프로세스의 시그널 핸들러가 변경됨. 테스트 코드에서 의도치 않은 부작용.

**수정:** 시그널 등록을 `run_backtest()` 내부 또는 `if __name__ == '__main__'` 가드 내부로 이동.

### M-3. load_from_json() 취약한 키 처리 (config.py:119-127)

`BacktestConfig(**data)` 에서 JSON에 예상치 못한 키가 있으면 `TypeError`, 필수 키 누락 시 기본값으로 무시됨. `timeframe`과 `is_tick`이 동시에 있으면 로직이 불명확.

### M-4. avg_time 단일 값 vs GUI의 다중 값 (runner.py:200)

GUI는 `avg_list`가 쉼표 구분 다중 값 (`60,120,180`). CLI는 `[config.avg_time]` 단일 값만 지원. 다중 avg_time으로 연속 백테스트 시 엔진 재시작 필요.

### M-5. list_strategies() SQL 패턴 (config.py:167)

`f'SELECT index FROM {table}'` — 현재는 하드코딩 튜플이라 안전하지만 anti-pattern.

### M-6. 결과 수집 불완전 (runner.py:288-326)

`_extract_metrics()`에서 `day_count`, `bootstrap_avg/min/max`가 항상 0으로 반환됨. backtest.db에 이 값들이 저장되는지 확인 필요. `mdd_amount`도 0으0 고정.

---

## 7. CLI 기본 기능 점검

### 7.1 --help 출력 평가

현재 `parse_args`의 argparse 설정 기반 --help 예상 출력:

```
usage: stom_backtest [-h] [--list-strategies] [--config FILE] [--buy NAME]
                     [--sell NAME] [--start YYYYMMDD] [--end YYYYMMDD]
                     [--timeframe {tick,min}] [--betting BETTING]
                     [--avg-time AVG_TIME] [--start-time START_TIME]
                     [--end-time END_TIME] [--engines ENGINES] [--oms]
                     [--blacklist] [--back-club]
                     [--divid-mode {종목코드별 분류,일자별 분류,한종목 로딩}]
                     [--format {json,text}] [-o FILE]
```

**평가:**

| 항목 | 상태 | 비고 |
|------|------|------|
| 프로그램 설명 | OK | "STOM CLI Backtest Runner - 주식 백테스트를 커맨드라인에서 실행" |
| 필수 인자 표시 | 미흡 | `--buy`, `--sell`, `--start`, `--end`가 required=False지만 validate()에서 필수 |
| 기본값 표시 | OK | argparse default 표시됨 |
| 사용 예시 | 없음 | epilog에 예시가 없음 |
| 버전 표시 | 없음 | `--version` 미구현 |
| 누락 인자 | 있음 | `--one-code`, `--timeout`, `--verbose`, `--quiet` 없음 |

### 7.2 누락된 CLI 기본 기능

| 기능 | 중요도 | 상태 |
|------|--------|------|
| `--version` | 중간 | 없음 |
| `--verbose / --quiet` | 중간 | 없음 (verbose 항상 True) |
| `--timeout` | 높음 | 없음 (C-2와 연관) |
| `--one-code` | 높음 | 없음 (H-2와 연관) |
| `--dry-run` | 중간 | 없음 (설정 검증만 하고 실행하지 않는 모드) |
| 사용 예시 (epilog) | 낮음 | 없음 |
| `--profile` | 낮음 | 없음 (성능 프로파일링) |

---

## 8. GUI vs CLI 기능 갭 분석

### 8.1 GUI에 있고 CLI에 없는 기능

| GUI 기능 | CLI 상태 | 중요도 | 비고 |
|----------|----------|--------|------|
| 엔진 시작/종료 분리 | 통합됨 (run_backtest 내부) | - | 설계 차이 (허용) |
| 다중 avg_time 지원 | 단일 값만 | 중간 | M-4 |
| 한종목 로딩 모드 | 불능 | 높음 | H-2 |
| 스케줄 백테스트 | 없음 | 낮음 | schedul=True 모드 |
| 백클럽 모드 (상세 변수 출력) | 인자만 존재, 미검증 | 낮음 | |
| 진행률 표시 | stderr 로그만 | 중간 | GUI는 프로그레스바 |
| 취소 기능 (도중 중단) | Ctrl+C만 | 중간 | GUI는 버튼 |
| 차트 출력 | Total 프로세스에서 생성 (matplotlib agg) | 확인 필요 | schedul=False시 GUI 백엔드 사용 시도 가능 |
| 텔레그램 알림 | teleQ dummy | 낮음 | 별도 구현 필요 |
| 전략 편집 | 없음 | 중간 | 향후 수식관리자 CLI |
| 연속 백테스트 (엔진 재사용) | 없음 | 중간 | GUI는 엔진 유지 |
| 최적화/GA | 없음 | 향후 | Phase 3 이후 |
| DICT_SET 설정 연동 | 미동기화 | CRITICAL | C-1 |

### 8.2 matplotlib 백엔드 문제

**문제:** `Total.Report()` → `PlotShow()` (`back_static.py:440-642`)에서 matplotlib 차트를 생성합니다. GUI 환경에서는 기본 백엔드(Qt5Agg)가 사용되는데, CLI headless 환경에서는 `DISPLAY` 없이 실행 시 충돌 가능.

**확인 필요:** `schedul=True`일 때 `agg` 백엔드가 자동 선택되는지, 또는 CLI에서 명시적으로 `matplotlib.use('agg')`를 호출해야 하는지.

---

## 9. TDD 기반 개발 계획

### 9.1 테스트 전략

```
tests/
├── unit/                          # 단위 테스트
│   ├── test_config.py             # config.py 테스트
│   ├── test_output.py             # output.py 테스트
│   ├── test_queue_drain.py        # queue_drain.py 테스트
│   └── test_runner_helpers.py     # runner.py 헬퍼 함수 테스트
├── integration/                   # 통합 테스트
│   ├── test_engine_sequence.py    # 엔진 메시지 시퀀스 테스트
│   ├── test_backtest_e2e.py       # 실제 DB로 백테스트 1회 실행
│   └── test_cleanup.py            # 프로세스 정리 테스트
├── fixtures/                      # 테스트 데이터
│   ├── strategy_test.db           # 테스트용 strategy.db
│   ├── stock_tick_test.db         # 소규모 틱 데이터
│   └── sample_config.json         # 샘플 설정 파일
└── conftest.py                    # pytest fixtures
```

### 9.2 테스트 케이스 명세

#### test_config.py (단위)

```
TC-C01: parse_args(['--help']) → SystemExit(0)
TC-C02: parse_args(['--list-strategies']) → None 반환 + 목록 출력
TC-C03: parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131'])
        → BacktestConfig 정상 생성
TC-C04: parse_args(['--config', 'sample.json']) → JSON에서 로드
TC-C05: parse_args([]) → 필수 인자 없이 → BacktestConfig(기본값)
TC-C06: validate(config with empty buy) → ['매수 전략 미지정']
TC-C07: validate(config with start > end) → ['시작일자가 종료일자보다 큼']
TC-C08: validate(config with invalid date 20251301) → ['날짜 형식 오류']
TC-C09: validate(config with nonexistent strategy) → ['전략이 DB에 없음']
TC-C10: load_from_json(valid.json) → 정상 BacktestConfig
TC-C11: load_from_json(invalid.json) → 적절한 에러
TC-C12: list_strategies() with test DB → {'stockbuy': [...], 'stocksell': [...]}
TC-C13: list_strategies() with missing DB → {'stockbuy': [], 'stocksell': []}
```

#### test_output.py (단위)

```
TC-O01: format_result(error_result, 'json') → 유효한 JSON, status='error'
TC-O02: format_result(success_result, 'json') → 유효한 JSON, metrics 포함
TC-O03: format_result(success_result, 'text') → 포매팅된 텍스트
TC-O04: format_result(empty_metrics, 'json') → 기본값으로 채워진 JSON
TC-O05: format_result(success_result, 'text') → 한글 레이블 + 숫자 포매팅
```

#### test_queue_drain.py (단위)

```
TC-Q01: QueueDrainer(queue, verbose=True) → tuple 메시지 stderr 출력
TC-Q02: QueueDrainer(queue, verbose=False) → 메시지 무시, last_message 갱신
TC-Q03: QueueDrainer.stop() → 스레드 정상 종료
TC-Q04: QueueDrainer with None 메시지 → 루프 종료
TC-Q05: QueueDrainer with 문자열 메시지 → 정상 처리
TC-Q06: QueueDrainer with 빈 큐 → timeout 후 계속 대기
```

#### test_runner_helpers.py (단위)

```
TC-R01: _extract_metrics(config) with empty DB → None
TC-R02: _extract_metrics(config) with valid result → dict with 16 keys
TC-R03: _cleanup_procs() with dead processes → no error
TC-R04: _cleanup_procs() with live processes → all killed
TC-R05: _signal_handler → _cleanup_procs 호출 + sys.exit(1)
```

#### test_engine_sequence.py (통합)

```
TC-I01: BackSubTotal 프로세스 생성 + 종료 → 정상 라이프사이클
TC-I02: BackEngine 프로세스 생성 + '종목명' 메시지 → 정상 수신
TC-I03: 엔진 메시지 시퀀스 (종목명 → 데이터로딩 → 공유데이터 → 백테유형) → 정상
TC-I04: 큐 drain 후 프로세스 kill → 데드락 없음
TC-I05: DICT_SET 동기화 후 BackTest 프로세스 → 올바른 DB 선택
```

#### test_backtest_e2e.py (통합 / E2E)

```
TC-E01: run_backtest(valid_config) with test DB → status='success', metrics 존재
TC-E02: run_backtest(invalid_config) → status='error', 적절한 메시지
TC-E03: run_backtest(timeout_config) → 시간 초과 시 정상 종료
TC-E04: Ctrl+C during backtest → 모든 프로세스 정리
TC-E05: stom_backtest.py --list-strategies → 전략 목록 출력
TC-E06: stom_backtest.py --buy X --sell Y --start D1 --end D2 → JSON 결과
TC-E07: stom_backtest.py --format text → 텍스트 결과
TC-E08: stom_backtest.py -o result.json → 파일 저장
```

---

## 10. 단계별 실행 계획

### Phase 1: 안정화 (결함 수정 + 테스트 기반)

**목표:** 현재 코드의 CRITICAL/HIGH 결함 수정, 테스트 인프라 구축

**1.1 테스트 인프라 구축** (TDD 준비)
- [ ] `tests/conftest.py` 생성 (pytest fixtures: 임시 DB, 샘플 config)
- [ ] `tests/fixtures/` 에 테스트용 strategy.db, 소규모 tick DB 준비
- [ ] `requirements-dev.txt` 생성 (pytest, pytest-timeout 등)

**1.2 CRITICAL 결함 수정** (TDD: 테스트 먼저)
- [ ] TC-I05 작성 → C-1 수정 (DICT_SET 동기화)
- [ ] TC-E03 작성 → C-2 수정 (join timeout)
- [ ] TC-I04 작성 → C-3 수정 (큐 drain 후 cleanup)

**1.3 HIGH 결함 수정** (TDD)
- [ ] TC-R01~R02 작성 → H-1 수정 (DB 연결 try/finally)
- [ ] TC-C08 작성 → H-3 수정 (날짜 검증)
- [ ] H-2 수정: `--one-code` 인자 추가 + TC-C03 확장
- [ ] H-4 수정: SIGBREAK 핸들러 + Windows 테스트
- [ ] H-5 수정: 데드코드 제거

**1.4 단위 테스트 완성**
- [ ] TC-C01~C13 전체 작성 (config.py 100% 커버리지)
- [ ] TC-O01~O05 전체 작성 (output.py 100% 커버리지)
- [ ] TC-Q01~Q06 전체 작성 (queue_drain.py 100% 커버리지)
- [ ] TC-R01~R05 전체 작성 (runner.py 헬퍼)

**산출물:**
- 결함 수정된 cli/ 모듈
- `tests/unit/` 4개 파일 (약 400줄)
- `tests/conftest.py`
- `tests/fixtures/`

### Phase 2: 실행 검증 (E2E 테스트)

**목표:** 실제 DB로 백테스트 1회 성공 증명

**2.1 사전 조건 확인**
- [ ] stock_tick_back.db 또는 stock_min_back.db 데이터 존재 확인
- [ ] strategy.db에 유효한 매수/매도 전략 존재 확인
- [ ] matplotlib agg 백엔드 동작 확인 (headless 차트 생성)

**2.2 DICT_SET 전수 조사**
- [ ] BackTest.Start() 내부에서 사용하는 모든 DICT_SET 키 목록화
- [ ] BackEngineBase 및 하위 클래스에서 사용하는 DICT_SET 키 목록화
- [ ] Total.Report() 에서 사용하는 DICT_SET 키 목록화
- [ ] CLI에서 동기화해야 할 키 완전 목록 작성 + 코드 반영

**2.3 E2E 테스트 실행**
- [ ] TC-E05: `--list-strategies` 실행 성공
- [ ] TC-E01: 소규모 데이터로 tick 백테스트 1회 성공
- [ ] TC-E01b: 소규모 데이터로 min 백테스트 1회 성공
- [ ] TC-E06: JSON 결과 출력 정상 확인
- [ ] TC-E07: 텍스트 결과 출력 정상 확인
- [ ] TC-E08: 파일 저장 정상 확인
- [ ] TC-E04: Ctrl+C 프로세스 정리 확인

**2.4 결과 정합성 검증**
- [ ] 동일 전략/기간으로 GUI 백테스트 실행 → 결과 기록
- [ ] 동일 전략/기간으로 CLI 백테스트 실행 → 결과 기록
- [ ] GUI vs CLI 결과 비교 (거래횟수, 승률, 수익률 일치 여부)

**산출물:**
- `tests/integration/` 4개 파일 (약 300줄)
- DICT_SET 동기화 완전 목록
- GUI vs CLI 결과 비교 보고서

### Phase 3: CLI 기본 기능 보강

**목표:** 프로덕션 수준 CLI UX 달성

**3.1 누락 인자 추가**
- [ ] `--version` 추가
- [ ] `--timeout` 추가 (C-2 연동)
- [ ] `--one-code` 추가 (H-2 연동)
- [ ] `--verbose / --quiet` 추가
- [ ] `--dry-run` 추가 (설정 검증만)

**3.2 --help 개선**
- [ ] 필수 인자 그룹 분리 (`required` 인자 그룹)
- [ ] epilog에 사용 예시 추가
- [ ] 한글 설명 보강

**3.3 에러 메시지 개선**
- [ ] 모든 에러 경로에서 구체적 메시지 출력
- [ ] 비정상 종료 시 exit code 구분 (1=인자 오류, 2=실행 오류, 3=시간 초과)

**3.4 MEDIUM 결함 수정**
- [ ] M-1: _child_procs.clear()
- [ ] M-2: signal 등록 위치 이동
- [ ] M-3: load_from_json 키 검증
- [ ] M-4: avg_time 다중 값 지원 (`--avg-time 60,120,180`)
- [ ] M-6: 결과 수집 완전성 (day_count, bootstrap 값)

**산출물:**
- 보강된 CLI (--version, --timeout, --one-code, --verbose, --dry-run)
- 개선된 --help 출력
- 완전한 에러 처리

### Phase 4: 기능 확장

**목표:** 수식관리자 CLI, 전략 평가, 연속 실행

**4.1 수식관리자 CLI**
- [ ] `stom formula list` — DB에서 수식 목록 조회
- [ ] `stom formula add <name> --code <file>` — 파일 기반 수식 등록
- [ ] `stom formula test <code>` — 구문 검증
- [ ] `stom formula delete <name>` — 삭제
- [ ] `stom formula export/import` — JSON 직렬화

**4.2 전략 DSL headless 평가**
- [ ] `trade/strategy_base.py:Strategy` 클래스 CLI 인스턴스화
- [ ] `stom strategy evaluate` 명령으로 headless 전략 실행
- [ ] V2.51 문법 변경 자동 감지 (`고가미갱신지속틱수()` 등)

**4.3 연속 백테스트**
- [ ] 엔진 프로세스 유지 + 반복 백테스트 (GUI 패턴)
- [ ] 전략 파라미터 스윕 (`--sweep` 모드)
- [ ] 결과 비교 테이블 출력

**산출물:**
- `cli/formula.py` — 수식관리자 CLI
- `cli/strategy.py` — 전략 평가 CLI
- `cli/sweep.py` — 파라미터 스윕

---

## 11. 리스크 및 대응

| 리스크 | 심각도 | 대응 |
|--------|--------|------|
| DICT_SET 키 누락으로 엔진 오동작 | 높음 | Phase 2.2 전수 조사 필수 |
| 테스트 데이터 부재 | 중간 | 소규모 fixture DB 생성 또는 기존 DB에서 추출 |
| Windows 멀티프로세싱 특이성 | 중간 | spawn 방식 기본값 확인, freeze_support() 필요 여부 |
| matplotlib headless 충돌 | 중간 | `matplotlib.use('agg')` 조기 호출 |
| 전략 exec() 보안 | 중간 | Phase 4 이후 safe_exec 복원 검토 |
| 대규모 데이터 메모리 부족 | 낮음 | SharedMemory vs pickle 모드 CLI 지원 검토 |

---

## 12. 우선순위 요약

```
즉시 (Phase 1) — 결함 수정 + 테스트 기반 구축
├── C-1 DICT_SET 동기화 (CRITICAL)
├── C-2 join timeout (CRITICAL)
├── C-3 큐 drain + cleanup (CRITICAL)
├── H-1~H-5 수정
└── 단위 테스트 100% 커버리지

단기 (Phase 2) — 실행 검증
├── DICT_SET 전수 조사
├── E2E 백테스트 1회 성공
└── GUI vs CLI 결과 정합성 확인

중기 (Phase 3) — CLI UX 완성
├── --version, --timeout, --one-code, --verbose, --dry-run
├── --help 개선
└── MEDIUM 결함 전체 수정

장기 (Phase 4) — 기능 확장
├── 수식관리자 CLI
├── 전략 DSL 평가
└── 연속 백테스트/스윕
```

---

## 부록 A: 참조 파일 목록

| 파일 | 라인 | 설명 |
|------|------|------|
| `cli/config.py:1-173` | 전체 | 인자 파싱, 검증, 전략 목록 |
| `cli/runner.py:1-326` | 전체 | 핵심 백테스트 오케스트레이터 |
| `cli/output.py:1-109` | 전체 | 결과 포매팅 |
| `cli/queue_drain.py:1-41` | 전체 | windowQ 소비자 |
| `stom_backtest.py:1-37` | 전체 | CLI 진입점 |
| `ui/ui_backtest_engine.py:77-266` | backengine_start() | 엔진 초기화 (GUI) |
| `ui/ui_button_clicked_editer_stock.py:630-688` | stock_backtest_start() | 백테스트 시작 (GUI) |
| `backtest/backtest.py:247-377` | BackTest 클래스 | 백테스트 오케스트레이터 |
| `backtest/backtest.py:16-244` | Total 클래스 | 최종 집계 + 리포트 |
| `backtest/backengine_base.py:19-718` | BackEngineBase | 엔진 기반 클래스 |
| `backtest/backengine_kiwoom_tick.py:7-143` | Strategy() | 틱 전략 실행 |
| `backtest/back_subtotal.py:1-217` | BackSubTotal | 중간 집계 |
| `backtest/back_static.py:88-178` | GetMoneytopQuery, GetBuyStg, GetSellStg | SQL + 전략 컴파일 |
| `backtest/back_static.py:440-741` | PlotShow, GetResult, bootstrap_test | 차트 + 통계 |
| `trade/strategy_base.py:14-1125` | Strategy 클래스 | DSL 통합 기반 |
| `utility/setting.py:15-33` | DICT_SET, DB 경로 상수 | 전역 설정 |

## 부록 B: DICT_SET 동기화 필요 키 (조사 예정)

| 키 | 사용 파일 | 용도 | CLI 대응 |
|----|-----------|------|----------|
| `주식타임프레임` | backtest.py:290 | DB 선택 | config.is_tick |
| `백테매수시간기준` | runner.py:81 | BackSubTotal 인자 | 직접 전달 중 |
| `backtest_oms_apply` | ui_backtest_engine.py:108 | 엔진 선택 | config.oms |
| `증권사` | 다수 | gubun 결정 | 'S' 하드코딩 |
| `blacklist_add` | 다수 | 블랙리스트 | config.blacklist |
| `백테일괄로딩` | backengine_base.py:308 | SharedMemory 여부 | 조사 필요 |
| *(추가 조사 필요)* | | | |
