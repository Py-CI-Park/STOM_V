# Morning Report — 2026-06-28 Human Process Research Loop

## 상태
- 실행 시각: 2026-06-28T15:03:31.268284+00:00
- 모드: research-only advisory
- canonical process: `process-research`, preset: `research`
- 금지 유지: export=false, live=false, finalPromotion=false
- 3틱 슬리피지: 이번 루프의 즉시 hard gate가 아니라 promotion/live 전 advisory risk로만 유지
- 공식 백테스트: 주문금액·호가/잔량 기반 체결·수수료/세금이 반영된 1차 평가 기준

## 핵심 결론
| 항목 | 결론 |
|---|---|
| 최고 2025 전체기간 재생 후보 | `human_seed_rr8_21_trail_keep=0.7` profit 3,089,180, MDD 18.84 |
| OOS 안정 기준선 | 이전 검증 기준 `rr8_12_turnover_min_902=1.5` 유지. 4/4 OOS window 통과 근거가 있음 |
| 한 가지 mutation 결과 | `turnover_min_902 1.5 -> 3.0`은 gate는 통과했지만 profit 2,538,600, MDD 19.49로 부모보다 악화 |
| 성과 부진 주요 원인 | 시드 자체보다 백테스트 후 분석을 다음 가설로 바꾸는 구조와 GPT one-mutation discipline 부족 |
| 엔진 | 이번 seed/mutation replay는 64 prepare/run 성공. 32 fallback은 trigger 없음 |

## 공식 전체기간 replay / one mutation 결과
| candidate | profit | MDD | trades | daily | gate | csv |
|---|---:|---:|---:|---:|---:|---|
| human_seed_rr8_21_trail_keep=0.7 | 3,089,180 | 18.84 | 165 | 0.7 | 1 | backtest/csv\stock_bt_GATE_rr8_21_trail_keep_0_7_B_20260628234747.csv |
| human_seed_rr8_12_turnover_min_902=1.5 | 3,062,696 | 12.87 | 190 | 0.8 | 1 | backtest/csv\stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260628234642.csv |
| human_seed_rr8_0_cap_max=2500 | 3,047,522 | 17.34 | 145 | 0.6 | 1 | backtest/csv\stock_bt_GATE_rr8_0_cap_max_2500_B_20260628234715.csv |
| human_mutation_rr8_13_turnover_min_902=3 | 2,538,600 | 19.49 | 152 | 0.6 | 1 | backtest/csv\stock_bt_GATE_rr8_13_turnover_min_902_3_B_20260628235311.csv |
| human_seed_gptauth_B_gen8 | 1,772,126 | 15.14 | 550 | 2.3 | 1 | backtest/csv\stock_bt_AILOOP_follow12_gptauth_B_seeded64_20260628_g8_buy_20260628234820.csv |

## 분석 카드 / prompt repair
- `analysis_cards.jsonl`: 5개 카드 생성. 각 카드에 metrics, time/market-cap segment, Edge Ratio, MFE/MAE, loss cluster, next hypothesis, safety flags 포함.
- `prompt_mutation_receipts.jsonl`: PM001 1개. A001/C001에서 `turnover_min_902 1.5 -> 3.0` 단일 mutation으로 C005 제안/실행.
- 결과: C005는 부모보다 profit -524,096, MDD +6.62p 악화되어 `executed_and_rejected_below_parent`.

## 대시보드 확인
| page path | text length | screenshot |
|---|---:|---|
| /ui/evolution/process | 4293 | `artifacts/human-process-research-20260628/dashboard-process.png` |
| /ui/evolution/lab | 4184 | `artifacts/human-process-research-20260628/dashboard-lab.png` |
| /ui/evolution/workbench | 24247 | `artifacts/human-process-research-20260628/dashboard-workbench.png` |
| /ui/evolution | 11868 | `artifacts/human-process-research-20260628/dashboard-audit.png` |

참고: `/ui/evolution/audit` 요청은 현재 `/ui/evolution` overview 표면으로 렌더링되었습니다. Audit 버튼/텍스트는 관측되지만 직접 audit route 정합성은 후속 UI 정리 항목입니다.

## 다음 연구 queue
1. `rr8_12_turnover_min_902=1.5`를 OOS-stable baseline으로 유지하고, `rr8_21_trail_keep=0.7`은 2025 profit comparator로만 사용합니다.
2. turnover를 더 조이는 방향은 우선순위에서 내립니다. 이번 single-axis mutation이 손익과 MDD를 모두 악화시켰습니다.
3. 다음 mutation은 분석 카드의 손실 군집/시간대/exit edge를 보고 **exit/trailing 또는 특정 loss-cluster repair**로 한 축만 진행합니다.
4. GPT는 analysis card 1개만 입력하고, 한 가지 작은 변경만 생성하도록 제한합니다.
5. 64 engine은 계속 짧은 batch 기본값으로 쓰되, timeout/no-metrics/replay failure 발생 시 32 fallback receipt를 남깁니다.

## 산출물
- baseline: `artifacts/human-process-research-20260628/baseline_setup.json`
- candidate cards: `artifacts/human-process-research-20260628/candidate_cards.jsonl`
- full-period receipts: `artifacts/human-process-research-20260628/full_period_backtest_receipts.json`
- analysis cards: `artifacts/human-process-research-20260628/analysis_cards.jsonl`
- prompt mutation receipts: `artifacts/human-process-research-20260628/prompt_mutation_receipts.jsonl`
- dashboard verification: `artifacts/human-process-research-20260628/dashboard_verification.json`
- final summary: `artifacts/human-process-research-20260628/final_summary.json`
