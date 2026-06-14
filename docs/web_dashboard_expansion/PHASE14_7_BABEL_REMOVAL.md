# Phase 14.7 — 런타임 babel 완전 제거 (완결)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_6_TS_SEED.md`.
> **목표**: 보조 엔트리(lab/pro/verdict/legacy)도 컴파일 번들로 전환하고 `vendor-babel.js`(3MB 런타임 변환기)를 저장소에서 완전 제거한다. **대시보드 전체에서 런타임 babel 의존 0.** 화면 동작 변화 0.

## 한 줄 요약
lab/pro/verdict/STOM-legacy 4개 페이지를 index.html 과 동일한 컴파일 번들 `bundle/app.js` + `stom-ui.js` 로 전환(각자 LabPage/ProPage/VerdictPanel 마운트). `app.jsx` 자동 마운트를 플래그(`__STOM_NO_AUTO_MOUNT__`)로 가드해 app.js 를 재사용. `vendor-babel.js` 삭제. 테스트의 babel 의존도 esbuild 로 이관.

## 무엇이 바뀌었나
- `app.jsx`: 자동 App 마운트를 `window.__STOM_NO_AUTO_MOUNT__` 로 가드. 이 플래그면 페이지가 직접 다른 루트(LabPage 등)를 마운트한다(같은 app.js 재사용 — DRY).
- `lab.html`·`pro.html`·`verdict.html`: text/babel 8~1개 + 인라인 babel 마운트 제거 → `<script defer src="bundle/app.js">` + 플래그 + `DOMContentLoaded` 에서 `React.createElement(window.LabPage/ProPage/VerdictPanel, …)` 마운트(JSX 없는 순수 JS — babel 불필요). vendor-babel 제거. (verdict.html 은 이전에 dashboard-pages.jsx 만 로드해 의존 누락 위험이 있었으나 이제 전체 번들로 안전.)
- `STOM AI Dashboard.html`: CDN(unpkg react/dom/babel) 레거시 → 로컬 vendor + app.js(자동 마운트). 이전엔 컴포넌트 10개만 로드(누락 위험)했으나 전체 번들로 정상화.
- **`vendor-babel.js` 삭제**(3MB). `build-app.mjs` htmlTargets 에 verdict 추가, setV 정규식을 `src="…"` 앵커로 정밀화(주석 오버라이트 방지).

## 로드 순서 안전성
- 4개 페이지 공통: vendor-react/dom(클래식, 파싱 중) → `__STOM_NO_AUTO_MOUNT__=true`(클래식 인라인, 파싱 중) → stom-ui(모듈, defer) → app.js(defer) → 인라인 마운트(`DOMContentLoaded`, app.js 뒤). 플래그는 app.js 실행 전 세팅되고, 마운트는 app.js 가 컴포넌트를 정의한 뒤 실행.

## 테스트 이관 (babel → esbuild)
- **transform 검증 11개**(`*_transforms_with_vendor_babel`): `require(vendor-babel.js)` → `require(../webui-build/node_modules/esbuild)` + `esbuild.transformSync({loader:'jsx',…})`. (dir=frontend 기준 상대경로, 추가 인자 불필요.)
- **구조/캐시 단정 6개**(phase9 lab_pro 순서·research_pro 마운트·sim_phase6_1 lab 의존·hypotheses 레거시·validation lab×2): per-file `.jsx` 단정 → app.js 의 `==== X.jsx ====` 마커 / `bundle/app.js` 로드 기준으로 갱신(의미 보존).

## 검증
- **실화면(전 5페이지)**: 8771 `/ui/`·`/ui/lab.html`·`/ui/pro.html`·`/ui/verdict.html`·`/ui/STOM AI Dashboard.html` 모두 rooted·**`window.Babel` undefined**·`window.fmtMoney` 함수·0 pageerror. `/ui/vendor-babel.js` → **404**(삭제 확인).
- **게이트**: 전체 pytest 신규 실패 0(pre-existing 7) + `verify_nonrelease_sync.py` exit 0 + 코드리뷰.

## Phase 14 완료
14.0(스파이크)→14.1(하네스)→14.2(포매터 de-dup)→14.3(차트 헬퍼)→14.4(전체 컴파일·메인 babel 제거)→14.5(content-hash)→14.6(TS 시드)→**14.7(런타임 babel 완전 제거)**. 대시보드 프런트는 이제 **빌드 시점 컴파일 단일 번들**로 동작하며 런타임 babel 의존이 전무하다. 화면·기능·백엔드·URL 불변.
