# 2026-06-18 Post-Q4 3H Bulk Research

## 목적
기존 공식 OOS CSV를 다시 넓게 계산해서, 다음에 어떤 후보를 공식 OOS로 올릴지 정했다. 이 작업은 조건식을 새로 생성한 것이 아니라, 이미 검증된 결과 파일을 조합해 방어 규칙과 다음 실험 우선순위를 좁힌 연구다.

## 범위
| 항목 | 상태 |
|---|---:|
| 사용 데이터 | annual 공식 OOS 15개 CSV, 2025 Q4 공식 OOS 3개 CSV |
| 총 거래 수 | annual 1,373건, Q4 83건 |
| 생성 후보 | exit2 운용 9개, r8 필터 10개, 조합 64개 |
| `backtest.py` 수정 | 없음 |
| live/V3K/DB 변경 | 없음 |
| 조건식 신규 생성 | 없음 |

## 핵심 성과
| 구분 | 후보 | 전체 수익 | 전체 연평균 | 전체 MDD | 최근 수익 | Q4 수익 | Q4 MDD | 판단 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 원점수 1위 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 46,745,487 | 43.21% | 10.94% | 8,551,375 | 1,028,539 | 12.72% | 11월 제외 규칙이라 과최적화 위험 큼 |
| 실행 추천 1위 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 39,402,438 | 38.68% | 7.68% | 6,941,830 | 952,502 | 11.36% | 과최적화 위험이 낮은 robust 후보 |
| r8 단독 방어 후보 | `r8_exclude_cap_lt_1500` | 9,420,419 | 32.47% | 7.68% | 2,705,797 | 310,886 | 9.09% | 단순한 진입 전 필터 |
| exit2 단독 운용 후보 | `exit2_full_after_prior_r8r2_loss_else_off` | 35,392,509 | 36.01% | 8.94% | 7,039,427 | 132,648 | 18.23% | 조건식 변경 없이 검증 가능 |

## 다음 작업 우선순위
| 우선 | 작업 | 목적 | 예상 시간 | `backtest.py` 필요 |
|---:|---|---|---:|---|
| 1 | robust 조합 후보 공식 OOS | 과최적화 낮은 후보가 실제 공식 실행에서도 유지되는지 확인 | 45분 | 아니오 |
| 2 | 원점수 1위 shadow 비교 | 11월 제외 규칙이 우연인지 비교만 수행 | 35분 | 아니오 |
| 3 | exit2 포트폴리오 규칙 공식 리포트 | 조건식 변경 없이 방어 규칙을 대시보드/리포트로 확정 | 25분 | 아니오 |
| 4 | r8 저시총 필터 단독 공식 OOS | `r8_4` 자체 손실 방어 효과를 단독 검증 | 40분 | 아니오 |
| 5 | exit-rule 재설계 연구 | 사후 exit 손실을 진입 시점 causal proxy로 바꿀 수 있는지 설계 | 60분 | 보류 |

## 1시간 보고 처리
이번 대량 재분석은 로컬 CSV/JSON 집계라 1시간 안에 종료됐다. 따라서 중간 1시간 보고를 꾸며서 만들지 않고, `post-q4-3h-hourly-progress-20260618.jsonl`에 시작, 중간 체크포인트, 1시간 미만 완료 기록을 남겼다.

## 증거 파일
| 파일 | 내용 |
|---|---|
| `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-baseline-20260618.json` | 입력 CSV, 거래 수, 기준 포트폴리오 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-rule-grid-20260618.json` | exit2 운용 규칙 9개 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-r8-filter-grid-20260618.json` | r8 진입 전 필터와 사후진단 구분 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-combined-candidates-20260618.json` | 조합 후보 64개 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json` | 점수표와 연평균 수익률 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` | 다음 공식 OOS 추천 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-research-20260618_summary.json` | 대시보드 Research Records 요약 |

## 결론
다음 단계는 조건식 대량 재생성이 아니라, `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` 후보를 공식 OOS로 먼저 확인하는 것이다. `backtest.py` 관련 수정은 exit-rule 설계가 더 명확해질 때까지 보류한다.
