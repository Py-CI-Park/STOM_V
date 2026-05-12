# V3K Page 032 — Phase H H-2/H-3 approval gate 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 031 / F1 actual cutover approval gate |
| f51 단계 | B3 / Phase H H-2/H-3 |
| 위험도 | critical |
| live dry-run | 사용자 승인 + KHOPENAPI 환경 전 금지 |

---

## 0. 목적

Page 032는 Phase H H-2/H-3 actual live dry-run 또는 ON 전환을 바로 실행하는 단계가 아니다. H-2/H-3의 승인 조건과 환경 조건을 확인하고, 미충족 시 no-go를 문서화하는 gate다.

---

## 1. Gate 조건

| 조건 | 필요 상태 |
| --- | --- |
| H-1 contract-only hook | 완료 |
| KHOPENAPI 호환 환경 | 필요 |
| `V3K_PHASE_H_USER_ACK=1` | actual H-2/H-3 cycle에서만 설정 |
| 주문 API 호출 0건 증거 | live dry-run 전후 audit 필요 |
| Kiwoom 주문/청산 runtime 코드 보존 | 필수 |
| post-health smoke | 필요 |
| ON 전환 | 사용자 승인 후 별도 commit |

---

## 2. 본 page에서 금지

- KHOPENAPI 실제 login/connect.
- live dry-run 실행.
- Kiwoom 주문/청산/live runtime 변경.
- `V3K_PHASE_H_USER_ACK=1` 설정.
- feature flag ON 전환.
- LS Securities 직접 의존.
- 운영 `_database/` write.

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Phase H H-2/H-3 approval gate를 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md, docs/update_log/2026-05-12_v3k_phase_h_h1_kiwoom_dryrun_hook.md, docs/update_log/2026-05-12_v3k_f1_actual_cutover_approval_gate.md, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. KHOPENAPI 호환 환경, V3K_PHASE_H_USER_ACK=1, live dry-run, ON 전환, Kiwoom 주문/청산/live runtime 변경, LS Securities 직접 의존, feature flag ON 전환은 수행하지 말고 H-2/H-3 gate 충족 여부와 승인 필요 조건만 문서화한다. 완료 시 update_log/registry/audit next candidate를 갱신하고 audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시킨 뒤 한국어 Lore commit한다."
```
