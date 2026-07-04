# 2026-06-28 12시간 후속 조건식 연구 실행 기록

## 상태
- 실행 시각: 2026-06-28T03:06:09.659335Z
- 승인 계획: `.gjc/_session-019edda6-58ba-7000-ab80-318bc34f3b8a/plans/ralplan/019edda6-58ba-7000-ab80-318bc34f3b8a/pending-approval.md`
- 모드: research-only advisory
- 금지 유지: export=false, live=false, finalPromotion=false, protected path mutation 없음
- 실제 소요: 약 2시간 45분+검증/문서화. 승인 계획은 최대 12시간 예산이었지만, B1은 도구 1회 3600초 제한으로 gen17에서 중단되고 B2는 64엔진 재준비 타임아웃이 반복되어 추가 장시간 반복을 중단했습니다.

## 결론
| 항목 | 결론 | 근거 |
|---|---|---|
| 엔진 수 | 64 선택 | 32/48/64 모두 성공률 1.0, timeout/recovery 0. 64가 amortized p50 75.20s로 최저, steady p50 29.57s. |
| fallback 검증 승자 | `rr8_12_turnover_min_902=1.5` | 4/4 연도 gate 통과, profit 합 15,694,418, max MDD 13.58. |
| 기존 fallback best 재평가 | `rr8_21_trail_keep=0.7`은 2022 daily 0.4로 1개 창 미통과 | 3/4 gate 통과, profit 합 14,223,795. |
| GPT-auth B | 새 GPT 생성 후보는 fallback 안정성 후보를 넘지 못함 | B1 gen8 gate 통과 profit 1,772,126 / MDD 15.14 / trades 550이나 fallback rr8_12의 2025 profit 3,062,696보다 낮음. |
| C promotion-review | 생성 없이 read-only evidence health만 수행 | C_new_candidates=0, C_generation_rows=0, C_evaluated=0. |

## 32/48/64 warm-engine benchmark
| engine | prepare sec | amortized p50 sec | steady p50 sec | steady p95 sec | success | timeout | recovery |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 128.58 | 80.03 | 37.17 | 37.52 | 1.00 | 0 | 0 |
| 48 | 140.50 | 80.92 | 34.09 | 34.94 | 1.00 | 0 | 0 |
| 64 | 136.87 | 75.20 | 29.57 | 29.88 | 1.00 | 0 | 0 |

선택 사유: selected 64: lowest amortized_p50 among stable 32/48/64; 64 amortized 75.20s and steady p50 29.57s. 48 measured but did not beat 32/64 on amortized p50.

## fallback top 3 OOS / walk-forward 성격 검증
| 순위 | 후보 | gate windows | profit sum | avg profit | max MDD | min daily | trades | edge ratio | 3틱 slippage profit |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `rr8_12_turnover_min_902=1.5` | 4/4 | 15,694,418 | 3,923,604 | 13.58 | 0.50 | 644 | 1.582 | -7,511,100 |
| 2 | `rr8_0_cap_max=2500` | 3/4 | 14,451,817 | 3,612,954 | 17.34 | 0.40 | 483 | 1.658 | -2,965,958 |
| 3 | `rr8_21_trail_keep=0.7` | 3/4 | 14,223,795 | 3,555,949 | 18.84 | 0.40 | 545 | 1.577 | -5,129,590 |

해석: `rr8_12_turnover_min_902=1.5`가 기존 최고손익 후보보다 총손익·MDD·연도별 gate 안정성이 좋습니다. 단, 0~3틱 슬리피지 스트레스는 세 후보 모두 3틱에서 음수로 전환되어 실전 승격이 아니라 연구 후보 유지가 맞습니다.

## GPT-auth B seeded run
| run | rows | ok | gate pass | user-constraint pass | 비고 |
|---|---:|---:|---:|---:|---|
| B1 selected-engine | 18 | 8 | 2 | 2 | gen17까지 도달 후 도구 제한 시간으로 중단. |
| B2 adaptive | 6 | 0 | 0 | 0 | warm prepare 실패 뒤 cold fallback이 engine_data_response_timeout 반복. |

- B1 seed gen0: rr8_12 자체 재평가 profit 3,062,696 / MDD 12.87 / trades 190 / daily 0.8.
- B1 최고 신규 GPT 후보: gen8 profit 1,772,126 / MDD 15.14 / trades 550 / daily 2.3 / window {'window_start': 90500, 'window_end': 91000, 'window_minutes': 5.0, 'windows': [[90500, 91000]]}.
- GPT가 약했던 이유: (1) time_cap_bucket_v1 복잡도 초과가 반복되어 생성 실패가 많았고, (2) 성공 생성도 저빈도/과매매/MDD 실패가 많았으며, (3) B2에서는 64엔진 재준비가 engine_data_response_timeout으로 무너져 긴 연속 실험 안정성이 낮았습니다.

## C read-only promotion-review evidence health
| 필드 | 값 |
|---|---|
| C_new_candidates | 0 |
| C_generation_rows | 0 |
| C_evaluated | 0 |
| source ids | rr8_12_turnover_min_902=1.5, rr8_0_cap_max=2500, rr8_21_trail_keep=0.7, follow12_gptauth_B_seeded64_20260628/gen0, follow12_gptauth_B_seeded64_20260628/gen8 |
| export/live/finalPromotion | False/False/False |

## 산출물
| 종류 | 경로 |
|---|---|
| engine benchmark | `artifacts/12h-followup-research-20260628/engine_benchmark_32_48_64.json` |
| 48-inclusive decision | `artifacts/12h-followup-research-20260628/engine_decision_receipt_48_inclusive.json` |
| fallback validation | `artifacts/12h-followup-research-20260628/fallback_validation_summary.json` |
| GPT B summary | `artifacts/12h-followup-research-20260628/gpt_b_seeded_summary.json` |
| C read-only health | `artifacts/12h-followup-research-20260628/promotion_review_readonly_health.json` |
| safety receipt | `artifacts/12h-followup-research-20260628/safety_receipt.json` |

## 후속 추천
1. 연구 기준선은 `rr8_12_turnover_min_902=1.5`로 갱신합니다.
2. 64엔진은 단발/짧은 연속에서는 가장 빠르지만, B2에서 재준비 타임아웃이 발생했으므로 다음 장시간 운용은 64 단일 고정이 아니라 `64 사용 후 실패 시 32 복구` 정책을 별도 코드/운영 계획으로 설계해야 합니다.
3. GPT 생성은 현재 복잡도 가드와 충돌하므로 time_cap_bucket 프롬프트를 더 간결하게 만드는 별도 제품 코드 개선 계획이 필요합니다.
4. 3틱 슬리피지에서 후보들이 음수로 전환되므로 실전 승격 검토 전 체결/슬리피지 보수화 연구가 우선입니다.
