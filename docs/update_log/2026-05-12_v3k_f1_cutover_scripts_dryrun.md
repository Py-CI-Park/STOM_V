# V3K F1 cutover scripts dry-run — Page 030

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| f51 단계 | B2 |
| 선행 완료 | Page 029 / `e98d8703` F1 사전 ralplan |
| 본 단계 성격 | script 신설 + tempfile-only dry-run |
| 실제 cutover | **금지** |

---

## 0. 결론

```text
Page 030은 actual DB cutover가 아니다.
backup/cutover/rollback script와 smoke를 신설했지만, 검증은 tempfile fixture에서만 수행했다.
운영 _database/, _database_v3k_shadow/, DB 파일, Kiwoom live runtime, LS 직접 의존은 변경하지 않았다.
다음 단계는 Page 031 / `f1-actual-cutover-approval-gate` / F1 actual cutover approval gate이며, 사용자 명시 승인 전에는 실행하지 않는다.
```

---

## 1. 산출물

| 파일 | 역할 | 안전 경계 |
| --- | --- | --- |
| `scripts/backup_operational_database.py` | source DB 파일을 backup target으로 복사하고 checksum manifest 생성 | 기본 dry-run. `--apply`는 `V3K_CUTOVER_USER_ACK=1` + branch guard 필요 |
| `scripts/cutover_v3k_shadow_to_database.py` | shadow → target 복사 script | `--apply`는 branch + ACK + `--backup-first` + `--backup-dir` 필요. 실제 `_database` target은 `--allow-operating-target` 없으면 거부 |
| `scripts/rollback_v3k_cutover.py` | backup manifest 기준 target 복원 | `--apply`는 branch + ACK 필요. 실제 `_database` target은 `--allow-operating-target` 없으면 거부 |
| `scripts/smoke_v3k_cutover_dryrun.py` | backup/cutover/rollback guard와 checksum mismatch 검증 | `tempfile.TemporaryDirectory` fixture만 사용 |
| `.gitignore` | backup 디렉터리 commit 금지 | `_database.backup.*/` 추가 |

---

## 2. Guard 증거

| Guard | 구현 위치 | smoke 증거 |
| --- | --- | --- |
| branch guard | backup/cutover/rollback script | 현재 branch가 `STOM_Version_2U_C`일 때만 apply 허용 |
| `V3K_CUTOVER_USER_ACK=1` | backup/cutover/rollback script | ACK 없는 cutover/rollback apply 거부 |
| `--backup-first` | cutover script | flag 없는 cutover apply 거부 |
| backup manifest checksum | cutover/rollback script | corrupt backup fixture로 cutover 거부 |
| real `_database` extra guard | cutover/rollback script | actual target에는 `--allow-operating-target` 필요 |
| DB artifact cleanliness | final git status | 운영 DB/backup/sidecar artifact 변경 없음 |

---

## 3. Smoke 결과

`python scripts/smoke_v3k_cutover_dryrun.py`는 다음을 확인한다.

1. tempfile operational source → tempfile backup apply 통과.
2. ACK 없는 cutover apply 거부.
3. `--backup-first` 없는 cutover apply 거부.
4. ACK + backup-first + tempfile target cutover 통과.
5. ACK 없는 rollback apply 거부.
6. ACK + tempfile target rollback 통과.
7. corrupt backup checksum이면 cutover 거부.

---

## 4. actual cutover 잔여 gate

| Gate | 상태 |
| --- | --- |
| 사용자 명시 승인 | 미충족 |
| 운영 `_database/` full backup apply | 미수행 |
| actual `_database_v3k_shadow` → `_database` cutover | 미수행 |
| post-cutover health smoke | 미수행 |
| 7일 monitoring audit | 미수행 |
| cutover report commit | 미수행 |

따라서 `db-cutover-migration`은 계속 approval-gated 상태다.

---

## 5. 검증 기록

```powershell
python -m py_compile scripts/backup_operational_database.py scripts/cutover_v3k_shadow_to_database.py scripts/smoke_v3k_cutover_dryrun.py scripts/rollback_v3k_cutover.py
python scripts/smoke_v3k_cutover_dryrun.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph v3k_settings*.json
```

---

## 6. 다음 단계

Page 031은 **`f1-actual-cutover-approval-gate` / F1 actual cutover approval gate**다. 이 단계는 실제 cutover를 바로 수행하지 않고, 사용자 명시 승인·backup apply·post-cutover health·7일 monitoring 조건이 모두 충족됐는지 확인해야 한다.

승인 없이는 다음 실행 가능한 안전 작업으로 F3/F4 pre-work 또는 H-2 환경 점검 문서화만 가능하다.
