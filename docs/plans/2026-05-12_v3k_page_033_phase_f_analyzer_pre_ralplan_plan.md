# V3K Page 033 — Phase F analyzer pre-ralplan 계획

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-12 KST |
| worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| branch | `STOM_Version_2U_C` |
| 이전 page | Page 032 / Phase H H-2/H-3 approval gate |
| f51 단계 | C1 / F3 Phase F analyzer 전략 반영 사전 ralplan |
| 위험도 | high |
| 구현 | 본 page에서는 금지 |

---

## 0. 목적

Page 033은 analyzer output을 실제 전략/주문/청산 판단에 연결하기 전에 LF1~LF4 invariant를 다시 합의하는 단계다. 구현이 아니라 deliberate-mode planning이다.

---

## 1. Gate 조건

| 조건 | 필요 상태 |
| --- | --- |
| F5 production read-only boundary | 완료 |
| F1 actual cutover | 권장이나 현재 approval-gated |
| LF1 parity 통과 후 ON | pre-work에서 증명 필요 |
| LF2 rollback flag 즉시 OFF | pre-work에서 증명 필요 |
| LF3 손실·MDD·거래횟수 변동 한계 | backtest parity에서 수치화 필요 |
| LF4 registry | ON 전환 시점 별도 commit 필요 |

---

## 2. 본 page에서 금지

- analyzer output을 live 주문/청산 판단에 사용.
- feature flag ON 전환.
- Kiwoom 주문/청산/live runtime 변경.
- 운영 `_database/` write.
- LS Securities 직접 의존.

---

## 3. 추천 OMX 명령

```powershell
omx ralplan --deliberate "V3K F3 Phase F analyzer output 전략 반영 사전 합의를 1단계만 수행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_phase_f_analyzer_strategy_plan.md, docs/update_log/2026-05-12_v3k_phase_h_h2_h3_approval_gate.md, docs/CARRY_FORWARD_REGISTRY.md를 먼저 읽는다. LF1 parity 통과 후 ON, LF2 rollback flag 즉시 OFF, LF3 손실·MDD·거래횟수 변동 한계, LF4 V3K-PHASE-F-ENABLE registry invariant를 pre-mortem 3개(parity 한계 이탈, rollback flag 미작동, 24h monitoring 한계 이탈)와 expanded test plan으로 재검토한다. 본 단계는 합의/문서화만 수행하며 analyzer output live 주문/청산 사용, feature flag ON, Kiwoom live runtime 변경, 운영 _database write, LS Securities 직접 의존은 금지한다. 완료 시 update_log/registry/audit next candidate를 갱신하고 audit_v3k_runtime_activation_gap, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시킨 뒤 한국어 Lore commit한다."
```
