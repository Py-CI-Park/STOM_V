# 2UC-V3-BP-009A Page 2 - chart/UI scope decision

작성일: 2026-05-07 KST
대상 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
작업 성격: scope decision only, code 변경 없음

## 1. 진행률

```text
전체 V3->2U_C 진행률 [###################-]  96.3%  79 / 82 pages
BP-009A 진행률       [########------------]  40.0%   2 /  5 pages
현재 page            [####################] 100.0%  Page 2 완료
남은 page            [############--------]  60.0%   3 /  5 pages
```

## 2. Page 2 목표

Page 1에서 찾은 chart/UI 후보 C1~C8 중에서 이번 BP-009A cycle의 실제 Page 3 patch 대상으로 삼을 후보를 하나로 좁힌다. 이번 Page에서도 code는 수정하지 않는다.

## 3. 검토 근거

### 3.1 V3 source evidence

`STOM V3.12` commit `62e81349`의 `ui/draw_chart/draw_crosshair.py`에는 다음 두 가지 변경이 있다.

1. crosshair horizontal/vertical line의 zValue를 29로 지정한다.
2. DB/비실시간 chart에서 legend/label anchor 이동 중 예외가 발생해도 chart mouse move가 끊기지 않도록 `try/except Exception` guard를 둔다.

### 3.2 2U_C target evidence

2U_C의 대응 파일은 `ui/ui_draw_crosshair.py`이다.

확인 결과:

- `hLines`, `vLines` list는 존재한다.
- label은 이미 `setZValue(30)`을 사용한다.
- crosshair line에는 아직 zValue가 지정되지 않았다.
- legend anchor 이동은 guard 없이 직접 수행된다.
- 변경 범위는 `ui/ui_draw_crosshair.py` 단일 파일에 갇힐 수 있다.

## 4. 후보별 Page 2 판정

| 후보 | Page 1 판정 | Page 2 결정 | 이유 |
|---|---|---|---|
| `BP-009A-C1` chart moneytop query/time/table clear | conditional | 이번 cycle에서 제외, 별도 `BP-009B` 후보로 분리 | 2U_C `ui/ui_show_dialog.py`는 stock/coin/future, Kiwoom/해외선물 DB path, tick/min query 분기가 섞여 있어 별도 read-only mapping이 필요 |
| `BP-009A-C2` return press chart table path dedupe | hold 우세 | hold | V3는 `cell_clicked_06` 재사용이 가능하지만 2U_C는 data tuple 선두에 `coin` flag가 있어 단순 재사용이 위험 |
| `BP-009A-C3` crosshair line zValue + legend anchor guard | 가장 안전한 conditional | Page 3 patch 후보로 선정 | DB/LS/pyd와 무관하고 `ui/ui_draw_crosshair.py` 단일 visual-layer 변경으로 제한 가능 |
| `BP-009A-C4` candle/volume width last interval | no-op | no-op 확정 | 2U_C `ui/ui_draw_chart_items.py`는 이미 `xticks[-1] - xticks[-2]` 기준을 사용 중 |
| `BP-009A-C5` draw_chart_base exception unify | hold/conditional | hold | draw loop 전체 try/except 구조 변경은 regression 범위가 넓고 chart rendering 전반에 영향 |
| `BP-009A-C6` DB chart query simplification | hold | hold | 2U_C는 `utility/chart_hoga_query_sound.py`에 chart/hoga/sound가 결합되어 있고 data tuple/DB path 차이가 큼 |
| `BP-009A-C7` dialog_list 일괄 close | hold | hold | dialog lifecycle, window position 저장, pyd wrapper 영향이 명확하지 않음 |
| `BP-009A-C8` radar/analysis chart factor UI | excluded/hold | excluded for BP-009A | analysis runtime wiring, DB/settings, AnalyzerRisk 후속 설계 없이는 진행 금지 |

## 5. BP-009A Page 3 적용 범위 결정

Page 3에서 허용되는 patch scope는 아래로 제한한다.

허용:

- `C:/System_Trading/STOM/STOM_V.wt-dev/ui/ui_draw_crosshair.py` 단일 파일
- `hLines`, `vLines` 생성 직후 crosshair line zValue를 29로 지정
- 비실시간 chart label/legend anchor 이동 block에 최소 `try/except Exception: pass` guard 추가

금지:

- `ui/ui_draw_chart_base.py` draw loop 변경
- `ui/ui_show_dialog.py` moneytop query 변경
- `utility/chart_hoga_query_sound.py` query/data tuple 변경
- dialog lifecycle 변경
- analysis/radar chart UI 변경
- LS API, DB migration, pyd/UI broad merge

## 6. 검증 계획

Page 3에서 patch를 적용한다면 최소 검증은 다음과 같다.

```powershell
python -m py_compile C:/System_Trading/STOM/STOM_V.wt-dev/ui/ui_draw_crosshair.py
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py
python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev
git -C C:/System_Trading/STOM/STOM_V.wt-dev diff --check -- ui/ui_draw_crosshair.py
```

GUI runtime launch는 이번 Page 2 범위가 아니며, Page 3에서도 offline 검증 한계로 남을 수 있다.

## 7. 다음 OMX 명령

```powershell
omx ralph --no-deslop "2UC-V3-BP-009A Page 3 minimal patch를 진행한다. Page 2 문서 docs/update_log/2026-05-07_v3_2uc_bp009a_chart_ui_page2_scope_decision.md에 따라 2U_C의 ui/ui_draw_crosshair.py 단일 파일만 수정한다. 허용 범위는 hLines/vLines에 setZValue(29)를 부여하고, 비실시간 chart legend/label anchor 이동 block을 최소 try/except Exception: pass로 감싸는 것이다. ui_draw_chart_base, ui_show_dialog, chart_hoga_query_sound, dialog lifecycle, analysis/radar, LS API, DB migration, pyd/UI broad merge는 수정하지 않는다. py_compile, diff check, release sync를 통과시키고 root/2U_C 문서 commit까지 남긴다."
```