# V3K Page078 pre-approval stop condition 계획

## 목적

Page076에서 남은 gate status summary를 기계 판독 가능하게 만들었고, Page077에서 VERIFY-1B closure coverage를 최신화했다. 이제 실제 one-gate 승인 문구가 없는 상태에서 review-only 작업을 계속 증식하지 않도록, **사전 승인 상태의 stop condition**을 명확히 고정한다.

## stop condition

명시적 one-gate 승인 문구가 없으면 다음 상태가 정상이다.

- actual approval gate execution: `0/6`
- safe staged progress: `about 96%`
- next gate: `gui-sidecar-write-await-user-approval`
- next phrase: `I approve gui-sidecar-write-await-user-approval only`
- USER_ACK absent
- writer/rollback absent
- sidecar artifact absent
- DB/runtime/live artifact clean
- goal completion prohibited

## 검증 계획

- `scripts/audit_v3k_preapproval_stop_condition.py` 추가
- `scripts/run_v3k_audit_suite.py`에 `preapproval_stop_condition` 추가
- `scripts/audit_v3k_verify_1b_closure.py`의 최신 coverage에 Page078 추가
- `docs/CARRY_FORWARD_REGISTRY.md`에 Page078 기록

검증 명령:

```powershell
python scripts/audit_v3k_preapproval_stop_condition.py
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 실행하지 않는 범위

이 페이지는 stop condition을 검증할 뿐이다. USER_ACK, enable registry, sidecar write, rollback script, DB cutover, KHOPENAPI connect/login, ON 전환, live order/exit rule wiring은 생성하거나 실행하지 않는다.

