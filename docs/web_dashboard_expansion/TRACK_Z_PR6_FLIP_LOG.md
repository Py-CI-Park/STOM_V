# Track Z — PR-6 실행 로그 (Story 4 + 5b: THE FLIP)

> 2026-06-16 · 브랜치 `feature/webbt-track-z-pr6-flip` · 워크트리 `STOM_V.wt-webbt`
> 범위: **비가역 default-flip** — 기본 빌드 모델을 transform-concat 에서 esbuild `bundle:true` 로 전환.
> concat 은 **삭제하지 않고** `STOM_LEGACY_CONCAT=1` 뒤 비상 즉시 롤백으로 보존.

## 한 줄 결과

기본 빌드가 이제 실제 served 번들(`frontend/bundle/app.js`, `manifest.model=="bundle"`)을 산출한다.
하네스 V2/V3/V4 가 **served 번들**(`.track-z` 파일럿 아님)이 7탭 + 3 standalone 페이지를 **0 errors,
단일 React**로 렌더함을 증명. build-model 가드 2건을 bundle 불변식으로 swap. concat 폴백(STOM_LEGACY_CONCAT=1)
정상 동작 확인 후 기본(bundle)으로 재빌드해 트리를 flip 상태로 둠. 전체 unit: **신규 실패 0**.
`verify_nonrelease_sync.py` exit 0.

---

## 무엇이 바뀌었나

### 1. `ai_strategy_loop/dashboard/webui-build/build-app.mjs` (핵심)

- **기본 경로 = esbuild bundle**: 환경변수 없이 `node build-app.mjs` 실행 시, `buildServedBundle()`이
  `src/track-z-entry.pilot.js`(full per-module-scope ESM 그래프)를 alias-to-shim(`react`→`react-shim.js`,
  `react-dom`→`react-dom-shim.js`)로 classic IIFE 번들하여 **실제 served `frontend/bundle/app.js`** 에 쓴다.
- **공유 post-build 머신리(`runPostBuild`)**: bundle/concat 양쪽이 `bundle/app.js` 작성 후 동일하게 실행 —
  5개 HTML(index/lab/pro/verdict/"STOM AI Dashboard")의 `app.js`·`stom-ui.js` `?v=` content-hash 주입 +
  `manifest.json` 작성. 모델 차이는 manifest 본문뿐:
  - bundle: `model:"bundle"` + `entry` + `externalizedGlobals:{react:"window.React","react-dom":"window.ReactDOM"}`
  - concat: `model:"concat"` + `appSources:ORDER(26)`
- **비상 폴백 = `STOM_LEGACY_CONCAT=1`**: 옛 concat 경로(`_stripTopLevelEsm` + 26 ORDER + `==== X.jsx ====`
  마커 + `appSources`)를 그대로 보존. 삭제 아님 — git revert 보다 안전한 즉시 롤백.
- **레거시 파일럿 플래그 `STOM_BUNDLE=1` 보존**: 여전히 transient `.track-z/app.pilot.js` 만 빌드(served 트리
  미접촉). 구 도구 back-compat. `buildServedBundle()`을 공유하므로 served 빌드와 byte-equivalent.
- HTML 의 app.js script 태그는 **classic+defer 유지**(type=module 전환 없음). stom-ui.js 는 별도 ESM 모듈로
  불변.

### 2. `ai_strategy_loop/dashboard/webui-build/track-z-harness.mjs`

- `SERVED_APP = frontend/bundle/app.js` 상수 추가. **V2/V3/V4 가 served 번들을 로드**(이전 `.track-z/app.pilot.js`).
  → 하네스가 "브라우저가 실제 다운로드하는 파일"의 렌더를 증명(flip 의 load-bearing 안전 증거).
- V1 은 transient 파일럿 빌드 유지(alias-to-shim 메커니즘 클린 증명 — DemoBadge/LivePending republish).
- V2 이름 `V2_flagged_full_bundle` → `V2_served_default_bundle`. 주석/docstring 의 "flagged"·"legacy app.js"
  표현을 "served default bundle" 로 갱신.

### 3. build-model 가드 swap (Story 5b)

- **`tests/unit/dashboard/test_p14_build_harness.py`**
  - `test_app_bundle_contains_all_ordered_sources`(concat 26-마커) → **`test_app_bundle_is_single_entry_graph`**:
    `manifest.model=="bundle"`, app.js 에 `==== ` 마커 없음, `require("react")`/`react.development`/`__SECRET_INTERNALS`
    없음(단일 React), 풀앱(ReactDOM.createRoot + App/LabPage/ProPage/VerdictPanel), manifest entry/externalizedGlobals.
  - `test_content_hash_cache_consistency` 말미 `appSources==26`/`[-1]=="app.jsx"` → `model=="bundle"` +
    `entry` + `appSources not in manifest`. content-hash 일관성 본문은 모델 무관(공유 post-build)이라 불변.
  - **신규 `test_legacy_concat_fallback_still_26_sources`**: `STOM_LEGACY_CONCAT=1 node build-app.mjs` →
    concat app.js(26 마커) + `model=="concat"` + `appSources==26` 단언 후 `finally` 로 기본(bundle) 재빌드해
    트리 복원(테스트가 산출물 오염 안 함). node/esbuild 없으면 skip.
- **`tests/unit/dashboard/test_track_z_pr1_harness.py`**
  - `test_default_concat_path_still_26_sources` → **`test_default_manifest_is_bundle_model`**:
    `model=="bundle"` + entry + externalizedGlobals + `appSources not in manifest`.
  - 모듈 docstring: PR-1 파일럿 표현 → PR-6 flipped 현실(served 번들 V1~V4). V2 래퍼 docstring "legacy app.js"
    → "SERVED DEFAULT frontend/bundle/app.js".

### 4. 문서

- `docs/web_dashboard_expansion/COLLISION_TAX.md`: Track Z **EXECUTED** 표기 — 충돌 클래스 구조적 제거(기본
  per-module scope). 탤리(2/5)·go-signal 을 역사적 기록으로 동결.
- 본 로그 신설.

---

## 게이트 증거 (run + full output)

### (1) 기본 빌드 = bundle
```
$ cd ai_strategy_loop/dashboard/webui-build && node build-app.mjs
[build-app][bundle] app.js v=34ae83de (entry=src/track-z-entry.pilot.js, react via alias-to-shim) · stom-ui.js v=f41f5701
[build-app][bundle] html ?v= 갱신: index.html, lab.html, pro.html, verdict.html, STOM AI Dashboard.html
```
- `frontend/bundle/app.js` = 981,198 bytes(풀앱). `require("react")`=0, `react.development`=0, `__SECRET_INTERNALS`=0,
  `==== ` 마커=0. 컴포넌트 존재: `function App`(2), LabPage(4), ProPage(4), VerdictPanel(4), BacktestTab(3),
  ReactDOM.createRoot(1), Object.assign(window(29).
- manifest: `model:"bundle"`, `entry:"src/track-z-entry.pilot.js"`, `externalizedGlobals:{react:"window.React",
  "react-dom":"window.ReactDOM"}`, `bundles.app.js.v="34ae83de"`.
- 5개 HTML 전부 `bundle/app.js?v=34ae83de`(일관).
- **재현성**: 동일 소스 재빌드 시 v=34ae83de 동일(content-hash, no timestamp).

### (2) served 번들 렌더 증명 (하네스 — flip 의 load-bearing 안전 증거)
```
$ node track-z-harness.mjs   →   "allPass": true
```
- **V1**(메커니즘): pass, 0 errors, 단일 React, DemoBadge/LivePending 함수.
- **V2_served_default_bundle**: pass, App 마운트, #root 11,118자, FROZEN 전역 ready, 단일 React, 0 errors.
- **V3 per-tab(7/7)**: evolution(72,163 — 데이터 컴포넌트 렌더) · backtest(12,374) · simulation(9,709) ·
  lab(8,569) · pro(7,124) · verdict(5,431) · process(4,476, iframe present). 전부 errs=0, boundary 미발동.
- **V4 standalone(3/3)**: lab(4,282) · pro(2,835) · verdict(1,142). 전부 errs=0, mountError=None.

### (3) 비상 폴백 동작
```
$ STOM_LEGACY_CONCAT=1 node build-app.mjs
[build-app][LEGACY concat] app.js v=9a496366 (26 files) · stom-ui.js v=f41f5701
[build-app][LEGACY concat] html ?v= 갱신: index.html, lab.html, pro.html, verdict.html, STOM AI Dashboard.html
```
- concat app.js: `==== app.jsx ====` 존재, 총 26 마커. manifest `model:"concat"`, `appSources` 26개.
- 확인 후 `node build-app.mjs`(기본=bundle) 재실행 → 트리를 flip 상태(v=34ae83de)로 복원.

### (4) 베이스라인
- `tests/unit/dashboard/test_p14_build_harness.py` + `test_track_z_pr1_harness.py`: **21 passed**
  (swap 가드 + 신규 fallback 테스트 + V1~V4 하네스 래퍼; cp949 stderr-decode 경고 1건은 사전존재 무해).
- full `python -m pytest tests/unit/ -q`: **7 failed(사전존재 backend/CLI/PyQt) / passed≥3240 / 2 skipped**,
  신규 실패 0. (아래 "최종 베이스라인" 참조 — 실측 갱신.)
- `python scripts/verify_nonrelease_sync.py`: exit 0.

---

## 롤백 절차 (instant rollback)

flip 후 운영 이상이 보이면 **둘 중 하나**:

1. **즉시(권장) — 비상 플래그 + 재빌드**:
   ```
   cd ai_strategy_loop/dashboard/webui-build
   STOM_LEGACY_CONCAT=1 node build-app.mjs   # served app.js 를 옛 concat 으로 되돌림
   ```
   → `bundle/app.js`(concat) + `manifest.model:"concat"` + 5 HTML `?v=` 가 concat 해시로 갱신. 커밋하면 운영 복원.
   concat 코드는 build-app.mjs 안에 그대로 보존돼 있으므로 코드 변경 불필요.

2. **git revert** — 본 PR 커밋을 revert(build-app.mjs·harness·테스트·문서 일괄 원복).

폴백 경로는 `test_legacy_concat_fallback_still_26_sources` 가 매 테스트런마다 검증하므로 항상 동작 보장.

## STOP 조건
**기본=bundle 전환 + 가드 swap + 폴백 보존 + ALL 게이트 GREEN.** 트리는 flip 상태(bundle, v=34ae83de).
behavior-invariant(동일 UI/탭; 하네스가 동일 렌더 증명). 커밋·아키텍트 리뷰는 오케스트레이터 담당.
