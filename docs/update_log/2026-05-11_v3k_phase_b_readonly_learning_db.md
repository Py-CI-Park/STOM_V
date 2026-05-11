# 2026-05-11 V3K Phase B read-only learning DB 검증 구현 기록

## 1. 목적

이번 단계의 목적은 `STOM_Version_2U_C`에서 Kiwoom 증권 API와 기존 live/order runtime을 유지한 채, V3K 학습 DB 읽기 경계가 실제 DB 존재 상황에서도 안전한지 검증하는 것이다.

Phase A에서 `_database_v3k_shadow/`와 `v3k_schema_manifest`를 DDL-only로 만들었고, Phase B에서는 이 산출물을 직접 운영 DB로 승격하지 않는다. 대신 다음 두 경계를 분리한다.

| 경계 | 처리 |
| --- | --- |
| 실제 `_database_v3k_shadow/` | read-only health/hash/count 확인만 수행 |
| row-read 기능 검증 | temp fixture DB에서만 수행 |

이 선택은 `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md`의 Option B를 따른다.

## 2. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `scripts/smoke_v3k_learning_db_readonly_existing.py` | 신규 Phase B smoke. temp fixture DB에 학습 row를 넣고 `V3KLearningDataAdapter`가 `?mode=ro` 경로에서만 읽는지 검증한다. |
| `strategy/v3k_analyzer_adapter.py` | `sqlite3.Connection`을 `contextlib.closing()`으로 닫아 Windows에서 fixture DB 파일 핸들이 남지 않도록 보정했다. |
| `docs/update_log/2026-05-11_v3k_phase_b_readonly_learning_db.md` | 본 작업 기록. |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-B` carry-forward 항목 추가. |
| `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` | 진행률을 구현 완료 상태로 갱신. |

## 3. 신규 smoke가 검증하는 항목

`smoke_v3k_learning_db_readonly_existing.py`는 temp fixture DB를 사용한다. 실제 `_database_v3k_shadow/`에는 검증 row를 쓰지 않는다.

| 검증 | 결과 |
| --- | --- |
| flag OFF + DB 존재 | rows 없음, disabled diagnostic 확인 |
| flag ON + DB 없음 | rows 없음, missing DB diagnostic 확인 |
| flag ON + DB 존재 | `last_update < backtest_date` row만 반환 |
| `last_update == backtest_date` | 반환되지 않음 |
| `last_update > backtest_date` | 반환되지 않음 |
| `limit=1` | 가장 최신 eligible row 1개만 반환 |
| `?mode=ro` 연결에서 INSERT 시도 | readonly 오류로 거부 |
| fixture row count | adapter 실행 전후 동일 |
| 실제 `_database_v3k_shadow/` snapshot | smoke 전후 동일 |
| manifest hash | `.omx/reports/v3k-shadow-manifest.json`과 실제 `v3k_schema_manifest` hash 일치 |

검증 대상 learning DB contract:

```text
candle_pattern min
volume_spike tick/min
volume_profile tick/min
volatility_pattern tick/min
volatility_stop_take tick/min
```

`candle_pattern tick`은 현재 learning DB contract가 없으므로 명시적으로 skip reason을 출력한다.

## 4. adapter 보정 이유

초기 smoke 실행 중 Windows에서 temp fixture DB 삭제가 실패했다.

```text
PermissionError: [WinError 32] 다른 프로세스가 파일을 사용 중이기 때문에 ... volatility_pattern.db
```

원인은 `sqlite3.Connection` context manager가 transaction 처리는 하지만 connection 객체를 즉시 close하지 않는다는 점이다. `V3KLearningDataAdapter.load_before_backtest()`가 read-only connection을 열고 SELECT를 수행한 뒤 파일 핸들을 늦게 해제하면서 temp DB cleanup과 충돌했다.

따라서 다음처럼 보정했다.

```python
from contextlib import closing

with closing(sqlite3.connect(uri, uri=True)) as conn:
    conn.row_factory = sqlite3.Row
    rows = tuple(dict(row) for row in conn.execute(query, params).fetchall())
```

이 변경은 read-only adapter의 resource lifecycle만 정리하며, Kiwoom receiver/order/strategy/live runtime에는 연결하지 않는다.

## 5. 운영 DB 및 runtime 안전성

| 항목 | 상태 |
| --- | --- |
| 운영 `_database/` | 변경 없음 |
| 실제 `_database_v3k_shadow/*.db` | read-only 확인만 수행, commit 제외 |
| Kiwoom 주문/청산/live runtime | 변경 없음 |
| LS증권 직접 의존성 | 추가 없음 |
| feature flag DB row | 삽입 없음 |
| listed shares row | 삽입 없음 |
| temp fixture DB | `%TEMP%` 아래 생성 후 삭제, repo에 남지 않음 |

## 6. 검증 결과

아래 명령 세트가 통과했다.

```powershell
python -m py_compile strategy/v3k_analyzer_adapter.py scripts/init_v3k_shadow_db.py scripts/v3k_db_health.py scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.phase-b.before.json --strict
python scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.phase-b.after.json --strict
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_settings_surface.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git status --short -- _database/ _database_v3k_shadow/ *.db
```

핵심 smoke 출력:

```text
read-only existing learning DB ok: candle_pattern min
read-only existing learning DB ok: volume_spike tick
read-only existing learning DB ok: volume_spike min
read-only existing learning DB ok: volume_profile tick
read-only existing learning DB ok: volume_profile min
read-only existing learning DB ok: volatility_pattern tick
read-only existing learning DB ok: volatility_pattern min
read-only existing learning DB ok: volatility_stop_take tick
read-only existing learning DB ok: volatility_stop_take min
candle_pattern tick skipped: no tick learning DB contract
v3k Phase B read-only learning DB smoke passed
```

## 7. 완료 판정

Phase B는 계획서의 완료 기준 중 read-only learning DB 검증 구현 범위를 충족한다.

| 완료 기준 | 판정 |
| --- | --- |
| 신규 read-only smoke/test | 완료 |
| row-read 검증 | 완료 |
| leakage 차단 검증 | 완료 |
| missing DB fallback | 완료 |
| flag OFF fallback | 완료 |
| write rejection | 완료 |
| 실제 shadow DB read-only health/hash | 완료 |
| 운영 DB 무변경 | 완료 |
| Kiwoom runtime 무변경 | 완료 |
| LS 직접 의존성 없음 | 완료 |
| update_log/registry 기록 | 완료 |

## 8. 다음 단계

다음 단계는 Phase C가 아니라, Phase B 결과를 바탕으로 **어떤 활성화 경계로 갈지 다시 선택하는 것**이다.

추천 순서:

1. Phase B commit 직후 전체 상태 확인.
2. Phase C 후보 중 하나를 별도 계획서로 작성.
   - GUI/settings 연결
   - formula/global runtime hook
   - live Kiwoom dry-run preload diagnostic
   - analyzer output 전략 반영
3. 각 후보는 여전히 default-OFF, rollback, Kiwoom untouched audit, LS dependency audit를 포함해야 한다.

현 시점에서 운영 DB cutover와 live trading decision 반영은 아직 진행하지 않는다.