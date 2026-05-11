# 2026-05-12 V3K Phase C2-4 persistent 설정 저장 여부 재판단 기록

## 1. 목적

이번 작업의 목적은 Page 012 Phase C2-4를 완료하는 것이다. C2-3에서 실제 V3K checkbox/layout 노출이 가능하지만 기존 설정 groupBox에 즉시 삽입하는 것은 위험하다고 판단했으므로, 실제 widget 추가 전에 V3K GUI settings를 어디까지 저장할지 결정했다.

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

## 3. 비교한 저장 정책

| 선택지 | 장점 | 위험/비용 | 판단 |
| --- | --- | --- | --- |
| A. session-only | 운영 DB를 바꾸지 않는다. rollback이 쉽다. 실제 UI preview와 smoke를 가장 작게 시작할 수 있다. | 재시작/설정 파일 전환 후 유지되지 않는다. 사용자가 persistence를 기대하면 혼동 가능성이 있다. | **다음 구현 경계로 선택**. UI label/log에 session-only임을 명확히 해야 한다. |
| B. sidecar 설정 저장소 | 운영 `setting.db` schema를 건드리지 않고 persistence를 제공할 수 있다. 향후 migration 전 완충층이 될 수 있다. | sidecar 파일/DB 위치, ignore/backup, 설정 파일 복사와 동기화, 손상 복구 정책이 새로 필요하다. 파일 write가 발생한다. | 보류. session-only UI preview 이후 별도 phase로 설계한다. |
| C. 운영 `_database/setting.db` migration | 기존 설정 저장/불러오기 흐름과 가장 일관된다. | `etc` table 또는 신규 table schema 변경, 설정 파일 복사/적용, 구버전 DB 호환, rollback, 사용자 DB 백업이 필요하다. | 현재 제외. DB cutover/migration plan 전까지 금지한다. |

## 4. 결정

C2-4의 결정은 다음과 같다.

```text
다음 실제 UI 구현은 session-only V3K UI preview로 제한한다.
sidecar 저장소와 운영 setting.db migration은 이번 페이지에서 구현하지 않는다.
```

이 결정의 의미:

1. Page 013에서 실제 V3K UI skeleton을 만들 수 있다.
2. 단, UI는 default-OFF/session-only state만 표시하거나 토글한다.
3. 재시작 후 유지되지 않는다는 점을 문서와 UI label/tooltip 또는 로그로 명확히 해야 한다.
4. persistent 저장은 sidecar 또는 setting.db migration을 별도 phase에서 다시 판단한다.
5. 운영 `_database/setting.db`는 계속 무변경이다.

## 5. 왜 sidecar를 즉시 선택하지 않았는가

sidecar는 운영 `setting.db`보다 안전한 장기 후보지만, 이번 단계에서 바로 구현하지 않는다.

| 이유 | 설명 |
| --- | --- |
| 위치 정책 | `_database_v3k_settings.json`처럼 둘지, `_database/v3k_settings.db`처럼 둘지, 사용자별 경로를 둘지 결정해야 한다. |
| ignore/commit 정책 | runtime 설정 파일이 repo에 커밋되지 않도록 `.gitignore`와 artifact guard가 필요하다. |
| 설정 파일 복사와 동기화 | 기존 `setting_*.db` 복사/적용과 sidecar persistence의 관계가 정해져야 한다. |
| 복구 정책 | sidecar 손상/누락 시 default-OFF fallback과 diagnostic이 필요하다. |
| 테스트 | sidecar write/read, corruption, missing file, rollback smoke가 별도로 필요하다. |

따라서 sidecar는 “운영 DB migration 전 완충층” 후보로 남기되, 실제 UI preview가 session-only로 안정화된 뒤 별도 phase에서 다룬다.

## 6. 왜 운영 setting.db migration을 제외했는가

| 이유 | 설명 |
| --- | --- |
| schema 위험 | `setting.db`의 `etc` table 또는 신규 table schema 변경이 필요하다. |
| 구버전 DB 호환 | 기존 사용자 DB에 column/table이 없을 때 fallback/migration이 필요하다. |
| 설정 파일 복사 영향 | `SettingAllApp`/`SettingAllSave`가 `setting_*.db` 파일 복사와 연동된다. |
| rollback 비용 | 잘못된 schema 변경은 사용자 설정 DB 복구가 필요하다. |
| 현재 목표 초과 | C2는 GUI activation 경계이며 운영 DB cutover는 별도 DB phase에서 다뤄야 한다. |

## 7. 다음 경계

다음 경계는 **Page 013 / C2-5 session-only V3K UI preview skeleton**이다.

권장 사항:

1. 기존 groupBox에 끼워 넣지 말고 별도 V3K 탭 또는 별도 dialog를 검토한다.
2. `v3k_settings_contract_rows()` metadata를 표시 원천으로 사용한다.
3. MainWindow의 `v3k_settings`/`v3k_feature_flags` in-memory state만 갱신한다.
4. `setting.db` write, sidecar write, `_database_v3k_shadow` row 변경은 금지한다.
5. `verify_pyd_gui_contract.py`와 가능한 경우 `smoke_offline_gui.py`를 실행한다.

## 8. 이번 단계에서 변경하지 않은 것

- 실제 PyQt checkbox/widget 추가
- 운영 `_database/setting.db` schema/write
- sidecar 설정 파일/DB write
- `_database_v3k_shadow` row/data
- Kiwoom 주문/청산/live runtime
- formula globals runtime hook
- analyzer output trading decision
- LS Securities 직접 의존성

## 9. 검증 결과

아래 검증을 통과했다. 최초에 `verify_pyd_gui_contract.py`와 `smoke_offline_gui.py`를 인자 없이 실행했을 때는 argparse usage 오류가 발생했으므로, 기존 기록 문서의 Python 3.13 실행 형식에 맞춰 branch/version/log-dir 인자를 명시해 재실행했다.

```powershell
python -m py_compile strategy/v3k_settings_surface.py strategy/v3k_analyzer_adapter.py ui/ui_mainwindow.py ui/ui_v3k_settings_bridge.py scripts/smoke_v3k_gui_wrapper_bridge.py scripts/smoke_v3k_gui_settings_bridge.py scripts/smoke_v3k_settings_surface.py
python scripts/smoke_v3k_gui_wrapper_bridge.py
python scripts/smoke_v3k_gui_settings_bridge.py
python scripts/smoke_v3k_settings_surface.py
python scripts/smoke_offline_gui.py --branch STOM_Version_2U_C --version V2.79 --offline --log-dir .omx/logs/v3k-c2
python scripts/verify_pyd_gui_contract.py --branch STOM_Version_2U_C --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/v3k-c2/verify_pyd_gui_contract.json --log-dir .omx/logs/v3k-c2
python scripts/audit_v3k_verify_1a.py --base 57496d24
python scripts/audit_v3k_verify_1b_closure.py
python scripts/verify_nonrelease_sync.py
git diff --check
git status --short -- _database/ _database_v3k_shadow/ *.db
```

검증 메모:

- `smoke_offline_gui.py`는 Python 3.13/PyQt 환경의 font directory warning과 offline guard의 `KHOPENAPI` no-candidate 로그를 출력했지만 최종 결과는 `[OK] offline GUI smoke passed`였다.
- `git diff --check`의 EOF blank line 경고는 문서 EOF를 single newline으로 정리한 뒤 통과했다.
- `git status --short -- _database/ _database_v3k_shadow/ *.db` 출력은 비어 있었으므로 operating DB/shadow DB artifact 변경은 없다.

## 10. 진행률

```text
초기 11페이지: [███████████] 11 / 11 = 100%
Page 012: [██████████] 5 / 5 = 100%
Page 013: [░░░░░░░░░░] 0 / 5 = 0%
```

Page 012에서 완료된 항목:

1. C2 wrapper inventory/plan
2. C2-1 no-GUI wrapper adapter smoke
3. C2-2 MainWindow in-memory helper integration
4. C2-3 GUI checkbox/layout feasibility 검토
5. C2-4 persistent 설정 저장 여부 재판단

## 11. 다음 작업 지침

다음 단계는 **Page 013 / C2-5 session-only V3K UI preview skeleton**이다. 실제 UI skeleton은 허용하되, 저장은 session-only로 제한한다. sidecar/setting.db persistence는 아직 구현하지 않는다.
