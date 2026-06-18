# 2026-06-18 Post-Session Research and Dashboard Handoff

## 시작 기준
이 문서는 2026-06-18 작업을 마친 뒤, 2026-06-19 이후 이어서 시작할 연구와 대시보드 정리 작업을 남기기 위한 핸드오프다.

다음 시작 명령:

```text
$start-work .omo/plans/post-20260618-official-oos-dashboard-cleanup.md
```

## 현재 상태 요약
| 구분 | 상태 | 근거 |
|---|---|---|
| Q4 방어 후보 사전 선별 | 완료 | `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json` |
| 다음 공식 OOS 후보 | 정해짐 | `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` |
| 공식 백테스트 실행 | 아직 안 함 | 사전 선별 단계만 완료 |
| 조건식 신규 생성 | 아직 안 함 | 후보를 먼저 좁힌 상태 |
| `backtest.py` 수정 | 보류 | exit-rule 설계가 확정되지 않았음 |
| 대시보드 Research Records | 노출 확인 | `post-q4-3h-bulk-research-20260618` 캠페인 목록 1위 확인 |

## 다음 연구로 남길 공식 OOS 후보
| 쉬운 이름 | 내부 이름 | 목적 | 예상 시간 | 채택 판단 |
|---|---|---|---:|---|
| 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 과최적화 위험이 낮은 robust 후보를 공식 엔진으로 검증 | 45분 | 1순위 |
| 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 원점수 1위가 우연/과최적화인지 shadow 비교 | 35분 | 채택 전용 아님 |
| exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | 조건식 변경 없이 포트폴리오 운용 규칙으로 검증 | 25분 | 보조 규칙 |
| r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | r8 자체 방어 효과만 분리 검증 | 40분 | 원인 분해 |

## 대시보드 중간 정리
| 항목 | 현재 확인 | 부족한 사항 |
|---|---|---|
| Research Records | 새 연구 캠페인 노출과 상세 조회 가능 | 후보 이름이 길고 어려워서 쉬운 별칭이 필요 |
| 연구 일지 | `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md` 작성됨 | 대시보드 문서 탭에서 최신 update_log 자동 노출은 아직 미구현 |
| 백테스트/진화 대시보드 연결 | 연구 기록은 보임 | 백테스트 GUI의 요일별/시간별 수익률 그래프가 진화 대시보드 실시간 후보 대상에도 완전히 보이는지 확인 필요 |
| 증거 종류 구분 | JSON에는 수익/MDD/연평균 기록됨 | `공식 OOS`, `CSV 재분석`, `포트폴리오 규칙`, `설계/보류` 라벨을 사용자에게 더 명확히 보여야 함 |
| 실패/보류 설명 | `backtest.py` 수정은 보류라고 기록됨 | 왜 보류인지 대시보드에서도 바로 보여주는 설명이 필요 |

## 부족한 사항
| 우선 | 부족한 점 | 왜 중요한가 | 다음 조치 |
|---:|---|---|---|
| 1 | robust 후보의 공식 백테스트가 아직 없음 | CSV 재분석은 최종 검증이 아니므로 공식 엔진 실행이 필요 | 계획 2번 실행 |
| 2 | 후보 이름이 너무 어렵다 | 사용자가 무엇을 검증하는지 이해하기 어려움 | 별칭 표와 대시보드 라벨 추가 |
| 3 | Research Docs 최신 일지 자동 노출이 부족하다 | 연구 기록을 대시보드에서 찾기 어렵다 | update_log 자동 인덱싱 구현 또는 보류 사유 기록 |
| 4 | 요일/시간별 그래프의 진화 대시보드 적용 여부가 불명확하다 | GUI 백테스트 이미지의 분석력을 실시간 후보에도 적용해야 한다 | 현재 기능 확인 후 구현 계획 수립 |
| 5 | `backtest.py` 수정 필요 여부가 아직 결론나지 않았다 | exit-rule 자체를 바꾸면 위험도가 커진다 | causal proxy 설계 후 별도 승인 |

## 다음 작업 계획 파일
| 파일 | 역할 |
|---|---|
| `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` | 2026-06-19 이후 실행할 공식 OOS와 대시보드 정리 계획 |
| `docs/research/2026-06-18_post_q4_official_oos_next_research.md` | 장기 연구 기록 위치의 공식 OOS 다음 연구 요약 |
| `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md` | 오늘 완료한 사전 선별 연구 일지 |
| `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` | 다음 공식 OOS 추천 후보 |

## 주의 사항
- 다음 작업은 공식 백테스트로 넘어가는 단계다.
- 단, `11월 제외` 후보는 원점수는 높지만 과최적화 위험이 크므로 채택 후보가 아니라 비교용이다.
- `backtest.py` 수정은 아직 하지 않는다.
- live/V3K/DB/보호 경로는 건드리지 않는다.
- 작업이 1시간을 넘으면 진행률, 목적, 중간 성과, 남은 예상 시간을 표로 보고한다.

## 한 줄 결론
다음 시작 시에는 `저시총 제외 방어 조합`을 공식 OOS로 먼저 검증하고, 동시에 대시보드에서 연구 기록과 후보 이름을 더 쉽게 볼 수 있도록 정리한다.
