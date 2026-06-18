# P1 — ResearchWiki + AIContext 전용 홈(연구실 탭 편입) · ENABLING

> 2026-06-14. 대시보드 스타일·구조 개선 프로그램(consensus plan) Phase 1. 사이드바 중복 제거(P2)의 선행.

## 한 줄 요약
`ResearchWikiPanel`·`AIContextPanel`이 진화 사이드바에만 있어 제거 불가였던 문제를 해소 — **연구실(LabPage) 탭 본문에 가산 렌더**(진화 사이드바와 동일 백엔드 컨텍스트 props). 진화 사이드바는 **건드리지 않음**(제거는 P2). OQ#1 = fold(새 탭 안 만듦 → STOM_TABS==6 유지).

## 변경
- **dashboard-pages.jsx `LabPage`**: ResearchLabPanel 아래에 `<ResearchWikiPanel baseUrl={base} wsStatus="na" runId={runId} />` + `<AIContextPanel baseUrl={base} wsStatus="na" runId={runId} genNo={0} />` 가산(각 `window.*` 가드). 진화 사이드바의 동일 props 패턴 보존 → P2의 wiki_frontend prop 단언이 새 홈에서 만족 가능(C1 enabler).
- 빌드 산출물 재생성·커밋: bundle/app.js(v=83a1a8cf) + manifest.json (M2). format.ts 무변경 → stom-ui.js 불변.

## 가드 준수
- **app.jsx 무변경** → 4개 app.jsx-잠금 테스트(design_pass 4패널·integrated_layout Wiki×2·ai_context_pack·wiki_frontend) 전부 green 유지(P1은 가산만; 제거는 P2).
- STOM_TABS==6 불변(test_phase9 green). FROZEN 전역 미개명. test_p14·index_cache_bumped·no_duplicate_globals green.

## 검증
- `npm run build` OK(app.js v=83a1a8cf, 26 files). 영향 계약 39 passed(design_pass·phase9·wiki_frontend·ai_context_pack·p14·index_cache·no_dup).
- 전체 pytest == 핀 베이스라인(신규 실패 0) — (게이트 로그).
- 8771: 6탭 각 0 pageerror(총 0). **연구실 탭 실화면에 RESEARCH WIKI(Metrics Glossary) + AI CONTEXT(context pack) 두 섹션 가산 렌더 확인**(스크린샷).

## 다음
P0(토큰 스캐폴딩) → P2(사이드바 중복 제거 — 이제 가능) → P3 → P4 → P6 → P7.
