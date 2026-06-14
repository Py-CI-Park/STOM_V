# P2 — 구조 통합(라이브 차트 기하 공유 · 결정 동선 크로스링크, 픽셀 중립)

> 2026-06-14. ralplan 계획 P2. 대시보드 감사 우선순위 3(중간 위험·픽셀 중립 구조 정리).

## 한 줄 요약
중복된 라이브 자본/낙폭 차트의 **스케일·경로 수식을 공유 `_liveChartGeom` 으로 추출**(engine 전폭본·phase-detail 인라인본 공유, byte-동일 → 픽셀 중립)하고, **운영 채택 결정 동선**(내보내기 승인 WS `final_approval` ↔ 운용 결정 기록 REST `/record_decision`)을 **양방향 크로스링크**로 안내. 백엔드 라우트·픽셀(기본 스냅샷) 무변경.

## 감사 정정(실측 — 계획 가정 수정)
- 계획의 P2(a)는 "두 차트가 **height+legend 만 다름** → `LiveBacktestChartBase({state,height,showLegend})` 컴포넌트로 병합"이었으나, 실측 결과 두 차트는 다음이 **모두 다르다**:
  - 치수(H 240/200·여백), `xMax` 공식(전폭본은 `equity.length` 항 포함), 그라디언트 색(**전폭=토큰 `var(--teal/--red)` vs 인라인=하드코딩 hex `#4cd6b3`/`#ff6b6b`** — `--red`≠`#ff6b6b`), 영역 렌더(className vs `fill="url()"`), 우축 눈금 수(4 vs 2), x라벨 수(3 vs 2), 범례 유무, 패널 래퍼 유무, 빈상태 문구.
  - → 단일 컴포넌트 병합은 ~8개 분기 prop(컨피그 수프)이 필요하고, 색/눈금 통일은 **픽셀을 바꿔 P2 픽셀중립 가드를 위반**한다.
  - **결론**: 픽셀 중립한 **공유 부분(스케일·경로 수식)만** `_liveChartGeom` 으로 추출하고 시각 셸은 각자 유지. 전면 시각 통합(색 토큰화·눈금 일치 등)은 픽셀 재베이스라인이 허용되는 **Design Pass 로 이연**.

## 변경
- **engine.jsx**: `_liveChartGeom({equity,drawdown,baseline,W,H,padL,padR,padT,padB,xMax})` 신설 →
  `{innerW,innerH,maxEq,minEq,ddMax,x,y,yDD,eqPath,eqAreaPath,ddAreaPath}` 반환. `LiveBacktestChart`
  가 자체 치수·xMax 로 호출(`useMemo_e`). 죽은 `innerW` 제거. window 노출에 `_liveChartGeom` 추가.
- **phase-detail.jsx**: `LiveBacktestChartInline` 이 동일 `_liveChartGeom` 호출(`useMemo_ph`, 자체
  치수·xMax·시각 셸 유지). 중복 경로 빌더 제거. 죽은 `innerW` 제거. `window.LiveBacktestChart` 가드 보존.
- **cards.jsx**: `ApprovalDialog`(WS `final_approval`)에 결정 동선 크로스링크 — "증거 → 내보내기 승인
  (이 단계) → 결정 이력→운용 결정 탭 기록(REST `/record_decision`)". 모달(조건부 — 기본 스냅샷 밖).
- **dashboard-pages.jsx**: verdict `decide` 하위탭에 역방향 크로스링크 — 내보내기 승인은 진화 탭
  다이얼로그(WS), 이 폼은 운용 결정 append-only 기록(REST)임을 명시. decide 하위탭(기본 summary — 스냅샷 밖).
- **test_p2_structural.py**(신규): 순수 Python grep — `_liveChartGeom` 단일 최상위 선언·양 차트 호출·
  window 노출/가드 보존, 결정 크로스링크(양방향)·백엔드 라우트 무변경(WS/REST)·VerdictPanel 미개명.

## FROZEN/가드 준수
- window 전역 미개명: `LiveBacktestChart`·`LiveBacktestChartInline`·`VerdictPanel`·`LabPage`·`ProPage`.
- 백엔드 라우트 무변경: `final_approval`(app.jsx WS send)·`/record_decision`(dashboard-pages.jsx REST POST) 그대로.
- 픽셀 중립: 크로스링크는 조건부 모달·비기본 하위탭에만 — 기본 6탭+lab/pro/verdict 스냅샷 불변.
- 번들 충돌 가드: `_liveChartGeom` 은 engine.jsx 단일 최상위 선언(test_no_duplicate_globals green).

## 검증
- **빌드**: `npm run build` → app.js v=fc4cf129 (26 files), 5 HTML ?v= 갱신.
- **픽셀 중립 증명**: `_liveChartGeom` 의 eqPath/eqAreaPath/ddAreaPath 문자열 조립이 각 원본과 byte-동일
  (start/mid/end 단일공백 결합 동일). 런타임(8771) `window._liveChartGeom` 호출 → eqPath`M…`·area`…Z`·
  스케일 함수·maxEq/minEq/ddMax 정확.
- **계약**: test_p2_structural + test_p11_engine_gauges + test_p13_bt_overlay_split + test_no_duplicate_globals
  + test_dashboard_live_demo_split + test_p14 = 79 passed.
- **게이트**: 전체 pytest 신규 실패 0(핀 베이스라인 동일) — (게이트 로그 참조).
- **실화면(8771)**: app.js 새 해시, 6탭 각 0 pageerror(총 0), 전역(EnginePanel/LiveBacktestChart/
  _liveChartGeom/VerdictPanel/LabPage/ProPage/ApprovalDialog) 정상.

## 다음
P3(HoF·process-flow·freeze_verdict 통합 + 공유 tick 헬퍼 → format.ts) → Design Pass(진화 사이드바 정리·그룹화·시각 위계, 픽셀 재베이스라인).
