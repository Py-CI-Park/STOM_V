# 2026-05-12 V3K Phase C2-7 GUI preview closeout and sidecar persistence decision

## 1. 목적

Page 015 / C2-7의 목적은 C2 GUI activation lane을 닫을지, sidecar persistence 설계를 먼저 열지, 또는 Phase D formula/global runtime boundary로 넘어갈지 결정하는 것이다.

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

따라서 같은 목표를 현재 세션에서 직접 이어서 수행했다.

## 3. C2 목표 대비 현재 구현 점검

| C2 항목 | 현재 상태 | 판단 |
| --- | --- | --- |
| settings surface | `strategy/v3k_settings_surface.py`가 default-OFF contract를 제공 | 완료 |
| MainWindow inert state | `attach_v3k_gui_settings_bridge(self)`가 `v3k_settings`/`v3k_feature_flags`를 보유 | 완료 |
| session-only preview dialog | `ui/ui_v3k_settings_preview.py`가 lazy dialog skeleton과 in-memory toggle/reset 제공 | 완료 |
| visible launcher | `Alt+V` / `v3_pushButton`이 `ShowV3KSettingsPreview()` 호출 | 완료 |
| persistence 차단 | `setting.db`, sidecar, shadow DB write 없음 | 유지 |
| no-GUI smoke | `scripts/smoke_v3k_gui_settings_preview.py`가 launcher/session-only 경계를 검증 | 완료 |

결론:

```text
C2 GUI activation lane은 session-only preview + Alt+V launcher 기준으로 닫아도 충분하다.
```

## 4. sidecar persistence 판단

sidecar persistence는 지금 구현하지 않는다.

| 검토 항목 | 판단 |
| --- | --- |
| 사용자 편의 | preview flag가 재시작 후 유지되지 않는 불편은 있다. |
| 안전성 | sidecar는 운영 `setting.db` migration보다 안전하지만 file write가 생긴다. |
| 미해결 정책 | 파일 위치, `.gitignore`, backup, corruption recovery, 기존 `setting_*.db` 복사 흐름과의 동기화가 미정이다. |
| 현재 목적 | C2는 GUI activation 경계이며 persistence 구현 page가 아니다. |

따라서 sidecar는 다음 조건 중 하나가 발생할 때 별도 page로 연다.

1. Phase D/E/F 진행 중 session-only flag만으로 검증 흐름이 반복적으로 불편해진다.
2. 사용자가 명시적으로 V3K preview flag persistence를 요구한다.
3. file/path/ignore/backup/corruption policy를 별도 문서로 먼저 닫을 수 있다.

## 5. operating setting.db 판단

운영 `_database/setting.db` migration은 계속 금지한다.

이유:

- `etc` table 또는 신규 table schema migration이 필요하다.
- 기존 사용자 DB와 설정 파일 복사/적용 흐름을 건드린다.
- rollback/backup/corruption 대응이 sidecar보다 훨씬 무겁다.
- 현재는 V3K 기능 활성화의 초기 안전 단계이며 운영 설정 DB를 바꿀 이유가 부족하다.

## 6. 다음 phase 선택

다음은 **Page 016 / Phase D-0 formula/global runtime boundary design**으로 이동한다.

단, Page 016은 바로 `globals().update` runtime hook을 구현하지 않는다. 먼저 아래를 설계/검증한다.

1. `trade/formula_manager.py::FormulaManager.UpdateGlobalsFunc`의 기존 `globals().update` 경계
2. `trade/base_strategy.py`의 formula function 생성 경계
3. `strategy/v3k_formula_facade.py`의 `V3K_` prefixed callable contract
4. 기존 전략식 이름과 `V3K_` prefix 충돌 가능성
5. feature flag가 OFF일 때 globals가 생성되지 않는 조건

## 7. 이번 단계에서 변경하지 않은 것

- sidecar 파일/DB 생성 또는 write
- 운영 `_database/setting.db` schema/write
- `_database_v3k_shadow` row/data 변경
- `globals().update` runtime hook
- Kiwoom 주문/청산/live runtime
- analyzer output trading decision
- LS Securities 직접 의존성

## 8. 검증 결과

아래 검증을 통과했다.

```powershell
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/set_main_menu.py ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py ui/ui_v3k_settings_preview.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py scripts/smoke_v3k_gui_settings_preview.py scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_gui_settings_preview.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_formula_facade.py
python scripts/smoke_offline_gui.py --branch STOM_Version_2U_C --version V2.79 --offline --log-dir .omx/logs/v3k-c2-7
python scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U_C --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v3k-c2-7/verify_pyd_gui_contract.json --log-dir .omx/logs/v3k-c2-7
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

검증 메모:

- `smoke_offline_gui.py`는 기존과 같이 Python 3.13/PyQt font warning과 offline guard의 `KHOPENAPI` no-candidate 로그를 출력하지만 최종 결과는 `[OK] offline GUI smoke passed`다.
- DB artifact status 출력은 비어 있었으므로 운영 DB/shadow DB 변경은 없다.

## 9. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [██████████] 5 / 5 = 100%
Page 013: [██████████] 5 / 5 = 100%
Page 014: [██████████] 5 / 5 = 100%
Page 015: [██████████] 5 / 5 = 100%
Page 016: [░░░░░░░░░░] 0 / 5 = 0%
```

Page 015 완료 항목:

1. C2 목표 대비 현재 구현 점검
2. sidecar persistence 필요성 판단
3. 다음 phase 선택: Phase D-0 formula/global runtime boundary design
4. registry/update_log 정리
5. full regression

## 10. 다음 작업 지침

다음 단계는 **Page 016 / Phase D-0 formula/global runtime boundary design**이다.

추천 명령:

```powershell
omx ralph "force: V3K Page 016 Phase D-0 formula/global runtime boundary design을 진행한다. 대상은 C:/System_Trading/STOM/STOM_V.wt-dev 의 STOM_Version_2U_C branch다. docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md와 docs/update_log/2026-05-12_v3k_phase_c2_7_gui_preview_closeout.md를 기준으로 trade/formula_manager.py의 UpdateGlobalsFunc, trade/base_strategy.py의 formula function 생성, strategy/v3k_formula_facade.py의 V3K_ prefixed globals facade 사이 충돌/주입 경계를 설계한다. 첫 단계에서는 globals().update runtime hook, Kiwoom 주문/청산/live runtime, analyzer output trading decision, 운영 _database/setting.db schema/write, sidecar 파일 write, LS Securities 직접 의존성을 변경하지 않는다. 결과를 docs/update_log와 CARRY_FORWARD_REGISTRY에 기록하고 필요한 경우 source-level collision smoke 계획을 추가한 뒤 py_compile, smoke_v3k_formula_facade.py, smoke_v3k_gui_settings_preview, smoke_v3k_settings_surface, audit_v3k_verify_1a --base 57496d24, audit_v3k_verify_1b_closure, verify_nonrelease_sync, git diff --check, DB artifact status를 통과시키고 한국어 Lore commit한다."
```
