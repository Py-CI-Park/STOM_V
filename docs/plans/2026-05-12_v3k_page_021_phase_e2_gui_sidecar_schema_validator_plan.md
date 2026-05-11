# V3K Page 021 — Phase E-2 GUI sidecar schema validator 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `46d24856 V3K GUI sidecar persistence를 write 없이 설계한다`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md`
- `docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md`
- `docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md`

---

## 0. 목적

Page 021의 목적은 실제 sidecar 파일 write 없이 V3K GUI sidecar schema payload를 검증하는 pure validator를 구현하는 것이다.

이 단계는 future persistence 구현 전 corruption recovery와 default-OFF fallback을 코드와 smoke로 증명하기 위한 중간 단계다.

---

## 1. Page 021 완료 결과

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 021-1 | schema validator 구현 | `strategy/v3k_gui_sidecar.py`에 filesystem write 없는 `validate_v3k_gui_sidecar_payload()`를 추가했다. |
| 021-2 | valid payload smoke | dict payload와 JSON text payload 모두 schema v1로 정상 정규화되는지 검증했다. |
| 021-3 | invalid/corrupt smoke | missing payload, invalid JSON, non-mapping, missing schema, unsupported schema/surface, invalid settings가 default-OFF fallback 되는지 검증했다. |
| 021-4 | session override 관계 | sidecar load result보다 session-only preview override가 우선한다는 merge contract를 검증했다. |
| 021-5 | no-artifact guard | `_v3k_sidecar`, `_database`, `*.db` artifact가 생성되지 않음을 검증했다. |

현재 진행률:

```text
Page 021: [██████████] 5 / 5 = 100%
```

---

## 2. 구현된 validator contract

### 2.1 모듈과 주요 API

추가 모듈:

- `strategy/v3k_gui_sidecar.py`

주요 API:

- `validate_v3k_gui_sidecar_payload(payload)`
- `apply_v3k_sidecar_session_override(sidecar_result, session_settings)`
- `V3KGuiSidecarValidationResult`

### 2.2 Validator 입력

허용 입력:

- `dict`/`Mapping`
- JSON 문자열
- UTF-8 bytes
- `None`

금지/제외:

- filesystem read/write
- `_v3k_sidecar/v3k_gui_settings.json` 생성
- operating `_database/setting.db` 접근

### 2.3 Fallback 정책

다음은 모두 `valid=False`, default-OFF settings, diagnostic 반환으로 처리한다.

- payload missing
- invalid JSON
- mapping이 아닌 payload
- missing/unsupported `schema_version`
- unsupported `surface_version`
- `settings`가 mapping이 아님

unknown setting key는 valid schema에서는 무시하고 diagnostic에 남긴다.

### 2.4 Session-only override 우선순위

Page 021에서 검증한 우선순위는 다음과 같다.

```text
V3K default-OFF
-> valid sidecar settings
-> current session-only preview override
```

즉, future sidecar load가 구현되더라도 현재 session preview toggle은 process lifetime 동안 더 높은 우선순위를 가진다.

---

## 3. 이번 Page에서 하지 않은 것

| 하지 않은 작업 | 이유 |
| --- | --- |
| sidecar 파일 write | Page 021은 pure validator 단계다. |
| sidecar 파일 read | 파일 경로 loader는 Page 022에서 별도 검토한다. |
| operating `_database/setting.db` write | V3K persistence는 운영 setting DB와 분리한다. |
| Kiwoom live/order/exit runtime 변경 | GUI schema validator와 무관하며 계속 금지다. |
| formula/global runtime hook | Page 018에서 보류했다. |
| analyzer output trading decision | live trading 영향이 있어 별도 phase 전까지 금지다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 4. 검증 기준

Page 021 완료 검증은 다음을 통과했다.

- `python -m py_compile strategy/v3k_gui_sidecar.py scripts/smoke_v3k_gui_sidecar_schema_validator.py scripts/audit_v3k_gui_sidecar_persistence_design.py scripts/audit_v3k_verify_1b_closure.py`
- `python scripts/smoke_v3k_gui_sidecar_schema_validator.py`
- `python scripts/audit_v3k_gui_sidecar_persistence_design.py`
- V3K smoke 전체
- `python scripts/audit_v3k_verify_1a.py --base 57496d24`
- `python scripts/audit_v3k_verify_1b_closure.py`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`
- `git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph`

---

## 5. 다음 페이지

다음은 Page 022 / Phase E-3 `GUI sidecar read-only loader`다.

Page 022의 목적은 실제 write 없이 sidecar file path를 읽는 read-only loader를 구현할지 판단하고, 구현한다면 missing file/corrupt file/valid file을 모두 default-OFF fallback 또는 valid load로 처리하는 것이다.

---

## 6. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 022 Phase E-3 GUI sidecar read-only loader를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md와 docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md를 기준으로, 실제 sidecar write 없이 `_v3k_sidecar/v3k_gui_settings.json` 후보 경로를 read-only로 load하는 adapter를 설계/구현한다. missing file, corrupt file, valid file, unknown key, default-OFF fallback, session-only override 관계를 tempfile 기반 smoke로 검증하되 실제 repo `_v3k_sidecar` artifact는 만들지 않는다. 운영 _database/setting.db schema/write, sidecar write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
