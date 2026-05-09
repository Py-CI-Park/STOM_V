# 2UC-V3-BP-009B - chart moneytop 후보 batch 기록

작성일: 2026-05-07 KST
대상 lane: `STOM_Version_2U_C`
운영 방식: 후보 단위 batch-loop, Page 논리는 문서에 누적하고 commit은 후보 단위로 축소

## 1. 진행률

BP-009A final baseline `82 / 82 pages` 이후 BP-009B 5-page 논리를 후보 단위로 한 번에 처리했다.

```text
전체 V3->2U_C 진행률 [####################] 100.0%  87 / 87 pages
BP-009B 진행률       [####################] 100.0%   5 /  5 pages
현재 후보            [####################] 100.0%  BP-009B 완료
남은 page            [--------------------]   0.0%   0 /  5 pages
```

## 2. Page 1 - read-only inventory

Source:

- V3 version: `STOM V3.07`
- V3 commit: `6ab5d036 STOM V3.07`
- V3 source file: `ui/event_click/button_clicked_chart.py`
- V3 update item: `차트 머니탑 리스트 오류 수정`

Target:

- 2U_C target file: `ui/ui_show_dialog.py`
- target function: `chart_moneytop_list(ui)`

V3 diff 핵심:

1. `starttime`, `endtime`를 정수로 먼저 변환
2. tick query에서 `starttime < 90030`이면 `90030`으로 보정
3. query 조립 시 중복 `int()` 제거
4. table contents를 조회 결과 판정 전에 먼저 clear
5. 빈 DataFrame 판정을 `df.empty`로 변경

## 3. Page 2 - scope decision

2U_C는 V3와 다르게 `chart_moneytop_list` 내부에 아래 분기가 있다.

- coin tick/min DB path
- stock/future DB path
- Kiwoom 증권사 여부
- 주식/코인 timeframe 분리
- crypto 24h market과 stock/future 장 시작 시간 차이

따라서 V3의 `starttime < 90030` 보정과 query 구조 전체 변경은 2U_C에 바로 이식하지 않는다.

이번 BP-009B에서 허용한 안전 scope:

- stale table 방지를 위해 조회 결과 판정 전 `ui.ct_tableWidgett_01.clearContents()` 실행
- `len(df) == 0` 대신 `df.empty` 사용

hold scope:

- `starttime < 90030` tick 보정
- market별 query/time normalization
- coin/future/Kiwoom 별 default time 재정의

## 4. Page 3 - minimal patch 적용

2U_C code commit:

```text
cd35395f BP-009B moneytop 리스트 초기화를 보정한다
```

변경 파일:

```text
ui/ui_show_dialog.py
```

적용 내용:

```python
ui.ct_tableWidgett_01.clearContents()
if df is None or df.empty:
    return
```

## 5. Page 4 - docs sync / carry-forward

| 항목 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-009B` |
| 적용 상태 | 완료 |
| source commit | `6ab5d036 STOM V3.07` |
| target code commit | `cd35395f BP-009B moneytop 리스트 초기화를 보정한다` |
| Kiwoom 영향 | 없음, DB query 자체는 변경하지 않음 |
| DB 영향 | schema/query path 변경 없음 |
| pyd/UI broad 영향 | pyd wrapper 변경 없음, 단일 dialog helper function의 table refresh만 보정 |
| rollback | `cd35395f` 단일 revert |

## 6. Page 5 - final guard

검증 결과:

| Guard | Result |
|---|---|
| `python -m py_compile STOM_V.wt-dev/ui/ui_show_dialog.py` | passed |
| root `verify_release_sync.py` | passed |
| 2U_C `verify_release_sync.py --root STOM_V.wt-dev` | passed |
| root status | clean before docs commit |
| 2U_C status | clean after code commit before docs mirror |
| runtime artifact | `_database`, `_log`, `*.db`, `backtest/graph/*` 미추적 유지 |

## 7. 제외/hold 기록

`BP-009B`는 V3 chart moneytop diff 전체를 가져온 것이 아니다. query/time normalization은 별도 evidence 없이는 진행하지 않는다.

후속 후보를 만들 경우 새 ID를 사용한다.

- `2UC-V3-BP-009C`: chart moneytop time normalization read-only only
- 또는 후순위 후보인 `2UC-V3-BP-010A`: Binance/Upbit websocket guard inventory

## 8. 다음 OMX 명령

```powershell
omx ralph --prd "STOM V3에서 STOM_Version_2U_C로 선별 backport할 다음 safe 후보 batch를 계속 진행한다. 현재 완료 기준은 BP-009B final guard이며, 다음 우선 후보는 BP-010A Binance/Upbit websocket guard read-only inventory이다. 후보 단위 batch-loop로 처리하고, Page 논리는 문서에 남기되 commit은 후보당 최대 code commit 1개, root docs commit 1개, 2U_C mirror docs commit 1개로 제한한다. LS API, DB migration, pyd/UI broad merge는 제외한다."
```