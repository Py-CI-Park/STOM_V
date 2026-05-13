# V3K Page 057 - GUI actual sidecar write preflight 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 056 / approval gate final decision table |
| 현재 page | Page 057 / GUI actual sidecar write preflight |
| 상태 | `completed-preflight` |
| gate | `gui-sidecar-write-await-user-approval` |
| 목적 | 가장 낮은 위험 승인 gate인 GUI actual sidecar write를 실제 실행하지 않고, source-of-truth, USER_ACK, rollback, monitoring, artifact guard를 다시 검증한다. |
| 실제 write 여부 | 아님. sidecar 파일 생성, USER_ACK 생성, writer 구현, writer 실행을 수행하지 않는다. |

---

## 1. 배경

Page056 final decision table은 남은 gate 중 첫 번째 추천 순서를 GUI actual sidecar write로 정했다. 다만 이 gate도 파일 지속화와 사용자 설정 source-of-truth에 닿기 때문에, 실제 구현 또는 실행 전에 preflight를 통과해야 한다.

Page057은 preflight 전용이다. 다음 작업은 금지한다.

- actual sidecar write 실행
- `_v3k_sidecar/v3k_gui_settings.json` 생성
- `V3K_GUI_SIDECAR_USER_ACK=1` 생성
- GUI writer 구현 또는 MainWindow 연결
- Phase F/G/H ON
- KHOPENAPI connect/login
- 운영 `_database/` write
- live order/exit rule 연결

---

## 2. Preflight checklist

| 항목 | 근거 | 상태 |
| --- | --- | --- |
| source-of-truth 후보 | `_v3k_sidecar/v3k_gui_settings.json` | 승인 전 후보로만 유지 |
| 승인 기록 | `V3K_GUI_SIDECAR_USER_ACK=1` 또는 동등 update_log 승인 | 미생성 |
| read-only loader | `strategy/v3k_gui_sidecar.py` | 유지 |
| strategy module writer 금지 | `scripts/audit_v3k_gui_sidecar_write_guard.py` | 유지 |
| tempfile-only prototype | `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py` | 통과 |
| rollback | backup-before-replace, corrupt reject, temp cleanup, disable path | prototype proof 있음 |
| monitoring | 저장/로드 log, schema mismatch, default-OFF fallback | 승인 전 조건 |
| artifact guard | `_v3k_sidecar`, `_database`, DB, raw report artifact status | clean 필요 |

---

## 3. 승인 전 사용자 결정 사항

1. 실제 source-of-truth 위치를 `_v3k_sidecar/v3k_gui_settings.json`로 확정할지 결정한다.
2. GUI writer 호출 시점을 저장 버튼, 미리보기 종료, 별도 명령 중 하나로 결정한다.
3. `V3K_GUI_SIDECAR_USER_ACK=1` 또는 동등 update_log 승인 방식을 결정한다.
4. rollback owner와 fallback trigger를 결정한다.
5. monitoring owner와 확인 기간을 결정한다.
6. sidecar write 실패 시 default-OFF fallback을 즉시 유지할지 결정한다.

---

## 4. 검증 명령

```powershell
python scripts/audit_v3k_gui_sidecar_write_guard.py
python scripts/smoke_v3k_gui_sidecar_tempfile_writer.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

---

## 5. 다음 단계

사용자 명시 승인 전에는 실제 GUI sidecar writer를 구현하거나 실행하지 않는다. 승인이 주어지면 별도 commit cycle에서 writer 구현, artifact guard, rollback proof, monitoring 기록을 분리해 진행한다.
