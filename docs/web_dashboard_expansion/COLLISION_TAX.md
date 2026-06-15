# Collision-Tax Tally — esbuild transform(단일 스코프) 충돌 클래스 추적

> Track Z(transform→bundle 이관) 트리거. 충돌 1건이 리뷰에서 잡히거나 누적 5건 도달 시 Track Z 스케줄.

| # | 날짜 | 사건 | 비용/대응 |
|---|------|------|-----------|
| 1 | 2026-06-14 | (이전 P1) CodeBlock(code-viewer vs strategy-inspector) 충돌 — 하이라이팅 손실 | CvCodeBlock 리네임 + test_no_duplicate_globals 신설 |
| 2 | 2026-06-15 | (프로그램 P7) VdtPromoteChecklist: research-lab `function` vs dashboard-pages `const = window.*` 자기-별칭 충돌 → "already declared" SyntaxError, 전 탭 크래시 | dashboard-pages 를 `<window.Vdt*/>` 멤버표현식 직접참조로 수정 + test_no_duplicate_globals 가 자기-별칭도 카운트하도록 강화(블라인드스팟 제거) |

**누적: 2 / 5.** (트리거 A=리뷰 충돌 1건은 발생했으나 즉시 수정+가드 강화로 흡수. 누적 5 도달 시 Track Z 정식 착수.)
