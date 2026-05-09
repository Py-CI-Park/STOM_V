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
## 18. `2UC-V3-BP-005A` 선정 기록

재정렬 Page 3/4 결과 `2UC-V3-BP-005A`를 다음 safe micro-candidate로 선정했다. 이 기록은 실제 runtime 코드 적용이 아니라, 다음 적용 cycle을 시작하기 위한 공식 후보 등록이다.

| 항목 | 내용 |
|---|---|
| 선정 후보 | `2UC-V3-BP-005A` |
| 상위 후보 | `2UC-V3-BP-005` UI 버튼 바운스 / progress 표시 개선 |
| V3 근거 | `66f90b1d STOM V3.16`, `ui/update_widget/update_progressbar.py` |
| 2U_C 대상 | `ui/ui_update_progressbar.py` |
| 후보 범위 | `setRange()` 후 `setValue()` 순서 보정, 경과/남은 시간 표시를 `str(... )[:-3]` 형식으로 축약 |
| 2U_C 보정점 | 2U_C에는 `ss_progressBar_01`과 `cs_progressBar_01` 분기가 모두 있으므로 적용 시 stock/coin 양쪽을 일관되게 검토 |
| no-op | `BounceButton`은 2U_C `ui/set_widget.py`에 이미 존재하므로 재적용하지 않음 |
| 제외 범위 | DB관리 다이얼로그 progressbar 추가, 분석 시스템 progressbar, BounceButton 재적용, LS/API/DB/pyd 관련 변경 |
| 다음 단계 | 별도 `2UC-V3-BP-005A` 적용 cycle에서 read-only diff 확인 후 최소 patch 여부 결정 |

`2UC-V3-BP-005A`는 broker-neutral / DB-neutral / pyd-neutral 성격의 UI 표시 보정 후보로만 취급한다. 코드 적용 시에는 `ui/ui_update_progressbar.py` 단일 파일 변경을 원칙으로 하며, 적용 전후 `py_compile`, `git diff --check`, 변경 파일 guard를 통과해야 한다.

## 19. `2UC-V3-BP-005A` 적용 완료 기록

`2UC-V3-BP-005A`는 후속 적용 cycle Page 1~3에서 read-only 확인, 최소 patch 결정, 실제 적용 및 검증을 완료했다. 이 기록은 Page 4 공식 추적 문서 반영 단계이며, runtime code 변경은 이미 `STOM_Version_2U_C`의 별도 commit으로 고정했다.

| 항목 | 내용 |
|---|---|
| 적용 상태 | 완료 |
| 적용 branch | `STOM_Version_2U_C` |
| 적용 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 적용 commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| V3 근거 | `66f90b1d STOM V3.16`, `ui/update_widget/update_progressbar.py` |
| 적용 파일 | `.gitignore`, `ui/ui_update_progressbar.py` |
| 적용 범위 | progressbar `setRange()` / `setValue()` 호출 순서 보정, 경과/남은 시간 표시를 `str(... )[:-3]` 형식으로 단축 |
| 2U_C 보정 | V3 diff의 stock 중심 변경을 2U_C의 stock/coin 분기(`ss_progressBar_01`, `cs_progressBar_01`)에 일관되게 수동 이식 |
| `.gitignore` 보강 | `backtest/graph/` runtime graph 산출물을 stage하지 않도록 보호 규칙 추가 |
| 제외 범위 | BounceButton 재적용, DB관리 다이얼로그 progressbar, 분석 시스템 progressbar, LS/API/DB/pyd 변경 |
| 검증 | `py_compile`, `git diff --check`, `git diff --cached --check`, root/2U_C `verify_release_sync.py` 통과 |

`2UC-V3-BP-005A`는 V3 파일 단위 cherry-pick이 아니라 2U_C 구조에 맞춘 최소 수동 이식으로 완료했다. 후속 BP-001/BP-003 재평가는 BP-005A final guard 이후 별도 read-only cycle에서 다시 판단한다.

## 20. `2UC-V3-BP-005A` final guard 완료 기록

`2UC-V3-BP-005A`는 Page 5 final guard에서 root와 2U_C 상태, release sync, runtime artifact guard, `STOM_Version_3U_C` 미생성 원칙을 최종 확인하고 종료한다.

| 항목 | final guard 결과 |
|---|---|
| 최종 상태 | 완료 |
| 2U_C code commit | `f942ed2f BP-005A 프로그레스바 표시 보정을 적용한다` |
| root 추적 commit | `e5f10e19 BP-005A Page 4 공식 추적을 완료한다` 이후 Page 5 final guard commit |
| 2U_C mirror commit | `97221a2a BP-005A Page 4 상태를 2U_C 미러에 남긴다` 이후 Page 5 mirror commit |
| status guard | root clean, 2U_C clean |
| release sync | root/2U_C 모두 `release sync preflight passed` |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| 3U_C guard | `STOM_Version_3U_C` branch 없음 |
| 다음 후보 | BP-001/BP-003은 별도 read-only 재평가 cycle 전까지 후순위 조건부 유지 |

이 final guard로 BP-005A는 공식 allowlist 상 완료 항목으로 닫는다. 후속 후보는 broad merge가 아니라 다시 micro-candidate 단위로만 재개한다.

## 21. `2UC-V3-BP-001` / `2UC-V3-BP-003` read-only 재평가 Page 1 기록

BP-005A final guard 이후 남은 큰 후보인 BP-001/BP-003을 바로 적용하지 않고, 먼저 read-only로 기존 판정과 V3 diff 규모를 재확인했다. 이 기록은 새 적용이 아니라 다음 Page 2 판단을 위한 근거 고정이다.

| 항목 | 내용 |
|---|---|
| cycle | BP-001/BP-003 read-only 재평가 cycle Page 1 / 5 |
| 코드 변경 | 없음 |
| OMX 경로 | `omx explore` 시도 후 Windows harness 미준비로 실패, `omx sparkshell`로 fallback |
| BP-001 근거 | V3 `backtest/` diff가 25 files, 1228 insertions, 1341 deletions로 넓고 V3.02~V3.18 전반에 걸침 |
| BP-001 판정 | hold 우세 유지, 2U_C B/S/R custom과 legacy parity 보정 충돌 위험 때문에 broad merge 금지 |
| BP-003 근거 | V3 trade diff가 8 files, 275 insertions, 374 deletions이며 V3 receiver/restapi 구조와 2U_C min/tick/websocket 구조가 다름 |
| BP-003 판정 | 조건부 유지, Page 2에서 mock 가능한 단일 조건 후보만 분리 검토 |
| 다음 단계 | BP-001 hold 유지 확정과 BP-003 micro-candidate 분리 가능성 판단 |

Page 2에서도 V3 파일 단위 cherry-pick은 금지한다. 특히 root `trade/restapi_binance.py` / `trade/restapi_upbit.py` 전체 이식, V3 `binance_receiver.py` / `upbit_receiver.py` 직접 이식, 실거래 API 호출 순서 변경은 별도 테스트 설계 없이는 적용하지 않는다.

## 22. `2UC-V3-BP-001` / `2UC-V3-BP-003` read-only 재평가 Page 2 판단 기록

Page 2에서는 BP-001 hold 유지 여부와 BP-003 micro-candidate 분리 가능성을 판단했다. 이 단계에서도 runtime code는 변경하지 않았다.

| 항목 | 내용 |
|---|---|
| cycle | BP-001/BP-003 read-only 재평가 cycle Page 2 / 5 |
| 코드 변경 | 없음 |
| BP-001 판단 | hold 확정. V3 backtest 변경 범위가 넓고 2U_C custom backtest 구조와 충돌 가능성이 큼 |
| BP-003 판단 | 이번 cycle에서 적용 후보 미선정. V3 receiver/restapi/trader 변경이 2U_C min/tick/websocket 구조와 맞지 않음 |
| 검토한 후보 | trader 주문 처리, websocket reconnect/close, Upbit 인증 header, REST API 변경 |
| 제외 사유 | 각 후보가 V3 `UI_NUM`/BaseTrader/MonitorTraderQ 구조, root REST 파일 구조, 실거래 websocket 연결 흐름과 묶여 있음 |
| 다음 단계 | Page 3에서 BP-001 hold 확정과 BP-003 미선정/hold 사유를 공식 기록으로 닫음 |

향후 BP-003을 재개하려면 V3 파일 단위가 아니라 2U_C 파일 기준으로 더 작은 후보 ID를 새로 만든다. 예: `websocket close guard`, `REST 응답 예외 처리`, `주문 실패 로그 보정`처럼 mock test가 가능한 단일 조건이어야 한다.

## 23. `2UC-V3-BP-001` / `2UC-V3-BP-003` hold 공식 기록

Page 3에서는 Page 2 판단을 공식 hold 기록으로 고정했다. 이 기록은 적용 포기가 아니라, 현재 V3 diff 단위가 2U_C 안전 적용 단위보다 넓기 때문에 다음 후보를 새 ID로 재분리하기 전까지 적용하지 않는다는 의미다.

| 항목 | 내용 |
|---|---|
| cycle | BP-001/BP-003 read-only 재평가 cycle Page 3 / 5 |
| 코드 변경 | 없음 |
| `2UC-V3-BP-001` | hold 확정 |
| BP-001 hold 사유 | V3 backtest 변경이 25 files 규모이고 2U_C B/S/R custom 및 legacy parity 보정과 충돌 가능성이 큼 |
| `2UC-V3-BP-003` | 이번 cycle 적용 후보 미선정 / hold |
| BP-003 hold 사유 | V3 receiver/strategy/trader/REST API 변경이 한 묶음이며 2U_C min/tick/websocket 구조와 1:1 대응하지 않음 |
| 재개 조건 | 2U_C 파일 기준의 mock 가능한 단일 조건 후보 ID가 있을 때만 새 cycle로 재개 |
| 다음 단계 | Page 4에서 root 문서와 2U_C mirror checkpoint 동기화 검증 |

BP-003의 미래 후보 예시는 `websocket close guard`, `REST 응답 예외 처리`, `주문 실패 로그 보정`이다. 단, 이 예시들도 실제 적용 전에는 별도 read-only Page 1부터 새 cycle로 시작한다.

## 24. `2UC-V3-BP-001` / `2UC-V3-BP-003` 문서 동기화 검증 기록

Page 4에서는 Page 3 hold 공식 기록이 root 공식 문서와 2U_C mirror checkpoint에 일관되게 반영되었는지 확인했다. 이 단계도 runtime code를 변경하지 않았다.

| 항목 | 내용 |
|---|---|
| cycle | BP-001/BP-003 read-only 재평가 cycle Page 4 / 5 |
| 코드 변경 | 없음 |
| root 공식 문서 | checkpoint, allowlist, Phase 11 decision 모두 BP-001 hold / BP-003 hold 결론 포함 |
| 2U_C mirror | Page 4 시작 시점 root checkpoint와 2U_C checkpoint SHA256 hash 일치 |
| 동기화 결론 | 일치 |
| 다음 단계 | Page 5 final guard에서 release sync, runtime artifact guard, 3U_C 미생성 원칙 확인 |

이 기록 이후에도 BP-001/BP-003 결론은 변경하지 않는다. Page 5는 final guard와 다음 handoff 안내만 수행한다.

## 25. `2UC-V3-BP-001` / `2UC-V3-BP-003` final guard 완료 기록

Page 5 final guard에서 BP-001/BP-003 read-only 재평가 cycle을 hold 완료 상태로 닫았다. 이 단계에서도 runtime code는 변경하지 않았다.

| 항목 | 내용 |
|---|---|
| cycle | BP-001/BP-003 read-only 재평가 cycle Page 5 / 5 |
| 최종 상태 | hold 완료 |
| `2UC-V3-BP-001` | hold 확정 |
| `2UC-V3-BP-003` | 이번 cycle 적용 후보 미선정 / hold |
| release sync | root/2U_C 모두 `release sync preflight passed` |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| 3U_C guard | `STOM_Version_3U_C` branch 없음 |
| 재개 조건 | 새 후보 ID와 새 read-only cycle 없이는 재개하지 않음 |

이 final guard로 BP-001/BP-003 재평가 cycle은 종료한다. 다음 안전한 기본값은 전체 handoff 점검이며, 새 코드 적용은 별도 후보 ID가 준비될 때만 시작한다.

## 26. `2UC-V3-BP-006A` 적용 완료 및 Page 4 문서 동기화 기록

`2UC-V3-BP-006A`는 V3 `strategy/analyzer_risk.py`를 2U_C에 runtime wiring 없는 dormant module로 보존하는 후보이다. 이 기록은 Page 4 공식 문서 동기화 단계이며, runtime code 변경은 이미 `STOM_Version_2U_C`의 별도 code commit으로 고정했다.

| 항목 | 내용 |
|---|---|
| cycle | `2UC-V3-BP-006A` Page 4 / 5 |
| source version | `STOM V3.18` |
| source file | `strategy/analyzer_risk.py` |
| source blob | `d1f73368fb5ce82f5549a4b69eccd85f4c30f81d` |
| target files | `strategy/__init__.py`, `strategy/analyzer_risk.py` |
| 적용 성격 | dormant module 보존 |
| 2U_C code commit | `15467b43 BP-006A risk analyzer를 dormant module로 보존한다` |
| 2U_C whitespace fix commit | `0ea00ea4 BP-006A risk analyzer의 diff check 공백을 보정한다` |
| root Page 3 문서 commit | `7aee8a52 BP-006A Page 3 적용 결과를 공식 checkpoint로 남긴다` |
| 2U_C Page 3 mirror commit | `8234a84d BP-006A Page 3 적용 기록을 2U_C에 미러링한다` |
| 검증 | `py_compile`, `git diff --check`, `verify_release_sync.py --root STOM_V.wt-dev` 통과 |
| runtime wiring | 없음 / 별도 후보 ID와 test spec 없이는 금지 |
| 다음 단계 | Page 5 final guard |

적용 완료의 의미는 `strategy/analyzer_risk.py`가 2U_C repo에 보존되었다는 뜻이다. 기존 `research/analyzer/risk_analyzer.py`, `trade/*`, GUI, DB, LS/Kiwoom API 흐름에는 연결하지 않았다.

BP-006A 후속 작업에서 runtime 연결을 검토하려면 새 후보 ID를 부여하고, 호출 지점, `dict_findex` mapping, array shape, mock 가능한 test spec을 별도 Page 1부터 다시 기록해야 한다.
## 27. `2UC-V3-BP-006A` final guard 완료 기록

`2UC-V3-BP-006A`는 Page 5 final guard에서 root와 2U_C 상태, py_compile, release sync, runtime artifact guard, `STOM_Version_3U_C` 미생성 원칙을 최종 확인하고 종료한다.

| 항목 | 내용 |
|---|---|
| cycle | `2UC-V3-BP-006A` Page 5 / 5 |
| 최종 상태 | 완료 |
| 적용 의미 | dormant module 보존 완료 |
| runtime wiring | 없음 / 별도 후보 ID 없이는 금지 |
| 2U_C code commit | `15467b43 BP-006A risk analyzer를 dormant module로 보존한다` |
| 2U_C whitespace fix commit | `0ea00ea4 BP-006A risk analyzer의 diff check 공백을 보정한다` |
| Page 4 root commit | `f1b43ac8 BP-006A Page 4 공식 동기화로 적용 추적을 고정한다` |
| Page 4 2U_C mirror commit | `f3e5840e BP-006A Page 4 동기화 상태를 2U_C에 미러링한다` |
| py_compile | `strategy/analyzer_risk.py` passed |
| release sync | root/2U_C 모두 `release sync preflight passed` |
| runtime artifact guard | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| 3U_C guard | `STOM_Version_3U_C` branch 없음 |
| 확장 진행률 | `61 / 61 page`, 100.0% |
| 다음 처리 | 종료 / handoff 유지 또는 새 후보 ID 기반 별도 cycle |

이 final guard로 BP-006A는 공식 allowlist 상 완료 항목으로 닫는다. `AnalyzerRisk` runtime 연결은 이 cycle의 범위가 아니며, 호출 지점과 test spec을 갖춘 별도 후보 ID 없이는 시작하지 않는다.

## 28. V3 -> 2U_C no-more-safe-candidates closure

BP-006A final guard 이후 `STOM_Version_3`와 `STOM_Version_2U_C`의 남은 diff를 다시 조사했다. 결론은 새로 열 수 있는 안전한 Kiwoom 호환 micro-candidate가 없다는 것이다. 상세 handoff는 `docs/update_log/2026-05-07_v3_2uc_no_more_safe_candidates_handoff.md`에 남겼다.

```text
이전 baseline        [####################] 100.0%  61 / 61 page
no-more closure      [####################] 100.0%   1 /  1 page
전체 확장 진행률     [####################] 100.0%  62 / 62 page
현재 page            [####################] 100.0%   1 /  1 page
남은 page            [--------------------]   0.0%   0 /  0 page
```

| 항목 | 판정 |
|---|---|
| `2UC-V3-BP-007A` | 미개시 / gate 통과 후보 없음 |
| BP-002/BP-004 잔여 | 이전 판단 유지, BP-002C hold와 BP-004C no-op 유지 |
| sound split 잔여 | `pyttsx_sound.py` 추가만으로는 process/thread wiring 경계가 함께 움직여 안전한 micro-candidate가 아님 |
| strategy analyzer runtime wiring | DB/settings/runtime wiring 필요, HOLD-001 또는 별도 BP-ID 없이는 시작하지 않음 |
| dashboard/CLI/research/tests | 현재 2U_C Kiwoom runtime에 직접 반영할 기능 후보가 아님 |
| 남은 queue | 제외/보류/no-op 항목뿐이므로 추가 safe candidate 없음 |

추천 OMX 검증:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev"
```

## 29. `2UC-V3-BP-007A` application record

`2UC-V3-BP-007A` was opened during the 2026-05-07 re-audit after the previous 62/62 no-more baseline. The candidate is intentionally limited to the existing 2U_C `utility/timesync.py` file.

```text
total progress       [####################]  98.5%  66 / 67 pages
BP-007A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

| Item | Value |
|---|---|
| Status | applied in 2U_C |
| Source V3 versions | `STOM V3.0`, `STOM V3.11` |
| Source commits | `06b70418`, `dbab03b3` |
| Source path | `utility/sub_process_and_thread/timesync.py` |
| Target path | `utility/timesync.py` |
| 2U_C code commit | `61e12951 BP-007A timesync log correction applied` |
| Applied scope | docstring, local `dateutil.tz` removal, `astimezone()`, Korean queue logs, `except Exception` |
| Kiwoom adjustment | preserved the 2U_C `utility.timesync` import path and `utility.static.thread_decorator` |
| Excluded scope | V3 file move, `utility.static_method` split, settings/DB split, LS API, dashboard/CLI/test broad changes, pyd/UI restructuring |
| Verification | `py_compile`, isolated mock, `git diff --check`, `git diff --cached --check` |
| Remaining risk | live NTP/SystemTime behavior not exercised in this offline pass |

## 30. `2UC-V3-BP-007A` final guard

```text
total progress       [####################] 100.0%  67 / 67 pages
BP-007A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Next OMX command:

```powershell
omx cancel
```

Final guard passed for `2UC-V3-BP-007A`.

| Guard | Result |
|---|---|
| root status | clean |
| 2U_C status | clean |
| py_compile | passed for `utility/timesync.py` |
| release sync | passed for root and 2U_C |
| forbidden runtime artifacts | none tracked |
| `STOM_Version_3U_C` | absent |
| remaining candidate queue | no additional safe micro-candidate opened |


## 31. `2UC-V3-BP-008A` application record

`2UC-V3-BP-008A` was opened after BP-007A final guard because the fresh post-BP-007A inventory found one smaller residual V3.11 dependency-cleanup sub-candidate in `utility/static.py`. This supersedes only the narrow `pytz` bootstrap residue; the broad no-more/hold conclusions remain in effect for LS API, DB migration, pyd/UI, static_method split, trade/backtest/dashboard/CLI/test broad changes, sound/process wiring, and AnalyzerRisk runtime wiring.

```text
total progress       [####################]  98.6%  71 / 72 pages
BP-008A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

| Item | Value |
|---|---|
| Status | applied in 2U_C |
| Source V3 version | `STOM V3.11` |
| Source commit | `dbab03b3` |
| Source path | `utility/static_method/static_datetime.py` |
| Target path | `utility/static.py` |
| 2U_C code commit | `6e4c10a0 BP-008A static timezone dependency? ????` |
| Applied scope | replace `pytz` UTC/CME bootstrap with `datetime.timezone.utc` and `zoneinfo.ZoneInfo` |
| Kiwoom adjustment | preserved the existing 2U_C `utility.static` path and all exported names |
| Excluded scope | V3 static module split, telegram bot timezone cleanup, requirements cleanup, LS API, DB migration, pyd/UI restructuring |
| Verification | `py_compile`, DST equivalence mock, `git diff --check`, `git diff --cached --check` |
| Remaining risk | full GUI/runtime launch not exercised in this offline pass |


## 32. `2UC-V3-BP-008A` final guard

```text
total progress       [####################] 100.0%  72 / 72 pages
BP-008A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Next OMX command:

```powershell
omx cancel
```

Final guard passed for `2UC-V3-BP-008A`.

| Guard | Result |
|---|---|
| root status | clean before Page 5 doc append |
| 2U_C status | clean before Page 5 doc append |
| py_compile | passed for `utility/static.py` |
| release sync | passed for root and 2U_C |
| forbidden runtime artifacts | none tracked |
| `STOM_Version_3U_C` | absent |
| remaining candidate queue | no additional safe micro-candidate opened after BP-008A |

`2UC-V3-BP-008A` is closed as completed. Future timezone/dependency cleanup beyond `utility/static.py` requires a new BP-ID and separate Page 1 inventory.
