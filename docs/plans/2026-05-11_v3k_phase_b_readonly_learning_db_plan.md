# V3K Phase B — read-only learning DB 검증 계획

작성일: 2026-05-11 KST  
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`  
대상 branch: `STOM_Version_2U_C`  
직전 기준 commit: `1196946a V3K Phase A shadow DB rehearsal을 실행 가능하게 한다`

---

## 0. 목적과 현재 위치

### 0.1 V3K 전체 목적

V3K의 목표는 `STOM_Version_2U_C`에서 **Kiwoom 증권 API를 유지한 채**, V3로 진행되며 추가된 분석·학습·DB·백테스트·실시간 사전학습 기능을 LS증권 직접 의존성 없이 반영하는 것이다.

즉, 목표는 다음 두 문장을 동시에 만족하는 것이다.

```text
V3 기능은 가져온다.
LS증권 직접 의존성은 가져오지 않고 Kiwoom 운용 경계를 보존한다.
```

### 0.2 Phase A 완료 상태

Phase A는 `1196946a`에서 다음 상태로 완료되었다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| shadow DB manifest | 완료 | `.omx/reports/v3k-shadow-manifest.json` commit됨 |
| shadow DB apply tool | 완료 | `scripts/apply_v3k_shadow_db.py` |
| schema hash invariant | 완료 | `scripts/init_v3k_shadow_db.py::compute_schema_hash` + `tests/unit/test_v3k_shadow_schema_hash.py` |
| shadow DB 실체 | 완료/ephemeral | `_database_v3k_shadow/` 생성됨, `.gitignore`로 commit 제외 |
| health 검증 | 완료/ephemeral | `.omx/reports/v3k-db-health.before.json`, `.after.json` 생성, commit 제외 |
| row 정책 | 완료 | `v3k_feature_flags=0`, `v3k_listed_shares=0`, `v3k_schema_manifest=17` 확인 |
| Kiwoom/live runtime | 보존 | Phase A 변경 파일은 script/doc/test 중심이며 주문·청산·live runtime 미변경 |
| LS 직접 의존성 | 없음 | Phase A audit 통과 |

Phase A manifest의 기준 수량은 다음과 같다.

| 기준 | 값 |
| --- | ---: |
| DB 파일 수 | 7 |
| manifest table template 수 | 13 |
| 실제 적용 후 `v3k_schema_manifest` row 수 | 17 |

### 0.3 Phase B의 역할

Phase B는 **학습 DB를 실제 runtime에 연결하는 단계가 아니다.**  
Phase B는 이미 존재하는 `V3KLearningDataAdapter`가 학습 DB를 다음 방식으로만 읽는다는 사실을 검증하는 단계다.

1. feature flag가 OFF이면 DB를 읽지 않는다.
2. DB가 없으면 missing diagnostic으로 안전하게 종료한다.
3. DB가 있으면 SQLite URI `?mode=ro` + `uri=True`로만 연다.
4. `last_update < backtest_date` 규칙으로 미래 데이터 leakage를 막는다.
5. 검증 중에도 운영 `_database/`와 Kiwoom 주문·청산·live runtime은 건드리지 않는다.
6. LS증권 직접 의존성을 추가하지 않는다.

---

## 1. scope 정본

### 1.1 In scope

| 분류 | 포함 항목 |
| --- | --- |
| 계획 문서 | 본 파일 `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` |
| Phase B 구현 후보 | read-only 학습 DB fixture smoke/test 추가 |
| 검증 대상 | `strategy/v3k_analyzer_adapter.py::V3KLearningDataAdapter` |
| 입력 산출물 | `_database_v3k_shadow/`, `.omx/reports/v3k-shadow-manifest.json`, `compute_schema_hash`, `v3k_schema_manifest` |
| 허용 DB | temp/fixture shadow DB 또는 기존 `_database_v3k_shadow/`에 대한 read-only open |
| 허용 동작 | SELECT, schema/hash read, missing-DB fallback 확인, read-only write rejection 확인 |

### 1.2 Out of scope

| 분류 | 제외 항목 | 이유 |
| --- | --- | --- |
| 운영 DB | 운영 `_database/` 변경 | V3K cutover 전까지 금지 |
| runtime 연결 | Kiwoom 주문·청산·실시간 receiver/trader 변경 | Phase B는 검증 단계이며 live 연결 단계가 아님 |
| feature flag ON | 실제 설정/GUI에서 V3K flag 활성화 | Phase C 이후 별도 승인 필요 |
| LS 의존성 | LS증권 API, `restapi_ls`, LS 계좌/주문 전제 | V3K 정의 위반 |
| DB cutover | shadow DB를 운영 DB로 승격 | Phase G 이후 별도 승인 또는 cutover phase 필요 |
| 영구 데이터 insert | 운영 또는 committed DB에 sentinel row 저장 | `.db` commit 금지 및 운영 격리 정책 위반 |

---

## 2. Phase A에서 상속되는 lifetime invariant

Phase B는 Phase A plan의 lifetime invariant를 깨지 않는다.

| # | invariant | Phase B 적용 방식 |
| --- | --- | --- |
| L1 | `schema_hash`는 PRAGMA 등가 입력 기반 sha256 64자 | fixture schema도 Phase A helper로 생성하거나 manifest hash와 비교한다. |
| L2 | `init_v3k_shadow_db.py --dry-run` 외부 동작 보존 | Phase B에서 `init_v3k_shadow_db.py`의 CLI surface를 변경하지 않는다. |
| L3 | sentinel prefix = `_v3kshadow_smokeA_` | 실제 row fixture가 필요하면 temp fixture DB에서만 이 prefix를 사용한다. |
| L4 | shadow dir = `_database_v3k_shadow/` | 실제 shadow dir은 read-only 대상으로만 사용한다. |
| L5 | feature flag default-OFF | 검증 row를 넣더라도 feature flag는 request-local dict로만 켜고 DB flag row는 넣지 않는다. |
| L6 | `last_update < backtest_date` | Phase B acceptance에서 before/equal/after row 필터를 반드시 확인한다. |
| L7 | LS Securities 직접 의존 금지 | 신규 import/문서/fixture에 LS API 전제를 넣지 않는다. |
| L8 | Kiwoom live/order/liquidation runtime 변경 금지 | Phase B 변경 파일 whitelist로 차단한다. |
| L9 | CLI surface 보존 | Phase B 신규 smoke는 별도 script로 추가하고 기존 Phase A CLI를 깨지 않는다. |

---

## 3. RALPLAN-DR 요약

### 3.1 Principles

| # | 원칙 | 설명 |
| --- | --- | --- |
| P1 | read-only 우선 | 실제 `_database_v3k_shadow/`는 읽기 전용 확인 대상으로만 사용한다. |
| P2 | fixture는 임시·격리 | row-read 검증용 데이터는 temp/ignored fixture DB에만 넣는다. |
| P3 | adapter 계약을 검증 | 구현 목적은 `V3KLearningDataAdapter`의 `?mode=ro`, flag, leakage 계약을 증명하는 것이다. |
| P4 | runtime 미접속 | Phase B에서 backtest/live order path에 연결하지 않는다. |
| P5 | 증거 기반 종료 | before/after hash·row count·git status·audit script 결과가 있어야 완료로 본다. |

### 3.2 Decision drivers

| 우선순위 | Driver | 의미 |
| --- | --- | --- |
| 1 | 운영 DB 무변경 | 어떤 검증도 운영 `_database/`를 쓰면 안 된다. |
| 2 | 실제 읽기 경로 증명 | 단순 missing-DB smoke가 아니라 row가 있을 때 adapter가 SELECT 결과를 반환하는지 확인해야 한다. |
| 3 | 후속 Phase C–G 비용 최소화 | Phase B가 read-only 경계를 확정해야 GUI/runtime 연결 전 위험이 낮아진다. |

### 3.3 Viable options

#### Option A — 실제 `_database_v3k_shadow/`에 sentinel row를 INSERT해서 검증

- 장점: 실제 shadow DB에서 row-read까지 검증 가능.
- 단점: Phase A의 DDL-only/default-OFF 성격을 흔들고, read-only 검증 단계에서 write가 발생한다.
- 판정: **기각**. Phase B의 핵심은 read-only 검증이므로 실제 shadow DB에 검증 row를 쓰지 않는다.

#### Option B — 실제 `_database_v3k_shadow/`는 read-only health/hash만 확인하고, row-read는 temp fixture copy에서 검증

- 장점: 실제 shadow DB 무변경, adapter row-read 검증, leakage 검증, read-only URI 검증을 모두 만족한다.
- 단점: “실제 shadow DB의 실제 데이터”를 읽는 것은 아직 아니다. 다만 Phase A shadow가 DDL-only라 현재 실제 학습 row가 없으므로 합리적이다.
- 판정: **선택안**.

#### Option C — 기존 missing-DB smoke만 유지

- 장점: 변경이 거의 없다.
- 단점: row가 존재할 때 adapter가 올바르게 읽는지, `last_update < backtest_date`가 동작하는지, read-only URI가 쓰기를 막는지 검증하지 못한다.
- 판정: **기각**. Phase B 목표를 충족하지 못한다.

### 3.4 ADR

| 항목 | 결정 |
| --- | --- |
| Decision | Phase B는 Option B로 진행한다. |
| Why | 실제 shadow DB는 Phase A 산출물로 보존하고, row-read 검증은 temp fixture DB에서 수행해야 read-only 원칙과 기능 검증을 동시에 만족한다. |
| Consequence | Phase B 구현 시 신규 smoke/test는 temp fixture DB를 만들 수 있지만, `_database_v3k_shadow/`와 `_database/`에는 INSERT/UPDATE/DELETE를 하지 않는다. |
| Follow-up | Phase C 전, Phase B 결과를 `docs/update_log/`와 `docs/CARRY_FORWARD_REGISTRY.md`에 기록한다. |

---

## 4. Phase B 상세 실행 계획

### B00. 실행 전 preflight

| 항목 | 명령/검증 | 완료 조건 |
| --- | --- | --- |
| branch 확인 | `git branch --show-current` | `STOM_Version_2U_C` |
| dirty 상태 확인 | `git status --short --branch` | tracked 변경은 계획된 파일만 |
| Python 확인 | `python --version` | Python 3.13.x 우선, pytest 필요 시 py3.11 fallback 가능 |
| Phase A manifest 확인 | `.omx/reports/v3k-shadow-manifest.json` read | `dbs` 7개, template 13개 |
| shadow DB health | `python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.phase-b.before.json --strict` | ok=true |

### B01. 신규 read-only fixture smoke 설계

후속 구현에서는 다음 신규 script를 우선 후보로 둔다.

```text
scripts/smoke_v3k_learning_db_readonly_existing.py
```

필수 속성:

1. `tempfile.TemporaryDirectory()` 또는 `.omx/tmp/v3k_phase_b_fixture/` 아래에 fixture DB를 생성한다.
2. fixture schema는 `scripts/init_v3k_shadow_db.py`의 schema dict/helper를 재사용한다.
3. fixture row는 `_v3kshadow_smokeA_` prefix를 사용한다.
4. row 생성이 끝난 뒤 adapter 호출은 `V3KLearningDataAdapter(base_dir=<fixture_dir>)`로 수행한다.
5. adapter 내부 open은 기존 코드처럼 `?mode=ro`만 사용해야 한다.
6. 검증 종료 후 temp fixture는 삭제되거나 `.gitignore`로 추적되지 않아야 한다.

### B02. adapter row-read acceptance

최소 검증 행렬:

| 케이스 | 기대 결과 |
| --- | --- |
| flag OFF + DB 존재 | rows 없음, diagnostic = disabled |
| flag ON + DB 없음 | rows 없음, diagnostic = missing DB |
| flag ON + DB 존재 + `last_update < backtest_date` | 해당 row 반환 |
| flag ON + DB 존재 + `last_update == backtest_date` | row 미반환 |
| flag ON + DB 존재 + `last_update > backtest_date` | row 미반환 |
| limit=1 | 최신 eligible row 1개만 반환 |
| candle_pattern + tick 요청 | table/contract 정책에 어긋나지 않는지 별도 판단 또는 skip reason 명시 |

### B03. SQLite read-only 강제 확인

후속 구현은 adapter가 직접 write API를 제공하지 않더라도, 같은 fixture DB를 `?mode=ro`로 연 연결에서 write가 실패하는지 확인해야 한다.

| 검증 | 기대 결과 |
| --- | --- |
| `sqlite3.connect(f'{db.as_uri()}?mode=ro', uri=True)` | 성공 |
| 위 연결에서 `INSERT` 시도 | `sqlite3.OperationalError: attempt to write a readonly database` 또는 동등 오류 |
| adapter 실행 후 fixture row count | pre/post 동일 |
| 실제 `_database_v3k_shadow/v3k_meta.db` row count | pre/post 동일 |

### B04. 실제 Phase A shadow DB read-only health/hash 확인

실제 `_database_v3k_shadow/`에 대해서는 다음만 허용한다.

1. `scripts/v3k_db_health.py --read-only --strict`
2. `v3k_schema_manifest` row count 및 hash read
3. manifest JSON hash와 DB manifest hash 비교
4. `v3k_feature_flags`와 `v3k_listed_shares` row count가 0인지 확인

금지:

- 실제 `_database_v3k_shadow/`에 fixture/sentinel row INSERT
- 실제 `_database_v3k_shadow/`를 operational DB로 rename/copy
- `_database/` 접근 또는 write

### B05. 변경 파일 whitelist

Phase B 구현에서 허용되는 변경 파일은 다음으로 제한한다.

| 경로 | 유형 | 비고 |
| --- | --- | --- |
| `scripts/smoke_v3k_learning_db_readonly_existing.py` | 신규 후보 | row-read/read-only 검증 script |
| `tests/unit/test_v3k_learning_db_readonly.py` | 선택 신규 | script가 커지면 unit test로 분리 |
| `docs/update_log/2026-05-11_v3k_phase_b_readonly_learning_db.md` | 신규 | 구현 후 작업 기록 |
| `docs/CARRY_FORWARD_REGISTRY.md` | 수정 | 구현 완료 후 `V3K-PHASE-B` 기록 |
| `.gitignore` | 조건부 수정 | `.omx/tmp/v3k_phase_b_fixture/` 등 fixture artifact 누설 방지 필요 시 |

다음 경로 변경은 commit 전 차단한다.

```text
_database/
_database_v3k_shadow/*.db
trade/
receiver/
ui/
utility/setting.py
utility/kiwoom.py
restapi_ls*
```

---

## 5. 검증 명령 세트

Phase B 구현 완료 후 최소 검증은 다음 순서로 실행한다.

```powershell
Set-Location C:/System_Trading/STOM/STOM_V.wt-dev

# V01 branch/lane
git branch --show-current

# V02 compile
python -m py_compile strategy/v3k_analyzer_adapter.py scripts/init_v3k_shadow_db.py scripts/v3k_db_health.py scripts/smoke_v3k_learning_db_readonly_existing.py

# V03 Phase A shadow health before
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.phase-b.before.json --strict

# V04 Phase B read-only fixture smoke
python scripts/smoke_v3k_learning_db_readonly_existing.py

# V05 Phase A shadow health after
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.phase-b.after.json --strict

# V06 existing V3K smoke 유지
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_settings_surface.py

# V07 audit closure 유지
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py

# V08 DB/ephemeral 파일 누설 차단
git status --short -- _database/ _database_v3k_shadow/ *.db
git diff --cached --name-only | Select-String -Pattern '(^|/)_(database|database_v3k_shadow)|\.db$' -Quiet; if ($?) { throw 'DB artifact staged' }
```

> 주의: `verify_release_sync.py`는 root official lane의 release preflight 성격이다. `STOM_Version_2U_C`에서는 존재하지 않을 수 있으므로 Phase B 구현 검증은 `verify_nonrelease_sync.py`를 기본으로 한다.

---

## 6. 위험 매트릭스

| ID | 위험 | 자동 탐지 | 차단/복구 |
| --- | --- | --- | --- |
| R1 | 운영 `_database/` write | `git status --short -- _database/` | 즉시 중단, 변경 폐기, 원인 문서화 |
| R2 | 실제 `_database_v3k_shadow/`에 fixture row 삽입 | before/after row count 비교 | fixture는 temp DB로 이동 |
| R3 | adapter가 read-write로 DB open | `?mode=ro` grep + write rejection smoke | `sqlite3.connect(...?mode=ro, uri=True)` 유지 |
| R4 | leakage 규칙 파괴 | equal/after `last_update` row 반환 여부 | `last_update < backtest_date` 쿼리 유지 |
| R5 | LS 직접 의존성 추가 | audit script, grep `restapi_ls|LS증권` | import/전제 제거 |
| R6 | Kiwoom runtime 변경 | diff whitelist 검사 | Phase C/E/F 전까지 차단 |
| R7 | feature flag default-OFF 파괴 | flag OFF smoke | DB flag row 대신 request-local flag 사용 |
| R8 | fixture artifact commit 누설 | git status/check-ignore | `.gitignore` 보강 또는 tempdir 사용 |

---

## 7. 완료 기준

Phase B는 다음을 모두 만족할 때 완료로 인정한다.

- [ ] 계획 문서가 commit되어 후속 구현자가 목적·제약·검증을 단독으로 이해할 수 있다.
- [ ] 신규 read-only smoke/test가 row-read, leakage, missing DB, flag OFF, write rejection을 검증한다.
- [ ] 실제 `_database_v3k_shadow/`는 read-only health/hash 확인만 수행하며 row count가 pre/post 동일하다.
- [ ] 운영 `_database/` 변경이 없다.
- [ ] Kiwoom 주문·청산·live runtime 변경이 없다.
- [ ] LS증권 직접 의존성이 없다.
- [ ] 기존 V3K smoke/audit가 모두 통과한다.
- [ ] `docs/update_log/`와 `docs/CARRY_FORWARD_REGISTRY.md`에 Phase B 완료 기록이 남는다.

---

## 8. 후속 실행 추천 명령

본 계획 문서 commit 이후, Phase B 구현을 시작할 때 추천하는 OMX 실행 프롬프트는 다음이다.

```powershell
omx ralph "force: V3K Phase B read-only learning DB 검증을 docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md에 따라 구현한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. 실제 _database_v3k_shadow는 read-only health/hash 확인만 수행하고 row-read 검증은 temp fixture DB에서 수행한다. 운영 _database, Kiwoom 주문/청산/live runtime, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 docs/update_log와 CARRY_FORWARD_REGISTRY에 Phase B 결과를 기록하고 py_compile, smoke suite, audit_v3k_verify_1a, audit_v3k_verify_1b_closure, verify_nonrelease_sync를 통과시킨다."
```

만약 `omx ralph`가 `.omx/prd.json` gate로 멈추면, 같은 프롬프트를 Codex 세션에 직접 붙여 넣고 본 계획의 V01–V08 검증 순서대로 진행한다.

---

## 9. 현재 페이지/전체 페이지 진행률 정본

| Page | 이름 | 상태 | 진행률 |
| ---: | --- | --- | ---: |
| 001 | V3/V3U/2U_C 전략 kick-off 및 워크트리 정리 | 완료 | 100% |
| 002 | V3 공식 ingress 및 3U pyd-free 전환 | 완료 | 100% |
| 003 | 2U_C V3K 목표 재정의와 문서 정본화 | 완료 | 100% |
| 004 | V3K DESIGN-0/1/1B DB·adapter 설계 | 완료 | 100% |
| 005 | V3K analyzer/backtest/realtime 안전 후보 반영 | 완료 | 100% |
| 006 | 2U_C V3K 감사·의도적 미완료 항목 재평가 | 완료 | 100% |
| 007 | commit history compact 및 lane 정리 | 완료 | 100% |
| 008 | 활성 5개 worktree 재감사와 Python 3.13 재검증 | 완료 | 100% |
| 009 | Phase A shadow DB rehearsal | 완료 | 100% |
| 010 | Phase B read-only learning DB 검증 | **현재 계획 완료 / 구현 대기** | 20% |
| 011 | Phase C–G GUI/runtime/cutover 전 단계별 실행 | 대기 | 0% |

전체 기준 현재 위치:

```text
[█████████░░] 9.2 / 11 pages = 약 83.6%
```

Phase B 내부 기준 현재 위치:

```text
[██░░░░░░░░] 1 / 5 steps = 20%
```

Phase B 내부 단계:

| Step | 이름 | 상태 |
| ---: | --- | --- |
| B1 | read-only 검증 계획 작성 | 완료 |
| B2 | fixture smoke/test 구현 | 대기 |
| B3 | 실제 shadow DB read-only health/hash 검증 | 대기 |
| B4 | smoke/audit 전체 회귀 | 대기 |
| B5 | update_log/registry 기록 및 commit | 대기 |