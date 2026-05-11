# V3K Page 021 — Phase E-2 GUI sidecar schema validator 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md`
- `docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md`

---

## 0. 목적

Page 021의 목적은 실제 sidecar 파일 write 없이 V3K GUI sidecar schema payload를 검증하는 pure validator를 구현하는 것이다.

이 단계는 future persistence 구현 전 corruption recovery와 default-OFF fallback을 코드와 smoke로 증명하기 위한 중간 단계다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 021-1 | schema validator 구현 | dict/string payload를 검증하되 filesystem write를 하지 않는다. |
| 021-2 | valid payload smoke | schema v1 valid settings가 정상 정규화되는지 확인한다. |
| 021-3 | invalid/corrupt smoke | missing schema, invalid JSON, unknown key가 default-OFF fallback/diagnostic으로 처리되는지 확인한다. |
| 021-4 | session override 관계 | sidecar load result와 session-only preview override 우선순위를 문서화/검증한다. |
| 021-5 | no-artifact guard | `_v3k_sidecar`, `_database`, `*.db` artifact를 만들지 않음을 검증한다. |

현재 진행률:

```text
Page 021: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

다음은 Page 021에서 변경하지 않는다.

- 실제 `_v3k_sidecar/v3k_gui_settings.json` file write
- operating `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- LS증권 직접 의존성

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 021 Phase E-2 GUI sidecar schema validator를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md와 docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md를 기준으로, 실제 sidecar 파일 write 없이 V3K GUI sidecar schema payload를 검증하는 pure validator를 구현한다. valid schema, missing schema, corrupt/invalid payload, unknown key, default-OFF fallback, session-only override 관계를 smoke로 증명한다. 운영 _database/setting.db schema/write, 실제 _v3k_sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_gui_sidecar_persistence_design.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB/sidecar artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
