# V3K Page 014 — session-only preview launcher exposure 계획

작성일: 2026-05-12 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `58295b01 V3K UI 저장 정책을 session-only로 먼저 고정한다`
연결 문서:
- `docs/update_log/2026-05-12_v3k_phase_c2_5_session_only_ui_preview.md`
- `docs/plans/2026-05-12_v3k_page_013_session_only_ui_preview_plan.md`

---

## 0. 목적

Page 014의 목적은 Page 013에서 MainWindow에 붙인 `ShowV3KSettingsPreview` lazy opener를 사용자에게 노출할지, 노출한다면 어디에 어떻게 노출할지 결정하는 것이다.

전체 V3K 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

---

## 1. Page 014 in-scope

| 항목 | 내용 |
| --- | --- |
| 노출 위치 검토 | main menu button geometry, shortcut, tooltip, 기존 click handler 충돌 확인 |
| 구현 후보 | visible launcher button, shortcut-only launcher, 또는 명시적 manual entry 유지 |
| 저장 정책 | 계속 session-only. preview toggle은 in-memory attribute만 갱신 |
| smoke | source-level launcher 위치/호출 경계, persistence write 부재, default-OFF 유지 검증 |

---

## 2. Out-of-scope

| 항목 | 이유 |
| --- | --- |
| 운영 `_database/setting.db` schema/write | C2-4에서 보류한 고위험 경계 |
| sidecar 설정 파일/DB write | 별도 저장소 정책 page 전까지 보류 |
| 기존 설정 groupBox에 직접 checkbox 삽입 | C2-3에서 위험으로 판정 |
| Kiwoom 주문/청산/live runtime | UI preview 노출과 무관 |
| formula globals runtime hook | Phase D 전까지 금지 |
| analyzer output trading decision | Phase F/G 전까지 금지 |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외 |

---

## 3. 권장 진행 순서

| Step | 작업 | 완료 조건 |
| ---: | --- | --- |
| 014-1 | main menu/shortcut geometry inventory | 새 launcher 후보가 기존 버튼/단축키와 충돌하는지 기록 |
| 014-2 | exposure 방식 결정 | visible button, shortcut-only, manual entry 중 하나를 선택 |
| 014-3 | 최소 구현 | 선택한 방식으로 `ShowV3KSettingsPreview` 호출 경계를 연결 |
| 014-4 | no-GUI smoke 보강 | launcher source marker, persistence 부재, default-OFF 유지 확인 |
| 014-5 | full C2 regression | pyd/offline/nonrelease/audit 검증 후 다음 page 결정 |

2026-05-12 C2-6 구현 결과:

| Step | 결과 |
| ---: | --- |
| 014-1 | `ui/set_main_menu.py`의 기존 left menu geometry를 확인했다. `Alt` block의 `(23, 450, 16, 15)` 위치가 비어 있어 기존 button과 겹치지 않는 후보로 선택했다. |
| 014-2 | visible launcher button을 선택했다. shortcut-only/manual entry는 사용자 발견성이 낮아 제외했다. |
| 014-3 | `v3_pushButton`을 추가하고 `Alt+V` shortcut으로 `ShowV3KSettingsPreview()`를 호출하게 했다. |
| 014-4 | `scripts/smoke_v3k_gui_settings_preview.py`에 launcher source marker, geometry, shortcut, persistence 부재 검증을 추가했다. |
| 014-5 | full C2 regression 통과 후 Page 015로 넘긴다. |

현재 진행률:

```text
Page 014: [██████████] 5 / 5 = 100%
```

---

## 4. 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 015 Phase C2-7 V3K GUI preview closeout and sidecar persistence decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md를 기준으로 session-only V3K preview가 충분한지, 다음에 sidecar persistence 설계를 시작할지, 아니면 GUI는 session-only로 닫고 Phase D formula/analyzer runtime boundary로 넘어갈지 재판단한다. 운영 _database/setting.db schema/write, sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 다음 page 계획을 추가한 뒤 py_compile, smoke_v3k_gui_settings_preview, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```
