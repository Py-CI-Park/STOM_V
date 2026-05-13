# V3K F1 actual DB cutover approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 053 |
| source | Page029 F1 DB cutover pre-ralplan, Page030 cutover scripts dry-run, Page031 actual cutover approval gate, Page052 Phase H H-2/H-3 approval prep |
| marker | `F1_ACTUAL_DB_CUTOVER_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `f1-actual-db-cutover-await-user-approval` |

---

## 1. 요약

F1 actual DB cutover는 운영 `_database/`를 영구 변경할 수 있는 critical gate다. 이번 Page053에서는 actual cutover를 하지 않고, 사용자 승인, USER_ACK, backup checksum manifest, rollback, post-cutover health, 7-day monitoring 조건을 명확한 감사 대상으로 고정했다.

No operating DB write: 운영 `_database/` write, `_database_v3k_shadow/` → `_database/` actual cutover, `V3K_CUTOVER_USER_ACK=1`, backup apply, rollback apply, DB 파일 commit, backup directory commit, Kiwoom live runtime 변경, LS Securities 직접 의존 추가는 수행하지 않았다.

---

## 2. 준비된 근거

| 근거 | 설명 |
| --- | --- |
| `scripts/backup_operational_database.py` | backup helper. 기본 dry-run, apply는 branch/ACK guard 필요 |
| `scripts/cutover_v3k_shadow_to_database.py` | cutover helper. apply는 ACK, backup-first, backup-dir, operating-target guard 필요 |
| `scripts/rollback_v3k_cutover.py` | rollback helper. apply는 ACK와 operating-target guard 필요 |
| `scripts/smoke_v3k_cutover_dryrun.py` | tempfile-only backup/cutover/rollback guard smoke |
| `scripts/v3k_db_health.py` | read-only health report |
| `scripts/run_v3k_audit_suite.py` | V3K 전체 audit suite |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | 현재 판정 |
| --- | --- | --- |
| 운영 DB write 금지 | artifact guard, git status artifact scope | 유지 |
| DB 파일 commit 금지 | artifact guard | 유지 |
| USER_ACK 없는 cutover 금지 | `V3K_CUTOVER_USER_ACK=1` script guard | 유지 |
| backup-first 없는 cutover 금지 | cutover script guard + smoke | 유지 |
| backup checksum manifest 필요 | backup/cutover script + smoke | actual cutover 전 필수 |
| rollback 가능성 선행 | rollback script + smoke | actual cutover 전 필수 |
| post-cutover health 필요 | `v3k_db_health.py`, F5 smoke, VERIFY set | actual cutover 전 필수 |
| 7-day monitoring 필요 | Page029/031 LC3 | actual cutover 전 필수 |
| Kiwoom live runtime 유지 | VERIFY-1A | 유지 |
| LS Securities 직접 의존 금지 | VERIFY-1A, LS marker audit | 유지 |

---

## 4. Actual cutover 전 사용자 결정지

1. `F1 actual DB cutover` gate 명시 승인 여부
2. USER_ACK 형태: `V3K_CUTOVER_USER_ACK=1`, update_log, registry 중 어떤 것을 정식 승인 기록으로 삼을지 결정
3. backup 범위: 운영 `_database/` full backup apply 위치와 checksum manifest 보존 방식
4. cutover 명령 범위: `--apply --backup-first --backup-dir <backup> --allow-operating-target` 허용 여부
5. rollback 범위: `rollback_v3k_cutover.py --apply --backup-dir <backup> --allow-operating-target` 즉시 실행 가능성
6. post-cutover health: schema/F5/VERIFY/nonrelease sync 필수 검증 묶음
7. 7-day monitoring: timestamp, owner, alert, fallback trigger, 새 cutover 금지 규칙

---

## 5. 남은 상태

현재 다음 후보는 `f1-actual-db-cutover-await-user-approval`이다. 사용자가 위 gate를 명시 승인하고 backup/rollback/post-health/7-day monitoring 조건을 확정하기 전까지 actual cutover는 수행하지 않는다.

Directive: `F1_ACTUAL_DB_CUTOVER_APPROVAL_PREP`는 승인 준비 기록이며 운영 DB write, actual cutover, USER_ACK 생성, backup apply, rollback apply, DB 파일 commit, Kiwoom live runtime 변경으로 해석하면 안 된다.
