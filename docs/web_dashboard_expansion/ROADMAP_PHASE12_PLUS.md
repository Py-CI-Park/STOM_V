# 웹 대시보드 로드맵 — Phase 12+ (A 마감·B 검증·C 분석강화·D 기반현대화)

> 2026-06-13 · 현재 완성도 ~97%(Phase 6~11 완료, PR #42~#48 머지). 사용자 지시: A+B+C+D 전체를 단계 계획으로.
> 프로세스(모든 단계 공통): wt-webbt 분리 개발 → 게이트(전체 pytest 신규 실패 0·vendor-babel·8771 스크린샷) → 코드리뷰 → PR → 머지 → wt-dev 8770. 캐시 per-asset 락스텝.

## 시퀀싱 원칙 (의존성)
1. **A+B 먼저** — 현재 완성분을 "깔끔히 마감·고정"한 뒤 신기능을 얹어야 회귀 표면이 작다. (정리 안 된 위에 기능 추가 = 부채 누적)
2. **C는 그 다음** — 기능 추가는 안정된 베이스라인 위에서.
3. **D는 분리·후순위** — 화면 변화 0의 대형 리팩터. A~C와 독립이며, 잘못되면 전 화면 회귀 위험이 커 별도 사이클·별도 승인.

권장 순서: **Phase 12(A+B) → Phase 13(C) → Phase 14(D, 선택)**.

---

## Phase 12 — 마감 정리 + 라이브 검증 (A+B) · 비용 낮음 · 위험 낮음

### §A. 마감 정리 (리뷰 잔여 LOW/MEDIUM 일괄)
| 항목 | 출처 | 파일 |
|------|------|------|
| 죽은 CSS 제거(.process-flow-row/.process-box* ~40줄) | Phase11 리뷰 LOW | styles.css |
| 플로우 스크롤 어포던스 정리(또는 minWidth로 실제 스크롤) | Phase11 리뷰 LOW | phase-detail.jsx |
| 엔진 게이지 "Progress" 라벨 명확화(Overall vs 세대내) | Phase11 리뷰 LOW | engine.jsx |
| footprint 호가단위 경계 교차 시 bar별 tick 계산 | Phase6 리뷰 MEDIUM | simulation-charts.jsx |
| net_qty null/0 구분(`!=null && isFinite`) | Phase6 리뷰 LOW | sim-live-chart.jsx·simulation-charts.jsx |
| vwap σ 수치안정형(선택) | Phase8 리뷰 LOW | replay_engine.py |

### §B. 라이브 검증 + 회귀 스냅샷 고정
- 실데이터 run으로 **콤보 히트맵·프로세스 흐름 육안 확정**(현재 run은 조합 데이터 0이라 빈상태만 확인됨 — 데이터 있는 run 선택해 그리드/노드 렌더 확인).
- Playwright 시각 회귀 세트 정식화: 6탭 각 핵심 화면 스냅샷을 `C:/Temp` out-of-tree 하네스로 1회 캡처해 기준선 박제(향후 회귀 비교용). pytest 게이트 아님(수동 QA 증거).
- 게이트: 전체 pytest 신규 실패 0 + vendor-babel + 8771 스크린샷.

---

## Phase 13 — 분석 기능 강화 (C) · 비용 중간 · 위험 중간

감사에서 90%대로 남은 "잔손" 기능 완결. 파일 소유 분리 트랙.

| 트랙 | 기능 | 파일 |
|------|------|------|
| C-1 | 백테 결과 **비교 오버레이↔분할 토글**(현재 오버레이만) | backtest.jsx·backtest-charts.jsx |
| C-2 | **파라미터 스윕 빌더 UI**(현 스윕 모드는 라벨만 — 바운드/스텝 입력 폼 + /bt/run sweep 파라미터 라우팅) | backtest.jsx·backtest_api.py |
| C-3 | 시뮬 **LWC 신호 마커 패리티**(현재 신호 마커가 SVG/라이브만 — LWC에도) | simulation-charts.jsx |
| C-4 | 체결 로그 **CSV 내보내기** | simulation.jsx |
| C-5 | (선택) 변수 조합 매트릭스 **드릴다운**(셀 클릭→쌍별 상세) | research-lab.jsx |

게이트: 각 트랙 backend 순수함수 단위테스트 + 소스/구조 테스트 + 전체 스위트 신규 실패 0.

---

## Phase 14 — 기반 기술 현대화 (D, 선택·대형) · 비용 높음 · 위험 높음

> 화면 변화 0, 개발 생산성·유지보수성↑. A~C와 독립. **별도 승인 후 단독 사이클**.
> 착수 핸드오프 상세: `docs/web_dashboard_expansion/PHASE14_0_SPIKE_HANDOFF.md`.

### 1. 동기 — 현 구조의 부채 (2026-06-14 실측)
| 부채 | 실측 | 문제 | Vite 후 |
|---|---|---|---|
| in-browser Babel 런타임 변환 | vendor-babel.js가 jsx **26개**를 브라우저서 매 로드 컴파일 | 첫 로드 지연·CPU 낭비 | 빌드 1회 컴파일 |
| window 전역 + 수동 로드 순서 | `Object.assign(window,…)` **26곳**, index.html 26 스크립트 순서 의존 | 순서 깨지면 ReferenceError(Phase6.1 lab.html 크래시 전례) | import/export 자동 의존성 |
| 수동 캐시 계약 | `?v=` + 계약 테스트 **3파일** 락스텝 | 매 변경 수작업·휴먼에러 | content-hash 자동 |
| 대형 단일 파일 | backtest-charts **2,814줄**·backtest 2,152·sim-charts 1,842 (총 20,296줄) | 파악·변경 난이도 | 모듈 분할 |
| TS 부재 | 전부 순수 JS | 타입 안전망 없음 | (선택) 점진 TS |

### 2. 단계별 작업 리스트 (무중단·점진)
| 단계 | 작업 | 위험 | 게이트 |
|---|---|---|---|
| **14.0 스파이크·결정** | Vite vs esbuild 선정, 1개 모듈만 ESM 전환해 `/ui/` 동일 경로 빌드 서빙 PoC, 시각 동등성 기준 확립 | 낮음 | Phase12-B 6탭 스냅샷 == PoC 픽셀 동등 |
| **14.1 빌드 하네스** | package.json·vite.config·출력 dir·base 경로, FastAPI가 빌드 산출물 서빙. 런타임 babel 폴백 유지(양립) | 중간 | 빌드 성공 + 화면 무변화 |
| **14.2 리프/유틸 전환** | 의존 없는 헬퍼부터(connection·chart 순수함수) import/export화 | 낮음 | 전탭 스냅샷 동등 + pytest 무변 |
| **14.3 중간 컴포넌트 전환** | backtest-charts·simulation-charts **모듈 분할 동시 수행**(2,814/1,842줄→차트별) | 중간 | 차트 픽셀 회귀 0 |
| **14.4 탭 셸·app.jsx 전환** | 탭 + 오케스트레이터 마지막 전환(최대 폭발 반경) | **높음** | 6탭 전수 스냅샷 + WS/페이싱 회귀 0 |
| **14.5 캐시 계약 폐지** | `?v=` 수동 핀 → content-hash, 계약 테스트 3파일 → 빌드 매니페스트 검증 | 중간 | 신방식 계약 통과 |
| **14.6 TS 점진(선택)** | ESM 안정 후 .ts 점진(allowJs) | 낮음 | tsc 통과·런타임 동일 |
| **14.7 정리** | vendor-babel.js 런타임·window shim 제거 | 중간 | 전 게이트 + 스냅샷 동등 |

### 3. 변경 vs 유지 (불변 보장)
| 항목 | Phase 14 |
|---|---|
| 백엔드(FastAPI·라우트·무예외) | **불변** — 프런트 빌드만 교체 |
| `/ui/` URL·8770/8771 | **불변** — 산출물 동일 경로 서빙 |
| 화면·UX·기능 | **불변(목표)** — 픽셀 동등성 게이트로 강제 |
| dashboard pytest(475+) | 유지(소스 grep 계약은 ESM 후 일부 조정) |
| 워크트리→PR→wt-dev | **불변** |

### 4. 리스크 레지스터
| 위험 | 완화 | 롤백 |
|---|---|---|
| 전 화면 회귀 | 모듈 단위 점진 + Phase12-B 스냅샷 동등성 게이트(빅뱅 금지) | 빌드 도입 전 커밋 즉시 복귀(브랜치 격리) |
| node/npm 운영 의존 | 빌드 산출물 커밋(런타임 npm 불필요)·14.1 babel 폴백 | — |
| 분할 중 컴포넌트 누락 | 분할 전후 window export 목록 == 검증 | 파일 단위 되돌림 |
| 캐시 전환 혼선 | content-hash가 수동 핀보다 안전 | — |

### 5. 결정 포인트 (착수 전)
| 질문 | 옵션 |
|---|---|
| 빌드 도구 | **Vite**(권장·HMR·생태계) vs esbuild(경량) |
| node/npm 운영 | 빌드 산출물 커밋 vs 서버 빌드 |
| TS | 이번 포함 vs ESM 안정 후 별도 |
| 범위 | 14.0~14.5(핵심) vs 14.7까지(완전 청산) |

---

## 진행 현황
- ✅ **Phase 12(A 마감 + B 검증)** — PR #50 머지·라이브
- ✅ **Phase 13(C 분석 기능 강화)** — PR #51 머지·라이브
- ⏳ **Phase 14(D 기반 현대화)** — 진행 중:
  - ✅ 14.0 스파이크(Vite 결정 + 격리 PoC) — PR #53 머지·라이브. `PHASE14_0_EXECUTION_PLAN.md`
  - ✅ 14.1 빌드 하네스(lib 번들 `frontend/bundle/stom-ui.js` + index.html 로드, babel 폴백 양립) — `PHASE14_1_BUILD_HARNESS.md`
  - ⏳ 14.2 리프/유틸 전환(connection.jsx de-dup) → 14.7 정리
