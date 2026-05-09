# 2UC-V3-BP-009A Page 1 - chart/UI 후보 read-only inventory

작성일: 2026-05-07 KST  
대상 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)  
작업 성격: read-only inventory, code 변경 없음

## 1. 진행률

운영 page 산정은 다음처럼 잡는다.

- BP-008A final baseline: `72 / 72 pages`
- Candidate inventory 완료: `5 / 5 pages`
- BP-009A 신규 cycle: `5 pages`
- 따라서 이번 cycle 완료 목표 총량: `72 + 5 + 5 = 82 pages`

```text
전체 V3->2U_C 진행률 [###################-]  95.1%  78 / 82 pages
BP-009A 진행률       [####----------------]  20.0%   1 /  5 pages
현재 page            [####################] 100.0%  Page 1 완료
남은 page            [################----]  80.0%   4 /  5 pages
```

## 2. 이번 Page의 목표와 금지 범위

목표는 V3.07, V3.12, V3.14, V3.17의 chart/UI 관련 변경을 2U_C 기존 구조에 mapping하는 것이다. 이번 Page에서는 후보만 찾고 code는 수정하지 않는다.

금지 범위:

- LS API / LS REST / LS REAL / LS WebSocket 반영 금지
- DB migration 또는 `_database` 변경 금지
- V3 UI 폴더 구조 broad merge 금지
- V3U pyd-free 산출물 직접 반영 금지
- `ui_mainwindow.pyd` / `main_window.pyd` rename 또는 pyd 구조 변경 금지
- analysis runtime wiring, dashboard, broad backtest 변경 금지

## 3. 사용한 OMX/검증 표면

| 표면 | 결과 |
|---|---|
| `omx explore` | Windows POSIX wrapper 문제로 실패. code 수정 없음 |
| `omx sparkshell` | V3 관련 commit hash와 worktree status 확인에 사용 |
| `git show` | V3.07 / V3.12 / V3.14 / V3.17 관련 파일 diff 확인 |
| `git grep` / snippet inspection | 2U_C 대응 파일 mapping 확인 |

확인된 V3 source commit:

| version | commit |
|---|---|
| `STOM V3.07` | `6ab5d036` |
| `STOM V3.12` | `62e81349` |
| `STOM V3.14` | `f76222f8` |
| `STOM V3.17` | `f5975f4c` |

## 4. V3 -> 2U_C 대응 파일 mapping

| V3 path | 2U_C 대응 path | 관찰 |
|---|---|---|
| `ui/create_widget/set_dialog_chart.py` | `ui/set_dialog_chart.py` | factor layout/dialog_list 변경이 있으나 2U_C widget 수와 pyd wrapper 계약 차이가 있음 |
| `ui/event_click/button_clicked_chart.py` | `ui/ui_show_dialog.py`, `ui/ui_button_clicked_chart.py` | `chart_moneytop_list`는 2U_C에서 `ui_show_dialog.py`에 존재 |
| `ui/event_click/table_cell_clicked.py` | `ui/ui_cell_clicked.py` | return/cell click data tuple이 2U_C stock/coin 분기와 다름 |
| `ui/event_keypress/overwrite_return_press.py` | `ui/ui_return_press.py` | V3는 `cell_clicked_06` 재사용으로 단순화했으나 2U_C tuple 첫 값에 `coin`이 추가됨 |
| `ui/draw_chart/draw_crosshair.py` | `ui/ui_draw_crosshair.py` | line zValue와 legend anchor guard가 아직 2U_C에 없음 |
| `ui/draw_chart/draw_chart_items.py` | `ui/ui_draw_chart_items.py` | V3.14 xticks 마지막 간격 보정은 이미 2U_C에 존재 |
| `ui/draw_chart/draw_chart_base.py` | `ui/ui_draw_chart_base.py` | V3.17 예외처리 통합은 후보이나 draw loop 전체 영향이 큼 |
| `utility/sub_process_and_thread/chart_hoga_query.py` | `utility/chart_hoga_query_sound.py` | 2U_C는 chart/hoga/sound가 결합된 legacy process라 V3 구조를 직접 적용할 수 없음 |
| `ui/update_widget/update_textedit.py` | `ui/ui_update_textedit.py` | shutdown/data-save 관련 변경은 chart/UI 소규모 범위를 벗어남 |

## 5. 후보별 1차 판정

| 후보 | source | target | 1차 판정 | 이유 |
|---|---|---|---|---|
| `BP-009A-C1` chart moneytop query/time/table clear | V3.07 `button_clicked_chart.py` | 2U_C `ui/ui_show_dialog.py` | conditional | DB schema 변경은 없지만 2U_C는 coin/stock/future와 Kiwoom 증권사 분기가 있어 수동 mapping 필요 |
| `BP-009A-C2` return press chart table path dedupe | V3.07 `overwrite_return_press.py` | 2U_C `ui/ui_return_press.py`, `ui/ui_cell_clicked.py` | hold 우세 | V3 data tuple과 2U_C data tuple이 다르며 `coin` flag가 추가되어 단순 이식 위험 |
| `BP-009A-C3` crosshair line zValue + legend anchor guard | V3.12 `draw_crosshair.py` | 2U_C `ui/ui_draw_crosshair.py` | 가장 안전한 conditional | DB/LS/pyd와 무관하고 visual layer의 line/legend guard에 국한됨 |
| `BP-009A-C4` candle/volume width last interval | V3.14 `draw_chart_items.py` | 2U_C `ui/ui_draw_chart_items.py` | no-op | 2U_C는 이미 `xticks[-1] - xticks[-2]` 기준을 사용 중 |
| `BP-009A-C5` draw_chart_base exception unify | V3.17 `draw_chart_base.py` | 2U_C `ui/ui_draw_chart_base.py` | hold/conditional | 예외처리 범위가 draw loop 전체라 regression 범위가 넓음 |
| `BP-009A-C6` DB chart query simplification | V3.07 / V3.12 `chart_hoga_query*.py` | 2U_C `utility/chart_hoga_query_sound.py` | hold | 2U_C legacy combined process, stock/coin/future DB path, data tuple shape 차이 큼 |
| `BP-009A-C7` dialog_list 일괄 close | V3.07 `set_dialog_*` | 2U_C `set_dialog_*`, close paths | hold | dialog lifecycle/win position/pyd wrapper 영향 확인 필요 |
| `BP-009A-C8` radar/analysis chart factor UI | V3.12+ | 2U_C chart/factor UI | excluded/hold | analysis runtime wiring, DB/settings, AnalyzerRisk 후속 설계 필요 |

## 6. Page 1 결론

이번 Page에서 바로 code 적용하지 않는다. Page 2 scope decision에서 가장 안전한 후보는 `BP-009A-C3`이다.

추천 Page 2 결정 방향:

1. `BP-009A-C3`만 BP-009A의 실제 patch 대상으로 좁힐지 판단한다.
2. `BP-009A-C1`은 DB schema 변경은 없지만 broker/market 분기가 있으므로 별도 `BP-009B` 또는 BP-009A 후속으로 분리한다.
3. `C2`, `C5`, `C6`, `C7`, `C8`은 Page 2에서 hold/no-op/excluded로 닫는 것을 우선 검토한다.

## 7. 다음 OMX 명령

```powershell
omx ralph --no-deslop "2UC-V3-BP-009A Page 2 scope decision을 진행한다. Page 1 문서 docs/update_log/2026-05-07_v3_2uc_bp009a_chart_ui_page1_inventory.md를 기준으로 code 구현 없이 BP-009A-C3 crosshair line zValue + legend anchor guard만 실제 Page 3 patch 후보로 좁힐지 판단한다. C1 chart_moneytop은 별도 후보로 분리할지 결정하고, C2/C5/C6/C7/C8은 hold/no-op/excluded 여부를 문서화한다. root와 2U_C에 Page 2 문서 commit만 남긴다. LS API, DB migration, pyd/UI broad merge는 제외한다."
```