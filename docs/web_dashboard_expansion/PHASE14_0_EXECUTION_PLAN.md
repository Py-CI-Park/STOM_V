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

## 4. 결정·실측 기록 (2026-06-14 완료)
- **Vite 버전**: 5.4.21 (devDep 11패키지, `npm install` 8s). 빌드 174~315ms.
- **빌드 산출물**: `frontend/poc/index.html`(988B) + `frontend/poc/assets/index-<hash>.js`(~3.45KB, content-hash 파일명 — 14.5 캐시 자동화 미리보기). `emptyOutDir`로 이전 해시 자동 정리 확인.
- **출력 동등성**: PoC 어서션 하네스 **24/24 PASS**(`data-poc-status=PASS`), pageerror 0. 포매터 8종 + 판정 2종 + STATUS_KR 5키 전수 일치. 코드리뷰가 소스 diff(U+2014/U+2212/ko-KR 로케일 포함)+Node 런타임 양쪽에서 바이트 동일 확인.
- **production 무변경(공존 증명)**: `git diff b054644d -- index.html '*.jsx' styles.css app.py` **완전 비어있음**. 변경분=신규 디렉터리 2개(`frontend/poc/`·`webui-build/`)뿐. production `/ui/` 6탭 렌더 **pageerror 0**. → 픽셀 diff보다 강한 구조적 무변경 증거(동적 콘텐츠 노이즈 없음).
- **서빙**: `/ui/poc/`·`/ui/poc/assets/*.js`·`/ui/` 모두 200. **백엔드 라우트/마운트 변경 0**(app.py:3251 StaticFiles 재귀 서빙에 얹음).
- **pytest**: `7 failed, 3185 passed, 2 skipped` — 7건 모두 문서화된 pre-existing(신규 실패 **0**). 브랜치 게이트 `verify_nonrelease_sync.py` exit=0.
- **node/npm 운영**: 산출물(`frontend/poc/`) 커밋, `node_modules`/`.vite` 무시 → **런타임 npm-free 유지**. devDep 취약점 2건은 빌드 도구 한정(운영 영향 0).
- **코드리뷰**: APPROVE (CRITICAL/HIGH/MEDIUM 0, LOW 2 — STATUS_KR 3키 추가 검증·DOM 가드로 반영 완료 → 24/24).

### 다음(14.1) 범위 메모
- 빌드 하네스 정식화: `dist/` vs `poc/` 출력 컨벤션 확정, `frontend/dist/` 커밋 정책 결정(.gitignore 71줄 조정 여부).
- 14.2에서 connection.jsx가 format.mjs를 소비하도록 전환(중복 제거) — 단, index.html 런타임-babel 경로와의 양립/순서 설계 필요.
- 빌드 산출물 커밋이 PR 노이즈를 키우므로(해시 변경 시 diff) 빌드 재현성·CI 빌드 옵션도 14.1에서 검토.
