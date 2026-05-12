# V3K Page 031 — F1 actual cutover approval gate 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 030 / F1 cutover scripts dry-run |
| f51 단계 | F1 actual cutover gate |
| 위험도 | critical |
| 실제 cutover | 사용자 명시 승인 전 금지 |

---

## 0. 목적

Page 031은 actual cutover를 바로 실행하는 단계가 아니라, actual cutover 실행 조건이 충족됐는지 확인하고 사용자 명시 승인이 필요한 지점을 문서화하는 gate다.

---

## 1. Gate 조건

| 조건 | 필요 상태 |
| --- | --- |
| 사용자 명시 승인 | 필요 |
| `V3K_CUTOVER_USER_ACK=1` | actual cutover cycle에서만 설정 |
| 운영 `_database/` backup apply | 승인 후 T05 직전 수행 |
| backup checksum manifest | PASS 필요 |
| cutover script guard | branch/ACK/backup-first/allow-operating-target 모두 필요 |
| post-cutover health | actual cutover 직후 PASS 필요 |
| 7일 monitoring | actual cutover 이후 새 cutover 금지 |

---

## 2. 본 page에서 금지

- 운영 `_database/` write.
- actual `_database_v3k_shadow` → `_database` cutover.
- DB 파일 commit.
- Kiwoom live runtime 변경.
- LS Securities 직접 의존.
- feature flag ON 전환.

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K F1 actual cutover approval gate를 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/update_log/2026-05-12_v3k_f1_cutover_scripts_dryrun.md, docs/plans/2026-05-12_v3k_page_031_f1_actual_cutover_approval_gate_plan.md, docs/plans/2026-05-12_v3k_db_cutover_plan.md, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. 사용자 명시 승인, 운영 _database backup apply, actual cutover, DB 파일 commit, Kiwoom live runtime, LS Securities 직접 의존, feature flag ON 전환은 수행하지 말고 gate 충족 여부와 승인 필요 조건만 문서화한다. 완료 시 update_log/registry/audit next candidate를 갱신하고 audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시킨 뒤 한국어 Lore commit한다."
```
