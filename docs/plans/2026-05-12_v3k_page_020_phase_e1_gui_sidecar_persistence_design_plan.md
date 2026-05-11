# V3K Page 020 — Phase E-1 GUI sidecar persistence design 계획

작성일: 2026-05-12 KST
완료일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `87d7e696 V3K runtime activation 다음 후보를 GUI sidecar 설계로 좁힌다`

기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md`
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md`
- `docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md`

---

## 0. 목적

Page 020의 목적은 session-only V3K GUI 설정을 미래에 안전하게 저장할 수 있도록 sidecar persistence contract를 설계하는 것이다.

이번 단계에서도 실제 sidecar write는 구현하지 않는다. 먼저 파일 경로, ignore/backup, corruption recovery, schema version, default-OFF rollback, session-only preview와의 관계, smoke 계획을 문서와 audit로 고정한다.

---

## 1. Page 020 완료 결과

| Step | 작업 | 완료 결과 |
| ---: | --- | --- |
| 020-1 | sidecar 경로 설계 | sidecar root는 `_v3k_sidecar/`, 후보 파일은 `_v3k_sidecar/v3k_gui_settings.json`으로 정의했다. |
| 020-2 | ignore/backup 정책 | `.gitignore`에 `_v3k_sidecar/`를 추가했다. backup 후보는 `_v3k_sidecar/backups/` 아래에 두기로 설계했다. |
| 020-3 | schema version 설계 | `schema_version=1`, `surface_version`, `settings`, `updated_at`, `source` 필드를 필수 schema 초안으로 고정했다. |
| 020-4 | corruption recovery | missing/corrupt/unknown schema는 write 없이 default-OFF fallback과 diagnostic으로 처리하기로 설계했다. |
| 020-5 | smoke 계획 | `scripts/audit_v3k_gui_sidecar_persistence_design.py`로 no-write, ignored path, default-OFF, session-only preview boundary를 검증한다. |

현재 진행률:

```text
Page 020: [██████████] 5 / 5 = 100%
```

---

## 2. Sidecar persistence contract

### 2.1 경로

| 항목 | 값 |
| --- | --- |
| sidecar root | `_v3k_sidecar/` |
| settings file | `_v3k_sidecar/v3k_gui_settings.json` |
| backup dir | `_v3k_sidecar/backups/` |
| git 추적 | 금지. `_v3k_sidecar/` 전체를 `.gitignore`에 추가한다. |
| 운영 DB 영향 | 없음. `_database/setting.db`를 읽거나 쓰지 않는다. |

### 2.2 schema v1 초안

```json
{
  "schema_version": 1,
  "surface_version": "V3K_SETTINGS_SURFACE_V1",
  "settings": {
    "<V3K feature flag key>": false
  },
  "updated_at": "<ISO-8601 timestamp>",
  "source": "v3k_gui_settings_preview"
}
```

규칙:

- `schema_version`이 없거나 1이 아니면 default-OFF fallback.
- `settings`가 mapping이 아니면 default-OFF fallback.
- unknown key는 무시하고 diagnostic에 남긴다.
- 값은 기존 `normalize_v3k_settings()` contract에 따라 bool로 정규화한다.
- 손상된 파일을 자동 overwrite하지 않는다.

### 2.3 session-only preview와 persisted setting 관계

현재 preview는 계속 session-only다.

향후 load가 구현되면 권장 우선순위는 다음과 같다.

```text
DEFAULT_FLAGS / V3K defaults
-> valid sidecar settings load
-> current session preview toggle override
```

단, Reset 버튼은 우선 session memory만 OFF로 돌린다. persisted reset/write는 별도 저장 action이 도입될 때만 다룬다.

### 2.4 backup/rollback 정책

향후 write 구현 전제 조건:

- write 전 기존 sidecar가 있으면 `_v3k_sidecar/backups/` 아래로 timestamped backup을 만든다.
- 새 파일은 temp file에 먼저 쓰고 atomic replace한다.
- write 실패 시 기존 파일을 유지한다.
- corrupt file은 자동 삭제/overwrite하지 않고 default-OFF fallback한다.
- 모든 경로는 `_v3k_sidecar/` 내부로 제한한다.

---

## 3. 이번 Page에서 하지 않은 것

| 하지 않은 작업 | 이유 |
| --- | --- |
| sidecar 파일 생성 | Page 020은 design page다. runtime artifact를 만들지 않는다. |
| sidecar write 구현 | 경로·schema·복구·검증 contract가 먼저다. |
| operating `_database/setting.db` write | V3K persistence는 운영 setting DB와 분리한다. |
| Kiwoom live/order/exit runtime 변경 | persistence 설계와 무관하며 계속 금지다. |
| formula/global runtime hook | Page 018에서 보류했다. |
| analyzer output trading decision | live trading 영향을 주므로 별도 phase 전까지 금지다. |
| LS증권 직접 의존성 | V3K 정의상 영구 제외다. |

---

## 4. 검증 기준

Page 020 완료 검증은 다음을 통과했다.

- `python -m py_compile scripts/audit_v3k_gui_sidecar_persistence_design.py`
- `python scripts/audit_v3k_gui_sidecar_persistence_design.py`
- V3K smoke 전체
- `python scripts/audit_v3k_verify_1a.py --base 57496d24`
- `python scripts/audit_v3k_verify_1b_closure.py`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`
- `git status --short -- _v3k_sidecar _database _database_v3k_shadow _log backup *.db backtest/graph`

---

## 5. 다음 페이지

다음은 Page 021 / Phase E-2 `GUI sidecar schema validator`다.

Page 021의 목적은 파일 write 없이 sidecar schema payload를 검증하고, valid/missing/corrupt/unknown-key 입력을 default-OFF fallback과 diagnostics로 정리하는 pure validator를 구현하는 것이다.

---

## 6. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 021 Phase E-2 GUI sidecar schema validator를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md와 docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md를 기준으로, 실제 sidecar 파일 write 없이 V3K GUI sidecar schema payload를 검증하는 pure validator를 구현한다. valid schema, missing schema, corrupt/invalid payload, unknown key, default-OFF fallback, session-only override 관계를 smoke로 증명한다. 운영 _database/setting.db schema/write, 실제 _v3k_sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
