# V3K GUI sidecar write approval prep

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 049 |
| source | Page048 approval-gate-selection |
| marker | `GUI_SIDECAR_WRITE_APPROVAL_PREP` |
| 상태 | `completed-approval-prep` |
| next candidate | `gui-sidecar-write-await-user-approval` |

---

## 1. 요약

GUI actual sidecar write gate는 남은 approval gate 중 상대적으로 위험이 낮지만, 실제 파일 write와 운영 설정 지속화에 닿을 수 있으므로 사용자 승인 전에는 실행하지 않는다.

이번 문서는 source-of-truth, prompt-to-artifact checklist, rollback/monitoring, STOP condition을 명확히 고정하기 위한 승인 준비 기록이다.

No actual write execution: actual sidecar write 실행, sidecar artifact 생성, Phase F/G/H ON, enable registry 생성, USER_ACK 생성, Kiwoom live runtime 변경, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, live order/exit rule 연결은 수행하지 않았다.

---

## 2. 증거 목록

| 근거 | 설명 |
| --- | --- |
| `strategy/v3k_gui_sidecar.py` | read-only validation/loader/merge contract가 존재한다. |
| `scripts/audit_v3k_gui_sidecar_write_guard.py` | strategy module writer 금지와 actual write approval required 정책을 검증한다. |
| `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` | tempfile-only atomic write, backup-before-replace, rollback, corrupt reject proof를 제공한다. |
| `scripts/run_v3k_audit_suite.py` | V3K 통합 safety/audit runner다. |
| `scripts/audit_v3k_verify_1a.py` | Kiwoom/runtime untouched, LS dependency marker, artifact guard를 검증한다. |

---

## 3. Prompt-to-artifact checklist

| 명시 요구 | concrete evidence | 현재 상태 |
| --- | --- | --- |
| LS Securities 직접 의존 금지 | VERIFY-1A, Phase G LS excise | 유지 |
| Kiwoom 주문/청산/live runtime 유지 | VERIFY-1A | 유지 |
| sidecar actual write는 승인 전 금지 | VERIFY-1B USER_APPROVAL_REQUIRED | 유지 |
| sidecar strategy module read-only | write guard audit | 유지 |
| missing/invalid sidecar default-OFF | loader + write guard audit | 유지 |
| tempfile writer proof | tempfile writer smoke | 유지 |
| repo sidecar artifact 금지 | sidecar write guard + audit suite artifact status | 유지 |
| 운영 DB write 금지 | audit suite artifact status | 유지 |

---

## 4. Actual write 전에 사용자가 결정해야 하는 것

1. `GUI actual sidecar write` gate의 명시 승인 여부
2. source-of-truth 위치: `_v3k_sidecar/v3k_gui_settings.json` 또는 별도 위치
3. writer 호출 시점: GUI 저장 버튼, 미리보기 종료 시점, 별도 명령 중 선택
4. rollback 조건: backup-before-replace, corrupt reject, temp cleanup, disable path
5. monitoring 조건: 저장/로드 log, schema mismatch, default-OFF fallback 동작

---

## 5. 남은 상태

현재 후보는 `gui-sidecar-write-await-user-approval`이다. 사용자가 이 gate를 명시 승인하기 전까지 actual writer 구현이나 실행은 하지 않는다.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_PREP`는 승인 준비 기록이며 actual sidecar write 실행, USER_ACK, ON 전환, DB cutover, Kiwoom live runtime 변경으로 해석하면 안 된다.
