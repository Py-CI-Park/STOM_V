# V3K Page 015 — GUI preview closeout and sidecar persistence decision 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `5c1b9f7a V3K preview를 session-only dialog로 먼저 분리한다`
연결 문서:
- `docs/plans/2026-05-12_v3k_page_014_preview_launcher_exposure_plan.md`
- `docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md`

---

## 0. 목적

Page 015의 목적은 C2 GUI preview를 어디에서 닫을지 결정하는 것이다. Page 014까지 session-only preview dialog와 visible launcher는 완료되었으므로, 다음에는 다음 셋 중 하나를 선택해야 한다.

1. C2 GUI preview는 session-only로 충분하다고 보고 Phase D formula/analyzer runtime boundary로 이동한다.
2. V3K feature flag 사용성 때문에 sidecar persistence 설계 page를 먼저 연다.
3. 운영 `setting.db` migration은 계속 금지한다.

---

## 1. 판단 기준

| 선택지 | 장점 | 위험/비용 | 현재 기본값 |
| --- | --- | --- | --- |
| C2 closeout → Phase D | runtime 위험을 키우지 않고 다음 V3K 기능 경계로 이동 가능 | preview toggle이 재시작 후 유지되지 않음 | 추천 |
| sidecar persistence design | 사용자가 V3K preview state를 보존 가능 | 파일 위치/ignore/backup/corruption/동기화 정책 필요 | 설계만 가능 |
| operating `setting.db` migration | 기존 설정 저장 흐름과 일관 | schema/rollback/사용자 DB 위험 | 금지 |

---

## 2. Page 015 in-scope

| 항목 | 내용 |
| --- | --- |
| C2 closeout 판단 | session-only preview + launcher가 C2 목표에 충분한지 검토 |
| sidecar 필요성 판단 | 지금 persistence 설계가 필요한지, Phase D 이후로 미룰지 결정 |
| 문서화 | update_log와 registry에 결정 기록 |
| 검증 | 기존 C2 smoke/regression을 재실행해 session-only 상태 유지 확인 |

---

## 3. Out-of-scope

| 항목 | 이유 |
| --- | --- |
| sidecar 파일 실제 생성/write | Page 015는 decision page이며 구현 page가 아니다. |
| 운영 `_database/setting.db` schema/write | 별도 DB migration/cutover/rollback plan 전까지 금지 |
| Kiwoom 주문/청산/live runtime | C2 decision과 무관 |
| formula globals runtime hook | Phase D 전까지 금지 |
| analyzer output trading decision | Phase F/G 전까지 금지 |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외 |

---

## 4. 권장 진행 순서

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 015-1 | C2 목표 대비 현재 구현 점검 | bridge, preview, launcher, smoke가 모두 session-only인지 확인 |
| 015-2 | sidecar persistence 필요성 판단 | 지금 설계할지 Phase D 이후로 미룰지 결정 |
| 015-3 | 다음 phase 선택 | Phase D 또는 sidecar design page 중 하나를 next command로 고정 |
| 015-4 | registry/update_log 정리 | C2 closeout/보류 사유/다음 경계 기록 |
| 015-5 | full regression | C2 smoke + pyd/offline/nonrelease/audit + DB artifact status 통과 |

현재 진행률:

```text
Page 015: [░░░░░░░░░░] 0 / 5 = 0%
```

---

## 5. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 015 Phase C2-7 V3K GUI preview closeout and sidecar persistence decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md를 기준으로 session-only V3K preview가 충분한지, 다음에 sidecar persistence 설계를 시작할지, 아니면 GUI는 session-only로 닫고 Phase D formula/analyzer runtime boundary로 넘어갈지 재판단한다. 운영 _database/setting.db schema/write, sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 다음 page 계획을 추가한 뒤 py_compile, smoke_v3k_gui_settings_preview, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```
