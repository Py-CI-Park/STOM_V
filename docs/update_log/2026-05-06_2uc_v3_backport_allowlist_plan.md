# 2U_C V3 backport allowlist 및 검증 계획

작성일: 2026-05-06
대상 root: `C:/System_Trading/STOM/STOM_V`
대상 custom worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
상위 문서: `docs/update_log/2026-05-06_2uc_v3_backport_queue_start.md`

## 1. 목적

이 문서는 Phase 11.3에서 읽기 전용으로 선별한 V3 -> 2U_C 백포트 후보를 Phase 11.4 기준으로 고정한다.

`STOM_Version_2U_C`는 V3 branch가 아니라 V2/Kiwoom 유지 custom lane이다. 따라서 V3의 LS API 전환, DB schema migration, V3U pyd-free 구현을 직접 가져오지 않는다. 이 문서의 allowlist는 실제 코드 적용이 아니라, 이후 후보별 수동 백포트 여부를 판단하기 위한 작업 큐와 검증 기준이다.

## 2. 사용자 전략 원안 반영

이번 allowlist는 앞선 전략 협의의 핵심 결정을 따른다.

- `STOM_Version_3`는 공식 V3 ingress lane으로 유지한다.
- `STOM_Version_3U`는 V3에서 분기하되, pyd 제거는 `STOM_Version_2U`의 pyd-to-py 추론 산출물과 검증 도구를 참고한다.
- `STOM_Version_2U_C`는 계속 V2/Kiwoom 유지 custom lane으로 개발한다.
- V3의 새 기능 중 LS증권 전환이 아닌 기능은 2U_C에 선별 backport할 수 있다.
- `STOM_Version_3U_C`는 아직 만들지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/`는 커밋하지 않는다.

## 3. Phase 11.3 근거 요약

읽기 전용 분석 결과는 다음과 같다.

| 항목 | 결과 |
|---|---|
| V3 공식 범위 | `STOM V3.0` ~ `STOM V3.18`, 총 19개 공식 commit |
| V3 base | `0a2d7fa1807d23216048740a73cfca3448470a16` |
| V3 HEAD | `7faec937 STOM V3.18` |
| 2U_C HEAD | `baefe77b 2U_C pyd MainWindow 상태 계약을 주변 helper와 맞춘다` |
| 2U_C custom 규모 | 2U 대비 653 commit, 724 changed files |
| 2U_C 작업 상태 | 기존 보호 출력 `?? backtest/graph/` 외 추적 변경 없음 |

`omx explore`는 Windows POSIX wrapper 미준비로 실패했으므로, Phase 11.3은 `omx sparkshell` 및 로컬 git 분석으로 대체했다. 이후 작업에서도 Windows 환경에서는 단순 repository 조회에 `omx sparkshell` 또는 직접 PowerShell/git 명령을 사용한다.

## 4. 절대 제외 목록

아래 항목은 별도 설계 승인 전까지 2U_C 백포트 대상이 아니다.

| 제외 항목 | 제외 사유 |
|---|---|
| V3.0 전체 구조 전환 | LS RESTAPI 전면 전환, DB 비호환, UI/실행 구조 변경이 함께 들어 있음 |
| `trade/restapi_ls.py`, `trade/restapi_lsdata.py` | 2U_C는 Kiwoom 유지 lane이며 LS runtime 직접 채택 금지 |
| LS TR/REAL/주문체결 protocol 변경 | Kiwoom 유지 runtime과 목적이 다름 |
| Kiwoom 관련 파일 삭제 전제 | 2U_C 목표와 반대 |
| DB primary key 일괄 삽입, 거래소별 설정 분리, 기존 DB 비호환 변경 | migration spec 없이는 적용 금지 |
| V3U pyd-free 구현 | V3U 전용 산출물이며 2U_C 백포트 근거가 아님 |
| `main_window.pyd` / `ui_mainwindow.pyd` rename 또는 pyd 구조 변경 | 2U_C는 이미 pyd-to-py 추론 경계와 wrapper 계약이 별도로 존재 |
| `STOM_Version_3U_C` 생성 | 현재 전략상 보류 |
| `backtest/graph/` 산출물 | 보호 출력이며 source input 아님 |

## 5. Allowlist 후보 매트릭스

### BP-001: 백테스트 엔진 안정화

| 필드 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-001` |
| Source V3 version | V3.02, V3.03, V3.10, V3.18 중심 |
| Source commits | `3a84bb35`, `3e67661b`, `4851a36e`, `7faec937` |
| Source files | `backtest/backengine_base.py`, `backtest/backengine_base_oms.py`, `backtest/back_code_test.py`, `backtest/backtest.py`, `backtest/optimiz.py`, `backtest/rolling_walk_forward_test.py` |
| 목표 | 데이터 언패킹, 데이터 로딩, 호가단위, 분석 변수 전달, 백테스트 로그/오류 처리 중 broker-neutral 수정만 선별 |
| 적용 방식 | 파일 단위 cherry-pick 금지, 함수/조건문 단위 수동 이식 |
| Kiwoom 영향 | 중간. 2U_C에는 Kiwoom backengine과 B/S/R custom이 있으므로 공통 base 변경은 회귀 위험이 큼 |
| DB 영향 | 낮음으로 시작하되, 분석 DB 또는 schema 요구가 발견되면 즉시 보류 |
| 검증 | `python -m py_compile` 대상 파일, 기존 backtest 관련 단위 테스트, `scripts/smoke_offline_gui.py`, 2U_C custom verifier |
| 판정 | 1순위 allowlist. 단, 한 번에 하나의 오류군만 적용 |

### BP-002: 차트/DB차트/크로스헤어 안정화

| 필드 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-002` |
| Source V3 version | V3.03, V3.07, V3.08, V3.12, V3.14, V3.18 중심 |
| Source commits | `3e67661b`, `6ab5d036`, `b431be59`, `62e81349`, `f76222f8`, `7faec937` |
| Source files | V3 `ui/draw_chart/*`, `ui/event_click/*`, `ui/update_widget/*` 중 chart 관련 파일 |
| 2U_C mapping | `ui/ui_draw_chart_base.py`, `ui/ui_draw_chart_db.py`, `ui/ui_draw_chart_real.py`, `ui/ui_button_clicked_chart.py`, `ui/ui_update_textedit.py` 등 |
| 목표 | 실시간차트 인덱스/데이터 개수 불일치, x축 변환, DB차트 인자/화살표 표시, 크로스헤어 중복/레이어 오류 중 API 무관 수정 선별 |
| 적용 방식 | V3 경로 구조가 다르므로 수동 mapping 필수 |
| Kiwoom 영향 | 낮음~중간. 화면 데이터 구조가 Kiwoom tick/min 데이터와 맞는지 확인 필요 |
| DB 영향 | DB차트 query/schema 변경을 요구하면 해당 부분은 제외 |
| 검증 | chart 관련 파일 py_compile, offline GUI smoke, DB차트 호출 mock, pyd GUI contract verifier |
| 판정 | 1순위 allowlist. UI 구조 변경 자체는 제외하고 버그 수정만 추출 |

### BP-003: Binance/Upbit 안정화

| 필드 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-003` |
| Source V3 version | V3.02, V3.03, V3.08, V3.17, V3.18 중심 |
| Source commits | `3a84bb35`, `3e67661b`, `b431be59`, `f5975f4c`, `7faec937` |
| Source files | `trade/binance/*`, `trade/upbit/*`, `trade/restapi_binance.py`, `trade/restapi_upbit.py` 중 LS 무관 부분 |
| 목표 | websocket queue size, websocket 종료 속도, 최초 tick 수량/금액 계산, 주문유형 선택 방지 중 Binance/Upbit 전용 수정만 선별 |
| 적용 방식 | LS API 또는 V3 공통 receiver 구조에 묶인 부분은 제외 |
| Kiwoom 영향 | 낮음. 단, 공통 `trade/base_*` 변경이 필요하면 별도 후보로 분리 |
| DB 영향 | 낮음. 계정/주문 DB 저장 방식 변경이 나오면 제외 |
| 검증 | 해당 trade 파일 py_compile, import smoke, Binance/Upbit mock 수준 검증 |
| 판정 | 2순위 allowlist. 실거래 runtime이라 소규모 단위로만 진행 |

### BP-004: webcrawling / sound / log 소규모 안정화

| 필드 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-004` |
| Source V3 version | V3.03, V3.06, V3.16, V3.17 중심 |
| Source commits | `3e67661b`, `72b33f3f`, `66f90b1d`, `f5975f4c` |
| Source files | `utility/sub_process_and_thread/webcrawling.py`, `utility/sub_process_and_thread/chart_hoga_query*.py`, `ui/update_widget/update_textedit.py` 등 |
| 2U_C mapping | `utility/webcrawling.py`, `utility/chart_hoga_query_sound.py`, `ui/ui_update_textedit.py` |
| 목표 | 이미지/사진 웹크롤링 예외처리, 차트호가쿼리사운드 재구동 관련 불필요 처리 제거, 로그 색상 태그 필터 등 |
| 적용 방식 | 2U_C에 이미 일부 안정화가 반영된 흔적이 있으므로 중복 여부를 먼저 비교 |
| Kiwoom 영향 | 낮음 |
| DB 영향 | 없음 예상 |
| 검증 | py_compile, smoke_offline_gui, 기존 `scripts/verify_nonrelease_sync.py` 중 관련 계약 확인 |
| 판정 | 2순위 allowlist. 중복 audit 후 적용 |

### BP-005: UI 버튼 바운스 / progress 표시 개선

| 필드 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-005` |
| Source V3 version | V3.15, V3.16 중심 |
| Source commits | `bbc3fd1d`, `66f90b1d` |
| Source files | V3 `ui/create_widget/set_widget.py`, `ui/update_widget/update_progressbar.py` 등 |
| 2U_C 현황 | `ui/set_widget.py`에 `BounceButton`이 이미 존재함 |
| 목표 | 이미 반영된 기능은 no-op으로 판정하고, progressbar 개선만 별도 확인 |
| 적용 방식 | 중복 기능 재적용 금지 |
| Kiwoom 영향 | 낮음 |
| DB 영향 | 없음 |
| 검증 | UI smoke 및 pyd GUI contract verifier |
| 판정 | 기본 no-op. progressbar만 별도 후보화 가능 |

## 6. 별도 설계 트랙으로 보류할 후보

### HOLD-001: V3 분석 시스템 확장

| 필드 | 내용 |
|---|---|
| Source V3 version | V3.04 ~ V3.18 전반 |
| 포함 기능 | 캔들분석, 가격대분석, 거래량분석, 변동성분석, 변손익분석, 시장미시구조 레이더차트 |
| 보류 이유 | `strategy/` 신규 구조, 분석 DB, 설정 UI, backtest/runtime 전략연산이 서로 묶여 있음 |
| 2U_C 현황 | 시장미시구조분석 일부 흔적은 있으나 V3 분석 시스템 전체와 동일하지 않음 |
| 재개 조건 | DB migration 없는 최소 단위 설계서, Kiwoom tick/min 데이터 호환성 검증, UI 설정 영향표 작성 |
| 판정 | 지금은 코드 backport 금지. 별도 architecture/design phase 필요 |

### HOLD-002: V3 DB 구조 개선

| 필드 | 내용 |
|---|---|
| Source V3 version | V3.0, V3.08, V3.11 등 |
| 포함 기능 | 거래소별 설정 분리, DB primary key, `INSERT OR REPLACE INTO`, 분석 데이터 저장 구조 |
| 보류 이유 | 기존 2U_C DB와 비호환 가능성이 크고 사용자의 `_database` 보호 원칙과 충돌 가능 |
| 재개 조건 | DB 백업/복구 절차, migration script, rollback plan, 샘플 DB smoke 통과 |
| 판정 | 지금은 제외 |

## 7. 후보 적용 운영 규칙

1. broad merge 금지.
2. 파일 단위 cherry-pick 금지.
3. 한 commit에는 하나의 Backport ID만 담는다.
4. 적용 전 이 문서 또는 registry에 Backport ID를 명시한다.
5. 적용 중 LS API, DB migration, pyd 구조 변경이 끼어 있으면 즉시 중단하고 후보를 분리한다.
6. 2U_C의 Kiwoom 유지 custom을 삭제하거나 약화하지 않는다.
7. `backtest/graph/`, `_database`, `_log`, `*.db`는 항상 제외한다.
8. 검증 결과와 미검증 위험을 commit body 또는 update log에 남긴다.

## 8. 후보별 최소 검증 세트

공통 최소 검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short
git -C C:/System_Trading/STOM/STOM_V.wt-dev diff --check
python -m py_compile <changed-python-files>
python scripts/verify_pyd_gui_contract.py
python scripts/smoke_offline_gui.py
```

후보별 추가 검증:

| 후보 | 추가 검증 |
|---|---|
| BP-001 | backtest 관련 unit test, B/S/R custom 회귀 확인, backengine import smoke |
| BP-002 | chart/UI smoke, DB차트 호출 mock, pyd MainWindow wrapper 계약 확인 |
| BP-003 | Binance/Upbit import smoke, websocket 종료/queue 관련 mock, 실계정 호출 금지 |
| BP-004 | webcrawling timeout/cleanup mock, chart_hoga_query_sound process wrapper 확인 |
| BP-005 | UI smoke 및 기존 BounceButton 중복 여부 확인 |

## 9. 다음 실행 순서

1. Phase 11.5에서 실제 첫 백포트 대상을 하나만 고른다.
2. 가장 안전한 첫 대상은 `BP-004 webcrawling / sound / log 소규모 안정화` 또는 `BP-002 chart bugfix 중 단일 함수 수정`이다.
3. `BP-001 backtest engine`은 효과가 크지만 2U_C custom 충돌 위험이 커서 첫 적용 전 더 작은 오류군으로 쪼갠다.
4. `BP-003 Binance/Upbit`은 실거래 runtime이므로 mock 검증 준비 후 진행한다.
5. `HOLD-001`, `HOLD-002`는 설계 문서 없이 진행하지 않는다.

## 10. Phase 11.4 판정

Phase 11.4 기준으로 2U_C V3 백포트 큐는 다음 상태다.

```text
문서화 완료: yes
코드 변경: no
커밋 대상 runtime 변경: no
allowlist 후보: BP-001 ~ BP-005
보류 후보: HOLD-001 ~ HOLD-002
다음 단계: Phase 11.5 첫 적용 후보 선택 또는 no-op 종료 판정
```

## 11. Phase 11.5 최종 판정 링크

Phase 11.5 최종 판정은 `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`에 고정했다.

요약:

- 첫 적용 후보는 `BP-004`로 선택한다.
- 즉시 runtime 코드는 변경하지 않는다.
- 다음 실제 구현은 `2UC-V3-BP-004A` 시스템로그 ANSI escape 제거 또는 `2UC-V3-BP-004B` 웹크롤링 숫자 파싱 보정처럼 micro-candidate 단위로만 시작한다.
- V3 파일 단위 cherry-pick과 broad merge는 계속 금지한다.

## 12. `2UC-V3-BP-004A` 적용 기록

`2UC-V3-BP-004A`는 실제 2U_C 코드에 적용 완료되었다.

| 항목 | 내용 |
|---|---|
| 적용 commit | `e204e0f3 2U_C 시스템로그 색상 escape를 제거한다` |
| 적용 파일 | `ui/ui_update_textedit.py` |
| 적용 범위 | 시스템로그 append 직전 `ansi_escape` 정규식과 `sub` 처리 추가 |
| 제외 범위 | V3 DB관리/progressbar/종료 확인 흐름, LS API, DB migration, V3U pyd-free 변경 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 1개 확인, runtime artifact guard |

`2UC-V3-BP-004B`는 후속 micro-candidate로 진행되어 실제 2U_C 코드에 적용 완료되었다.

## 13. `2UC-V3-BP-004B` 적용 기록

`2UC-V3-BP-004B`는 실제 2U_C 코드에 적용 완료되었다.

| 항목 | 내용 |
|---|---|
| 적용 commit | `944bab37 2U_C 재무정보 숫자 파싱을 보정한다` |
| 적용 파일 | `utility/webcrawling.py` |
| 적용 범위 | `JmjpCrawling`의 재무정보 `num_list` 생성 직후 쉼표/하이픈 제거 1줄 추가 |
| 제외 범위 | V3 webcrawling 파일 전체, V3 예외처리 구조, LS API, DB migration, V3U pyd-free 변경 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 1개 확인, runtime artifact guard |

다음 BP-004 후보를 진행할 경우 `2UC-V3-BP-004C` chart_hoga_query_sound data 길이 처리부터 읽기 전용 필요성 확인을 수행한다.

## 14. `2UC-V3-BP-004C` no-op 판정 기록

`2UC-V3-BP-004C`는 읽기 전용 필요성 확인 결과 no-op으로 판정했다.

| 항목 | 내용 |
|---|---|
| 판정 | no-op |
| 2U_C 적용 commit | 없음 |
| 대상 파일 | `utility/chart_hoga_query_sound.py` |
| 근거 파일 | `ui/ui_cell_clicked.py`, `ui/ui_return_press.py`, `ui/ui_show_dialog.py` |
| V3 근거 | `3e67661b STOM V3.03` |
| no-op 사유 | 2U_C는 `coin` 인자를 포함한 7/9 chart payload를 유지하므로 V3.03의 6/8 payload 변경을 적용하면 tuple 해석이 깨질 수 있음 |
| 다음 조건 | chart payload 계약을 바꾸려면 별도 설계 문서와 producer/consumer 동시 변경 계획이 필요함 |

다음 BP-004 후보를 진행할 경우 `2UC-V3-BP-004D` DB관리/progressbar 표시 개선은 현재 보류 후보이므로, 별도 설계 없이 코드 적용하지 않는다.

## 15. `2UC-V3-BP-002A` 적용 기록

BP-002 차트 안정화 후보군의 첫 번째 micro-candidate로 `2UC-V3-BP-002A`를 실제 2U_C 코드에 적용 완료했다.

| 항목 | 내용 |
|---|---|
| 적용 commit | `f2f447d1 2U_C 차트 봉 폭 계산을 마지막 간격 기준으로 보정한다` |
| 적용 파일 | `ui/ui_draw_chart_items.py` |
| 적용 범위 | `CandlestickItem`과 `VolumeBarItem`의 width 계산 2곳을 마지막 xtick 간격 기준으로 보정 |
| V3 근거 | `f76222f8 STOM V3.14` |
| 제외 범위 | V3 draw_chart 파일 전체, radar chart, 분석 시스템 chart, chart_hoga_query 구조 변경, LS API, DB migration, V3U pyd-free 변경 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 1개 확인, runtime artifact guard |

다음 BP-002 후보를 진행할 경우 V3.03의 DB차트 인자/화살표 표시 보정 또는 실시간차트 x축 보정을 바로 적용하지 말고, 먼저 2U_C legacy chart 경로와의 mapping을 읽기 전용으로 다시 확인한다.

## 16. `2UC-V3-BP-002B` 적용 기록

BP-002 차트 안정화 후보군의 두 번째 micro-candidate로 `2UC-V3-BP-002B`를 실제 2U_C 코드에 적용 완료했다.

| 항목 | 내용 |
|---|---|
| 적용 commit | `76329b3b 2U_C DB차트 상태 초기화를 보강한다` |
| 적용 파일 | `ui/ui_draw_chart_db.py` |
| 적용 범위 | DB차트 진입 시 `self.same_code, self.same_time = False, False`로 초기화하여 이전 real chart 상태가 DB차트 full redraw 판단에 섞이지 않게 함 |
| V3 근거 | `3e67661b STOM V3.03` |
| 제외 범위 | 실시간차트 `ctpg_xticks` append 조건, 매수/매도 arrow 음수 index, V3 LS `market_gubun` routing, V3 draw_chart 파일 전체, DB migration, V3U pyd-free 변경 |
| no-op | crosshair 중복 방지 조건은 2U_C에 이미 반영되어 있어 추가 적용하지 않음 |
| hold | arrow index 음수화와 LS routing은 2U_C Kiwoom 유지 구조와 충돌 위험이 있어 보류 |
| 검증 | `python -m py_compile ui/ui_draw_chart_db.py`, `git diff --check`, `git diff --cached --check`, 변경 파일 1개 확인, runtime artifact guard |

다음 BP-002 후보를 진행할 경우 `2UC-V3-BP-002C`로 실시간차트 x축 append 조건을 검토할 수 있다. 단, `draw_line`, `draw_candle`, `draw_bar`, `len_list`의 incremental update 조건이 모두 `same_code and same_time`에 묶여 있으므로 코드 적용 전 반드시 mapping과 runtime 영향 범위를 다시 확인한다.
## 17. `2UC-V3-BP-002C` hold 판정 기록

BP-002 차트 안정화 후보군의 세 번째 micro-candidate로 V3.03 실시간차트 x축 append 조건을 검토했으나, `2UC-V3-BP-002C`는 현재 hold로 고정한다.

| 항목 | 내용 |
|---|---|
| 판정 | hold |
| 2U_C 적용 commit | 없음 |
| 대상 파일 | `ui/ui_draw_chart_real.py` |
| 관련 파일 | `ui/ui_draw_chart_base.py`, `ui/ui_draw_chart_items.py`, chart data producer 경로 |
| V3 근거 | `3e67661b STOM V3.03` |
| 적용 보류 사유 | 2U_C는 `same_code and not same_time`에서 full redraw 경로를 사용하므로, V3처럼 x축만 append하면 `ctpg_xticks`와 `ctpg_arry` 길이/캐시 상태가 불명확해질 수 있음 |
| 제외 범위 | 실시간차트 `ctpg_xticks` 조건 변경, draw 계열 incremental 조건 변경, chart data producer 계약 변경, LS routing 변경 |
| 재검토 조건 | 2U_C GUI 실시간차트 runtime 재현 또는 chart state 계약 설계 후 적용 후보를 새 micro-candidate로 분리 |
| 검증 | V3 HEAD 확인, 2U_C `same_code/same_time` drawing 조건 확인, chart producer 경로 grep, 상태 guard |

다음 BP-002 후보를 진행할 경우 BP-002C를 즉시 코드 적용 대상으로 되돌리지 말고, 먼저 `ctpg_arry`가 rolling window인지 append-only인지 runtime evidence를 확보한다.