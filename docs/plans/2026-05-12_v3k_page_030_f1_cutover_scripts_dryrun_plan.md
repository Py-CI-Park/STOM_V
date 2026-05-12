# V3K Page 030 — F1 cutover scripts dry-run 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 029 / F1 DB cutover 사전 ralplan |
| f51 단계 | B2 |
| 위험도 | 높음(단, 본 page는 script + tempfile dry-run만 허용) |
| 실제 cutover | 금지 |

---

## 0. 목적

Page 030은 F1 actual cutover가 아니라, actual cutover를 안전하게 실행하기 위한 script와 dry-run smoke를 준비하는 단계다.

---

## 1. In-scope

| Step | 산출 | 제한 |
| ---: | --- | --- |
| 030-1 | `scripts/backup_operational_database.py` | dry-run 기본, 실제 apply는 별도 승인 전까지 guard |
| 030-2 | `scripts/cutover_v3k_shadow_to_database.py` | apply는 branch/backup-first/ack guard 없으면 거부 |
| 030-3 | `scripts/smoke_v3k_cutover_dryrun.py` | tempfile fixture만 사용 |
| 030-4 | `scripts/rollback_v3k_cutover.py` | tempfile rollback 검증 |
| 030-5 | `.gitignore` backup 정책 | `_database.backup.*` commit 금지 |
| 030-6 | update_log/registry 갱신 | actual cutover gate 유지 |

---

## 2. Out-of-scope / Gate

- 운영 `_database/` write 금지.
- 실제 `_database_v3k_shadow` → `_database` cutover 금지.
- DB 파일 commit 금지.
- backup 디렉터리 commit 금지.
- Kiwoom 주문/청산/live runtime 변경 금지.
- LS Securities 직접 의존 금지.
- feature flag ON 전환 금지.

---

## 3. 검증

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

## 4. 추천 OMX 명령

```powershell
omx ralph "force: V3K F1 DB cutover script/dry-run 신설을 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/update_log/2026-05-12_v3k_f1_db_cutover_pre_ralplan.md, docs/plans/2026-05-12_v3k_page_030_f1_cutover_scripts_dryrun_plan.md, docs/plans/2026-05-12_v3k_db_cutover_plan.md, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. scripts/backup_operational_database.py, scripts/cutover_v3k_shadow_to_database.py, scripts/smoke_v3k_cutover_dryrun.py, scripts/rollback_v3k_cutover.py를 신설하되 운영 _database write, 실제 cutover, DB 파일 commit, Kiwoom live runtime, LS Securities 직접 의존, feature flag ON 전환은 금지한다. 모든 apply 경로는 branch/backup-first/V3K_CUTOVER_USER_ACK guard로 막고 smoke는 tempfile fixture만 사용한다. 완료 시 docs/update_log와 registry를 갱신하고 py_compile, smoke_v3k_cutover_dryrun, audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시킨 뒤 한국어 Lore commit한다."
```
