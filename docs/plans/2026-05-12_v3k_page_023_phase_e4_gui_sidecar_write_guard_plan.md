# V3K Page 023 — Phase E-4 GUI sidecar write guard/rollback decision 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e3_gui_sidecar_readonly_loader.md`
- `docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md`

---

## 0. 목적

Page 023의 목적은 sidecar actual write를 바로 구현하는 것이 아니라, write를 허용하기 전에 반드시 필요한 guard/rollback 조건을 확정하는 것이다.

Page 022에서 read-only loader는 완료되었다. 그러나 write는 다음 위험을 동반한다.

- corrupt sidecar가 생겼을 때 fallback만으로 충분한지
- 기존 sidecar를 backup하지 않고 덮어써도 되는지
- atomic write 실패 시 partial file이 남지 않는지
- GUI session-only override와 persisted sidecar의 우선순위가 유지되는지
- 운영 `_database/setting.db`와의 sync 정책을 의도적으로 분리할 수 있는지
- repo/사용자 runtime artifact를 커밋하지 않는 불변식을 유지할 수 있는지

따라서 Page 023은 write 구현 전 guardrail page로 둔다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 023-1 | write risk table | atomic write, backup, rollback, corruption recovery, no-DB-sync 위험을 표로 정리 |
| 023-2 | approval gate | actual write를 다음 page에서 진행할 수 있는 조건과 보류 조건을 명확히 구분 |
| 023-3 | smoke 설계 | future writer가 통과해야 할 tempfile-only smoke contract 작성 |
| 023-4 | audit 확장 | sidecar write가 아직 runtime에 연결되지 않았음을 확인하는 audit 기준 추가 |
| 023-5 | next page 결정 | 조건 충족 시 Page 024는 tempfile-only writer prototype, 부족 시 read-only 유지 |

현재 진행률:

```text
Page 023: [░░░░░░░░░░░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

Page 023에서는 다음을 변경하지 않는다.

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 023 Phase E-4 GUI sidecar write guard/rollback decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md와 docs/update_log/2026-05-12_v3k_phase_e3_gui_sidecar_readonly_loader.md를 기준으로, sidecar actual write를 바로 구현하지 말고 atomic write, backup, rollback, corruption recovery, no-DB-sync, session override 우선순위, artifact 미커밋 조건을 문서와 audit/smoke 기준으로 확정한다. 실제 repo `_v3k_sidecar` artifact, operating _database/setting.db schema/write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer trading decision, 외부 broker 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
