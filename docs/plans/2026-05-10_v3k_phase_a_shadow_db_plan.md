> **ralplan 합의 이력**
> - iteration 1: Architect `ITERATE_WITH_NOTES` (3 권고 + P2) → Critic `ITERATE` (9 Required Revisions)
> - iteration 2: Planner v2 (9 흡수) → Architect `APPROVE` (4 cosmetic memo) → Critic `ITERATE` (3 Required Revisions)
> - iteration 3: Planner v3 (3 흡수 + 3 Optional) → Architect `APPROVE` (regression 없음) → Critic **APPROVE**
> - 합의 모드: short deliberation. 합의 종결 시점에 본 문서를 `docs/plans/`에 정본화한다.
> - 출처 audit: `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` §8 Phase A.

# V3K Phase A — Shadow DB Rehearsal 단독 상세 실행 계획 v3

작성일: 2026-05-10 KST
대상 root lane: `STOM_Version_2`
최종 구현 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
선행 문서:
- `docs/update_log/2026-05-09_v3k_design_1_db_learning_design.md`
- `docs/update_log/2026-05-09_v3k_design_1b_readonly_scripts.md`
- `docs/superpowers/specs/2026-05-09-v3k-db-learning-migration-spec.md`

본 v3 계획은 ralplan iteration 3의 Planner 산출물이다. v2 → Critic iteration 2의 3개 Required Revisions(G.1 commit boundary 정정, T01 회귀 3종 입력 layer 명확화, task별 worktree/lane 표 추가)와 3개 Optional Improvements(O1 V08b row count, O2 EXPECTED_DBS 라벨 비교, O3 V05 task 단계별 차등)를 흡수하여 v2를 부분 수정한다. v2의 보존 영역(A.1 Principles, A.2 Drivers, A.3 Options, B.1 Lifetime Invariants 8종, B.2 Phase A 한정 5종, E R1–R10, F rollback 3종, H commit sample 6종, I ADR 요지, J 핵심 설계 질문)은 재현하면서 변경 부위만 정정한다.

---

## 0. V3K 전체 미션과 Phase A–G 로드맵 (큰 그림 보존)

> 본 절은 사용자 명시 요청에 따라 amendment commit에서 신설되었다. Phase A 단독 상세 계획을 미래의 작업자가 단독으로 읽더라도 V3K 전체 목적과 본 plan의 위치를 잃지 않도록 박는다. §0–§0.3은 `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` §0 TL;DR과 §6·§8 정본을 본 plan 안에 재현한 것이다.

### 0.1 V3K 미션 statement

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
단, LS Securities REST/TR/REAL 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface(init_v3k_shadow_db.py / backtest CLI / realtime CLI / 전체 STOM CLI 진입점)의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지하고, 명시적 사용자 승인 후에만 ON 전환을 허용한다.
```

### 0.2 Phase A–G 전체 로드맵 (audit §8 정본 재현)

| Phase | 목표 1줄 | 본 plan scope | 후속 plan 작성 의무 | 의존 입력 |
| --- | --- | --- | --- | --- |
| **A** | shadow DB rehearsal — `_database_v3k_shadow/` 생성 + schema_hash invariant 고정 | **본 plan (V3K-PA)** | — | DESIGN-1, DESIGN-1B, migration spec |
| B | read-only learning DB 검증 — `V3KLearningDataAdapter`의 `?mode=ro` smoke | scope 외 | `docs/plans/<YYYY-MM-DD>_v3k_phase_b_*.md` 별도 plan 필수 | Phase A 산출물(manifest, schema_hash, sentinel L3) |
| C | GUI/settings 연결 — `v3k_settings_surface.py`를 MainWindow/pyd wrapper에 노출 (default-OFF 유지) | scope 외 | 별도 plan 필수 | Phase B 산출물 |
| D | formula/global runtime 연결 — `V3K_` prefix callable만 runtime globals에 제한 노출 | scope 외 | 별도 plan 필수 | Phase B 산출물 |
| E | live Kiwoom dry-run hook — KHOPENAPI 호환 환경에서 preload diagnostic only | scope 외 | 별도 plan 필수 | Phase C·D 산출물 |
| F | analyzer output 전략 반영 — backtest 회귀 + rollback flag로 전략/주문/청산 판단에 통합 | scope 외 | 별도 plan 필수 (고위험) | Phase D·E 산출물 |
| G | V3 microstructure engine replacement — adapter가 아닌 engine 자체 이식/재구현 | scope 외 | 별도 plan 필수 (대형, G-1/G-2/G-3 분해 권장) | Phase F 산출물 |

> 본 plan은 **Phase A 한정**이다. Phase B 이후의 어떤 결정도 본 plan에서 정하지 않는다. 후속 plan은 각각 ralplan 합의 또는 동등 수준의 사전 검토를 거쳐야 한다(§K 참조).

### 0.3 본 plan의 scope 경계

| In scope (본 plan에서 다룬다) | Out of scope (본 plan에서 다루지 않는다) |
| --- | --- |
| `apply_v3k_shadow_db.py` 신규 작성 | Phase B의 `V3KLearningDataAdapter` read 동작 변경 |
| `compute_schema_hash` 추가 + manifest stamp | sentinel `_v3kshadow_smokeA_` row의 INSERT (Phase B 이후) |
| `_database_v3k_shadow/` 디렉터리 + 7 DB 생성 (DDL only) | DB 데이터 cutover, 운영 `_database/` 변경 |
| `.gitignore` ephemeral 분리 + branch 가드 환경 변수 | GUI flag 연결, runtime hook 연결 |
| `V3K-PHASE-A` carry-forward registry section | `V3K-PHASE-B`~`V3K-PHASE-G` registry section |
| 회귀 테스트 3종, V01–V12 검증 자동화 | live Kiwoom runtime 호출, LS broker-neutral 설계 |
| Phase A 한정 lane 정책 (V05–V09 = 2U_C 한정) | Phase B 이후의 lane 정책 재검토 |

---

## A. RALPLAN-DR 요약

### A.1 Principles (5)

| # | Principle | 의도 |
| --- | --- | --- |
| P1 | 운영 `_database/` 무변경 보장 | shadow 도입이 V2/Kiwoom runtime을 절대 흔들지 않는다 |
| P2 | DESIGN-1B 외부 동작 보존 | `init_v3k_shadow_db.py` CLI/manifest/dry-run 강제는 lifetime invariant |
| P3 | Default-OFF feature flag 무결성 | apply 단계는 DDL만, sentinel/data row는 Phase B 이후 책임 |
| P4 | 산출물 의도 분리 (commit vs ephemeral) | manifest/registry/script만 commit; health JSON/diff markdown은 ephemeral |
| P5 | 자동 검증 가능성 (PowerShell 명령으로 PASS/FAIL 판정) | 모든 task 완료 조건과 위험 detection은 명령으로 재현 가능해야 한다 |

### A.2 Decision Drivers (Top 3)

1. **Phase B–G 변경 비용 최소화**: schema_hash, sentinel naming, default-OFF 등 Phase A에서 굳히면 후속 phase에서 마이그레이션이 필요한 결정은 lifetime invariant로 분리한다.
2. **CLAUDE.md 정책 정합성**: 한국어 commit 본문, PowerShell syntax, `python scripts/verify_release_sync.py` 마지막 단계, `_database/`/`*.db` 미생성, V3K-PHASE-A registry 섹션.
3. **Architect/Critic 4 risk 흡수**: (a) schema_hash 비결정성, (b) branch 가드 경로 정규화, (c) sentinel 충돌, (d) DDL/data 분리 — 4개를 R1–R10 3-tuple에 명시 매핑한다.

### A.3 Viable Options

#### Option 1 — Steelman: 단일 `init_v3k_shadow_db.py` 확장
신규 파일 없이 기존 script에 `--apply` 모드를 추가하여 dry-run/apply를 분기.

- 장점: 산출물 1개 감소, 신규 import 경로 없음, schema 정의 단일 출처 강제됨.
- 단점: DESIGN-1B의 "dry-run 강제(--dry-run required)" 외부 동작이 깨질 위험. CLI 공개 surface가 변경되어 lifetime invariant P2와 충돌. apply 경로 버그가 dry-run 경로까지 전염될 수 있음.
- 평가: 단일 출처 장점은 Option 2-hybrid의 직접 import로 동등 확보 가능. P2 위반 위험으로 **기각**.

#### Option 2-hybrid — 별도 `apply_v3k_shadow_db.py` + 직접 import (선택안)
신규 `scripts/apply_v3k_shadow_db.py`가 `init_v3k_shadow_db.py`에서 `LEARNING_DBS`/`META_DBS`/`create_table_sql`을 직접 import. schema 추출 모듈(`_v3k_shadow_schema.py`)은 만들지 않음.

- 장점: DESIGN-1B 외부 동작 100% 보존(P2). schema 정의 단일 출처(`init_v3k_shadow_db.py`)를 유지하면서 신규 surface는 apply만 책임. 산출물 신규 4 → 3으로 축소(R2 흡수).
- 단점: apply 스크립트가 init 모듈에 의존하는 import 방향. 단, init은 stdlib만 사용하므로 import 부작용 없음.
- 평가: P1·P2·P4 모두 충족. **선택**.

#### Option 4 — DDL을 `.sql` 파일 + `executescript` (5줄 평가, fair alternatives)
schema를 `scripts/v3k_shadow_ddl.sql`로 추출하여 `apply_v3k_shadow_db.py`가 `executescript()`로 적용.

- 장점: schema가 SQL 자체로 표현되어 PRAGMA 기반 hash와 직접 비교 가능, diff 도구 호환성 우수.
- 단점: `init_v3k_shadow_db.py`가 Python dict로 schema를 보유한다는 lifetime invariant 위반. dual-source 동기화 부담 신규 발생. 7개 DB × placeholder 치환 로직(`{strategy_gubun}`, `{tick|min}`)을 SQL 내에서 표현 불가.
- 평가: 단일 출처 원칙 위배 + placeholder 처리 곤란. **기각**.

#### Option 3 (참고용) — pytest 기반 contract test로 대체 (R2 회귀 테스트 위치)
schema 회귀 테스트를 별도 contract test로 분리. → R1 회귀 3종에 흡수되어 별도 옵션으로 분리할 필요 없음.

### A.4 선택안: Option 2-hybrid 사유

| Driver | 충족 |
| --- | --- |
| Phase B 변경 비용 최소화 | schema_hash 정의 + sentinel naming + default-OFF가 lifetime invariant로 고정 |
| CLAUDE.md 정합성 | manifest/registry만 commit, ephemeral 4종은 `.gitignore`로 제외 |
| Risk 흡수 | R3(branch 가드 경로 정규화), R4(sentinel 충돌), R5(default-OFF DDL/data 분리), R8(schema_hash 비결정성)에 직접 매핑 |
| 외부 동작 보존 | DESIGN-1B `--dry-run` required, manifest 포맷, JSON 출력 위치 모두 무변경 |

---

## B. V3K Lifetime Invariant 분류

### B.1 Lifetime Invariant — Phase B–G 변경 금지 (8 항목)

| # | Invariant | 근거 |
| --- | --- | --- |
| L1 | `schema_hash` = `PRAGMA table_info` 등가 입력 `(cid, name, type, notnull, dflt_value, pk)` tuple의 정렬·직렬화 후 `sha256` hex 64자 | 동일 schema는 동일 hash, 컬럼 순서/공백 변경에도 hash 불변 |
| L2 | `init_v3k_shadow_db.py`의 외부 동작(CLI 인자 `--dry-run` required, manifest JSON 포맷, `creates_databases=False`, `creates_directories=False`) | DESIGN-1B 종료 판정의 핵심 |
| L3 | sentinel naming = `_v3kshadow_smokeA_` 접두 | Phase B 이후 prefix 충돌 차단 |
| L4 | shadow 디렉터리 = `_database_v3k_shadow/`, `_database/`와 형제 위치 | 운영 DB와 물리적·논리적 분리 |
| L5 | feature flag default-OFF 정책 (`v3k_feature_flags.enabled = 0`) | Phase B 이후 ON 전환은 명시적 INSERT/UPDATE 필요 |
| L6 | `last_update < backtest_date` 학습 데이터 사용 규칙 | leakage 방지 |
| L7 | LS Securities 직접 의존 금지 | V3K = V3 features + Kiwoom retained 정의 |
| L8 | 운영 `_database/`, `*.db` 파일 git commit 금지 | `.gitignore` 정책 |
| L9 | STOM CLI surface 보존 — `init_v3k_shadow_db.py` CLI 외에 backtest CLI, realtime CLI, 전체 STOM CLI 진입점의 외부 동작 무변경 | V2.67 CLI 통합 이력 보호, V3K 미션 "CLI surface 유지" 조항(§0.1), Kiwoom retained 조건의 일부 |

### B.2 Phase A 한정 결정 — Phase B에서 자유 변경 (5 항목)

| # | Phase A 결정 | Phase B 이후 변경 가능성 |
| --- | --- | --- |
| A1 | `apply_v3k_shadow_db.py` script 위치 (`scripts/`) | 다른 위치(`scripts/v3k/`)로 이동 가능 |
| A2 | health.before/after JSON 파일명 명명 규칙 | runbook 변경 시 자유 |
| A3 | `--strategy-gubun` CLI 인자 명세 ("Phase A 한정" docstring 명시) | Phase B에서 다중 strategy gubun 지원 시 시그니처 변경 가능 |
| A4 | apply 시 stdout 로그 형식 | 자유 |
| A5 | rehearsal smoke 시나리오 (3개 시나리오 자체) | Phase B 이후 검증 매트릭스 변경 자유 |

---

## C. 상세 실행 계획 (T01–T07)

> v1의 T01(`_v3k_shadow_schema.py` 추출)을 R2에 따라 제거하고 T01–T07로 재번호한다.

### C.0 Task별 실행/commit lane (Rev3 신설)

worktree 매핑:
- `C:/System_Trading/STOM/STOM_V` = `STOM_Version_2` branch (V2 root, release-ingress)
- `C:/System_Trading/STOM/STOM_V.wt-dev` = `STOM_Version_2U_C` branch (구현 lane)

| Task | 실행 lane(s) | commit lane | 사유 |
| --- | --- | --- | --- |
| T01 (schema_hash + 회귀 3종) | 양쪽 (검증) | `STOM_Version_2U_C` | 코드 수정은 2U_C, dry-run·pytest 검증은 V2 root에서도 동일하게 PASS해야 함 |
| T02 (apply 신규) | `STOM_Version_2U_C`만 | `STOM_Version_2U_C` | apply 자체는 2U_C 한정. branch 가드가 V2 root 실행 차단 (R3) |
| T03 (ADR + docstring) | `STOM_Version_2U_C` | `STOM_Version_2U_C` | docs는 구현 lane |
| T04 (`.gitignore` + 환경 변수) | `STOM_Version_2U_C` | `STOM_Version_2U_C` | 정책 변경은 구현 lane |
| T05 (registry `## V3K-PHASE-A`) | `STOM_Version_2U_C` | `STOM_Version_2U_C` | registry는 구현 lane |
| T06 (R1–R10 위험표 검증) | 양쪽 | `STOM_Version_2U_C` | dry-run 검증은 양쪽, 위험표 commit은 2U_C |
| T07 (통합 V01–V12) | apply 단계(V05–V09)만 2U_C, 그 외 양쪽 | n/a (검증 task, commit 산출물 0건) | V05 단계별 가드 (O3 흡수) |

### T01. `init_v3k_shadow_db.py`에 `schema_hash` 계산 함수 추가 + 회귀 테스트 3종

- 작업 ID: `V3K-PA-T01`
- 목표: L1 invariant `schema_hash` 정의를 코드로 고정하고 회귀 테스트로 보호.
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py` (수정)
  - `C:/System_Trading/STOM/STOM_V/tests/unit/test_v3k_shadow_schema_hash.py` (신규)
- 변경 의도:
  - `init_v3k_shadow_db.py`에 `compute_schema_hash(table_name, table) -> str` 함수 추가. 입력은 PRAGMA table_info 등가 정보 (Python dict 형태의 columns 정의), 내부에서 `(cid, name, type, notnull, dflt_value, pk)` tuple로 sorted 직렬화 후 sha256 hex 64자 산출.
  - manifest의 `tables[table_name]`에 `schema_hash` 필드 stamp.
- 회귀 테스트 3종 (Rev2 — 입력 layer는 모두 **Python dict**, PRAGMA-등가 입력 기준):
  - **(a) 동일성 (idempotency)**: 같은 dict 입력으로 `compute_schema_hash`를 두 번 호출 → 동일 hash.
  - **(b) 키 순서 불변 (key order invariance)**: columns 정의의 key 순서만 다른 의미적으로 동일한 dict 두 개 → 동일 hash. 내부 sorted tuple 강제로 보장.
  - **(c) `dflt_value` SQL 공백 불변**: column 정의의 `dflt_value` SQL 표현에서 공백/줄바꿈만 다른 dict 두 개 → 동일 hash. PRAGMA가 normalize한 결과로 동등 판정 (예: `DEFAULT 0` vs `DEFAULT  0` vs `DEFAULT\n0`).
- 입력 layer 명시: 본 회귀 3종은 모두 `compute_schema_hash`의 dict 입력에 적용된다. SQL string 입력은 본 함수의 surface가 아니며, SQL → dict 변환은 sqlite의 `PRAGMA table_info` 결과를 모방한다.
- 완료 조건 (PASS/FAIL 자동 명령):
  ```powershell
  python -m py_compile C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py
  python -m pytest C:/System_Trading/STOM/STOM_V/tests/unit/test_v3k_shadow_schema_hash.py -q
  ```
  PASS: exit 0, manifest JSON에 모든 table에 `schema_hash` 포함.
- 의존하는 선행 작업: 없음 (T01이 Phase A의 출발점).

### T02. `apply_v3k_shadow_db.py` 신규 작성 — DDL 전용, default-OFF

- 작업 ID: `V3K-PA-T02`
- 목표: `_database_v3k_shadow/` 디렉터리 + 7개 SQLite 파일을 DDL만으로 생성. sentinel/data row INSERT 금지.
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/scripts/apply_v3k_shadow_db.py` (신규)
- 변경 의도:
  - `from init_v3k_shadow_db import LEARNING_DBS, META_DBS, create_table_sql, compute_schema_hash` 직접 import.
  - argparse: `--apply` (required), `--shadow-dir` (default `_database_v3k_shadow`), `--strategy-gubun` (Phase A 한정 docstring 명시), `--allow-existing` (idempotency 옵션).
  - branch 가드: `Path.resolve() + relative_to` 패턴을 `init_v3k_shadow_db.ensure_report_path` 패턴 그대로 재사용 (R3 흡수). 환경 변수 `V3K_PHASE_A_BRANCH_BYPASS=1` 우회 허용 (CI/이중 worktree 대응).
  - 각 DB 파일에 `executescript(create_table_sql)` 적용. **`v3k_feature_flags`, `v3k_listed_shares`에 INSERT 금지**.
  - `v3k_meta.db`의 `v3k_schema_manifest`에 (db_name, table_name, schema_hash) row만 stamp (이는 manifest이지 feature/data 아님).
- 완료 조건:
  ```powershell
  python -m py_compile C:/System_Trading/STOM/STOM_V/scripts/apply_v3k_shadow_db.py
  python -c "import sqlite3, pathlib; p=pathlib.Path('C:/System_Trading/STOM/STOM_V/_database_v3k_shadow/v3k_meta.db'); c=sqlite3.connect(f'{p.as_uri()}?mode=ro', uri=True); print(c.execute(\"SELECT COUNT(*) FROM v3k_feature_flags\").fetchone()[0])"
  ```
  PASS: feature_flags row count = 0 (R5/default-OFF 자동검증).
- 의존하는 선행 작업: T01.

### T03. v1 R2 후속 — `_v3k_shadow_schema.py` 추출 보류 명시 + ADR 기록

- 작업 ID: `V3K-PA-T03`
- 목표: schema 단일 출처는 `init_v3k_shadow_db.py`이며, 추출은 Phase A에서 보류한다는 결정을 ADR과 docstring으로 고정.
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md` (신규, ADR 본문 포함)
  - `C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py`의 module docstring 갱신 (수정 — T01과 합쳐도 무방)
- 변경 의도:
  - ADR 본문(I 섹션)에 "추출 보류 — schema dict는 Phase A 동안 init_v3k_shadow_db에 잔류, Phase B 결정에 따라 추출 가능" 기록.
  - module docstring에 "Phase A: 본 모듈은 LEARNING_DBS/META_DBS/create_table_sql/compute_schema_hash의 단일 출처이며, apply_v3k_shadow_db는 직접 import한다" 추가.
- 완료 조건:
  ```powershell
  Test-Path C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md
  Select-String -Path C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py -Pattern "Phase A: .* 단일 출처"
  ```
  PASS: 둘 다 True/매치 1건.
- 의존하는 선행 작업: T01, T02.

### T04. ephemeral 산출물 분리 + `.gitignore` 갱신 + branch 가드 우회 환경 변수

- 작업 ID: `V3K-PA-T04`
- 목표: health.before/after JSON과 diff markdown을 git에서 분리(R3 흡수). manifest/script/registry만 commit.
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/.gitignore` (수정 — `.omx/reports/v3k-db-health.*.json`, `.omx/reports/v3k-phase-a-diff.*.md` 추가)
  - `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md` (수정 — runbook 섹션에 ephemeral 첨부 정책 명시)
- 변경 의도:
  - `.gitignore`에 ephemeral 패턴 4종 추가 + 코멘트로 "Phase A rehearsal artefacts; attach to PR description, do not commit" 명시.
  - **manifest 예외 정책 명시 (Rev1 흡수)**: `.omx/reports/v3k-shadow-manifest.json`은 ephemeral 정책의 명시적 예외이며 commit 대상이다. 사유는 schema 정의의 audit trail로서 Phase B 이후 schema_hash 회귀 비교의 baseline 역할을 하기 때문이다. 본 정책은 H.4 commit message 본문 한 줄에 명시한다.
  - branch 가드 우회는 `V3K_PHASE_A_BRANCH_BYPASS=1` 환경 변수로 통일.
- 완료 조건:
  ```powershell
  git -C C:/System_Trading/STOM/STOM_V check-ignore .omx/reports/v3k-db-health.before.json
  git -C C:/System_Trading/STOM/STOM_V check-ignore .omx/reports/v3k-phase-a-diff.md
  ```
  PASS: 두 명령 모두 exit 0 + 경로 출력.
- 의존하는 선행 작업: T02.

### T05. `docs/CARRY_FORWARD_REGISTRY.md` `## V3K-PHASE-A` 섹션 추가

- 작업 ID: `V3K-PA-T05`
- 목표: V3K-DESIGN-1B 패턴을 따라 V3K-PHASE-A 항목을 registry에 등록 (R6 흡수).
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md` (수정)
- 변경 의도:
  - `## V3K-DESIGN-2`(파일 마지막) 다음에 `## V3K-PHASE-A: shadow DB rehearsal` 섹션 추가.
  - 기재 항목: Date, Root commit target, Final implementation lane, Records (script 신규 1, doc 신규 1, manifest 갱신), Decision (3종: schema_hash 정의, default-OFF DDL only, ephemeral 분리), Verification (V01–V12 PowerShell 명령), Next phase, Directive.
- 완료 조건:
  ```powershell
  Select-String -Path C:/System_Trading/STOM/STOM_V/docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-PHASE-A"
  ```
  PASS: 매치 1건.
- 의존하는 선행 작업: T03.

### T06. R1–R10 3-tuple 위험 자동탐지 명령 정합 검증

- 작업 ID: `V3K-PA-T06`
- 목표: E 섹션 위험표의 모든 trigger/자동탐지명령/차단액션이 실제 PowerShell에서 실행 가능한지 dry-run.
- 변경 대상 파일:
  - `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md` (수정 — 위험표 검증 절 추가)
- 변경 의도:
  - 각 R1–R10 자동탐지명령을 dry-run하여 syntax error 0건임을 확인.
  - 위험 detect 시 차단액션이 실제로 가능한지 짝(`exit 1` / commit 차단 / branch 자동 stash) 명시.
- 완료 조건:
  ```powershell
  pwsh -NoProfile -Command "& { foreach ($r in 1..10) { Write-Host \"R$r OK\" } }"
  ```
  PASS: R1~R10 라벨 출력 + 실제 명령은 V01–V12에서 실행되어 PASS.
- 의존하는 선행 작업: T03, T05.

### T07. 통합 검증 V01–V12 + `verify_release_sync.py` 마지막 단계

- 작업 ID: `V3K-PA-T07`
- 목표: D 섹션 V01–V12 전 PowerShell 명령 PASS, 마지막에 release preflight 통과.
- 변경 대상 파일: 없음 (검증 단계, 새 파일 생성 0건). `_database_v3k_shadow/`는 rehearsal 후 삭제.
- 변경 의도:
  - rehearsal: T01–T06 산출 후 V01부터 V12까지 순차 실행.
  - 종료 시 `_database_v3k_shadow/` 삭제 + WAL/SHM 잔재 cleanup (F 섹션 rollback과 동일 절차).
  - 마지막에 `python scripts/verify_release_sync.py` 통과 확인.
- 완료 조건:
  ```powershell
  python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
  ```
  PASS: `release sync preflight passed`.
- 의존하는 선행 작업: T01–T06 모두.

---

## D. 검증 단계 V01–V12 (PowerShell 명령)

> V05 PASS 기준은 task 단계별로 차등 적용된다 (Rev3 + O3 흡수). 단순화하면: **apply 직전·후의 V05–V09는 `STOM_Version_2U_C`만 PASS, 그 외 V01–V04 / V10–V12는 양쪽(V2 root, 2U_C) PASS.**

| # | PowerShell 명령 | 실행 lane | PASS 기준 | 실패 시 조치 |
| --- | --- | --- | --- | --- |
| V01 | `python -m py_compile C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py C:/System_Trading/STOM/STOM_V/scripts/apply_v3k_shadow_db.py` | 양쪽 | exit 0 | T01/T02 코드 재검토 |
| V02 | `python -m pytest C:/System_Trading/STOM/STOM_V/tests/unit/test_v3k_shadow_schema_hash.py -q` | 양쪽 | exit 0, 3 tests pass (동일성/키 순서 불변/`dflt_value` SQL 공백 불변) | T01 회귀 테스트 보강 |
| V03 | `python C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py --dry-run --manifest .omx/reports/v3k-shadow-manifest.json` | 양쪽 | exit 0, manifest에 `schema_hash` 필드 7개 DB 전부 stamp | manifest builder 점검 |
| V04 | `python C:/System_Trading/STOM/STOM_V/scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.before.json` | 양쪽 | exit 0, `ok=false`, `missing_dbs` 7개 | DESIGN-1B 정상 상태(빈 shadow) |
| V05 | `git -C <wt> branch --show-current` | **2U_C 전용** | `STOM_Version_2U_C` 정확 일치. V2 root에서는 본 단계 skip(V06 직전 가드) | T04 branch 가드 우회 환경 변수 점검; V2 root에서 apply 시도 시 R3 발현 |
| V05b | `Select-String -Path C:/System_Trading/STOM/STOM_V/scripts/init_v3k_shadow_db.py,C:/System_Trading/STOM/STOM_V/scripts/v3k_db_health.py -Pattern "EXPECTED_DBS\|LEARNING_DBS"` | 양쪽 | 두 출처에서 동일 라벨 7건 출력 (O2 흡수, 수동 라벨 비교) | EXPECTED_DBS 동기화 누락 → Phase B 후속 리팩터로 분리 |
| V06 | `python C:/System_Trading/STOM/STOM_V.wt-dev/scripts/apply_v3k_shadow_db.py --apply --shadow-dir _database_v3k_shadow` | **2U_C 전용** | exit 0, 7개 .db 파일 생성 | T02 apply 로직 점검 |
| V07 | `python -c "import sqlite3, pathlib; p=pathlib.Path('C:/System_Trading/STOM/STOM_V.wt-dev/_database_v3k_shadow/v3k_meta.db'); c=sqlite3.connect(f'{p.as_uri()}?mode=ro', uri=True); print(c.execute('SELECT COUNT(*) FROM v3k_feature_flags').fetchone()[0])"` | **2U_C 전용** | `0` 출력 (R5/default-OFF 자동) | T02 INSERT 코드 제거 |
| V08 | `python -c "import sqlite3, pathlib; p=pathlib.Path('C:/System_Trading/STOM/STOM_V.wt-dev/_database_v3k_shadow/v3k_code_meta.db'); c=sqlite3.connect(f'{p.as_uri()}?mode=ro', uri=True); print(c.execute('SELECT COUNT(*) FROM v3k_listed_shares').fetchone()[0])"` | **2U_C 전용** | `0` 출력 | T02 INSERT 제거 |
| V08b | `python -c "import sqlite3, pathlib; p=pathlib.Path('C:/System_Trading/STOM/STOM_V.wt-dev/_database_v3k_shadow/v3k_meta.db'); c=sqlite3.connect(f'{p.as_uri()}?mode=ro', uri=True); print(c.execute('SELECT COUNT(*) FROM v3k_schema_manifest').fetchone()[0])"` | **2U_C 전용** | 정수 출력 = manifest stamp 결과 row 수와 일치 (7개 DB × table 수 합) (O1 흡수) | T02 manifest stamp 로직 점검 |
| V09 | `python C:/System_Trading/STOM/STOM_V.wt-dev/scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health.after.json` | **2U_C 전용** | exit 0, `ok=true`, `missing_dbs=[]` | T02 DDL 누락 점검 |
| V10 | `git -C C:/System_Trading/STOM/STOM_V check-ignore .omx/reports/v3k-db-health.before.json .omx/reports/v3k-db-health.after.json .omx/reports/v3k-phase-a-diff.md` | 양쪽 | exit 0, 3 경로 모두 출력 | T04 `.gitignore` 보강 |
| V11 | `git -C C:/System_Trading/STOM/STOM_V status --porcelain -- _database/ _database_v3k_shadow/ *.db` | 양쪽 | (빈 출력) | 운영 `_database/` 무변경(P1), shadow `*.db`도 stage되지 않아야 함 |
| V12 | `python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py` | 양쪽 | `release sync preflight passed` | release-blocking 항목 차단; 즉시 rollback |

> 모든 명령은 `STOM_V` 또는 `STOM_V.wt-dev` 워크트리 루트에서 실행. 절대경로 명령은 위치 무관. V05–V09 (5개)와 V08b는 **`STOM_V.wt-dev` (2U_C) 한정**이며 V2 root에서는 R3 가드에 의해 의도적으로 차단된다.

---

## E. 위험 매트릭스 R1–R10 (3-tuple)

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지명령, 차단액션) | 추가 완화책 |
| --- | --- | --- | --- | --- | --- |
| R1 | 운영 `_database/` 변경 | 치명 | 낮음 | (`apply` 실수 인자, `git status`에 `_database/` 등장, `git checkout -- _database/` + apply 즉시 중단) | T02 argparse choices에 `_database` 차단; `executescript` 직전 `Path.relative_to(_database_v3k_shadow)` assert |
| R2 | Kiwoom runtime/order/receiver 변경 | 치명 | 매우 낮음 | (`scripts/`, `strategy/` 외부 변경, `git diff --name-only -- trade/ ui/ utility/`, commit 차단 + `git restore --staged`) | Phase A 산출물 화이트리스트 명시 |
| R3 | branch 가드 경로 정규화 어긋남 (Architect risk b) | 높음 | 중간 | (이중 worktree에서 `Path.resolve()` 결과가 expected branch와 mismatch, `python -c "from pathlib import Path; ..."` resolve 후 relative_to 검사, `V3K_PHASE_A_BRANCH_BYPASS=1` 미설정 시 exit 2) | `init_v3k_shadow_db.ensure_report_path` 패턴 재사용 |
| R4 | sentinel naming 충돌 (Architect risk c, O1 흡수) | 높음 | 중간 | (`v3k_feature_flags`에 비-sentinel row 등장 가능성, Phase A에서는 INSERT 금지로 회피, Phase B 이후 `Select-String _v3kshadow_smokeA_` 일관성 검사) | L3 invariant + Phase A는 INSERT 자체 금지 |
| R5 | default-OFF DDL/data 분리 위반 (Architect risk d) | 치명 | 낮음 | (`v3k_feature_flags`에 row 1건 이상 존재, V07/V08 SELECT COUNT, apply 즉시 rollback + INSERT 코드 제거) | T02 코드 리뷰에서 INSERT 패턴 grep 차단 |
| R6 | LS 직접 의존 신규 import | 치명 | 매우 낮음 | (`scripts/apply_v3k_shadow_db.py` import 추가, `python -m grep` `import.*restapi_ls`, commit pre-hook reject) | argparse에서 `--broker` 옵션 자체 노출 금지 |
| R7 | DB 파일 commit 누락 가드 | 높음 | 낮음 | (`*.db` 파일이 `git status`에 등장, `git -C ... status --porcelain '*.db'`, V11에서 비어있어야 PASS) | `.gitignore` `*.db` 이미 존재(line 54), shadow도 동일 가드 |
| R8 | `schema_hash` 비결정성 (Architect risk a) | 높음 | 중간 | (같은 schema가 hash 달라짐, T01 회귀 3종(동일성/키 순서 불변/`dflt_value` SQL 공백 불변) fail, T01 부정합 commit 차단) | sorted tuple 강제 + `repr` 대신 명시 직렬화 |
| R9 | Python 3.13.13 외 환경 실행 | 중간 | 낮음 | (`python --version` ≠ `Python 3.13.x`, `if (-not (python --version 2>&1 \| Select-String '^Python 3\.13\.')) { throw }`, 실행 거부) | runbook 첫 단계에 버전 검증 |
| R10 | `init_v3k_shadow_db.py` 외부 동작 회귀 | 치명 | 낮음 | (`--dry-run` 미강제 또는 manifest 포맷 변경, V03 manifest schema 비교, T01 코드리뷰에서 외부 동작 변경 reject) | L2 invariant + module docstring 명시 |

---

## F. Rollback 절차 (시나리오 3개, WAL/SHM cleanup 포함)

### F.1 시나리오 1 — apply 도중 실패 (DDL 일부 적용)

```powershell
# 1) 모든 SQLite handle 종료 확인
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*v3k*" } | Stop-Process -Force

# 2) shadow 디렉터리 + WAL/SHM 잔재 cleanup
Remove-Item -Recurse -Force C:/System_Trading/STOM/STOM_V.wt-dev/_database_v3k_shadow/

# 3) git에 잔재 없는지 확인
git -C C:/System_Trading/STOM/STOM_V.wt-dev status --porcelain -- _database_v3k_shadow/

# 4) verify_release_sync 통과 확인
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
```

### F.2 시나리오 2 — apply 성공 후 V07/V08 `feature_flags` row 발견 (R5 발현)

```powershell
# 1) 즉시 shadow 폐기 (data 격리)
Remove-Item -Recurse -Force C:/System_Trading/STOM/STOM_V.wt-dev/_database_v3k_shadow/

# 2) WAL/SHM cleanup (defensive)
Get-ChildItem -Path C:/System_Trading/STOM/STOM_V.wt-dev/ -Filter "*.db-*" -Recurse | Remove-Item -Force

# 3) T02 코드에서 INSERT 패턴 grep 후 제거
Select-String -Path C:/System_Trading/STOM/STOM_V.wt-dev/scripts/apply_v3k_shadow_db.py -Pattern "INSERT INTO v3k_feature_flags|INSERT INTO v3k_listed_shares"

# 4) T01 hash 회귀 재실행
python -m pytest C:/System_Trading/STOM/STOM_V.wt-dev/tests/unit/test_v3k_shadow_schema_hash.py -q
```

### F.3 시나리오 3 — registry/docs commit 후 health.json 누설(commit) 발견

```powershell
# 1) 누설된 ephemeral 파일을 unstage + 작업 디렉터리에서 제거
git -C C:/System_Trading/STOM/STOM_V.wt-dev rm --cached .omx/reports/v3k-db-health.before.json .omx/reports/v3k-db-health.after.json .omx/reports/v3k-phase-a-diff.md
Remove-Item -Force C:/System_Trading/STOM/STOM_V.wt-dev/.omx/reports/v3k-db-health.before.json, C:/System_Trading/STOM/STOM_V.wt-dev/.omx/reports/v3k-db-health.after.json, C:/System_Trading/STOM/STOM_V.wt-dev/.omx/reports/v3k-phase-a-diff.md -ErrorAction SilentlyContinue

# 2) `.gitignore` 패턴 재확인 (T04)
Select-String -Path C:/System_Trading/STOM/STOM_V.wt-dev/.gitignore -Pattern "v3k-db-health|v3k-phase-a-diff"

# 3) 한국어 정정 commit (Commit Language Rules)
git -C C:/System_Trading/STOM/STOM_V.wt-dev commit -m "V3K Phase A 임시 산출물을 git 추적에서 제외한다"

# 4) verify_release_sync 통과 확인
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
```

---

## G. 산출물 목록 (commit 7건 + 선택 1건, ephemeral 4건 분리)

### G.1 Commit 포함 (7건, Rev1 정정)

> v2의 8/9 자기 변호("9건으로 셈")를 폐기. 실제 commit 산출물은 1–7 = **7건**.

| # | 분류 | 경로 | 종류 |
| --- | --- | --- | --- |
| 1 | 신규 script | `scripts/apply_v3k_shadow_db.py` | 신규 |
| 2 | 신규 test | `tests/unit/test_v3k_shadow_schema_hash.py` | 신규 |
| 3 | 신규 docs (ADR + V01–V12 runbook 통합) | `docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md` | 신규 |
| 4 | 수정 script | `scripts/init_v3k_shadow_db.py` (`compute_schema_hash` 추가, manifest stamp, docstring) | 수정 |
| 5 | 수정 ignore | `.gitignore` (ephemeral 4종 추가) | 수정 |
| 6 | 수정 registry | `docs/CARRY_FORWARD_REGISTRY.md` (`## V3K-PHASE-A` 섹션) | 수정 |
| 7 | 수정 manifest | `.omx/reports/v3k-shadow-manifest.json` (schema_hash stamp 결과) — **ephemeral 정책의 명시적 예외**: schema 정의의 audit trail이며 Phase B 회귀 baseline. T04 또는 H.4 commit message 본문에 본 사유 한 줄 명시 | 수정 |

### G.1b 선택 산출물 (Phase A 종료 시 별도 PR로 분리 가능)

| # | 분류 | 경로 | 종류 | 분리 정책 |
| --- | --- | --- | --- | --- |
| O1 | (선택) 신규 Phase A 종료 audit | `docs/update_log/2026-05-10_v3k_phase_a_closure.md` | 신규 | Phase A rehearsal 종료 시점에 별도 PR로 분리해도 무방. 본 PR 범위에 포함하지 않아도 G.1 Commit 7건이 Phase A 본체 산출물로 충분 |

> v2의 #8 "runbook 발췌"는 #3 파일과 동일하므로 별도 산출물로 셈하지 않는다 (PR description에서는 #3 파일의 V01–V12 섹션을 인용).

### G.2 Ephemeral (4건, .gitignore + PR description 첨부)

| # | 경로 | 생성 단계 | 생애주기 |
| --- | --- | --- | --- |
| E1 | `.omx/reports/v3k-db-health.before.json` | V04 | rehearsal 종료 시 수동 삭제 |
| E2 | `.omx/reports/v3k-db-health.after.json` | V09 | rehearsal 종료 시 수동 삭제 |
| E3 | `.omx/reports/v3k-phase-a-diff.md` (E1↔E2 diff markdown) | V09 직후 수동 생성 | rehearsal 종료 시 수동 삭제 |
| E4 | apply stdout report (`.omx/reports/v3k-apply-report.json` 또는 PowerShell transcript) | V06 | rehearsal 종료 시 수동 삭제 |

> 4종 모두 PR description에 첨부. git 트리에는 절대 들어가지 않음. manifest(#7)는 ephemeral이 아닌 commit 대상으로 명시 분리.

---

## H. Commit message 한국어 sample (CLAUDE.md `## Commit Language Rules` 정렬)

> 형식: 한국어 제목(60자 이내) 1줄 + 빈 줄 + 한국어 markdown 본문 3줄.

### H.1 commit 1+4 — schema_hash + apply script 쌍

```text
V3K Phase A schema_hash 정의와 shadow apply script를 도입한다

- `init_v3k_shadow_db.py`에 `compute_schema_hash`를 추가하고 manifest에 stamp한다.
- `scripts/apply_v3k_shadow_db.py`를 신규 작성해 DDL만 적용하며 default-OFF를 보존한다.
- 운영 `_database/`와 Kiwoom runtime은 변경하지 않는다.
```

### H.2 commit 2 — schema_hash 회귀 테스트 3종

```text
V3K schema_hash 비결정성 회귀 테스트 3종을 추가한다

- 동일성, 키 순서 불변, `dflt_value` SQL 공백 불변 3종으로 hash 안정성을 보호한다.
- 입력은 PRAGMA table_info 등가 dict이며 SQL string 입력은 본 함수의 surface가 아니다.
- pytest -q 통과를 Phase A 종료 조건에 포함한다.
```

### H.3 commit 3 — Phase A 운영 문서

```text
V3K Phase A shadow DB rehearsal 운영 절차를 문서화한다

- `docs/update_log/2026-05-10_v3k_phase_a_shadow_rehearsal.md`에 ADR과 V01–V12를 기록한다.
- 위험 R1–R10을 (trigger, 자동탐지명령, 차단액션) 3-tuple로 명시한다.
- ephemeral 산출물 첨부 정책과 rollback 3 시나리오를 함께 둔다.
```

### H.4 commit 5 — `.gitignore` ephemeral 분리

```text
V3K Phase A 임시 산출물을 git 추적에서 제외한다

- `.omx/reports/v3k-db-health.*.json`와 `v3k-phase-a-diff.md`를 ignore에 추가한다.
- runbook PR description 첨부만 허용하고 트리 commit은 금지한다.
- `v3k-shadow-manifest.json`은 schema audit trail이라 ephemeral 예외로 commit 대상이다.
```

### H.5 commit 6 — registry `## V3K-PHASE-A` 섹션

```text
V3K-PHASE-A 항목을 carry-forward registry에 등록한다

- DESIGN-1B 패턴을 따라 records, decision, verification, next phase를 기재한다.
- `STOM_Version_2U_C` lane의 lifetime invariant를 함께 명시한다.
- V01–V12 PowerShell 명령을 검증 절에 포함한다.
```

### H.6 commit 7 — manifest schema_hash stamp 결과

```text
V3K shadow manifest에 schema_hash stamp 결과를 갱신한다

- 7개 DB 모든 table에 schema_hash를 포함한 manifest를 생성한다.
- manifest 외부 동작과 dry-run 강제는 변경하지 않는다.
- `.omx/reports/v3k-shadow-manifest.json`은 schema audit trail로 ephemeral 정책의 명시적 예외 대상이다.
```

---

## I. ADR 요지

- **Decision**: V3K Phase A는 별도 `apply_v3k_shadow_db.py`를 신설하여 `init_v3k_shadow_db.py`에서 schema 정의(LEARNING_DBS/META_DBS/create_table_sql/compute_schema_hash)를 직접 import하고, DDL만으로 7개 shadow DB를 생성한다. sentinel/data row INSERT는 Phase B 이후 책임이며 Phase A에서는 default-OFF를 자동검증한다.
- **Drivers**:
  1. DESIGN-1B 외부 동작 보존 (lifetime invariant L2).
  2. Phase B 변경 비용 최소화 (schema_hash·sentinel·default-OFF를 Phase A에서 굳힘).
  3. CLAUDE.md 정합성 (한국어 commit, PowerShell, verify_release_sync, `_database/` 무변경).
- **Alternatives considered**:
  - Option 1 단일 script 확장 → P2 위반(--dry-run required 변경 위험)으로 기각.
  - Option 4 .sql 파일 + executescript → schema 단일 출처 위반 + placeholder 처리 곤란으로 기각.
  - Option 3 schema 추출 모듈 신설 → R2/Critic 지적에 따라 보류; Phase A 동안 `init_v3k_shadow_db.py`를 단일 출처로 유지.
- **Why chosen**: Option 2-hybrid는 외부 동작 0 변경, schema 단일 출처 유지, 신규 surface(apply만)에 신규 위험을 격리, 산출물 신규 4 → 3으로 축소.
- **Consequences**:
  - 긍정: Phase B로 넘어갈 때 schema_hash, sentinel naming, default-OFF가 invariant로 고정되어 후속 phase의 변경 surface가 명확.
  - 부정: `apply_v3k_shadow_db.py`가 `init_v3k_shadow_db`에 import 의존. 단, init은 stdlib만 사용하므로 import side effect는 0.
  - **Phase A 한정 운영 단서 (Rev3 + O3)**: V05–V09(apply 단계)는 `STOM_Version_2U_C` (`STOM_V.wt-dev`)에서만 PASS 기준을 만족하며, V2 root에서 실행 시 R3 branch 가드에 의해 의도적으로 차단된다. 이는 Phase A 한정 결정이며 Phase B 이후 lane 정책 재검토 가능.
- **Follow-ups**:
  - F1: Phase B에서 sentinel row INSERT/UPDATE 명시 시점에 `_v3kshadow_smokeA_` prefix 일관성 회귀 테스트 추가.
  - F2: Phase B에서 `--strategy-gubun` 다중화 검토 시 A3 결정 변경.
  - F3: Phase G 폐쇄 시 `_database_v3k_shadow/` 와 ephemeral 산출물의 영구 cleanup 절차 합의.
  - F4: Phase B에서 EXPECTED_DBS 두 출처(`init_v3k_shadow_db.py`, `v3k_db_health.py`) derive 리팩터 (O2의 후속).

---

## J. 핵심 설계 질문 답변

> v1 Q1–Q6 + Architect/Critic 신규 질문 통합. v3에서 Q2/QArch2를 Rev2 입력 layer 명확화에 맞춰 갱신.

### Q1. schema 정의의 단일 출처는 어디인가?
A. **`scripts/init_v3k_shadow_db.py`**. DESIGN-1B 종료 판정의 외부 동작(L2)이며, Phase A에서는 추출하지 않는다. apply는 직접 import.

### Q2. schema_hash는 무엇이고 어디에 stamp되는가?
A. PRAGMA table_info 등가 입력 (Python dict)을 `(cid, name, type, notnull, dflt_value, pk)` tuple로 sorted 직렬화 후 sha256 hex 64자 (L1). manifest의 `dbs[db_name].tables[table_name].schema_hash`와 `v3k_meta.db.v3k_schema_manifest` row 양쪽에 stamp. 회귀 테스트 3종(T01)으로 결정성 보호. 입력은 dict이며 SQL string 입력은 본 함수의 surface가 아니다.

### Q3. default-OFF는 어떻게 자동검증되는가?
A. T02에서 INSERT 코드 자체를 작성하지 않고, V07/V08 SELECT COUNT = 0으로 자동검증 (R5). Phase A에서는 `v3k_meta.db`의 `v3k_schema_manifest` 외에 어떤 row도 만들지 않는다. `v3k_schema_manifest`는 schema 정의 자체이지 feature/data가 아님. row 수는 V08b로 별도 검증 (O1 흡수).

### Q4. ephemeral과 commit 산출물의 경계는?
A. commit (G.1, 7건): script(1, 4), test(2), docs(3), ignore(5), registry(6), manifest(7). manifest는 schema audit trail이라 ephemeral 예외. ephemeral (G.2, 4건): health.before/after JSON, diff markdown, apply report. `.gitignore` 패턴 + V10 자동 검증.

### Q5. sentinel naming은 왜 `_v3kshadow_smokeA_`인가?
A. 기존 `_smoke_` prefix와 충돌 가능성을 차단하고 Phase 식별자(`A`)를 포함하여 Phase B/C/D rehearsal과도 분리. L3 invariant.

### Q6. `--strategy-gubun` CLI는 Phase A 한정인가?
A. 그렇다 (A3). docstring에 "Phase A 한정" 명시. Phase B 이후 다중 strategy gubun을 다룰 때는 시그니처 변경 자유.

### QArch1. branch 가드 경로 정규화는 어떻게 검증되는가?
A. `init_v3k_shadow_db.ensure_report_path` 패턴(`Path.resolve() + relative_to`)을 그대로 재사용 (R3). 이중 worktree·CI 환경은 `V3K_PHASE_A_BRANCH_BYPASS=1` 환경 변수로 명시적 우회. apply는 `STOM_Version_2U_C` (`STOM_V.wt-dev`)에서만 PASS, V2 root에서는 의도적으로 차단(C.0 + V05 기준).

### QArch2. schema_hash가 비결정적이 될 시나리오와 detection은? (Rev2 갱신)
A. 다음 3종이 회귀 3종과 1:1 매핑된다.
  1. **동일 입력 비결정성** (idempotency 위반): 같은 dict 두 번 호출 시 hash 변동 → 회귀 (a) 동일성 fail.
  2. **dict 키 순서 의존**: columns 키 순서가 다른 의미적으로 동일한 dict가 다른 hash → 회귀 (b) 키 순서 불변 fail. 내부 sorted tuple 강제로 보호.
  3. **`dflt_value` SQL 공백/줄바꿈 의존**: column 정의 내 `dflt_value` SQL 표현의 공백만 다른 dict가 다른 hash → 회귀 (c) `dflt_value` SQL 공백 불변 fail. PRAGMA가 normalize한 결과로 동등 판정.
  detection은 `pytest -q`. 차단액션은 commit 차단.

### QCrit1. EXPECTED_DBS의 두 출처(`init`/`v3k_db_health`) 동기화는?
A. Phase A에서는 **수동 라벨 비교**만 수행 (V05b, O2 흡수): `Select-String -Path .../init_v3k_shadow_db.py,.../v3k_db_health.py -Pattern "EXPECTED_DBS|LEARNING_DBS"`로 양쪽 라벨 7건 일치 확인. derive 리팩터는 Phase B 후속 task로 분리(I.Follow-ups F4).

### QCrit2. Option 4(.sql + executescript)는 왜 기각인가?
A. (1) Python dict가 schema 단일 출처(L2 후행 결과)를 형성 — dual-source 동기화 부담 신규 발생. (2) `{strategy_gubun}` / `{tick|min}` placeholder 치환은 SQL 자체로 표현 곤란. (3) compute_schema_hash 입력이 Python dict이므로 .sql 파일에서 hash 도출 시 파서 추가 필요.

### QCrit3. WAL/SHM 잔재가 발생하면 어떻게 처리하는가?
A. F.1/F.2 시나리오에 통합. `Get-ChildItem -Filter "*.db-*"`로 WAL/SHM 잔재를 명시적으로 정리한 뒤 verify_release_sync.

---

## K. Phase A 종료 후 다음 단계 전환 지침 (Phase B 착수 전 필수)

> 본 절은 amendment commit에서 신설되었다. Phase A는 V3K 전체 7-phase 로드맵(§0.2)의 첫 단계일 뿐이다. Phase A 완료 즉시 Phase B를 시작하기 전에 본 §K의 전환 지침을 반드시 따라야 한다. 이를 통해 §0 미션 statement와 §0.2 로드맵, audit `2026-05-10_2uc_v3k_full_feature_audit.md` §8 정본이 phase 간 단절 없이 보존된다.

### K.1 Phase A 완료 판정 체크리스트 (다음 단계 진입 gate)

아래 9 체크가 모두 PASS여야 Phase B 착수 가능. 하나라도 FAIL이면 §F rollback 절차 적용 후 Phase A 보완.

| # | 체크 | 판정 명령/근거 |
| --- | --- | --- |
| K1.1 | T01–T07 모든 task가 commit됨 | `git -C C:/System_Trading/STOM/STOM_V.wt-dev log --oneline | Select-String "V3K Phase A"`가 7건 이상 |
| K1.2 | V01–V12 + V05b + V08b 모두 PASS | `.omx/reports/v3k-db-health.after.json`의 `"ok": true` |
| K1.3 | `verify_release_sync.py` PASS | "release sync preflight passed" |
| K1.4 | `_database_v3k_shadow/` 7 DB 생성 + manifest schema_hash stamp 완료 | V09 + V08b 결과 |
| K1.5 | DB 파일 0건 commit | `git log --all -- '*.db'` 결과 없음 |
| K1.6 | LS direct marker 0건 | `Select-String -Path scripts/ -Pattern "ls_securities\|LS_REST\|xingapi\|restapi_ls"` 0건 |
| K1.7 | Kiwoom runtime/order/receiver 변경 0건 | `git diff <pre-phase-A> HEAD -- trade/ ui/ utility/` 빈 출력 |
| K1.8 | STOM CLI surface 변경 0건 (L9) | `init_v3k_shadow_db.py --dry-run` manifest 키 set 변화 없음 + backtest/realtime CLI 진입점 시그니처 무변경 |
| K1.9 | `CARRY_FORWARD_REGISTRY.md`에 `## V3K-PHASE-A` 섹션 + 산출물 등록 완료 | T05 검증 명령 |

### K.2 V3K 전체 목적 재확인 체크리스트 (Phase B 착수 전 필수)

Phase B로 넘어가기 전에 §0.1 미션 statement를 한 번 더 확인. 6개 중 하나라도 NO면 Phase B plan 작성 전에 audit 보고서 갱신 + ralplan 재합의 필요.

- [ ] V3 신기능을 2U_C에 **모두** 반영하는 큰 목적이 그대로인가? (§0.1)
- [ ] LS Securities 직접 의존이 본 phase에 새로 도입되지 않았는가? (L7)
- [ ] Kiwoom증권 API/runtime 보존 원칙이 깨지지 않았는가? (P1, L4)
- [ ] STOM CLI surface(`init_v3k_shadow_db.py` 외 backtest CLI/realtime CLI 포함)가 깨지지 않았는가? (L9)
- [ ] DB 격리 원칙(`_database/`와 `_database_v3k_shadow/` 분리)이 유지되는가? (L4, L8)
- [ ] Phase A의 lifetime invariant L1–L9가 Phase B에서 변경 불가임을 후속 plan에 명시할 준비가 되었는가? (§B.1)

### K.3 Phase B 착수 전 재계획 절차 (ralplan 재실행 권장)

다음 절차를 따라 Phase B plan을 작성한다. 본 plan과 동등한 합의 수준을 요구한다.

1. **audit doc §8 Phase B 재확인**: `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` §8 "Phase B — read-only learning DB 검증" 절을 출처로 인용.
2. **`/oh-my-claudecode:ralplan` 재실행**: Phase B 단독 상세 합의 워크플로 (Planner → Architect → Critic) short deliberation 모드를 본 plan과 동일하게 적용. 고위험 phase(F·G)인 경우 `--deliberate` 플래그 강제.
3. **Phase B plan 신설**: `docs/plans/<YYYY-MM-DD>_v3k_phase_b_readonly_learning_db_plan.md` 신규 파일로 작성. **본 plan을 amend해서 Phase B를 추가하지 않는다**(§K.5).
4. **§0.2 로드맵에서 Phase B 위치 갱신은 새 Phase B plan 안에서만** 한다. 본 plan의 §0.2는 freeze 상태로 유지하고, 새 plan이 §0.2를 인용·확장한다.
5. **Phase A → Phase B 산출물 매핑 명시** (§K.4 참조).
6. **Phase B-specific lifetime invariant 추가 여부 평가**. 새 invariant가 필요하면 본 plan §B.1에 L10+를 추가하지 않고 Phase B plan 안에 별도 invariant 표를 신설한다. 본 plan §B.1은 Phase A 종료 시점에 freeze.
7. **carry-forward registry에 `## V3K-PHASE-B` 섹션 추가**: V3K-PHASE-A 패턴 follow.
8. **사용자 명시 승인 후에만 Phase B 코드 commit 시작**.

### K.4 Phase A → Phase B 산출물 입력 매핑

Phase A가 만든 결과물 중 Phase B에서 사용되는 것을 명시한다. Phase B plan은 이 매핑을 인용하여 의존성을 추적해야 한다.

| Phase A 산출물 | Phase B에서의 사용 | 보존 invariant |
| --- | --- | --- |
| `_database_v3k_shadow/` 7 DB | `V3KLearningDataAdapter`의 `?mode=ro` smoke 대상 (read-only) | L4, L8 |
| `v3k_meta.db.v3k_schema_manifest` (stamped) | Phase B read-only adapter의 schema_hash 검증 baseline | L1 |
| `compute_schema_hash` 함수 (`init_v3k_shadow_db.py`) | Phase B의 schema drift detection에서 재사용 (dual-source 금지) | L1, L2 |
| sentinel `_v3kshadow_smokeA_` prefix | Phase B에서 read-only smoke fixture로만 사용. **INSERT는 여전히 금지** | L3, L5 |
| `init_v3k_shadow_db.py`의 `LEARNING_DBS`/`META_DBS`/`create_table_sql` | Phase B의 adapter contract에서 직접 import. dual-source 금지 | L2 |
| `.gitignore` ephemeral 패턴 | Phase B의 read-only smoke 결과물에도 동일 정책 적용 | P4, L8 |
| `.omx/reports/v3k-shadow-manifest.json` | Phase B의 schema_hash 회귀 baseline (audit trail) | L1 |
| Phase A 한정 lane 정책 (V05–V09 = 2U_C 한정) | Phase B에서는 read-only smoke이므로 양쪽 lane 허용 검토 가능 (A1 자유) | A1, A3 |

### K.5 모든 후속 phase의 별도 plan 작성 의무

Phase B–G 각각은 별도 plan 문서를 필수로 작성한다. **본 plan(`2026-05-10_v3k_phase_a_shadow_db_plan.md`)을 amend해서 Phase B–G를 추가하지 않는다**.

| 후속 phase | 필수 산출 plan 파일명 형식 |
| --- | --- |
| Phase B | `docs/plans/<YYYY-MM-DD>_v3k_phase_b_readonly_learning_db_plan.md` |
| Phase C | `docs/plans/<YYYY-MM-DD>_v3k_phase_c_gui_settings_plan.md` |
| Phase D | `docs/plans/<YYYY-MM-DD>_v3k_phase_d_formula_global_plan.md` |
| Phase E | `docs/plans/<YYYY-MM-DD>_v3k_phase_e_kiwoom_dryrun_plan.md` |
| Phase F | `docs/plans/<YYYY-MM-DD>_v3k_phase_f_analyzer_strategy_plan.md` (고위험, `--deliberate` 권장) |
| Phase G | `docs/plans/<YYYY-MM-DD>_v3k_phase_g_microstructure_engine_plan.md` (대형, G-1/G-2/G-3 분해 권장) |

각 후속 plan은 다음을 반드시 포함:
- §0 V3K 미션 statement 재인용 (§0.1 한 줄 변경 금지)
- §0.2 Phase A–G 로드맵 표에서 본 phase 위치 표시
- 직전 phase 산출물 입력 매핑 (Phase A의 §K.4 패턴 따름)
- §K-equivalent 절: 다음 phase 전환 체크리스트 + 미션 재확인 체크리스트
- audit `2026-05-10_2uc_v3k_full_feature_audit.md` §8 해당 Phase 절을 출처로 인용
- Phase별 lifetime invariant 표 (필요 시 신설, 본 plan §B.1 freeze)

### K.6 V3K 미션 완료 판정 (Phase G 종료 시점)

Phase G까지 모두 완료되면 다음 8개를 만족해야 V3K 미션 완료로 본다(audit §6.2의 8개 의도적 미완료 항목 전체 해소).

1. shadow DB가 운영 cutover됨 (Phase A·B 합산 결과)
2. GUI flag로 사용자가 명시적 ON 가능 (Phase C, default-OFF 보존)
3. `V3K_` prefix formula/global runtime 연결 (Phase D)
4. live Kiwoom dry-run hook 실행 (Phase E)
5. analyzer output이 전략/주문/청산 판단에 통합 (Phase F)
6. V3 microstructure engine 동등 기능이 2U_C에서 작동 (Phase G)
7. LS Securities 직접 의존 0건 (전 phase 보존, L7)
8. Kiwoom API/runtime/CLI surface 무변경 (전 phase 보존, L7·L9)

V3K 미션 완료 시 audit 보고서 갱신과 `## V3K-PHASE-G-CLOSURE` registry 등록이 필요하다. 이 시점에 `_database_v3k_shadow/`를 운영 `_database/`로 cutover하는 별도 phase(Phase H로 격상하거나 Phase G 내 종결 절로 흡수)에 대한 의사결정도 필요하다.

### K.7 본 plan freeze 정책

Phase A 종료(K.1 모든 체크 PASS 시점) 이후 본 plan은 **freeze 상태**가 된다. 다음만 허용:
- 오탈자/포맷 정정 commit
- audit 보고서 cross-reference 갱신
- 본 §K의 후속 plan 파일명 갱신 (실제 파일명이 결정된 후)

다음은 금지:
- §A·B·C·D·E·F·G·H·I·J 본문 변경
- Phase B–G 내용을 본 plan에 추가
- lifetime invariant L1–L9 의미 변경

본 freeze 정책은 lifetime invariant의 안정성을 후속 phase에서 보장하기 위함이다.

---

## 부록. Phase A 출력 형식 표

| 항목 | 값 |
| --- | --- |
| ralplan iteration | 3 (Planner v3, Architect APPROVE, Critic APPROVE) |
| 다음 단계 | V3K-PHASE-A 착수 (사용자 명시 승인 후) |
| 절대경로 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` (구현), `C:/System_Trading/STOM/STOM_V` (V2 root, 일부 검증 양쪽) |
| 활성 branch | 구현 lane: `STOM_Version_2U_C`, V2 root lane: `STOM_Version_2` |
| Python 버전 | `Python 3.13.13` (R9 자동 검증) |
| Commit 본문 언어 | 한국어 markdown (CLAUDE.md `## Commit Language Rules`) |

---

## 변경 요약 (v2 → v3)

본 v3는 Critic iteration 2의 3개 Required Revisions와 3개 Optional Improvements를 흡수한다.

### Required Revisions (3종)
- **Rev1 — G.1 commit boundary 정정**: v2의 "9건으로 셈" 자기 변호 문장(line 333) 삭제. G.1 표를 commit **7건**으로 재정렬, 별도 G.1b를 선택 산출물(closure audit)로 분리. 산출물 #7 manifest의 ephemeral 예외 사유(schema audit trail / Phase B 회귀 baseline)를 T04 본문 + H.4 commit message + H.6 commit message 본문 한 줄에 명시.
- **Rev2 — T01 회귀 3종 입력 layer 명확화**: 회귀 3종을 (a) 동일성(idempotency), (b) 키 순서 불변(key order invariance), (c) `dflt_value` SQL 공백 불변으로 재기술. 입력은 모두 PRAGMA table_info 등가 Python dict임을 T01 본문, H.2 commit message, J.QArch2 답변에 일관 표현으로 명시. SQL string 입력은 surface가 아님을 분리.
- **Rev3 — task별 worktree/lane 표 추가**: C.0 신설하여 T01–T07 각 task의 실행 lane / commit lane / 사유 표 게재. V05 PASS 기준을 task 단계별 차등으로 갱신: V05–V09는 `STOM_Version_2U_C` 한정, 그 외 V01–V04 / V10–V12는 양쪽. I.Consequences에 Phase A 한정 lane 정책 한 줄 추가.

### Optional Improvements (3종, 흡수)
- **O1 — V08b 추가**: `v3k_schema_manifest` row count 자동검증을 V08과 V09 사이에 V08b로 신설.
- **O2 — V05b 추가**: V01–V12 어딘가에 `Select-String EXPECTED_DBS\|LEARNING_DBS` 라벨 비교 1줄 추가 (V05b로 배치). derive 리팩터는 Phase B 후속 task로 분리(I.Follow-ups F4).
- **O3 — V05 task 단계별 차등**: I.Consequences에 Phase A 한정 운영 단서 한 줄 추가 + D 표 머리말에 단순화된 정책 명시.

### v2에서 보존 (변경 없음)
- A.1 5 Principles, A.2 3 Decision Drivers, A.3 Option 1 steelman / Option 2-hybrid 선택 / Option 4 5줄 평가
- B.1 8 Lifetime Invariants (L1 표현만 명료화), B.2 5 Phase A 한정 결정
- E R1–R10 3-tuple 위험 매트릭스 (R8 표현만 회귀 3종 새 명칭으로 동기화)
- F 3 rollback 시나리오 (apply lane을 `STOM_V.wt-dev` 절대경로로 통일)
- H 6 commit message sample (H.2/H.4/H.6 본문만 정정)
- I ADR 요지 (Consequences 1줄 + Follow-ups F4 추가)
- J 핵심 설계 질문 답변 (Q2/Q4/QArch2/QCrit1만 갱신)

---

## 한 줄 결론

V3K Phase A v3는 별도 `apply_v3k_shadow_db.py`로 schema 단일 출처와 default-OFF DDL만의 적용 경로를 분리하고, schema_hash·sentinel·default-OFF·branch 가드·ephemeral 분리를 lifetime invariant로 고정하면서, Critic iteration 2의 G.1 commit boundary(7건+선택 1건), T01 회귀 3종 입력 layer 명확화(dict 입력의 동일성/키 순서 불변/`dflt_value` SQL 공백 불변), task별 lane 표(V05–V09는 2U_C 한정)를 흡수한 ralplan iteration 3 실행 계획이다.
