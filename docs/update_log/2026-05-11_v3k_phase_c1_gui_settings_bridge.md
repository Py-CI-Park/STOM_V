# 2026-05-11 V3K Phase C1 GUI/settings default-OFF bridge 구현 기록

## 1. 목적

Phase C1의 목적은 V3K 기능을 실제 GUI/runtime에 바로 연결하지 않고, 기존 설정 dict 경계에서 V3K flag를 **default-OFF로 안전하게 인식**할 수 있는 no-GUI bridge를 마련하는 것이다.

전체 목적은 계속 다음과 같다.

```text
2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성을 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. Inventory 결과

| 경계 | 파일/근거 | 이번 phase 판단 |
| --- | --- | --- |
| 설정 DB 로드 | `utility/setting.py::database_load()`, `DICT_SET` 구성 | 직접 변경하지 않음. 운영 `_database/setting.db`와 import-time DB load에 닿지 않기 위해 no-GUI bridge로 분리. |
| 사용자 설정 loader | `utility/setting_user.py::load_settings()` | 직접 변경하지 않음. Phase C1에서는 dict-like 입력만 bridge. |
| 설정 GUI 버튼 | `ui/set_setup_tap.py`의 `SettingLoad_*`, `SettingSave_*` 연결 | 직접 변경하지 않음. pyd-free wrapper/GUI 영향은 후속 세부 phase로 보류. |
| MainWindow 설정 wrapper | `ui/ui_mainwindow.py`, `ui/ui_button_clicked_settings.py` | 직접 변경하지 않음. 이번 phase는 wrapper 변경 없이 contract를 먼저 고정. |
| V3K 설정 surface | `strategy/v3k_settings_surface.py` | 변경. 기존 설정 dict와 V3K flag를 default-OFF로 병합하는 bridge 추가. |
| no-GUI smoke | `scripts/smoke_v3k_gui_settings_bridge.py` | 신규. QApplication/DB 없이 dict_set bridge를 검증. |

## 3. 변경 내용

| 파일 | 변경 |
| --- | --- |
| `strategy/v3k_settings_surface.py` | `V3KSettingsBridgeResult`, `extract_v3k_settings_from_dict_set()`, `bridge_v3k_settings_into_dict_set()` 추가 |
| `scripts/smoke_v3k_gui_settings_bridge.py` | no-GUI settings bridge smoke 신규 추가 |
| `docs/update_log/2026-05-11_v3k_phase_c1_gui_settings_bridge.md` | 본 구현 기록 |
| `docs/CARRY_FORWARD_REGISTRY.md` | `V3K-PHASE-C1` 기록 추가 |
| `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md` | Page 011 진행률을 Phase C1 완료 상태로 갱신 |

## 4. Bridge 계약

`bridge_v3k_settings_into_dict_set()`의 계약은 다음과 같다.

1. 입력 `dict_set`을 직접 mutate하지 않는다.
2. 기존 legacy 설정 key를 보존한다.
3. V3K setting contract key가 없으면 모두 `False`로 삽입한다.
4. 기존 dict_set에 V3K key가 있으면 bool로 정규화한다.
5. 명시적 `raw_settings` override가 있으면 그것을 우선한다.
6. unknown V3K setting은 diagnostic으로 남기고 무시한다.
7. 반환 결과에는 `settings`, `feature_flags`, 병합된 `dict_set`이 포함된다.

## 5. Smoke 검증 항목

`smoke_v3k_gui_settings_bridge.py`는 다음을 검증한다.

| 검증 | 결과 |
| --- | --- |
| empty dict_set | 모든 V3K key가 default-OFF로 삽입 |
| source mutation | 원본 dict_set 변경 없음 |
| legacy key | 보존됨 |
| 기존 V3K key | bool로 정규화 |
| explicit override | raw_settings가 우선 |
| unknown flag | diagnostic 기록 후 무시 |
| formula facade 연결 | 명시적으로 formula flags가 켜진 경우에만 `V3K_` prefixed globals 생성 |
| runtime artifact | `_database`, `_database_v3k_shadow`, `_log`, `*.db` 상태 변화 없음 |

## 6. 의도적으로 변경하지 않은 항목

| 항목 | 보류 이유 |
| --- | --- |
| `utility/setting.py` 직접 변경 | import-time DB load와 운영 `_database/setting.db` 경계에 닿으므로 no-GUI bridge 검증 뒤 별도 판단 필요 |
| `ui/set_setup_tap.py` GUI 요소 추가 | 실제 UI layout/pyd-free wrapper 영향 가능성이 있어 별도 GUI smoke 필요 |
| `ui/ui_button_clicked_settings.py` 저장/로드 로직 변경 | 설정 DB write 경계이므로 default-OFF bridge contract가 먼저 필요 |
| formula `globals().update` runtime 연결 | Phase D 후보이며 이름 충돌/전략식 side effect 위험 |
| live Kiwoom preload diagnostic | Phase E 후보이며 event loop/latency 위험 |
| analyzer output trading decision | Phase F/G 후보이며 실제 매수·매도·청산 판단 변경 위험 |
| LS증권 API import | V3K 정의 위반 |

## 7. 검증 결과

아래 검증 세트가 통과했다.

```powershell
python -m py_compile strategy/v3k_settings_surface.py scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_learning_db_readonly_existing.py
python scripts/smoke_v3k_learning_loader.py
python scripts/smoke_v3k_backtest_learning_hook.py
python scripts/smoke_v3k_realtime_learning_boundary.py
python scripts/smoke_v3k_formula_facade.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git status --short -- _database/ _database_v3k_shadow/ *.db
```

핵심 smoke 출력:

```text
v3k GUI/settings bridge default-OFF insertion ok
v3k GUI/settings bridge preserves legacy keys and normalizes V3K keys
v3k GUI/settings explicit override bridge ok
v3k GUI/settings extraction filter ok
v3k GUI/settings bridge smoke passed
```

## 8. 완료 판정

Phase C1은 “GUI/settings default-OFF bridge”의 no-GUI contract 단계로 완료한다.

| 완료 기준 | 판정 |
| --- | --- |
| 설정 저장/로드 및 wrapper inventory | 완료 |
| default-OFF dict_set bridge | 완료 |
| no-GUI smoke | 완료 |
| 운영 DB 무변경 | 완료 |
| Kiwoom live/order runtime 무변경 | 완료 |
| formula runtime hook 미연결 | 완료 |
| analyzer trading decision 미반영 | 완료 |
| LS 직접 의존성 없음 | 완료 |
| 문서/registry 기록 | 완료 |

## 9. 다음 작업

Page 011의 남은 작업은 “다음 활성화 경계 재선택”이다. Phase C1 후속으로 가능한 선택지는 다음이다.

1. Phase C2: 실제 GUI wrapper에 V3K settings 표시/저장 경계를 최소 연결한다.
2. Phase D: formula/global runtime hook 계획을 작성한다.
3. Phase E: live Kiwoom dry-run preload diagnostic 계획을 작성한다.
4. Phase F/G: analyzer output 전략 반영/cutover는 아직 고위험으로 보류한다.

가장 안전한 다음 추천은 **Phase C2 GUI wrapper inventory/계획**이다. 아직 runtime 연결이 아니라 wrapper 영향 분석과 no-op GUI smoke를 먼저 설계하는 단계가 안전하다.