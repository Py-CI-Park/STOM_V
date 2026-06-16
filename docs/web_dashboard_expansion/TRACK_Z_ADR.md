# ADR: Track Z — app.js ESM 번들 이관 (esbuild transform-concat → bundle)

> **상태:** CONSENSUS CLOSED (Architect=SOUND, Critic=APPROVE) — 2026-06-15
> **범위:** `frontend/bundle/app.js` 생성 파이프라인 한정. `stom-ui.js` 및 `format.ts`는 이 ADR의 결정 범위 밖.
> **출처:** `track-z-esm-bundle-migration.md` (ralplan Revision 3) 의 ADR 섹션을 독립 문서로 추출.

---

## 결정 (Decision)

`app.js`를 **esbuild `bundle:true`, 단일 엔트리, React/ReactDOM는 alias-to-virtual-shim 방식, 출력은 classic IIFE** 로 이관한다.

- `app.js` 스크립트 태그는 모든 5개 HTML에서 **classic + defer 그대로 유지** (type=module 전환 없음).
- `stom-ui.js` (`format.ts` 엔트리, Vite lib 빌드)는 **AS-IS 유지, 별도 모듈로 먼저 로드** (0.A 경계 결정 — 아래 상술).
- 기본값 전환(concat 폐기)은 **COLLISION_TAX 게이트 충족 후로 연기** (0.B 유예 결정 — 아래 상술).
- Vite(`rollupOptions.output.globals`)는 esbuild pilot이 React 단일 정체성을 증명하지 못할 경우의 **명시적 fallback** (최후 수단이 아닌 현실적 대안).

---

## 0.A — stom-ui.js 경계 결정

**결정: `format.ts` / `stom-ui.js`는 현행 그대로 유지한다. Track Z 번들에 포함하지 않는다.**

### 근거

- `stom-ui.js`의 내보내기(`fmt*`, `STATUS_KR`, `_axisTicks`, `_priceTick`, `_hmsTimeLabel`, `STOM_PIPELINE`, `isDemoSource`, `livePanelPending` 등)는 **`window.*` 참조 계약이 FROZEN** 되어 있다. `connection.jsx:914-919`, `chart.jsx:7`, `backtest-charts.jsx:49`, `sim-live-chart.jsx:46-47`, `simulation-charts.jsx:157-158`, `research-pro.jsx:802`, `research-lab.jsx:1046` 에서 직접 참조하며, `test_p14_build_harness` (lines 107-109, 134)가 이를 단언한다.
- `stom-ui.js`는 **빌드 번들과 구버전 babel fallback 양쪽**에서 `window.*`로 소비된다. 번들에 포함하면 두 독립-캐시 아티팩트가 결합되어 각자의 캐시 무효화 전략을 공유해야 한다.
- **Track Z의 blast radius를 `app.js`만으로 격리**하기 위해 `stom-ui.js`를 별도로 유지한다. 이 경계 덕분에 번들 롤백이 `stom-ui.js` 재빌드 없이 `app.js` 하나만 되돌리면 된다.

### 이 결정이 고정하는 규칙

- stom-ui 호스팅 심볼(`fmt*`, `STATUS_KR`, `_axisTicks` 등)은 Track Z 변환 중에도 **절대 `import`로 변환하지 않는다.**
- `stom-ui.js`의 export 이름·형태를 변경하지 않는다.
- 향후 `stom-ui.js`를 번들에 합치는 것은 Track Z 완료 후 별도 후속 작업으로 진행할 수 있다(현재 범위 밖).

---

## 0.B — 기본값 전환 유예 게이트 (Deferral Gate)

**결정: 빌드 스캐폴딩 + 변환은 `STOM_BUNDLE` 플래그 뒤에서 즉시 진행하되(기본값 OFF, 운영에 no-op), 비가역적 기본값 전환(Story 4) + concat 폐기는 아래 게이트 중 하나가 충족될 때까지 연기한다.**

### 게이트 조건 (둘 중 하나)

- **(A)** COLLISION_TAX 누적 카운터가 **5에 도달**한다.
- **(B)** `test_no_duplicate_globals`가 잡을 수 없는 **가드 회피형 충돌**이 발생한다 (단일 스코프 모델의 구조적 맹점을 노출하는 충돌).

### 근거

- COLLISION_TAX 현재 누적: **2 / 5** (형식 트리거 미충족).
- 플래그-점진적 설계 덕분에 스캐폴딩/파일럿/변환은 기본값 OFF인 동안 운영에 no-op이므로, 게이트 충족 전에 진행해도 거버넌스 위반이 아니다. **가역적 단계는 게이트 없이 진행 가능; 비가역적 전환만 게이트를 기다린다.**
- 현 시점의 구조적 위험은 충분히 `test_no_duplicate_globals`로 통제되고 있다.

### 오버라이드 경로

팀이 "지금 전환"을 선택할 경우, 이 게이트 대비 **서면 명시적 정당화**가 있어야 한다. 보수적 연기가 기본값이다.

---

## 드라이버 (Drivers)

1. **교차-파일 식별자 해석이 핵심 위험면이다 (빌드 도구가 아님).** 26개 파일이 현재 단일 스코프를 공유한다. 동일 심볼이 `<DemoBadge/>`(베어 참조)와 `<window.DemoBadge/>`(방어 참조) 양쪽으로 소비된다. 실제 번들은 각 모듈에 독립 스코프를 부여하여 교차-파일 베어 소비가 명시적 `import` 없이는 `ReferenceError`가 된다. 이것이 지배적 작업이자 지배적 위험이다.
2. **벤더 React 글로벌이 런타임 `require` 없이 외부화되어야 한다.** React/ReactDOM는 npm 패키지가 아니라 `window.React`/`window.ReactDOM`을 설정하는 classic script다. esbuild `external:['react']`는 `require("react")` 를 방출 → "Dynamic require of react is not supported" 충돌. 해결책은 `react` → virtual shim(`export default window.React; export const {useState, …} = window.React;`) alias다.
3. **concat-모델 테스트 결합이 예상보다 ~3배 넓다.** `==== X.jsx ====` ORDER 마커 + `appSources==26` 를 단언하는 파일이 **16개** (재-grep 검증)다. 기존 가드를 단순 삭제하면 커버리지가 가장 위험한 시점에 묵시적으로 하락한다.

---

## 고려한 대안 (Alternatives Considered)

| 대안 | 기각 이유 |
|------|----------|
| **Option B** — esbuild ESM, `app.js`를 `type=module`로 전환 | 5개 HTML의 FROZEN 스크립트-태그 / 마운트 순서 계약을 변경함. classic inline 마운트 스크립트와 모듈 스크립트 간 교차-영역 문제 발생. |
| **bare esbuild `external:['react']`** | 런타임 `require("react")` 방출 → "Dynamic require" 크래시. |
| **M-B** — hook-alias shim 유지 (`const {useState}=React`) | 어차피 각 파일에서 `export` 추가를 위해 건드리므로 alias 정리가 사실상 공짜. COLLISION_TAX 근본 원인(충돌 클래스)을 남겨 두는 것은 Track Z 목표와 상충. |
| **stom-ui.js 번들 합산** | 두 독립-캐시 아티팩트 결합 + FROZEN export 계약 위험 + blast radius 확대. |
| **지금 기본값 전환 (flip-now)** | COLLISION_TAX 2/5 — 형식 게이트 미충족; Story 0.B 유예 게이트가 지배. |

---

## 선택 이유 (Why Chosen)

- **Option A (esbuild bundle + classic IIFE)** 는 FROZEN 계약에 대한 blast radius가 가장 작다. `app.js` 태그가 classic + defer로 유지되므로 5개 HTML과 inline classic 마운트 스크립트가 변경되지 않는다.
- **alias-to-shim**은 글로벌(non-npm) React에서 esbuild가 단일 React 정체성을 제공할 수 있는 유일한 메커니즘이다.
- **플래그-점진적 + 2단계 전환** 설계는 "가역적 단계"와 "베이스라인 무회귀"를 동시에 만족시킨다.
- **Option C (Vite)**는 esbuild pilot에서 React 단일 정체성 실패 시 현실적 fallback으로 유지된다 (Vite의 `rollupOptions.output.globals`가 이 문제를 natively 해결하므로).

---

## 결과 (Consequences)

**양(+)의 결과**
- 26개 파일이 독립 모듈 스코프를 얻는다 → 충돌 클래스 구조적 불가능.
- 18개 hook alias (16개 파일) 정리됨.
- entry 모듈이 유일한 FROZEN 글로벌 퍼블리셔가 됨 (명시적 `Object.assign(window, { LabPage, ProPage, VerdictPanel })`; verbatim 문장 보존).
- 런타임 게이트(Story 1 하니스)가 FROZEN 글로벌 도달 가능성을 소스-문자열이 아닌 런타임으로 단언함.

**음(-)의 결과 / 비용**
- 각 .jsx 파일에 `import`/`export` 추가 필요 (26개 파일 수정).
- 16개 결합 테스트 파일 + 3개 빌드-모델 테스트 마이그레이션 (Story 5에서 선처리).
- 런타임 하니스(node+jsdom 또는 Playwright)를 새로 구축해야 함 (기존 없음).
- stom-ui `window.*` alias 는 보존 (변환 불가 — HARD rule); 각 파일 변환 중 실수 위험이 있어 Story 2 의존성 맵이 선결 조건.

**불변 사항**
- `ORDER` + `==== X.jsx ====` 마커는 Story 4 전까지 제거되지 않는다.
- `stom-ui.js` export 이름·형태 불변.
- 모든 5개 HTML의 `?v=` content-hash 자동화 보존.
- 런타임 npm-free (빌드 아티팩트 커밋 유지).

---

## 후속 작업 (Follow-ups, Track Z 범위 밖)

- 대형 파일 9개 분해 (backtest-charts 2868줄, backtest 2204줄, simulation-charts 1836줄, chart 1739줄, simulation 1490줄, research-lab 1268줄, research-pro 1042줄, connection 927줄, panels 907줄) — Track Z 완료 후 언블록됨.
- Track Z 안정화 이후 `stom-ui.js`의 번들 합산 검토 (현재 범위 밖).
- Playwright 하니스의 포트 설정 가능화 (하드코딩 8770 제거) — Story 1 내에서 처리.
