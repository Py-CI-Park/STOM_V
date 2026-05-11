# 2026-05-12 V3K Phase C2-2 MainWindow in-memory bridge 구현 기록

## 1. 목적

이번 작업의 목적은 Page 012 Phase C2-2를 완료하는 것이다. C2-1에서 증명한 no-GUI wrapper helper를 실제 `MainWindow` 초기화 경계에 **default-OFF in-memory state**로 최소 연결했다.

전체 목적은 계속 동일하다.

```text
2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성을 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. 실행 경로

추천 명령인 `omx ralph`를 먼저 실행했지만 현재 비대화형 Codex 환경에서는 다음 오류로 중단되었다.

```text
Error: stdin is not a terminal
```

따라서 같은 목표를 현재 세션에서 직접 이어서 수행했다.

## 3. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `ui/ui_mainwindow.py` | `attach_v3k_gui_settings_bridge` import 및 `self.dict_set = dict_set` 직후 `self.v3k_settings_bridge_result = attach_v3k_gui_settings_bridge(self)` 호출 추가 |
| `ui/ui_v3k_settings_bridge.py` | helper가 `v3k_settings_bridge_result` attr도 부착하도록 보강 |
| `scripts/smoke_v3k_gui_wrapper_bridge.py` | MainWindow source-level integration boundary smoke 추가 |
| `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md` | Page 012 진행률과 다음 C2-3 명령 갱신 |
| `docs/update_log/2026-05-12_v3k_phase_c2_2_mainwindow_in_memory_bridge.md` | 본 구현 기록 |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-C2-2` carry-forward 기록 추가 |

## 4. MainWindow integration contract

이번 연결은 다음 contract를 지킨다.

1. `self.dict_set = dict_set` 이후, `WidgetCreater(self)`와 실제 widget 생성 전에 V3K bridge state를 부착한다.
2. `replace_dict_set=True`를 사용하지 않는다.
3. 기존 `dict_set` 객체를 교체하거나 mutate하지 않는다.
4. `MainWindow`는 in-memory attribute만 갖는다.
5. PyQt checkbox/widget, settings DB schema/write, shadow DB row, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer trading decision은 변경하지 않는다.

부착되는 주요 attribute:

| Attribute | 의미 |
| --- | --- |
| `v3k_settings_bridge_result` | C2 helper가 반환한 bridge result |
| `v3k_settings_surface_version` | settings surface version |
| `v3k_settings` | normalized V3K settings |
| `v3k_feature_flags` | normalized V3K feature flags |
| `v3k_settings_diagnostics` | unknown key 등 diagnostic |
| `v3k_settings_bridge_dict_set` | legacy key 보존 + V3K key default-OFF 보강 copy |

## 5. Smoke 보강

`scripts/smoke_v3k_gui_wrapper_bridge.py`에 source-level MainWindow integration check를 추가했다.

검증 내용:

| 검증 | 내용 |
| --- | --- |
| import marker | `ui/ui_mainwindow.py`가 `attach_v3k_gui_settings_bridge`를 import하는지 확인 |
| call marker | `self.v3k_settings_bridge_result = attach_v3k_gui_settings_bridge(self)` 호출 확인 |
| order | `self.dict_set = dict_set` 이후, `WidgetCreater(self)` 이전 호출인지 확인 |
| no dict replacement | MainWindow integration에 `replace_dict_set=True`가 없는지 확인 |
| previous C2-1 contract | default-OFF, mutation 없음, explicit replacement, diagnostics, missing dict_set, artifact 불변성 유지 |

대표 출력:

```text
v3k MainWindow in-memory bridge integration boundary ok
v3k GUI wrapper bridge smoke passed
```

## 6. 의도적으로 변경하지 않은 것

| 항목 | 이유 |
| --- | --- |
| 실제 GUI checkbox/widget | C2-3에서 layout/pyd-free wrapper 영향 검토 후 진행해야 한다. |
| `setting.db` persistent 저장 | 운영 설정 DB schema/write 변경은 별도 cutover/rollback plan 전까지 보류한다. |
| `SettingLoad_*`/`SettingSave_*` 저장 흐름 | 설정 DB write와 프로세스 재구동 경계가 있어 이번 단계 범위 밖이다. |
| Kiwoom receiver/trader/order/exit/live runtime | 이번 단계는 MainWindow in-memory state 보유만 검증한다. |
| formula globals runtime hook | Phase D 전까지 금지한다. |
| analyzer output trading decision | Phase F/G 전까지 금지한다. |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외한다. |

## 7. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_v3k_analyzer_adapter.py
python scripts/smoke_v3k_analyzer_modules.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

## 8. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [██████░░░░] 3 / 5 = 60%
```

Page 012에서 완료된 항목:

1. C2 wrapper inventory/plan
2. C2-1 no-GUI wrapper adapter smoke
3. C2-2 MainWindow in-memory helper integration

남은 항목:

1. C2-3 GUI checkbox/layout feasibility 검토
2. C2 persistent 설정 저장 여부 재판단

## 9. 다음 작업 지침

다음 단계는 **C2-3 GUI checkbox/layout feasibility 검토**다. 아직 실제 widget을 바로 추가하지 말고, `set_setup_tap.py`, `ui_button_clicked_settings.py`, MainWindow alias, pyd-free GUI contract, 설정 DB 저장 필요성을 먼저 검토해야 한다. 실제 checkbox 추가는 검토 문서와 no-GUI/layout smoke 조건이 명확할 때만 진행한다.
