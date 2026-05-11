# 2026-05-12 V3K Phase C2-5 session-only UI preview skeleton 기록

## 1. 목적

Page 013 / C2-5의 목적은 C2-4에서 선택한 저장 정책에 따라 **persistent 저장 없이 session-only V3K UI preview skeleton**을 실제 코드 경계로 추가하는 것이다.

전체 목표는 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 안전한 단계로 반영한다.
```

## 2. 선택한 UI 경계

| 선택지 | 판단 |
| --- | --- |
| 기존 설정 groupBox에 checkbox 삽입 | 제외. 기존 layout/저장 흐름과 결합도가 높다. |
| 기존 main menu에 즉시 버튼 추가 | 보류. 화면 배치와 단축키 충돌 검토가 필요하다. |
| 별도 V3K dialog skeleton | **선택**. 기존 설정 layout을 건드리지 않고 session-only 상태를 표시/토글할 수 있다. |

이번 단계에서는 별도 dialog skeleton을 만들되, **visible launcher 버튼은 추가하지 않았다**. 대신 MainWindow에 `ShowV3KSettingsPreview` lazy opener method를 붙여 다음 단계에서 안전한 노출 위치를 결정할 수 있게 했다.

## 3. 구현 내용

| 파일 | 내용 |
| --- | --- |
| `ui/ui_v3k_settings_preview.py` | V3K settings preview helper 추가. MainWindow-like 객체에 lazy dialog opener를 붙이고, dialog 내부 checkbox 토글은 `v3k_settings`/`v3k_feature_flags` in-memory attribute만 갱신한다. |
| `ui/ui_mainwindow.py` | `attach_v3k_settings_preview(self)`를 C2-2 bridge 직후, `WidgetCreater(self)` 전 위치에 연결했다. |
| `scripts/smoke_v3k_gui_settings_preview.py` | no-GUI smoke 추가. persistence marker 부재, lazy opener, default-OFF model, in-memory toggle/reset, MainWindow 연결 순서를 검증한다. |
| `docs/plans/2026-05-12_v3k_page_013_session_only_ui_preview_plan.md` | Page 013 완료 상태와 다음 경계를 기록했다. |
| `docs/CARRY_FORWARD_REGISTRY.md` | C2-5 carry-forward record를 추가했다. |

## 4. session-only 보장

이번 단계에서 의도적으로 하지 않은 것:

- 운영 `_database/setting.db` schema/write
- sidecar 설정 파일/DB write
- `_database_v3k_shadow` row/data 변경
- Main menu 또는 기존 설정 tab layout에 visible launcher 추가
- Kiwoom 주문/청산/live runtime 변경
- formula globals runtime hook
- analyzer output trading decision 연결
- LS Securities 직접 의존성 추가

session-only 상태는 다음 attribute에만 보유된다.

```text
MainWindow.v3k_settings
MainWindow.v3k_feature_flags
MainWindow.v3k_settings_diagnostics
MainWindow.v3k_settings_preview_result
MainWindow.ShowV3KSettingsPreview
```

## 5. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile ui/ui_v3k_settings_preview.py ui/ui_mainwindow.py scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

추가 commit 전에는 기존 C2 검증 세트도 다시 실행한다.

## 6. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [██████████] 5 / 5 = 100%
Page 013: [██████████] 5 / 5 = 100%
```

Page 013 완료 항목:

1. V3K UI preview 위치 결정: 별도 dialog skeleton 선택
2. session-only UI skeleton 구현: lazy dialog opener + checkbox state model
3. no-GUI source-level smoke 추가
4. GUI/pyd-free 기존 smoke와 함께 재검증
5. C2 저장소 후속 판단: persistence는 계속 보류, 다음은 visible launcher 노출 판단

## 7. 다음 작업 지침

다음 단계는 **Page 014 / C2-6 session-only V3K preview launcher exposure**다.

다음 단계에서 해야 할 일:

1. `ShowV3KSettingsPreview`를 어디에 노출할지 결정한다.
2. 기존 main menu button geometry, shortcut, tooltip 충돌을 검토한다.
3. 가능하면 가장 작은 visible launcher를 추가한다.
4. 그래도 persistence는 추가하지 않는다.
5. sidecar/settings DB migration은 별도 page 전까지 계속 금지한다.

추천 명령:

```powershell
omx ralph "force: V3K Page 014 Phase C2-6 session-only V3K preview launcher exposure를 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_014_preview_launcher_exposure_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_5_session_only_ui_preview.md를 기준으로 MainWindow에 붙은 ShowV3KSettingsPreview lazy opener를 사용자에게 노출할 가장 작은 안전 경계를 검토한다. 기존 main menu geometry/shortcut/layout 충돌을 먼저 확인하고, 가능하면 session-only V3K preview dialog를 여는 visible launcher 또는 명시적 manual entry를 구현한다. 운영 _database/setting.db schema/write, sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 완료 시 py_compile, smoke_v3k_gui_settings_preview, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
