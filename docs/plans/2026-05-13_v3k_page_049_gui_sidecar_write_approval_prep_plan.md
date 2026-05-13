# V3K Page 049 - GUI sidecar write approval prep 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 048 / approval gate selection |
| 현재 page | Page 049 / GUI sidecar write approval prep |
| 상태 | `completed-approval-prep` |
| 다음 후보 | `gui-sidecar-write-await-user-approval` |
| 목적 | GUI sidecar actual write를 바로 실행하지 않고, 사용자 승인 전 필요한 source-of-truth, USER_ACK, rollback, monitoring, STOP condition을 문서와 감사 도구에 고정한다. |
| 위험도 | approval prep은 낮음, actual GUI write는 medium-high |
| 실제 write 여부 | 아님. sidecar artifact를 생성하지 않고 approval prep만 수행한다. |

---

## 1. 배경

Page048에서 남은 approval gate 중 가장 낮은 위험 후보로 GUI sidecar write가 선정되었다. 그러나 GUI write는 사용자 설정을 파일로 지속화할 수 있으므로, 실제 구현이나 실행 전에 source-of-truth 위치와 rollback/monitoring 조건을 명시해야 한다.

이번 Page049는 승인 준비 단계이며, 다음을 수행하지 않는다.

- actual sidecar write 실행
- sidecar artifact 생성 또는 commit
- USER_ACK 생성
- enable registry 생성
- Phase F/G/H ON
- 운영 `_database/` write
- Kiwoom live runtime 변경
- live order/exit rule 연결

---

## 2. 성공 기준

| 기준 | 증거 |
| --- | --- |
| 승인 준비 문서 존재 | `docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_prep.md` |
| 실제 write 미수행 | sidecar artifact status clean |
| Kiwoom 유지 | VERIFY-1A |
| LS Securities 직접 의존 금지 | VERIFY-1A / Phase G LS excise |
| default-OFF 유지 | VERIFY-1B / audit suite |
| 다음 후보 명시 | `gui-sidecar-write-await-user-approval` |

---

## 3. 사용자가 승인 전 결정할 항목

1. GUI sidecar actual write를 진행할지 여부
2. sidecar source-of-truth 파일 위치
3. write trigger
4. rollback owner와 fallback 조건
5. monitoring owner와 확인 기간
6. 실패 시 즉시 disable 조건

---

## 4. 금지선

- `V3K_GUI_SIDECAR_USER_ACK` 또는 동등한 승인 기록 없이 writer를 실행하지 않는다.
- `_database/`, `_database_v3k_shadow/`, `.db`, `.omx/reports` raw artifact를 commit하지 않는다.
- Kiwoom 주문/청산/live runtime을 수정하지 않는다.
- LS Securities 직접 의존성을 추가하지 않는다.
- Phase F/G/H ON 또는 live order/exit 연결로 해석하지 않는다.

---

## 5. 검증 명령

```powershell
python scripts/audit_v3k_gui_sidecar_write_guard.py
python scripts/smoke_v3k_gui_sidecar_tempfile_writer.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar
```

---

## 6. 다음 단계

Page049 이후에도 실제 GUI sidecar write는 사용자 승인 대기 상태로 남긴다. 이후 Page050~Page054는 더 높은 위험 gate를 같은 방식으로 승인 준비 상태에 고정한다.
