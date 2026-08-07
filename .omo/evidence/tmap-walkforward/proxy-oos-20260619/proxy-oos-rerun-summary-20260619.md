# Proxy OOS Rerun Summary (2026-06-19)

## 결론

타임아웃 원인을 정리한 뒤 Q4와 2022~2026 YTD 공식 OOS를 재실행했습니다. 세 후보 모두 공식 evidence는 생성됐지만 approved pass gate를 통과하지 못했습니다. 최종 결론은 `completed_no_pass`입니다.

## 후보별 결과

| 후보 | 결정 | 총수익 | MDD | 거래수 | 양수 기간 | Q4 수익 | 집중도 top1/top5 | 실패 핵심 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| P1_entry_liquidity_proxy | `reject` | 1,168,567원 | 22.14% | 167 | 3 | 99,818원 | 0.021/0.095 | profit_gt_official_r8, mdd_lte_official_r8, all_official_gates_passed, positive_periods_gte_4 |
| P2_defensive_exit_proxy | `reject` | 3,856,918원 | 15.89% | 272 | 4 | -101,992원 | 0.019/0.093 | profit_gt_official_r8, all_official_gates_passed, q4_profit_positive |
| P3_trend_vol_exit_proxy | `reject` | 6,338,838원 | 22.86% | 263 | 5 | 132,797원 | 0.016/0.071 | profit_gt_official_r8, mdd_lte_official_r8 |

## 기준

- Pass: 총수익 > 7,292,861원, MDD <= 19.09%, 전체 gate 통과, 거래수 >=132, 4개 이상 양수 기간, Q4 양수, top1 <=0.20, top5 <=0.50, CSV reconcile.
- 세 후보 모두 pass 조건을 만족하지 못했습니다.
- 실매매/export/운영 DB 승격 없음.
