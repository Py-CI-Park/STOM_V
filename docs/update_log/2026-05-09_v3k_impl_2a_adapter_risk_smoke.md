# V3K-IMPL-2A adapter skeleton 및 AnalyzerRisk dormant smoke

작성일: 2026-05-09 KST
작업 lane: `STOM_Version_2U_C`
상위 contract: `docs/update_log/2026-05-09_v3k_design_2_analyzer_data_contract.md`
상세 spec: `docs/superpowers/specs/2026-05-09-v3k-analyzer-data-contract-spec.md`
작업 성격: feature flag 기본 OFF adapter skeleton + dormant AnalyzerRisk smoke fixture

## 0. 이번 단계 결론

`V3K-IMPL-2A`는 V3 analyzer를 2U_C runtime에 바로 연결하지 않고, 먼저 안전한 adapter boundary를 추가했다.

이번 단계에서 추가한 runtime 영향은 다음과 같다.

```text
기존 backtest/realtime import path 변경: 없음
주문/청산 logic 변경: 없음
core DB 변경: 없음
LS API 의존성 추가: 없음
feature flag 기본값: OFF
```

추가된 파일은 다음 2개다.

| 파일 | 역할 |
| --- | --- |
| `strategy/v3k_analyzer_adapter.py` | V3K analyzer용 feature-flagged adapter skeleton |
| `scripts/smoke_v3k_analyzer_adapter.py` | adapter OFF guard 및 dormant AnalyzerRisk ON smoke fixture |

## 1. 구현 범위

### 1.1 `strategy/v3k_analyzer_adapter.py`

추가된 핵심 요소는 다음과 같다.

| 요소 | 설명 |
| --- | --- |
| `V3KAnalyzerContext` | market/type/tick 여부/dict_findex/code_data/feature_flags를 명시적으로 담는 input contract |
| `V3KAnalyzerOutput` | analyzer output을 runtime 주문 logic과 분리하는 neutral bundle |
| `normalize_v3k_flags` | V3K feature flag를 bool로 정규화하며 기본값은 모두 OFF |
| `resolve_field` | Kiwoom factor name을 안전하게 찾는 helper |
| `slice_window` | 기존 2U_C backtest window slicing 규칙을 보존하는 helper |
| `build_market_info` | V3 analyzer가 기대하는 market_info compatibility view 초안 |
| `missing_risk_fields` | AnalyzerRisk 실행 전 필수 field 누락을 no-signal로 전환하기 위한 guard |
| `V3KAnalyzerAdapter.analyze_risk` | dormant `strategy.analyzer_risk.AnalyzerRisk`를 feature flag ON일 때만 실행하는 smoke path |

### 1.2 기본 OFF 조건

다음 flag가 모두 ON일 때만 dormant AnalyzerRisk smoke path가 실행된다.

```text
V3K_BACKTEST_LEARNING_ENABLED
V3K_RISK_ANALYZER_V3_ENGINE
리스크분석
```

flag가 없거나 일부만 ON이면 `risk_score=None`을 반환하고 diagnostics에 disabled 이유를 남긴다.

### 1.3 `scripts/smoke_v3k_analyzer_adapter.py`

smoke script는 다음 4개 fixture를 만든다.

| fixture | factor list | 목적 |
| --- | --- | --- |
| `stock-tick` | `list_stock_tick` | 주식 tick 필드 contract 검증 |
| `stock-min` | `list_stock_min` | 주식 min 필드 contract 검증 |
| `coin-tick` | `list_coin_tick` | 코인/future 계열 tick 필드 contract 검증 |
| `coin-min` | `list_coin_min` | 코인/future 계열 min 필드 contract 검증 |

검증은 두 가지 mode로 나뉜다.

```powershell
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_adapter.py --enable-v3-risk
```

첫 번째는 기본 OFF 상태에서 analyzer가 실행되지 않는지 확인한다. 두 번째는 명시적으로 flag를 켰을 때 dormant AnalyzerRisk가 0~100 범위의 risk score를 산출하는지 확인한다.

## 2. 검증 결과

### 2.1 py_compile

```powershell
python -m py_compile strategy\v3k_analyzer_adapter.py scripts\smoke_v3k_analyzer_adapter.py
```

결과: 통과.

### 2.2 기본 OFF smoke

```powershell
python scripts\smoke_v3k_analyzer_adapter.py
```

결과:

```text
stock-tick: OFF no-signal, ON path intentionally disabled
stock-min: OFF no-signal, ON path intentionally disabled
coin-tick: OFF no-signal, ON path intentionally disabled
coin-min: OFF no-signal, ON path intentionally disabled
v3k analyzer adapter smoke passed
```

### 2.3 dormant AnalyzerRisk ON smoke

```powershell
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
```

결과:

```text
stock-tick: OFF no-signal, ON risk_score=9.76
stock-min: OFF no-signal, ON risk_score=9.62
coin-tick: OFF no-signal, ON risk_score=9.24
coin-min: OFF no-signal, ON risk_score=9.01
v3k analyzer adapter smoke passed
```

## 3. 변경하지 않은 것

이번 단계에서는 다음을 의도적으로 변경하지 않았다.

```text
- `backtest/backengine_base.py` runtime wiring
- realtime receiver/order path
- 기존 `trade.risk_analyzer.RiskAnalyzer` 활성 경로
- strategy formula/global 함수 경로
- core DB schema 및 DB 파일
- LS Securities REST/TR/REAL API 의존성
```

## 4. 위험과 보정

| 위험 | 현재 대응 |
| --- | --- |
| analyzer output이 기존 주문/청산에 영향을 줄 위험 | adapter가 기존 runtime에 import되지 않으며 flag 기본 OFF |
| field 누락으로 runtime exception이 날 위험 | `missing_risk_fields` guard가 no-signal 반환 |
| dormant AnalyzerRisk의 실제 동작 미확인 | 4개 synthetic fixture에서 ON smoke 통과 |
| V3 전체 analyzer가 아직 미반영 | 다음 단계에서 module staging/추가 smoke로 확장 |

## 5. 다음 단계

다음 단계는 `V3K-IMPL-2B`다.

목표는 아직 runtime에 연결하지 않고, V3의 나머지 analyzer module을 2U_C에 staging하면서 import/py_compile/field-contract smoke를 추가하는 것이다.

```powershell
omx ralph --prd "V3K-IMPL-2B를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 V3 analyzer module staging을 진행하는 것이다. AnalyzerCandlePattern, AnalyzerVolumeSpike, AnalyzerVolumeProfile, AnalyzerVolatilityPattern, AnalyzerVolatilityStopTake를 runtime wiring 없이 반영하거나 adapter staging 대상으로 준비하고, feature flag 기본 OFF, import/py_compile, field-contract smoke, forbidden artifact guard, docs/registry 갱신, 한국어 commit까지 수행한다. core DB 변경, 주문/청산 변경, LS API 의존성 반영은 금지한다."
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
| 10. V3K-IMPL | 진행 중 | IMPL-2A 완료, analyzer/backtest/realtime/UI 구현 남음 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 판단 |

```text
전체 11단계 중 9단계 + 구현 1차 발판 완료 = 약 84%
[#################---] 84%

현재 단계 V3K-IMPL-2A = 100%
[####################] 100%
```