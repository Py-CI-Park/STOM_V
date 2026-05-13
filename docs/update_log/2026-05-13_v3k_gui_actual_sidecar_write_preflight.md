# V3K GUI actual sidecar write preflight

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 057 |
| source | Page049 GUI sidecar write approval prep, Page056 approval gate final decision table |
| marker | `GUI_ACTUAL_SIDECAR_WRITE_PREFLIGHT` |
| 상태 | `completed-preflight` |
| gate | `gui-sidecar-write-await-user-approval` |

---

## 1. 목적

Page056 기준 첫 번째 추천 승인 gate는 GUI actual sidecar write다. 이번 Page057은 실제 write를 하지 않고, 승인 전 source-of-truth, USER_ACK, rollback, monitoring, artifact guard가 충분히 정리되었는지 확인한 preflight 기록이다.

No actual sidecar write execution: `_v3k_sidecar/v3k_gui_settings.json` 생성, sidecar artifact 생성, `V3K_GUI_SIDECAR_USER_ACK=1` 생성, writer 구현, writer 실행, MainWindow 연결, Phase F/G/H ON, KHOPENAPI connect/login, 운영 `_database/` write, DB 파일 commit, raw `.omx/reports` artifact commit, Kiwoom live runtime 변경, live order/exit rule 연결, LS Securities 직접 의존 추가는 수행하지 않았다.

---

## 2. Prompt-to-artifact checklist

| 명시 요구 | concrete evidence | 현재 상태 |
| --- | --- | --- |
| source-of-truth 후보 고정 | `_v3k_sidecar/v3k_gui_settings.json` | 승인 전 후보 |
| USER_ACK 없는 실행 금지 | `V3K_GUI_SIDECAR_USER_ACK=1` 미생성 | 유지 |
| strategy module writer 금지 | `scripts/audit_v3k_gui_sidecar_write_guard.py` | 통과 |
| read-only loader default-OFF | `load_v3k_gui_sidecar_file` missing-file fallback | 유지 |
| tempfile-only writer prototype | `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` | 통과 |
| rollback proof | backup-before-replace, corrupt reject, temp cleanup | prototype proof |
| monitoring 조건 | 저장/로드 log, schema mismatch, default-OFF fallback | 승인 전 조건 |
| artifact guard | `_v3k_sidecar`, `_database`, DB, raw report status | clean |
| Kiwoom live runtime 유지 | VERIFY-1A | 유지 |
| LS Securities 직접 의존 금지 | VERIFY-1A / Phase G LS excise | 유지 |

---

## 3. Preflight 판단

GUI actual sidecar write는 다음 조건이 충족되기 전까지 계속 보류한다.

1. 사용자가 `GUI actual sidecar write` gate를 명시 승인한다.
2. `V3K_GUI_SIDECAR_USER_ACK=1` 또는 동등 update_log 승인 기록을 남긴다.
3. source-of-truth 위치와 writer 호출 시점을 확정한다.
4. rollback owner, monitoring owner, fallback trigger를 확정한다.
5. V3K audit suite, `verify_nonrelease_sync.py`, artifact guard가 green이다.

---

## 4. 현재 결론

preflight는 완료되었지만 actual write는 승인 대기 상태다. 이 문서는 실제 write 구현이나 실행 승인이 아니다.

Directive: `GUI_ACTUAL_SIDECAR_WRITE_PREFLIGHT`는 승인 전 점검 기록이며 actual sidecar write 실행, USER_ACK 생성, writer 구현, MainWindow 연결, 운영 DB write, Kiwoom live runtime 변경, live order/exit rule 연결로 해석하면 안 된다.
