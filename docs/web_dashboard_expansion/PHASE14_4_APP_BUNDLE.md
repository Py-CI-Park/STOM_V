# Phase 14.4 — 전체 컴포넌트 빌드 컴파일 (런타임 babel 제거 · 최대 폭발반경)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_3_CHART_HELPERS.md`.
> **목표**: index.html 의 운영 컴포넌트 26개를 빌드 시점에 JSX→JS 컴파일한 단일 클래식 스크립트(`bundle/app.js`)로 교체해 **메인 페이지의 런타임 babel(vendor-babel.js)을 제거**한다. 화면 동작 변화 0.

## 한 줄 요약
26개 `.jsx`(connection~app)를 esbuild 로 각각 변환→**index.html 로드 순서대로 연결**한 `bundle/app.js`(커밋) 생성. index.html 은 26개 `text/babel` 스크립트 + `vendor-babel.js` 를 **단일 `<script defer src="bundle/app.js">` 로 교체**. 런타임 변환 0.

## 설계 (안전성 근거)
- **변환만(transform), 번들링 아님**: esbuild `transform`(loader=jsx, jsxFactory=React.createElement)으로 각 파일을 개별 변환 후 순서대로 문자열 연결. 전역 스코프 공유 모델 보존 → 파일 간 bare 식별자(`fmtMoney`, 컴포넌트명) 해소 그대로.
- **중복 선언 없음 확인**: 현재 babel-standalone 이 공유 스코프에서 무충돌 실행 = 최상위 이름 중복 없음(connection.jsx 만 plain `useState`, 나머지 파일별 별칭) → concat 안전. import/export 미사용도 확인.
- **로드 순서**: `app.js` 는 `defer` 클래식 → 파싱 후·DOMContentLoaded 전 실행. 문서 순서상 `stom-ui.js`(head, ESM 모듈) 뒤 → `window.fmt*/_axisTicks` 준비된 뒤 실행. vendor-react(클래식, 파싱 중) 먼저 → React 전역 사용 가능. app.jsx 의 ReactDOM 마운트는 defer 라 DOM 준비됨.
- **순서 보존**: `build-app.mjs` 의 `ORDER` 배열(=기존 index.html 순서). 산출물에 `/* ==== X.jsx ==== */` 마커를 심어 검증 가능.

## 무엇이 바뀌었나
- 신규 `webui-build/build-app.mjs`(esbuild) + `package.json` 스크립트(`build`=lib+app, `build:app`). esbuild devDep 명시.
- `bundle/app.js` 신규 산출물(커밋, ~950KB, 런타임 npm-free).
- `index.html`: 26 `text/babel` + `vendor-babel.js` 제거 → `<script defer src="bundle/app.js?v=20260614k">` 1줄. vendor-react/react-dom/lightweight-charts(클래식) + stom-ui(모듈) 유지.

## 계약 테스트 오버홀 (14.4↔14.5 결합)
per-file `?v=` 핀·로드순서를 index.html 에서 단정하던 13개 테스트를 **app.js 의 `==== X.jsx ====` 마커 / `bundle/app.js?v=`** 기준으로 갱신(의미 보존):
- 로드순서: test_tab_shell·integrated_layout·research_lab/wiki/glossary/run_compare/strategy_prompt/ai_context/hypotheses → app.js 마커 순서.
- 캐시핀: test_dashboard_validation_views·analysis_gen_filter·tmap → `bundle/app.js?v=` + app.js 마커 존재.
- 서빙: test_dashboard_ws(`/ui/` 본문) → `bundle/app.js`·`bundle/stom-ui.js` 마커.
- test_p14_build_harness: index.html 이 app.js 로드 + **text/babel·vendor-babel 부재** 단정(런타임 babel 제거 가드).
- 레거시 `STOM AI Dashboard.html` 은 아직 text/babel(미전환) → hypotheses 테스트는 레거시=HTML 순서, index=app.js 마커로 분기.

## 검증
- **실화면**: 8771 실 `/ui/` 6탭+하위탭 전수 클릭 **pageerror 0**, `window.App/fmtMoney` 정의, **`window.Babel` undefined**(babel 미로드), 스크린샷 픽셀 정상. lab.html/pro.html(미전환, 유지) 0 error.
- **게이트**: 전체 `pytest tests/unit/ -q` 신규 실패 0(pre-existing 7만) + `verify_nonrelease_sync.py` exit 0 + 코드리뷰.

## 잔여 / 다음
- **lab.html·pro.html·STOM AI Dashboard.html 은 아직 런타임 babel 사용**(각자 컴포넌트 서브셋 + 인라인 마운트). 이들 전환 + `vendor-babel.js` 파일 완전 제거는 **14.7**.
- **14.5**: `app.js`/`stom-ui.js` 수동 `?v=` → content-hash + 매니페스트. app.js 미니파이(현재 미적용, ~950KB)도 14.5에서.
- **14.6**(선택): TS 점진.
