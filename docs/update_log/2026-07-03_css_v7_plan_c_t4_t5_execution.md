# CSS_V7 Plan C T4~T5 실행 기록

## 범위

- 사용자 지정 범위: T4~T5 only
- 금지 준수: Plan B/D 미실행, A3/promotion/export/live/final 경로 미수정, `git add -A` 미사용, DB UPDATE/DELETE 미사용
- 원문 재확인: `.omo/evidence/ai-loop-full-next-execution-20260703/source_read_receipt.md`

## 결과 요약

| 단계 | 결과 |
|---|---|
| T4 static gate | CSS_V7 25건 checked, bad=0 |
| T4 unique pairs | 21개 생성(tick 7, min 14), combo priority 1/2 반영 |
| T4 loop DB mirror | `loop_strategies.db`에 CSS_V7 25건 INSERT-only 반영 |
| T4 rollback | `loop_strategies.db.bak.css_v7_20260703T064540Z` 생성 |
| T4 duplicate abort | collision abort 증거 생성(exit=3) |
| T5 positive control | `gate_healthy` |
| T5 smoke | tick 7/7 timeout, min은 첫 페어 장시간 무출력으로 중단 |
| T5 train/OOS/WF | smoke go 후보 없음으로 미실행 |

## 최종 후보 상태

| 상태 | 후보 수 |
|---|---:|
| 생존 | 0 |
| 기각 | 0 |
| 보류 | 21 |

## 주요 증거

- `artifacts/chart_sulsa_validation_20260702/static_gate_report.json`
- `artifacts/chart_sulsa_validation_20260702/pairs_unique.json`
- `artifacts/chart_sulsa_validation_20260702/mirror_insert_receipt.json`
- `.omo/evidence/ai-loop-full-next-execution-20260703/t4-mirror-duplicate-abort.json`
- `artifacts/chart_sulsa_validation_20260702/positive_control_receipt.json`
- `artifacts/chart_sulsa_validation_20260702/smoke_tick.log`
- `artifacts/chart_sulsa_validation_20260702/smoke_min.log`
- `artifacts/chart_sulsa_validation_20260702/t5_validation_summary.json`
- `.omo/evidence/ai-loop-full-next-execution-20260703/t5-smoke-timeout-blocker.json`
- `docs/research/condition_research/chart_sulsa/css_v7_validation_ledger.jsonl`

## 다음 판단

Plan C는 DB mirror까지는 완료됐지만 validation은 smoke 단계에서 보류다. 다음에는 Plan B 야간 배치로 넘어가기 전에 CSS_V7 smoke timeout 원인을 먼저 줄이는 것이 효율적이다. 예: CSS_V7 전건이 아니라 대표 1~2쌍으로 짧은 warm timeout/엔진 수/기간 축소 probe를 별도 계획으로 확인한 뒤, 정상 실행 시간이 확보되면 Plan C validation을 재개한다.
