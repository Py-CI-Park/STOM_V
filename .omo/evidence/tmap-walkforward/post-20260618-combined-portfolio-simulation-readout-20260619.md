# 2026-06-19 Combined Portfolio Simulation Readout

## 목적

공식 OOS를 통과한 `r8_exclude_cap_lt_1500` entry filter와 기존 `exit2` prior-month 포트폴리오 규칙을 결합했을 때 연구상 의미를 정리한다.

## 증거 타입 구분

| 레이어 | 증거 타입 | 설명 |
|---|---|---|
| r8 저시총 제외 entry filter | 공식 OOS | wrapper-backed `r8_exclude_cap_lt_1500` 결과 |
| exit2 prior-month -500k | 포트폴리오 규칙 | 직전 월 exit2 손익이 -500k 이하이면 다음 달 제외 |
| 결합 후보 | 포트폴리오 시뮬레이션/CSV 재분석 | 순수 공식 buy/sell OOS 아님 |

## 입력 / 근거 artifact

| 입력 | 파일 | 역할 |
|---|---|---|
| r8 저시총 제외 공식 OOS | `.omo/evidence/tmap-walkforward/post-q4-r8-lowcap-official-oos-summary-20260619.json` | 단독 entry-filter 공식 OOS 근거 |
| 결합 후보 시뮬레이션 | `.omo/evidence/tmap-walkforward/post-q4-3h-combined-candidates-20260618.json` | `r8_exclude_cap_lt_1500 + exit2 prior-month` 포트폴리오 재분석 근거 |
| exit2 prior-month 규칙 | `.omo/evidence/tmap-walkforward/r8-exit2-prior-loss-500k-split-20260618.json` | 직전 월 손실 기반 allocation rule 근거 |
| 기존 판단 카드 | `.omo/evidence/tmap-walkforward/post-20260618-robust-decision-card-20260619.json` | `oos_passed` 판단 및 caveat 근거 |

## 공식 OOS 단독 결과

| 항목 | 값 |
|---|---:|
| Q4 stress 수익 | 310,886원 |
| Q4 stress MDD | 9.25% |
| 2022-2025 full-year + 2026 YTD 총수익 | 7,292,861원 |
| 최악 MDD | 19.09% |
| 총 거래수 | 263 |
| Gate | pass |

주의: 2026은 `2026-01-01~2026-02-28` YTD이며 full-year가 아니다.

## Combined Portfolio Simulation 결과

| 구간 | 수익 | MDD | 거래수 | 연환산 |
|---|---:|---:|---:|---:|
| 전체 | 39,402,438원 | 7.6823% | 1073 | 38.6826% |
| 2025~2026 최근 | 6,941,830원 | 12.6478% | 322 | 39.0624% |
| 2025 Q4 | 952,502원 | 11.3583% | 67 | 33.3884% |

### 연도별 수익

| 연도 | 수익 |
|---:|---:|
| 2022 | 6,560,023원 |
| 2023 | 14,757,205원 |
| 2024 | 11,143,380원 |
| 2025 | 5,728,090원 |
| 2026 YTD | 1,213,740원 |

## 해석

- 공식 OOS 기준으로 r8 저시총 제외 entry filter는 단독 검증을 통과했다.
- combined portfolio simulation 기준으로 전체 수익은 39,402,438원, MDD는 7.6823%, Q4 수익은 952,502원이다.
- 다만 combined 수치는 포트폴리오 레이어 재분석이므로, 순수 공식 buy/sell OOS로 부르면 안 된다.
- 2026 공식 OOS 범위는 2026-02-28까지의 YTD이며 full-year가 아니다.

## 결론

현재 결론은 `combined_research_supported_not_production_ready`이다. 즉 연구상 조합은 지지되지만, production/export 승격은 별도 승인/계획 전에는 하지 않는다.

## 다음 추천

현재 연구 page는 종료 가능하다. 승격 논의 전 더 정확한 결합 수치가 필요하면, 새로 생성된 r8 low-cap 공식 CSV와 기존 exit2/r2full 공식 CSV를 월별 equity로 다시 합치는 fresh exact combined portfolio simulation을 별도 연구로 진행한다.
