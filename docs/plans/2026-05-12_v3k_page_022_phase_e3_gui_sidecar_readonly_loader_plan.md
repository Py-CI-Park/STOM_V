# V3K Page 022 — Phase E-3 GUI sidecar read-only loader 계획/완료 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md`
- `docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md`

---

## 0. 목적

Page 022의 목적은 실제 sidecar write 없이 V3K GUI settings sidecar 후보 파일을 read-only로 load하는 adapter를 설계/구현하는 것이다.

Page 021은 payload validator만 다루고 filesystem은 건드리지 않았다. Page 022에서는 tempfile 기반 smoke로 missing file, corrupt file, valid file, unknown key, session-only override 우선순위를 검증하되 repo의 실제 `_v3k_sidecar/` artifact는 만들지 않는다.

---

## 1. 완료 범위

| Step | 작업 | 완료 기준 | 상태 |
| ---: | --- | --- | --- |
| 022-1 | read-only loader 설계 | path를 입력받아 read만 수행하고 write/create를 하지 않는 helper 정의 | 완료 |
| 022-2 | missing file smoke | 파일이 없으면 default-OFF fallback과 diagnostic 반환 | 완료 |
| 022-3 | corrupt/valid file smoke | corrupt JSON은 fallback, valid JSON은 schema validator 결과 반환 | 완료 |
| 022-4 | session override 관계 | loader result보다 session-only override가 우선함을 검증 | 완료 |
| 022-5 | no-repo-artifact guard | repo `_v3k_sidecar`, `_database`, `*.db` artifact 미생성 검증 | 완료 |

진행률:

```text
Page 022: [████████████████████] 5 / 5 = 100%
```

---

## 2. 구현 결정

- `strategy/v3k_gui_sidecar.py::load_v3k_gui_sidecar_file()`을 추가한다.
- 기본 후보 경로는 `_v3k_sidecar/v3k_gui_settings.json`이지만, helper는 파일을 만들지 않고 `Path.is_file()`과 `read_text(encoding="utf-8")`만 수행한다.
- missing file, unreadable file, read 실패는 모두 default-OFF fallback으로 닫는다.
- valid file의 payload 해석은 Page 021에서 만든 `validate_v3k_gui_sidecar_payload()`에 위임한다.
- session-only preview override는 sidecar load 결과보다 항상 높은 우선순위를 유지한다.

---

## 3. 검증 파일

- `scripts/smoke_v3k_gui_sidecar_readonly_loader.py`
  - `tempfile.TemporaryDirectory()` 내부에서만 corrupt/valid 파일을 작성한다.
  - repo `_v3k_sidecar/`는 생성하지 않는다.
  - artifact status를 smoke 전후로 비교한다.
- `scripts/audit_v3k_gui_sidecar_persistence_design.py`
  - Page 022 기록 문서와 read-only loader missing-file default-OFF contract를 추가 확인한다.
- `scripts/audit_v3k_verify_1b_closure.py`
  - V3K closure checklist에 read-only loader smoke를 포함한다.

---

## 4. Out-of-scope

다음은 Page 022에서 의도적으로 변경하지 않는다.

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성

---

## 5. 다음 단계

Page 023은 `V3K-PHASE-E4`로 진행한다.

목표는 sidecar write를 바로 구현하는 것이 아니라, actual write를 허용하기 전에 필요한 guard/rollback/atomic-write/backup/corruption-recovery 조건을 문서와 smoke 기준으로 확정하는 것이다. 조건이 충분하지 않으면 계속 read-only 상태로 보류한다.
