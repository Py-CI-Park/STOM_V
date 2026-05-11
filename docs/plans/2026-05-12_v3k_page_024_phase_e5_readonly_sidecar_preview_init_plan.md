# V3K Page 024 — Phase E-5 read-only sidecar preview initialization bridge 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md`
- `docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md`

---

## 0. 목적

Page 024의 목적은 actual sidecar write가 아니라, Page 022에서 만든 read-only loader를 session-only GUI preview 초기값에 연결할 수 있는지 검토하고 필요하면 최소 구현하는 것이다.

핵심 원칙:

- sidecar 파일은 읽기만 한다.
- repo `_v3k_sidecar` 파일을 생성하지 않는다.
- operating `_database/setting.db`를 쓰지 않는다.
- session override가 sidecar보다 우선한다.
- valid sidecar가 없으면 기존 default-OFF preview와 동일하게 동작한다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 024-1 | preview init 경계 조사 | `ui/ui_v3k_settings_preview.py`에서 초기 settings 주입 지점 확인 |
| 024-2 | read-only bridge 설계 | loader 결과를 session-only preview 초기값으로만 넘기는 경로 설계 |
| 024-3 | smoke 확장 | missing/corrupt/valid sidecar가 preview 초기값에 미치는 영향을 tempfile/monkeypatch로 검증 |
| 024-4 | no-write guard | preview open 과정에서 sidecar/DB/runtime artifact가 생성되지 않음을 검증 |
| 024-5 | 다음 후보 결정 | actual write 보류 유지 또는 tempfile-only writer prototype 재검토 |

현재 진행률:

```text
Page 024: [░░░░░░░░░░░░░░░░░░░░] 0 / 5 = 0%
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
omx ralph "force: V3K Page 024 Phase E-5 read-only sidecar preview initialization bridge를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md와 docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md를 기준으로, actual sidecar write 없이 Page 022 read-only loader를 session-only GUI preview 초기값에 연결할 수 있는지 검토하고 필요하면 최소 구현한다. missing/corrupt/valid sidecar, session override 우선순위, default-OFF fallback, no-write/no-DB/no-runtime-artifact 조건을 tempfile 또는 monkeypatch 기반 smoke로 검증한다. 실제 repo `_v3k_sidecar` artifact, operating _database/setting.db schema/write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer trading decision, 외부 broker 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_gui_sidecar_write_guard.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
