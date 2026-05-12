# V3K Page 025 — Phase E-6 sidecar tempfile-only writer prototype 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e5_readonly_sidecar_preview_init.md`
- `docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md`

---

## 0. 목적

Page 025의 목적은 repo sidecar actual write가 아니라, Page 023에서 정의한 guard 조건을 만족할 수 있는 writer contract를 tempfile 안에서만 prototype으로 검증하는 것이다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 025-1 | writer contract 설계 | atomic write, backup-before-replace, rollback, corruption recovery 조건 명세 |
| 025-2 | tempfile-only prototype | repo `_v3k_sidecar`가 아닌 tempfile directory에서만 writer 후보 검증 |
| 025-3 | failure smoke | invalid payload, write failure, corrupt existing file 시 rollback 확인 |
| 025-4 | no artifact guard | repo sidecar/DB/runtime artifact 미생성 확인 |
| 025-5 | actual write go/no-go | repo sidecar write를 계속 보류할지 다음 단계에서 제한 승인할지 결정 |

현재 진행률:

```text
Page 025: [░░░░░░░░░░░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 025 Phase E-6 sidecar tempfile-only writer prototype을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md와 docs/update_log/2026-05-12_v3k_phase_e5_readonly_sidecar_preview_init.md를 기준으로, repo sidecar actual write 없이 tempfile directory에서만 atomic write, backup-before-replace, rollback, corruption recovery writer contract를 prototype/smoke로 검증한다. 실제 repo `_v3k_sidecar` artifact, operating _database/setting.db schema/write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer trading decision, 외부 broker 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_gui_sidecar_write_guard.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
