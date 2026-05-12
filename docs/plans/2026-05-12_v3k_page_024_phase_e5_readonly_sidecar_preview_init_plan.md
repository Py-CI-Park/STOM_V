# V3K Page 024 — Phase E-5 read-only sidecar preview initialization bridge 계획/완료 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md`
- `docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md`

---

## 0. 목적

Page 024의 목적은 actual sidecar write가 아니라, Page 022에서 만든 read-only loader를 session-only GUI preview 초기값에 연결할 수 있는지 검토하고 최소 구현하는 것이다.

핵심 원칙:

- sidecar 파일은 읽기만 한다.
- repo `_v3k_sidecar` 파일을 생성하지 않는다.
- operating `_database/setting.db`를 쓰지 않는다.
- session override가 sidecar보다 우선한다.
- valid sidecar가 없으면 기존 default-OFF preview와 동일하게 동작한다.

---

## 1. 완료 범위

| Step | 작업 | 완료 조건 | 상태 |
| ---: | --- | --- | --- |
| 024-1 | preview init 경계 조사 | `ui/ui_v3k_settings_preview.py` 초기 settings 주입 지점 확인 | 완료 |
| 024-2 | read-only bridge 설계 | loader 결과를 session-only preview 초기값으로만 넘기는 경로 설계 | 완료 |
| 024-3 | smoke 확장 | missing/corrupt/valid sidecar가 preview 초기값에 미치는 영향을 tempfile로 검증 | 완료 |
| 024-4 | no-write guard | preview open 과정에서 sidecar/DB/runtime artifact가 생성되지 않음을 검증 | 완료 |
| 024-5 | 다음 후보 결정 | actual write는 계속 보류하고 Page 025를 tempfile-only writer prototype 검토로 결정 | 완료 |

진행률:

```text
Page 024: [████████████████████] 5 / 5 = 100%
```

---

## 2. 구현 결정

- `attach_v3k_settings_preview()`는 read-only sidecar loader를 통해 초기 preview state를 계산할 수 있다.
- `initialize_v3k_preview_from_sidecar()`를 추가해 valid sidecar settings를 `v3k_settings`/`v3k_feature_flags`의 session-only 초기값으로만 반영한다.
- missing/corrupt sidecar는 default-OFF fallback으로 닫는다.
- sidecar initialization 자체는 session dirty 상태가 아니며, 사용자가 preview에서 toggle한 뒤에만 dirty가 된다.
- `set_v3k_preview_session_flag()`와 reset은 계속 in-memory/session-only 변경만 수행한다.

---

## 3. Out-of-scope

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성

---

## 4. 다음 단계

Page 025는 `V3K-PHASE-E6: sidecar tempfile-only writer prototype`으로 계획한다.

단, Page 025도 repo sidecar write가 아니다. Page 023 guard를 만족하기 위한 writer contract를 tempfile 안에서만 증명하는 단계다.
