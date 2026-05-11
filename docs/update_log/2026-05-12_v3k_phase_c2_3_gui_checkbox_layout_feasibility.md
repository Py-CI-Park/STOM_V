# 2026-05-12 V3K Phase C2-3 GUI checkbox/layout feasibility 검토 기록

## 1. 목적

이번 작업의 목적은 Page 012 Phase C2-3을 완료하는 것이다. C2-1/C2-2에서 V3K settings/feature_flags를 no-GUI helper와 MainWindow inert state로 준비했으므로, 다음 단계에서는 실제 GUI checkbox/layout에 노출할 수 있는지 안전 경계를 검토했다.

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

`omx explore`도 Windows POSIX allowlist runtime 제한으로 사용할 수 없어, PowerShell/Python read-only 조사로 대체했다.

## 3. 조사한 실제 GUI/settings 경계

| 경계 | 파일/근거 | 관찰 | C2-3 판단 |
| --- | --- | --- | --- |
| 설정 탭 구조 | `ui/set_setup_tap.py:16-32` | `ssd_tab`, `sod_tab`, `cod_tab` 3개 탭 구조다. 일반 설정 탭에 8개 groupBox가 고정 배치된다. | 기존 일반설정 탭에 12개 V3K checkbox를 억지 삽입하기보다 별도 V3K 탭 또는 별도 dialog가 안전하다. |
| 일반 설정 groupBox | `ui/set_setup_tap.py:209-216` | groupBox 01~08이 y=5~707까지 촘촘히 배치된다. `set_tapWidgett_01` 높이는 742다. | 현재 layout에 여백이 거의 없다. 실제 checkbox 추가는 고정 geometry 재배치 위험이 있다. |
| 백테 groupBox | `ui/set_setup_tap.py:293-318` | 백테 관련 checkbox가 이미 16개 이상 있고 y=125까지 사용한다. | V3K 분석/학습 flag를 백테 groupBox에 추가하면 기존 백테 UI와 충돌 가능성이 높다. |
| 기타 groupBox | `ui/set_setup_tap.py:320-331` | 기타 checkbox가 2줄, 시리얼키가 있으면 3줄째를 사용한다. | 시리얼키 조건부 UI와 충돌하므로 V3K flag를 기타 groupBox에 넣는 것은 부적합하다. |
| Load/Save 버튼 | `ui/set_setup_tap.py:178-194`, `333-349` | 8개 groupBox별 `SettingLoad_*`, `SettingSave_*`가 고정 연결된다. | 새 V3K UI를 만들면 별도 load/save wrapper 또는 기존 `SettingSave_08` 확장이 필요하다. 후자는 DB schema 위험이 있다. |
| 기타 설정 load/save | `ui/ui_button_clicked_settings.py:237-250`, `626-657` | `etc` table에서 기존 column을 읽고 `UPDATE etc SET ...`로 저장한다. | V3K flag를 여기에 저장하려면 `setting.db` schema migration이 필요하므로 C2-3에서는 금지한다. |
| 전체 설정 적용 | `ui/ui_button_clicked_settings.py:1549-1594` | 설정 파일 복사 후 load/save 전체를 연쇄 호출한다. | V3K persistent 저장을 끼우면 설정 파일 복사/적용 흐름까지 영향을 받는다. C2-4에서 정책을 먼저 정해야 한다. |
| MainWindow aliases | `ui/ui_mainwindow.py:995-1017`, `1389-1417` | wrapper와 legacy `sjButtonClicked_*` alias가 고정되어 있다. | 실제 GUI 버튼/slot 추가 시 alias 및 pyd-free wrapper contract 검증이 필요하다. |
| C2 in-memory state | `ui/ui_mainwindow.py`, `ui/ui_v3k_settings_bridge.py` | V3K settings/feature_flags는 이미 MainWindow에 inert default-OFF state로 존재한다. | 실제 checkbox는 이 state를 표시/토글하는 presentation layer로만 시작해야 한다. |

## 4. V3K UI 노출 대상 규모

`strategy.v3k_settings_surface.v3k_settings_contract_rows()` 기준:

| 항목 | 수량 |
| --- | ---: |
| 전체 V3K setting contract | 13 |
| `ui_exposable=True` | 12 |

UI 노출 후보는 다음 그룹으로 나뉜다.

| 그룹 | 예시 | 판단 |
| --- | --- | --- |
| `ui` | `V3K_ANALYSIS_UI_ENABLED` | 상위 표시/활성화 gate로 볼 수 있다. |
| `learning` | `V3K_BACKTEST_LEARNING_ENABLED`, `V3K_REALTIME_LEARNING_ENABLED` | DB/read-only policy와 강하게 연결된다. |
| `analyzer` | `캔들분석`, `거래량분석`, `가격대분석`, `변동성분석`, `변손익분석`, `리스크분석`, `V3K_RISK_ANALYZER_V3_ENGINE` | 실제 trading decision과 혼동될 수 있어 label/tooltip에서 “분석 staging”임을 명확히 해야 한다. |
| `formula` | `V3K_FORMULA_MANAGER_ADAPTER`, `V3K_STG_GLOBALS_FACADE` | runtime globals hook과 혼동될 수 있어 Phase D 전까지 default-OFF/preview 표시에 그쳐야 한다. |

## 5. feasibility 결론

C2-3 결론은 다음과 같다.

| 질문 | 결론 |
| --- | --- |
| 실제 GUI checkbox/layout 노출이 기술적으로 가능한가 | 가능하다. 이미 MainWindow에 inert state가 있고 `v3k_settings_contract_rows()`가 label/group metadata를 제공한다. |
| 지금 즉시 기존 일반설정 groupBox에 checkbox를 추가하는 것이 안전한가 | 안전하지 않다. 고정 geometry가 촘촘하고 시리얼키 조건부 UI, 기존 load/save 버튼, pyd-free wrapper alias 영향이 있다. |
| 가장 안전한 UI 형태는 무엇인가 | 기존 groupBox에 끼워 넣기보다 `set_tapWidgett_01`에 별도 `v3k_tab`을 추가하거나 별도 dialog로 분리하는 것이다. |
| persistent 저장 없이 표시만 할 수 있는가 | 가능하지만 재시작/설정 파일 전환 시 유지되지 않는다. 이 정책을 사용자가 이해할 수 있게 해야 한다. |
| persistent 저장이 필요한가 | 실제 사용자 토글을 제공하려면 필요할 가능성이 높다. 다만 `setting.db` schema 변경은 C2-4에서 별도 판단해야 한다. |
| C2-3에서 widget을 추가했는가 | 아니다. 이번 commit은 feasibility 문서화만 수행했다. |

## 6. 권장 설계 방향

C2-4에서 persistent 설정 정책을 정한 뒤, 실제 GUI를 구현한다면 다음 순서가 안전하다.

1. **C2-4**: persistent 설정 저장 여부 재판단.
   - 선택지 A: 당분간 in-memory/session-only 토글만 허용.
   - 선택지 B: 운영 `setting.db`가 아닌 sidecar 설정 저장소를 설계.
   - 선택지 C: 운영 `setting.db` schema migration을 별도 cutover plan으로 진행.
2. **C2-5 또는 Page 013**: 별도 V3K 탭/dialog skeleton.
   - 기존 groupBox 재배치 없이 `v3k_settings_contract_rows()`를 읽어 표시한다.
   - default-OFF, no persistence 또는 C2-4에서 정한 저장 정책만 사용한다.
3. **이후 단계**: formula/live/analyzer runtime hook은 Phase D/E/F/G에서 별도 진행한다.

## 7. C2-3에서 금지 유지한 것

| 금지 항목 | 유지 이유 |
| --- | --- |
| 실제 PyQt checkbox/widget 추가 | layout/pyd-free wrapper와 persistent policy가 아직 완전히 닫히지 않았다. |
| `setting.db` schema/write 변경 | 운영 설정 DB cutover/rollback 계획 전까지 금지한다. |
| `_database_v3k_shadow` row 변경 | GUI layout feasibility와 무관하다. |
| Kiwoom 주문/청산/live runtime | GUI 표시 검토 단계이며 runtime activation이 아니다. |
| formula globals runtime hook | Phase D 전까지 금지한다. |
| analyzer output trading decision | Phase F/G 전까지 금지한다. |
| LS Securities 직접 의존성 | V3K 정의상 영구 제외한다. |

## 8. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

## 9. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [████████░░] 4 / 5 = 80%
```

Page 012에서 완료된 항목:

1. C2 wrapper inventory/plan
2. C2-1 no-GUI wrapper adapter smoke
3. C2-2 MainWindow in-memory helper integration
4. C2-3 GUI checkbox/layout feasibility 검토

남은 항목:

1. C2 persistent 설정 저장 여부 재판단

## 10. 다음 작업 지침

다음 단계는 **C2-4 persistent 설정 저장 여부 재판단**이다. 실제 GUI widget 추가 전에 V3K setting state를 session-only로 둘지, sidecar 설정 저장소를 둘지, 운영 `setting.db` migration으로 갈지 결정해야 한다. 기본 추천은 운영 `setting.db`를 즉시 변경하지 않고, 먼저 session-only 또는 별도 sidecar 정책을 문서로 결정하는 것이다.
