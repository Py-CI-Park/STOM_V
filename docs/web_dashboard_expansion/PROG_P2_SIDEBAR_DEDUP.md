# P2 — 진화 사이드바 중복 제거(Wiki/AIContext) · C1 5-edit

> 2026-06-14. 대시보드 스타일·구조 개선 프로그램 Phase 2. P1(연구실 탭 홈) 완료로 가능.

## 한 줄 요약
P1 에서 연구실 탭에 홈을 얻은 `ResearchWikiPanel`·`AIContextPanel`을 **진화 사이드바에서 제거**(중복 해소) + 발견용 버튼(→ 연구실 탭). `ResearchLabPanel`·`ResearchHeatmapPanel`은 계약/사용자요청으로 유지. 4개 app.jsx-잠금 계약 테스트를 새 홈(dashboard-pages.jsx)으로 리타겟. 진화 섹션 라벨 9→7.

## 변경
- **app.jsx** 진화 사이드바: `<ResearchWikiPanel>`·`<AIContextPanel>` + 그 SectionLabel(Wiki/AI Context Pack) 제거. 발견용 버튼 `📚 연구 위키·AI 컨텍스트 팩 → 연구실 탭`(`setActiveTab("lab")` — 재마운트 아님, 순수 네비게이션).
- **C1 FIVE 테스트 동반수정**(이번 PR 소유):
  1. test_design_pass::test_all_four_research_panels_still_mounted — Wiki/AIContext → dashboard-pages.jsx, Lab/Heatmap → app.jsx(양 파일 읽기).
  2. test_dashboard_integrated_layout — `text="Wiki"` 2곳(required 목록 + 순서 단언) 제거, 비-Wiki 순서 4건 유지.
  3. test_dashboard_ai_context_pack — `<AIContextPanel` 마운트 단언 → dashboard-pages.jsx(ai-context.jsx body·번들순서 단언 무변경).
  4. test_dashboard_wiki_frontend — `<ResearchWikiPanel`+`baseUrl={base}`/`wsStatus="na"` → dashboard-pages.jsx(실제 P1 fold props).
- 빌드 산출물 재생성·커밋(app.js v=9151d5d8, manifest) — M2.

## 가드 준수
- **소진적 스윕**: tests/unit/ 전체에서 app.jsx 의 Wiki/AIContext 마운트를 단언하는 다른 테스트 0(코드리뷰 독립 확인) — 미열거 깨짐 없음.
- ResearchLabPanel·ResearchHeatmapPanel·비-Wiki 섹션순서 유지. FROZEN 전역 미개명. no_dup_globals/p14/index_cache/phase9 green.

## 검증
- app.jsx Wiki/AIContext 마운트 0; 4 리타겟 테스트 explicit green.
- 전체 pytest 7 failed(핀 베이스라인 동일) + 3229 passed — 신규 0. verify_nonrelease exit0.
- 8771 6탭 0 pageerror; 진화 섹션 라벨 9→7(중복 2개 제거 확인). code-review APPROVE(0 이슈).

## 다음
P3(진화 IA 완화 — `<details>` 그룹) → P4(PIPELINE 통합) → P6(디자인시스템 랜딩) → P7.
