# 2026-06-18 Post-Q4 Official OOS Next Research

## 목적
이 문서는 2026-06-18에 끝낸 Q4 방어 후보 사전 선별 결과를 장기 연구 기록 위치에 남기기 위한 요약이다. 세션별 작업 로그는 `docs/update_log/`에 있고, 이 파일은 다음 연구자가 바로 이해할 수 있는 연구 노트 역할을 한다.

## 현재 결론
공식 백테스트를 바로 여러 개 돌리기 전에, 기존 공식 OOS CSV를 재분석해서 후보를 좁혔다. 이 재분석은 최종 검증이 아니며, 다음 단계는 공식 OOS 실행이다.

| 구분 | 상태 |
|---|---|
| 조건식 신규 생성 | 하지 않음 |
| 공식 OOS 실행 | 아직 하지 않음 |
| CSV 재분석 | 완료 |
| 다음 공식 OOS 후보 선정 | 완료 |
| `backtest.py` 수정 | 보류 |

## 다음 공식 OOS 후보
| 우선 | 쉬운 이름 | 내부 이름 | 이유 | 예상 시간 |
|---:|---|---|---|---:|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 과최적화 위험이 낮고, 전체/Q4/MDD가 균형 있게 개선됨 | 45분 |
| 2 | 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 원점수는 1위지만 달력 월 제외 규칙이라 shadow 비교만 수행 | 35분 |
| 3 | exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | 조건식 변경 없이 적용 가능한 포트폴리오 규칙 | 25분 |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | r8 방어 효과만 분리해서 원인을 확인 | 40분 |

## 주요 성과 지표
| 후보 | 전체 수익 | 연평균 수익률 | 전체 MDD | 최근 수익 | Q4 수익 | Q4 MDD | 판단 |
|---|---:|---:|---:|---:|---:|---:|---|
| `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 39,402,438 | 38.68% | 7.68% | 6,941,830 | 952,502 | 11.36% | 실행 추천 1위 |
| `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 46,745,487 | 43.21% | 10.94% | 8,551,375 | 1,028,539 | 12.72% | 비교용, 과최적화 위험 |
| `exit2_full_after_prior_r8r2_loss_else_off` | 35,392,509 | 36.01% | 8.94% | 7,039,427 | 132,648 | 18.23% | 포트폴리오 규칙 후보 |

## 대시보드 정리 과제
| 항목 | 현재 상태 | 필요한 작업 |
|---|---|---|
| Research Records | `post-q4-3h-bulk-research-20260618` 노출 확인 | 긴 내부 후보명에 쉬운 별칭 표시 |
| 연구 문서 | update_log와 이 research 노트에 기록 | 최신 연구 일지를 대시보드 문서 탭에서 쉽게 찾도록 개선 |
| 증거 종류 | JSON에 결과 기록 | `공식 OOS`, `CSV 재분석`, `포트폴리오 규칙`, `설계/보류` 라벨 추가 |
| 요일/시간별 그래프 | 백테스트 GUI에는 존재 | 진화 대시보드의 실시간 후보 대상 그래프 구현 여부 확인 |
| `backtest.py` | 수정하지 않음 | exit-rule causal proxy가 설계될 때까지 보류 |

## 다음 시작 명령
```text
$start-work .omo/plans/post-20260618-official-oos-dashboard-cleanup.md
```

## 관련 파일
| 파일 | 역할 |
|---|---|
| `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` | 다음 공식 OOS와 대시보드 정리 실행 계획 |
| `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md` | 세션 핸드오프 문서 |
| `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md` | 사전 선별 연구 실행 로그 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` | 다음 공식 OOS 추천 JSON |

## 주의
이 파일은 연구 기록이다. 실제 공식 백테스트 완료 보고가 아니며, 다음 세션에서는 공식 OOS 실행 결과로 이 결론을 확인해야 한다.
