# 2U_C V3 backport Phase 11 최종 판정

작성일: 2026-05-06
대상 root: `C:/System_Trading/STOM/STOM_V`
대상 custom worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`
상위 문서:

- `docs/update_log/2026-05-06_2uc_v3_backport_queue_start.md`
- `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`

## 1. 목적

이 문서는 V3 전환 계획의 마지막 페이지였던 Phase 11, 즉 `2U_C V3 backport queue`의 첫 실행 방향을 확정한다.

Phase 11은 실제 V3 기능을 2U_C에 무조건 적용하는 단계가 아니라, `STOM_Version_2U_C`가 V2/Kiwoom 유지 custom lane이라는 전제를 지키면서 V3의 broker-neutral 개선만 안전하게 선별할 수 있는지 판정하는 단계다.

## 2. 현재 상태

| 항목 | 상태 |
|---|---|
| root HEAD | `96049642 2U_C V3 백포트 후보 allowlist를 고정한다` |
| root status | clean |
| 2U_C status | 기존 보호 출력 `?? backtest/graph/`만 존재 |
| V3 source 범위 | `STOM V3.0` ~ `STOM V3.18` |
| V3U 상태 | pyd-free 완료 |
| 3U_C | 생성하지 않음 |
| 이번 단계 runtime 코드 변경 | 없음 |

## 3. 직접 실행한 Phase 11.5 명령

상태 확인:

```powershell
omx sparkshell powershell -NoProfile -Command "git -C C:\System_Trading\STOM\STOM_V log -1 --oneline; git -C C:\System_Trading\STOM\STOM_V status --short; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short"
```

BP-004 후보 source 확인:

```powershell
omx sparkshell powershell -NoProfile -Command "git -C C:\System_Trading\STOM\STOM_V.wt-3 show --name-only --oneline 3e67661b 72b33f3f 66f90b1d f5975f4c -- utility/sub_process_and_thread/webcrawling.py utility/sub_process_and_thread/chart_hoga_query_sound.py ui/update_widget/update_textedit.py; git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short"
```

추가 로컬 읽기 전용 확인:

- V3 BP-004 관련 commit별 patch 통계 확인
- V3 최종 파일과 2U_C mapping 파일의 class/function/keyword 차이 확인
- 2U_C mapping 파일 `py_compile` 확인

## 4. BP-004 검토 결과

BP-004는 `webcrawling / sound / log 소규모 안정화` 후보였고, 다음 V3 commit에서 관련 변경이 확인되었다.

| V3 commit | 관련 파일 | 요약 |
|---|---|---|
| `3e67661b` V3.03 | `ui/update_widget/update_textedit.py`, `utility/sub_process_and_thread/chart_hoga_query_sound.py`, `utility/sub_process_and_thread/webcrawling.py` | ANSI 색상 코드 제거, chart/hoga data 길이 처리, 웹크롤링 예외/파싱 보정 |
| `72b33f3f` V3.06 | `ui/update_widget/update_textedit.py`, `utility/sub_process_and_thread/chart_hoga_query_sound.py` | DB관리/로그 흐름 재구성, 차트호가쿼리사운드 관련 변경 |
| `66f90b1d` V3.16 | `ui/update_widget/update_textedit.py` | 학습/DB관리 진행률 표시 개선 |
| `f5975f4c` V3.17 | `ui/update_widget/update_textedit.py`, `utility/sub_process_and_thread/webcrawling.py` | 종료 확인 흐름, 재무정보 웹크롤링 파싱 보정 |

## 5. 2U_C와의 mapping 결과

| V3 source | 2U_C target | 판정 |
|---|---|---|
| `utility/sub_process_and_thread/webcrawling.py` | `utility/webcrawling.py` | 2U_C에는 이미 `request_timeout`, `treemap_timer.cancel()`, `wait(2000)` 등 V3보다 강한 custom hardening이 있음 |
| `utility/sub_process_and_thread/chart_hoga_query_sound.py` | `utility/chart_hoga_query_sound.py` | V3 final에는 동일 경로가 없고, 2U_C는 legacy path와 Kiwoom/coin 구조를 유지함 |
| `ui/update_widget/update_textedit.py` | `ui/ui_update_textedit.py` | V3는 `UI_NUM`, 신규 DB관리/progress/분석 시스템 구조를 전제로 하며 2U_C와 직접 호환되지 않음 |

따라서 BP-004는 후보 자체는 유효하지만, 파일 단위 적용이나 broad cherry-pick은 금지한다.

## 6. Phase 11.5 최종 판정

```text
첫 적용 후보: BP-004
즉시 코드 적용: no
판정 유형: 선택 후 보류(no runtime change)
이유: V3와 2U_C의 파일 구조 및 runtime 전제가 달라 바로 적용하면 회귀 위험이 큼
권장 다음 작업: BP-004를 더 작은 micro-candidate로 분리
```

Phase 11.5 기준으로 실제 코드 변경은 하지 않는다. 대신 다음 사이클의 첫 구현 후보를 아래처럼 제한한다.

| Micro ID | 설명 | 우선순위 | 조건 |
|---|---|---|---|
| `2UC-V3-BP-004A` | 시스템로그 ANSI escape 제거만 검토 | 1 | 2U_C 시스템로그에 색상 escape가 실제 유입되는지 재현 후 적용 |
| `2UC-V3-BP-004B` | 재무정보/웹크롤링 숫자 파싱 보정만 검토 | 2 | 현재 2U_C 파싱과 V3 파싱 차이를 unit 또는 sample HTML로 검증 후 적용 |
| `2UC-V3-BP-004C` | chart_hoga_query_sound data 길이 처리만 검토 | 3 | 2U_C queue payload 계약을 먼저 문서화한 뒤 적용 |
| `2UC-V3-BP-004D` | DB관리/progressbar 표시 개선 | 보류 | V3 DB관리/분석 시스템 전제가 섞여 있어 별도 설계 필요 |
| `2UC-V3-BP-004E` | 프로그램 종료 확인 흐름 | 보류 | V3 LS receiver 종료 흐름과 섞여 있어 Kiwoom 유지 종료 계약 재검토 필요 |

## 7. 완료 기준

Phase 11은 다음 기준으로 완료한다.

- V3/V3U 전환 결과는 유지한다.
- 2U_C는 V2/Kiwoom 유지 custom lane으로 유지한다.
- V3 백포트는 문서화된 Backport ID 없이는 의도된 차이로 취급하지 않는다.
- 실제 첫 구현은 `2UC-V3-BP-004A` 또는 `2UC-V3-BP-004B`처럼 micro-candidate 단위로만 시작한다.
- LS API, DB migration, V3U pyd-free 변경, `STOM_Version_3U_C` 생성은 계속 제외한다.

## 8. 다음 권장 명령

Phase 11 계획은 여기서 닫고, 다음 실제 개발 사이클을 시작할 때는 아래처럼 micro-candidate 하나만 선택한다.

```powershell
omx sparkshell powershell -NoProfile -Command "git -C C:\System_Trading\STOM\STOM_V.wt-dev grep -n -e 'Traceback' -e 'Error' -e '시스템로그' -e 'x1B' -- ui/ui_update_textedit.py; git -C C:\System_Trading\STOM\STOM_V.wt-3 show --unified=3 3e67661b -- ui/update_widget/update_textedit.py"
```

이 명령은 `2UC-V3-BP-004A` 시스템로그 ANSI escape 제거가 실제로 필요한지 확인하는 읽기 전용 진입 명령이다.

## 9. Phase 11 이후 첫 micro-candidate 실행 기록

Phase 11 종료 후 첫 실제 2U_C micro-candidate로 `2UC-V3-BP-004A`를 적용했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-004A` |
| 적용 branch | `STOM_Version_2U_C` |
| 적용 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 적용 commit | `e204e0f3 2U_C 시스템로그 색상 escape를 제거한다` |
| 변경 파일 | `ui/ui_update_textedit.py` |
| 변경 범위 | 시스템로그 append 직전 ANSI escape 제거 2줄 |
| V3 근거 | `3e67661b STOM V3.03`, “python 3.13 오류 로그에 색상 코드 제거” |
| 적용 방식 | V3 파일 단위 적용이 아니라 2U_C legacy 경로에 수동 최소 이식 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 guard, runtime artifact guard, `STOM_Version_3U_C` 부재 확인 |
| 남은 상태 | 2U_C에는 기존 보호 출력 `?? backtest/graph/`만 남아 있음 |

이 적용은 Phase 11의 원칙을 따른 첫 사례다. 즉, V3 기능을 broad merge하지 않고 문서화된 Backport ID의 micro-candidate 단위로만 2U_C에 반영했다.

## 10. Phase 11 이후 두 번째 micro-candidate 실행 기록

두 번째 실제 2U_C micro-candidate로 `2UC-V3-BP-004B`를 적용했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-004B` |
| 적용 branch | `STOM_Version_2U_C` |
| 적용 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 적용 commit | `944bab37 2U_C 재무정보 숫자 파싱을 보정한다` |
| 변경 파일 | `utility/webcrawling.py` |
| 변경 범위 | 재무정보 `num_list` 생성 직후 쉼표/하이픈 제거 1줄 |
| V3 근거 | `f5975f4c STOM V3.17`, “재무정보 웹크롤링 오류 수정” 및 `7faec937 STOM V3.18` 최종 형태 |
| 적용 방식 | V3 파일 단위 적용이 아니라 2U_C legacy `JmjpCrawling` 경로에 수동 최소 이식 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 guard, runtime artifact guard, `STOM_Version_3U_C` 부재 확인 |
| 남은 상태 | 2U_C에는 기존 보호 출력 `?? backtest/graph/`만 남아 있음 |

이 적용도 Phase 11의 원칙을 유지했다. 즉, V3 `webcrawling.py` 전체를 가져오지 않고 재무정보 숫자 파싱 보정 1줄만 micro-candidate 단위로 2U_C에 반영했다.

## 11. Phase 11 이후 세 번째 micro-candidate 판정 기록

세 번째 2U_C micro-candidate로 `2UC-V3-BP-004C`를 검토했으나, runtime 코드는 변경하지 않는 no-op으로 판정했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-004C` |
| 대상 branch | `STOM_Version_2U_C` |
| 대상 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 판정 | no-op |
| 2U_C 변경 commit | 없음 |
| 검토 파일 | `utility/chart_hoga_query_sound.py`, `ui/ui_cell_clicked.py`, `ui/ui_return_press.py`, `ui/ui_show_dialog.py` |
| V3 근거 | `3e67661b STOM V3.03`의 chart data 길이 처리 변경 |
| no-op 사유 | 2U_C producer는 `coin` 인자를 포함한 7/9 payload를 유지하지만, V3.03 변경은 `coin` 인자 제거 후의 6/8 payload를 전제로 함 |
| 확인 근거 | `ui/ui_cell_clicked.py`, `ui/ui_return_press.py`, `ui/ui_show_dialog.py`가 `(coin, code, ...)` tuple을 만들고, `utility/chart_hoga_query_sound.py`가 `len(data) == 7` / `len(data) == 9`로 분기함 |
| 제외 범위 | V3 chart_hoga_query 파일 rename, V3 최종 8/10 payload 구조, 분석 시스템 인자, LS/DB/V3U 관련 변경 |

이 판정은 2U_C의 legacy chart payload 계약을 보존하기 위한 것이다. `2UC-V3-BP-004C`를 코드로 적용하려면 먼저 2U_C chart payload 계약 자체를 변경하는 별도 설계가 필요하다.

## 12. BP-002 첫 번째 micro-candidate 실행 기록

BP-004 계열 완료 후 다음 후보군인 BP-002 차트 안정화에서 첫 번째 2U_C micro-candidate로 `2UC-V3-BP-002A`를 적용했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-002A` |
| 적용 branch | `STOM_Version_2U_C` |
| 적용 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 적용 commit | `f2f447d1 2U_C 차트 봉 폭 계산을 마지막 간격 기준으로 보정한다` |
| 변경 파일 | `ui/ui_draw_chart_items.py` |
| 변경 범위 | `CandlestickItem`과 `VolumeBarItem`의 폭 계산에서 두 번째 interval 기준을 `xticks[2] - xticks[1]`에서 `xticks[-1] - xticks[-2]`로 변경 |
| V3 근거 | `f76222f8 STOM V3.14`, candlestick / volume bar 폭 계산 보정 |
| 적용 방식 | V3 `draw_chart` 파일 단위 적용이 아니라 2U_C legacy chart item 파일에 수동 최소 이식 |
| 검증 | `py_compile`, `git diff --check`, 변경 파일 guard, runtime artifact guard, `STOM_Version_3U_C` 부재 확인 |
| 남은 상태 | 2U_C에는 기존 보호 출력 `?? backtest/graph/`만 남아 있음 |

이 적용은 BP-002도 broad merge가 아니라 micro-candidate 단위로만 진행한다는 기준을 세운 첫 사례다. V3의 radar chart, 분석 시스템 chart, chart_hoga_query 구조 변경은 함께 가져오지 않았다.

## 13. BP-002 두 번째 micro-candidate 실행 기록

`2UC-V3-BP-002B`는 V3.03 chart 변경 중 2U_C Kiwoom 유지 구조와 충돌하지 않는 DB차트 상태 초기화 보정만 선별 적용했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-002B` |
| 적용 branch | `STOM_Version_2U_C` |
| 적용 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 적용 commit | `76329b3b 2U_C DB차트 상태 초기화를 보강한다` |
| 변경 파일 | `ui/ui_draw_chart_db.py` |
| 변경 범위 | DB차트 진입 시 `same_time`뿐 아니라 `same_code`도 함께 `False`로 초기화 |
| V3 근거 | `3e67661b STOM V3.03`, DB차트 표시용 상태 초기화 보정 |
| no-op 판정 | crosshair 중복 방지 조건은 2U_C에 이미 존재하므로 추가 변경 없음 |
| hold 판정 | 실시간차트 `ctpg_xticks` append 조건, 매수/매도 arrow 음수 index, LS `market_gubun` routing은 즉시 반영하지 않음 |
| 검증 | `python -m py_compile ui/ui_draw_chart_db.py`, `git diff --check`, `git diff --cached --check`, 변경 파일 guard |
| 남은 상태 | 2U_C에는 기존 보호 출력 `?? backtest/graph/`만 남아 있음 |

이 적용은 V3.03 chart 변경을 전체 병합한 것이 아니라, DB차트 stale `same_code` 가능성을 제거하는 safe micro-candidate만 반영한 것이다. 다음 BP-002 후보는 실시간차트 x축 보정 여부를 다시 읽기 전용으로 검토한 뒤 별도 micro-candidate로 분리한다.
## 14. BP-002 세 번째 micro-candidate hold 판정 기록

`2UC-V3-BP-002C`는 V3.03의 실시간차트 x축 append 조건 변경을 2U_C에 적용할 수 있는지 검토했으나, 현재 단계에서는 runtime 코드를 변경하지 않고 hold로 판정했다.

| 항목 | 내용 |
|---|---|
| Micro ID | `2UC-V3-BP-002C` |
| 대상 branch | `STOM_Version_2U_C` |
| 대상 worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| 판정 | hold |
| 2U_C 변경 commit | 없음 |
| 검토 파일 | `ui/ui_draw_chart_real.py`, `ui/ui_draw_chart_base.py`, `ui/ui_draw_chart_items.py`, chart data producer 경로 |
| V3 근거 | `3e67661b STOM V3.03`, 실시간차트 x축 데이터 변환 오류 수정 |
| hold 사유 | V3는 `same_code and not same_time`에서 `ctpg_xticks`를 append하지만, 2U_C의 `draw_line`, `draw_candlestick`, `draw_volumebar`, formula draw 계열은 대부분 `same_code and same_time`일 때만 incremental update를 수행함 |
| 위험 | x축만 append되고 데이터/item은 full redraw 경로로 들어가면 `ctpg_xticks`, `ctpg_arry`, `len_list`, item cache 길이 관계가 어긋날 수 있음 |
| 재개 조건 | GUI runtime 재현 또는 별도 chart state 설계로 `same_code and not same_time` 경로의 x축/데이터 길이 계약을 확정한 뒤 재검토 |
| 검증 | V3 HEAD 구조 유지 확인, 2U_C drawing 조건 grep, chart data producer 경로 읽기 전용 확인, root/2U_C status guard |

이 판정은 V3의 실시간차트 x축 보정 의도를 부정하는 것이 아니라, 2U_C Kiwoom 유지 lane에서 동일 변경을 안전하게 적용하려면 추가 runtime evidence가 필요하다는 의미다. BP-002C는 broad merge가 아니라 hold record로 닫고, 후속 작업은 더 작은 증거 단위로 분리한다.