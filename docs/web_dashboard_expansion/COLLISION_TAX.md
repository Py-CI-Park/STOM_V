# Collision-Tax Tally — esbuild transform(단일 스코프) 충돌 클래스 추적

> Track Z(transform→bundle 이관) 트리거. 충돌 1건이 리뷰에서 잡히거나 누적 5건 도달 시 Track Z 스케줄.

| # | 날짜 | 사건 | 비용/대응 |
|---|------|------|-----------|
| 1 | 2026-06-14 | (이전 P1) CodeBlock(code-viewer vs strategy-inspector) 충돌 — 하이라이팅 손실 | CvCodeBlock 리네임 + test_no_duplicate_globals 신설 |
| 2 | 2026-06-15 | (프로그램 P7) VdtPromoteChecklist: research-lab `function` vs dashboard-pages `const = window.*` 자기-별칭 충돌 → "already declared" SyntaxError, 전 탭 크래시 | dashboard-pages 를 `<window.Vdt*/>` 멤버표현식 직접참조로 수정 + test_no_duplicate_globals 가 자기-별칭도 카운트하도록 강화(블라인드스팟 제거) |

**누적: 2 / 5.** (트리거 A=리뷰 충돌 1건은 발생했으나 즉시 수정+가드 강화로 흡수. 누적 5 도달 시 Track Z 정식 착수.)

---

## Story 4 정식 착수 조건 (Go-Signal)

> Track Z PR-1 (스캐폴딩, 플래그 기본값 OFF) 진행 중 — **탤리 미증가**.

**Story 4 (기본값 전환 + concat 폐기)는 다음 조건 중 하나가 충족될 때 착수한다:**

- **(A) 누적 카운터가 5에 도달한다** (현재 2/5).
- **(B) `test_no_duplicate_globals`가 잡을 수 없는 가드 회피형 충돌이 발생한다** — 단일 스코프 모델의 구조적 맹점을 노출하는 충돌로, 기존 가드가 감지하지 못하고 운영에 영향을 준 경우.

**이 게이트 이전에 기본값을 전환하려면 서면 명시적 정당화가 필요하다.** 보수적 연기가 기본값이다.

**현재 진행 중인 작업 (탤리 미영향):**
- Track Z PR-1: `STOM_BUNDLE` 플래그 뒤 스캐폴딩 + 파일럿 모듈 + 런타임 하니스 구축. 플래그 기본값 OFF — 운영에 no-op. 탤리를 증가시키지 않는다.
