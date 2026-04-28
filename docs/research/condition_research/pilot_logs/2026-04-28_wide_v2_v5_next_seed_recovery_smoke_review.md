# Wide v2 v5 next seed recovery smoke 검토

## 실행 목적

Wide v2 v5 반복 루프에서 round best 조건식이 다음 라운드 seed 형식에 맞지 않을 때 즉시 중단하지 않고, ranked 후보 중 seed-compatible 후보를 찾아 다음 라운드로 계속 진행하는지 검증했다.

이번 검증은 WFO/OOS가 아니라 `candidate_count=2`, `max_rounds=2` smoke다. 목표는 좋은 조건식 확정이 아니라 round002 진입 실패(`invalid_seed_expression`) 복구 여부 확인이다.

## 실행 명령

```powershell
$env:PYTHONUTF8='1'
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2V5NextSeedRecoverySmoke_20260428 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --seed-candidate WideV1Final_B_20260425 `
  --seed-expression "66.999 <= 시가총액 < 2_580 and 등락율 > 4.83" `
  --iteration-v2-trade-amount-feature "B_등락율" `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428.json `
  --leaderboard-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_leaderboard.json `
  --summary-output backtest\temp\wide_v2_v5_next_seed_recovery_smoke_20260428_summary.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-28_wide_v2_v5_next_seed_recovery_smoke_summary.md
```

## 결과 요약

- status: `ok`
- stop_reason: `max_rounds_reached`
- completed_round_count: `2`
- failed_round: 없음
- failure_phase: 없음
- leaderboard_count: `8`
- 소요 시간: 약 `00:56:02`

## 핵심 복구 증거

- round001 best: `WideV2V5NextSeedRecoverySmoke_20260428__round001__cand003`
- rejected reason: `invalid_seed_expression`
- rejected expression: `66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173`
- next seed selection: `compatible_fallback`
- fallback seed: `WideV2V5NextSeedRecoverySmoke_20260428__round001__cand001`
- fallback expression: `66.999 <= 시가총액 < 2_580 and 4.39 <= 등락율 < 5.11`

즉, 수익/점수 기준의 round best는 그대로 global best 후보로 보존했고, 다음 라운드 실행용 seed만 v5 형식에 맞는 cand001로 분리 선택했다.

## 라운드 흐름

```text
initial seed
-> round001 실행
-> round001 best cand003 선택
-> cand003은 v5 next seed 형식 불일치
-> ranked 후보에서 cand001 compatible fallback 선택
-> round002 실행 성공
-> max_rounds=2 도달로 정상 종료
```

## 퀀트 관점 해석

이번 결과는 조건식 수익성을 확정한 것이 아니다. 다만 자동 개선 루프에 필요한 최소 동작, 즉 "가장 좋은 후보"와 "다음 탐색을 이어갈 수 있는 seed 후보"를 분리하는 구조가 실제 백테스트 실행에서도 작동함을 확인했다.

최종 WFO handoff 후보는 여전히 global best인 `round001__cand003`이다. 이 후보는 점수 기준으로 가장 좋지만, v5 seed로는 부적합하다. 따라서 다음 full run에서도 보고서에 `next_seed_selection_status`를 반드시 확인해야 한다.

## CLI 관점 해석

이전 실패 원인이었던 round002 seed validation 중단은 해결됐다. 결과 파일과 Markdown 보고서에 다음 metadata가 남는다.

- `next_seed_selection_status`
- `next_seed_strategy_name`
- `next_seed_expression`
- `rejected_round_best_seed_strategy_name`
- `rejected_round_best_seed_expression`
- `rejected_round_best_seed_reason`

초기 smoke 재실행 시 PowerShell `Start-Process -ArgumentList` quoting 문제로 seed expression이 쪼개지는 실행 실패가 한 번 있었다. 이는 CLI 로직 실패가 아니며, 인자 quoting을 명시적으로 검증한 뒤 재실행했다.

## 판정

다음 단계로 넘어갈 수 있다.

조건:

- `invalid_seed_expression`으로 중단되지 않았다.
- round002가 실제 실행됐다.
- 최종 종료 사유가 `max_rounds_reached`다.
- summary/report에 next seed 선택 근거가 남았다.

## 다음 추천 단계

바로 `candidate_count=10` full run 계획으로 넘어간다. 다만 이번 smoke가 약 56분 걸렸으므로 full run은 2시간 이상 걸릴 가능성이 있다. full run 전 계획 문서에는 실행 시간 제한, 로그 위치, 중단 기준, 결과 판정 기준을 명확히 포함해야 한다.

추천 명령:

```text
$writing-plans Wide v2 v5 candidate_count=10 full run 및 WFO handoff 후보 선정 계획 작성
```
