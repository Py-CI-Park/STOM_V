# V3K approval gate final decision table

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| page | Page 056 |
| source | Page049~Page055 approval prep and closeout review |
| marker | `APPROVAL_GATE_FINAL_DECISION_TABLE` |
| 상태 | `completed-decision-table` |
| next candidate | `live-order-exit-rule-consumption-await-user-approval` |

---

## 1. 목적 재확인

최종 목적은 `STOM_Version_2U_C`에 V3의 LS Securities 직접 의존을 제외한 신기능을 Kiwoom 유지 상태로 반영하는 것이다. safe-staged 기능, 문서, 감사 guard는 정렬되었지만 실제 운영 활성화는 사용자 승인 gate가 필요하다.

이번 Page056은 남은 gate를 실행하는 commit이 아니다. 사용자가 승인할 수 있도록 위험도, 선행 조건, rollback, monitoring, 금지선을 최종 표로 고정한다.

No actual gate execution: actual ON, USER_ACK 생성, enable registry 생성, KHOPENAPI connect/login, 운영 `_database/` write, DB 파일 commit, `.omx/reports` raw artifact commit, Kiwoom live runtime 변경, live order/exit rule 연결, LS Securities 직접 의존 추가는 수행하지 않았다.

---

## 2. Final decision table

| 순서 | Gate | 위험도 | 선행 조건 | 승인 기록 | rollback / kill switch | monitoring | 현재 결정 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GUI actual sidecar write | medium-high | source-of-truth 위치, schema validator, tempfile writer proof, artifact guard clean | `V3K_GUI_SIDECAR_USER_ACK=1` 또는 동등 update_log 승인 | backup-before-replace, corrupt reject, temp cleanup, disable path | 저장/로드 log, schema mismatch, default-OFF fallback | 승인 대기 |
| 2 | Phase F F-4 ON | critical | Phase F default-OFF smoke, parity proof, rollback audit, F1/sidecar source-of-truth 결정 | `V3K_PHASE_F_USER_ACK=1`, `V3K-PHASE-F-ENABLE` | rollback flag, immediate OFF, 24h stop trigger | parity, 손실, MDD, 거래 횟수, 24h monitoring | 승인 대기 |
| 3 | Phase G G-3 ON | critical | Phase G unit smoke, parity proof, benchmark proof, LS excise audit | `V3K_PHASE_G_USER_ACK=1`, `V3K-PHASE-G-ENABLE` | rollback flag, kill switch, immediate OFF | parity, latency, memory, microstructure signal drift | 승인 대기 |
| 4 | Phase H H-2/H-3 Kiwoom live dry-run | critical | KHOPENAPI compatible environment, H-1 hook smoke, env sentinel, zero-order plan | `V3K_PHASE_H_USER_ACK=1` | no-order guard, dry-run disable, fallback to H-1 contract-only | zero-order evidence, post-health, live log archive | KHOPENAPI 환경 및 승인 대기 |
| 5 | F1 actual DB cutover | critical | backup script, checksum manifest, dry-run smoke, rollback script, post-health plan | `V3K_CUTOVER_USER_ACK=1` | backup restore, rollback script, cutover disable | DB health, post-cutover smoke, 7-day monitoring | 승인 대기 |
| 6 | live order/exit rule consumption | critical | Phase F/G/H/F1 선행 gate 승인, shadow/dryrun proof, staged rollout plan | `V3K_LIVE_DECISION_USER_ACK=1`, `V3K-LIVE-ORDER-EXIT-ENABLE` | `V3K_LIVE_DECISION_DISABLE=1`, kill switch, immediate OFF | shadow/live delta, 주문 수량, 청산 조건, anomaly alert | 최종 critical 승인 대기 |

---

## 3. Prompt-to-artifact checklist

| 명시 요구 | concrete evidence | 현재 상태 |
| --- | --- | --- |
| 남은 gate 6개 모두 포함 | Final decision table | 충족 |
| 사용자 승인 전 actual ON 금지 | `No actual gate execution`, VERIFY-1B | 충족 |
| USER_ACK 없는 실행 금지 | 각 gate 승인 기록 column | 충족 |
| enable registry 없는 ON 금지 | Phase F/G/live decision rows | 충족 |
| KHOPENAPI connect/login 금지 | Phase H row, Directive | 충족 |
| 운영 DB write 금지 | F1 row, Directive, artifact status | 충족 |
| Kiwoom live runtime 유지 | VERIFY-1A | 충족 |
| LS Securities 직접 의존 금지 | VERIFY-1A, LS excise audit | 충족 |
| raw `.omx/reports` commit 금지 | artifact status | 충족 |

---

## 4. 추천 승인 순서

1. GUI actual sidecar write
2. Phase F F-4 ON
3. Phase G G-3 ON
4. Phase H H-2/H-3 Kiwoom live dry-run
5. F1 actual DB cutover
6. live order/exit rule consumption

이 순서는 위험도가 낮은 persistent UI write부터 시작해, 마지막에 실제 거래 판단 경로인 live order/exit rule consumption으로 가는 보수적 순서다. 단, 운영 DB cutover가 먼저 필요하다고 판단되면 F1은 별도 승인 cycle에서 재검토해야 한다.

---

## 5. Stop condition

다음 조건 중 하나라도 없으면 실제 gate 실행을 하지 않는다.

- 사용자 명시 승인
- USER_ACK 또는 동등 승인 기록
- enable registry 또는 동등 활성화 기록
- rollback owner
- monitoring owner
- fallback trigger
- V3K audit suite green
- `verify_nonrelease_sync.py` green
- DB/sidecar/live artifact guard clean

Directive: `APPROVAL_GATE_FINAL_DECISION_TABLE`은 사용자 결정을 돕는 표이며 actual ON, USER_ACK 생성, enable registry 생성, KHOPENAPI connect/login, 운영 DB write, Kiwoom live runtime 변경, live order/exit rule 연결 승인으로 해석하면 안 된다.
---

## Page058 reconciliation note

Page058 separates recommended approval order first from runtime critical next candidate.

- recommended approval order first: `gui-sidecar-write-await-user-approval`
- runtime critical next candidate: `live-order-exit-rule-consumption-await-user-approval`

The first value is the safest user approval order if an approval cycle begins. The second value is the highest risk remaining runtime activation candidate and must not be interpreted as approval to connect live order or exit decisions.

No ON/DB/live execution is granted by this note. USER_ACK creation, enable registry creation, KHOPENAPI connect/login, operating `_database` write, sidecar artifact creation, Kiwoom live runtime modification, live order/exit rule connection, and LS Securities direct dependency remain blocked.
