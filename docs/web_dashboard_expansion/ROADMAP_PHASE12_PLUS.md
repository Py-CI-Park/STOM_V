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

### 동기 (현 아키텍처의 부채)
- in-browser Babel 트랜스폼(런타임 컴파일 — 첫 로드 느림)
- window 전역 + 수동 로드 순서 의존(전역 충돌·순서 깨짐 위험)
- 수동 캐시 계약(`?v=` + 계약 테스트 락스텝 — 매 변경 수작업)
- 대형 단일 jsx(simulation-charts.jsx 1600줄+)

### 이전안 (단계적·무중단)
1. Vite(또는 esbuild) 빌드 도입 — 기존 jsx를 모듈로 점진 전환(window 전역 → import/export). 빌드 산출물을 같은 `/ui/` 경로로 서빙해 백엔드·URL 불변.
2. 대형 jsx 분할(차트별 모듈), TS는 선택(점진 도입 가능).
3. 캐시는 빌드 해시(content-hash)로 자동화 → 수동 `?v=` 계약 폐지.
4. **게이트 강화 필수**: 전환 전후 Playwright 전탭 스냅샷 동등성(픽셀 회귀 0)·전체 pytest 유지. 한 모듈씩 전환·검증(빅뱅 금지).

### 리스크·완화
- 전 화면 회귀 위험 → 모듈 단위 점진 + 스냅샷 동등성 게이트(Phase 12-B에서 만든 기준선 활용).
- 백엔드 무예외 계약·라우트는 불변(프런트 빌드만 교체).
- 롤백: 빌드 도입 전 커밋으로 즉시 복귀 가능(브랜치 격리).

---

## 즉시 실행 권장
**Phase 12(A+B)부터 착수** — 낮은 위험으로 현재 ~97%를 깔끔히 마감·고정하고, 그 기준선(스냅샷)이 이후 C·D의 회귀 안전망이 된다.
