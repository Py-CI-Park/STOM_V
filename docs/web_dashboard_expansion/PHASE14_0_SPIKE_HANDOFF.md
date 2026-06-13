# Phase 14.0 스파이크 — 착수 핸드오프 (post-compaction 자급자족 문서)

> 2026-06-14 작성. **목적**: compaction 후 컨텍스트가 비어도 이 문서만으로 Phase 14.0(Vite 빌드 PoC)을 착수할 수 있게 한다.
> 상위 계획: `docs/web_dashboard_expansion/ROADMAP_PHASE12_PLUS.md` Phase 14 섹션.

## 0. 한 줄 요약
대시보드 프런트(`ai_strategy_loop/dashboard/frontend/`)를 in-browser Babel + window 전역에서 **Vite 모듈 번들로 점진 이전**하는 첫 단계. 14.0은 **위험 낮은 PoC**: 빌드 도구를 정하고, 모듈 1개만 ESM으로 전환해 `/ui/` 동일 경로로 빌드 서빙되는지 + 화면이 픽셀 동일한지 증명한다. **운영 화면은 절대 바꾸지 않는다.**

## 1. 환경·전제 (그대로 사실)
- 워크트리: `C:/System_Trading/STOM/STOM_V.wt-webbt`. 작업 브랜치: `feature/webbt-phase14` (origin `lazycodex/tick-sparse-positive-generation-improvement-20260604` 에서 분기).
- 운영 서버: 8770(wt-dev 실서버) / 8771(wt-webbt 검증). 재기동 스크립트: `C:/Temp/restart_wtdev_server.py`(8770) · `C:/Temp/restart_webbt_server.py`(8771).
- 프런트 현황(2026-06-14 실측): jsx 26개·`Object.assign(window,…)` 26곳·총 20,296줄(최대 backtest-charts.jsx 2,814)·빌드시스템 **없음**(vendor-babel.js 런타임 변환)·index.html 26 `text/babel` 스크립트 수동 순서.
- 백엔드: FastAPI가 `frontend/`를 StaticFiles로 `/ui/` 서빙. 무예외 계약(HTTP 200 + error 페이로드). **백엔드·라우트·URL 불변이 원칙.**
- 캐시 계약: `?v=YYYYMMDDx` + 계약 테스트 3파일(`tests/unit/test_dashboard_validation_views.py`·`test_analysis_gen_filter.py`·`test_tmap.py`) 락스텝.
- 게이트 표준: 전체 `python -m pytest tests/unit/ -q` 신규 실패 0(**pre-existing 7개 제외**: test_backtest_button_contract·test_backtest_process_protocol_diagnostics×2·test_backtest_spawn_contract_audit×2·test_runner_helpers·test_ui_jisu_cleanup) + vendor-babel 변환 + 8771 Playwright.
- 회귀 안전망: **Phase 12-B 6탭 스냅샷 기준선**(out-of-tree, `C:/Temp/webbt_phase6_shots/p12_baseline/tab_*.png`). 14.0의 동등성 비교 기준.

## 2. 14.0 산출물 (Definition of Done)
1. **빌드 도구 결정**: Vite vs esbuild — 결정과 근거를 이 문서 §6에 기록. (권장 Vite.)
2. **PoC 빌드 파이프라인**(격리): `frontend/`(또는 신규 `frontend-build/`)에 package.json + 설정. 모듈 **1개만** ESM(import/export)으로 전환해 번들 생성. 산출물을 `/ui/`가 서빙하는 경로로 출력하거나, 별도 PoC HTML(`/ui/_vite_poc.html`)로 로드.
3. **양립 증명**: 기존 런타임-babel 경로(index.html)는 **그대로 동작**하면서, PoC 빌드 모듈도 같은 화면을 렌더. (전환은 14.1+에서, 14.0은 공존 PoC.)
4. **픽셀 동등성**: PoC가 렌더한 화면 == Phase 12-B 해당 스냅샷(육안/스크린샷 비교). 회귀 0.
5. **게이트**: 전체 pytest 신규 실패 0(빌드 PoC는 런타임 경로 미변경이라 기존 테스트 영향 없어야 함) + 8771 health/ui 200 + 페이지 에러 0.
6. **node/npm 운영 정책 결정**: 빌드 산출물을 저장소에 커밋(런타임 npm 불필요)할지 §6에 기록.

## 3. 권장 PoC 후보 모듈 (가장 안전한 첫 전환)
**connection.jsx의 순수 포매터 헬퍼** 또는 **chart.jsx의 순수 축/틱 헬퍼**(`_axisTicks` 등) — UI 의존·다른 전역 의존이 없어 ESM 전환 위험이 가장 낮다. 단일 함수 1개를 ESM 모듈로 빼고, PoC 엔트리에서 import해 동일 출력 확인.
- 피해야 할 것: app.jsx·simulation-charts.jsx 등 대형/오케스트레이터(폭발 반경 큼 — 14.3/14.4 영역).

## 4. 단계 절차 (체크리스트)
1. `git fetch origin && git checkout -b feature/webbt-phase14 origin/lazycodex/tick-sparse-positive-generation-improvement-20260604`
2. 빌드 도구 결정(§6 기록) → package.json + vite/esbuild 설정 추가(`frontend/` 격리).
3. PoC 모듈 1개 ESM 전환 + PoC 엔트리(HTML 또는 기존 페이지에 빌드 산출물 1개 주입).
4. 빌드 실행 → 산출물 `/ui/` 경로 서빙 확인(FastAPI StaticFiles 경로 점검; 필요 시 마운트 1줄만, 백엔드 라우트 불변).
5. 8771 재기동 → PoC 화면 렌더 + 기존 화면 무변화 동시 확인.
6. Playwright로 PoC vs Phase12-B 스냅샷 동등성 캡처(`C:/Temp/webbt_phase6_shots/`).
7. 전체 pytest 게이트(신규 실패 0).
8. 코드리뷰(별도 패스) → PR → 머지 → wt-dev 통합 → 8770 재기동.
9. §6에 결정·실측·다음 단계(14.1 범위) 기록.

## 5. 제약·금지 (회귀 방지)
- **빅뱅 금지**: 14.0은 모듈 1개. 전면 전환은 14.2+.
- 런타임-babel 경로(index.html 26 스크립트)는 14.0에서 건드리지 않는다(양립).
- 백엔드/라우트/URL/무예외 계약 불변. styles.css 토큰·디자인 불변.
- 화면 변화 0(픽셀 동등성 게이트로 강제). 기능 변경 금지.
- node 미설치 환경 대비: 빌드 산출물 커밋 정책을 결정(§6). 런타임은 npm 의존 없게.

## 6. 결정·실측 기록 (착수 시 채움)
- 빌드 도구: ____ (근거: ____)
- node/npm 운영: 빌드 산출물 커밋? ____ 
- PoC 전환 모듈: ____
- `/ui/` 서빙 방식: ____ (StaticFiles 경로 / 별도 PoC HTML)
- 픽셀 동등성 결과: ____
- 다음(14.1) 범위 메모: ____

## 7. compaction 후 재개 첫 행동
1. 이 문서 + ROADMAP_PHASE12_PLUS.md 읽기.
2. 메모리 `web-dashboard-3tab-expansion.md`로 Phase 6~13 맥락 복구.
3. §4 체크리스트 1번부터 진행.
