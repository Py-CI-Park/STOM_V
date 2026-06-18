# Phase 14.3 — 차트 순수 헬퍼 빌드 이전 (_axisTicks de-dup)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_2_LEAF_DEDUP.md`.
> **목표(이 단계 범위)**: `chart.jsx`의 순수 헬퍼 `_axisTicks`를 빌드 번들 단일 출처로 이전(14.2 포매터 패턴 재적용). 화면 동작 변화 0.

## 한 줄 요약
`chart.jsx`의 `function _axisTicks(...)` 정의(축 눈금 등분 헬퍼)를 `webui-build/src/format.mjs`로 옮겨 번들이 `window._axisTicks`로 제공. `chart.jsx`는 `const _axisTicks = window._axisTicks` 별칭만 유지.

## 범위 재조정 (로드맵 대비)
로드맵의 14.3은 "차트 순수함수 + 대형 차트 파일 분할"을 함께 묶었으나, **대형 React 컴포넌트 파일의 빌드 컴파일**은 스크립트 실행 타이밍(런타임-babel은 DOMContentLoaded, ESM 모듈은 그 이전, 클래식은 파싱 중)이 섞이는 위험이 있어 **14.4에서 전체 컴포넌트를 한 번에 빌드 컴파일**하는 방식으로 처리한다(혼합 타이밍 위험 회피). 14.3은 **위험 0의 순수 헬퍼 이전**으로 한정.

## 무엇이 바뀌었나
- `webui-build/src/format.mjs`: `_axisTicks` export + `window._axisTicks` 노출 추가.
- `chart.jsx`: `function _axisTicks` 정의 제거 → `const _axisTicks = window._axisTicks` 별칭. 내부 4개 호출부(ProfitChart 축 2곳·BacktestDetailChart 축 2곳)는 bare `_axisTicks(...)` 그대로(별칭으로 해소).
- `index.html`: `chart.jsx?v=20260614b → 20260614j`.
- `bundle/stom-ui.js`: 재빌드(1.13KB→1.43KB).

## 다중 엔트리포인트 회귀 수정 (코드리뷰 발견 — 중요)
코드리뷰가 **14.2부터의 잠재 회귀**를 포착: `index.html` 외에 `lab.html`·`pro.html`·`STOM AI Dashboard.html`도 `connection.jsx`/`chart.jsx`를 로드하지만 **번들(stom-ui.js)을 안 받아** 그 페이지들에선 de-dup된 `window.fmt*`/`_axisTicks`가 undefined였다(특정 컴포넌트 마운트 시 깨짐).
- **수정**: 3개 standalone 엔트리에 `<script type="module" src="bundle/stom-ui.js">` 추가(중복 재도입 없이 모든 엔트리가 번들로 수렴 — 올바른 장기 방향). `lab/pro`의 connection/chart 캐시 핀도 `i/j`로 락스텝.
- **재발 방지**: `test_all_entrypoints_loading_deduped_jsx_also_load_bundle` — connection/chart를 로드하는 모든 HTML이 번들도 로드하는지 단정.
- `STOM AI Dashboard.html`은 CDN(unpkg)·캐시 버전 없는 **벤더링 이전 레거시**로 확인됨(index.html이 정식 진입점) — 번들만 추가하고 제거는 사용자 판단에 맡김(문서 표기).

## 검증
- **실화면**: 8771 실 `/ui/` 6탭 전수 클릭 pageerror 0 + `window._axisTicks(0,100,5)=[0,25,50,75,100]` 정확(진화 ProfitChart·백테 BacktestDetailChart 축 렌더 정상).
- **회귀 가드**: `test_p14_build_harness.py` 6/6 — `_axisTicks` 정의가 chart.jsx에서 제거(`function _axisTicks(` 부재)·format.mjs/번들 잔존·window 별칭 확인.
- **캐시 계약 락스텝**: `test_dashboard_validation_views.py`의 chart.jsx 핀을 `20260614b→20260614j`로 동기 갱신(계약 테스트가 chart.jsx 버전을 핀하므로 필수).
- **게이트**: 전체 pytest 신규 실패 0 + `verify_nonrelease_sync.py` exit 0 + 코드리뷰.

## 다음 (14.4 — 최대 폭발반경)
남은 24개 컴포넌트 .jsx를 빌드(Vite)로 일괄 컴파일해 단일 번들 로드 → 런타임-babel 제거 준비. 6탭 전수 스냅샷+WS/페이싱 회귀 0. (14.7에서 vendor-babel 최종 제거.)
