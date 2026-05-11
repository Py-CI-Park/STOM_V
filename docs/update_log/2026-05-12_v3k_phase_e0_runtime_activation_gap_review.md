# V3K Phase E-0 runtime activation gap review 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `0d8ac586 V3K formula/global runtime hook을 dry-run 경계로 보류한다`

---

## 1. 이번 작업의 목적

Page 018에서 formula/global direct runtime hook을 보류하고 dry-run boundary를 유지하기로 결정했다. Page 019의 목적은 여기서 멈추지 않고, 지금까지 intentionally held로 남아 있던 runtime activation 후보 전체를 다시 모아 다음에 무엇을 실제 구현 후보로 전환할지 결정하는 것이다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 019 Phase E-0 runtime activation gap review ..."
```

결과는 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. 통합 held item inventory

| 후보 | 현재 상태 | 위험도 | 결정 |
| --- | --- | --- | --- |
| formula/global runtime hook | dry-run boundary 완료, direct hook 보류 | 높음 | 보류 |
| GUI setting persistence | session-only preview 완료, persistence 보류 | 중간 | 다음 후보 |
| analyzer DB constructor runtime use | adapter/staging 완료, runtime constructor use 보류 | 높음 | 보류 |
| live order/exit rule consumption | V3K analyzer output의 거래 판단 반영 보류 | 치명 | 보류 |
| production learning DB read | shadow/read-only dry-run 단계 | 높음 | 보류 |
| DB cutover/migration | 운영 DB 교체/마이그레이션 보류 | 치명 | 보류 |

---

## 4. 다음 후보 결정

다음 구현 후보는 `GUI setting persistence sidecar design`으로 결정했다.

다만 이 결정은 즉시 sidecar write를 구현한다는 뜻이 아니다. Page 020에서는 다음을 먼저 설계한다.

- sidecar 파일 경로
- gitignore/backup 정책
- schema version
- corruption recovery
- default-OFF rollback
- session-only preview와 persisted setting의 우선순위
- smoke/audit 범위

운영 `_database/setting.db` schema/write는 계속 금지한다. sidecar write도 위 정책이 문서와 smoke로 고정되기 전까지 구현하지 않는다.

---

## 5. 후보별 보류 이유

| 보류 후보 | 보류 이유 |
| --- | --- |
| formula/global runtime hook | VERIFY-1A runtime guard와 충돌하고 live strategy global namespace를 바꾼다. |
| analyzer DB constructor runtime use | 운영 DB read boundary와 locking/rollback 검증이 필요하다. |
| live order/exit rule consumption | 실제 매매 판단에 영향을 주므로 mock/backtest proof가 먼저다. |
| production learning DB read | 운영 DB 성능, lock, fallback, rollback 검증이 부족하다. |
| DB cutover/migration | backup/cutover/rollback plan 없이 진행할 수 없다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 6. 추가한 검증 스크립트

추가 파일:

- `scripts/audit_v3k_runtime_activation_gap.py`

검사 내용:

1. Page 019 기준 문서가 존재하는지 확인한다.
2. 다음 후보가 `gui-setting-sidecar-persistence-design` 하나로 고정되었는지 확인한다.
3. VERIFY-1A가 여전히 `trade/base_strategy.py`, `trade/formula_manager.py`를 보호하는지 확인한다.
4. runtime guarded file에 V3K import/hook이 없는지 확인한다.
5. DB/runtime/sidecar artifact status가 clean인지 확인한다.

---

## 7. 검증 결과

이번 단계에서 실행하고 통과한 검증:

```powershell
python -m py_compile scripts/audit_v3k_runtime_activation_gap.py
python scripts/audit_v3k_runtime_activation_gap.py
python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py scripts/smoke_v3k_formula_runtime_hook_decision.py scripts/audit_v3k_runtime_activation_gap.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_settings_surface.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph
```

결과:

- runtime activation gap audit 통과
- V3K smoke 전체 통과
- VERIFY-1A/1B 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime artifact status 변경 없음

---

## 8. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 19 / 20 = 95.0%
현재 Page 019 진행률:          [██████████] 5 / 5 = 100%
다음 Page 020 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 019는 다음 구현 후보를 GUI sidecar persistence design으로 고정하고 완료한다. 다음은 Page 020에서 sidecar persistence의 경로·schema·rollback·smoke 계획을 작성하는 단계다.
