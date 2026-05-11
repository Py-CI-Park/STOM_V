# V3K Phase E-1 GUI sidecar persistence design 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `87d7e696 V3K runtime activation 다음 후보를 GUI sidecar 설계로 좁힌다`

---

## 1. 이번 작업의 목적

Page 019에서 다음 runtime activation 후보를 `GUI setting persistence sidecar design`으로 좁혔다. Page 020의 목적은 실제 sidecar write를 구현하기 전에 sidecar persistence의 경로, ignore, schema, corruption recovery, rollback, smoke contract를 먼저 고정하는 것이다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 020 Phase E-1 GUI sidecar persistence design ..."
```

결과는 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. Sidecar 설계 결정

| 항목 | 결정 |
| --- | --- |
| sidecar root | `_v3k_sidecar/` |
| settings file | `_v3k_sidecar/v3k_gui_settings.json` |
| backup dir | `_v3k_sidecar/backups/` |
| git policy | `_v3k_sidecar/` 전체 ignore |
| schema version | `1` |
| operating setting DB | 사용하지 않음 |
| current preview | 계속 session-only |
| 이번 단계 write | 없음 |

---

## 4. Schema v1 초안

필수 필드:

- `schema_version`
- `surface_version`
- `settings`
- `updated_at`
- `source`

정책:

- `schema_version != 1`이면 default-OFF fallback.
- `settings`가 dict가 아니면 default-OFF fallback.
- unknown key는 무시하고 diagnostic에 남긴다.
- bool 정규화는 기존 `normalize_v3k_settings()`를 따른다.
- corrupt payload는 자동 overwrite하지 않는다.

---

## 5. Session-only preview 관계

현재 `ui/ui_v3k_settings_preview.py`는 계속 session-only다.

- dialog toggle은 MainWindow-like object의 in-memory `v3k_settings`, `v3k_feature_flags`만 변경한다.
- setting DB 또는 sidecar file에 쓰지 않는다.
- Page 020에서도 이 boundary를 유지한다.

향후 sidecar load가 생기더라도 추천 우선순위는 다음과 같다.

```text
V3K default-OFF
-> valid sidecar load
-> current session preview override
```

---

## 6. 추가한 검증 스크립트

추가 파일:

- `scripts/audit_v3k_gui_sidecar_persistence_design.py`

검사 내용:

1. Page 020 기준 문서가 존재하는지 확인한다.
2. `_v3k_sidecar/`가 `.gitignore`에 포함되어 있는지 확인한다.
3. sidecar file, backup dir, schema version contract가 예상대로인지 확인한다.
4. V3K settings contract가 default-OFF와 aligned 상태인지 확인한다.
5. session-only preview notice와 `persistent_writes=False` boundary가 유지되는지 확인한다.
6. runtime preview/settings code가 sidecar write 구현을 포함하지 않는지 확인한다.
7. `_v3k_sidecar`, `_database`, `_database_v3k_shadow`, `_log`, `backup`, `*.db`, `backtest/graph` artifact status가 clean인지 확인한다.

---

## 7. 의도적으로 하지 않은 작업

| 하지 않은 작업 | 이유 |
| --- | --- |
| sidecar 파일 생성 | design page이며 runtime artifact를 만들지 않는다. |
| sidecar write 구현 | schema validator와 corruption fallback smoke가 먼저 필요하다. |
| operating `_database/setting.db` write | V3K persistence는 운영 setting DB와 분리한다. |
| Kiwoom live/order/exit runtime 변경 | persistence 설계와 무관하며 계속 금지다. |
| formula/global runtime hook | Page 018에서 보류했다. |
| analyzer output trading decision | live trading 영향이 있어 별도 phase 전까지 금지다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 8. 검증 결과

이번 단계에서 실행하고 통과한 검증:

```powershell
python -m py_compile scripts/audit_v3k_gui_sidecar_persistence_design.py
python scripts/audit_v3k_gui_sidecar_persistence_design.py
python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/audit_v3k_gui_sidecar_persistence_design.py scripts/audit_v3k_runtime_activation_gap.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/audit_v3k_runtime_activation_gap.py
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
git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph
```

결과:

- GUI sidecar persistence design audit 통과
- runtime activation gap audit 통과
- V3K smoke 전체 통과
- VERIFY-1A/1B 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime/sidecar artifact status 변경 없음

---

## 9. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 20 / 21 = 95.2%
현재 Page 020 진행률:          [██████████] 5 / 5 = 100%
다음 Page 021 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 020은 sidecar persistence design contract를 고정하고 완료한다. 다음은 Page 021에서 실제 file write 없이 sidecar schema payload validator를 구현하는 단계다.
