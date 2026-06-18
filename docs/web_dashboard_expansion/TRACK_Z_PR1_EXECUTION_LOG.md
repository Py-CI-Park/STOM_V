# Track Z — PR-1 실행 로그 (Story 0 + Story 1)

> 2026-06-15 · 브랜치 `feature/webbt-track-z-pr1` (부모 `lazycodex/tick-sparse-positive-generation-improvement-20260604` 기준) · 워크트리 `STOM_V.wt-webbt`
> 범위: **PR-1 only** — ESM 번들 골격을 **플래그(STOM_BUNDLE) 뒤, 기본 OFF**로 구축하고 파일럿 1개로 메커니즘 증명. Story 2~5는 미착수. **전환(flip)·concat 은퇴 없음.**
> 계획서: `.omc/plans/track-z-esm-bundle-migration.md` · 합의: Architect=SOUND, Critic=APPROVE.

## 한 줄 결과
esbuild `bundle:true` 플래그 경로가 파일럿에서 **클린 빌드 + `require("react")` 0 + 2nd-React 센티넬 0 + window 재배포 + 런타임 단일 React 정체성/훅 디스패치**를 달성. 기본 빌드(플래그 OFF) **바이트 불변**. **신규 실패 0 / 통과 +9**. Vite 폴백 불필요.

> **정직성 단서(아키텍트 nit#1)**: 이 파일럿은 phase-detail.jsx의 `const {useState_ph}=React`(자유 전역참조)를 유지하므로 **bare `import {useState} from "react"` → shim 경유 경로 자체는 파일럿이 직접 실행하지 않는다.** alias-to-shim 메커니즘의 정확성은 (a) build-app.mjs의 alias 설정 + (b) 아키텍트 독립 probe(`import`가 `var React=window.React`로 해소됨 확인)로 증명됐고, (c) 하네스가 `useState`를 `window.React`로 호출하는 Probe 컴포넌트로 **단일-React 훅 디스패치**를 런타임 검증(nit#2 반영)한다. **전체 shim 경유(파일에 `import` 부여)는 Story 3 변환에서 실행/검증**한다.

## Story 0 — 결정 문서 (코드 무변경)
- **0.A stom-ui 경계**: `format.ts`/`stom-ui.js`는 **현행 유지(AS-IS), 첫 모듈로 별도 로드**. 번들에 합치지 않음 → Track Z 폭발반경을 app.js로 한정. (`TRACK_Z_ADR.md` 신설)
- **0.B 연기 게이트**: 충돌세 **2/5** → 정식 트리거(5) 미달. 플래그 뒤 준비작업은 지금, **되돌리기 어려운 기본 전환(Story 4)은 5 도달 또는 가드-회피 충돌 시까지 보류**. (`COLLISION_TAX.md`에 Go-Signal 기록, tally 미증가)

## Story 1 — 구현
### 신설 파일
| 파일 | 목적 |
|------|------|
| `webui-build/src/react-shim.js` | `export default window.React` + 훅 named re-export. bare `react`를 alias |
| `webui-build/src/react-dom-shim.js` | `window.ReactDOM`(createRoot 등) re-export. `react-dom`/`react-dom/client` alias |
| `webui-build/src/track-z-entry.pilot.js` | 플래그 파일럿 엔트리: `import {DemoBadge,LivePending} from phase-detail.jsx` → `Object.assign(window,{...})` |
| `webui-build/track-z-harness.mjs` | node+jsdom 런타임 하네스 (V1 파일럿 + V2 index), JSON 출력, 둘 다 통과 시 exit 0 |
| `tests/unit/dashboard/test_track_z_pr1_harness.py` | pytest 래퍼: 소스계약 6 + node-gated 하네스 3 (node/esbuild/jsdom 부재 시 skip, test_phase9 패턴) |

### 수정 파일
| 파일 | 변경 |
|------|------|
| `webui-build/build-app.mjs` | `STOM_BUNDLE=1` 플래그 경로(esbuild bundle:true·IIFE·alias-to-shim·출력은 gitignore `.track-z/app.pilot.js`·`bundle/` 손대기 전 `process.exit(0)`); `_stripTopLevelExports` 추가해 concat 루프에 적용 |
| `frontend/phase-detail.jsx` | 말미 1줄 `export { DemoBadge, LivePending };` (ESM dual-safe; 기존 `Object.assign(window,...)` 유지) |
| `webui-build/.gitignore` | `.track-z/` 추가 |
| `webui-build/package.json` | `jsdom ^26.1.0` devDependency + `harness` 스크립트 |
| `webui-build/package-lock.json` | jsdom 반영(오프라인 캐시) |

### export/concat 충돌 해결
top-level `export {...}`는 레거시 concat(classic script 연결)을 깨뜨림. 해결: phase-detail.jsx는 한 줄 `export`를 유지하고, **기본 concat 경로가 `_stripTopLevelExports`(라인 정규식 `^\s*export\s*\{[^}]*\}\s*;?\s*$`)로 transform 전에 제거**. 검증: 매칭은 phase-detail.jsx:787 단 1건, 빌드된 app.js에 `export {` 누출 0, 플래그 번들은 `import`로 소비.
> 참고(Story 3 대비): 현 strip은 `export {…}` 한 줄 형태만 처리. Story 3에서 `export default`/`export function`/다중행 형태를 26파일로 확장할 때 robust화 필요 — PR-1 파일럿엔 충분.

### 하네스: node+jsdom 채택 (Playwright 아님)
jsdom 부재(전역 `npm ls -g`의 jsdom은 UNMET-OPTIONAL 유령) → test 전용으로 `webui-build/node_modules`에 설치(서빙 런타임은 npm-free 유지). 해결한 jsdom 특이점: (1) jsdom은 `<script type=module>` 미실행 → stom-ui(format.ts)를 하네스용 classic IIFE로 번들해 `window.fmt*` 설정; (2) jsdom은 `fetch`/`WebSocket` 부재 → App의 `useBackend`(`/health→/config/spec→/status→WS`)에 계약 유효 IDLE_STATE + onopen 발화 WS 스텁 주입(데모-시뮬레이터 경로 회피). **가장 어려운 INDEX 경로(vendor-lightweight-charts 로드)로 검증**, 파일럿만이 아님.

## HARD 게이트 증거
- **G1 (플래그 OFF 바이트 불변)**: `node build-app.mjs` → `app.js v=5d10d7ab (26 files)`; `git diff --stat -- bundle/app.js`·`index.html` = **EMPTY**. (status에 bundle/app.js 미등장 — 오케스트레이터 재확인)
- **G2 (플래그 번들 react require 없음)**: `STOM_BUNDLE=1 node build-app.mjs` → exit 0; `.track-z/app.pilot.js` grep: `require("react")`=0, `react.development`=0, `__SECRET_INTERNALS`=0.
- **G3 (베이스라인)**: `python -m pytest tests/unit/ -q` → **8 failed, 3237 passed, 2 skipped**; `python scripts/verify_nonrelease_sync.py` → exit 0.
- **G4 (하네스 V1+V2)**: `node track-z-harness.mjs` → `host: node+jsdom`; V1 pass(DemoBadge/LivePending 함수·단일 React 정체성·dynReq 0); V2 pass(App 함수·#root 10988자·errors 0); `ALL PASS: True`, exit 0.

## 베이스라인 8 vs 7 — 오케스트레이터 독립 검증 결과
브리프 기대치는 "7 failed"였으나 현재 부모 브랜치는 **8 failed**. 8번째는 `test_phase9_spa_tabs.py::TestDashboardPages::test_verdict_append_only_post_and_checklist` (`:70 assert "const ICON = {" in dashboard-pages.jsx`).
- 독립 검증: **committed parent의 dashboard-pages.jsx에 `const ICON = {` 0건**(P7가 `_VDT_STATUS_ICON`으로 이동). Track Z는 dashboard-pages.jsx도 해당 테스트도 **건드리지 않음**(`git status`로 확인). → **Track Z 유무와 무관하게 동일 실패 = 선재(pre-existing) 결함**.
- 원인: P7(#74) ICON→_VDT_STATUS_ICON 리팩터 시 이 assertion 미갱신. 핸드오프의 "7 failed" 핀이 이 머지 이후 **8로 드리프트**한 것. **Track Z 책임 아님 / 범위 밖**(별도 1줄 테스트 수정으로 처리 가능).
- **Track Z 순효과: 신규 실패 0, 통과 +9(신규 하네스 테스트), 기본 산출물 바이트 불변.**

## 사용 도구
esbuild(Vite 폴백 미발동). 파일럿/하네스 스크래치는 gitignore `webui-build/.track-z/`(스테이징 안 됨).

## 미커밋 상태
실행자들은 커밋/스테이징 안 함. 오케스트레이터가 아키텍트 검토 + deslop + 회귀 재확인 후 단일 커밋 → 부모로 PR(머지 보류, 사용자 확인).
