# V3K Page 012 — Phase C2 GUI wrapper inventory/plan

작성일: 2026-05-11 KST
대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
기준 commit: `88335424 V3K Phase C1에서 설정 bridge를 default-OFF로 고정한다`
연결 문서:
- `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md`
- `docs/update_log/2026-05-11_v3k_phase_c1_gui_settings_bridge.md`

---

## 0. 목적

Phase C2의 목적은 **V3K 설정 bridge를 실제 MainWindow/pyd-free wrapper 경계에 연결하기 전에**, GUI 설정 저장/로드 흐름과 wrapper 호출 지점을 정확히 고정하는 것이다.

전체 V3K 목적은 변하지 않는다.

```text
STOM_Version_2U_C에서 Kiwoom 증권 API를 유지한다.
LS증권 직접 의존성은 제외한다.
V3의 분석·학습·DB·백테스트·실시간 사전학습 기능은 안전한 단계로 반영한다.
```

중요한 해석:

- Page 011은 Phase C1 완료 이후 다음 활성화 경계를 **Phase C2 GUI wrapper inventory/plan**으로 재선택하면서 닫힌다.
- Page 012는 Phase C2의 실제 진입 페이지다.
- 이 문서는 구현 완료 보고서가 아니라, 다음 코드 변경이 운영 DB·Kiwoom live runtime·주문/청산 판단으로 번지지 않도록 막는 실행 전 안전계획이다.

---

## 1. 현재 확정 상태

| 구분 | 상태 | 증거 |
| --- | --- | --- |
| Phase A | 완료 | `_database_v3k_shadow/` DDL-only rehearsal, schema hash, manifest, health 검증 |
| Phase B | 완료 | read-only learning DB row-read/leakage/write-rejection smoke |
| Phase C1 | 완료 | `bridge_v3k_settings_into_dict_set()`와 no-GUI `smoke_v3k_gui_settings_bridge.py` |
| 다음 경계 | 선택 완료 | Phase C2는 GUI wrapper inventory/plan, 실제 runtime hook은 아직 아님 |

Phase C1에서 만들어진 핵심 contract:

1. 모든 V3K flag는 기본값 `False`다.
2. `bridge_v3k_settings_into_dict_set()`는 입력 `dict_set`을 mutate하지 않는다.
3. legacy 설정 key는 보존한다.
4. 명시 입력이 없는 V3K key는 항상 default-OFF로 보강된다.
5. unknown V3K key는 diagnostic으로만 남고 무시된다.
6. formula facade도 명시적으로 formula flag가 켜질 때만 `V3K_` prefix globals를 만든다.

---

## 2. Phase C2에서 반드시 유지할 lifetime invariant

| Invariant | 의미 | Phase C2 적용 방식 |
| --- | --- | --- |
| Kiwoom 유지 | 2U_C는 V3 branch가 아니며 LS증권 전환 대상이 아니다. | `trade/stock_korea/kiwoom_*` 경계는 변경하지 않는다. LS import를 추가하지 않는다. |
| default-OFF | V3K 기능은 사용자가 명시적으로 켜기 전 기존 동작을 바꾸면 안 된다. | C2 최초 구현도 `bridge_v3k_settings_into_dict_set()`의 default-OFF 결과만 사용한다. |
| 운영 DB 무변경 | `_database/setting.db` schema/write 흐름은 운영 설정이다. | persistent 설정 저장/DB column 추가는 C2 최초 범위에서 제외한다. |
| shadow DB 무데이터 | `_database_v3k_shadow/`는 rehearsal artifact다. | C2는 shadow DB row를 만들거나 수정하지 않는다. |
| live runtime 무연결 | Kiwoom event loop, receiver/trader/order/exit에 영향 주면 안 된다. | C2는 GUI/wrapper inventory와 no-GUI smoke까지만 허용한다. |
| formula globals 무연결 | `globals().update`류 runtime hook은 이름 충돌과 전략 평가 side effect 위험이 있다. | Phase D 계획 전에는 runtime hook을 만들지 않는다. |
| analyzer output 미사용 | 분석 결과가 매수·매도·청산 판단에 들어가면 고위험이다. | Phase F/G 계획 전에는 trading decision으로 넘기지 않는다. |
| 공식 lane 무변경 | V2/V3/3U는 각각 공식/pyd-free lane이다. | C2 작업은 `STOM_Version_2U_C`에 한정한다. |

---

## 3. GUI/settings wrapper inventory

| 경계 | 파일/라인 근거 | 관찰 | Phase C2 판단 |
| --- | --- | --- | --- |
| 설정 탭 관리 버튼 | `ui/set_setup_tap.py:24-28` | 로딩/설정/삭제/저장 버튼이 `SettingAllLoad/App/Del/Save`로 직접 연결된다. | 실제 widget 추가 전 버튼/slot 영향 분석이 필요하다. 최초 C2는 widget 추가 금지. |
| 설정 개별 로드 버튼 | `ui/set_setup_tap.py:178-185` | 8개 설정 그룹이 `SettingLoad_01`~`SettingLoad_08`로 연결된다. | V3K flag 노출 위치를 기존 8개 그룹에 억지로 끼우면 layout/pyd-free wrapper 영향이 생긴다. |
| 설정 개별 저장 버튼 | `ui/set_setup_tap.py:187-194` | 8개 설정 그룹이 `SettingSave_01`~`SettingSave_08`로 연결된다. | persistent save는 운영 `setting.db` write 경계에 닿으므로 후순위다. |
| MainWindow 설정 wrapper | `ui/ui_mainwindow.py:993-1014` | MainWindow가 `setting_load_*`, `setting_save_*`, `setting_all_*`를 얇게 감싼다. | C2에서 바꿀 수 있는 가장 좁은 경계는 별도 helper/wrapper 추가이나, 최초에는 문서+smoke로 검증한다. |
| legacy button alias | `ui/ui_mainwindow.py:1387-1415` | `sjButtonClicked_*` alias가 설정 버튼을 다시 매핑한다. | wrapper 변경 시 legacy alias smoke가 필요하다. |
| 전체 설정 적용 | `ui/ui_button_clicked_settings.py:1549-1594` | `setting_all_app()`는 설정 DB 복사 후 load/save를 연쇄 호출한다. | 이 경계는 DB write와 프로세스 영향이 있어 C2 최초 대상에서 제외한다. |
| 전체 설정 저장/삭제 | `ui/ui_button_clicked_settings.py:1597-1621` | 설정 DB 파일 복사/삭제와 combobox refresh를 수행한다. | persistent V3K 설정 저장은 별도 DB/schema plan 전까지 보류한다. |
| 기타 설정 저장 | `ui/ui_button_clicked_settings.py:626-657` | `etc` table 업데이트 후 `ui.dict_set`을 직접 갱신한다. | V3K flag를 여기에 넣으면 `setting.db` schema migration이 필요하므로 금지한다. |
| Kiwoom/future manager 재구동 | `ui/ui_button_clicked_settings.py:304-312` | 증권사/에이전트 설정 변경 시 32비트 manager를 재구동한다. | C2는 이 경로에 절대 연결하지 않는다. |
| import-time 설정 DB 로드 | `utility/setting.py:95-113`, `utility/setting.py:406-424` | import 시 `setting.db`를 읽고 `DICT_SET`을 구성한다. | C2 최초 구현에서 import-time DB 로더 수정 금지. |
| runtime 사용자 설정 loader | `utility/setting_user.py:22-45`, `utility/setting_user.py:349-365` | runtime load_settings도 `setting.db`를 읽고 dict를 반환한다. | C2 최초 구현에서 loader 직접 수정 금지. |
| V3K settings bridge | `strategy/v3k_settings_surface.py:243-270` | Phase C1에서 dict-like bridge가 준비됨. | C2의 유일한 입력 contract로 사용한다. |

---

## 4. Phase C2 후보 분해

| 후보 | 내용 | 위험 | 판단 |
| --- | --- | --- | --- |
| C2-0 inventory/plan | 본 문서와 update_log로 wrapper 경계를 고정한다. | 낮음 | 이번 commit 범위 |
| C2-1 no-GUI wrapper adapter smoke | `FakeMainWindow`/dict 기반으로 wrapper가 V3K bridge 결과를 보유할 수 있는지 검증한다. 실제 PyQt widget, DB, live runtime은 사용하지 않는다. | 낮음~중간 | **다음 추천 단계** |
| C2-2 MainWindow in-memory helper | 실제 MainWindow에 `self.v3k_settings`/`self.v3k_feature_flags` 같은 in-memory helper를 default-OFF로 보강한다. DB 저장 없음. | 중간 | C2-1 smoke 이후 |
| C2-3 GUI checkbox 노출 | 실제 설정 탭에 V3K checkbox/표시를 노출한다. | 중간~높음 | pyd-free GUI smoke, layout 검증 후 |
| C2-4 persistent setting DB 저장 | V3K flag를 `setting.db` 또는 sidecar DB에 저장한다. | 높음 | DB schema/cutover plan 전까지 보류 |

---

## 5. 다음 실행 단계: C2-1 권장안

다음 단계는 **C2-1 no-GUI wrapper adapter smoke**가 가장 안전하다.

권장 구현 범위:

| 항목 | 권장 |
| --- | --- |
| 신규 helper 후보 | `ui/ui_v3k_settings_bridge.py` 또는 `strategy/v3k_settings_surface.py` 내 helper 재사용 |
| smoke 후보 | `scripts/smoke_v3k_gui_wrapper_inventory.py` 또는 `scripts/smoke_v3k_gui_wrapper_bridge.py` |
| 입력 | legacy `dict_set`, 명시 `raw_settings`, unknown V3K key |
| 출력 | default-OFF `settings`, `feature_flags`, diagnostic, source mutation 없음 |
| 금지 | PyQt widget 생성, `setting.db` write, `_database`/shadow DB write, live Kiwoom hook, formula globals runtime hook |
| 성공 기준 | no-GUI smoke + 기존 V3K smoke suite + VERIFY-1A/1B + nonrelease sync 통과 |

C2-1은 “실제 GUI 표시”가 아니라 “GUI wrapper가 안전하게 들고 있을 수 있는 V3K 설정 객체의 경계 검증”이다. 이 순서를 지켜야 C2-2/C2-3에서 실제 MainWindow나 widget을 바꾸더라도 rollback 지점이 작다.

---

## 5.1 C2-1 구현 결과

2026-05-12 KST 기준 C2-1 no-GUI wrapper adapter smoke를 완료했다.

| 산출물 | 내용 |
| --- | --- |
| `ui/ui_v3k_settings_bridge.py` | `attach_v3k_gui_settings_bridge()` helper. PyQt/DB/subprocess/globals runtime 의존성 없이 MainWindow-like object에 V3K settings/feature_flags를 부착한다. |
| `scripts/smoke_v3k_gui_wrapper_bridge.py` | FakeMainWindow 기반 no-GUI smoke. default-OFF, source mutation 없음, explicit in-memory dict replacement, diagnostics, missing dict_set object, artifact 불변성을 검증한다. |
| `docs/update_log/2026-05-12_v3k_phase_c2_1_gui_wrapper_bridge.md` | C2-1 구현 기록과 보류 항목 기록. |

C2-1은 실제 `ui/ui_mainwindow.py`를 아직 변경하지 않는다. 즉, “wrapper가 안전하게 보유할 수 있는 state contract”를 먼저 증명한 단계다. 실제 MainWindow 연결은 C2-2에서 별도 검토/구현한다.

---

## 5.2 C2-2 구현 결과

2026-05-12 KST 기준 C2-2 MainWindow in-memory helper integration을 완료했다.

| 산출물 | 내용 |
| --- | --- |
| `ui/ui_mainwindow.py` | `self.dict_set = dict_set` 직후, `WidgetCreater(self)` 이전에 `attach_v3k_gui_settings_bridge(self)`를 호출해 V3K state를 default-OFF in-memory로 보유한다. |
| `ui/ui_v3k_settings_bridge.py` | `v3k_settings_bridge_result` attribute를 helper에서 함께 부착하도록 보강했다. |
| `scripts/smoke_v3k_gui_wrapper_bridge.py` | MainWindow source-level integration boundary smoke를 추가했다. |
| `docs/update_log/2026-05-12_v3k_phase_c2_2_mainwindow_in_memory_bridge.md` | C2-2 구현 기록과 보류 항목 기록. |

C2-2는 실제 checkbox/widget 또는 persistent DB 저장이 아니다. MainWindow가 V3K settings/feature_flags를 안전하게 보유할 수 있는 in-memory state를 준비한 단계다.

---

## 5.3 C2-3 feasibility 결과

2026-05-12 KST 기준 C2-3 GUI checkbox/layout feasibility 검토를 완료했다.

| 검토 항목 | 결론 |
| --- | --- |
| 기존 일반설정 탭 내 삽입 | 고정 geometry와 기존 8개 groupBox가 촘촘해 즉시 삽입은 위험하다. |
| 기타 groupBox 재사용 | 시리얼키 조건부 UI와 기존 `SettingSave_08`/`etc` table 저장 경계가 있어 부적합하다. |
| 백테 groupBox 재사용 | 기존 백테 옵션이 이미 밀집되어 있고 V3K analyzer/formula flag까지 넣으면 의미가 섞인다. |
| 별도 V3K 탭/dialog | 가장 안전한 후보. 기존 groupBox 재배치를 피하고 V3K settings contract metadata를 그대로 표시할 수 있다. |
| persistent 저장 | 실제 사용자 토글을 제공하려면 필요할 수 있으나, 운영 `setting.db` schema/write 변경은 C2-4에서 별도 판단해야 한다. |

C2-3에서는 실제 widget을 추가하지 않았다. 다음 단계는 C2-4 persistent 설정 저장 여부 재판단이다.

---

## 5.4 C2-4 persistent 저장 결정

2026-05-12 KST 기준 C2-4 persistent 설정 저장 여부 재판단을 완료했다.

| 선택지 | 판단 |
| --- | --- |
| session-only | **다음 구현 경계로 선택**. 운영 DB와 sidecar 파일을 만들지 않고 UI preview를 가장 작게 시작한다. |
| sidecar 설정 저장소 | 운영 `setting.db`보다 안전한 장기 후보지만 파일 위치/ignore/backup/동기화 정책이 필요하므로 보류한다. |
| 운영 `_database/setting.db` migration | 기존 설정 DB schema/write와 설정 파일 복사/적용 흐름을 바꾸므로 현재 제외한다. |

Page 012는 이 결정으로 완료한다. 다음은 Page 013 session-only V3K UI preview skeleton이다.

---

## 5.5 C2-5 session-only UI preview skeleton

2026-05-12 KST 기준 Page 013 / C2-5를 완료했다.

| 항목 | 결과 |
| --- | --- |
| UI 경계 | 기존 groupBox가 아니라 별도 lazy dialog skeleton을 선택했다. |
| 연결 방식 | MainWindow에 `ShowV3KSettingsPreview` opener method를 붙였다. |
| 저장 정책 | session-only. 운영 DB/sidecar/shadow DB write 없음. |
| 노출 정책 | visible launcher는 아직 추가하지 않았다. Page 014에서 geometry/shortcut/layout 충돌을 먼저 닫는다. |
| 검증 | `smoke_v3k_gui_settings_preview.py`와 기존 C2 smoke를 통과했다. |

---

## 5.6 C2-6 session-only preview launcher exposure

2026-05-12 KST 기준 Page 014 / C2-6을 완료했다.

| 항목 | 결과 |
| --- | --- |
| 노출 방식 | visible launcher button 선택 |
| 위치 | Alt block의 빈 칸 `(23, 450, 16, 15)` |
| 단축키 | `Alt+V` |
| 동작 | `ShowV3KSettingsPreview()` 호출 |
| 저장 정책 | session-only 유지. `setting.db`/sidecar/shadow DB write 없음 |

다음은 Page 015에서 GUI preview를 session-only로 닫고 Phase D로 넘어갈지, sidecar persistence 설계를 먼저 열지 결정한다.

---

## 6. 검증 계획

문서-only C2-0 검증:

```powershell
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

C2-1 구현 시 추가 검증:

```powershell
python -m py_compile strategy/v3k_settings_surface.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py
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
git status --short -- _database/ _database_v3k_shadow/ *.db
```

GUI/wrapper 실제 파일을 건드린 뒤에는 가능한 경우 다음도 추가한다.

```powershell
python scripts/verify_pyd_gui_contract.py
python scripts/smoke_offline_gui.py
```

단, 위 두 GUI 검증은 PyQt/Windows GUI 환경 의존성이 있으므로 실패 시 실패 원인이 환경인지 코드인지 update_log에 분리 기록한다.

---

## 7. 명시적 보류 항목 재확인

| 보류 항목 | 보류 이유 | C2에서 다시 봐도 보류가 맞는가 |
| --- | --- | --- |
| 운영 `_database/setting.db` schema migration | persistent 설정 저장은 기존 사용자 설정 DB를 바꾼다. | 맞음. C2-1은 no-GUI/in-memory smoke로 충분하다. |
| 실제 GUI checkbox 추가 | layout, pyd-free wrapper, legacy alias 영향이 있다. | 맞음. C2-1 smoke 후 C2-3로 별도 진행해야 한다. |
| formula/global runtime hook | strategy globals 충돌과 평가 side effect가 있다. | 맞음. Phase D plan 전까지 금지. |
| live Kiwoom dry-run preload | event loop/latency/receiver coupling 위험이 있다. | 맞음. Phase E plan 전까지 금지. |
| analyzer output trading decision | 매수·매도·청산 판단을 바꾸는 최고위험 단계다. | 맞음. Phase F/G plan 전까지 금지. |
| LS Securities 직접 의존성 | V3K의 정의 위반이다. | 영구 금지. |

---

## 8. Page 진행률

Page 011은 이 문서와 연결된 update_log를 통해 “다음 활성화 경계 재선택”을 완료한다.

```text
Page 011: [██████████] 5 / 5 steps = 100%
전체 11페이지: [███████████] 11 / 11 pages = 100%
```

단, 이는 “초기 11페이지 계획의 완료”이지 “V3K 전체 생산 활성화 완료”가 아니다. 2U_C에 V3 기능을 Kiwoom 유지 상태로 안전하게 더 활성화하려면 Page 012부터 C2-1 → C2-2 → C2-3 순서로 별도 commit을 쌓아야 한다.

Page 012 현재 상태:

| Step | 이름 | 상태 | 진행률 |
| ---: | --- | --- | ---: |
| 012-1 | C2 wrapper inventory/plan | 완료 | 100% |
| 012-2 | C2-1 no-GUI wrapper adapter smoke | 완료 | 100% |
| 012-3 | C2-2 MainWindow in-memory helper 검토 | 완료 | 100% |
| 012-4 | C2-3 GUI checkbox/layout 검토 | 완료 | 100% |
| 012-5 | C2 persistent 설정 저장 여부 재판단 | 완료 | 100% |

```text
Page 012: [██████████] 5 / 5 steps = 100%
```

---

## 9. 다음 추천 OMX 명령

```powershell
omx ralph "force: V3K Page 015 Phase C2-7 V3K GUI preview closeout and sidecar persistence decision을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md를 기준으로 session-only V3K preview가 충분한지, 다음에 sidecar persistence 설계를 시작할지, 아니면 GUI는 session-only로 닫고 Phase D formula/analyzer runtime boundary로 넘어갈지 재판단한다. 운영 _database/setting.db schema/write, sidecar 파일 write, Kiwoom 주문/청산/live runtime, formula globals runtime hook, analyzer output trading decision, LS Securities 직접 의존성은 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 다음 page 계획을 추가한 뒤 py_compile, smoke_v3k_gui_settings_preview, smoke_v3k_gui_wrapper_bridge, smoke_v3k_gui_settings_bridge, smoke_v3k_settings_surface, verify_pyd_gui_contract.py, smoke_offline_gui.py, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```

현재 Codex 환경에서 `omx ralph`가 `stdin is not a terminal`로 실패하면, 같은 프롬프트를 현재 세션에서 직접 이어서 수행한다.

연결된 다음 페이지 계획: `docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md`
