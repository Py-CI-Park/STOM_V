# Intent vs. Reality Ledger

| intent_id | expected truth | observed reality | diff | violated invariant | intent source | supporting observations | status | claim ids |
|---|---|---|---|---|---|---|---|---|
| I-01 | AI loop은 STOM 문법으로 유효한 매수·매도 조건식을 자율 생성하고 공식 백테스트로 검증해야 한다. | 조사 중 | 조사 중 | syntax + official evidence | 사용자 요청; `ai_strategy_loop/AGENTS.md` | pending | unknown | pending |
| I-02 | 생성은 결과변수 누수 없이 B_* 및 시점상 이용 가능한 시장 데이터에 기반해야 한다. | 조사 중 | 조사 중 | no leakage | 사용자 요청; root/CLI AGENTS | pending | unknown | pending |
| I-03 | 반복 루프는 단순 무작위 탐색이 아니라 실패 피드백·가설·다양성·재현 가능한 상태를 축적해야 한다. | 조사 중 | 조사 중 | cumulative learning | 사용자 요청; handoff purpose | pending | unknown | pending |
| I-04 | 성과 판정은 비용·MDD·표본수·시간순 OOS·다중검정 위험을 반영해야 한다. | 조사 중 | 조사 중 | robust validation | 사용자 요청; research docs | pending | unknown | pending |
| I-05 | 대시보드/Hall of Fame은 사람 기준과 AI 후보를 같은 정의·기간·비용으로 비교해야 한다. | 조사 중 | 조사 중 | metric comparability | 사용자 요청 | pending | unknown | pending |
| I-06 | 최근 실험 실패는 보고서 오류나 게이트 엄격성 탓으로 오인하지 않고 실행 증거로 설명되어야 한다. | handoff는 v2 8개 전부 no_go, 7개 측정 가능 행 전부 손실·MDD 초과라고 기록 | 원자료 교차검증 필요 | causal evidence | latest handoff | O-pending | unknown | C-pending |
| I-07 | 다음 개발은 닫힌 v2/Plan D 반복이 아니라 실패 메커니즘을 교정한 v3 설계에서 시작해야 한다. | v3 design-only plan 존재, 미실행 | 설계 적절성 검토 필요 | stop discipline | latest handoff | O-pending | unknown | C-pending |

