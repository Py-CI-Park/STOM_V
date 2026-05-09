# V3K-IMPL-3B backtest learning-data dry-run/no-op hook

작성일: 2026-05-09 KST
작업 lane: `STOM_Version_2U_C`
상위 단계: `docs/update_log/2026-05-09_v3k_impl_3_backtest_learning_loader.md`
작업 성격: backtest engine dry-run/no-op hook 연결, feature flag 기본 OFF

## 0. 이번 단계 결론

`V3K-IMPL-3B`는 IMPL-3에서 만든 `V3KLearningDataAdapter`를 `backtest/backengine_base.py`에 **dry-run/no-op hook**으로 연결했다.

이번 단계는 아직 analyzer 생성자 호출, analyzer output 주입, 주문/청산 변경을 수행하지 않는다. 기본 flag가 OFF이면 기존 backtest loop에서 즉시 빈 tuple을 반환하고 내부 load plan도 변경하지 않는다.

```text
기존 주문/청산 logic 변경: 없음
analyzer 생성자 호출: 없음
DB 파일 생성/수정: 없음
core DB schema 변경: 없음
LS API 의존성 반영: 없음
feature flag 기본값: OFF
```

## 1. 구현 범위

### 1.1 `backtest/backengine_base.py`

추가된 요소는 다음과 같다.

| 요소 | 설명 |
| --- | --- |
| `self.v3k_learning_loader` | `V3KLearningDataAdapter` instance. DB를 생성하지 않는다. |
| `self.v3k_learning_load_plan` | flag ON일 때 code/date별 dry-run load 결과를 보관하는 내부 plan dict |
| `_v3k_strategy_gubun()` | `market_gubun`을 `stock/future/coin` table prefix로 변환 |
| `_v3k_learning_flags()` | `dict_set`에서 V3K master/analyzer별 flag를 안전하게 추출 |
| `_v3k_learning_kinds_for_current_timeframe()` | tick에서는 candle pattern을 제외하고 learning DB kind를 순회 |
| `PrepareV3KLearningLoadPlan()` | feature flag가 OFF이면 즉시 no-op, ON이면 read-only/missing-DB load plan 생성 |

`BackTest()` loop에는 일자 segment 시작 시 다음 hook이 들어간다.

```python
self.PrepareV3KLearningLoadPlan(code, day_vals[start_idx])
```

기본 OFF 상태에서는 이 호출이 아무 것도 하지 않는다.

### 1.2 hook 동작 정책

| 조건 | 동작 |
| --- | --- |
| `V3K_BACKTEST_LEARNING_ENABLED=False` | 빈 tuple 반환, `v3k_learning_load_plan` 변경 없음 |
| master flag ON + analyzer flag ON + DB 없음 | missing DB diagnostics를 담은 load result를 plan에 기록 |
| DB 존재 | `V3KLearningDataAdapter`의 read-only URI path로만 query 수행 |
| tick timeframe | candle pattern load 제외 |
| min timeframe | candle pattern 포함 |

## 2. smoke script

새 script는 다음과 같다.

```text
scripts/smoke_v3k_backtest_learning_hook.py
```

검증 항목은 다음과 같다.

1. `BackEngineBase`를 실제 MainLoop 없이 `object.__new__`로 생성한다.
2. feature flag OFF 상태에서 `PrepareV3KLearningLoadPlan()`이 빈 tuple을 반환하고 plan을 변경하지 않는지 확인한다.
3. feature flag ON + DB missing 상태에서 tick mode는 4개, min mode는 5개 missing-DB result를 반환하는지 확인한다.
4. smoke 전후 git status 기준 `_database_v3k_shadow`, `*.db`, `backtest/graph` 등 금지 산출물 변화가 없는지 확인한다.
5. local TA-Lib ABI 문제 때문에 smoke script 안에서만 `talib` stub을 사용한다. production code는 stub을 사용하지 않는다.

## 3. 검증 결과

### 3.1 hook smoke

```powershell
python scripts\smoke_v3k_backtest_learning_hook.py
```

결과:

```text
backtest hook OFF no-op ok
backtest hook ON missing-DB no-op ok: tick
backtest hook ON missing-DB no-op ok: min
v3k backtest learning hook smoke passed
```

### 3.2 regression smoke

다음 기존 smoke도 재통과했다.

```powershell
python scripts\smoke_v3k_learning_loader.py
python scripts\smoke_v3k_analyzer_modules.py --import-only
python scripts\smoke_v3k_analyzer_modules.py
python scripts\smoke_v3k_analyzer_adapter.py
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
```

## 4. 이번 단계에서 의도적으로 하지 않은 것

```text
- analyzer class 생성자 호출
- learning DB table 생성
- `_database_v3k_shadow` 생성
- 실제 DB read 성공 fixture 생성
- analyzer output을 `Strategy()` globals에 주입
- 주문/청산 조건 변경
- realtime receiver/order path 변경
- formula/global facade 변경
- LS API 의존성 반영
```

## 5. 다음 단계

다음 단계는 `V3K-IMPL-4`다.

목표는 realtime learning-data usage의 안전 경계를 준비하는 것이다. backtest처럼 바로 매매 로직에 연결하지 말고, feature flag 기본 OFF와 missing-DB no-op, Kiwoom receiver/order path 무변경 조건을 유지해야 한다.

```powershell
omx ralph --prd "V3K-IMPL-4를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 realtime learning-data usage 경계를 feature flag 기본 OFF와 missing-DB no-op 방식으로 준비하는 것이다. Kiwoom receiver/order path, 주문/청산 조건, core DB, DB 파일 생성/수정은 금지한다. V3KLearningDataAdapter를 realtime에서 안전하게 preload/dry-run 할 수 있는 adapter boundary와 smoke를 만들고, py_compile, backtest hook smoke, learning loader smoke, analyzer module smoke, adapter smoke, forbidden artifact guard, release sync, docs/registry 갱신, 한국어 commit까지 수행한다."
```

## 6. 전체 계획 progress

| 전체 단계 | 상태 | 설명 |
| --- | --- | --- |
| 1. V3 공식 lane 진입 | 완료 | V3.18 ingress 완료 |
| 2. V3U pyd-free 전환 | 완료 | 3U parity audit 완료 |
| 3. 2U_C safe-candidate 백포트 | 완료 | BP-002A~BP-014A 선별/종료 |
| 4. V3 미반영 신기능 audit | 완료 | 학습/분석/DB 미반영 확인 |
| 5. V3K 목표 재정의 | 완료 | Kiwoom 유지 + V3 신기능 목적 고정 |
| 6. V3K-DESIGN-0 | 완료 | Phase 0 kickoff |
| 7. V3K-DESIGN-1 | 완료 | DB/학습 설계 |
| 8. V3K-DESIGN-1B | 완료 | read-only script 3종 |
| 9. V3K-DESIGN-2 | 완료 | analyzer/data contract |
| 10. V3K-IMPL | 진행 중 | IMPL-2A/2B/3/3B 완료, realtime/UI/facade 구현 남음 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 판단 |

```text
전체 11단계 중 9단계 + 구현 3B 완료 = 약 90%
[##################--] 90%

현재 단계 V3K-IMPL-3B = 100%
[####################] 100%

V3K-IMPL 내부 진행 = 65%
[#############-------] 65%
```