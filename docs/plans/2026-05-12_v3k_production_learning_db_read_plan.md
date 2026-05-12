# V3K Production Learning DB Read — Phase B 후속 실행 계획 (F5)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| audit §6.2 항목 | #2 production learning DB contents read |
| 현재 단계 (F6 산식) | S2 (50%) — shadow read-only 완료, production read 미진행 |
| 목표 단계 | S3 (75%) read-only production read 작동 → S4 (100%) operational use |
| Phase letter | (audit §8에 없음, Phase B 후속) — letter 명명: 본 plan 내 `Phase B+` 또는 신규 letter `I` 사용 |
| 의존 입력 | Phase A (shadow DB) 완료, Phase B (`3eac14ec`) 완료 |
| 위험도 | 중간 (운영 DB read는 lock·성능 영향 가능) |

---

## 0. V3K 미션 재인용 (Phase A plan §0.1)

```text
V3K = V3 신기능을 STOM_Version_2U_C에 모두 반영한다.
LS Securities 직접 의존은 제외하고 Kiwoom증권 API/runtime을 유지한다.
STOM CLI surface의 외부 동작도 유지한다.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
feature flag는 모든 phase에서 default-OFF로 유지한다.
```

본 plan은 audit §6.2 #2 (production learning DB read)를 다룬다.

---

## A. Drivers + Scope

### A.1 Drivers

1. Phase B의 shadow read-only smoke가 read-only adapter 경계를 증명했다(`3eac14ec`). 다음 단계는 운영 `_database/`의 실제 learning DB를 읽는 것
2. read는 reversible하므로 위험이 cutover보다 낮음. F1(DB cutover) 전에 read를 먼저 작동시키는 것이 안전
3. F6 산식 #2 항목을 S2 → S3로 전이

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| 운영 `_database/` learning DB 파일을 `?mode=ro` SQLite URI로만 읽기 | 운영 DB write (영구 금지, P1) |
| `last_update < backtest_date` 규칙 검증 (L6) | shadow → 운영 DB cutover (F1 별도) |
| missing DB no-op diagnostic | feature flag ON 전환 (사용자 명시 승인 후 별도) |
| read-only smoke + production read smoke 2종 | analyzer output 전략 반영 (F3 별도) |

---

## B. Phase-specific invariants (L1–L9 보존 + 신규)

본 plan은 Phase A plan §B.1의 L1–L9를 모두 보존한다. 신규 invariant는 없다. 다음을 특히 강조한다.

- **L4 보존**: 운영 `_database/` 디렉터리 절대 변경 금지
- **L5 보존**: feature flag default-OFF
- **L6 보존**: `last_update < backtest_date` leakage 방지 규칙
- **L8 보존**: 운영 `_database/` DB 파일 commit 절대 금지

---

## C. 상세 실행 계획 (T01–T05)

### C.0 task별 실행/commit lane

| Task | 실행 lane | commit lane |
| --- | --- | --- |
| T01 (read-only connection 확장) | 양쪽 검증 | `STOM_Version_2U_C` |
| T02 (production read smoke 신설) | 양쪽 검증 | `STOM_Version_2U_C` |
| T03 (last_update < backtest_date 검증) | 양쪽 검증 | `STOM_Version_2U_C` |
| T04 (missing/lock fallback smoke) | 양쪽 검증 | `STOM_Version_2U_C` |
| T05 (CARRY_FORWARD_REGISTRY 갱신) | `STOM_Version_2U_C` | `STOM_Version_2U_C` |

### T01 — `V3KLearningDataAdapter`에 production read path 추가

- 목표: `?mode=ro` SQLite URI로 운영 `_database/` learning DB를 read-only로 여는 path 추가. 기존 shadow read 경로는 보존
- 변경 파일:
  - `strategy/v3k_analyzer_adapter.py` (수정 — 신규 production read method)
  - `strategy/v3k_learning_loader.py` 또는 동등 모듈 (조회 시 production source 선택 옵션)
- 변경 의도:
  - 새 method `read_production_learning_db(db_name, table_name) -> dict | None`
  - 입력: `_database/{db_name}` 경로, 미존재 시 no-op None
  - 출력: `PRAGMA table_info` + 일부 sample row (성능 영향 최소화)
  - **write 일체 금지**, `?mode=ro` URI 강제
- 완료 조건 (PASS/FAIL):
  ```powershell
  python -m py_compile strategy/v3k_analyzer_adapter.py
  python -c "from strategy.v3k_analyzer_adapter import V3KAnalyzerAdapter; assert hasattr(V3KAnalyzerAdapter, 'read_production_learning_db')"
  ```
  PASS: 둘 다 exit 0
- 선행: 없음 (Phase B 산출물 기반)

### T02 — production read smoke 신설

- 목표: `scripts/smoke_v3k_learning_db_production_read.py` 신설
- 변경 파일: `scripts/smoke_v3k_learning_db_production_read.py` (신규)
- 변경 의도:
  - 운영 `_database/pattern_analysis.db`, `volume_spike.db`, `volume_profile.db`, `volatility_pattern.db`, `volatility_stop_take.db` 5개 learning DB의 read 시도
  - 각 DB가 존재 시: `PRAGMA table_info` 출력 + row count 1건
  - 미존재 시: no-op diagnostic
  - lock 발생 시: 즉시 retry 1회 후 no-op
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_learning_db_production_read.py
  ```
  PASS: exit 0, stdout에 5개 DB 각각 결과(read/no-op/lock-fallback) 출력
- 선행: T01

### T03 — `last_update < backtest_date` 규칙 검증 smoke

- 목표: L6 invariant 자동검증
- 변경 파일: `scripts/smoke_v3k_learning_db_leakage_guard.py` (신규)
- 변경 의도:
  - 운영 learning DB의 `last_update` 컬럼 최대값을 read
  - 가상 backtest_date(현재 KST date)와 비교
  - `last_update >= backtest_date`인 row가 발견되면 leakage warning + exit 1
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_learning_db_leakage_guard.py
  ```
  PASS: exit 0, stdout에 "leakage guard PASS"
- 선행: T02

### T04 — missing/lock fallback smoke

- 목표: read 경로의 robustness 검증 (운영 환경에서 DB가 일시적으로 lock 또는 missing일 때)
- 변경 파일: `scripts/smoke_v3k_learning_db_fallback.py` (신규)
- 변경 의도:
  - DB rename 트릭으로 missing 상태 모의 → no-op diagnostic 확인
  - `BEGIN IMMEDIATE` 등 lock 모의 → retry-then-noop 확인
  - 양쪽 모두 exit 0
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_learning_db_fallback.py
  ```
  PASS: exit 0, missing/lock 두 시나리오 모두 no-op
- 선행: T03

### T05 — `docs/CARRY_FORWARD_REGISTRY.md`에 V3K-PROD-READ 섹션 추가

- 목표: registry 등록
- 변경 파일: `docs/CARRY_FORWARD_REGISTRY.md` (수정)
- 변경 의도: V3K-DESIGN-1B / V3K-PHASE-A / V3K-PHASE-B 패턴 follow. Records, Decision, Verification, Next phase, Directive 기재
- 완료 조건:
  ```powershell
  Select-String -Path docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-PROD-READ"
  ```
  PASS: 매치 1건
- 선행: T01–T04

---

## D. 검증 단계 V01–V08

| # | 명령 | 실행 lane | PASS |
| --- | --- | --- | --- |
| V01 | `python -m py_compile strategy/v3k_analyzer_adapter.py scripts/smoke_v3k_learning_db_production_read.py scripts/smoke_v3k_learning_db_leakage_guard.py scripts/smoke_v3k_learning_db_fallback.py` | 양쪽 | exit 0 |
| V02 | `python scripts/smoke_v3k_learning_db_production_read.py` | 2U_C | exit 0 + 5 DB 결과 |
| V03 | `python scripts/smoke_v3k_learning_db_leakage_guard.py` | 2U_C | exit 0 + leakage PASS |
| V04 | `python scripts/smoke_v3k_learning_db_fallback.py` | 2U_C | exit 0 + missing/lock 모두 no-op |
| V05 | `git -C C:/System_Trading/STOM/STOM_V.wt-dev status --porcelain -- _database/` | 양쪽 | (빈 출력) — 운영 DB 변경 0건 |
| V06 | `git log --all -- '*.db'` | 양쪽 | 0건 — DB 파일 commit 금지 |
| V07 | `python scripts/audit_v3k_verify_1a.py --base 57496d24` | 양쪽 | passed |
| V08 | `python scripts/verify_release_sync.py` | 양쪽 | "release sync preflight passed" |

---

## E. 위험 매트릭스

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지명령, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | 운영 DB write (P1 위반) | 치명 | 매우 낮음 | (`?mode=ro` URI 누락, V05 git status 비어있음 검사, exit 1 + rollback) |
| R2 | 운영 DB lock 장기 점유 | 높음 | 낮음 | (BEGIN IMMEDIATE 미사용, V04 lock smoke, retry-then-noop) |
| R3 | leakage (`last_update >= backtest_date`) | 높음 | 중간 | (L6 위반, V03 leakage smoke, exit 1) |
| R4 | DB 파일 commit | 높음 | 낮음 | (`.gitignore *.db` 우회, V06 git log, commit reject) |
| R5 | Kiwoom runtime 영향 | 치명 | 매우 낮음 | (trade/utility/ 변경, V07 audit, runtime guard reject) |
| R6 | LS 직접 의존 신규 | 치명 | 매우 낮음 | (LS marker grep, audit guard, reject) |

---

## F. Rollback

### F.1 read smoke 실패 또는 leakage 발견

```powershell
# 1) read smoke 결과를 .omx/reports/v3k-prod-read-fail.json에 캡처
# 2) 코드 변경을 git restore --staged
# 3) Phase B 산출물 기준으로 baseline 복귀 (3eac14ec)
git -C C:/System_Trading/STOM/STOM_V.wt-dev checkout 3eac14ec -- strategy/v3k_analyzer_adapter.py
# 4) verify_release_sync 확인
python scripts/verify_release_sync.py
```

### F.2 운영 DB 변경 발견 시 (R1 발현)

```powershell
# 1) 즉시 변경 사항 unstage + working tree 복귀
git -C C:/System_Trading/STOM/STOM_V.wt-dev restore -- _database/
git -C C:/System_Trading/STOM/STOM_V.wt-dev status --porcelain -- _database/  # 빈 출력 확인
# 2) write 경로 코드 grep
Select-String -Path strategy/v3k_analyzer_adapter.py -Pattern "INSERT|UPDATE|DELETE|DROP"
# 3) write 코드 제거 후 T01 재실행
```

---

## G. 산출물

### G.1 Commit 포함 (6건)

| # | 분류 | 경로 |
| ---: | --- | --- |
| 1 | 수정 | `strategy/v3k_analyzer_adapter.py` (production read method) |
| 2 | 신규 | `scripts/smoke_v3k_learning_db_production_read.py` |
| 3 | 신규 | `scripts/smoke_v3k_learning_db_leakage_guard.py` |
| 4 | 신규 | `scripts/smoke_v3k_learning_db_fallback.py` |
| 5 | 수정 | `docs/CARRY_FORWARD_REGISTRY.md` (V3K-PROD-READ 섹션) |
| 6 | 신규 | `docs/update_log/<YYYY-MM-DD>_v3k_production_learning_db_read.md` (실행 결과 보고서) |

### G.2 Ephemeral

| # | 경로 |
| --- | --- |
| E1 | `.omx/reports/v3k-prod-read.json` |
| E2 | `.omx/reports/v3k-prod-leakage-guard.json` |

---

## H. Commit message 한국어 sample

### H.1 commit 1+2 — production read 도입

```text
V3K production learning DB read 경로를 read-only로 도입한다

- `strategy/v3k_analyzer_adapter.py`에 `read_production_learning_db` method를 추가한다.
- `?mode=ro` SQLite URI 강제로 운영 `_database/`를 절대 변경하지 않는다.
- production read smoke를 추가해 5 learning DB의 read/no-op/lock-fallback을 검증한다.
```

### H.2 commit 3 — leakage guard

```text
V3K learning DB leakage guard smoke를 추가한다

- L6 invariant `last_update < backtest_date`를 자동검증한다.
- leakage 발견 시 exit 1로 차단한다.
- 운영 DB는 read-only로만 접근한다.
```

### H.3 commit 4 — fallback smoke

```text
V3K learning DB missing/lock fallback smoke를 추가한다

- missing DB 시 no-op diagnostic을 확인한다.
- lock 시 retry-then-noop 동작을 검증한다.
- 운영 환경의 일시적 lock에도 안전하게 동작한다.
```

### H.4 commit 5 — registry

```text
V3K-PROD-READ 항목을 carry-forward registry에 등록한다

- production learning DB read 경계와 검증 명령을 기재한다.
- Phase B 산출물(`3eac14ec`)의 후속 단계로 위치를 명시한다.
```

---

## I. ADR 요지

- **Decision**: production learning DB는 `?mode=ro` SQLite URI로만 읽고, `last_update < backtest_date` leakage guard를 자동검증한다. Phase B의 shadow read-only adapter 경로는 보존하며 production read 경로를 추가만 한다
- **Drivers**: L1·L4·L5·L6·L8 보존, F6 산식 #2 항목 S2→S3 전이, F1 cutover 전 read 작동 확보
- **Alternatives considered**:
  - production write 도입 → P1 위반으로 기각
  - shadow → production 동시 read → 복잡도 증가로 보류 (필요 시 별도 phase)
- **Why chosen**: read-only는 reversible하고 위험 낮음. F1 cutover의 precondition으로 자연스러움
- **Consequences**:
  - 긍정: F6 #2 항목 S3 도달, F1 cutover의 read 측 검증 baseline 확보
  - 부정: production DB 부재 시 no-op 빈도 증가 (운영 환경 점검 필요)
- **Follow-ups**:
  - F1 DB cutover plan에서 본 phase의 read 결과를 입력으로 사용
  - 일정 기간 production read 안정성 모니터링 후 S3 → S4 전이 별도 phase

---

## J. 핵심 설계 질문

### Q1. production DB가 일시적으로 lock된 경우 동작은?
A. retry 1회 후 no-op diagnostic. exit 0 유지. lock 빈도가 높으면 V04 smoke에서 발견되어 별도 retry 정책 검토.

### Q2. `last_update >= backtest_date` 발견 시 처리?
A. exit 1로 차단. L6 invariant 위반. F.1 rollback으로 read 경로 자체를 비활성화하고 별도 leakage 분석.

### Q3. shadow와 production 둘 다 사용?
A. Phase B 산출물은 shadow read-only, 본 plan은 production read-only 추가. 두 경로는 독립. 어느 것을 사용할지 결정하는 운영 정책은 F1(cutover)에서 정의.

### Q4. Phase letter는?
A. audit §8에 본 phase가 없음. F2(letter remapping decision) §3.2 convention에 따라 `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md`로 파일명만 사용. letter 부여는 closeout 시 F2 매핑 표에 행 추가 가능.

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T05 모두 commit
- V01–V08 모두 PASS
- F6 #2 항목 S2 → S3 전이 확인

### K.2 본 phase 완료 후 진행 가능한 phase

- **F1 (DB cutover plan)**: 본 phase의 production read 작동이 cutover의 precondition
- **F3 (Phase F analyzer 전략 반영)**: analyzer가 production learning DB를 source로 사용 가능
- **closure gate (F7)**: §1.1 #2 항목 종착 단계 평가에 본 phase 결과 사용

### K.3 본 plan freeze 정책

본 phase 완료 commit 후 본 plan은 freeze. 추가 read 정책 변경은 별도 phase plan으로 분리.

---

## L. 관련 문서

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan, §0 미션 + §K 전환 지침)
- `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md` (Phase B plan)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2, letter convention)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6, S0–S4 산식)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7, closure gate)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #2)
