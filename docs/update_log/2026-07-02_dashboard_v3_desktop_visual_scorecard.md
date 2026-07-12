# 2026-07-02 대시보드 V3 데스크톱 시각 검토와 완성도 평가

## 범위

- 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dashboard-remodel`
- 브랜치: `feature/dashboard-remodel-20260626`
- 기준: PC/데스크톱 사용만 평가한다. 모바일 `390px` findings는 이번 점수에서 제외한다.
- V2 기본 경로와 V3 명시 경로를 모두 유지한다.
- live order, broker login, account control, KHOPENAPI, DB cutover, USER_ACK, V3K gate advancement는 범위 밖이다.

## 핵심 결론

V3 remodel은 데스크톱 기준으로 기능 동등성 94/100, UX/UI 성숙도 95/100, 종합 완성도 95/100으로 평가한다. V2는 운영 기준 기능의 source of truth로는 여전히 중요하지만, PC 대시보드 UX/UI 완성도는 86/100 수준이다.

이번 후속 작업 전 V3 desktop blocker는 Condition 화면의 heatmap 내부 label/cell overflow였다. `heatmap()` grid column 최소폭과 CSS child minimum을 조정한 뒤, V3 8개 remodel 경로를 1280x720, 1440x900, 1920x1080에서 재검증했고 overflow/graphic/fetch/ws 문제가 모두 0으로 정리됐다.

## 점수표

| 평가 항목 | V2 데스크톱 | V3 데스크톱 | 판단 |
|---|---:|---:|---|
| 기본 경로 안정성 | 100 | 100 | `/ui`는 V2 유지, `/ui/remodel/*`는 명시 V3 유지 |
| 실기능 동등성 | 100 | 94 | V3는 backtest/replay/condition/audit 핵심 계약을 갖췄지만 실제 live happy path는 제한 검증 |
| 워크플로우 UX | 78 | 95 | V3는 workflow rail, shared context, handoff가 있어 V2보다 프로세스 추적성이 높음 |
| 시각적 일관성 | 82 | 96 | V3 24개 데스크톱 브라우저 조합 통과, V2는 legacy React Flow desktop overflow 측정 잔존 |
| 그래프/표 containment | 84 | 97 | V3 heatmap overflow 보정 후 chart/heatmap/table desktop clipping 없음 |
| 상태/오류/빈 데이터 표현 | 83 | 95 | V3는 reference/demo/live/error/empty/stale/requires-confirmation vocabulary가 공통화됨 |
| 안전 게이트 | 96 | 98 | V3 reference mode fetch/ws 0, 실행성 action은 manual-gated 유지 |
| 검증 성숙도 | 84 | 96 | V3는 unit/static/backend parity와 Chrome CDP evidence가 함께 존재 |
| **종합** | **86/100** | **95/100** | V3는 PC remodel 기준으로 리뷰/커밋 가능한 완성도 |

## 데스크톱 시각 검증

기존 전체 visual compare:

- 전체 48 checks
- overflow failures 16
- graphic failures 9
- blankish 0

사용자 조건에 따라 모바일 결과는 out-of-scope로 재분류했다. 데스크톱만 보면:

- desktop checks 32
- V3 desktop overflow baseline 2건: Condition heatmap at 1280/1440
- V3 desktop graphic failures 0
- V2 desktop overflow 2건: legacy React Flow viewport measurement
- V2 desktop graphic failures 4건: zero-size SVG placeholder 성격

수정 후 V3 desktop CDP 검증:

- 8개 V3 경로 x 3개 viewport = 24 checks
- viewport: 1280x720, 1440x900, 1920x1080
- document overflow 0
- heatmap child overflow 0
- chart/graphic overflow 0
- blankish 0
- reference/demo fetch 0
- WebSocket 0

## 변경 내용

- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
  - `heatmap()` grid column을 `minmax(54px, .8fr) repeat(n, minmax(0, 1fr))`로 바꿔 좁은 데스크톱 panel에서도 셀이 수축되게 했다.
- `ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css`
  - `.chart-box`에 `min-width: 0`, `max-width: 100%`, `overflow: hidden`을 추가했다.
  - `.heatmap`, `.heat-cell`, `.heat-label` 최소폭/overflow 규칙을 panel containment 기준으로 정리했다.

## 검증 결과

```text
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
passed

python -m pytest tests/unit/test_dashboard_remodel_baseline_contract.py tests/unit/test_dashboard_remodel_static.py -q
32 passed, 1 warning

python -m pytest <tests/unit/test_dashboard_remodel*.py expanded by PowerShell> -q
59 passed, 1 warning

python -m pytest tests/unit/dashboard/test_backtest_ws_job.py tests/unit/dashboard/test_simulation_ws.py tests/unit/dashboard/test_research_pro.py tests/unit/dashboard/test_p2_structural.py -q
64 passed, 1 warning

git diff --check
passed, CRLF warnings only

git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json
clean
```

`pytest tests/unit/ -q` 전체 묶음은 이번 후속 작업에서 실행하지 않았다.

## Evidence

- `.omo/evidence/dashboard-v3-visual-comparison-20260702/visual_compare_results.json`
- `.omo/evidence/dashboard-v3-visual-comparison-20260702/problem_v3-condition-desktop-heatmap.png`
- `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/todo01_desktop_visual_reclassify.json`
- `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/todo02_desktop_visual_cdp.json`
- `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/todo02_desktop-1280_condition.png`
- `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/todo02_desktop-1440_condition.png`
- `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/todo02_desktop-1920_condition.png`

## 잔여 리스크

- 실제 정상 live backend happy path는 이 환경에서 end-to-end로 검증하지 않았다.
- V3K gate 4~6, broker/account/order/DB 계열 기능은 의도적으로 미실행 상태다.
- 모바일은 사용하지 않는 조건으로 제외했다. 추후 모바일 사용 조건이 생기면 별도 responsive pass가 필요하다.

## 커밋 판단

현재 PC 대시보드 기준으로 V3 remodel은 커밋 가능한 상태다. 커밋 시 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`는 제외하고, `.omo/evidence/dashboard-v3-desktop-visual-polish-20260702/`와 이 문서를 포함하는 편이 좋다.
