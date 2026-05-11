# 2026-05-11 V3K Page 011 종료 및 Phase C2 GUI wrapper inventory 선택 기록

## 1. 작업 목적

이번 작업의 목적은 Phase C1 완료 이후 다음 활성화 경계를 재선택하고, **실제 MainWindow/pyd-free wrapper를 변경하기 전** C2 inventory/plan을 남기는 것이다.

전체 목적은 계속 동일하다.

```text
2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성을 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능을 단계적으로 안전 반영한다.
```

## 2. 실행 경로

먼저 직전 추천 명령인 `omx ralph`를 실행했으나, 현재 Codex 비대화형 환경에서는 다음 오류로 중단되었다.

```text
Error: stdin is not a terminal
```

따라서 같은 목표를 현재 세션에서 직접 이어서 수행했다. `omx explore`도 Windows POSIX allowlist runtime 제한으로 실패했으므로, 이후 repository 조사는 PowerShell/Python read-only 명령으로 대체했다.

## 3. 조사한 경계

| 경계 | 조사 결과 | 판단 |
| --- | --- | --- |
| `ui/set_setup_tap.py` | 설정 탭 버튼과 `SettingLoad_*`/`SettingSave_*` button wiring이 존재한다. | 실제 widget 추가는 layout/pyd-free wrapper 위험이 있어 다음 단계에서 바로 하지 않는다. |
| `ui/ui_mainwindow.py` | `SettingLoad_*`, `SettingSave_*`, `SettingAll*` wrapper와 legacy `sjButtonClicked_*` alias가 존재한다. | C2 최초 구현은 MainWindow mutation 전 no-GUI wrapper smoke로 시작한다. |
| `ui/ui_button_clicked_settings.py` | `setting_all_app()`는 DB 복사 후 load/save 연쇄 호출, `setting_save_08()`은 `etc` table write, `setting_save_01()`은 Kiwoom/future manager 재구동 경계를 포함한다. | V3K flag persistent save나 manager 경계 연결은 보류한다. |
| `utility/setting.py` | import-time `setting.db` read와 global `DICT_SET` 구성 경계다. | 운영 DB loader 직접 변경 금지. |
| `utility/setting_user.py` | runtime `load_settings()`도 `setting.db`를 읽어 dict를 반환한다. | C2 최초 구현에서 직접 변경 금지. |
| `strategy/v3k_settings_surface.py` | Phase C1 bridge가 default-OFF dict-like contract를 제공한다. | C2의 유일한 안전 입력 contract로 삼는다. |

## 4. 결정

다음 활성화 경계는 **Phase C2 GUI wrapper inventory/plan**으로 확정한다.

다만 Phase C2를 “즉시 실제 GUI checkbox 추가”로 해석하지 않는다. 안전한 실행 순서는 다음과 같다.

1. C2-0: GUI wrapper inventory/plan 문서화 — 이번 작업 완료.
2. C2-1: no-GUI wrapper adapter smoke — 다음 추천 단계.
3. C2-2: MainWindow in-memory helper 검토 — C2-1 통과 후.
4. C2-3: 실제 GUI checkbox/layout 노출 — pyd-free GUI smoke 준비 후.
5. C2-4: persistent setting DB 저장 — 별도 DB/schema migration plan 전까지 보류.

## 5. 왜 다른 후보를 선택하지 않았는가

| 후보 | 보류 이유 |
| --- | --- |
| Phase D formula/global runtime hook | `globals().update` 또는 strategy formula runtime에 닿으면 이름 충돌과 평가 side effect가 생길 수 있다. |
| Phase E live Kiwoom dry-run preload diagnostic | live event loop, receiver/trader coupling, latency 검증이 필요하다. |
| Phase F/G analyzer output trading decision | 매수·매도·청산 판단을 직접 바꿀 수 있는 최고위험 단계다. |
| 운영 DB cutover/persistent setting DB | 사용자 설정 DB schema와 파일 복사/삭제 경계를 바꾸므로 별도 rollback/cutover plan이 필요하다. |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외 대상이다. |

## 6. 진행률 정리

| 페이지 | 의미 | 상태 |
| --- | --- | --- |
| Page 009 | Phase A shadow DB rehearsal | 완료 |
| Page 010 | Phase B read-only learning DB verification | 완료 |
| Page 011 | Phase C-G 활성화 경계 선택 및 C1 완료 후 재선택 | 완료 |
| Page 012 | Phase C2 GUI wrapper inventory/plan 및 후속 C2 구현 준비 | 시작 |

```text
Page 011: [██████████] 5 / 5 steps = 100%
초기 11페이지 전체: [███████████] 11 / 11 pages = 100%
Page 012: [██░░░░░░░░] 1 / 5 steps = 20%
```

## 7. 이번 작업에서 변경하지 않은 것

- 운영 `_database/` 및 `setting.db`
- `_database_v3k_shadow/` row/data
- Kiwoom receiver/trader/order/exit/live runtime
- formula globals runtime hook
- analyzer output의 trading decision 반영
- V2/V3/3U 공식/pyd-free lane
- LS Securities 직접 import/dependency

## 8. 다음 작업 지침

다음 작업은 C2-1 no-GUI wrapper adapter smoke다. 이 단계는 실제 PyQt widget이나 DB write 없이, Phase C1 bridge 결과를 MainWindow-like object가 안전하게 보유할 수 있는지를 검증해야 한다.

권장 명령은 다음과 같다.

```powershell
omx ralph "force: V3K Page 012 Phase C2-1 no-GUI GUI-wrapper adapter smoke를 구현한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md를 기준으로 실제 PyQt widget, 운영 _database/setting.db schema/write, _database_v3k_shadow row, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. Phase C1의 bridge_v3k_settings_into_dict_set을 재사용하여 Fake/MainWindow-like object가 V3K settings와 feature_flags를 default-OFF로 안전 보유하는 no-GUI helper와 smoke를 추가한다. 완료 시 py_compile, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, Phase B read-only smoke, 기존 V3K smoke suite, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync를 통과시키고 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록 후 한국어 Lore commit한다."
```
