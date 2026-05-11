# 2026-05-12 V3K Phase C2-1 no-GUI GUI-wrapper adapter smoke 구현 기록

## 1. 목적

이번 작업의 목적은 Page 012 Phase C2-1을 완료하는 것이다. Phase C1에서 만든 `bridge_v3k_settings_into_dict_set()`를 실제 MainWindow/pyd-free wrapper에 바로 연결하지 않고, 먼저 **Fake/MainWindow-like object가 V3K settings와 feature_flags를 default-OFF로 안전하게 보유할 수 있는지** no-GUI helper와 smoke로 증명했다.

전체 목적은 계속 동일하다.

```text
2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성을 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. 실행 경로

직전 추천 명령인 `omx ralph`를 먼저 실행했지만 현재 비대화형 Codex 환경에서는 다음 오류로 중단되었다.

```text
Error: stdin is not a terminal
```

따라서 같은 목표를 현재 세션에서 직접 이어서 수행했다.

## 3. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `ui/ui_v3k_settings_bridge.py` | no-GUI/no-DB `attach_v3k_gui_settings_bridge()` helper 추가 |
| `scripts/smoke_v3k_gui_wrapper_bridge.py` | FakeMainWindow 기반 C2-1 smoke 신규 추가 |
| `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md` | Page 012 진행률과 다음 C2-2 명령 갱신 |
| `docs/update_log/2026-05-12_v3k_phase_c2_1_gui_wrapper_bridge.md` | 본 구현 기록 |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-C2-1` carry-forward 기록 추가 |

## 4. Helper contract

`attach_v3k_gui_settings_bridge()`의 contract는 다음과 같다.

1. `strategy.v3k_settings_surface.bridge_v3k_settings_into_dict_set()`를 재사용한다.
2. PyQt, QApplication, sqlite3, `DB_PATH`, `DB_SETTING`, `globals().update`, subprocess runtime을 import하거나 호출하지 않는다.
3. `ui_like.dict_set`이 있으면 읽기 입력으로만 사용한다.
4. 기본값에서는 기존 `dict_set` 객체를 교체하지 않는다.
5. `replace_dict_set=True`가 명시된 경우에만 normalized V3K key가 포함된 **복사본**을 `ui_like.dict_set`에 in-memory로 재할당한다.
6. source dict는 mutate하지 않는다.
7. 다음 attribute를 MainWindow-like object에 부착한다.

| Attribute | 의미 |
| --- | --- |
| `v3k_settings_surface_version` | settings surface contract version |
| `v3k_settings` | normalized V3K setting dict |
| `v3k_feature_flags` | runtime adapter가 읽을 수 있는 normalized feature flag dict |
| `v3k_settings_diagnostics` | unknown key 등 진단 메시지 tuple |
| `v3k_settings_bridge_dict_set` | legacy key를 보존하고 V3K key를 default-OFF로 보강한 copy |

## 5. Smoke 검증 항목

`scripts/smoke_v3k_gui_wrapper_bridge.py`는 다음을 검증한다.

| 검증 | 결과 |
| --- | --- |
| helper dependency boundary | PyQt/sqlite3/DB/globals/subprocess marker 없음 |
| default-OFF attrs | FakeMainWindow에 V3K settings/feature_flags가 모두 default-OFF로 부착됨 |
| dict_set replacement 기본값 | 기본 호출은 기존 `dict_set` 객체를 교체하지 않음 |
| source mutation | source dict가 mutate되지 않음 |
| explicit in-memory replacement | `replace_dict_set=True`일 때만 copy로 교체됨 |
| raw override | 명시 raw_settings가 source보다 우선함 |
| diagnostics | unknown V3K key가 diagnostic으로 전달됨 |
| missing dict_set object | `dict_set`이 없는 object도 지원하며 새 dict_set을 만들지 않음 |
| artifact guard | `_database`, `_database_v3k_shadow`, `_log`, `*.db`, `backtest/graph` 상태 불변 |

대표 출력:

```text
v3k GUI wrapper bridge dependency boundary ok
v3k GUI wrapper bridge default-OFF attrs ok
v3k GUI wrapper bridge explicit in-memory dict replacement ok
v3k GUI wrapper bridge override diagnostics ok
v3k GUI wrapper bridge missing-dict_set object ok
v3k GUI wrapper bridge smoke passed
```

## 6. 의도적으로 변경하지 않은 것

| 항목 | 이유 |
| --- | --- |
| `ui/ui_mainwindow.py` 실제 연결 | C2-2에서 별도 in-memory helper integration으로 다룬다. |
| `ui/set_setup_tap.py` 실제 checkbox/widget | layout과 pyd-free wrapper smoke가 필요하므로 C2-3 이후로 보류한다. |
| `ui/ui_button_clicked_settings.py` persistent save | 운영 `setting.db` write/schema 경계라 C2-4 또는 별도 DB plan 전까지 보류한다. |
| `utility/setting.py`, `utility/setting_user.py` | import-time/runtime setting DB loader 변경은 운영 DB 영향이 있으므로 보류한다. |
| Kiwoom receiver/trader/order/exit/live runtime | 이번 단계는 GUI-wrapper state smoke일 뿐 live runtime hook이 아니다. |
| formula globals runtime hook | Phase D 전까지 금지한다. |
| analyzer output trading decision | Phase F/G 전까지 금지한다. |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외한다. |

## 7. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py strategy/v3k_settings_surface.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py
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
Page 012: [████░░░░░░] 2 / 5 = 40%
```

Page 012에서 완료된 항목:

1. C2 wrapper inventory/plan
2. C2-1 no-GUI wrapper adapter smoke

남은 항목:

1. C2-2 MainWindow in-memory helper integration 검토/구현
2. C2-3 GUI checkbox/layout 검토
3. C2 persistent 설정 저장 여부 재판단

## 9. 다음 작업 지침

다음 단계는 **C2-2 MainWindow in-memory helper integration**이다. 이 단계에서도 아직 실제 GUI checkbox, persistent setting DB write, Kiwoom live runtime hook은 금지한다. 목표는 `MainWindow.__init__` 같은 실제 wrapper 경계에서 C2-1 helper를 default-OFF로 보유할 수 있는지 최소 변경으로 검증하는 것이다.
