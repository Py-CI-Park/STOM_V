# Process Research Actual Run Review — 2026-06-29

## 결론
개선된 process-research 루프를 실제로 실행했다. 4개 후보가 공식 백테스트까지 완료됐고, 연구 프로세스 계약은 정상 작동했다. 다만 이번 실행에서는 기준선을 이긴 후보가 없었다.

## 실행 요약
| 항목 | 결과 |
|---|---|
| 최종 실행 상태 | ok / candidates_evaluated |
| process | process-research |
| preset | research |
| requested candidate_count | 6 |
| actual executed candidate_count | 4 |
| slot allocation | {'repair': 2, 'discovery': 2} |
| lanes | ['repair', 'discovery', 'repair', 'discovery'] |
| next allocation | {'schema_version': 1, 'slots_total': 4, 'previous_slots_by_lane': {'repair': 2, 'discovery': 2}, 'slots_by_lane': {'repair': 3, 'discovery': 1}, 'better_lane': 'repair', 'shift_applied': {'from': 'discovery', 'to': 'repair', 'count': 1}, 'decision_reason': 'opposing_lane_advantage_capped', 'repair_lane_score': 102.0, 'discovery_lane_score': 0.0, 'tie_breaks_used': [], 'blockers': [], 'authority': 'research_budget_steering_only'} |
| best candidate | actual_pr_relaxed_20260629__cand004 |

## 후보 결과
| rank | candidate | lane | expression | trades | total_profit | retention | promotion_score | pass |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | actual_pr_relaxed_20260629__cand004 | discovery | `-11_905_509_280 <= 거래대금증감 < -5232658666.2` | 93 | 358,654 | 0.489 | -40.533 | False |
| 2 | actual_pr_relaxed_20260629__cand001 | repair | `6.684 <= 등락율 < 7.43` | 93 | 357,247 | 0.489 | -40.553 | False |
| 3 | actual_pr_relaxed_20260629__cand002 | discovery | `4074.1 <= 매수총잔량 < 7154.6` | 99 | 344,974 | 0.521 | -40.750 | False |
| 4 | actual_pr_relaxed_20260629__cand003 | repair | `176.854 <= 체결강도 < 201.327` | 98 | 287,668 | 0.516 | -41.626 | False |

## 해석
- 후보 4개 모두 official backtest는 성공했다.
- 그러나 모두 promotion score가 음수라 기준선을 이기지 못했다.
- default 분석 기준에서는 후보가 생성되지 않았고, relaxed 분석에서만 후보가 생성됐다.
- 따라서 실제 병목은 엔진 실행보다 **결과 분석에서 후보를 충분히 만들고, 그 후보를 다음 프롬프트/수정 축으로 연결하는 단계**다.

## 다음 개선
1. default 분석에서 후보 0개이면 자동 relaxed exploration pass를 실행한다.
2. relaxed 후보는 promotion 후보가 아니라 discovery/diagnostic 후보로 라벨링한다.
3. 이번처럼 discovery lane score가 cap되면 다음 round는 repair 3 / discovery 1로 이동한다.
4. 후보 생성 기준을 alpha 완화 하나로만 두지 말고 segment/root-cause 기반 후보를 별도 생성한다.
