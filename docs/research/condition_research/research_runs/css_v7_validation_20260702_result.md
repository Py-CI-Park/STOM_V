# CSS_V7 검증 결과 - Plan C T4~T5

- 실행일: 2026-07-03
- 범위: T4~T5 only
- 원문: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md`
- 산출물 루트: `artifacts/chart_sulsa_validation_20260702/`

## T4 결과

| 항목 | 결과 | 증거 |
|---|---:|---|
| CSS_V7 static gate | checked=25, bad=0 | `static_gate_report.json` |
| 유니크 페어 | 21개 | `pairs_unique.json` |
| tick 페어 | 7개 | `pairs_tick.json` |
| min 페어 | 14개 | `pairs_min.json` |
| loop DB mirror | INSERT 25건 | `mirror_insert_receipt.json` |
| loop DB backup | 생성됨 | `ai_strategy_loop/state/loop_strategies.db.bak.css_v7_20260703T064540Z` |
| duplicate-name abort | collision_abort, exit=3 | `.omo/evidence/ai-loop-full-next-execution-20260703/t4-mirror-duplicate-abort.json` |

## T5 결과

| 항목 | 결과 | 증거 |
|---|---:|---|
| positive control | gate_healthy | `positive_control_receipt.json` |
| tick smoke | 7/7 timeout | `smoke_tick.log` |
| min smoke | prepare 후 첫 페어 장시간 무출력으로 중단 | `smoke_min.log` |
| train | 미실행 | smoke go 후보 없음 |
| OOS/WF | 미실행 | train 후보 없음 |
| survivor export | 0건 | `css_v7_survivors_for_plan_d.jsonl` |

## 최종 판정

| 상태 | 개수 | 설명 |
|---|---:|---|
| 생존 | 0 | smoke 통과 후보 없음 |
| 기각 | 0 | 성능 열위로 기각한 후보 없음 |
| 보류 | 21 | smoke timeout 또는 smoke 미완료 blocker |

T5는 smoke 단계에서 중단한다. tick lane은 전건 `백테스트 시간 초과 (300초)`였고, min lane은 `bt_warm_run_timeout=1200` 설정에서 첫 페어부터 계획서 기대 시간보다 길어져 전체 14건 실행을 중단했다. 따라서 train/OOS/WF/slippage는 열지 않았다.

## Lineage

`python scripts/check_research_evidence_lineage.py --report artifacts/chart_sulsa_validation_20260702/lineage_report.json`를 실행했다. 결과는 exit 1이며, 보고된 error/warning은 기존 `.omo/evidence/tmap-walkforward` 과거 산출물의 누락/불일치 이슈다. 이번 CSS_V7 T4/T5 산출물 blocker는 `t5-smoke-timeout-blocker.json`에 별도 기록했다.
