# Wide v2 v5 direct_v4 shortfall recovery 검증

## 실행 목적

직전 `candidate_count=10` full run은 v4 후보가 4개 존재한다는 이유로 recovery가 생략되어 `selected_candidate_count=4`에서 중단되었다. 이번 실행은 direct_v4 후보가 요청 수보다 부족할 때 `direct_v4_shortfall` recovery가 실행되고, 후보 백테스트와 WFO handoff 후보 선정까지 이어지는지 검증했다.

## 실행 조건

- run_id: `WideV2V5DirectV4ShortfallRecovery_20260428`
- candidate_count: `10`
- max_rounds: `1`
- start/end: `20250101-20251231`
- seed_candidate: `WideV1Final_B_20260425`
- seed_expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
- trade_amount_feature: `B_등락율`
- elapsed: `02:05:01.5510118`
- exit_code: `0`

## 결과 요약

- status: `ok`
- stop_reason: `max_rounds_reached`
- completed_round_count: `1`
- round status: `ok`
- round phase: `candidates_evaluated`
- leaderboard_count: `20`
- final_best_candidate: `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
- final_best_expression: `66.999 <= 시가총액 < 2_580 and 등락율 > 3.535`
- final_best_adjusted_score: `112.06250936127728`
- wfo_candidate: `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`

## recovery 상태

- requested_count: `10`
- initial_v4_candidate_count: `4`
- recovery_attempted: `True`
- recovery_reason: `direct_v4_shortfall`
- recovery_needed_count: `6`
- final_candidate_pool_count: `28`
- recovery_family_counts:
  - direct_v4: `4`
  - recovered_trade_feature: `6`
  - auto_secondary_feature: `18`
- eligible_count: `28`
- planned_execution_count: `20`
- execution_count: `20`
- actual_selected_count: `10`
- row_set_identity_status: `all_distinct`

## leaderboard 상위 후보

| rank | strategy | adjusted_score | retention | actual_rowset_selected | expression |
| --- | --- | ---: | ---: | --- | --- |
| 1 | `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007` | `112.06250936127728` | `0.9518164575430406` | `True` | `66.999 <= 시가총액 < 2_580 and 등락율 > 3.535` |
| 2 | `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand003` | `70.18193557985185` | `0.9706740589436825` | `True` | `66.999 <= 시가총액 < 2_580 and 1912.72 <= 전일동시간비 < 15_653_600` |
| 3 | `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand004` | `66.2483852958148` | `0.9758899912459877` | `True` | `66.999 <= 시가총액 < 2_580 and 546.999 <= 당일거래대금 < 2_173` |
| 4 | `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand010` | `48.91465643114266` | `0.9778596440035016` | `True` | `66.999 <= 시가총액 < 2_580 and -4_737_585_770 <= 거래대금증감 < 2_585_119_850` |
| 5 | `WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand001` | `33.94050979980738` | `0.9842427779398891` | `True` | `66.999 <= 시가총액 < 2_580 and 4.39 <= 등락율 < 5.11` |

## 판단

이번 구현은 원래 문제를 해결했다.

```text
이전 실패:
v4 후보 4개
-> direct_v4_available
-> recovery_attempted=False
-> selected_candidate_count=4
-> insufficient_retention_candidates

이번 결과:
v4 후보 4개
-> direct_v4_shortfall
-> recovery_attempted=True
-> final_candidate_pool_count=28
-> execution_count=20
-> actual_selected_count=10
-> final_best_candidate 선정
```

즉 후보 생성/보강 단계는 MVP 다음 단계로 넘어갈 수 있다. 다만 실행 시간이 `02:05:01`로 길어진 이유는 `candidate_count=10`이 실제 실행 10개가 아니라, v5 oversampling 정책에 따라 eligible 후보 28개 중 최대 20개를 백테스트했기 때문이다.

## 관찰된 보완점

`backtest/temp/wide_v2_v5_direct_v4_shortfall_recovery_20260428_summary.json`은 UTF-8로 읽으면 정상 파싱된다. PowerShell 기본 인코딩으로 읽으면 한국어가 깨져 보일 수 있으므로 확인 시 `-Encoding UTF8` 또는 Python `encoding='utf-8'`을 사용해야 한다.

생성된 optimizer Markdown report의 `## V5 recovery` 섹션은 success case에서 top-level recovery metadata를 받지 못해 빈 값으로 표시된다. 이번 리뷰는 유효한 round JSON의 `iteration_v5` metadata를 기준으로 작성했다. 이는 WFO/OOS 검증을 막는 문제는 아니지만, 운영 관측성을 위해 후속으로 보강하는 것이 좋다.

## 다음 단계

final_best_candidate와 wfo_candidate가 존재하므로 다음 MVP 단계는 WFO/OOS 검증 실행 계획이다.

```text
$writing-plans Wide v2 WFO/OOS 검증 실행 계획 작성
```
