# V3K Page 040 — Phase G G-3 approval gate 완료

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 039 / Phase G G-2 parity·benchmark work |
| 현재 page | Page 040 / Phase G G-3 approval gate |
| 다음 page | Page 041 / V3K governance gap triage |
| 목적 | G-2 proof가 있어도 Phase G를 바로 ON 하지 않고, 사용자 승인·rollback·monitoring·registry 조건을 gate로 고정한다. |
| 결과 | `blocked-awaiting-user-approval` |
| 위험도 | critical |

---

## 1. Page040 판정

Page039에서 Phase G microstructure engine의 synthetic parity와 benchmark proof는 통과했다. 그러나 proof 통과는 ON 승인과 동의어가 아니다. 현재 시점에는 다음 필수 조건이 없다.

| 조건 | 현재 상태 | 판정 |
| --- | --- | --- |
| 사용자 명시 승인 | 없음 | 미충족 |
| `V3K_PHASE_G_USER_ACK=1` 사용 승인 | 없음 | 미충족 |
| `V3K-PHASE-G-ENABLE` registry 생성 승인 | 없음 | 미충족 |
| live order/exit rule 연결 승인 | 없음 | 미충족 |
| rollback plan의 실제 운영 승인 | 문서 수준만 존재 | 미충족 |
| 24h monitoring 계획 승인 | 문서 수준만 존재 | 미충족 |
| benchmark/parity baseline archive 정책 | Architect addendum M3의 governance follow-up으로 남음 | 미충족 |
| Kiwoom live runtime 변경 승인 | 없음 | 미충족 |

따라서 Page040의 최종 판정은 `blocked-awaiting-user-approval`이다.

---

## 2. Page039 proof 확인

Page040에서는 아래 proof가 존재함을 확인했다.

| proof | 경로 | 상태 |
| --- | --- | --- |
| parity proof script | `scripts/backtest_v3k_phase_g_parity.py` | 존재 / 재실행 PASS |
| benchmark proof script | `scripts/benchmark_v3k_phase_g_engine.py` | 존재 / 재실행 PASS |
| LS/runtime excise audit | `scripts/audit_v3k_phase_g_ls_excise.py` | 두 신규 script 포함 / PASS |
| runtime activation gap audit | `scripts/audit_v3k_runtime_activation_gap.py` | Page040 처리 후 next 이동 |
| VERIFY-1A / VERIFY-1B | `scripts/audit_v3k_verify_1a.py`, `scripts/audit_v3k_verify_1b_closure.py` | PASS |

중요: `.omx/reports/v3k-phase-g-*-latest.json`은 ignored local evidence로만 사용되며 commit하지 않는다.

---

## 3. ON 금지 범위

사용자가 별도 ON cycle을 명시적으로 승인하지 않는 한 아래를 실행하지 않는다.

- `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=True` 기본값 변경
- `V3K-PHASE-G-ENABLE` registry 생성
- `V3K_PHASE_G_USER_ACK=1` 사용
- live order/exit rule 연결
- `trade/base_strategy.py` 또는 Kiwoom live strategy decision path 변경
- KHOPENAPI login/connect 또는 주문 API 호출
- 운영 `_database/` read/write
- DB 파일 또는 `.omx/reports/` commit
- LS Securities 직접 의존 import/call 추가

---

## 4. 왜 blocked가 올바른가

Phase G는 V3K의 핵심 V3 기능이지만, microstructure output은 live order/exit decision과 결합될 경우 실제 거래 판단에 영향을 줄 수 있다. 따라서 G-2 proof가 통과했더라도 다음 조건 없이는 ON을 진행할 수 없다.

1. 사용자가 `Phase G ON` 자체를 명시적으로 승인해야 한다.
2. ON registry와 rollback 절차가 별도 commit으로 남아야 한다.
3. live runtime 연결 전후의 24h monitoring 계획이 있어야 한다.
4. Architect addendum에서 지적한 M3 baseline archive 정책을 ON 전까지 해소해야 한다.
5. M1/M2 governance gap도 추후 ON 전환의 안정성을 높이기 위해 먼저 triage해야 한다.

---

## 5. 다음 안전 후보

다음 후보는 Page041 / `governance-gap-triage-plan`이다.

Page041은 ON 실행이 아니라, `docs/update_log/2026-05-13_v3k_code_review_addendum_architect_iterate.md`에서 정본화한 M1/M2/M3 governance gap을 triage하는 안전 단계다.

| gap | 요약 | Page041 처리 방향 |
| --- | --- | --- |
| M1 | `v3k_analyzer_adapter.py`가 staging module의 single point of coupling | contract/docstring/변경 정책 검토 |
| M2 | audit guard CI/pre-commit 자동 실행 부재 | local audit runner 또는 hook/CI 정책 문서화 검토 |
| M3 | Phase F/G/H baseline report archive 정책 부재 | ON 전 baseline archive 예외 정책 검토 |

Directive: Page040 blocked 판정을 Phase G 기능 실패로 해석하지 말 것. G-2 proof는 존재하지만, ON 승인은 별도 사용자 승인·rollback·monitoring·governance 조건이 충족될 때까지 보류한다.
