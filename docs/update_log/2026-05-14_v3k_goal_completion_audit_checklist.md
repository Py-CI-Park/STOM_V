# V3K 목표 완료 감사 체크리스트

`V3K_GOAL_COMPLETION_OBJECTIVE_CHECKLIST`

## 결론

현재 목표는 **완료가 아니다**. 목적은 맞게 유지되고 있고 대부분의 안전 준비와 검증은 완료되었지만, 실제 approval gate execution은 아직 `0/6`이다. 따라서 `update_goal(status="complete")`를 호출하면 안 된다.

## 목표 재정의

사용자 목표를 concrete deliverable로 다시 쓰면 다음과 같다.

> `STOM_Version_2U_C`에 V3의 새로운 기능을 반영하되, LS증권 직접 의존은 제외하고 현 Kiwoom API, 주문, 청산, live runtime을 유지한다. DB/학습/분석/backtest/realtime/GUI/live decision 관련 기능은 feature flag default-OFF와 rollback 가능한 approval gate를 통해 단계별로 검증한다.

## Prompt-to-artifact checklist

| 사용자 요구/명시 조건 | 산출물 또는 증거 | 현재 판정 |
| --- | --- | --- |
| V3 기능을 2U_C에 반영 | `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`, `docs/CARRY_FORWARD_REGISTRY.md`, Phase A~H update log, `scripts/audit_v3k_verify_1b_closure.py` | safe-staged 완료, runtime ON은 gate 전 |
| LS증권 제외 | `scripts/audit_v3k_verify_1a.py --base 57496d24`, `scripts/audit_v3k_phase_g_ls_excise.py`, closure audit | 충족 |
| Kiwoom 유지 | `scripts/audit_v3k_verify_1a.py --base 57496d24`, `scripts/verify_nonrelease_sync.py` | 충족 |
| DB/학습 데이터 반영 | shadow/read-only DB 설계와 dry-run scripts, F1 cutover approval prep 문서 | 실제 운영 DB cutover는 미실행 |
| 분석/학습/백테스트 기능 반영 | analyzer adapter, Phase F proof, backtest learning hook, realtime learning boundary 문서와 smoke | default-OFF / approval-gated |
| microstructure/거래 판단 확장 | Phase G engine, parity/benchmark, LS excise audit | G-3 ON 미실행 |
| GUI 설정 반영 | sidecar design, schema validator, readonly loader, preview, approval template, first gate preflight/blocker snapshot | 실제 sidecar write 미실행 |
| live Kiwoom dry-run | Phase H H-1 contract-only hook, H-2/H-3 approval prep | KHOPENAPI connect/login 미실행 |
| live order/exit rule consumption | approval prep와 runtime activation gap 문서 | 최종 live decision wiring 미실행 |
| 단계별 commit 관리 | Page064~Page073 docs, `docs/CARRY_FORWARD_REGISTRY.md`, 한국어 Lore commit | 계속 유지 |
| goal skill 사용 | active goal 유지, Page068 handoff, Page073 checklist | 완료 호출 금지 |
| 검증 명령 | `python scripts/run_v3k_audit_suite.py`, `python scripts/verify_nonrelease_sync.py`, `git diff --check`, artifact status | 통과 필요 |

## 남은 approval gate checklist

| 순서 | Gate | 현재 조건 | 성공 조건 |
| ---: | --- | --- | --- |
| 1 | `gui-sidecar-write-await-user-approval` | `V3K_GUI_SIDECAR_USER_ACK` absent, writer/rollback absent | 정확한 one-gate 승인 후 default-OFF sidecar write와 rollback 검증 |
| 2 | `phase-f-f4-on-await-user-approval` | `V3K_PHASE_F_USER_ACK` absent | Phase F analyzer ON 전환을 default-OFF/rollback 조건으로 검증 |
| 3 | `phase-g-g3-on-await-user-approval` | `V3K_PHASE_G_USER_ACK` absent | Phase G microstructure ON 전환을 parity/benchmark 조건으로 검증 |
| 4 | `phase-h-h2-h3-live-dryrun-await-user-approval` | `V3K_PHASE_H_USER_ACK` absent | KHOPENAPI 승인 환경에서 Kiwoom live dry-run만 검증 |
| 5 | `f1-actual-db-cutover-await-user-approval` | `V3K_CUTOVER_USER_ACK` absent | 백업, rollback, 운영 DB cutover 승인 증거 확보 |
| 6 | `live-order-exit-rule-consumption-await-user-approval` | `V3K_LIVE_DECISION_USER_ACK` absent | live order/exit rule consumption을 최종 승인 후 연결 |

## 현재 미완료 이유

- actual gate execution progress: `0/6`
- first gate `gui-sidecar-write-await-user-approval`도 아직 approval phrase만 정의되어 있고 USER_ACK, writer, rollback, sidecar artifact가 없다.
- `phase-f-f4-on`, `phase-g-g3-on`, `phase-h-h2-h3`, `f1 actual DB cutover`, `live-order-exit-rule-consumption`은 모두 사용자 승인과 환경 조건이 필요하다.
- 따라서 suite green은 “안전하게 막혀 있다”는 증거이지 “최종 목표 완료” 증거가 아니다.

## 완료 불가 조건

다음 중 하나라도 사실이면 goal completion은 금지된다.

- `actual approval gate execution`이 `6/6`이 아니다.
- `LS Securities` 직접 broker runtime 의존이 들어왔다.
- Kiwoom order/exit/live runtime이 승인 없이 변경되었다.
- 신규 기능이 default-ON으로 바뀌었다.
- `_database`, `_database_v3k_shadow`, `_v3k_sidecar`, DB 파일 또는 raw `.omx/reports`가 승인 없이 commit되었다.
- `python scripts/run_v3k_audit_suite.py`가 실패한다.
- `python scripts/verify_nonrelease_sync.py`가 실패한다.

## 현재 사용할 검증 명령

```powershell
python scripts/audit_v3k_goal_completion_objective_checklist.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## 다음 진행 안내

승인 없이 계속 진행하면 다음 작업은 review-only blocker 점검만 가능하다. 실제 첫 gate 실행을 위해서는 아래 정확한 문구가 필요하다.

```text
I approve gui-sidecar-write-await-user-approval only
```

추천 OMX 명령:

```powershell
omx ralph "force: 현재 active V3K goal을 유지하고 STOM_Version_2U_C에서 남은 approval gate 중 다음 1개만 진행한다. 명시적 one-gate 승인 문구가 없으면 실제 USER_ACK, sidecar write, DB write, KHOPENAPI connect/login, ON 전환, live runtime 변경을 실행하지 않는다. 먼저 docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md와 docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md를 읽고, 실행 가능한 낮은 위험 작업만 문서화/검증/커밋한다. 검증은 python scripts/run_v3k_audit_suite.py, python scripts/verify_nonrelease_sync.py, git diff --check, artifact status를 통과시킨다."
```

