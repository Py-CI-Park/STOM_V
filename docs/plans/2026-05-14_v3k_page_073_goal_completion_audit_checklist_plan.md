# V3K Page073 목표 완료 감사 체크리스트 계획

## 목적

`STOM_Version_2U_C`의 V3K 목표는 **V3 기능을 LS증권 직접 의존 없이 Kiwoom 유지 상태로 반영**하는 것이다. 이 페이지는 현재 active goal을 완료로 오인하지 않도록, 남은 approval gate를 실제 산출물과 검증 증거에 매핑하는 completion audit 계획이다.

## 현재 전제

- 대상 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dev`
- 대상 브랜치: `STOM_Version_2U_C`
- 목적: `V3 기능 + Kiwoom 유지`
- 제외: `LS Securities REST/TR/REAL` 직접 broker runtime 의존
- 현재 상태: safe-staged / review-ready, 그러나 actual approval gate execution은 `0/6`
- 첫 승인 후보: `gui-sidecar-write-await-user-approval`

## 읽어야 하는 기준 문서

2U_C 내부 기준 문서:

1. `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
2. `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md`
3. `docs/CARRY_FORWARD_REGISTRY.md`
4. `docs/update_log/2026-05-14_v3k_goal_skill_and_remaining_gate_completion_audit.md`
5. `docs/update_log/2026-05-14_v3k_goal_handoff_audit_suite_integration.md`
6. `docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md`
7. `docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_preflight.md`
8. `docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md`

상위 공식 lane 참고 문서:

1. `C:/System_Trading/STOM/STOM_V/docs/V3_UPDATE_OPERATING_SYSTEM.md`
2. `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-04_v3_transition_strategy_review.md`
3. `C:/System_Trading/STOM/STOM_V/docs/update_log/2026-05-06_v3_v3u_final_handoff.md`

## 완료 판단 기준

완료는 다음 조건이 모두 실제 증거로 충족될 때만 가능하다.

| 구분 | 완료 조건 | 현재 판정 |
| --- | --- | --- |
| V3K 기능 | DB/학습/분석/backtest/realtime/GUI/Phase F/G/H/live decision 계열이 Kiwoom 유지 조건으로 반영 또는 명시 보류 근거 확정 | 부분 충족, gate 전 safe-staged |
| LS 제외 | LS증권 직접 REST/TR/REAL broker runtime 의존이 없다 | 충족 |
| Kiwoom 유지 | Kiwoom 주문/청산/live runtime을 변경하지 않는다 | 충족 |
| feature flag | 신규 기능은 default-OFF로 유지된다 | 충족 |
| artifact | `_database`, `_database_v3k_shadow`, `_v3k_sidecar`, DB 파일, raw `.omx/reports`가 커밋되지 않는다 | 충족 |
| approval gate | 여섯 gate가 순서대로 승인, 실행, 검증, 기록된다 | 미충족, `0/6` |
| goal 완료권한 | 모든 gate 증거가 확인되기 전 `update_goal(status="complete")`를 호출하지 않는다 | 충족 |

## 남은 gate 순서

1. `gui-sidecar-write-await-user-approval`
2. `phase-f-f4-on-await-user-approval`
3. `phase-g-g3-on-await-user-approval`
4. `phase-h-h2-h3-live-dryrun-await-user-approval`
5. `f1-actual-db-cutover-await-user-approval`
6. `live-order-exit-rule-consumption-await-user-approval`

## 실행하지 않는 범위

명시적인 one-gate 승인 전에는 아래를 실행하지 않는다.

- USER_ACK 환경 생성
- enable registry heading 생성
- `_v3k_sidecar` 실제 write
- 운영 `_database/` write 또는 DB cutover
- KHOPENAPI connect/login
- Kiwoom live runtime 변경
- live order/exit rule consumption 연결
- `update_goal(status="complete")`

## 검증 계획

Page073은 다음 검증 표면을 추가한다.

1. `scripts/audit_v3k_goal_completion_objective_checklist.py`
2. `scripts/run_v3k_audit_suite.py`에 Page073 audit 추가
3. `python scripts/run_v3k_audit_suite.py`
4. `python scripts/verify_nonrelease_sync.py`
5. `git diff --check`
6. `git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`

## 다음 OMX 명령 형태

승인 없이 이어갈 때는 review-only 명령을 사용한다.

```powershell
omx ralph "force: 현재 active V3K goal을 유지하고 STOM_Version_2U_C에서 남은 approval gate 중 다음 1개만 검토한다. 명시적 one-gate 승인 문구가 없으면 USER_ACK, sidecar write, DB write, KHOPENAPI, ON 전환, live runtime 변경을 실행하지 말고 blocker와 다음 승인 조건만 문서화한다. 검증은 python scripts/run_v3k_audit_suite.py, python scripts/verify_nonrelease_sync.py, git diff --check, artifact status를 통과시킨다."
```

첫 gate 실행을 실제로 시작하려면 정확히 아래 문구가 필요하다.

```text
I approve gui-sidecar-write-await-user-approval only
```

