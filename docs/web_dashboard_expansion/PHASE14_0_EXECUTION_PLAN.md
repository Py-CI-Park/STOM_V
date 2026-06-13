# Phase 14.0 실행계획 — Vite 빌드 PoC (무중단 공존)

> 2026-06-14 작성·승인. 상위: `ROADMAP_PHASE12_PLUS.md` Phase 14, 착수 핸드오프: `PHASE14_0_SPIKE_HANDOFF.md`.
> **목표**: 빌드 도구(Vite)를 정하고, 순수 모듈 1개를 ESM으로 전환해 `/ui/`로 빌드 서빙되는지 + 결과가 동등한지 증명한다. **운영 화면·백엔드·런타임 babel 경로는 절대 바꾸지 않는다(공존 PoC).**

## 0. 결정 (코드 실측 반영)
| 항목 | 확정 | 근거 |
|------|------|------|
| 빌드 도구 | **Vite** | 사용자 선택(HMR·생태계·React 기본) |
| PoC 전환 모듈 | `connection.jsx` 순수 포매터 `fmtScore/fmtPct/fmtMoney/fmtInt/fmtTime` + `STATUS_KR` + `isDemoSource/livePanelPending` (909~941줄) | window·타전역 의존 0, 이미 `Object.assign(window,…)` 노출, index.html 최초 로드(35줄)=기반 모듈 |
| 제외 | `DEFAULT_BASE` | `window.location` 의존(순수 아님) |
| 미채택 후보 | `chart.jsx _axisTicks`(5줄) | window 미노출(파일 사적)·내부 4곳 사용 → 추출 시 production 파일 수정 필요(위험↑) |
| 빌드 워크스페이스 | `ai_strategy_loop/dashboard/webui-build/` (**served `frontend/` 바깥**) | node_modules·소스가 `/ui/`로 노출되지 않음 |
| 빌드 산출물 | `ai_strategy_loop/dashboard/frontend/poc/` (커밋) → `/ui/poc/` **자동 서빙** | StaticFiles 재귀 서빙(`app.py:3251` `StaticFiles(frontend, html=True)`), **백엔드 라우트 불변** |
| node/npm 정책 | 빌드 산출물 커밋(런타임 npm 의존 0), `node_modules` 무시 | 핸드오프 §6 기본 |

## 1. 정밀화 2건 (핸드오프 대비 변경)
1. **산출물 경로**: `.gitignore`가 `frontend/dist/`(71)·`dist/`(21)·`node_modules/`(64)를 무시 → `dist/`에 빌드하면 커밋 안 됨(런타임 npm-free 정책 위반). **`frontend/poc/`(비무시)로 출력**해 커밋. `dist/` 커밋 정책은 14.1에서 결정.
2. **동등성 게이트 재정의**: 순수 포매터는 "픽셀"이 아니라 **출력 문자열 동등성**이 정확한 증명.
   - (a) 빌드 번들 `fmtMoney(x)` === babel경로 `fmtMoney(x)` (테스트 벡터 전수 일치)
   - (b) production 화면이 Phase12-B 6탭 스냅샷과 픽셀 동일(공존이 index.html을 안 건드렸음 증명)

## 2. 절차 (9단계)
1. `feature/webbt-phase14` 브랜치 생성(origin 부모 tip `b054644d`). ✅
2. `webui-build/`에 `package.json`(vite devDep) + `vite.config.mjs`(output→`../frontend/poc/`, base `./`) + `.gitignore`(node_modules).
3. `webui-build/src/format.mjs` — 포매터를 ESM `export` + 로드 시 `Object.assign(window,…)`로 동일 전역 계약 재현.
4. `webui-build/poc.html` — vendor-react 불필요(순수 JS), 빌드 번들 로드 + 인라인 어서션 하네스(테스트 벡터 PASS/FAIL 표시).
5. `npm install` → `npm run build` → `frontend/poc/` 산출물(해시 파일명·HTML 참조 자동 배선) → `/ui/poc/` 자동 서빙 확인.
6. 8771 재기동 → `/ui/poc/`에서 PASS + **기존 `/ui/` 무변화** 동시 확인.
7. Playwright: ① PoC 출력 동등성 캡처 ② production 6탭이 Phase12-B 스냅샷과 동일(`C:/Temp/webbt_phase6_shots/`).
8. 전체 `pytest tests/unit/ -q` 신규 실패 0(런타임 babel 경로 미변경이라 기존 테스트 무영향이어야 함) + 코드리뷰(별도 패스) → PR → 머지 → wt-dev 통합 → 8770 재기동.
9. 결정·실측 + 14.1 범위(빌드 하네스 정식화·`dist/` 커밋 정책) 기록.

## 3. 불변 보장 / 롤백
- index.html 26 스크립트·vendor-babel 경로·백엔드·라우트·URL·styles.css **불변**. 기능/화면 변화 0.
- 브랜치 격리 → 문제 시 `frontend/poc/` + `webui-build/` 삭제로 **잔여 0** 복귀.
- 게이트: 전체 pytest 신규 실패 0(pre-existing 7 제외) + 8771 `/health`·`/ui` 200 + pageerror 0.

## 4. 결정·실측 기록 (착수 후 채움)
- Vite 버전: ____
- 빌드 산출물 크기/파일: ____
- 출력 동등성 결과(테스트 벡터): ____
- production 6탭 스냅샷 동등성: ____
- pytest 신규 실패: ____ (기대 0)
- 다음(14.1) 범위 메모: ____
