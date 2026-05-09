# V3K-IMPL-3 backtest learning-data read-only load path

작성일: 2026-05-09 KST
작업 lane: `STOM_Version_2U_C`
상위 contract: `docs/update_log/2026-05-09_v3k_design_2_analyzer_data_contract.md`
직전 단계: `docs/update_log/2026-05-09_v3k_impl_2b_analyzer_module_staging.md`
작업 성격: V3 analyzer learning DB manifest + `last_update < backtest_date` read-only load path

## 0. 이번 단계 결론

`V3K-IMPL-3`는 V3 analyzer learning-data를 2U_C backtest에서 사용할 수 있도록 하기 위한 read-only load path를 adapter에 추가했다. 이번 단계는 **runtime backtest loop 연결 전 단계**이며, DB 파일을 만들거나 analyzer 생성자를 호출하지 않는다.

이번 단계에서 보존한 안전 조건은 다음과 같다.

```text
기존 backtest/realtime import path 변경: 없음
주문/청산 logic 변경: 없음
core DB schema 변경: 없음
DB 파일 생성/수정: 없음
LS API 의존성 반영: 없음
feature flag 기본값: OFF
learning cutoff 정책: last_update < backtest_date
```

## 1. 구현 범위

### 1.1 `strategy/v3k_analyzer_adapter.py`

추가된 요소는 다음과 같다.

| 요소 | 설명 |
| --- | --- |
| `LearningDbContract` | analyzer kind별 DB명/table template/order column contract |
| `LEARNING_DB_CONTRACTS` | V3 학습 DB 5종 manifest |
| `LearningLoadRequest` | code, backtest_date, strategy_gubun, tick/min, feature flag, limit 요청 object |
| `LearningLoadResult` | read-only load 결과, query, params, diagnostics, rows |
| `learning_query_for_request()` | `last_update < backtest_date` query를 생성 |
| `V3KLearningDataAdapter` | feature flag 기본 OFF + read-only SQLite URI loader |
| `safe_identifier()` | table name SQL identifier guard |

### 1.2 learning DB manifest

| analyzer kind | DB | table template | cutoff |
| --- | --- | --- | --- |
| `candle_pattern` | `pattern_analysis.db` | `{strategy_gubun}_pattern_score` | `last_update < backtest_date` |
| `volume_spike` | `volume_spike.db` | `{strategy_gubun}_volume_spike_{tick|min}` | `last_update < backtest_date` |
| `volume_profile` | `volume_profile.db` | `{strategy_gubun}_volume_score_{tick|min}` | `last_update < backtest_date` |
| `volatility_pattern` | `volatility_pattern.db` | `{strategy_gubun}_volatility_pattern_{tick|min}` | `last_update < backtest_date` |
| `volatility_stop_take` | `volatility_stop_take.db` | `{strategy_gubun}_volatility_{tick|min}` | `last_update < backtest_date` |

`risk` analyzer는 learning DB가 없으므로 이번 load manifest에서 제외한다.

## 2. feature flag 정책

learning load가 실제 query를 실행하려면 다음 두 조건을 모두 만족해야 한다.

```text
V3K_BACKTEST_LEARNING_ENABLED = ON
analyzer별 flag = ON
```

예:

```text
캔들분석 = ON
거래량분석 = ON
가격대분석 = ON
변동성분석 = ON
변손익분석 = ON
```

flag가 꺼져 있으면 `LearningLoadResult.rows`는 비어 있고 diagnostics에 disabled 이유를 남긴다.

## 3. read-only DB 정책

`V3KLearningDataAdapter`는 DB가 존재할 때만 read-only URI로 연결한다.

```text
file:///.../pattern_analysis.db?mode=ro
```

DB가 없으면 SQLite 연결을 시도하지 않고 다음 diagnostics를 반환한다.

```text
learning DB missing; read-only load skipped
```

따라서 이번 단계 smoke에서는 `_database_v3k_shadow`, `*.db` 파일이 생성되지 않는다.

## 4. smoke script

새 script는 다음과 같다.

```text
scripts/smoke_v3k_learning_loader.py
```

검증 항목은 다음과 같다.

1. learning query가 항상 `last_update < ?`를 사용한다.
2. `last_update <= ?`가 query에 들어가지 않는다.
3. feature flag OFF 상태에서는 rows가 비어 있고 disabled diagnostics가 남는다.
4. feature flag ON + DB missing 상태에서는 rows가 비어 있고 missing diagnostics가 남는다.
5. missing DB path를 생성하지 않는다.
6. table identifier에 SQL injection 성격 문자열이 들어오면 `ValueError`로 거부한다.
7. smoke 전후 git status 기준 금지 산출물 변화가 없다.

## 5. 검증 결과

### 5.1 py_compile

```powershell
python -m py_compile strategy\v3k_analyzer_adapter.py scripts\smoke_v3k_learning_loader.py
```

결과: 통과.

### 5.2 learning loader smoke

```powershell
python scripts\smoke_v3k_learning_loader.py
```

결과:

```text
learning load contract ok: candle_pattern min
learning load contract ok: volume_spike tick
learning load contract ok: volume_spike min
learning load contract ok: volume_profile tick
learning load contract ok: volume_profile min
learning load contract ok: volatility_pattern tick
learning load contract ok: volatility_pattern min
learning load contract ok: volatility_stop_take tick
learning load contract ok: volatility_stop_take min
unsafe identifier guard ok
v3k learning loader smoke passed
```

### 5.3 regression smoke

다음 기존 smoke도 재통과했다.

```powershell
python scripts\smoke_v3k_analyzer_modules.py --import-only
python scripts\smoke_v3k_analyzer_modules.py
python scripts\smoke_v3k_analyzer_adapter.py
python scripts\smoke_v3k_analyzer_adapter.py --enable-v3-risk
```

## 6. 이번 단계에서 의도적으로 하지 않은 것

```text
- `_database_v3k_shadow` 생성
- 실제 SQLite learning DB 생성/수정
- analyzer DB class 생성자 호출
- backtest loop에서 load result 사용
- analyzer output을 strategy context에 주입
- 주문/청산 rule 변경
- realtime receiver/order path 변경
- LS API 의존성 반영
```

즉, 이번 단계는 backtest learning-data의 **read-only policy/load adapter**를 만든 것이며, backtest runtime wiring은 다음 단계에서 별도로 feature flag OFF와 dry-run gate를 거쳐야 한다.

## 7. 다음 단계

다음 단계는 `V3K-IMPL-3B`를 권장한다.

목표는 `backtest/backengine_base.py`에 analyzer 생성자나 주문 영향 없이, feature flag 기본 OFF 상태의 dry-run hook 또는 load-plan hook을 추가하는 것이다. 이 hook은 실제 DB가 없으면 no-op이어야 하며, OFF 상태에서 기존 backtest 결과를 바꾸면 안 된다.

```powershell
omx ralph --prd "V3K-IMPL-3B를 시작한다. 목표는 STOM_Version_2U_C에서 Kiwoom증권을 유지한 채 backtest learning-data load path를 backtest engine에 dry-run/no-op hook으로 연결하는 것이다. feature flag 기본 OFF 상태에서 기존 backtest 동작과 주문/청산 결과는 바꾸지 말고, analyzer 생성자 호출과 DB 파일 생성/수정은 금지한다. V3KLearningDataAdapter의 load plan만 안전하게 호출 가능한 경계로 준비하고, py_compile, learning loader smoke, analyzer module smoke, adapter smoke, forbidden artifact guard, release sync, docs/registry 갱신, 한국어 commit까지 수행한다."
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
| 10. V3K-IMPL | 진행 중 | IMPL-2A/2B/3 완료, backtest dry-run/realtime/UI 구현 남음 |
| 11. V3K-VERIFY | 남음 | 통합 검증/승격 판단 |

```text
전체 11단계 중 9단계 + 구현 3차 발판 완료 = 약 88%
[##################--] 88%

현재 단계 V3K-IMPL-3 = 100%
[####################] 100%

V3K-IMPL 내부 진행 = 55%
[###########---------] 55%
```