# 2UC-V3-BP-009A Page 5 - final guard

작성일: 2026-05-07 KST
대상 lane: `STOM_Version_2U_C`
작업 성격: final guard, code 변경 없음

## 1. 최종 진행률

```text
전체 V3->2U_C 진행률 [####################] 100.0%  82 / 82 pages
BP-009A 진행률       [####################] 100.0%   5 /  5 pages
현재 page            [####################] 100.0%  Page 5 완료
남은 page            [--------------------]   0.0%   0 /  5 pages
```

## 2. Final guard 결과

| Guard | Result |
|---|---|
| `python -m py_compile STOM_V.wt-dev/ui/ui_draw_crosshair.py` | passed |
| root `verify_release_sync.py` | passed |
| 2U_C `verify_release_sync.py --root STOM_V.wt-dev` | passed |
| root status | clean before Page 5 doc append |
| 2U_C status | clean before Page 5 doc append |
| forbidden runtime artifacts | `_database`, `_log`, `*.db`, `backtest/graph/*` tracked 파일 없음 |
| `STOM_Version_3U_C` branch | 없음 |
| runtime code 변경 | Page 5에서는 없음 |

## 3. 최종 적용 요약

| 항목 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-009A` |
| source | `STOM V3.12`, commit `62e81349` |
| target code commit | `f791c54a BP-009A crosshair 표시 경계를 보정한다` |
| target file | `ui/ui_draw_crosshair.py` |
| 적용 내용 | crosshair line zValue 29, 비실시간 label/legend anchor guard |
| 제외 | LS API, DB migration, pyd/UI broad merge, chart_hoga_query_sound, ui_draw_chart_base, chart moneytop, dialog lifecycle, analysis/radar |

## 4. 종료 판단

`2UC-V3-BP-009A`는 완료한다. 다음 후보는 code patch가 아니라 `BP-009B` read-only inventory로 시작하는 것이 안전하다. `BP-009B`는 Page 1에서 chart moneytop query/time/table clear 후보만 분리 조사한다.

## 5. 다음 OMX 명령

```powershell
omx ralph --no-deslop "2UC-V3-BP-009B Page 1 read-only inventory를 시작한다. 범위는 BP-009A에서 분리한 chart moneytop query/time/table clear 후보만 조사한다. V3.07 button_clicked_chart.py의 chart_moneytop_list 변경과 2U_C ui/ui_show_dialog.py의 chart_moneytop_list를 비교하고, stock/coin/future, Kiwoom/해외선물, tick/min DB path 분기를 mapping한다. code 구현은 하지 말고 safe/hold/no-op 판단 문서와 root/2U_C commit만 남긴다. LS API, DB migration, pyd/UI broad merge는 제외한다."
```