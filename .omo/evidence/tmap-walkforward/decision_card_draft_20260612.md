# 결정 카드 — THETA_seed_902905_06_B [DRAFT]
> 생성: 2026-06-12 10:16

> **N10 양식 의무 필드**: 비교군 ≥3 · 약세 연도 단독 성과 · 기각된 경로 ·
> 거래 중복도 · 남은 검증.

## 0. 자동 조립 공시

> **이 초안은 자동 조립 — 판정·권고는 사람이 작성.**
> 수치는 전부 advisory. 최종 결정 전 사람이 각 섹션을 검토·보완해야 한다.

## 1. 후보

- **buy_name**: THETA_seed_902905_06_B
- **sell_name**: THETA_seed_902905_06_S
- **run_id**: theta_star_reeval_20260611
- **gen_no**: 7
- **graded_score**: 7.850

### 1-1. 훈련 성과 (train)

| 구간 | 후보 | 시드 | 비교 |
|---|---|---|---|
| train | 10,965,479 / MDD 10.04 / 272건 | 8,631,199 / MDD 17.44 / 307건 | 수익 +27.0% · MDD 차 |
| **2025 (약세 연도 단독)** | **1,856,990** | 자료 없음 | — |

### 1-2. 연도별 (train)

| 연도 | 수익 |
|---|---|
| 2023 | 4,590,073 |
| 2024 | 4,518,416 |
| 2025 | 1,856,990 |

- 흑자 연도: 3 / 3

## 2. 과적합 통계 (V1)

- **DSR**: 0.945
- **n_trials**: 80
- **PBO**: 0.343
- **쌍둥이 경고**: 후보 풀 평균 상관 0.93 > 0.7 — 후보들이 사실상 쌍둥이라 PBO가 과적합을 과소평가할 수 있음(유효 독립 후보 ≈ 1.1)

### 2-1. MC 블록 부트스트랩

- P(흑자): 1.0
- 중앙값 수익: 10,628,872
- n_days: 212

## 3. OOS 연도별 (후보 vs 시드)

| run_id | gen_no | buy_name | profit | mdd | trade_count |
|---|---|---|---|---|---|
| cldgen_oos_2022_20260610 | 0 | CLDGEN_0610_C7_SEEDPLUS_B | 1,712,130 | 8.97 | 31 |
| cldgen_oos_2022_20260610 | 1 | Tick_B_902_905_Update_2 | 2,110,382 | 13.11 | 58 |
| cldgen_oos_2026_20260610 | 0 | CLDGEN_0610_C7_SEEDPLUS_B | -229,360 | 12.3 | 5 |
| cldgen_oos_2026_20260610 | 1 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| exit2c_oos_2022_20260611 | 0 | EXIT2C_02_B | 2,546,721 | 9.15 | 55 |
| exit2c_oos_2022_20260611 | 1 | Tick_B_902_905_Update_2 | 2,110,382 | 13.11 | 58 |
| exit2c_oos_2026_20260611 | 0 | EXIT2C_02_B | -70,903 | 20.14 | 9 |
| exit2c_oos_2026_20260611 | 1 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| exit2na_oos_2022_20260612 | 0 | EXIT2NA_06_B | 2,183,037 | 9.54 | 55 |
| exit2na_oos_2022_20260612 | 1 | Tick_B_902_905_Update_2 | 2,110,382 | 13.11 | 58 |
| exit2na_oos_2026_20260612 | 0 | EXIT2NA_06_B | -288,237 | 20.87 | 9 |
| exit2na_oos_2026_20260612 | 1 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| theta_oos_2022_20260611 | 0 | THETA_seed_902905_06_B | 2,097,751 | 13.75 | 55 |
| theta_oos_2022_20260611 | 1 | Tick_B_902_905_Update_2 | 2,110,382 | 13.11 | 58 |
| theta_oos_2026_20260611 | 0 | THETA_seed_902905_06_B | 164,602 | 14.7 | 9 |
| theta_oos_2026_20260611 | 1 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| tick_oos_dash_p2_smoke_20260604 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oos_dash_p2_smoke_20260604 | 1 | AILOOP_tick_oos_dash_p2_smoke_20260604_g1_buy | -3,703,913 | 14.86 | 179 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 1 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g1_buy | -68,046,741 | 228.56 | 5619 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 2 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g2_buy | -5,172,945 | 64.66 | 1251 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 3 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g3_buy | -557,565 | 30.91 | 711 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 4 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_buy | -67,190 | 23.52 | 287 |
| tick_oos_dash_p3_train_2023_2025_20260604 | 5 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g5_buy | 1,432,608 | 5.74 | 99 |
| tick_oos_dash_p5_ai_2022_20260604 | 0 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_buy | -531,523 | 16.77 | 99 |
| tick_oos_dash_p5_ai_2026_20260604 | 0 | AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_buy | 126,238 | 2.52 | 2 |
| tick_oos_dash_p5_seed_2022_20260604 | 0 | Tick_B_902_905_Update_2 | 2,223,554 | 13.02 | 58 |
| tick_oos_dash_p5_seed_2026_20260604 | 0 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| tick_oos_p1_smoke_20260603 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oos_p1_smoke_20260603 | 1 | AILOOP_tick_oos_p1_smoke_20260603_g1_buy | 482,322 | 3.53 | 36 |
| tick_oos_p2_train_2023_2025_20260603 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oos_p2_train_2023_2025_20260603 | 1 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g1_buy | -16,043,382 | 84.49 | 3451 |
| tick_oos_p2_train_2023_2025_20260603 | 2 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g2_buy | -1,327,373 | 36.03 | 413 |
| tick_oos_p2_train_2023_2025_20260603 | 3 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g3_buy | 248,716 | 11.15 | 58 |
| tick_oos_p2_train_2023_2025_20260603 | 4 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy | -697,147 | 19.75 | 182 |
| tick_oos_p2_train_2023_2025_20260603 | 5 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g5_buy | 1,665,802 | 6.93 | 62 |
| tick_oos_p4_ai_2022_20260603 | 0 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy | 248,274 | 3.22 | 10 |
| tick_oos_p4_ai_2026_20260603 | 0 | AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy | -80,344 | 1.61 | 1 |
| tick_oos_p4_seed_2022_20260603 | 0 | Tick_B_902_905_Update_2 | 2,223,554 | 13.02 | 58 |
| tick_oos_p4_seed_2026_20260603 | 0 | Tick_B_902_905_Update_2 | -191,109 | 15.63 | 10 |
| tick_oosrob_p4_smoke_20260604 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oosrob_p4_smoke_20260604 | 1 | AILOOP_tick_oosrob_p4_smoke_20260604_g1_buy | -9,708,723 | 29.93 | 705 |
| tick_oosrob_p4_smoke_20260604 | 2 | AILOOP_tick_oosrob_p4_smoke_20260604_g2_buy | 37,127 | 0.74 | 1 |
| tick_oosrob_p5_train_2023_2025_20260604 | 0 | C_T_900_920_U2_B | 0 | 0.0 | 0 |
| tick_oosrob_p5_train_2023_2025_20260604 | 1 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g1_buy | -1,864,257 | 38.63 | 2408 |
| tick_oosrob_p5_train_2023_2025_20260604 | 2 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g2_buy | 0 | 0.0 | 0 |
| tick_oosrob_p5_train_2023_2025_20260604 | 3 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g3_buy | -2,452,476 | 73.39 | 1581 |
| tick_oosrob_p5_train_2023_2025_20260604 | 4 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g4_buy | -777,423 | 21.17 | 99 |
| tick_oosrob_p5_train_2023_2025_20260604 | 5 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g5_buy | -156,193 | 36.01 | 452 |
| tick_oosrob_p5_train_2023_2025_20260604 | 6 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g6_buy | 1,343,705 | 7.6 | 136 |
| tick_oosrob_p5_train_2023_2025_20260604 | 7 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g7_buy | 1,378,444 | 10.32 | 91 |
| tick_oosrob_p5_train_2023_2025_20260604 | 8 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g8_buy | -313,746 | 19.56 | 149 |
| tick_oosrob_p5_train_2023_2025_20260604 | 9 | AILOOP_tick_oosrob_p5_train_2023_2025_20260604_g9_buy | -1,342,087 | 33.75 | 115 |

## 4. 거래 중복도 (N10 의무)

- **Jaccard**: 0.888
- 후보 거래 수: 270 / 시드 거래 수: 304 / 공통: 270
- 해석: 사실상 동일 거래 — '보완'은 동일 베팅 2배와 같음(대체 검토)

## 5. 레짐 분해

- 지표: breadth(일별 고유 종목 수, moneytop 랭킹 회전)

| 전략 | 레짐 | 수익 | 기간(일) |
|---|---|---|---|
| THETA | active | 6,503,770 | 137 |
| THETA | contracted | 6,724,062 | 138 |
| THETA | unlabeled | 0 | 0 |
| SEED | active | 5,356,448 | 152 |
| SEED | contracted | 5,194,024 | 149 |
| SEED | unlabeled | 0 | 0 |

- THETA concentration: 0.5083
- SEED concentration: 0.5077

## 6. 기각된 경로 (N10 의무)

| 레이블 | 기각일 | 기각 근거 | train 수익 |
|---|---|---|---|
| REVIVAL EXIT2C take9 | 2026-06-11 | 고정 OOS 2026 -70,903 + maxMDD 20.14 위배 (결정 카드 §7b) | 12,319,055 |
| REVIVAL EXIT2NA take6 | 2026-06-12 | 고정 OOS 2026 -288,237(시드 열위) + maxMDD 20.87 + payoff 0.97 (결정 카드 §7c) | 11,230,126 |

## 7. 비교군 (N10 의무 — 차점 후보, ≥3 등재)

| gen_no | positive_years | 연도별 수익 요약 |
|---|---|---|
| 7 | 3 | 2023:4,590,073 / 2024:4,518,416 / 2025:1,856,990 |
| 5 | 3 | 2023:4,875,248 / 2024:3,909,879 / 2025:1,076,439 |
| 2 | 3 | 2023:4,754,964 / 2024:3,902,314 / 2025:1,233,720 |
| 6 | 3 | 2023:5,118,041 / 2024:4,117,757 / 2025:1,558,687 |
| 4 | 3 | 2023:4,226,996 / 2024:4,269,124 / 2025:1,532,023 |
| 1 | 3 | 2023:4,510,621 / 2024:3,725,865 / 2025:751,472 |
| 3 | 3 | 2023:5,244,083 / 2024:3,522,496 / 2025:704,379 |

## 8. 남은 검증 · 결정 (N10 의무 — 사람이 작성)

| # | 항목 | 결과 |
|---|---|---|
| 1 | V2 플라시보 | ___ |
| 2 | V4 walk-forward | ___ |
| 3 | V5 슬리피지 | ___ |
| 4 | 기타 | ___ |

## 9. 최종 결정 (사람이 작성)

- **판정**: ___ (PROMOTE / NEEDS_MORE_EVIDENCE / REJECT)
- **근거**: ___
- **결정자**: ___
- **결정일**: ___

> [DRAFT] 자동 조립 초안 — 판정·권고는 사람이 작성. 수치 전부 advisory.