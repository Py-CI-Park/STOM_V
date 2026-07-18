# UXR-P6 — Backtest gap: 웹 구현 인벤토리 + parity matrix (§10-2)

- 작성: 2026-07-18 · 브랜치: `uxr-p6-backtest`
- 원칙: **이식 아님 — 현 웹 구현 inventory → python GUI parity → 결손만 보강.**
  검토 §3(P5 "port" 오진단 High) 반영: 현 웹 백테스트는 이미 광범위하다.

## 1. 현 웹 백테스트 표면 (실측 인벤토리)

### 컴포넌트 (12 bt-*.jsx)
| 파일 | 역할 |
|---|---|
| bt-tab-root.jsx | 탭 루트·health·전략명 목록 오케스트레이션 |
| bt-tab-run.jsx | 실행 스펙(전략/기간)·`/bt/run`·job 진행·취소·메타 |
| bt-tab-library.jsx | 전략 CRUD(저장/삭제/검증)·변수 추출 |
| bt-tab-analysis.jsx | overlay·A/B·portfolio 분석 |
| bt-tab-mode-results.jsx | 모드별 결과 |
| bt-result-area.jsx | 결과 영역(메트릭·차트 호스트) |
| bt-equity-charts.jsx | 누적수익/낙폭 곡선 |
| bt-distribution-charts.jsx | 분포(손익 히스토그램 등) |
| bt-stat-panels.jsx | 지표 패널 |
| bt-gui-parity.jsx | **GUI parity 뷰(이미 존재)** |
| bt-chart-utils / bt-tab-utils | 공용 유틸 |

### 엔드포인트 (13 `/bt/*`)
- 읽기: `/bt/health` · `/bt/data_range` · `/bt/jobs` · `/bt/job` · `/bt/strategies`.
- Mutation(capability 게이트): `POST /bt/run`·`/bt/job/cancel`·`/bt/job/meta`·`/bt/portfolio`(SAFE_BACKTEST); `POST /bt/strategy`·`/bt/strategy/delete`·`/bt/strategy/validate`·`/bt/extract_vars`(STRATEGY_WRITE).
- Monte Carlo·portfolio 결합·A/B overlay 이미 구현.

## 2. Mutation 경계 (§10-4 — 이미 준수 확인)

- 모든 실행/전략 mutation은 `security_capabilities.py: HTTP_CAPABILITIES`로 capability 분류 + 세션 + origin 게이트.
- 취소는 `_confirmBacktestDanger`(v4-backtest.jsx)로 명시 확인 다이얼로그.
- demo 모드에서 mutation 전면 inert(`if (isDemo) return`).
- **결론: mutation 경계는 신규 설계 불필요 — 기존 계약 유지.**

## 3. Parity matrix (python GUI ↔ 웹) — 다음 단계 연구

현 웹 표면은 실행·전략CRUD·equity/분포/지표·GUI parity·portfolio·A/B까지 포함해 광범위하다.
**진짜 결손 식별은 `ui/`(PyQt 백테스트 화면)·`backtest/`(엔진) 대비 field-level 비교가 선행**돼야 하며, 이는 별도 연구 패스다(추측성 신규 UI 금지).

| 축 | 웹 상태 | GUI 비교 필요 |
|---|---|---|
| 실행 스펙(전략·기간·유니버스) | bt-tab-run | 파라미터 완전성 대조 |
| 진행/취소/job 이력 | bt-tab-run·/bt/jobs | ✓ 존재 |
| equity·drawdown | bt-equity-charts | 축·기간 해상도 대조 |
| 분포·거래 통계 | bt-distribution·stat-panels | 지표 항목 대조 |
| GUI parity 뷰 | bt-gui-parity | **이미 parity 전용 컴포넌트 존재** |
| portfolio·A/B | bt-tab-analysis | ✓ 존재 |
| Monte Carlo | bt-result-area | ✓ 존재 |

## 4. 판정

- P6는 "이식"이 **이미 대부분 완료**된 상태 — 남은 것은 (a) GUI field-level parity 대조로 **미세 결손** 식별, (b) 결손만 보강.
- 추측성 대규모 재작성은 검토가 명시적으로 경고한 오진단이므로 **하지 않는다.**
- 다음 실행: `ui/` 백테스트 화면 ↔ 웹 field 대조표 완성 → 확인된 결손 항목만 티켓화 후 보강.

## 5. 다음(P7 History·Reports)

- History stable identity·join·pagination(§10-10) + Reports 보안 계약(iframe sandbox/CSP/traversal·inline JS 금지, §10-5). P7은 보안 설계가 선행.
