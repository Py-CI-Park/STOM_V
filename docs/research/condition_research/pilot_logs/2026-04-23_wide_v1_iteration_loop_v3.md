# Wide v1 Iteration Loop v3 Pilot

## 목적

`WideV1IterationV2_20260423__cand005`를 기준으로 `best_feature_mix_v3` 후보 생성 규칙을 `candidate_count=10`으로 실제 실행하고, observed runtime JSON 기준으로 다음 분기 결정을 기록한다.

## 실행 조건

```text
worktree=C:\System_Trading\STOM\STOM_V.wt-wide-v3
branch=feature/wide-v1-v3-candidate-generation-rules
base_sha=682417e854b4213f722541889d3695cb0b748980
runtime_entrypoint=python .\stom_backtest.py discovery research WideV1IterationV3_20260423 ...
database_dir=C:\System_Trading\STOM\STOM_V.wt-dev\_database
input_csv=C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv
score_reference_csv=C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv
base_buy_strategy=WideV1IterationV2_20260423__cand005
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
period=20250101~20251231
time=090000~092800
avg_time=30
betting=20
engines=32
candidate_count=10
candidate_timeout=900
mode=best_feature_mix_v3
runtime_artifact=backtest/temp/wide_v1_iteration_v3_20260423.json
runtime_artifact_encoding=UTF-16 LE (Tee-Object observed output)
```

## 실행 결과

```text
status=ok
phase=candidates_evaluated
command_wall_time_seconds=1621
candidate_count_observed=10
best_candidate=WideV1IterationV3_20260423__cand001
best_reference_adjusted_score=13497.662902097409
best_trade_count=36096.0
best_trade_count_retention=0.8817451205510907
best_score_basis=reference
control_candidate=WideV1IterationV2_20260423__cand005
control_reference_adjusted_score=null
derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS
```

## v3 후보 family 분포

```json
{
  "v3_repair_trade_amount": 3,
  "v3_replace_secondary": 15,
  "v3_tighten_secondary": 15,
  "v3_control_keep_best": 1
}
```

## 상위 후보 요약

- rank=1 strategy=WideV1IterationV3_20260423__cand001 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=1.0
- rank=2 strategy=WideV1IterationV3_20260423__cand002 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=1.0
- rank=3 strategy=WideV1IterationV3_20260423__cand003 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=1.0
- rank=4 strategy=WideV1IterationV3_20260423__cand004 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9999722960992907
- rank=5 strategy=WideV1IterationV3_20260423__cand005 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9999445921985816
- rank=6 strategy=WideV1IterationV3_20260423__cand006 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9999445921985816
- rank=7 strategy=WideV1IterationV3_20260423__cand007 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9999168882978723
- rank=8 strategy=WideV1IterationV3_20260423__cand008 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9999168882978723
- rank=9 strategy=WideV1IterationV3_20260423__cand009 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9998614804964538
- rank=10 strategy=WideV1IterationV3_20260423__cand010 type=v3_tighten_secondary adjusted_score=13497.662902097409 estimated_retention=0.9998337765957447

## cleanup 결과

```text
attempted_count=9
deleted_count=9
kept_count=1
failed_count=0
kept_strategy=WideV1IterationV3_20260423__cand001
deleted_strategies=WideV1IterationV3_20260423__cand002,WideV1IterationV3_20260423__cand003,WideV1IterationV3_20260423__cand004,WideV1IterationV3_20260423__cand005,WideV1IterationV3_20260423__cand006,WideV1IterationV3_20260423__cand007,WideV1IterationV3_20260423__cand008,WideV1IterationV3_20260423__cand009,WideV1IterationV3_20260423__cand010
```

`derived_decision`은 runtime JSON field가 아니라 Task 6 계획 규칙을 observed JSON에 적용한 파생 판단이다. 여기서 PASS는 control score가 비어 있어 HOLD gate가 발동하지 않았다는 뜻이지, candidate가 control을 이겼다는 뜻은 아니다.

## 판정

```text
derived_decision=PASS_TO_V3_EXECUTION_RESULT_ANALYSIS
reason=status=ok and control_reference_adjusted_score is absent in the observed JSON, so the HOLD gate did not trigger.
```

## 관찰된 편차

- 계획서의 `python -m cli.main ...` 명령은 이 worktree에서 `No module named cli.main`으로 실패해, 동일 인자를 `python .\stom_backtest.py ...`로 재실행했다.
- `backtest/temp/wide_v1_iteration_v3_20260423.json`은 `Tee-Object` 영향으로 UTF-16 LE BOM 인코딩으로 기록됐다.
- observed JSON의 한국어 feature/expression metadata는 mojibake로 저장되어 본 문서의 상위 후보 표에는 expression 원문 대신 rank, type, retention, score만 기록했다.
- top 10 후보가 모두 동일한 `reference_adjusted_score=13497.662902097409`로 tie였고, artifact는 명시적 tie-break key를 노출하지 않는다. observed result에서는 `cand001`이 first-ranked/generated tied entry로 유지됐다.

## 남은 리스크

- observed JSON의 `control_candidate.reference_adjusted_score`가 `null`이라서 PASS 판정이 "control score 존재 시 비교" 게이트를 실제로 통과한 것은 아니다.
- top 10 후보가 모두 동일 점수이므로 실제 채택 전에는 tie-break 기준과 candidate rule 재검토가 필요하다.
- v3 best는 최종 채택본이 아니며 promote/WFO 검증은 아직 수행하지 않았다.
