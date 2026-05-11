# 2026-05-12 V3K Phase C2-6 preview launcher exposure 기록

## 1. 목적

Page 014 / C2-6의 목적은 Page 013에서 MainWindow에 붙인 `ShowV3KSettingsPreview` lazy opener를 사용자가 찾을 수 있는 최소 UI 경계로 노출하는 것이다.

전체 목적은 계속 동일하다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. 실행 경로

추천 명령인 `omx ralph`를 먼저 실행했지만 현재 비대화형 Codex 환경에서는 다음 오류로 중단되었다.

```text
Error: stdin is not a terminal
```

또한 `omx explore`는 Windows allowlist runtime이 POSIX shell wrapper에 의존한다는 오류로 실패했다. 따라서 `omx ralph`의 동일 목표를 현재 세션에서 직접 이어서 수행하고, read-only 조사는 PowerShell과 기존 파일 검토로 대체했다.

## 3. geometry / shortcut 검토

기존 `ui/set_main_menu.py`의 left menu button 구조를 기준으로 검토했다.

| 영역 | 기존 배치 | 판단 |
| --- | --- | --- |
| main tab buttons | `pushButton_00` ~ `pushButton_07`, `y=5..285`, `Ctrl+1..8` | 변경하지 않음 |
| Alt block | `Alt`, `T/L`, `D/Z`, `K/C`, `H/G`, `U/Q`, `B` | `B` 오른쪽 `(23, 450, 16, 15)`가 비어 있음 |
| Shift block | `Shift`, `S/Q`, `O/E` | 변경하지 않음 |
| Ctrl block | `Ctrl`, `B/A` | 변경하지 않음 |
| progress bar | `y=570..757` | 변경하지 않음 |

선택한 노출:

```text
button: v3_pushButton
label: V
shortcut: Alt+V
geometry: (23, 450, 16, 15)
action: ShowV3KSettingsPreview()
```

`Alt+V`는 기존 shortcut 목록에 없으며, `(23, 450)`은 기존 `bs_pushButton`의 오른쪽 빈 칸이므로 기존 버튼과 겹치지 않는다.

## 4. 구현 내용

| 파일 | 내용 |
| --- | --- |
| `ui/set_main_menu.py` | `v3_pushButton`을 추가하고 `Alt+V`로 `ShowV3KSettingsPreview()`를 호출하게 했다. |
| `scripts/smoke_v3k_gui_settings_preview.py` | launcher marker, `Alt+V` shortcut assignment, geometry, persistence write 부재를 source-level로 검증한다. |
| `docs/plans/2026-05-12_v3k_page_014_preview_launcher_exposure_plan.md` | Page 014 완료 상태와 다음 Page 015 판단 경계를 기록했다. |
| `docs/CARRY_FORWARD_REGISTRY.md` | C2-6 carry-forward record를 추가했다. |

## 5. 변경하지 않은 것

- 운영 `_database/setting.db` schema/write
- sidecar 설정 파일/DB write
- `_database_v3k_shadow` row/data 변경
- 기존 설정 groupBox checkbox 삽입
- Kiwoom 주문/청산/live runtime
- formula globals runtime hook
- analyzer output trading decision
- LS Securities 직접 의존성

## 6. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile ui/set_main_menu.py ui/ui_v3k_settings_preview.py ui/ui_mainwindow.py scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_settings_preview.py
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py ui/ui_v3k_settings_preview.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py scripts/smoke_v3k_gui_settings_preview.py scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_offline_gui.py --branch STOM_Version_2U_C --version V2.79 --offline --log-dir .omx/logs/v3k-c2-6
python scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U_C --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v3k-c2-6/verify_pyd_gui_contract.json --log-dir .omx/logs/v3k-c2-6
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

검증 메모:

- `smoke_offline_gui.py`는 기존과 같이 Python 3.13/PyQt font warning과 offline guard의 `KHOPENAPI` no-candidate 로그를 출력하지만 최종 결과는 `[OK] offline GUI smoke passed`다.
- DB artifact status 출력은 비어 있었으므로 운영 DB/shadow DB 변경은 없다.

## 7. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [██████████] 5 / 5 = 100%
Page 013: [██████████] 5 / 5 = 100%
Page 014: [██████████] 5 / 5 = 100%
Page 015: [░░░░░░░░░░] 0 / 5 = 0%
```

Page 014 완료 항목:

1. main menu/shortcut geometry inventory
2. exposure 방식 결정: visible launcher
3. 최소 구현: `v3_pushButton`, `Alt+V`, `ShowV3KSettingsPreview()`
4. no-GUI smoke 보강
5. full C2 regression

## 8. 다음 작업 지침

다음 단계는 **Page 015 / C2-7 V3K GUI preview closeout and sidecar persistence decision**이다.

다음 단계에서는 다음 중 하나를 결정해야 한다.

1. GUI preview는 session-only로 충분하므로 C2를 닫고 Phase D formula/analyzer runtime boundary로 이동한다.
2. 사용성 때문에 sidecar persistence 설계가 먼저 필요하다고 보고 sidecar 설계 page를 연다.
3. 운영 `setting.db` migration은 계속 금지한다.

추천 명령:

```powershell
omx ralph "force: V3K Page 015 Phase C2-7 V3K GUI preview closeout and sidecar persistence decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md를 기준으로 session-only V3K preview가 충분한지, 다음에 sidecar persistence 설계를 시작할지, 아니면 GUI는 session-only로 닫고 Phase D formula/analyzer runtime boundary로 넘어갈지 재판단한다. 운영 _database/setting.db schema/write, sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 다음 page 계획을 추가한 뒤 py_compile, smoke_v3k_gui_settings_preview, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```
