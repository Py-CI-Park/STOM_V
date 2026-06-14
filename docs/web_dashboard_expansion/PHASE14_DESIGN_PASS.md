# Design Pass — 시각 위계/그룹화(섹션 헤더 승격) · WCAG · 캐시버스트 (터미널·픽셀 변경 허용)

> 2026-06-14. ralplan 계획 Design Pass(터미널, 픽셀 재베이스라인 허용 단계).

## 한 줄 요약
진화 탭의 **논리 그룹 경계를 시각적으로 분명히** 한다 — `SectionLabel` 을 dim 인라인(ink-3·10.5px)에서 `.stom-section-label`(ink-1·12px·600·**좌측 teal accent 바**)로 승격해 "단일 30패널 스크롤"을 9개 그룹(Run Monitor·Strategy/Prompt·Compare·Generation Analytics·Research Lab·Wiki·AI Context·진화 분석·판정)으로 구획. WCAG AA+(9.37:1) 유지, styles.css 캐시버스트 수동 bump. **패널/동작/백엔드 무변경**.

## 감사 정정(실측 — 사이드바 제거는 안전 불가, 미수행)
계획의 "진화 사이드바 연구패널 4종(ResearchLabPanel/ResearchWikiPanel/AIContextPanel/ResearchHeatmapPanel)은 전용 탭에도 마운트된 중복 → 제거 + 슬림 링크"는 실측 결과 **대부분 거짓**이었다. 계획이 요구한 사전 검증("제거 전 test 가 사이드바 내용을 단언하지 않는지 확인")이 명확한 STOP 을 반환:

| 패널 | 실측 | 처리 |
|------|------|------|
| **ResearchLabPanel** | 전용 탭(LabPage) 있음 — 단, `test_dashboard_integrated_layout.py:31` 이 app.jsx 내 `<ResearchLabPanel`(+ `text="Research Lab"` 순서)을 **계약으로 단언** | **유지**(제거 시 계약 위반·다수 통합테스트 깨짐) |
| **ResearchHeatmapPanel** | app.jsx:281 주석에 **"사용자 요청"**(적합도추이 위 동일크기) + `test_sim_phase6_1.py:159` 요구 | **유지**(사용자 의도·테스트 계약) |
| **ResearchWikiPanel** | **진화 사이드바에만** 마운트(전용 탭 없음 — LabPage/ProPage 미렌더) | **유지**(제거=기능 상실) |
| **AIContextPanel** | **진화 사이드바에만** 마운트(전용 탭 없음) | **유지**(제거=기능 상실) |

→ 4종 모두 안전 제거 불가(기능 상실·사용자 의도·계약). **범위 축소가 아니라 계획의 사전검증 게이트가 구조 변경을 차단한 결과.** 밀도/조직 개선은 패널 삭제 대신 **시각 그룹화(섹션 헤더 승격)** 로 달성한다(기능 무손실).

## 변경
- **styles.css `.stom-section-label`**: ink-1(8.98:1)·12px·600·`letter-spacing .14em` 유지 + **flex 행 + `::before` 3px teal accent 바**(장식 — 대비 규칙 무관) + `margin-top 10px`. 30패널 스크롤을 섹션별로 구획.
- **app.jsx `SectionLabel`**: dim 인라인 스타일 div → `<div className="stom-section-label">`. 호출부(`<SectionLabel text="…">` ×9) 무변경 → `test_dashboard_integrated_layout` 의 `text="Research Lab"` 단언·순서 계약 유지.
- **5 HTML**: `styles.css?v=20260614f → 20260614g`(수동 핀 — build-app.mjs 는 app.js/stom-ui.js 만 해시).
- **test_design_pass.py**(신규): 순수 Python grep — SectionLabel 클래스 승격·accent CSS·캐시버스트·연구패널 4종 유지(회귀 가드).

## FROZEN/가드 준수
- window 전역 미개명: LabPage/ProPage/VerdictPanel/App. 백엔드 라우트 무변경. 패널 동작 무변경.
- `test_dashboard_integrated_layout`(연구패널 순서 계약)·`test_sim_phase6_1`(Heatmap)·`test_phase9_spa_tabs` 모두 green(연구패널 유지로 충족).
- 픽셀 변경은 섹션 헤더 시각 승격뿐(터미널 단계 허용). 패널 추가/삭제·레이아웃 그리드 변경 없음.

## 검증(재베이스라인 증거)
- **빌드**: `npm run build` → app.js v=e447dc29, stom-ui.js v=a142dbb8(불변), 5 HTML app.js/stom-ui ?v= 갱신 + styles.css ?v=20260614g.
- **계약**: test_dashboard_integrated_layout + test_phase9_spa_tabs + test_sim_phase6_1 + test_p14 + test_no_duplicate_globals + test_design_pass = green.
- **게이트**: 전체 pytest 신규 실패 0(핀 베이스라인 동일) — (게이트 로그 참조).
- **실화면(8771) 재베이스라인 스크린샷**: 6탭 풀페이지 캡처(`$JOB/tmp/shots_8771/`). 6탭 각 0 pageerror(총 0).
  - 섹션 헤더 **9개** 렌더(class `.stom-section-label`, color ink-1, 12px/600, accent 3px teal `rgb(76,214,179)`).
  - **WCAG: 섹션 헤더 대비 9.37:1**(AA text ≥4.5 충족).
  - 연구패널 4종 + Lab/Pro/Verdict 전역 모두 정상(기능 무손실).

## 재베이스라인 프로토콜(인간 승인)
픽셀이 의도적으로 바뀌므로 6탭 스냅샷이 갱신된다. 자동 스냅샷-diff 계약 테스트는 이 프로젝트에 없고(게이트는 pytest grep + 0 pageerror), 시각 증거는 Playwright 풀페이지 스크린샷이다. 새 기준 스크린샷을 PR 에 첨부해 **사용자가 8770 머지 결과로 최종 확인**한다(루프 내 사전 자동승인 금지 — 사용자 검토가 승인).

## 후속(이 계획 범위 밖)
- 연구패널 중복의 진짜 해소는 ResearchWikiPanel/AIContextPanel 에 전용 탭 홈을 부여(또는 lab/pro 탭에 편입)한 뒤라야 안전 — 별도 작업.
- 더 깊은 IA(접이식 그룹·반응형 재배치)는 패널 홈 정리 후 별도 RALPLAN.
