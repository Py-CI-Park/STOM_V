# V3K Page 023 — Phase E-4 GUI sidecar write guard/rollback decision 계획/완료 기록

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

따라서 Page 023은 write 구현 전 guardrail page로 완료했다.

---

## 1. 완료 범위

| Step | 작업 | 완료 조건 | 상태 |
| ---: | --- | --- | --- |
| 023-1 | write risk table | atomic write, backup, rollback, corruption recovery, no-DB-sync 위험을 표로 정리 | 완료 |
| 023-2 | approval gate | actual write를 다음 page에서 진행할 수 있는 조건과 보류 조건을 명확히 구분 | 완료 |
| 023-3 | smoke 설계 | future writer가 통과해야 할 tempfile-only smoke contract 작성 | 완료 |
| 023-4 | audit 확장 | sidecar write가 아직 runtime에 연결되지 않았음을 확인하는 audit 기준 추가 | 완료 |
| 023-5 | next page 결정 | 조건 부족으로 actual write는 보류하고 Page 024를 read-only preview init bridge로 결정 | 완료 |

진행률:

```text
Page 023: [████████████████████] 5 / 5 = 100%
```

---

## 2. 핵심 결정

- actual sidecar write는 아직 보류한다.
- Page 023은 write를 허용하지 않고, write를 허용하기 위한 불변 조건만 고정한다.
- 현재 `strategy/v3k_gui_sidecar.py`는 read-only loader만 유지해야 하며 writer 함수, `write_text`, `open(..., write)`, `os.replace`, `mkdir`, `unlink` 계열 구현을 넣지 않는다.
- actual GUI sidecar write implementation은 `audit_v3k_verify_1b_closure.py`의 `USER_APPROVAL_REQUIRED`에 계속 남긴다.
- 다음 Page 024는 write가 아니라 **read-only sidecar → session-only preview 초기값 연결 가능성**을 검토한다.

---

## 3. Out-of-scope

Page 023에서는 다음을 변경하지 않는다.

- 실제 repo `_v3k_sidecar/v3k_gui_settings.json` write/create
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- 증권사 API 교체 또는 외부 broker 직접 의존성
