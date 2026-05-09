# V3K-IMPL-2B analyzer module staging

작성일: 2026-05-09 KST
작업 lane: `STOM_Version_2U_C`
상위 contract: `docs/update_log/2026-05-09_v3k_design_2_analyzer_data_contract.md`
직전 단계: `docs/update_log/2026-05-09_v3k_impl_2a_adapter_risk_smoke.md`
작업 성격: V3 analyzer module staging + import/field-contract smoke

## 0. 이번 단계 결론

`V3K-IMPL-2B`는 V3의 주요 학습 analyzer module을 2U_C에 staging했다. 단, 아직 backtest/realtime runtime에는 연결하지 않았다.

이번 단계의 안전 조건은 다음과 같다.

```text
기존 backtest/realtime import path 변경: 없음
주문/청산 logic 변경: 없음
core DB schema 변경: 없음
DB 파일 생성/수정: 없음
LS API 의존성 반영: 없음
feature flag 기본값: OFF
```

## 1. staging된 V3 analyzer module

| module | class | V3K output | learning DB | runtime wiring |
| --- | --- | --- | --- | --- |
| `strategy/analyzer_candle_pattern.py` | `AnalyzerCandlePattern` | `패턴점수`, `패턴신뢰도` | `pattern_analysis.db` | 미연결 |
| `strategy/analyzer_volume_spike.py` | `AnalyzerVolumeSpike` | `거래량점수`, `거래량신뢰도` | `volume_spike.db` | 미연결 |
| `strategy/analyzer_volume_profile.py` | `AnalyzerVolumeProfile` | `가격대점수`, `가격대신뢰도` | `volume_profile.db` | 미연결 |
| `strategy/analyzer_volatility_pattern.py` | `AnalyzerVolatilityPattern` | `변동성점수`, `변동성신뢰도` | `volatility_pattern.db` | 미연결 |
| `strategy/analyzer_volatility_stop_take.py` | `AnalyzerVolatilityStopTake` | `예상수익률`, `익절수익률`, `손절수익률`, `변손익신뢰도` | `volatility_stop_take.db` | 미연결 |

각 파일에는 staging note를 추가했다. 이 note는 feature flag, DB migration gate, runtime wiring gate 없이 사용하지 말라는 경고다.

## 2. 2U_C 호환 보정

V3 원본 module은 V3 package 구조를 기준으로 import한다. 2U_C에서는 다음 import만 최소 보정했다.

| V3 import | 2U_C staging import |
| --- | --- |
| `ui.create_widget.set_text.famous_saying` | `ui.set_text.famous_saying` |
| `utility.static_method.static_datetime.now` | `utility.static.now` |
| `utility.static_method.static_decorator.thread_decorator` | `utility.static.thread_decorator` |
| `utility.settings.setting_base.UI_NUM, DB_PATH` | `utility.setting_base.ui_num as UI_NUM, DB_PATH` |

`talib`는 현재 local ABI 문제로 import가 실패할 수 있으므로, `analyzer_candle_pattern.py`에서 staging import가 깨지지 않도록 optional import로 감쌌다. 이 조치는 module import/py_compile 단계의 안전장치이며, candle pattern 실제 학습/계산 활성화 전에 TA-Lib runtime 검증을 별도로 통과해야 한다.

## 3. adapter contract 확장

`strategy/v3k_analyzer_adapter.py`에 다음을 추가했다.

| 요소 | 설명 |
| --- | --- |
| `AnalyzerModuleContract` | analyzer kind/module/class/flag/field/output/DB contract |
| `ANALYZER_MODULE_CONTRACTS` | candle, volume, volatility, risk analyzer registry |
| `staged_analyzer_modules()` | staging module 목록 제공 |
| `missing_analyzer_fields()` | stock/coin tick/min factor list에서 필수 field 누락 검증 |
| analyzer별 feature flag 상수 | `캔들분석`, `거래량분석`, `가격대분석`, `변동성분석`, `변손익분석` |

## 4. smoke script

새 script는 다음과 같다.

```text
scripts/smoke_v3k_analyzer_modules.py
```

이 script는 다음을 검증한다.

1. staging module import 가능 여부.
2. 각 module에 예상 class가 존재하는지 여부.
3. stock/coin tick/min factor list가 analyzer별 필수 field contract를 만족하는지 여부.
4. smoke 중 `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` status 변화가 없는지 여부.

## 5. 검증 결과

### 5.1 py_compile

```powershell
python -m py_compile `
  strategy\v3k_analyzer_adapter.py `
  strategy\analyzer_candle_pattern.py `
  strategy\analyzer_volume_spike.py `
  strategy\analyzer_volume_profile.py `
  strategy\analyzer_volatility_pattern.py `
  strategy\analyzer_volatility_stop_take.py `
  scripts\smoke_v3k_analyzer_adapter.py `
  scripts\smoke_v3k_analyzer_modules.py
```

결과: 통과.

### 5.2 module import smoke

```powershell
python scripts\smoke_v3k_analyzer_modules.py --import-only
```

결과: `AnalyzerCandlePattern`, `AnalyzerVolumeSpike`, `AnalyzerVolumeProfile`, `AnalyzerVolatilityPattern`, `AnalyzerVolatilityStopTake`, `AnalyzerRisk` import/class 확인 통과.

### 5.3 field-contract smoke

```powershell
python scripts\smoke_v3k_analyzer_modules.py
```

결과: stock/coin tick/min의 analyzer field contract 확인 통과.

### 5.4 IMPL-2A regression smoke

```powershell
python scripts\smoke_v3k_analyzer_adapter.py
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
```

결과: 기본 OFF no-signal 및 explicit ON AnalyzerRisk smoke 통과.

## 6. 이번 단계에서 의도적으로 하지 않은 것

```text
- analyzer 생성자 호출
- analyzer learning DB table 생성
- `_database` 또는 shadow DB 생성/수정
- `backtest/backengine_base.py`에 analyzer output 주입
- realtime receiver/order path 변경
- formula/global facade 변경
- LS API 의존성 반영
```

V3 analyzer 생성자 일부는 DB table 초기화를 수행하므로, DESIGN-1/1B의 DB cutover gate 전에는 생성자 호출을 runtime에 연결하지 않는다.

## 7. 다음 단계

다음 단계는 `V3K-IMPL-3`이다.

목표는 staging된 analyzer를 runtime에 바로 연결하는 것이 아니라, backtest learning-data load path를 feature flag 기본 OFF 상태로 설계/구현하는 것이다. 최초 구현은 DB write 없이 read-only 또는 dry-run 형태로 시작해야 한다.

```powershell
omx ralph --prd "V3K-IMPL-3를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 V3 analyzer learning-data를 backtest에서 사용할 수 있는 load path를 feature flag 기본 OFF와 read-only DB 원칙으로 준비하는 것이다. 먼저 learning DB path/manifest/last_update < backtest_date 정책을 adapter에 연결하고, analyzer 생성자나 backtest runtime wiring은 안전 gate를 통과한 범위로 제한한다. core DB 변경, DB 파일 생성/수정, 주문/청산 변경, LS API 의존성 반영은 금지한다. py_compile, module smoke, adapter smoke, forbidden artifact guard, docs/registry 갱신, 한국어 commit까지 수행한다."
```

## 8. 전체 계획 progress

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
| 10. V3K-IMPL | 진행 중 | IMPL-2A/2B 완료, backtest/realtime/UI 구현 남음 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 판단 |

```text
전체 11단계 중 9단계 + 구현 2차 발판 완료 = 약 86%
[#################---] 86%

현재 단계 V3K-IMPL-2B = 100%
[####################] 100%

V3K-IMPL 내부 진행 = 40%
[########------------] 40%
```
