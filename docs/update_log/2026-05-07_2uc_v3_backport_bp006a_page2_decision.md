# 2U_C V3 backport `2UC-V3-BP-006A` Page 2 판단 기록

작성일: 2026-05-07 KST  
작성 위치: `STOM_Version_2` root orchestration lane  
미러 대상: `STOM_Version_2U_C` active custom/backport lane  
cycle: `2UC-V3-BP-006A` read-only 후보 탐색 cycle Page 2 / 5  
source lane: `STOM_Version_3`  
target lane: `STOM_Version_2U_C`

## 1. 이번 단계의 목적

Page 1에서 V3 `strategy/analyzer_risk.py`를 새 후보 `2UC-V3-BP-006A`로 분리했다.

이번 Page 2는 code 적용 전 판단 단계다. 목표는 다음 질문에 답하는 것이다.

1. 2U_C에 둘 target path가 안전한가?
2. import graph가 runtime에 영향을 주지 않는가?
3. `AnalyzerRisk`가 요구하는 `dict_findex` key가 2U_C 계열 데이터 구조에 존재하는가?
4. 새 dependency가 필요한가?
5. Page 3에서 최소 patch를 적용할 수 있는가, 아니면 hold해야 하는가?

## 2. 진행률

### 2.1 기존 완료 기준선

```text
기존 완료 기준선 [████████████████████] 100.0%   56 / 56 page
```

### 2.2 BP-006A cycle 기준

```text
BP-006A cycle [████████------------]  40.0%    2 /  5 page
남은 page     [████████████--------]  60.0%    3 /  5 page
```

### 2.3 확장 추적 기준

```text
확장 전체     [███████████████████-]  95.1%   58 / 61 page
남은 page     [█-------------------]   4.9%    3 / 61 page
```

계산:

```text
기존 완료 56 page
+ BP-006A cycle Page 1 완료
+ BP-006A cycle Page 2 완료
= 58 / 61 page
```

## 3. OMX read-only preflight 결과

### 3.1 worktree 상태

| 항목 | 결과 |
|---|---|
| root status | clean |
| 2U_C status | clean |
| root 직전 HEAD | `97438cb9 BP-006A 후보 탐색을 새 read-only cycle로 시작한다` |
| 2U_C 직전 HEAD | `b588fa2c BP-006A 후보 탐색 Page 1 상태를 2U_C에 미러링한다` |

### 3.2 source symbol

V3 source file:

```text
STOM_Version_3:strategy/analyzer_risk.py
```

확인된 주요 symbol:

```text
def _calculate_rsi(...)
def _calculate_volatility(...)
class AnalyzerRisk
    __init__
    _setup_columns
    _setup_analysis_parameters
    get_risk_score
    analyze_batch_data
    _analyze_market_data
    _analyze_trend
    _calculate_momentum
    _analyze_chegyeol_strength
    _analyze_suyang_imbalance
    _analyze_price_position
    _analyze_angle_trend
    _analyze_volume_trend
    _calculate_risk_score
```

### 3.3 target path 충돌 확인

2U_C에는 현재 top-level `strategy/` directory가 없다.

```text
TOPLEVEL_STRATEGY_EXISTS = False
```

또한 `strategy/analyzer_risk.py`는 ignore 대상이 아니다.

```text
check-ignore strategy/analyzer_risk.py -> not_ignored
```

2U_C에는 기존 `research/analyzer/risk_analyzer.py`가 존재하지만 역할이 다르다.

| 파일 | 성격 |
|---|---|
| `research/analyzer/risk_analyzer.py` | portfolio VaR / Sharpe / drawdown 등 research risk analyzer |
| V3 `strategy/analyzer_risk.py` | 실시간/전략 데이터의 RSI, 변동성, 체결강도, 수량 불균형, 가격 위치, 각도, 거래량 기반 risk score analyzer |

따라서 기존 파일을 덮어쓰지 않고 top-level `strategy/analyzer_risk.py`로 dormant 추가하는 방식이 가장 안전하다.

## 4. dependency 판단

V3 source import:

```python
import numpy as np
from numba import njit
```

2U_C dependency / 사용 현황:

| 항목 | 결과 |
|---|---|
| `requirements32.txt` | `numpy==1.26.4` 확인 |
| `requirements64.txt` | `numpy==1.26.4`, `numba==0.63.1` 확인 |
| 기존 2U_C code | `backtest/back_static_numba.py`, `utility/numba_rolling.py`, `trade/risk_analyzer.py` 등에서 numba 계열 사용 확인 |
| 새 dependency 필요 여부 | 없음으로 판단 |

주의:

- `requirements32.txt`에는 `numba`가 보이지 않는다.
- 그러나 Page 3의 추천 적용 방식은 runtime wiring 없는 dormant module 추가이므로 32-bit 실행 흐름에 즉시 import 영향은 없다.
- 실제 runtime wiring은 별도 후보 ID 또는 후속 cycle에서 다뤄야 한다.

## 5. py_compile 사전 확인

Page 2에서는 repo 파일을 변경하지 않고 V3 source를 temp file로 추출해 compile만 확인했다.

```text
TEMP_PYCOMPILE_SOURCE -> py_compile_temp_passed
```

의미:

- V3 source 자체는 Python 문법 compile이 가능하다.
- 아직 2U_C repo 안에 파일을 추가한 것은 아니다.
- Page 3에서 실제 target path에 넣은 뒤 다시 `python -m py_compile strategy/analyzer_risk.py`를 실행해야 한다.

## 6. `dict_findex` key 호환성 판단

V3 `AnalyzerRisk`가 요구하는 key:

```text
현재가
당일거래대금
체결강도
초당매수수량
초당매도수량
분당매수수량
분당매도수량
고저평균대비등락율
최고현재가
최저현재가
체결강도평균
등락율각도
```

2U_C read-only grep 결과, 위 key들은 `backtest/`, `trade/base_strategy.py`, `trade/*_strategy_*` 계열에서 확인된다.

대표 근거:

| key 그룹 | 확인 위치 예시 |
|---|---|
| 현재가 / 당일거래대금 / 체결강도 | `backtest/back_code_test.py`, `backtest/backengine_*`, `trade/base_strategy.py` |
| 초당매수수량 / 초당매도수량 | `backtest/backengine_*_tick.py`, `trade/stock_korea/kiwoom_strategy_tick.py`, `trade/binance/binance_strategy_tick.py` |
| 분당매수수량 / 분당매도수량 | `backtest/backengine_*_min.py`, `trade/base_strategy.py` |
| 최고현재가 / 최저현재가 / 체결강도평균 / 등락율각도 | `trade/base_strategy.py`, `backtest/back_code_test.py` |

따라서 Page 2 기준으로는 key 이름 자체의 호환성은 충분하다고 판단한다.

단, 실제 array shape와 `dict_findex` mapping이 호출 지점마다 동일하다는 뜻은 아니다. Page 3에서는 runtime wiring을 하지 않고 dormant module로만 추가해야 한다.

## 7. Page 2 판단

`2UC-V3-BP-006A`는 **Page 3 최소 patch 적용 후보로 진행 가능**하다.

단, 적용 범위는 아래로 제한한다.

| 항목 | Page 3 제한 |
|---|---|
| target path | `strategy/__init__.py`, `strategy/analyzer_risk.py` |
| source | `STOM_Version_3:strategy/analyzer_risk.py` |
| runtime wiring | 금지 |
| 기존 `research/analyzer/risk_analyzer.py` 수정 | 금지 |
| 기존 `trade/` 전략 import 수정 | 금지 |
| DB / GUI / LS / Kiwoom API 수정 | 금지 |
| 검증 | `python -m py_compile strategy/analyzer_risk.py`, `git diff --check`, release sync |

Page 3의 성격은 **dormant module 추가**다.

이 방식은 다음 장점이 있다.

1. V3 source를 Kiwoom 2U_C에 보존할 수 있다.
2. 기존 runtime 흐름을 변경하지 않는다.
3. `strategy/` package를 향후 V3 feature backport의 분리 namespace로 사용할 수 있다.
4. 문제가 있으면 파일 단위로 되돌리기 쉽다.

## 8. Page 3 전 stop condition

Page 3로 넘어가기 전 조건:

```text
root / 2U_C clean
+ Page 2 문서 commit 완료
+ target path가 기존 파일을 덮어쓰지 않음
+ source py_compile temp 통과
+ key 이름 호환성 근거 확보
+ runtime wiring 금지 원칙 문서화
= Page 3 최소 patch 가능
```

## 9. 다음 OMX 명령

다음 단계는 Page 3 최소 patch 적용이다.

```powershell
omx sparkshell powershell -NoProfile -Command "Write-Output 'BP006A_PAGE3_PREFLIGHT'; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short; Write-Output 'TARGET_EXISTS'; Test-Path C:\System_Trading\STOM\STOM_V.wt-dev\strategy; Write-Output 'SOURCE_BLOB'; git -C C:\System_Trading\STOM\STOM_V rev-parse STOM_Version_3:strategy/analyzer_risk.py; Write-Output 'PAGE2_DOC'; git -C C:\System_Trading\STOM\STOM_V grep -n -e 'Page 3 최소 patch' -e '58 / 61 page' -e 'dormant module' -- docs/update_log/2026-05-07_2uc_v3_backport_bp006a_page2_decision.md"
```
