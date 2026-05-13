# V3K Page074 agent entrypoint contract 계획

## 목적

Page073에서 V3K 목표 완료 판단을 prompt-to-artifact checklist로 고정했지만, `STOM_Version_2U_C` checkout의 `AGENTS.md`에는 V3K 목적과 남은 gate가 명시되어 있지 않았다. 이 페이지는 이후 agent가 2U_C에 진입할 때 V3K 목표, 금지사항, 읽어야 할 문서, 검증 명령을 즉시 인지하도록 branch-local entrypoint를 보강하는 계획이다.

## 추가할 AGENTS.md 계약

`AGENTS.md`에 `V3K_2UC_AGENT_ENTRYPOINT_CONTRACT` section을 추가한다.

필수 내용:

- `V3K = V3 features + Kiwoom retained`
- LS Securities REST/TR/REAL direct broker dependency excluded
- Kiwoom API/order/exit/live runtime preserved
- actual approval gate execution `0/6`
- `update_goal(status="complete")` 금지 조건
- USER_ACK, enable registry, sidecar artifact, DB cutover, KHOPENAPI connect/login, live order/exit wiring 금지
- 남은 six gate order
- 첫 gate 정확 승인 문구
- 2U_C에서는 `verify_nonrelease_sync.py` 사용
- `run_v3k_audit_suite.py`, `git diff --check`, artifact status 검증

## 검증 계획

1. `scripts/audit_v3k_agent_entrypoint_contract.py` 추가
2. `scripts/run_v3k_audit_suite.py`에 `agent_entrypoint_contract` 추가
3. `docs/CARRY_FORWARD_REGISTRY.md`에 Page074 기록
4. 아래 명령 통과

```powershell
python scripts/audit_v3k_agent_entrypoint_contract.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 실행하지 않는 범위

이 페이지는 entrypoint contract만 보강한다. 실제 approval gate execution, USER_ACK 생성, sidecar write, DB write, KHOPENAPI 연결, ON 전환, live runtime 변경은 하지 않는다.

