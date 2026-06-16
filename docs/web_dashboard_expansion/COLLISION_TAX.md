# Collision-Tax Tally — esbuild transform(단일 스코프) 충돌 클래스 추적

> ✅ **EXECUTED (2026-06-16, Track Z PR-6 / Story 4+5b FLIP)** — 충돌 클래스가 **구조적으로 제거됨**.
> 기본 빌드가 esbuild `bundle:true`(per-module scope)로 전환되어, 단일 스코프(concat)에서 발생하던
> 최상위 식별자 충돌(중복 선언 / 자기-별칭 / 호이스팅)은 더 이상 발생 불가능하다. 아래 탤리와 go-signal은
> **역사적 기록**이며 더 이상 능동적 트리거가 아니다.

| # | 날짜 | 사건 | 비용/대응 |
|---|------|------|-----------|
| 1 | 2026-06-14 | (이전 P1) CodeBlock(code-viewer vs strategy-inspector) 충돌 — 하이라이팅 손실 | CvCodeBlock 리네임 + test_no_duplicate_globals 신설 |
| 2 | 2026-06-15 | (프로그램 P7) VdtPromoteChecklist: research-lab `function` vs dashboard-pages `const = window.*` 자기-별칭 충돌 → "already declared" SyntaxError, 전 탭 크래시 | dashboard-pages 를 `<window.Vdt*/>` 멤버표현식 직접참조로 수정 + test_no_duplicate_globals 가 자기-별칭도 카운트하도록 강화(블라인드스팟 제거) |

**누적: 2 / 5 (최종 — 동결).** 누적 5 도달 전에 PR-6 flip 이 충돌 클래스 자체를 제거했으므로 탤리는 더 이상 증가하지 않는다.

---

## Story 4 정식 착수 조건 (Go-Signal) — ✅ 충족·실행 완료

> ~~Track Z PR-1 (스캐폴딩, 플래그 기본값 OFF) 진행 중 — 탤리 미증가.~~ → **PR-6 에서 flip 실행됨.**

**Story 4 (기본값 전환 + concat 폐기) 착수 조건:**

- ~~(A) 누적 카운터가 5에 도달한다 (당시 2/5).~~
- ~~(B) `test_no_duplicate_globals`가 잡을 수 없는 가드 회피형 충돌이 발생한다.~~

**실제 착수 근거(서면 정당화):** (A)/(B) 자동 트리거 대신, **PR-1~PR-5 의 안전 게이트가 모두 GREEN** 으로
완료되어 flip 의 잔여 리스크가 실질 0 이 된 시점에 **명시적 정당화 하에** Story 4 를 착수했다:
- PR-3: 26/26 dual-safe ESM 변환 완료(flag-OFF byte-불변).
- PR-4(Story 4 진입게이트): 하네스 V3(7탭) + V4(3 standalone) 전부 0-error 렌더 — 비-기본탭 누락 import 0 확인.
- PR-5(Story 5a): 17개 concat-마커 결합 테스트를 model-agnostic 으로 이관.
- PR-6(Story 4+5b, 본 작업): 기본=bundle 전환 + build-model 가드 2건 swap + 비상 롤백 플래그.

**충돌 클래스 제거(구조적):** 기본이 per-module scope 번들이 되어 단일 스코프 충돌은 발생 불가능.
`test_no_duplicate_globals` 등 단일-스코프 가드는 비상 롤백(STOM_LEGACY_CONCAT=1) 경로의 안전망으로만
의미를 가진다.

**완료된 작업:**
- Track Z PR-6: 기본 빌드를 esbuild `bundle:true`(served `frontend/bundle/app.js`, manifest `model:"bundle"`)로
  전환. concat 경로는 `STOM_LEGACY_CONCAT=1` 뒤 **비상 즉시 롤백**으로 보존(삭제 아님). 하네스가 served
  번들의 7탭+3 standalone 렌더(0 errors, 단일 React)를 증명. 상세: `TRACK_Z_PR6_FLIP_LOG.md`.
