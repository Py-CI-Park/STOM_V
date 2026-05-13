# V3K Page 056 - approval gate final decision table 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 055 / approval gate closeout review |
| 현재 page | Page 056 / approval gate final decision table |
| 상태 | `completed-decision-table` |
| 다음 후보 | `live-order-exit-rule-consumption-await-user-approval` |
| 목적 | 실제 gate 실행 전 사용자가 승인해야 할 남은 gate별 조건, 위험도, 선행 조건, rollback, monitoring, 금지선을 한 표로 고정한다. |
| 실제 실행 여부 | 아님. ON, USER_ACK, enable registry, KHOPENAPI connect/login, 운영 DB write, live decision wiring은 수행하지 않는다. |

---

## 1. 배경

Page055에서 Page049~Page054 승인 준비가 사용자 승인 대기 상태로 정렬되었음을 확인했다. 다음 단계에서 실제 gate를 진행하려면 사용자가 어떤 gate를 승인하는지, 각 gate의 선행 조건과 rollback 조건이 무엇인지 한눈에 확인할 수 있어야 한다.

Page056은 실제 실행 명령이 아니라 최종 decision table이다. 이 문서를 기준으로 사용자는 가장 낮은 위험 gate부터 순차 승인하거나, 모든 운영 gate를 계속 보류할 수 있다.

---

## 2. 성공 기준

| 기준 | 증거 |
| --- | --- |
| 남은 6개 gate가 모두 표에 포함됨 | Page056 update_log |
| 각 gate에 승인 조건, 위험도, 선행 조건, rollback, monitoring 포함 | Page056 update_log |
| 실제 실행 금지선 명시 | Page056 update_log Directive |
| VERIFY-1B token guard 추가 | `scripts/audit_v3k_verify_1b_closure.py` |
| runtime activation gap 경로 guard 추가 | `scripts/audit_v3k_runtime_activation_gap.py` |

---

## 3. 남은 gate

| Gate | 우선순위 | 위험도 |
| --- | --- | --- |
| GUI actual sidecar write | 1 | medium-high |
| Phase F F-4 ON | 2 | critical |
| Phase G G-3 ON | 3 | critical |
| Phase H H-2/H-3 Kiwoom live dry-run | 4 | critical |
| F1 actual DB cutover | 5 | critical |
| live order/exit rule consumption | 6 | critical |

---

## 4. 금지선

- 사용자 명시 승인 없이 actual ON을 수행하지 않는다.
- USER_ACK 또는 동등 승인 기록을 생성하지 않는다.
- enable registry 또는 동등 활성화 기록을 생성하지 않는다.
- KHOPENAPI connect/login을 수행하지 않는다.
- 운영 `_database/` write를 수행하지 않는다.
- DB 파일을 commit하지 않는다.
- live order/exit rule을 연결하지 않는다.
- Kiwoom 주문/청산/live runtime을 수정하지 않는다.
- LS Securities 직접 의존을 추가하지 않는다.

---

## 5. 검증 명령

```powershell
python -m py_compile scripts/audit_v3k_runtime_activation_gap.py scripts/audit_v3k_verify_1a.py scripts/audit_v3k_verify_1b_closure.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/run_v3k_audit_suite.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar
```

---

## 6. 다음 단계

Page056 이후 실제 진행은 사용자의 명시 승인으로 시작해야 한다. 승인 전에는 최종 decision table을 바탕으로 추천 순서와 차단 조건을 안내하는 데서 멈춘다.
