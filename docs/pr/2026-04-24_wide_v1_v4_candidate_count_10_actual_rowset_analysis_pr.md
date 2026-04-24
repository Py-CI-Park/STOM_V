# Wide v1 v4 candidate_count=10 actual row-set 분석 PR 보고서

## 1. 목적

Wide v1 v4 후보 생성 규칙이 proxy row-set diversity를 실제 실행 row-set 다양성으로 연결하는지 확인했다. 이번 PR은 `best_feature_mix_v4`를 `candidate_count=10`으로 실제 실행하고, 생성된 후보 CSV 10개의 actual row-set을 분석해 다음 단계가 promote/WFO인지, 아니면 v5 보강 설계인지 결정한다.

## 2. 전체 계획

1. v4 runtime 실행 전 `runtime-preflight`로 전략 DB, 백테스트 DB, 매수/매도 전략을 검증한다.
2. 기존 CLI entrypoint인 `python .\stom_backtest.py discovery research ...`만 사용해 v4 후보 10개를 실행한다.
3. `--cleanup-best-candidate`를 유지해 임시 후보 전략을 DB에 남기지 않는다.
4. runtime JSON에서 proxy row-set selection과 v4 family 분산을 기록한다.
5. 후보 CSV의 actual row-set을 다시 묶어 실제 체결 row-set 중복 여부를 판단한다.
6. actual row-set이 모두 distinct이고 2개 이상 v4 family가 실행됐을 때만 promote/WFO 계획으로 진행한다.

## 3. 현재 실행 계획과 변경

- 계획 파일: `docs/superpowers/plans/2026-04-24-wide-v1-v4-candidate-count-10-actual-rowset-analysis.md`
- 실행 로그: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_iteration_loop_v4.md`
- row-set 분석: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_rowset_diversity.md`
- 최종 판단: `docs/research/condition_research/pilot_logs/2026-04-24_wide_v1_v4_execution_decision.md`

실행 중 `scripts/analyze_wide_v1_v4_rowset_diversity.py`가 v4 runtime 전체 후보가 아니라 v3 tie-break 후보만 분석하는 문제가 확인됐다. 그래서 `cli/research_v4_rowset.py`를 추가해 v4 실행 후보 전체를 직접 분석하도록 수정했고, 기존 script는 새 v4 전용 분석기를 호출하도록 바꿨다.

## 4. runtime 결과

```text
runtime_name=WideV1IterationV4_20260424
runtime_path=backtest\temp\wide_v1_iteration_v4_20260424.json
status=ok
phase=candidates_evaluated
candidate_result_count=10
candidate_status_counts={'ok': 10}
best_candidate=WideV1IterationV4_20260424__cand002
cleanup_deleted_count=10
cleanup_kept_count=0
```

v4 proxy selection은 10개 proxy group을 선택했고, proxy 중복 skip은 0개였다.

```text
selected_count=10
proxy_group_count=10
skipped_duplicate_proxy_count=0
```

## 5. actual row-set 결과

actual row-set 분석 결과는 `partially_distinct`다. 후보 10개가 9개 actual row-set group으로 묶였고, `cand004`와 `cand005`가 같은 row-set으로 collapse 됐다.

```text
row_set_identity_status=partially_distinct
candidate_count=10
group_count=9
decision=HOLD_V4_ROW_SET_REVIEW
next_command=$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```

v4 family 실행 분포는 4개 family로 분산됐다.

```text
{'v4_replace_secondary': 5, 'v4_relax_trade_amount': 2, 'v4_repair_trade_amount': 1, 'v4_tighten_secondary': 2}
```

중복 group:

```text
group_id=9
row_count=36096
representative=WideV1IterationV4_20260424__cand004
representative_family=v4_tighten_secondary
members=['WideV1IterationV4_20260424__cand004', 'WideV1IterationV4_20260424__cand005']
```

## 6. 전문가 판단

퀀트 관점에서는 promote/WFO로 바로 이동하지 않는 판단이 맞다. family 분산은 개선됐지만 actual row-set이 완전히 분리되지 않았으므로, 후보 생성의 다양성이 실제 체결 집합 다양성으로 완전히 전환됐다고 볼 수 없다.

CLI 개발 관점에서는 이번 수정이 필요했다. 기존 wrapper는 v3 tie-break 분석기를 재사용해 v4 runtime의 정상 후보 10개를 `candidate_count=0`으로 오판했다. v4 전용 row-set analyzer를 분리해 runtime 구조와 분석 목적이 일치하도록 만들었다.

전체 프로그램 관점에서는 기존 CLI entrypoint와 DB cleanup 계약을 유지했다. serial-key 관련 로직은 건드리지 않았고, `backtest/csv`, `backtest/graph`, `backtest/temp` 산출물은 소스 변경으로 stage하지 않는다.

## 7. 검증 결과

```text
python -m pytest tests/unit/test_research_v4_rowset.py tests/unit/test_research_v3_tiebreak.py tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_research_report.py -q
119 passed

python -m ruff check cli/research_v4_rowset.py cli/research_iteration_v4.py cli/research_loop.py cli/research_report.py scripts/analyze_wide_v1_v4_rowset_diversity.py tests/unit/test_research_v4_rowset.py tests/unit/test_research_iteration_v4.py tests/unit/test_research_loop.py tests/unit/test_research_report.py tests/unit/test_research_v3_tiebreak.py
All checks passed

basedpyright cli\research_v4_rowset.py cli\research_iteration_v4.py scripts\analyze_wide_v1_v4_rowset_diversity.py tests\unit\test_research_v4_rowset.py tests\unit\test_research_iteration_v4.py
0 errors, 0 warnings, 0 notes

python scripts\verify_nonrelease_sync.py
passed

git diff --check --ignore-cr-at-eol
passed, CRLF conversion warnings only
```

## 8. 남은 리스크

- v4는 10개 후보 중 1쌍이 actual row-set 중복으로 collapse 됐다.
- runtime stdout을 PowerShell `Tee-Object`로 저장할 때 한글 표시가 깨져 보일 수 있다. 분석은 `read_runtime_json`과 CSV path 기반으로 통과했다.
- 이번 PR은 promote/WFO를 실행하지 않았다.

## 9. 다음 단계

```text
$brainstorming Wide v1 v5 actual row-set diversity selection 보강 설계
```
