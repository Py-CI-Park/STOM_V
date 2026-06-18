# Phase 14.1 — 정식 빌드 하네스 (Vite lib · babel 폴백 양립)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_0_EXECUTION_PLAN.md`.
> **목표**: 14.0의 일회용 PoC(`/ui/poc/`)를 폐기하고, 운영 화면이 실제로 로드하는 **정식 빌드 번들**을 만든다. `connection.jsx`(런타임 babel)는 그대로 둬 **양립(=babel 폴백)** 을 실현. 화면 동작 변화 0.

## 한 줄 요약
`webui-build/src/format.mjs` → Vite **lib 모드** → `frontend/bundle/stom-ui.js`(커밋) → `index.html`이 `<script type="module">`로 로드 → `window.fmt*` 세팅. 빌드 번들이 **운영 경로에 실제 진입**했고, `connection.jsx`도 동일 전역을 세팅하므로 안전(이중 보장).

## 14.0 → 14.1 무엇이 달라졌나
| | 14.0 (PoC) | 14.1 (하네스 정식화) |
|---|---|---|
| 빌드 출력 | `frontend/poc/`(일회용 시험페이지) | `frontend/bundle/stom-ui.js`(운영 번들, 커밋) |
| Vite 모드 | app 모드(index.html 엔트리) | **lib 모드**(format.mjs 엔트리, 고정 파일명) |
| 운영 진입 | ❌ `/ui/poc/`는 아무도 안 씀 | ✅ `index.html`이 실제 로드 → 운영 경로 진입 |
| 검증 | 격리 시험페이지 24/24 | **실 `/ui/` 화면**에서 window.fmt* 출력 동등 |
| 폐기 | — | 14.0 throwaway(poc/·webui-build/index.html·poc-main.mjs) 제거 |

## 핵심 설계 결정
- **출력 디렉터리 = `frontend/bundle/`**: `.gitignore`가 `build/`(19)·`dist/`(21)·`frontend/{build,dist}/`(71·72)를 무시 → 산출물 커밋 정책 위반. gitignore negation은 부모 디렉터리 제외 규칙으로 불안정 → **무시되지 않는 `bundle/` 사용**(검증: `git check-ignore` exit 1).
- **고정 파일명 `stom-ui.js`**: `index.html`이 정적 참조 가능. 수동 `?v=` 캐시 계약 유지(content-hash 자동화는 14.5).
- **양립(babel 폴백)**: `connection.jsx`의 포매터 정의는 **유지**. 번들과 babel 둘 다 동일 `window.fmt*` 세팅 → de-dup(connection.jsx에서 제거)은 14.2.
- **로드 순서 안전성**: ESM 모듈은 DOMContentLoaded(babel가 .jsx 실행) **이전**에 실행 → `window.fmt*`가 React 렌더 전에 세팅. 게다가 소비처는 전부 렌더타임 호출이고 `typeof window.X === "function"` 가드/babel-스코프 폴백을 가져 **구조적으로 안전**(번들 미로드여도 깨지지 않음).

## 검증 (전부 통과)
- **실화면 동등성**: 8771/8770 실 `/ui/`에서 번들 네트워크 로드 확인 + `window.fmtMoney(1234567)="+1,234,567원"`·음수 U+2212·`STATUS_KR.running="실행중"` 등 출력 ALL OK, 6탭 pageerror 0, 화면 무변화.
- **회귀 가드 테스트**: `tests/unit/dashboard/test_p14_build_harness.py` 4/4 — 번들 커밋·완전성·index.html 로드·**connection.jsx↔format.mjs 락스텝(드리프트 차단)**·throwaway 폐기 확인.
- **게이트**: 전체 `pytest tests/unit/ -q` = `7 failed(전부 pre-existing)·3189 passed`·**신규 실패 0**. `verify_nonrelease_sync.py` exit=0.
- **코드리뷰**: APPROVE (CRITICAL/HIGH 0). 로드 순서 안전성 = 모듈 defer + babel 스코프 폴백 + 호출부 `typeof` 가드 3중.

## 다음 (Phase 14.2 — 리프/유틸 실전 전환)
- `connection.jsx`에서 포매터 정의 **제거**(de-dup) → `window.fmt*`를 번들만 제공(첫 진짜 전환).
- chart.jsx `_axisTicks` 등 다른 의존 없는 헬퍼도 번들로 이전.
- 게이트: 전탭 스냅샷 동등 + pytest 무변 + 락스텝 테스트가 de-dup 반영하도록 갱신.
- (14.5 예고) 고정 파일명 → content-hash + 매니페스트, 번들 신선도 자동 검증.
