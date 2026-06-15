# P7 — freeze_verdict 공유 셸 통합 + HoF field-diff 이연 (프로그램 최종 단계)

> 2026-06-15. 대시보드 스타일·구조 개선 프로그램 P7(마지막). field-diff 게이트로 손실 0 보장.

## 한 줄 요약
freeze_verdict 의 **공유 3블록(PROMOTE 체크리스트·경보·요약줄)을 정본 컴포넌트로 추출**(research-lab 정의, dashboard-pages 가 `<window.Vdt*/>` 멤버표현식으로 소비) — 각 패널의 고유 섹션은 전부 보존. **HoF 는 field-diff 결과 발산형으로 판정 → 병합 시 필드 손실 → 이연**(게이트 작동).

## field-diff (병합 전 — 손실 0 증명, PROG_P7_FIELD_DIFF.md)
- **HoF (DEFER)**: HallOfFamePanel(chart.jsx, payoff/일평균/동시보유/운영금/인간행/정렬/필터/스크린샷갤러리/30s refresh) vs _RpHallOfFame(research-pro.jsx, score/거래수/펼침코드/바로백테). 컬럼·마크업·기능이 본질적으로 달라 단일 코어는 config-soup·필드 손실 → **병합 안 함**(시각 일관성은 공유 CSS 토큰으로 이미 확보). HoF 무변경.
- **freeze_verdict (DO)**: _ValidationPanel(research-lab) vs VerdictPanel(dashboard-pages) 가 PROMOTE 체크리스트·경보·요약줄 데이터 계약 동일 → 3블록 추출.

## 변경
- **research-lab.jsx**: `VdtPromoteChecklist`/`VdtAlerts`/`VdtSummaryLines` 정본 함수(+로컬 `_VDT_STATUS_ICON`) 신설, window 노출. `_ValidationPanel` 이 인라인 3블록 → 공유 컴포넌트 호출. walkforward 표 등 고유 섹션 보존.
- **dashboard-pages.jsx**: `VerdictPanel` summary 하위탭이 `<window.VdtPromoteChecklist/>`/`<window.VdtAlerts/>`/`<window.VdtSummaryLines/>` 멤버표현식 직접 참조. OOS-CI 표 + 4 하위탭(검증결산/레짐/포트폴리오/결정) 보존. 정본 스타일(ICON 맵·width:100%·빈상태·alert `var(--amber)` 토큰).

## ⚠️ 충돌 사고 + 수정 + 가드 강화 (런타임 검증이 잡음)
- **사고**: 1차 구현이 dashboard-pages 에 `const VdtPromoteChecklist = window.VdtPromoteChecklist`(자기-별칭) 최상위 선언 → 단일 번들 스코프에서 research-lab 의 `function VdtPromoteChecklist` 와 **"already declared" SyntaxError → 전 탭 크래시**(8771 0탭/1 pageerror). 정적 grep 게이트(pytest)는 못 잡음 — **Playwright 런타임 검증이 포착**.
- **수정**: dashboard-pages 의 자기-별칭 const 3개 삭제 → `<window.Vdt*/>` 멤버표현식 직접 참조(window.LabPage 패턴). 재빌드 후 6탭 정상·0 pageerror.
- **가드 강화**: `test_no_duplicate_globals` 가 자기-별칭(`const X=window.X`)도 최상위 선언으로 카운트하도록 수정(과거 제외 = 블라인드스팟). 이제 자기-별칭↔함수정의 충돌도 차단.
- **collision-tax**: COLLISION_TAX.md 에 #2 기록(누적 2/5 — Track Z 트리거).

## 검증
- 전체 pytest 7 failed(핀 베이스라인 동일) + 3229 passed — 신규 0. verify_nonrelease exit0.
- no_duplicate_globals(강화)·p14·research_pro·design_pass·index_cache·hall_of_fame(33, 백엔드 무회귀)·validation_views(41) green.
- 8771 런타임: window.Vdt{PromoteChecklist,Alerts,SummaryLines} = function; 6탭 0 pageerror.
- **실화면(결정 이력 탭)**: 공유 PROMOTE 체크리스트(✅/⚠️)·경보(amber)·요약줄 + 고유 OOS-CI 표 + 4 하위탭 전부 렌더(필드 손실 0). app.js v=ec3151d4(.jsx 변경). styles.css 무변경(핀 그대로).

## 프로그램 완료
P1·P0·P2·P3·P4·P6·P7 전부 머지. (Track Z=esbuild bundle 이관은 트리거-조건부 이연, 현재 2/5.)
