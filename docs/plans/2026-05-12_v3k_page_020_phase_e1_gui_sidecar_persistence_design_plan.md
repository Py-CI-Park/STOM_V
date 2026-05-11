# V3K Page 020 — Phase E-1 GUI sidecar persistence design 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 문서:
- `docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md`
- `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md`

---

## 0. 목적

Page 020의 목적은 session-only V3K GUI 설정을 미래에 안전하게 저장할 수 있도록 sidecar persistence contract를 설계하는 것이다.

이번 단계에서도 실제 sidecar write는 구현하지 않는다. 먼저 파일 경로, ignore/backup, corruption recovery, schema version, default-OFF rollback, session-only preview와의 관계, smoke 계획을 문서와 audit로 고정한다.

---

## 1. In-scope

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 020-1 | sidecar 경로 설계 | 운영 `_database/setting.db`를 건드리지 않는 sidecar 후보 경로를 정의한다. |
| 020-2 | ignore/backup 정책 | git 추적 여부, backup 대상 여부, 사용자 환경별 충돌 가능성을 정리한다. |
| 020-3 | schema version 설계 | persisted V3K flags/settings의 versioned schema 초안을 작성한다. |
| 020-4 | corruption recovery | JSON/DB 손상 시 default-OFF fallback과 진단 메시지 정책을 정의한다. |
| 020-5 | smoke 계획 | write 구현 전후 필요한 no-artifact, default-OFF, load/save mock smoke를 정의한다. |

현재 진행률:

```text
Page 020: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 2. Out-of-scope

다음은 Page 020에서 변경하지 않는다.

- 실제 sidecar 파일 write 구현
- 운영 `_database/setting.db` schema/write
- Kiwoom 주문/청산/live runtime
- formula/global runtime hook
- analyzer output trading decision
- LS증권 직접 의존성

---

## 3. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 020 Phase E-1 GUI sidecar persistence design을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md와 docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md를 기준으로, V3K GUI setting persistence를 operating _database/setting.db가 아닌 sidecar 방식으로 설계한다. 이번 단계에서는 실제 sidecar write를 구현하지 말고, 파일 경로, gitignore/backup 정책, corruption recovery, schema version, default-OFF rollback, session-only preview와의 관계, smoke 계획을 문서와 audit로 고정한다. Kiwoom 주문/청산/live runtime, formula/global runtime hook, analyzer output trading decision, 운영 _database/setting.db schema/write, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, V3K smoke 전체, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
