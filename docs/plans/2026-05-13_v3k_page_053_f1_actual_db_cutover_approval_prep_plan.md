# V3K Page 053 - F1 actual DB cutover approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 052 / Phase H H-2/H-3 Kiwoom live dry-run approval prep |
| 현재 page | Page 053 / F1 actual DB cutover approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `f1-actual-db-cutover-await-user-approval` |
| 목적 | actual `_database_v3k_shadow` → `_database` cutover 전에 필요한 사용자 승인, USER_ACK, backup apply, checksum manifest, post-cutover health, rollback, 7-day monitoring 조건을 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual operating DB write는 critical |
| 실제 DB write 여부 | 아님. 운영 `_database/` write 없이 approval prep 문서화만 수행한다. |

---

## 1. 목표 재확인

V3K의 목표는 **LS Securities 직접 의존성을 제외하고 Kiwoom API/주문/청산/live runtime을 유지한 채 V3의 학습/분석/DB/backtest/realtime 기능을 `STOM_Version_2U_C`에 이행**하는 것이다.

F1 actual DB cutover는 V3K에서 운영 DB를 영구 변경할 수 있는 첫 critical gate다. Page030에서 backup/cutover/rollback script와 tempfile dry-run은 준비되었고, Page031에서 actual cutover가 사용자 승인 전 blocked임을 문서화했다. Page053은 이 blocked 상태를 최신 gate 흐름에 맞춰 다시 approval prep packet으로 고정하되, 운영 DB write는 수행하지 않는다.

---

## 2. 현재 F1 준비 상태

| 증거 | 역할 | 현재 상태 |
| --- | --- | --- |
| `scripts/backup_operational_database.py` | 운영 DB backup helper. 기본 dry-run, `--apply`는 ACK/branch guard 필요 | staged |
| `scripts/cutover_v3k_shadow_to_database.py` | shadow → target cutover helper. 기본 dry-run, apply는 backup-first/ACK/operating-target guard 필요 | staged |
| `scripts/rollback_v3k_cutover.py` | backup manifest 기준 rollback helper. apply는 ACK/operating-target guard 필요 | staged |
| `scripts/smoke_v3k_cutover_dryrun.py` | tempfile-only backup/cutover/rollback guard smoke | PASS 대상 |
| `scripts/v3k_db_health.py` | read-only DB health report | PASS 대상 |
| `scripts/run_v3k_audit_suite.py` | 전체 V3K default-OFF, artifact guard, nonrelease sync | PASS 대상 |

---

## 3. Prompt-to-artifact checklist

| 요구사항 | concrete evidence | Page053 처리 |
| --- | --- | --- |
| 운영 `_database/` write 금지 | artifact guard, git status artifact scope | actual DB write 미수행 |
| DB 파일 commit 금지 | artifact guard | DB file commit 없음 |
| backup-first 없이는 cutover 금지 | `smoke_v3k_cutover_dryrun.py` | `--backup-first` 필수 조건 유지 |
| USER_ACK 없는 cutover 금지 | script guard + smoke | `V3K_CUTOVER_USER_ACK=1` 필요 조건 명시 |
| backup checksum manifest 필요 | backup/cutover script + smoke | backup checksum manifest 필수 조건 명시 |
| rollback 가능성 선행 | rollback script + smoke | rollback path 필수 조건 명시 |
| post-cutover health 필요 | `v3k_db_health.py`, F5 smoke, VERIFY set | post-cutover health 필수 조건 명시 |
| 7일 monitoring 필요 | Page029/031 LC3 | 7-day monitoring 필수 조건 명시 |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A | actual runtime 미변경 |
| LS Securities 직접 의존 금지 | VERIFY-1A / LS marker audit | F1 prep에도 LS broker 의존성 금지 |

---

## 4. Actual F1 cutover 전 필수 승인 조건

1. 사용자가 `F1 actual DB cutover` gate를 명시적으로 승인한다.
2. `V3K_CUTOVER_USER_ACK=1` 또는 동등한 승인 기록이 생성된다.
3. 운영 `_database/` full backup apply를 수행하고 backup checksum manifest가 PASS한다.
4. `cutover_v3k_shadow_to_database.py --apply --backup-first --backup-dir <backup> --allow-operating-target` 실행 범위가 승인된다.
5. cutover 직후 `v3k_db_health.py`, F5 production read smoke, VERIFY-1A/VERIFY-1B, nonrelease sync가 PASS한다.
6. `rollback_v3k_cutover.py --apply --backup-dir <backup> --allow-operating-target` rollback path가 준비되어 있어야 한다.
7. 7-day monitoring window, alert, owner, fallback trigger, 새 cutover 금지 규칙이 승인된다.
8. 아래 검증이 모두 PASS한다.

```powershell
python -m py_compile scripts/backup_operational_database.py scripts/cutover_v3k_shadow_to_database.py scripts/rollback_v3k_cutover.py scripts/smoke_v3k_cutover_dryrun.py scripts/v3k_db_health.py
python scripts/smoke_v3k_cutover_dryrun.py
python scripts/v3k_db_health.py --read-only --output .omx/reports/v3k-db-health-page053.json
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
```

---

## 5. STOP condition

다음 중 하나라도 충족되지 않으면 F1 actual DB cutover를 수행하지 않는다.

- 사용자 명시 gate 승인 부재
- `V3K_CUTOVER_USER_ACK=1` 또는 동등 승인 기록 부재
- 운영 `_database/` full backup apply 부재
- backup checksum manifest PASS 부재
- `--backup-first`, `--backup-dir`, `--allow-operating-target` 승인 부재
- rollback path 검증 부재
- post-cutover health 계획 부재
- 7-day monitoring 계획 부재
- Kiwoom 주문/청산/live runtime 코드 변경 발생
- LS Securities 직접 의존 발생
- DB 파일, backup directory, raw report artifact commit 위험 발생

---

## 6. 다음 단계

현재 Page053의 결론은 `f1-actual-db-cutover-await-user-approval`이다. 다음 실제 실행은 사용자 승인과 backup/rollback/post-health/monitoring 계획 확정 전에는 수행하지 않는다. 승인 전 안전 작업으로는 live order/exit rule consumption gate 정리 또는 전체 approval gate closeout 재점검만 허용한다.
