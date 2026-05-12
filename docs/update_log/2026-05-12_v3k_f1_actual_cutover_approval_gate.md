# V3K F1 actual cutover approval gate — Page 031

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| f51 단계 | F1 actual cutover gate |
| 선행 완료 | Page 030 / `6197d7a0` cutover scripts dry-run |
| 본 단계 성격 | actual cutover 실행 전 승인 gate 문서화 |
| actual cutover | **미실행 / 승인 대기** |

---

## 0. 결론

```text
F1 actual cutover는 현재 실행하지 않는다.
사용자 명시 승인, 운영 _database backup apply, actual cutover, post-cutover health, 7일 monitoring 조건이 아직 충족되지 않았다.
Page 030에서 script와 tempfile dry-run은 준비됐지만, 이는 실제 _database write 승인으로 해석하면 안 된다.
다음 안전 단계는 Page 032 / `phase-h-h2-h3-approval-gate` / Phase H H-2/H-3 approval gate 문서화다. KHOPENAPI live dry-run도 실제 실행하지 않는다.
```

---

## 1. Gate 판정

| Gate | 필요 조건 | 현재 상태 | 판정 |
| --- | --- | --- | --- |
| 사용자 명시 승인 | 사용자가 actual cutover를 명시 승인 | 없음 | **BLOCK** |
| `V3K_CUTOVER_USER_ACK=1` | actual cutover cycle에서만 설정 | 설정하지 않음 | **BLOCK** |
| 운영 `_database/` backup apply | `backup_operational_database.py --apply` | 수행하지 않음 | **BLOCK** |
| backup checksum manifest | actual backup manifest PASS | 미생성 | **BLOCK** |
| actual cutover apply | `cutover_v3k_shadow_to_database.py --apply --backup-first --allow-operating-target` | 수행하지 않음 | **BLOCK** |
| post-cutover health | schema/F5/VERIFY smoke PASS | 미수행 | **BLOCK** |
| 7일 monitoring | cutover timestamp 기준 monitor audit | 미수행 | **BLOCK** |

---

## 2. 수행하지 않은 작업

다음은 의도적으로 수행하지 않았다.

- 운영 `_database/` write.
- `_database_v3k_shadow/` → `_database/` actual cutover.
- `V3K_CUTOVER_USER_ACK=1` 설정.
- 운영 backup apply.
- DB 파일 또는 backup 디렉터리 commit.
- Kiwoom 주문/청산/live runtime 변경.
- LS Securities REST/TR/REAL 직접 의존 추가.
- feature flag ON 전환.

---

## 3. 현재 사용 가능한 증거

| 증거 | 의미 |
| --- | --- |
| `scripts/smoke_v3k_cutover_dryrun.py` PASS | script guard와 checksum mismatch 거부가 tempfile에서 증명됨 |
| `audit_v3k_runtime_activation_gap.py` PASS | actual cutover가 next/gated 상태로 관리됨 |
| `audit_v3k_verify_1a.py --base 57496d24` PASS | Kiwoom runtime과 LS 직접 의존 보존 |
| `verify_nonrelease_sync.py` PASS | 2U_C nonrelease invariant 유지 |
| artifact status clean | 운영 DB/backup/sidecar artifact 변경 없음 |

---

## 4. 승인 요청 양식

actual cutover를 진행하려면 별도 대화에서 다음 수준의 명시 승인이 필요하다.

```text
V3K F1 actual cutover 실행을 승인합니다.

- 대상 branch: STOM_Version_2U_C
- 운영 _database/ full backup apply 허용
- _database_v3k_shadow/ → _database/ actual cutover 허용
- backup manifest와 cutover report commit 허용
- cutover 후 post-health와 7일 monitoring gate 수행 동의
```

이 문구에 준하는 명시 승인 없이는 actual cutover를 실행하지 않는다.

---

## 5. 다음 단계

f51 playbook 순서상 F1 actual cutover 다음에는 Phase H H-2/H-3가 위치하지만, 이 역시 KHOPENAPI 호환 환경과 사용자 승인이 필요하다. 따라서 다음 Page 032는 **`phase-h-h2-h3-approval-gate` / actual KHOPENAPI dry-run 실행이 아니라 approval/environment gate 문서화**로 제한한다.

Page 032에서도 다음은 금지한다.

- KHOPENAPI 실제 login/connect.
- Kiwoom 주문/청산/live runtime 변경.
- `V3K_PHASE_H_USER_ACK=1` 설정.
- feature flag ON 전환.

---

## 6. 검증 기록

```powershell
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph v3k_settings*.json
```

---

## 7. Freeze 정책

- 본 문서는 Page 031의 gate snapshot이다.
- actual cutover 승인 또는 거부가 발생하면 본 문서를 amend하지 않고 새 update_log를 작성한다.
