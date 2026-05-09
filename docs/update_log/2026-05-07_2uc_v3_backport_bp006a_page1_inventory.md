# 2U_C V3 backport 새 후보 탐색 Page 1 - `2UC-V3-BP-006A`

작성일: 2026-05-07 KST  
작성 위치: `STOM_Version_2` root orchestration lane  
미러 대상: `STOM_Version_2U_C` active custom/backport lane  
cycle: `2UC-V3-BP-006A` read-only 후보 탐색 cycle Page 1 / 5  
source lane: `STOM_Version_3`  
target lane: `STOM_Version_2U_C`

## 1. 이번 단계의 목적

기존 V3 도입부터 V3U, 2U_C 선별 backport까지의 본 계획은 `56 / 56 page`로 완료되어 있다.

이번 단계는 그 완료 상태를 깨는 것이 아니라, final handoff 문서에서 정의한 원칙에 따라 **새 후보 ID를 부여하고 read-only Page 1부터 다시 시작**하는 후속 cycle이다.

이번 Page 1의 목표는 다음과 같다.

1. V3와 2U_C 사이의 남은 차이를 다시 read-only로 본다.
2. LS API, DB migration, pyd, GUI 결합이 없는 후보만 찾는다.
3. 기존 BP-001/BP-003 hold 결론을 재개하지 않는다.
4. 새 후보가 있으면 별도 후보 ID로 분리한다.
5. 이번 page에서는 code를 변경하지 않는다.

## 2. 진행률

### 2.1 완료된 기존 기준선

```text
기존 완료 기준선 [████████████████████] 100.0%   56 / 56 page
```

이 기준선은 이미 완료된 V3 도입, V3U pyd-free 전환, 2U_C 기존 backport / 재정렬 / BP-005A / BP-001/BP-003 hold cycle을 의미한다.

### 2.2 새 후보 탐색 cycle 기준

```text
BP-006A cycle [████----------------]  20.0%    1 /  5 page
남은 page     [████████████████----]  80.0%    4 /  5 page
```

### 2.3 확장 추적 기준

새 cycle을 열었기 때문에, handoff 이후 확장 추적 기준은 아래와 같이 본다.

```text
확장 전체     [███████████████████-]  93.4%   57 / 61 page
남은 page     [█-------------------]   6.6%    4 / 61 page
```

계산:

```text
기존 완료 56 page
+ BP-006A read-only 후보 탐색 cycle 5 page 중 Page 1 완료
= 57 / 61 page
```

주의: 이 확장 추적은 기존 56 / 56 완료 상태를 부정하지 않는다. 새 후보를 열었기 때문에 별도 denominator를 추가한 것이다.

## 3. OMX read-only 조사 결과

### 3.1 현재 상태

| 항목 | 결과 |
|---|---|
| root status | clean |
| 2U_C status | clean |
| root HEAD | `a1f1e586 완료된 V3 2U_C 흐름을 handoff checkpoint로 고정한다` |
| 2U_C HEAD | `0f49e7d2 완료된 V3 2U_C handoff 상태를 active lane에 미러링한다` |
| handoff 원칙 | 새 후보 ID와 새 read-only cycle 없이는 재개하지 않음 |

### 3.2 V3 ↔ 2U_C 차이의 큰 범위

OMX read-only diff에서 아래 범위는 그대로 broad / hold로 유지한다.

| 영역 | 판단 | 사유 |
|---|---|---|
| `backtest/` 대규모 재구조화 | hold | 기존 BP-001과 동일하게 파일 수와 구조 변경이 넓음 |
| `cli/` 삭제/이동 | hold | 2U_C custom CLI/연구 흐름과 충돌 가능성 |
| `research/` 삭제 및 `strategy/` 이동 | 부분 후보만 분리 | 전체 이동은 broad지만 일부 standalone analyzer는 후보 가능 |
| `dashboard/` 신규 | hold | web backend / DB / websocket 운영면이 새로 생김 |
| `trade/receiver/trader/restapi` 계열 | hold | BP-003 결론과 동일하게 Kiwoom 유지 구조와 1:1 대응하지 않음 |

## 4. 새 후보 ID

이번 cycle의 새 후보는 아래와 같이 부여한다.

```text
2UC-V3-BP-006A
```

후보명:

```text
V3 strategy risk analyzer standalone 후보
```

## 5. 후보 근거

### 5.1 source 파일

| 항목 | 값 |
|---|---|
| source branch | `STOM_Version_3` |
| source latest version | `STOM V3.18` |
| source file | `strategy/analyzer_risk.py` |
| latest source blob | `d1f73368fb5ce82f5549a4b69eccd85f4c30f81d` |
| 변경 이력 | `STOM V3.09` 이후 `V3.11`, `V3.12`, `V3.13`, `V3.14`, `V3.15`, `V3.18`에서 추적됨 |
| line count | 670 lines |

### 5.2 import / 결합도

`strategy/analyzer_risk.py`의 import는 다음 두 개로 확인되었다.

```python
import numpy as np
from numba import njit
```

read-only pattern check에서 아래 결합 문자열은 발견되지 않았다.

```text
DB_PATH
sqlite
PyQt
QMessageBox
Kiwoom
키움
websocket
REST
xing
ebest
```

따라서 Page 1 기준에서는 다음 특징을 가진다.

| 기준 | 판단 |
|---|---|
| LS API 결합 | 발견되지 않음 |
| Kiwoom 직접 결합 | 발견되지 않음 |
| DB 결합 | 발견되지 않음 |
| GUI 결합 | 발견되지 않음 |
| pyd 결합 | 발견되지 않음 |
| 외부 신규 dependency | 없음으로 추정. `numpy`, `numba`는 기존 STOM 계열에서 이미 사용 |
| 단독 py_compile 가능성 | Page 2에서 확인 필요 |
| runtime 통합 필요성 | Page 2에서 target path와 import 경계 판단 필요 |

## 6. Page 1 판정

`2UC-V3-BP-006A`는 **Page 2로 넘길 수 있는 후보**로 판단한다.

다만 Page 1에서 즉시 적용하지 않는다.

이유:

1. 파일은 standalone에 가깝지만 670 lines로 작지는 않다.
2. 2U_C에는 현재 V3의 `strategy/` package가 그대로 존재하지 않는다.
3. 단순 파일 추가가 안전한지, 기존 `research/analyzer/risk_analyzer.py`와 개념 충돌이 없는지 확인해야 한다.
4. `AnalyzerRisk`가 기대하는 `dict_findex` key가 2U_C의 실시간/전략 데이터 구조와 맞는지 확인해야 한다.
5. Page 2에서 dormant module로만 둘지, 별도 namespace로 둘지, 적용하지 않고 hold할지 결정해야 한다.

## 7. secondary 후보

Page 1에서 함께 확인한 보조 후보는 다음과 같다.

| 후보 | 파일 | Page 1 판단 |
|---|---|---|
| microstructure analyzer | `strategy/analyzer_microstructure.py` | 1016 lines로 더 크고 history/orderbook 상태 관리가 있어 BP-006A 이후 후순위 |
| candle / volume / stop-take analyzers | `strategy/analyzer_candle_pattern.py` 등 | PyQt, DB_PATH, sqlite, talib 등 결합이 있어 이번 후보에서 제외 |
| dashboard backend | `dashboard/backend/*` | web backend / DB / websocket 운영면이 있어 제외 |
| backtest package 재구조화 | `backtest/*` | BP-001 hold 결론 유지 |

## 8. 다음 Page 2에서 판단할 질문

Page 2는 code 적용 전 판단 page다. 다음 질문에 답해야 한다.

1. `strategy/analyzer_risk.py`를 2U_C에 그대로 둘 target path가 있는가?
2. `strategy/` package를 새로 만들 경우 2U_C의 기존 `research/` / `trade/` 구조와 충돌하지 않는가?
3. 파일 추가만으로 dormant module이 되는가, 아니면 기존 import graph에 영향을 주는가?
4. `python -m py_compile`을 단독으로 통과하는가?
5. `AnalyzerRisk`의 필수 `dict_findex` key가 2U_C의 stock/coin 데이터 구조와 맞는가?
6. Page 3에서 최소 patch를 적용할 가치가 있는가, 아니면 hold로 닫아야 하는가?

## 9. 다음 OMX 명령

다음 단계는 Page 2 판단이다.

```powershell
omx sparkshell powershell -NoProfile -Command "Write-Output 'BP006A_PAGE2_PREFLIGHT'; git -C C:\System_Trading\STOM\STOM_V status --short; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short; Write-Output 'SOURCE_SYMBOLS'; git -C C:\System_Trading\STOM\STOM_V show STOM_Version_3:strategy/analyzer_risk.py | Select-String -Pattern '^class |^def |^    def '; Write-Output 'TARGET_CONFLICTS'; git -C C:\System_Trading\STOM\STOM_V ls-tree -r --name-only STOM_Version_2U_C -- strategy research/analyzer | Select-Object -First 120; Write-Output 'REQUIRED_KEYS'; git -C C:\System_Trading\STOM\STOM_V show STOM_Version_3:strategy/analyzer_risk.py | Select-String -Pattern \"dict_findex\\['\"; Write-Output 'ROOT_DOC'; git -C C:\System_Trading\STOM\STOM_V grep -n -e '2UC-V3-BP-006A' -e '57 / 61 page' -- docs/update_log/2026-05-07_2uc_v3_backport_bp006a_page1_inventory.md"
```

## 10. stop condition

이번 Page 1은 아래 조건을 만족하면 완료로 본다.

```text
root / 2U_C clean에서 시작
+ V3 source file과 blob 확인
+ broker / DB / GUI / pyd 결합 문자열 미발견
+ target 충돌 위험을 Page 2 질문으로 분리
+ code 변경 없음
+ root와 2U_C에 동일 문서 commit
= Page 1 완료
```
