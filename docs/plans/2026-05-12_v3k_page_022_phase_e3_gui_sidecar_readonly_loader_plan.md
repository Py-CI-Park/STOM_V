# V3K Page 022 — Phase E-3 GUI sidecar read-only loader 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md`
- `docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md`

---

## 0. 목적

Page 022의 목적은 실제 sidecar write 없이 V3K GUI settings sidecar 후보 파일을 read-only로 load하는 adapter를 설계/구현하는 것이다.

Page 021은 payload validator만 다뤘고 filesystem은 건드리지 않았다. Page 022에서는 tempfile 기반 smoke로 missing file, corrupt file, valid file 처리를 검증하되, repo의 실제 `_v3k_sidecar/` artifact는 만들지 않는다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 022-1 | read-only loader 설계 | path를 입력받아 read만 수행하고 write/create는 하지 않는 helper를 정의한다. |
| 022-2 | missing file smoke | 파일이 없으면 default-OFF fallback과 diagnostic을 반환한다. |
| 022-3 | corrupt/valid file smoke | corrupt JSON은 fallback, valid JSON은 schema validator 결과를 반환한다. |
| 022-4 | session override 관계 | loader result와 session-only override 우선순위를 유지한다. |
| 022-5 | no-repo-artifact guard | repo `_v3k_sidecar`, `_database`, `*.db` artifact가 생기지 않음을 검증한다. |

현재 진행률:

```text
Page 022: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

다음은 Page 022에서 변경하지 않는다.

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- LS증권 직접 의존성

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 022 Phase E-3 GUI sidecar read-only loader를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md와 docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md를 기준으로, 실제 sidecar write 없이 `_v3k_sidecar/v3k_gui_settings.json` 후보 경로를 read-only로 load하는 adapter를 설계/구현한다. missing file, corrupt file, valid file, unknown key, default-OFF fallback, session-only override 관계를 tempfile 기반 smoke로 검증하되 실제 repo `_v3k_sidecar` artifact는 만들지 않는다. 운영 _database/setting.db schema/write, sidecar write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
