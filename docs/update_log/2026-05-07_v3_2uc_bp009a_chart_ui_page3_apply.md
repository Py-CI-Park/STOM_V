# 2UC-V3-BP-009A Page 3 - crosshair minimal patch 적용 기록

작성일: 2026-05-07 KST
대상 lane: `STOM_Version_2U_C` (`C:/System_Trading/STOM/STOM_V.wt-dev`)
작업 성격: Page 2에서 허용한 `ui/ui_draw_crosshair.py` 단일 파일 최소 patch 적용

## 1. 진행률

```text
전체 V3->2U_C 진행률 [####################]  97.6%  80 / 82 pages
BP-009A 진행률       [############--------]  60.0%   3 /  5 pages
현재 page            [####################] 100.0%  Page 3 완료
남은 page            [########------------]  40.0%   2 /  5 pages
```

## 2. 적용 commit

| 항목 | 내용 |
|---|---|
| 2U_C code commit | `f791c54a BP-009A crosshair 표시 경계를 보정한다` |
| target file | `ui/ui_draw_crosshair.py` |
| source V3 version | `STOM V3.12` |
| source V3 commit | `62e81349 STOM V3.12` |
| source file | `ui/draw_chart/draw_crosshair.py` |

## 3. 적용 범위

허용 범위 그대로 아래 두 가지 변경만 적용했다.

1. `hLines`, `vLines` 구성 직후 각 crosshair line에 `setZValue(29)`를 부여했다.
2. 비실시간 chart에서 label/legend anchor 이동 중 예외가 발생해도 mouse move가 끊기지 않도록 해당 block을 `try/except Exception: pass`로 보호했다.

## 4. 제외 범위

이번 code commit은 아래 파일/영역을 수정하지 않았다.

- `ui/ui_draw_chart_base.py`
- `ui/ui_show_dialog.py`
- `utility/chart_hoga_query_sound.py`
- dialog lifecycle / window position 저장 경로
- analysis / radar chart UI
- LS API, DB migration, pyd/UI broad merge

## 5. 검증 결과

| 검증 | 결과 |
|---|---|
| `python -m py_compile ui/ui_draw_crosshair.py` | passed |
| `git diff --check -- ui/ui_draw_crosshair.py` | passed before code commit |
| `git diff --cached --check -- ui/ui_draw_crosshair.py` | passed before code commit |
| root `verify_release_sync.py` | passed after code commit |
| 2U_C `verify_release_sync.py --root STOM_V.wt-dev` | passed after code commit |
| worktree status | root/2U_C clean after code commit |

## 6. 남은 risk

GUI mouse-move runtime은 offline 환경에서 실행하지 않았다. 다만 변경 범위는 visual-layer의 zValue와 legend anchor guard에 갇혀 있으며, DB/LS/pyd/runtime process 경계에는 접근하지 않았다.

## 7. 다음 OMX 명령

```powershell
omx ralph --no-deslop "2UC-V3-BP-009A Page 4 docs sync를 진행한다. Page 3 code commit f791c54a와 문서 docs/update_log/2026-05-07_v3_2uc_bp009a_chart_ui_page3_apply.md를 기준으로 docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md와 docs/CARRY_FORWARD_REGISTRY.md에 적용 commit, 제외 범위, 검증 결과, rollback 기준을 공식 반영한다. root와 2U_C에 문서 commit만 남기고 code는 수정하지 않는다."
```