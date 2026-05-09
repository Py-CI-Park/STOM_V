# 2UC-V3-BP-009A Page 4 - 공식 문서 동기화

작성일: 2026-05-07 KST
대상 lane: `STOM_Version_2U_C`
작업 성격: docs sync only, code 변경 없음

## 1. 진행률

```text
전체 V3->2U_C 진행률 [####################]  98.8%  81 / 82 pages
BP-009A 진행률       [################----]  80.0%   4 /  5 pages
현재 page            [####################] 100.0%  Page 4 완료
남은 page            [####----------------]  20.0%   1 /  5 pages
```

## 2. 동기화 대상

| 문서 | 반영 내용 |
|---|---|
| `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md` | BP-009A Page 4 공식 sync 기록 |
| `docs/CARRY_FORWARD_REGISTRY.md` | BP-009A 적용 carry-forward 기록 |
| `docs/update_log/2026-05-07_v3_2uc_bp009a_chart_ui_page4_sync.md` | 이번 Page 4 기록 |

## 3. 공식 적용 기록

| 항목 | 내용 |
|---|---|
| Backport ID | `2UC-V3-BP-009A` |
| 적용 상태 | Page 4 docs sync 완료 |
| source V3 version | `STOM V3.12` |
| source commit | `62e81349 STOM V3.12` |
| target branch | `STOM_Version_2U_C` |
| target code commit | `f791c54a BP-009A crosshair 표시 경계를 보정한다` |
| target file | `ui/ui_draw_crosshair.py` |
| Kiwoom 영향 | 없음, visual-layer crosshair 표시 보정 |
| DB 영향 | 없음 |
| pyd/UI broad 영향 | pyd wrapper 변경 없음, 단일 UI helper file 변경 |
| LS dependency | 없음 |

## 4. Rollback 기준

만약 chart mouse move, crosshair 표시, legend 위치 갱신에 regression이 보이면 2U_C code commit `f791c54a`만 revert하면 된다. root/2U_C 문서 commit은 후속 correction 문서로 보정한다.

## 5. 다음 OMX 명령

```powershell
omx ralph --no-deslop "2UC-V3-BP-009A Page 5 final guard를 진행한다. root와 2U_C에서 verify_release_sync.py를 통과시키고, git status clean, forbidden runtime artifact guard, STOM_Version_3U_C branch 부재를 확인한다. final guard 결과를 docs/update_log/2026-05-07_v3_2uc_bp009a_chart_ui_page5_final_guard.md와 allowlist/CARRY_FORWARD_REGISTRY에 기록한 뒤 root와 2U_C에 문서 commit만 남긴다."
```