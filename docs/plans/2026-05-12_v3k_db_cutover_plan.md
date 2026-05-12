# V3K DB Cutover 실행 계획 (F1)

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| audit §6.2 항목 | #1 후반부 (shadow DB cutover) |
| 현재 단계 (F6 산식) | S2 (50%) — shadow 생성 완료, cutover 미진행 |
| 목표 단계 | S4 (100%) operational cutover |
| Phase letter | audit §8에 없음. F2 convention에 따라 별도 phase로 분류. letter 부여는 closure 시 |
| 의존 입력 | Phase A (`1196946a`) shadow rehearsal 완료, F5 production read S3 도달 권장 |
| 위험도 | **치명** (운영 DB 직접 영향) — `--deliberate` ralplan 권장 |

---

## 0. V3K 미션 재인용

```text
V3K = V3 신기능을 2U_C에 모두 반영. LS 제외, Kiwoom 유지, CLI 보존.
DB는 운영 _database/와 격리된 _database_v3k_shadow/로 separate 후 단계적 cutover한다.
```

본 plan은 위 마지막 줄의 "단계적 cutover" 책임이다.

---

## A. Drivers + Scope

### A.1 Drivers

1. F6 산식 #1 항목 S2 → S4 전이를 위한 cutover 작업
2. cutover는 영구 변경이므로 backup·rollback·검증 절차가 정본화되어야 함
3. F1은 closure gate(F7 §1.1 #1)의 종착 조건

### A.2 Scope

| In scope | Out of scope |
| --- | --- |
| `_database_v3k_shadow/` 7 DB 내용을 운영 `_database/`로 cutover | LS Securities 의존 (L7 영구 금지) |
| cutover 전 full backup + checksum 정본화 | shadow DB의 read-only smoke (Phase B에서 완료) |
| cutover 후 1주일 모니터링 + rollback gate | analyzer output 전략 반영 (F3 별도) |
| operational rollback 절차 | microstructure engine 이식 (F4 별도) |
| backup 파일 archive 정책 | feature flag 자동 ON (사용자 명시 승인 후 별도 commit) |

---

## B. Phase-specific invariants (L1–L9 + 신규 LC1–LC3)

### B.1 보존 invariants (L1–L9)

본 plan은 모든 L1–L9를 보존한다. 특히:
- **L4 일시 예외**: cutover 시점에 한해 운영 `_database/`에 write 발생. 단, full backup + verification gate 필수
- **L7·L8·L9**: 영구 보존

### B.2 신규 cutover-specific invariants (LC1–LC3)

cutover phase 전용 추가 invariant. closure 시 freeze.

| # | invariant | 사유 |
| --- | --- | --- |
| LC1 | cutover 전 운영 `_database/` 전체 backup 필수 (`_database.backup.<utc>/`) | rollback 가능성 보장 |
| LC2 | cutover commit은 단일 commit + 사용자 명시 승인 dance를 거친다 | 영구 변경의 가시성 보장 |
| LC3 | cutover 후 7일 모니터링 기간 동안 새 cutover 금지 | 안정성 확인 시간 |

---

## C. 상세 실행 계획 (T01–T08)

### C.0 task별 실행/commit lane

| Task | 실행 lane | commit lane |
| --- | --- | --- |
| T01 (backup script + checksum) | 양쪽 검증 | 2U_C |
| T02 (cutover script) | **2U_C 전용** | 2U_C |
| T03 (cutover dry-run smoke) | 양쪽 검증 | 2U_C |
| T04 (operational rollback script) | 양쪽 검증 | 2U_C |
| T05 (cutover 실행 — 사용자 명시 승인) | **2U_C 전용**, 사용자 승인 후 | 2U_C |
| T06 (post-cutover health smoke) | **2U_C 전용** | 2U_C |
| T07 (7일 모니터링 audit) | 양쪽 검증 | 2U_C |
| T08 (registry V3K-CUTOVER 등록) | 2U_C | 2U_C |

### T01 — backup + checksum script 신설

- 목표: 운영 `_database/` 전체를 timestamped backup 디렉터리로 복사 + sha256 checksum 생성
- 변경 파일:
  - `scripts/backup_operational_database.py` (신규)
- 변경 의도:
  - argparse: `--target-dir` (default `_database.backup.<utc>/`), `--dry-run` (default), `--apply` (LC1 enforce)
  - 모든 파일을 `_database/`에서 target으로 복사 + sha256 hex 64자 manifest 생성
  - manifest: `.omx/reports/v3k-db-backup-<utc>.json` (commit 가능 — schema audit trail와 동등)
  - **read-only 강제**: 운영 DB는 절대 변경 없음
- 완료 조건:
  ```powershell
  python -m py_compile scripts/backup_operational_database.py
  python scripts/backup_operational_database.py --dry-run --stdout
  ```
  PASS: exit 0 + dry-run manifest 출력
- 선행: 없음

### T02 — cutover script 신설

- 목표: shadow → 운영 cutover 실행 script. dry-run / apply 분리
- 변경 파일:
  - `scripts/cutover_v3k_shadow_to_database.py` (신규)
- 변경 의도:
  - argparse: `--apply` required, `--backup-first` required (LC1 enforce), `--shadow-dir` default `_database_v3k_shadow`, `--target-dir` default `_database`
  - 절차: (a) backup_operational_database.py 호출 → (b) checksum 통과 확인 → (c) shadow DB 파일을 운영 path로 복사 → (d) `?mode=ro` URI로 sanity read
  - branch 가드: `STOM_V.wt-dev` 외에서 실행 시 SystemExit (R3 패턴)
  - 환경 변수 `V3K_CUTOVER_USER_ACK=1` 강제 (LC2 enforce — 사용자 명시 승인 marker)
  - cutover report: `.omx/reports/v3k-db-cutover-<utc>.json`
- 완료 조건:
  ```powershell
  python -m py_compile scripts/cutover_v3k_shadow_to_database.py
  python scripts/cutover_v3k_shadow_to_database.py --apply --backup-first --shadow-dir _database_v3k_shadow_TEST  # ack 미설정 시 reject 확인
  ```
  PASS: 첫 번째 exit 0, 두 번째 exit 1 + "V3K_CUTOVER_USER_ACK required" 메시지
- 선행: T01

### T03 — cutover dry-run smoke 신설

- 목표: cutover 실제 실행 없이 시뮬레이션 + 모든 가드 작동 확인
- 변경 파일:
  - `scripts/smoke_v3k_cutover_dryrun.py` (신규)
- 변경 의도:
  - 가상 backup target + 가상 cutover target 사용
  - 모든 가드(branch, ack env, backup-first, checksum) 작동 시나리오 검증
  - exit 0 시 cutover script가 실제 실행 가능 상태임을 증명
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_cutover_dryrun.py
  ```
  PASS: exit 0 + 모든 가드 시나리오 PASS
- 선행: T02

### T04 — operational rollback script 신설

- 목표: cutover 후 문제 발견 시 backup으로 복귀
- 변경 파일:
  - `scripts/rollback_v3k_cutover.py` (신규)
- 변경 의도:
  - argparse: `--backup-dir` required, `--apply` required, `--verify-checksum` (default ON)
  - backup의 checksum 검증 후 `_database/`를 backup 내용으로 복원
  - rollback report: `.omx/reports/v3k-cutover-rollback-<utc>.json`
- 완료 조건:
  ```powershell
  python -m py_compile scripts/rollback_v3k_cutover.py
  python scripts/rollback_v3k_cutover.py --backup-dir _database.backup.TEST/ --apply  # 가상 backup으로 시뮬레이션
  ```
  PASS: 두 명령 모두 exit 0
- 선행: T01, T02

### T05 — cutover 실행 (사용자 명시 승인 후 단일 commit)

- 목표: T01–T04 통과 후 실제 cutover 실행
- 변경 파일:
  - 운영 `_database/*.db` 파일들 (cutover로 내용 변경, **commit 대상 아님** — L8)
  - `.omx/reports/v3k-db-backup-<utc>.json` (commit 대상, audit trail)
  - `.omx/reports/v3k-db-cutover-<utc>.json` (commit 대상, audit trail)
- 사전 조건:
  - F5 (production read) 완료
  - 사용자 명시 승인 (form: F7 §2 Gate 2 유사)
  - `V3K_CUTOVER_USER_ACK=1` 환경 변수 설정
- 실행 절차:
  1. `python scripts/backup_operational_database.py --apply` → backup 완료
  2. `python scripts/cutover_v3k_shadow_to_database.py --apply --backup-first` → cutover 완료
  3. report 2건만 git add + 단일 commit (LC2 enforce)
- 완료 조건:
  ```powershell
  python scripts/v3k_db_health.py --read-only --strict
  ```
  PASS: exit 0 + `ok=true` + `_database/` 7 DB 모두 검증
- 선행: T01–T04 + 사용자 명시 승인

### T06 — post-cutover health smoke

- 목표: cutover 직후 운영 DB의 schema_hash invariant 검증 (L1 보존)
- 변경 파일:
  - `scripts/smoke_v3k_post_cutover_schema_hash.py` (신규)
- 변경 의도: 운영 `_database/`의 각 DB에 대해 `compute_schema_hash` 재계산 후 manifest의 schema_hash와 비교. drift 발견 시 exit 1 + rollback trigger
- 완료 조건:
  ```powershell
  python scripts/smoke_v3k_post_cutover_schema_hash.py
  ```
  PASS: exit 0 + 7 DB 모두 schema_hash 일치
- 선행: T05

### T07 — 7일 모니터링 audit (LC3 enforce)

- 목표: cutover 후 7일간 운영 DB 안정성 모니터링
- 변경 파일:
  - `scripts/audit_v3k_post_cutover_monitor.py` (신규)
- 변경 의도:
  - cutover commit 이후 경과일 계산 → 7일 미만이면 새 cutover commit 거부
  - 7일 후 통과 시 다음 cutover 또는 closure 진입 허용
- 완료 조건:
  ```powershell
  python scripts/audit_v3k_post_cutover_monitor.py
  ```
  PASS: 7일 경과 시 exit 0, 미경과 시 exit 1 + 잔여 일수 출력
- 선행: T05

### T08 — `docs/CARRY_FORWARD_REGISTRY.md`에 V3K-CUTOVER 섹션 추가

- 목표: registry 등록
- 완료 조건:
  ```powershell
  Select-String -Path docs/CARRY_FORWARD_REGISTRY.md -Pattern "^## V3K-CUTOVER"
  ```
  PASS: 매치 1건
- 선행: T01–T07

---

## D. 검증 단계 V01–V12

| # | 명령 | lane | PASS |
| --- | --- | --- | --- |
| V01 | py_compile 4 scripts | 양쪽 | exit 0 |
| V02 | `python scripts/backup_operational_database.py --dry-run` | 양쪽 | manifest 출력 |
| V03 | `python scripts/smoke_v3k_cutover_dryrun.py` | 양쪽 | 모든 가드 PASS |
| V04 | `python scripts/cutover_v3k_shadow_to_database.py --apply --backup-first` (ack 미설정) | 2U_C | exit 1 + ack required 메시지 |
| V05 | `python scripts/backup_operational_database.py --apply` (T05 실행) | 2U_C, ack 후 | backup 완료 |
| V06 | `python scripts/cutover_v3k_shadow_to_database.py --apply --backup-first` (ack 설정) | 2U_C, ack 후 | cutover 완료 |
| V07 | `python scripts/v3k_db_health.py --read-only --strict` | 2U_C | `ok=true` |
| V08 | `python scripts/smoke_v3k_post_cutover_schema_hash.py` | 2U_C | 7 DB schema_hash 일치 |
| V09 | `python scripts/rollback_v3k_cutover.py --backup-dir ... --apply` (가상 시뮬) | 2U_C | rollback 동작 확인 |
| V10 | `git -C ... status --porcelain -- _database/*.db` | 2U_C | 0건 (L8 보존) |
| V11 | `python scripts/audit_v3k_post_cutover_monitor.py` | 양쪽 | 7일 미경과면 exit 1 |
| V12 | `python scripts/verify_release_sync.py` | 양쪽 | preflight passed |

---

## E. 위험 매트릭스

| ID | 위험 | 영향도 | 발생가능성 | (Trigger, 자동탐지, 차단액션) |
| --- | --- | --- | --- | --- |
| R1 | cutover 도중 운영 DB 손상 | 치명 | 낮음 | (cutover 실패, V07 health smoke FAIL, T04 rollback 즉시 실행) |
| R2 | backup checksum 불일치 | 치명 | 매우 낮음 | (T01 sha256 mismatch, T02가 backup-first 검증 시 exit 1, cutover 중단) |
| R3 | cutover 시 schema drift (L1 위반) | 치명 | 낮음 | (T06 schema_hash 불일치, T04 rollback) |
| R4 | 7일 모니터링 미경과에 새 cutover | 높음 | 중간 | (T07 audit exit 1, 새 cutover commit 거부) |
| R5 | 사용자 명시 승인 없이 cutover 실행 | 치명 | 낮음 | (`V3K_CUTOVER_USER_ACK` 미설정, T02 exit 1) |
| R6 | wrong worktree에서 cutover 실행 | 치명 | 낮음 | (branch 가드, T02 SystemExit) |
| R7 | DB 파일 commit (L8 위반) | 높음 | 낮음 | (V10 git status, `.gitignore *.db` + audit guard) |
| R8 | LS 직접 의존 신규 | 치명 | 매우 낮음 | (LS marker grep, audit reject) |
| R9 | Kiwoom runtime 영향 | 치명 | 매우 낮음 | (trade/ 변경, audit reject) |
| R10 | cutover 후 production read 실패 (F5 회귀) | 높음 | 중간 | (F5 smoke 재실행 FAIL, T04 rollback) |

---

## F. Rollback 절차

### F.1 cutover 실패 (T05 도중 또는 직후)

```powershell
# 1) cutover commit 즉시 revert
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <cutover-commit-sha> --no-edit
# 2) 운영 DB를 backup에서 복원
python scripts/rollback_v3k_cutover.py --backup-dir _database.backup.<utc>/ --apply
# 3) post-cutover health smoke 재실행
python scripts/smoke_v3k_post_cutover_schema_hash.py
# 4) verify_release_sync
python scripts/verify_release_sync.py
```

### F.2 7일 모니터링 중 문제 발견

```powershell
# 1) cutover commit revert
git -C C:/System_Trading/STOM/STOM_V.wt-dev revert <cutover-commit-sha> --no-edit
# 2) backup 복원
python scripts/rollback_v3k_cutover.py --backup-dir _database.backup.<utc>/ --apply
# 3) 문제 원인 phase plan 신설 (F.X) 후 재시도
```

### F.3 backup 자체가 손상된 경우

`_database.backup.<utc>.archive/` 디렉터리에 보존된 가장 최근 정상 backup을 사용. 정상 backup이 없으면 V3 upstream에서 schema 재구성 (긴급 절차, 별도 plan 필요).

---

## G. 산출물

### G.1 Commit 포함 (10건)

| # | 분류 | 경로 |
| ---: | --- | --- |
| 1 | 신규 | `scripts/backup_operational_database.py` |
| 2 | 신규 | `scripts/cutover_v3k_shadow_to_database.py` |
| 3 | 신규 | `scripts/smoke_v3k_cutover_dryrun.py` |
| 4 | 신규 | `scripts/rollback_v3k_cutover.py` |
| 5 | 신규 | `scripts/smoke_v3k_post_cutover_schema_hash.py` |
| 6 | 신규 | `scripts/audit_v3k_post_cutover_monitor.py` |
| 7 | 수정 | `.gitignore` (backup 디렉터리 보존 정책) |
| 8 | 수정 | `docs/CARRY_FORWARD_REGISTRY.md` (V3K-CUTOVER 섹션) |
| 9 | 신규 | `.omx/reports/v3k-db-backup-<utc>.json` (audit trail) |
| 10 | 신규 | `.omx/reports/v3k-db-cutover-<utc>.json` (audit trail) |

### G.2 Ephemeral 또는 비추적

- `_database.backup.<utc>/` — backup 디렉터리 (rollback용, commit 금지)
- `_database/*.db` — cutover 결과로 변경된 운영 DB (commit 금지, L8)

---

## H. Commit message 한국어 sample

### H.1 cutover 직전 — script 신설

```text
V3K DB cutover script와 backup/rollback 절차를 도입한다

- `backup_operational_database.py`와 `cutover_v3k_shadow_to_database.py`를 신규 작성한다.
- 사용자 명시 승인 환경 변수(`V3K_CUTOVER_USER_ACK`)를 강제한다.
- backup checksum 통과 후에만 cutover가 진행된다.
```

### H.2 cutover 실행 (사용자 명시 승인 후 단일 commit)

```text
V3K shadow DB를 운영 _database/로 cutover한다

- backup checksum이 통과한 후 7개 shadow DB를 운영 path로 복사한다.
- post-cutover schema_hash 검증으로 L1 invariant를 확인한다.
- 7일 모니터링 기간 동안 새 cutover는 금지된다.
- 사용자 명시 승인 marker는 V3K_CUTOVER_USER_ACK=1로 commit 시점에 기록한다.
```

### H.3 rollback

```text
V3K cutover를 backup에서 복원한다

- checksum 검증 후 운영 _database/를 backup 시점으로 복원한다.
- post-rollback health smoke가 7 DB 모두 PASS한다.
- 원인 phase plan을 별도로 작성한 후 재시도한다.
```

---

## I. ADR 요지

- **Decision**: shadow → 운영 cutover는 backup-first + 사용자 명시 승인 + 7일 모니터링 3-tuple gate로 운영. 단일 cutover commit (LC2)
- **Drivers**: L4 cutover 1회성 예외, L8 보존, audit §6.2 #1 종착 조건, F7 closure gate의 입력
- **Alternatives considered**:
  - in-place cutover (backup 없이) → R1 위험으로 기각
  - 점진적 cutover (DB 1개씩) → 7 DB의 schema_hash invariant가 한 묶음이므로 부분 cutover는 schema drift 위험 → 기각
  - shadow 영구 유지 (cutover 없음) → audit §6.2 #1이 종착하지 못함 → 기각
- **Why chosen**: backup + checksum + ack + 7일 모니터링 4-층 안전망이 cutover의 영구 변경 위험을 reversible하게 만든다
- **Consequences**:
  - 긍정: F6 #1 항목 S4 도달, F7 closure gate 통과
  - 부정: cutover 후 7일은 다른 cutover 금지로 일정 정체. 단, 안전성 우선
- **Follow-ups**:
  - shadow 디렉터리 정책 (F7 §4.3에서 결정)
  - cutover 후 production learning DB가 shadow와 의미적으로 동일한지 검증 smoke

---

## J. 핵심 설계 질문

### Q1. cutover 도중 power failure 시?
A. backup이 timestamped로 보존되어 있으므로 T04 rollback으로 복원. cutover script는 transactional하지 않으나 backup이 최후 방어선.

### Q2. 7일 모니터링은 어떻게 enforce되는가?
A. T07 `audit_v3k_post_cutover_monitor.py`가 cutover commit timestamp + 7일 경과 검사. 미경과 시 새 cutover script 실행 거부.

### Q3. backup 디렉터리는 commit되는가?
A. **아니다**. `_database.backup.<utc>/`는 `.gitignore`에 추가되어 commit 금지. backup의 sha256 manifest(`.omx/reports/v3k-db-backup-<utc>.json`)만 commit. 이는 audit trail로 schema_hash manifest와 동등 정책 (Phase A plan §G.1 #7 예외).

### Q4. cutover 후 shadow DB는?
A. closure 시점에 F7 §4.3 결정에 따른다. cutover 직후에는 보존(F1 본 plan에서는 결정 안 함). rollback 가능성을 위해 7일 모니터링 동안은 무조건 보존.

### Q5. Phase letter는?
A. audit §8에 본 phase가 없으므로 letter 미부여. F2 §3.2 convention에 따라 파일명만 사용. closure 시 F2 매핑 표에 행 추가 가능.

---

## K. 다음 단계 전환 지침

### K.1 완료 조건

- T01–T08 모두 commit (단, T05/T06/T07은 사용자 명시 승인 후)
- V01–V12 모두 PASS
- F6 산식 #1 항목 S2 → S4 전이 확인
- 7일 모니터링 통과

### K.2 본 phase 완료 후 진행 가능한 phase

- **F3 (Phase F analyzer 전략 반영)**: cutover된 운영 DB를 analyzer가 use하는 시나리오
- **closure gate (F7)**: §1.1 #1 종착 조건 PASS

### K.3 본 plan freeze 정책

cutover 완료 commit 후 본 plan은 freeze. 추가 cutover가 필요하면 별도 phase plan으로 분리.

---

## L. 관련 문서

- `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md` (Phase A plan, shadow rehearsal)
- `docs/plans/2026-05-12_v3k_production_learning_db_read_plan.md` (F5, precondition)
- `docs/update_log/2026-05-12_v3k_phase_letter_remapping_decision.md` (F2, letter convention)
- `docs/update_log/2026-05-12_v3k_progress_metric_methodology.md` (F6, S0–S4 산식)
- `docs/update_log/2026-05-12_v3k_mission_closeout_procedure.md` (F7, closure gate)
- `docs/update_log/2026-05-10_2uc_v3k_full_feature_audit.md` (§6.2 #1)
