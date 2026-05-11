# V3K Phase E-2 GUI sidecar schema validator 기록

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
이전 기준 commit: `46d24856 V3K GUI sidecar persistence를 write 없이 설계한다`

---

## 1. 이번 작업의 목적

Page 020에서 V3K GUI sidecar persistence의 경로와 schema를 설계했다. Page 021의 목적은 실제 sidecar 파일을 읽거나 쓰지 않고, payload 단위의 schema validation과 corruption/default-OFF fallback을 코드와 smoke로 증명하는 것이다.

---

## 2. 실행 방식

먼저 권장 Ralph 명령을 실행했다.

```powershell
omx ralph "force: V3K Page 021 Phase E-2 GUI sidecar schema validator ..."
```

결과는 Codex CLI TTY 제약으로 중단되었다.

```text
[ralph] Ralph persistence mode active. Launching Codex...
Error: stdin is not a terminal
```

따라서 동일 범위를 수동 실행으로 전환했다. 범위와 금지 조건은 Ralph prompt와 동일하게 유지했다.

---

## 3. 구현 내용

### 3.1 `strategy/v3k_gui_sidecar.py`

추가한 상수:

- `V3K_GUI_SIDECAR_DIR = "_v3k_sidecar"`
- `V3K_GUI_SIDECAR_FILE = "_v3k_sidecar/v3k_gui_settings.json"`
- `V3K_GUI_SIDECAR_BACKUP_DIR = "_v3k_sidecar/backups"`
- `V3K_GUI_SIDECAR_SCHEMA_VERSION = 1`
- `V3K_GUI_SIDECAR_REQUIRED_FIELDS`

추가한 API:

- `V3KGuiSidecarValidationResult`
- `validate_v3k_gui_sidecar_payload(payload)`
- `apply_v3k_sidecar_session_override(sidecar_result, session_settings)`

### 3.2 `scripts/smoke_v3k_gui_sidecar_schema_validator.py`

검증 내용:

- valid mapping payload
- valid JSON text payload
- missing payload default-OFF fallback
- invalid JSON default-OFF fallback
- non-mapping payload default-OFF fallback
- missing/unsupported schema version fallback
- unsupported surface version fallback
- invalid settings payload fallback
- unknown key diagnostic
- sidecar result보다 session-only preview override가 우선함
- 검사 전후 sidecar/DB artifact status 무변경

### 3.3 기존 audit 확장

- `scripts/audit_v3k_gui_sidecar_persistence_design.py`가 새 validator constants를 직접 참조하도록 조정했다.
- `scripts/audit_v3k_verify_1b_closure.py`의 required code/scripts 목록에 sidecar validator 관련 파일을 추가했다.

---

## 4. 의도적으로 하지 않은 작업

| 하지 않은 작업 | 이유 |
| --- | --- |
| `_v3k_sidecar/v3k_gui_settings.json` 생성 | validator page이며 runtime artifact를 만들지 않는다. |
| sidecar 파일 read | filesystem loader는 Page 022에서 별도 처리한다. |
| sidecar 파일 write | schema validator와 read-only loader 이후 별도 go/no-go가 필요하다. |
| operating `_database/setting.db` write | V3K persistence는 운영 setting DB와 분리한다. |
| Kiwoom live/order/exit runtime 변경 | GUI sidecar validator와 무관하며 계속 금지다. |
| formula/global runtime hook | Page 018에서 보류했다. |
| analyzer output trading decision | live trading 영향이 있어 별도 phase 전까지 금지다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 5. 검증 결과

이번 단계에서 실행하고 통과한 검증:

```powershell
python -m py_compile strategy/v3k_gui_sidecar.py scripts/smoke_v3k_gui_sidecar_schema_validator.py scripts/audit_v3k_gui_sidecar_persistence_design.py scripts/audit_v3k_verify_1b_closure.py
python scripts/smoke_v3k_gui_sidecar_schema_validator.py
python scripts/audit_v3k_gui_sidecar_persistence_design.py
python -m py_compile strategy/v3k_formula_facade.py trade/formula_manager.py trade/base_strategy.py scripts/audit_v3k_runtime_activation_gap.py scripts/smoke_v3k_formula_facade.py scripts/smoke_v3k_formula_boundary_contract.py scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/audit_v3k_runtime_activation_gap.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_formula_boundary_contract.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_formula_runtime_hook_decision.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_sidecar_schema_validator.py
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

- GUI sidecar schema validator smoke 통과
- GUI sidecar persistence design audit 통과
- runtime activation gap audit 통과
- V3K smoke 전체 통과
- VERIFY-1A/1B 통과
- nonrelease sync guard 통과
- `git diff --check` 통과
- DB/runtime/sidecar artifact status 변경 없음

---

## 6. 현재 위치

```text
전체 V3K staged activation 진행률: [█████████░] 21 / 22 = 95.5%
현재 Page 021 진행률:          [██████████] 5 / 5 = 100%
다음 Page 022 진행률:          [░░░░░░░░░░] 0 / 5 = 0%
```

Page 021은 pure schema validator 구현으로 완료한다. 다음은 Page 022에서 실제 write 없이 read-only sidecar loader를 구현할지 판단하고, 구현 시 tempfile 기반 smoke로 missing/corrupt/valid file handling을 검증하는 단계다.
