# V3K Page 029 — F1 DB cutover 사전 ralplan 재합의 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 028 / mid-checkpoint v3 |
| f51 단계 | B1 |
| 위험도 | 중간~높음(단, 본 page는 문서/합의만 수행) |
| 실제 cutover | 본 page에서 금지 |

---

## 0. 목적

Page 029는 F1 DB cutover script 또는 실제 cutover로 들어가기 전, `docs/plans/2026-05-12_v3k_db_cutover_plan.md`의 LC1~LC3 invariant가 충분한지 다시 합의하는 단계다.

이 단계는 **실행 전 안전 재검토**이며, 운영 `_database/`를 변경하지 않는다.

---

## 1. In-scope

| Step | 내용 | 산출 |
| ---: | --- | --- |
| 029-1 | F1 plan 재독해 | LC1/LC2/LC3 invariant 재정리 |
| 029-2 | pre-mortem 3개 작성 | power fail, backup 손상, schema drift |
| 029-3 | expanded test plan 작성 | checksum unit, dry-run integration, post-cutover health, 7일 monitoring observability |
| 029-4 | F5 production read 완료가 precondition임을 명시 | `bbb8975a` 근거 |
| 029-5 | B2 script 단계와 실제 cutover 단계를 분리 | B2는 script/dry-run, T05 actual cutover는 별도 승인 |
| 029-6 | registry/audit next candidate 갱신 | 다음 후보를 B2 script/dry-run으로 이동할지 판단 |

---

## 2. Out-of-scope / Gate

- 운영 `_database/` write 금지.
- `_database_v3k_shadow/`를 운영 DB로 cutover 금지.
- backup/rollback rehearsal이 운영 파일을 건드리면 중단.
- DB 파일 commit 금지.
- Kiwoom 주문/청산/live runtime 변경 금지.
- LS Securities 직접 의존 금지.
- feature flag ON 전환 금지.

---

## 3. 완료 조건

- F1 pre-mortem과 expanded test plan이 update_log로 남는다.
- `docs/CARRY_FORWARD_REGISTRY.md`에 Page 029 항목이 추가된다.
- 실제 cutover와 script/dry-run의 경계가 명시된다.
- 검증은 문서/보존 audit 중심으로 통과한다.

```powershell
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

---

## 4. 추천 OMX 명령

```powershell
omx ralplan --deliberate "V3K F1 DB cutover 사전 합의를 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/update_log/2026-05-12_v3k_ralph_command_playbook.md 의 B1, docs/plans/2026-05-12_v3k_db_cutover_plan.md, docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_bbb8975a.md, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. LC1 backup-first, LC2 단일 commit + 사용자 명시 승인, LC3 7일 모니터링 invariant를 pre-mortem 3개(power fail, backup 손상, schema drift)와 expanded test plan으로 재검토한다. 이 단계는 합의/문서화만 수행하며 운영 _database write, 실제 cutover, DB 파일 commit, Kiwoom live runtime, LS Securities 직접 의존, feature flag ON 전환은 금지한다. 완료 시 Page 029 plan/update_log/registry를 갱신하고 verify_nonrelease_sync, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, git diff --check, DB artifact status를 통과시킨다."
```
