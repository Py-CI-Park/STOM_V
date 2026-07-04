# 2026-06-19 Combined Portfolio Simulation Next Research Handoff

## 결론

이번 새 연구는 완료됐다. `저시총 제외 방어 조합`은 연구상 `combined_research_supported_not_production_ready`로 정리한다.

## 핵심 수치

| 항목 | 값 | 증거 타입 |
|---|---:|---|
| r8 low-cap 공식 OOS 총수익 | 7,292,861원 | 공식 OOS |
| r8 low-cap 공식 OOS 최악 MDD | 19.09% | 공식 OOS |
| combined portfolio 전체 수익 | 39,402,438원 | 포트폴리오 시뮬레이션/CSV 재분석 |
| combined portfolio MDD | 7.6823% | 포트폴리오 시뮬레이션/CSV 재분석 |
| combined Q4 수익 | 952,502원 | 포트폴리오 시뮬레이션/CSV 재분석 |

## 선택지 비교

| 선택지 | 추천 | 이유 |
|---|---|---|
| 이번 combined research 종료 | recommended_now | 공식 OOS entry-filter 통과와 기존 combined portfolio simulation readout가 완료되어 현재 질문에는 충분한 근거가 있다. |
| fresh exact combined portfolio simulation | recommended_if_promotion_discussion_needed | 승격 논의 전에는 새로 생성된 r8 low-cap 공식 CSV와 기존 exit2/r2full 공식 CSV를 월별 equity로 재결합해 정확한 combined 수치를 다시 만드는 것이 가장 의미 있다. |
| 신규 AI 생성 재개 | not_recommended_yet | 검증된 후보의 결합/승격 판단이 먼저이며, 신규 생성은 연구 분산과 과최적화 위험을 키운다. |

## 다음 연구 추천

현재 연구 page는 종료한다. 다만 승격 논의용 정확한 결합 수치가 필요해지면, `fresh exact combined portfolio simulation`을 다음 연구로 진행한다. 이 작업은 새로 생성된 r8 low-cap 공식 CSV와 기존 exit2/r2full 공식 CSV를 월별 equity로 다시 합치는 것이다.

## 금지/범위 밖

- production export
- live trading
- strategy DB write
- V3K gate/live path
- UI frontend/bundle work in this worktree

## 산출물

- `.omo/evidence/tmap-walkforward/post-20260618-combined-portfolio-simulation-readout-20260619.json`
- `.omo/evidence/tmap-walkforward/post-20260618-combined-portfolio-simulation-readout-20260619.md`
- `.omo/evidence/tmap-walkforward/post-20260618-combined-next-research-decision-20260619.json`

