# Phase 14.6 — TypeScript 점진 도입 (선택 · 시드)

> 2026-06-14 완료. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 선행: `PHASE14_5_CONTENT_HASH.md`.
> **목표(이 단계 범위)**: TS 타입체크 경로를 확립하고, 빌드 소스 모듈 1개를 `.ts` 로 전환해 점진 TS 도입의 시드를 만든다. 동작 변화 0.

## 범위 결정 (선택 단계)
20,000줄 규모의 기존 vanilla-JS 컴포넌트를 전면 타이핑하는 것은 동작하는 내부 툴에 비해 ROI 가 낮다. 따라서 14.6 은 **인프라 + 순수 모듈 1개(format)** 만 TS 로 전환하는 최소 시드로 한정한다. 나머지 `.jsx` 의 TS 화는 필요 시 후속.

## 무엇이 바뀌었나
- `webui-build/tsconfig.json` 신규: strict·noEmit·DOM lib, `src/**/*.ts` 만 대상(런타임 .jsx 비대상).
- `webui-build/src/format.mjs → format.ts`: 포매터/판정/`_axisTicks` 에 타입 명시(`unknown` 입력·반환 타입·`RunStateLike` 인터페이스). 런타임 코드·window 전역 계약 불변.
- `package.json`: `typescript` devDep + `typecheck`(tsc --noEmit) 스크립트.
- `vite.config.mjs`: lib entry `format.mjs → format.ts`(Vite/esbuild 가 .ts 네이티브 처리, 타입 strip → 동일 JS).
- 테스트(test_p14): `format.mjs` 경로 참조 → `format.ts`.

## 검증
- **typecheck**: `npm run typecheck`(tsc --noEmit) exit 0(strict 통과).
- **빌드 동등**: format.ts → stom-ui.js 빌드 성공. window 노출(fmt*·_axisTicks·STATUS_KR) 보존. (TS 출력 포매팅 차이로 content-hash 만 자동 변경 504ab1d4→ac59ac0e, HTML 자동 갱신.)
- **실화면**: 8771 `/ui/` `window.fmtMoney(1234567)="+1,234,567원"`·`_axisTicks` 함수·6탭 0 pageerror.
- **게이트**: 전체 pytest 신규 실패 0 + `verify_nonrelease_sync.py` exit 0. (소규모·검증완료 TS 시드로 자동검증=typecheck+빌드+Playwright 를 품질 게이트로 사용.)

## 다음 (14.7 — 완결)
lab.html·pro.html·STOM AI Dashboard.html(아직 런타임 babel) 의 컴포넌트도 빌드 번들로 전환하고, `vendor-babel.js` 파일을 저장소에서 완전 제거(런타임 babel 의존 0).
