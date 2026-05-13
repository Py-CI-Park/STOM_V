# V3K pre-approval stop condition

`V3K_PREAPPROVAL_STOP_CONDITION`

## 결론

현재 V3K 상태는 **사전 승인 준비 완료 / 실제 gate 실행 대기** 상태다. 추가 review-only 산출물은 새 증거, 새 요구, 또는 정확한 one-gate 승인 문구가 있을 때만 의미가 있다. 지금의 정상 stop condition은 “첫 gate 승인 대기”다.

## 현재 stop condition

| 항목 | 값 |
| --- | --- |
| objective | `V3 features + Kiwoom retained` |
| actual_gate_execution_progress | `0/6` |
| safe_staged_progress | `about 96%` |
| next_gate | `gui-sidecar-write-await-user-approval` |
| next_phrase | `I approve gui-sidecar-write-await-user-approval only` |
| USER_ACK | absent |
| sidecar writer | absent |
| rollback script | absent |
| sidecar artifact | absent |
| DB/runtime/live artifacts | clean |
| goal completion | prohibited |

## 의미

- 이 상태는 실패가 아니라 의도된 safety stop이다.
- `python scripts/run_v3k_audit_suite.py`가 green이어도 final completion이 아니다.
- `python scripts/audit_v3k_preapproval_stop_condition.py`가 통과하면 “승인 없이 더 진행할 실행 작업은 없다”는 뜻이다.
- 실제 다음 action은 정확한 첫 gate 승인 문구를 받는 것이다.

## 금지 사항

승인 전에는 아래를 하지 않는다.

- USER_ACK 생성
- enable registry 생성
- `_v3k_sidecar` write
- rollback script 생성
- 운영 `_database/` write
- KHOPENAPI connect/login
- ON 전환
- live order/exit rule wiring
- `update_goal(status="complete")`

## 다음 gate 승인 문구

```text
I approve gui-sidecar-write-await-user-approval only
```

## 검증

```powershell
python scripts/audit_v3k_preapproval_stop_condition.py
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

