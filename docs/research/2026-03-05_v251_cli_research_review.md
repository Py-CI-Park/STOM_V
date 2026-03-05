# STOM V2.51 기준 CLI 리서치 재검토 보고서

- 작성일: 2026-03-05
- 기준 브랜치: `STOM_Version_2U-cli-research-v251`
- 기준 커밋: `220cadc` (STOM V2.51.U1.5)
- 참조 보고서:
  - `2026-03-02_v250_cli_research_review_plan.md` (CLI-R1, V2.50 기준)
  - `2026-03-02_v250_stock_backtest_cli_first_plan.md` (CLI-R2, V2.50 기준)
- 목적: V2.50→V2.51 변경사항이 CLI 리서치 계획에 미치는 영향 분석 및 V2.51 기준 재평가

---

## 1) 결론 요약

V2.51의 변경사항은 CLI 구현 계획에 **긍정적 영향과 부정적 영향을 동시에** 미칩니다.

**긍정적 변화:**
- `trade/strategy_base.py` 도입으로 전략 DSL이 단일 클래스로 통합 → CLI에서 headless 전략 평가가 구조적으로 가능해짐
- 수식관리자(Formula Manager) 도입으로 DB 기반 수식 CRUD가 추가 → CLI 명령 확장 포인트 확보
- 디렉토리 구조 정리로 모듈 책임이 명확해짐

**부정적 변화:**
- `backengine_base.py`가 `research/auxiliary_indicator/smart_vwap_bands.py`를 직접 import → PyQt5/pyqtgraph 전이 의존성 **신규 발생**
- V2.50 CLI-R1에서 식별한 4개 호환성 갭이 **전부 미해결 상태**

**핵심 판단:** CLI 우선 구현은 여전히 가능하나, V2.50 대비 **PyQt5 전이 의존성 분리가 추가 선행 과제**로 등장했습니다.

---

## 2) V2.50→V2.51 변경사항과 CLI 영향

### 2.1 디렉토리 구조 변경

| V2.50 경로 | V2.51 경로 | CLI-R2 보고서 영향 |
|-----------|-----------|------------------|
| `backtester/` | `backtest/` | 모든 import 경로 변경, 보고서 참조 경로 갱신 필요 |
| `stock/` | `trade/stock_korea/` | 매니저 subprocess 경로 변경 |
| `coin/` | `trade/binance/`, `trade/upbit/` | 코인 관련 CLI 확장 시 경로 주의 |
| `future/` | `trade/future_oversea/` | 해외선물 CLI 확장 시 경로 주의 |
| `strategy/` | `research/auxiliary_indicator/` | 보조지표 모듈 경로 변경 |
| `deeplearning/` | `research/deeplearning/` | 딥러닝 CLI 확장 시 경로 주의 |

### 2.2 CLI-R2 코드 경로 참조 업데이트

| 항목 | V2.50 보고서 참조 | V2.51 실제 위치 | 라인 변화 |
|------|-----------------|----------------|----------|
| `class BackTest` | `backtester/backtest.py:246` | `backtest/backtest.py:247` | +1 |
| `Start()` | `backtester/backtest.py:268` | `backtest/backtest.py:269` | +1 |
| Result DB save | `backtester/backtest.py:194-201` | `backtest/backtest.py:195-202` | +1 |
| `GetMoneytopQuery` 호출 | `ui/ui_backtest_engine.py:168` | `ui/ui_backtest_engine.py:168` | 변화없음 |
| `stock_backtest_start` | `ui/ui_button_clicked_editer_stock.py:630` | 동일:630 | 변화없음 |
| BackTest 프로세스 시작 | `ui/ui_button_clicked_editer_stock.py:676-685` | 동일:676-685 | 변화없음 |

### 2.3 GetMoneytopQuery 시그니처

**변화없음.** V2.51에서도 동일한 6인자 시그니처 유지:
```python
# backtest/back_static.py:88
def GetMoneytopQuery(is_tick, gubun, startday, endday, starttime, endtime):
```

### 2.4 backQ 13-튜플 형식

**변화없음.** 생산자(`ui_button_clicked_editer_stock.py:676-679`)와 소비자(`backtest/backtest.py:271-287`) 모두 동일한 13개 요소 유지:
```
(betting, avgtime, startday, endday, starttime, endtime,
 buystg, sellstg, dict_cn, back_count, bl, schedul, back_club)
```

---

## 3) V2.51 신규 기능의 CLI 영향

### 3.1 `trade/strategy_base.py` — 전략 DSL 통합 클래스 (★ 핵심 변화)

V2.51의 가장 중요한 구조적 변화입니다.

**무엇인가:**
- 1125줄의 `Strategy` 클래스로, 이전에 각 엔진/전략 파일에 중복되어 있던 ~120개 시장 분석 함수를 단일 소스로 통합
- 모든 백테스트 엔진과 실시간 전략 프로세스의 **최상위 부모 클래스**

**상속 구조:**
```
Strategy (trade/strategy_base.py)
├── BackEngineBase (backtest/backengine_base.py:19)
│   ├── BackEngineKiwoomTick → BackEngineKiwoomMin
│   ├── BackEngineFutureTick → BackEngineFutureMin → BackEngineBinanceMin
│   ├── BackEngineUpbitTick → BackEngineUpbitMin
│   └── BackEngineBaseOms → *Tick2 → *Min2 엔진들
├── KiwoomStrategy* (trade/stock_korea/)
├── BinanceStrategy* (trade/binance/)
├── UpbitStrategy* (trade/upbit/)
├── FutureStrategy* (trade/future_oversea/)
└── FormulaManager (utility/chart.py:389)
```

**Strategy 클래스 제공 기능:**

| 영역 | 라인 범위 | 함수 수 | 설명 |
|------|----------|---------|------|
| 원시 데이터 접근자 | 59-215 | ~40 | `_현재가N()`, `_시가N()` 등 |
| 집계/윈도우 함수 | 227-345 | ~30 | `_이동평균()`, `_최고현재가()` 등 |
| 파생 지표 | 350-500 | ~25 | `_변동성()`, `_거래대금평균대비비율()` 등 |
| 전략 신호 | 491-698 | ~40 | `_가격급등`, `_이평지지후이평돌파` 등 |
| TA-Lib 래퍼 | 700-922 | ~25 | `_RSI_N()`, `_MACD_N()`, `_BBANDS_N()` 등 |
| 함수 레지스트리 | 924-1125 | 1 | `SetGlobalsFunc()` — 한글 이름 → 메서드 매핑 |

**CLI에 미치는 영향:**
- Strategy 클래스를 headless로 인스턴스화하면, GUI 없이도 전략 코드를 평가할 수 있음
- `FormulaManager(Strategy)`가 이미 `utility/chart.py:389`에서 이 패턴을 증명
- CLI에서 `strategy evaluate` 명령 구현의 기반이 됨

### 3.2 수식관리자 (Formula Manager) — CLI 확장 포인트

**DB 스키마** (`strategy.db:formula` 테이블):
```
(수식명, 체크유무, 팩터명, 표시형태, 색상, 크기, 라인타입, 수식코드)
```

**CRUD 경로:**
- 불러오기: `SELECT * FROM formula` (`ui/ui_etc.py:214`)
- 저장: `DELETE + INSERT` with `FormulaCodeTest` 검증 (`ui/ui_etc.py:248-253`)
- 삭제: `DELETE FROM formula WHERE 수식명 = '{name}'` (`ui/ui_etc.py:263`)

**표시 유형:**
- `선:일반`, `선:조건`, `화살표:일반`, `화살표:매매`, `범위`

**CLI 확장 가능 명령:**

| 명령 | 난이도 | 영향 | 설명 |
|------|--------|------|------|
| `stom formula list` | 낮음 | 높음 | DB에서 수식 목록 조회 |
| `stom formula add <name> --code <file>` | 중간 | 높음 | 파일 기반 수식 일괄 등록 |
| `stom formula test <code>` | 낮음 | 중간 | `BackCodeTest`로 수식 구문 검증 |
| `stom formula export/import` | 중간 | 높음 | JSON/YAML 직렬화 |
| `stom formula run <name> --ticker <code>` | 높음 | 매우 높음 | headless 수식 실행 + 신호 출력 |

### 3.3 `고가미갱신지속틱수` / `저가미갱신지속틱수` 호출 방법 변경 (Breaking Change)

```python
# V2.50: 변수처럼 호출 (괄호 없음)
self.line = 고가미갱신지속틱수

# V2.51: 함수로 호출 (괄호 필수)
self.line = 고가미갱신지속틱수()
```

**CLI 영향:** 기존 사용자 전략 코드가 V2.51에서 동작하려면 이 변경 반영 필요. CLI `strategy validate` 명령에 이 호환성 검사 추가 권장.

### 3.4 `_fi` 함수 삭제

`_fi` 함수는 로컬 클로저(함수 내부 정의)로, MainWindow나 외부 인터페이스에 영향 없음. CLI에도 **영향 없음**.

---

## 4) V2.50 CLI-R1 호환성 갭 재평가

### 갭 상태 요약

| # | 갭 항목 | V2.50 상태 | V2.51 상태 | 변화 |
|---|--------|-----------|-----------|------|
| 1 | GetMoneytopQuery `is_tick` 첫 번째 인자 | 치명 | **미해결** | 동일 |
| 2 | `utility/static.py` 강제 import (psutil/talib/QTest/winreg) | 치명 | **미해결** | 동일 |
| 3 | `utility/safe_exec.py` 부재 | 경미 | **미해결** | 동일 |
| 4 | `requirements-cli.txt` 부재 | 중간 | **미해결** | 동일 |
| 5 | 백테스트 엔진 PyQt5 전이 의존성 | N/A | **신규 (악화)** | ⚠️ NEW |

### 갭 5 상세: PyQt5 전이 의존성 (V2.51 신규)

**문제의 import 체인:**
```
backtest/backengine_base.py:9
  → from research.auxiliary_indicator.smart_vwap_bands import SmartVWAPCalculator
    → smart_vwap_bands.py:23  import pyqtgraph as pg
    → smart_vwap_bands.py:24  from PyQt5.QtGui import QFont
    → smart_vwap_bands.py:25  from PyQt5.QtCore import QTimer
    → smart_vwap_bands.py:27  from PyQt5.QtWidgets import QApplication, QMainWindow, ...
```

**영향 범위:** `BackEngineBase`가 **모든** 백테스트 엔진의 부모 클래스이므로, 모든 백테스트 실행이 PyQt5에 의존하게 됨. Headless/CLI 환경에서 `import backtest.backengine_*`만으로 `ImportError` 발생.

**추가 발견:**
- `backtest/back_static.py:8`에서 `from optuna_dashboard import run_server`가 모듈 레벨 import → 불필요한 GUI 대시보드 의존성
- `backtest/back_code_test.py:3`에서 `from PyQt5.QtCore import QThread` 직접 import (기존 문제)

**권장 해결 방향:**
1. `SmartVWAPCalculator`(순수 연산 클래스)와 `SmartVWAPChart`(GUI 시각화 클래스) 분리
2. `backengine_base.py`에서 연산 전용 모듈만 import
3. `optuna_dashboard` import를 lazy import로 전환

---

## 5) V2.51 기준 수정된 실행 계획

### V2.50 CLI-R1 Phase A 업데이트

기존 Phase A (복원 + 호환화)에 추가 필요한 항목:

| 기존 항목 | V2.51 상태 | 비고 |
|----------|-----------|------|
| GetMoneytopQuery `is_tick` 반영 | 여전히 필요 | 시그니처 동일 |
| `utility/static.py` fallback | 여전히 필요 | 강제 import 동일 |
| `safe_exec.py` 복원/대체 | 여전히 필요 | 파일 미존재 |
| 의존성 매니페스트 복원 | 여전히 필요 | 미존재 |
| **[NEW] smart_vwap_bands PyQt5 분리** | **추가 필요** | V2.51 신규 의존성 |
| **[NEW] optuna_dashboard lazy import** | **추가 필요** | 모듈 레벨 GUI import |
| **[NEW] import 경로 전체 갱신** | **추가 필요** | `backtester.*` → `backtest.*` |

### 신규 Phase A+ (V2.51 특화 선행 작업)

**A+.1 — SmartVWAPCalculator 분리**
- `research/auxiliary_indicator/smart_vwap_bands.py`에서 `SmartVWAPCalculator` 클래스를 별도 파일로 분리
- `backengine_base.py`가 GUI-free 모듈만 import하도록 변경

**A+.2 — optuna_dashboard lazy import**
- `backtest/back_static.py:8`의 `from optuna_dashboard import run_server`를 사용 시점으로 이동

**A+.3 — import 경로 갱신**
- 기존 CLI 코드의 모든 `from backtester.` → `from backtest.` 변환
- `from stock.` → `from trade.stock_korea.` 등

### 신규 Phase B+ (V2.51 기능 활용)

**B+.1 — 수식관리자 CLI 통합**
- `stom formula list/add/test/delete` 명령 추가
- `strategy.db:formula` 테이블 직접 접근

**B+.2 — Strategy DSL headless 평가**
- `trade/strategy_base.py:Strategy`를 CLI에서 인스턴스화
- `FormulaManager.update_user_data()` 패턴 재사용
- `stom strategy evaluate` 명령으로 전략 코드 headless 실행

**B+.3 — 전략 호환성 검사기**
- `고가미갱신지속틱수()` 등 V2.51 문법 변경 자동 감지
- `stom strategy validate --v251-compat` 플래그

---

## 6) 리스크 및 대응 (V2.51 기준 갱신)

| 리스크 | 심각도 | V2.50 대비 변화 | 대응 |
|--------|--------|---------------|------|
| PyQt5 전이 의존성 | 높음 | **신규** | SmartVWAPCalculator 분리 필수 |
| TA-Lib C 라이브러리 설치 | 중간 | 동일 | conda/pip fallback 가이드 |
| `globals()` 오염 | 중간 | 동일 (Strategy 클래스가 사용) | CLI에서 격리된 namespace 사용 |
| 전략 코드 `exec()` 보안 | 중간 | 동일 | `safe_exec` 복원 또는 AST 검증 |
| 튜플 계약 취약성 | 낮음 | 동일 (13-tuple 유지) | dataclass + 단위 테스트 |
| `winreg` Windows 전용 | 중간 | 동일 | 환경변수 fallback |

---

## 7) 최종 제안

### V2.51에서의 최적 전략

1. **Phase A+ 선행 필수**: PyQt5 전이 의존성 분리 없이는 headless 백테스트가 불가능
2. **Strategy 클래스 활용 극대화**: V2.51이 제공하는 DSL 통합 구조는 CLI에 매우 유리
3. **수식관리자 CLI 우선 구현 권장**: DB CRUD만으로 기능이 완결되므로 MVP 범위에 적합
4. **V2.50 보고서의 Phase S0~S2 계획은 유효**: 경로만 갱신하면 동일 설계 적용 가능

### 우선순위 (V2.51 기준)

```
P0 (차단 요인 제거)
├── A+.1 SmartVWAPCalculator PyQt5 분리
├── A+.2 optuna_dashboard lazy import
├── A.1  utility/static.py fallback
└── A.3  import 경로 갱신 (backtester→backtest)

P1 (MVP)
├── S0   headless 백테스트 1회 실행/결과 DB 기록
├── B+.1 수식관리자 CLI (list/add/test/delete)
└── A.2  GetMoneytopQuery is_tick 반영

P2 (AI 자율 운용)
├── B+.2 Strategy DSL headless 평가
├── B+.3 전략 호환성 검사기
├── S1   전략 저장/목록/검증 CLI
└── S2   run→result→재실행 자동 루프
```

---

## 8) 부록: V2.51 주요 파일 참조

| 파일 | 라인 | 설명 |
|------|------|------|
| `trade/strategy_base.py:14-1125` | Strategy 클래스 전체 | DSL 통합 기반 |
| `trade/strategy_base.py:924-1122` | SetGlobalsFunc() | ~120개 한글 함수 레지스트리 |
| `trade/strategy_base.py:450-454` | 고가/저가미갱신지속틱수 | 0인자 함수 변경 |
| `backtest/backengine_base.py:7-9` | Strategy, SmartVWAP, Micro import | V2.51 신규 의존성 |
| `backtest/backengine_base.py:19` | BackEngineBase(Strategy) | 상속 관계 |
| `backtest/backengine_base.py:97-98` | SmartVWAP/Micro 인스턴스화 | 엔진별 생성 |
| `backtest/back_static.py:88` | GetMoneytopQuery 정의 | 6인자 (is_tick 포함) |
| `backtest/backtest.py:247` | class BackTest | V2.50 대비 +1라인 |
| `utility/chart.py:389-553` | FormulaManager(Strategy) | headless 수식 실행 패턴 |
| `ui/ui_etc.py:208-312` | 수식 CRUD 함수 | DB 접근 패턴 |
| `utility/setting.py:20` | DB_STRATEGY 경로 | strategy.db 위치 |
| `research/auxiliary_indicator/smart_vwap_bands.py:23-27` | PyQt5 import | ⚠️ CLI 차단 요인 |
| `backtest/back_static.py:8` | optuna_dashboard import | ⚠️ 불필요 GUI 의존성 |
