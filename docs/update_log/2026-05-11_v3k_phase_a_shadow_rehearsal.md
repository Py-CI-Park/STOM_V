# V3K Phase A shadow DB rehearsal 실행 기록

작성일: 2026-05-11 KST
대상 branch: `STOM_Version_2U_C`
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`

## 1. 목적

V3K full activation의 첫 실행 phase인 Phase A를 시작한다. 목표는 운영 `_database/`를 건드리지 않고, V3 학습/분석 DB의 rehearsal 대상인 `_database_v3k_shadow/`를 생성할 수 있는 DDL-only 경로를 준비하고 검증하는 것이다.

이 단계는 다음을 하지 않는다.

- 운영 `_database/` 변경
- Kiwoom 주문/청산/live runtime 변경
- LS Securities REST/TR/REAL 직접 의존 도입
- feature flag ON 전환
- production learning row 삽입
- DB 파일 commit

## 2. 구현 요약

| 파일 | 변경 |
| --- | --- |
| `scripts/init_v3k_shadow_db.py` | `compute_schema_hash()` 추가, dry-run manifest에 `schema_hash` stamp 추가 |
| `scripts/apply_v3k_shadow_db.py` | Phase A 전용 DDL-only shadow DB apply script 신규 작성 |
| `tests/unit/test_v3k_shadow_schema_hash.py` | schema hash 결정성/키 순서/default 공백 회귀 테스트 추가 |
| `.gitignore` | `_database_v3k_shadow/` 및 Phase A ephemeral report ignore 추가 |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-A` carry-forward 등록 |

## 3. 핵심 결정

### 3.1 schema 단일 출처 유지

`scripts/init_v3k_shadow_db.py`가 `LEARNING_DBS`, `META_DBS`, `create_table_sql`, `compute_schema_hash`의 단일 출처다. 신규 apply script는 이 값을 직접 import한다.

### 3.2 dry-run CLI 보존

기존 `init_v3k_shadow_db.py --dry-run` 외부 동작은 유지한다. DB 생성은 신규 `apply_v3k_shadow_db.py --apply`에서만 수행한다.

### 3.3 default-OFF 보존

Phase A는 DDL과 schema manifest만 생성한다. `v3k_feature_flags`, `v3k_listed_shares`에는 row를 넣지 않는다.

### 3.4 DB 파일 commit 금지

`_database_v3k_shadow/`는 rehearsal 산출물이며 git commit 대상이 아니다. commit 대상은 script/test/docs/registry/ignore와 schema manifest audit trail만이다.

## 4. 검증 명령

```powershell
python -m py_compile scripts/init_v3k_shadow_db.py scripts/apply_v3k_shadow_db.py scripts/v3k_db_health.py
python -m pytest tests/unit/test_v3k_shadow_schema_hash.py -q
python scripts/init_v3k_shadow_db.py --dry-run --manifest .omx/reports/v3k-shadow-manifest.json
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.before.json
python scripts/apply_v3k_shadow_db.py --apply --shadow-dir _database_v3k_shadow
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.after.json --strict
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
```

## 5. 완료 기준

- `_database_v3k_shadow/`에 7개 DB가 생성된다.
- `v3k_db_health.py --strict`가 생성 후 통과한다.
- `v3k_feature_flags` row count는 0이다.
- `v3k_listed_shares` row count는 0이다.
- `v3k_schema_manifest` row count는 생성된 table 수와 일치한다.
- DB 파일은 git에 stage/commit되지 않는다.
- Kiwoom runtime/order/receiver 경로와 LS 직접 의존 audit이 통과한다.

## 6. 다음 단계

Phase A 완료 후 바로 Phase B를 구현하지 않는다. 먼저 `docs/plans/<YYYY-MM-DD>_v3k_phase_b_readonly_learning_db_plan.md`를 별도 작성하고, Phase A 산출물을 입력으로 삼아 read-only learning DB 검증 계획을 다시 수립한다.

Directive: Phase A 산출물은 V3K full activation의 시작점일 뿐이며, live Kiwoom runtime 또는 전략/주문 판단에는 연결하지 않는다.

## 7. 실행 결과

2026-05-11 KST 기준 Phase A rehearsal은 통과했다.

검증 증거:

```text
python -m py_compile scripts/init_v3k_shadow_db.py scripts/apply_v3k_shadow_db.py scripts/v3k_db_health.py
python -c "... schema_hash test functions ..." -> schema_hash_tests_py313_passed
py -3.11 -m pytest tests/unit/test_v3k_shadow_schema_hash.py -q -> 3 passed
python scripts/init_v3k_shadow_db.py --dry-run --manifest .omx/reports/v3k-shadow-manifest.json -> db_count 7, schema_hash OK
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.before.json -> missing shadow expected
python scripts/apply_v3k_shadow_db.py --apply --shadow-dir _database_v3k_shadow --allow-existing -> apply report 생성
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.after.json --strict -> OK
row counts -> feature_flags 0, listed_shares 0, schema_manifest 17
V3K smoke scripts -> OK
audit_v3k_verify_1a.py --base 57496d24 -> OK
audit_v3k_verify_1b_closure.py -> OK
verify_nonrelease_sync.py -> OK
```

주의:

- 현재 Python 3.13 환경에는 `pytest`가 없어서 schema hash test는 Python 3.13 직접 함수 실행으로 검증했고, pytest runner 자체는 기존 `py -3.11` 환경으로 보조 검증했다.
- `_database_v3k_shadow/`와 `.omx/reports/v3k-db-health.*.json`, `.omx/reports/v3k-shadow-apply-report.json`은 local rehearsal 산출물이며 commit하지 않는다.
- `.omx/reports/v3k-shadow-manifest.json`만 schema audit trail로 강제 추가한다.
