# V3K Page 019 — Phase E-0 runtime activation gap review 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `0d8ac586 V3K formula/global runtime hook을 dry-run 경계로 보류한다`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md`
- `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md`
- `docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md`

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

## 1. Page 019 완료 결과

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 019-1 | held item inventory | VERIFY-1B held list와 Page 018 보류 항목을 통합해 6개 runtime activation 후보로 정리했다. |
| 019-2 | 위험도 평가 | Kiwoom live 영향, DB 영향, rollback 가능성, smoke 가능성 기준으로 위험도를 평가했다. |
| 019-3 | 다음 구현 후보 선정 | `GUI setting persistence sidecar design`을 다음 후보로 선정했다. 단, Page 020은 sidecar write 구현이 아니라 persistence plan 작성 단계다. |
| 019-4 | 검증 계획 수립 | `scripts/audit_v3k_runtime_activation_gap.py`를 추가해 다음 후보가 하나로 고정되고 runtime guard/artifact clean이 유지되는지 검증한다. |
| 019-5 | 다음 Page 생성 | Page 020 / Phase E-1 GUI sidecar persistence design 계획을 생성했다. |

현재 진행률:

```text
Page 019: [██████████] 5 / 5 = 100%
```

---

## 2. Runtime activation 후보 평가

| 후보 | 위험도 | Kiwoom live 영향 | DB/파일 영향 | smoke 가능성 | 결정 |
| --- | --- | --- | --- | --- | --- |
| formula/global runtime hook | 높음 | 높음 | 낮음 | 중간 | 보류 |
| GUI setting persistence | 중간 | 낮음 | 중간 | 높음 | 다음 후보 |
| analyzer DB constructor runtime use | 높음 | 중간 | 높음 | 중간 | 보류 |
| live order/exit rule consumption | 치명 | 매우 높음 | 낮음 | 낮음 | 보류 |
| production learning DB read | 높음 | 중간 | 높음 | 중간 | 보류 |
| DB cutover/migration | 치명 | 높음 | 매우 높음 | 낮음 | 보류 |

---

## 3. 다음 후보 선정 이유

다음 후보는 `GUI setting persistence sidecar design`이다.

선정 이유:

1. Kiwoom 주문/청산/live runtime을 직접 건드리지 않는다.
2. `trade/formula_manager.py`, `trade/base_strategy.py` 등 VERIFY-1A runtime guard를 완화하지 않아도 된다.
3. 운영 `_database/setting.db`를 수정하지 않고 별도 sidecar 설계를 먼저 검토할 수 있다.
4. 파일 경로, ignore, backup, corruption recovery, rollback 정책을 문서와 smoke로 먼저 고정할 수 있다.
5. 실제 write 구현 전에도 충분히 검증 가능한 contract를 만들 수 있다.

중요한 제한:

```text
Page 020은 sidecar write 구현이 아니라 sidecar persistence design page다.
운영 setting.db schema/write는 계속 금지한다.
sidecar write도 path/ignore/backup/corruption recovery plan 전에는 구현하지 않는다.
```

---

## 4. 계속 보류하는 항목

| 보류 항목 | 보류 이유 |
| --- | --- |
| formula/global runtime hook | VERIFY-1A runtime guard와 충돌하고 live formula namespace를 바꾼다. |
| analyzer DB constructor runtime use | 운영 DB read boundary, locking, fallback 검증이 부족하다. |
| live order/exit rule consumption | 실제 매매 판단에 영향을 주므로 mock/backtest proof 전까지 금지한다. |
| production learning DB read | 운영 DB 성능, lock, rollback 검증이 아직 없다. |
| DB cutover/migration | migration, backup, cutover, rollback plan이 먼저 필요하다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 5. 검증 기준

Page 019 완료 검증은 다음을 통과했다.

- `python -m py_compile scripts/audit_v3k_runtime_activation_gap.py`
- `python scripts/audit_v3k_runtime_activation_gap.py`
- V3K smoke 전체
- `python scripts/audit_v3k_verify_1a.py --base 57496d24`
- `python scripts/audit_v3k_verify_1b_closure.py`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`
- `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph`

---

## 6. 다음 페이지

다음은 Page 020 / Phase E-1 `GUI sidecar persistence design`이다.

Page 020의 목적은 session-only V3K GUI 설정을 미래에 저장할 수 있도록 sidecar persistence contract를 설계하는 것이다. 이 단계도 아직 실제 sidecar write 구현이 아니다.

---

## 7. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 020 Phase E-1 GUI sidecar persistence design을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md와 docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md를 기준으로, V3K GUI setting persistence를 operating _database/setting.db가 아닌 sidecar 방식으로 설계한다. 이번 단계에서는 실제 sidecar write를 구현하지 말고, 파일 경로, gitignore/backup 정책, corruption recovery, schema version, default-OFF rollback, session-only preview와의 관계, smoke 계획을 문서와 audit로 고정한다. Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, 운영 _database/setting.db schema/write, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
