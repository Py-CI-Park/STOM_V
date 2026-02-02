# STOM CLI 인터페이스 개발 검토 보고서

**작성일**: 2026-02-01
**브랜치**: `STOM_Version_2U-cli-research`
**버전**: V2.36.U1.5.C1.0
**파생 기준**: V2.36.U1.5 (커밋: 8fc917c)

---

## 버전 정보

| 항목 | 값 |
|------|-----|
| 기반 버전 | V2.36.U1.5 |
| 커스텀 버전 | C1.0 |
| 버전 형식 | `V{major}.{minor}.U{patch}.C{custom}.{update}` |

### 버전 명명 규칙
- **U (Update)**: 메인 라인 업데이트 (ui_mainwindow.pyd → .py 마이그레이션 등)
- **C (Custom)**: 커스텀 기능 개발 브랜치 (CLI 인터페이스 등)
- 이 방식으로 U 버전 이력과 C 버전 이력을 동시에 추적 가능

---

## 1. 프로젝트 현황 분석

### 1.1 개요

STOM(System Trading Operation Manager)은 PyQt5 기반의 GUI 프로그램으로, 주식/코인/선물 자동매매 및 백테스팅 기능을 제공합니다.

### 1.2 현재 아키텍처

```
stom.py (Entry Point)
    └── QApplication + MainWindow
            ├── ui/ui_mainwindow.py (메인 컨트롤러)
            ├── stock/ (주식 트레이딩)
            ├── coin/ (암호화폐 트레이딩)
            ├── future/ (선물 트레이딩)
            ├── backtester/ (백테스팅 엔진)
            └── utility/ (유틸리티)
```

### 1.3 핵심 통계

| 항목 | 수치 |
|------|------|
| 총 Python 파일 | ~120개 |
| PyQt5 의존 파일 | 36개 |
| GUI 독립 파일 | ~84개 |
| SQLite 데이터베이스 | 13개 |
| 백테스트 엔진 | 16개 |

---

## 2. GUI 의존성 분석

### 2.1 PyQt5 사용 모듈 (36개)

#### 핵심 GUI 모듈
| 파일 | 역할 | Qt 의존도 |
|------|------|----------|
| `stom.py` | 앱 진입점, QApplication 생성 | **필수** |
| `ui/ui_mainwindow.py` | 메인 윈도우 컨트롤러 | **필수** |
| `ui/ui_*.py` (50+) | UI 다이얼로그, 테이블, 차트 | **필수** |

#### 트레이더 모듈
| 파일 | Qt 사용 요소 | 대체 가능성 |
|------|-------------|------------|
| `stock/kiwoom_trader.py` | QThread, QApplication | threading.Thread |
| `stock/kiwoom_manager.py` | QTimer, QThread | threading.Timer |
| `coin/upbit_trader.py` | QThread, QApplication | threading.Thread |
| `coin/binance_trader.py` | QThread, QApplication | threading.Thread |
| `future/future_trader.py` | QThread, QApplication | threading.Thread |

#### 유틸리티 모듈
| 파일 | Qt 사용 요소 | 대체 가능성 |
|------|-------------|------------|
| `utility/static.py` | QTest.qWait() (Line 12) | time.sleep() |

### 2.2 Qt 의존성 상세

```python
# utility/static.py - Line 12
from PyQt5.QtTest import QTest

# 사용처: qtest_qwait() 함수
def qtest_qwait(ms):
    QTest.qWait(ms)  # → time.sleep(ms/1000) 으로 대체 가능
```

---

## 3. CLI 구현 가능성 평가

### 3.1 기능별 CLI 가능성

| 기능 | 현재 구현 | CLI 가능성 | 비고 |
|------|----------|-----------|------|
| **백테스트 실행** | multiprocessing.Queue | ✅ **80%** | 핵심 로직 분리 가능 |
| **그리드 최적화** | Queue 기반 | ✅ **80%** | 동일 구조 |
| **Optuna 최적화** | Queue 기반 | ✅ **80%** | 동일 구조 |
| **GA 최적화** | Queue 기반 | ✅ **75%** | 약간의 리팩토링 필요 |
| **전략 관리** | SQLite DB | ✅ **95%** | 완전 독립 |
| **설정 관리** | SQLite + DICT_SET | ✅ **90%** | PyQt 없이 로드 가능 |
| **데이터 조회** | SQLite | ✅ **95%** | 완전 독립 |
| **실시간 트레이딩** | QApplication 필수 | ❌ **불가** | 이벤트 루프 필요 |
| **실시간 차트** | matplotlib + Qt | ❌ **불가** | GUI 필수 |
| **WebSocket 수신** | QThread 기반 | ⚠️ **30%** | 대규모 리팩토링 필요 |

### 3.2 모듈별 독립도 분석

#### GUI 독립적 모듈 (CLI 즉시 사용 가능)

```
utility/
├── setting.py          ✅ 95% - 설정 로드 (PyQt 없이 동작)
├── query.py            ✅ 100% - DB 쿼리
├── hoga.py             ✅ 100% - 호가 유틸리티
├── telegram_msg.py     ✅ 100% - 텔레그램 메시지
└── telegram_bot.py     ✅ 95% - 텔레그램 봇

backtester/
├── backtest.py         ✅ 90% - 백테스트 메인 (Queue 기반)
├── optimiz.py          ✅ 85% - 최적화 엔진
├── optimiz_conditions.py ✅ 85% - 조건 최적화
├── optimiz_genetic_algorithm.py ✅ 80% - GA 최적화
├── backfinder.py       ✅ 90% - 전략 찾기
├── back_static.py      ✅ 95% - 정적 유틸리티
└── backengine_*.py (16개) ✅ 85% - 백테스트 엔진들
```

#### GUI 의존적 모듈 (리팩토링 필요)

```
stock/
├── kiwoom_trader.py    ❌ QThread, QApplication 필수
├── kiwoom_manager.py   ❌ QTimer, QThread 필수
└── kiwoom_agent_*.py   ⚠️ 부분 의존

coin/
├── upbit_trader.py     ❌ QThread 필수
├── binance_trader.py   ❌ QThread 필수
└── *_websocket.py      ❌ QThread 기반

future/
├── future_trader.py    ❌ QThread 필수
└── future_manager.py   ❌ QTimer 필수
```

---

## 4. Queue 통신 패턴 분석

### 4.1 현재 Queue 구조

```python
# ui/ui_mainwindow.py 에서 정의된 Queue들
windowQ      # GUI 업데이트 메시지
soundQ       # 사운드 알림
queryQ       # DB 쿼리 요청
teleQ        # 텔레그램 메시지
chartQ       # 차트 데이터
hogaQ        # 호가 데이터
webcQ        # 웹소켓 통신
backQ        # 백테스트 통신
creceivQ     # 코인 수신
ctraderQ     # 코인 트레이더
cstgQ        # 코인 전략
liveQ        # 실시간 데이터
totalQ       # 전체 집계
```

### 4.2 백테스트 Queue 흐름

```
[UI] → backQ → [BacktestManager]
                    ↓
              [BackEngine Processes] (16개)
                    ↓
              totalQ → [Total Aggregator]
                    ↓
              windowQ → [UI Update]
```

### 4.3 CLI 어댑터 전략

```python
# CLI에서는 windowQ, soundQ를 로깅으로 대체
class CLIQueueAdapter:
    def __init__(self):
        self.windowQ = queue.Queue()  # → logging.info()
        self.soundQ = queue.Queue()   # → 무시 또는 beep
        self.backQ = queue.Queue()    # → 그대로 사용
        self.totalQ = queue.Queue()   # → 그대로 사용
```

---

## 5. 구현 방안

### 5.1 CLI 디렉토리 구조

```
cli/
├── __init__.py
├── main.py                      # CLI 진입점 (argparse/click)
├── adapters/
│   ├── __init__.py
│   ├── queue_adapter.py         # Queue → 로깅 변환
│   ├── settings_adapter.py      # PyQt 없이 설정 로드
│   └── output_adapter.py        # 결과 출력 (JSON/CSV)
├── commands/
│   ├── __init__.py
│   ├── backtest.py              # stom backtest run/list/result
│   ├── optimize.py              # stom optimize grid/optuna/ga
│   ├── strategy.py              # stom strategy list/show/export
│   └── data.py                  # stom data query/export
└── runners/
    ├── __init__.py
    ├── backtest_runner.py       # 헤드리스 백테스트 실행
    └── optimize_runner.py       # 헤드리스 최적화 실행
```

### 5.2 CLI 명령어 설계

```bash
# 백테스트
stom backtest run --strategy "전략명" --start 20250101 --end 20251231
stom backtest list
stom backtest result --id 123 --format json

# 최적화
stom optimize grid --strategy "전략명" --params "param1:1-10,param2:0.1-1.0"
stom optimize optuna --strategy "전략명" --trials 100
stom optimize ga --strategy "전략명" --generations 50

# 전략 관리
stom strategy list
stom strategy show "전략명"
stom strategy export "전략명" --format json

# 데이터 조회
stom data query --table stock_tick --code 005930 --date 20250101
stom data export --db backtest --query "SELECT * FROM results"
```

### 5.3 핵심 구현 코드 (예시)

#### settings_adapter.py
```python
"""PyQt5 없이 STOM 설정 로드"""
import sqlite3
import pandas as pd

def load_settings_without_qt():
    """utility/setting.py의 database_load()를 Qt 없이 실행"""
    from utility.setting import DB_SETTING

    con = sqlite3.connect(DB_SETTING)
    df_main = pd.read_sql('SELECT * FROM main', con).set_index('index')
    # ... 나머지 테이블 로드
    con.close()

    return build_dict_set(df_main, ...)
```

#### backtest_runner.py
```python
"""헤드리스 백테스트 실행기"""
from multiprocessing import Process, Queue
from backtester.backtest import Total
from cli.adapters.queue_adapter import CLIQueueAdapter

class HeadlessBacktestRunner:
    def __init__(self):
        self.adapter = CLIQueueAdapter()

    def run(self, strategy_name, start_date, end_date):
        # Queue 설정
        wq = self.adapter.create_window_queue()  # 로깅으로 리다이렉트
        sq = self.adapter.create_sound_queue()   # 무시
        tq = Queue()
        backQ = Queue()

        # 백테스트 프로세스 시작
        process = Process(target=run_backtest, args=(wq, sq, tq, ...))
        process.start()

        # 결과 수집
        return self.collect_results(tq)
```

---

## 6. 예상 작업량

### 6.1 컴포넌트별 예상

| 컴포넌트 | 예상 코드량 | 복잡도 | 예상 시간 |
|----------|------------|--------|----------|
| Queue Adapter | ~200줄 | 중간 | 0.5일 |
| Settings Adapter | ~100줄 | 낮음 | 0.25일 |
| Backtest Runner | ~500줄 | 높음 | 1.5일 |
| Optimize Runner | ~600줄 | 높음 | 2일 |
| CLI Commands | ~400줄 | 중간 | 1일 |
| Output Formatters | ~200줄 | 낮음 | 0.5일 |
| **총합** | **~2000줄** | - | **~6일** |

### 6.2 구현 우선순위

#### 1주차: 필수 기능
- [x] CLI 프로젝트 구조 설정
- [ ] Settings Adapter (PyQt 없이 설정 로드)
- [ ] 전략 목록/조회 명령
- [ ] 기본 백테스트 실행

#### 2주차: 핵심 기능
- [ ] 백테스트 결과 포맷터 (JSON/CSV)
- [ ] 그리드 최적화 실행
- [ ] 거래 데이터 조회

#### 3주차: 고급 기능
- [ ] Optuna 최적화
- [ ] GA 최적화
- [ ] 배치 실행 모드

---

## 7. 제약 사항

### 7.1 CLI로 구현 불가능한 기능

| 기능 | 이유 | 대안 |
|------|------|------|
| **실시간 트레이딩** | PyQt5 이벤트 루프가 키움/거래소 API와 통합됨 | 별도 헤드리스 트레이더 개발 필요 |
| **실시간 차트** | matplotlib + Qt 통합 | 정적 차트 이미지 생성 가능 |
| **WebSocket 수신** | QThread 기반 구현 | asyncio로 재구현 필요 |
| **호가창 표시** | 실시간 스트리밍 데이터 | 스냅샷 조회만 가능 |

### 7.2 기술적 제약

1. **SharedMemory 관리**
   - 백테스트 엔진이 SharedMemory 사용
   - CLI에서도 동일하게 관리 필요

2. **SQLite 동시 접근**
   - 다중 프로세스에서 동시 쓰기 제한
   - WAL 모드 또는 Queue 기반 쓰기 필요

3. **Windows 레지스트리**
   - 암호화 키가 레지스트리에 저장됨
   - `utility/static.py`의 `read_key()` 함수 사용

4. **프로세스 간 통신**
   - 기존 Queue 기반 통신 유지 필요
   - GUI 메시지만 로깅으로 변환

---

## 8. AI Agent 연동 시나리오

### 8.1 Claude Code 통합 예시

```python
# AI Agent가 CLI를 통해 STOM 제어
import subprocess
import json

# 전략 목록 조회
result = subprocess.run(
    ['python', '-m', 'cli.main', 'strategy', 'list', '--format', 'json'],
    capture_output=True, text=True
)
strategies = json.loads(result.stdout)

# 백테스트 실행
result = subprocess.run([
    'python', '-m', 'cli.main', 'backtest', 'run',
    '--strategy', '골든크로스전략',
    '--start', '20250101',
    '--end', '20251231',
    '--format', 'json'
], capture_output=True, text=True)
backtest_result = json.loads(result.stdout)

# 결과 분석
if backtest_result['total_return'] > 0:
    print(f"수익률: {backtest_result['total_return']:.2%}")
```

### 8.2 MCP (Model Context Protocol) 통합

```python
# MCP 서버로 STOM CLI 래핑
class STOMCLIServer:
    @mcp_tool("stom_backtest")
    def run_backtest(self, strategy: str, start: str, end: str):
        """백테스트 실행"""
        return execute_cli(['backtest', 'run', ...])

    @mcp_tool("stom_optimize")
    def run_optimization(self, strategy: str, method: str):
        """최적화 실행"""
        return execute_cli(['optimize', method, ...])
```

---

## 9. 결론 및 권장사항

### 9.1 결론

STOM CLI 인터페이스 개발은 **기술적으로 가능**하며, 특히 **백테스팅 및 최적화 기능**에 대해서는 높은 수준의 CLI 지원이 가능합니다.

| 영역 | 평가 | 권장 |
|------|------|------|
| 백테스트 | ✅ 가능 (80%) | **1순위 구현** |
| 최적화 | ✅ 가능 (80%) | **1순위 구현** |
| 전략 관리 | ✅ 가능 (95%) | **1순위 구현** |
| 데이터 조회 | ✅ 가능 (95%) | **1순위 구현** |
| 실시간 트레이딩 | ❌ 불가 | 별도 프로젝트 |

### 9.2 권장 접근 방식

1. **Phase 1: 읽기 전용 CLI** (1주)
   - 전략 목록/조회
   - 백테스트 결과 조회
   - 데이터 내보내기

2. **Phase 2: 백테스트 실행** (2주)
   - 헤드리스 백테스트 러너
   - Queue 어댑터 구현
   - 결과 포맷터

3. **Phase 3: 최적화 지원** (2주)
   - 그리드/Optuna/GA 최적화
   - 배치 실행 모드

4. **Phase 4: AI 통합** (1주)
   - MCP 서버 래핑
   - JSON API 정규화

### 9.3 다음 단계

1. 이 보고서를 기반으로 CLI 프로젝트 디렉토리 생성
2. `utility/static.py`에서 `QTest.qWait()` 의존성 제거 버전 작성
3. `settings_adapter.py` 구현으로 PyQt 없이 설정 로드
4. 간단한 `stom strategy list` 명령부터 시작

---

## 부록

### A. 관련 파일 목록

#### PyQt5 의존 파일 (36개)
```
stom.py
ui/ui_mainwindow.py
ui/ui_*.py (50+ files)
stock/kiwoom_trader.py
stock/kiwoom_manager.py
coin/upbit_trader.py
coin/binance_trader.py
future/future_trader.py
utility/static.py (QTest만 사용)
backtester/back_code_test.py
```

#### Queue 사용 파일 (11개)
```
ui/ui_mainwindow.py
ui/ui_backtest_engine.py
stock/kiwoom_manager.py
future/future_manager.py
backtester/backtest.py
backtester/optimiz.py
backtester/optimiz_conditions.py
backtester/optimiz_genetic_algorithm.py
backtester/rolling_walk_forward_test.py
utility/telegram_bot.py
stock/kiwoom_rest.py
```

### B. 데이터베이스 스키마

```
_database/
├── setting.db          # 시스템 설정
├── strategy.db         # 전략 정의
├── backtest.db         # 백테스트 결과
├── tradelist.db        # 거래 내역
├── optuna.db           # Optuna 최적화 결과
├── stock_tick.db       # 주식 틱 데이터
├── stock_min.db        # 주식 분봉 데이터
├── coin_tick.db        # 코인 틱 데이터
├── coin_min.db         # 코인 분봉 데이터
├── future_tick.db      # 선물 틱 데이터
├── future_min.db       # 선물 분봉 데이터
└── code_info.db        # 종목 정보
```

---

**작성**: Claude Code (AI Assistant)
**검토**: 2026-02-01
**상태**: 초안 (Draft)
