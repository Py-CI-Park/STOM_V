# V3K agent entrypoint contract

`V3K_2UC_AGENT_ENTRYPOINT_CONTRACT`

## 결론

`STOM_Version_2U_C`의 branch-local `AGENTS.md`에 V3K 목적과 남은 gate를 명시했다. 이제 이후 agent는 2U_C checkout에 들어왔을 때 V3K가 **V3 features + Kiwoom retained**이며, LS Securities 직접 의존은 제외되고, 실제 approval gate execution은 아직 `0/6`이라는 사실을 즉시 확인할 수 있다.

## 반영 내용

- `AGENTS.md`에 V3K entrypoint section 추가
- 읽어야 할 V3K 문서 목록 추가
- 남은 gate order 6개 명시
- 첫 승인 문구 `I approve gui-sidecar-write-await-user-approval only` 명시
- `update_goal(status="complete")` 금지 조건 명시
- USER_ACK, enable registry, sidecar artifact, DB cutover, KHOPENAPI connect/login, live order/exit wiring 금지 명시
- 2U_C lane 검증 명령에 `verify_nonrelease_sync.py` 사용 명시

## 현재 상태

| 항목 | 상태 |
| --- | --- |
| 목적 | V3 기능을 LS증권 직접 의존 없이 Kiwoom 유지 상태로 2U_C에 반영 |
| 실제 gate 실행 | `0/6` |
| 첫 gate | `gui-sidecar-write-await-user-approval` |
| 첫 승인 문구 | `I approve gui-sidecar-write-await-user-approval only` |
| 완료 처리 | 금지, 모든 gate 증거 확보 전 `update_goal(status="complete")` 금지 |
| 운영 DB write | 금지 |
| KHOPENAPI connect/login | 금지 |
| live order/exit wiring | 금지 |

## 검증

추가된 audit:

```powershell
python scripts/audit_v3k_agent_entrypoint_contract.py
```

통합 검증:

```powershell
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 다음 단계

승인 없이 이어갈 수 있는 작업은 review-only 문서화와 blocker 검증뿐이다. 실제 첫 gate 실행은 아래 정확 문구가 사용자에게서 명시된 뒤에만 가능하다.

```text
I approve gui-sidecar-write-await-user-approval only
```

