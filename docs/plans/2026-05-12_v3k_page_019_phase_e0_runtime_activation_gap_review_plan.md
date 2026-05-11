# V3K Page 019 — Phase E-0 runtime activation gap review 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md`
- `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md`

---

## 0. 목적

Page 019의 목적은 지금까지 intentionally held로 남긴 runtime activation 항목을 모두 다시 검토해, 다음 구현 대상으로 무엇을 전환할지 결정하는 것이다.

V3K 전체 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

---

## 1. 검토 대상

| 항목 | 현재 상태 | 재검토 질문 |
| --- | --- | --- |
| formula/global runtime hook | dry-run boundary까지 완료, direct hook 보류 | VERIFY-1A guard를 완화하지 않고도 안전하게 노출할 방법이 있는가? |
| GUI setting persistence | session-only preview 완료, persistence 보류 | sidecar/DB 중 어느 쪽이 더 안전한가? |
| analyzer DB constructor runtime use | adapter/staging 완료, runtime constructor use 보류 | read-only production DB 접근을 안전하게 mock/guard할 수 있는가? |
| live order/exit rule consumption | 보류 | live trading 전 mock/backtest에서 충분히 증명할 수 있는가? |
| production learning DB read | shadow/read-only dry-run 단계 | 운영 DB read-only 접근의 락/성능/rollback 조건은 무엇인가? |
| DB cutover/migration | 보류 | migration/cutover/rollback plan 없이 진행 가능한 범위가 있는가? |

---

## 2. Page 019 완료 조건

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 019-1 | held item inventory | VERIFY-1B held list와 최신 Page 018 보류 항목을 한 표로 통합한다. |
| 019-2 | 위험도 평가 | Kiwoom live 영향, DB 영향, rollback 가능성, smoke 가능성을 기준으로 평가한다. |
| 019-3 | 다음 구현 후보 선정 | 가장 안전한 1개 구현 후보와 보류 후보를 명확히 분리한다. |
| 019-4 | 검증 계획 수립 | 후보 구현에 필요한 smoke/audit/update 문서를 정의한다. |
| 019-5 | 다음 Page 생성 | 선택된 후보를 다음 Page의 계획으로 작성한다. |

현재 진행률:

```text
Page 019: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 019 Phase E-0 runtime activation gap review를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md와 docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md를 기준으로, 지금까지 intentionally held로 남긴 runtime activation 항목을 모두 재검토한다. formula/global runtime hook, GUI setting persistence, analyzer DB constructor runtime use, live order/exit rule consumption, production learning DB read, DB cutover/migration 중 어떤 항목을 다음 구현 대상으로 전환할지 위험도·검증 가능성·Kiwoom 유지 조건 기준으로 우선순위를 정한다. LS Securities 직접 의존성은 계속 제외하고, 운영 _database/setting.db schema/write 또는 sidecar write는 별도 migration/persistence plan 없이 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
