# Track Z — PR-7 실행 로그 (Retire concat fallback + redundant pilot path)

> 2026-06-16 · 브랜치 `feature/webbt-track-z-pr7-retire-concat` · 워크트리 `STOM_V.wt-webbt`
> 범위: 빌드를 **BUNDLE-ONLY** 로 단순화. PR-6 가 보존했던 비상 concat 폴백(`STOM_LEGACY_CONCAT=1`)과
> 잉여 파일럿 경로(`STOM_BUNDLE=1`)를 **제거**해 P5(9개 대형파일 분해)를 위한 깨끗한 모듈 모델 확보.

## 한 줄 결과

`build-app.mjs` 가 단일 esbuild `bundle:true` 빌드만 남았다. 제거한 것은 **사용되지 않던 빌드 머신리**뿐 —
served `bundle/app.js` 는 **byte-unchanged (`v=34ae83de`)**. 하네스 V1~V4 `allPass`(7탭+3페이지, served 번들,
0 errors, 단일 React). concat 폴백 테스트 1건 제거, build-model 가드는 bundle 불변식으로 유지, 신선도 가드 1건
추가. 전체 unit: 신규 실패 0. `verify_nonrelease_sync.py` exit 0.

## WHY (왜 지금 은퇴하나)

P5 는 9개 대형 `.jsx` 를 다수의 작은 모듈로 분해한다. concat 폴백은 26개 파일을 하드코딩된 `ORDER` 로 이어붙이므로,
분해로 새 파일이 생길 때마다 `ORDER` 에 손으로 추가 + dual-safe 를 영구 유지해야 한다(오류 유발, 게다가 폴백은
실하중에서 미검증). bundle 은 ESM 그래프를 자동 해석하므로 새 모듈에 빌드-스크립트 변경이 불필요. bundle 은
이미 검증됨(8770 라이브, 하네스가 7탭+3페이지 렌더, baseline green). 따라서 깨끗한 모듈 모델을 위해 지금 concat 은퇴.
향후 작업 롤백 = 소형 PR 단위 `git revert`.

## 무엇이 바뀌었나

### 1. `ai_strategy_loop/dashboard/webui-build/build-app.mjs` (핵심)

- **제거**: `buildLegacyConcat()`, `const ORDER`(26 파일), `_stripTopLevelEsm()`(import/export 스트리퍼),
  `==== X.jsx ====` 마커 생성, `STOM_LEGACY_CONCAT=1` 디스패치, `STOM_BUNDLE=1` 파일럿 경로
  (transient `.track-z/app.pilot.js` 빌드 + `manifest.pilot.json`).
- **유지**: `buildServedBundle()`(alias-to-shim react/react-dom, classic IIFE, es2018), `runPostBuild()`
  (content-hash `?v=` → 5개 HTML + `manifest.json{model:"bundle"}`), 엔트리 `src/track-z-entry.pilot.js`.
- **결과**: 환경변수 없이 단일 빌드. `STOM_BUNDLE`/`STOM_LEGACY_CONCAT` 는 더 이상 분기하지 않으므로
  설정해도 기본 bundle 빌드를 산출(no-op).
- 149→ 단일 bundle 경로. net `33 insertions / 116 deletions`.
- bundle/app.js 는 **byte-unchanged**(`v=34ae83de`) — dead 머신리만 제거, 번들 출력은 불변.

### 2. `tests/unit/dashboard/test_track_z_pr1_harness.py`

- `test_build_app_has_flag_path_and_export_stripper` → **`test_build_app_is_bundle_only`** 로 교체:
  bundle 불변식(alias-to-shim + classic IIFE) 유지 + 은퇴 머신리(`_stripTopLevelEsm`/`buildLegacyConcat`/
  `const ORDER`/`process.env.STOM_LEGACY_CONCAT`/`process.env.STOM_BUNDLE`) 부재를 가드.
- `test_track_z_flagged_bundle_has_no_react_require`(파일럿 `.track-z/app.pilot.js` 의존) →
  **`test_served_bundle_has_no_react_require`** 로 교체: served `bundle/app.js` 소스에 직접
  `require("react")`/2nd-React 센티넬 부재 단언(node 불필요).
- **신규 `test_committed_bundle_in_sync_with_source`** (architect nit #1, 신선도 가드): node+esbuild 게이트.
  `node build-app.mjs` 실행 후 `git diff --quiet` 로 커밋된 7개 산출물(bundle/app.js, manifest.json, 5개 HTML)이
  소스와 byte-동기임을 확인. 빌드는 결정론적(content-hash, no timestamp)이라 클린 트리에서 재빌드는 diff 0 —
  소스만 고치고 재빌드를 깜빡하면 즉시 실패. 가드 자체는 클린 트리를 더럽히지 않음(재현가능).
- `test_default_manifest_is_bundle_model` 유지(기본 manifest=bundle).

### 3. `tests/unit/dashboard/test_p14_build_harness.py`

- **제거**: `test_legacy_concat_fallback_still_26_sources`(concat 폴백이 사라짐). 미사용 `import re` 정리.
- **유지**: `test_app_bundle_is_single_entry_graph`(bundle 불변식 — 여전히 보호적),
  `test_content_hash_cache_consistency`(model=="bundle" + no appSources).

### 4. `.jsx` 컴포넌트 — 변경 없음

dual-safe `export {…}` + `import {…} from "./x.jsx"` 라인은 이제 **그냥 정상 ESM**(bundle 이 사용). 제거할
concat 이 없으므로 그대로 둠. `.jsx` 본문/stom-ui/research/backtest 미접촉.

## 게이트 결과

| 게이트 | 결과 |
|--------|------|
| `node build-app.mjs` (DEFAULT) | `app.js v=34ae83de` (model=bundle), diff 0 |
| `STOM_BUNDLE=1 node build-app.mjs` | no-op → `v=34ae83de` (에러 없음) |
| `STOM_LEGACY_CONCAT=1 node build-app.mjs` | no-op → `v=34ae83de` (에러 없음) |
| `node track-z-harness.mjs` | `allPass=true` (V1~V4, 7탭+3페이지) |
| `pytest tests/unit/` | 신규 실패 0 (concat-폴백 테스트 1건 제거로 count 소폭 감소) |
| `verify_nonrelease_sync.py` | exit 0 |

## 롤백

소형 PR 단위 `git revert`. (더 이상 환경변수 비상 폴백 없음 — bundle 이 단일·검증된 경로.)
