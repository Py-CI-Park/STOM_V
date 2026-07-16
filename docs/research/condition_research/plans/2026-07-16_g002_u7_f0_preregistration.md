# G002 U7-F0 Offline Frame Bridge 사전등록 (2026-07-16)

> 지위: **SEALED**
>
> 이 문서는 최초 outcome attempt 전에 고정한 outcome-blind 설계다. 이 문서는 결과, receipt, claim 또는 verdict를 포함하지 않으며, 설계 이후의 관측값으로 변경·구제하지 않는다.

## 1. 근거와 추론의 경계

- **근거:** 의제 보고서는 U7-F0을 같은 진입을 고정한 common-entry paired frame 분해로 지정하고, 이 1차 패키지의 engine budget을 0으로 정했다. 역사 범위의 incumbent cohort는 2022년 101건, 2023년 197건, 총 298건이다.
- **추론(검정 대상):** 엔진과 L3의 차이가 고정 진입 자체가 아니라 exit/호가깊이/종료 규약 성분으로 설명될 수 있다. 이는 이 사전등록으로 아직 입증되지 않았고, 2022--2023은 fresh OOS나 live 성과가 아니다.
- 2024년 이후의 모든 데이터와 거래는 명시적으로 제외한다. 결과를 읽어 cohort, factor, 구간, 통계량 또는 판정을 바꾸는 rescue는 없다.

## 2. 봉인된 cohort와 계측

### 2.1 공통 진입 cohort

고정 cohort는 2022=101, 2023=197, total=298의 **U7-F0 common-entry** 거래다. 각 identity는 정확한 instrument/day/entry identity로 해소한다. 조인은 source `t0` 또는 정확한 real-clock `t0+1`만 허용한다. nearest-neighbor, fill, 보간, 대체 매칭은 금지한다. identity가 미해소·다중·상충이면 outcome을 집계하지 않고 integrity failure로 중단한다.

### 2.2 고정 2×2×2 분해

동일 cohort와 entry를 유지한 여덟 셀을 다음처럼 고정한다.

- `E0`=synthetic entry, `E1`=recorded entry
- `D0`=adverse topbook depth, `D1`=ladder3 depth
- `T0`=09:30:00 cap, `T1`=09:28:00 terminal

각 셀은 동일 거래의 year-aware standardized endpoint로 계산한다. 주 효과는 **`year-aware standardized recorded ledger endpoint - sealed L3 net`** 이다. 모델 효과는 정확히 **`E1D1T1 - E0D0T0`** 이며, residual은 주 효과에서 이 모델 효과 및 아래 exact Shapley 성분으로 설명되지 않는 고정 잔차로 보고한다. 3개 factor의 exact Shapley decomposition은 모든 factor 순열을 완전 열거하여 계산하며 근사·sampling Shapley는 허용하지 않는다.

## 3. 고정 추론과 구간

- 연도별 primary/model/residual 및 Shapley 성분을 계산하고, pooled 값은 고정 cohort 가중치 `101/298`과 `197/298`로만 결합한다. 결과 기반 재가중은 금지한다.
- whole-day, year-stratified bootstrap을 정확히 20,000회 수행하고 seed는 `20260715`로 고정한다. 각 연도에서 관측된 day cluster의 고정 개수를 whole cluster 단위로 재표본하며, 각 replicate의 연도 평균은 재표본된 whole cluster 안의 모든 row로 계산한다. pooled replicate mean은 고정 cohort 가중치 `101/298` 및 `197/298`로 결합한다. bootstrap에 fixed event-N을 주장하거나 적용하지 않는다.
- fixed-N(2022=101, 2023=197)은 identified-set missingness aggregation에만 적용한다. fixed-N partial ranges는 다음으로 한정한다: engine-only primary는 ledger `±100`, model `±200`; excluded는 exact ledger-L3 및 model `±200`이다. 다른 부분표본, trim, winsorize, alternate fill, percentile 재선택은 없다.
- annual primary와 model의 confidence interval 및 explanation confidence interval을 보고한다. bootstrap explanation은 정확히 `1 - abs(P-M)/abs(P)`로 정의하며 `P=0`이면 `0`이다.

## 4. 공유 부호와 판정

가능/보편 및 KILL은 bootstrap draw가 아니라 **analytic identified-set completions**로 판정한다. 각 연도의 primary(`P`)와 model(`M`)에 대한 completion에서 same-sign 기준은 `P`와 `M`이 같은 0이 아닌 부호이고, 동치로 `M/P ∈ [0.5, 1.5]`인 것이다. possible은 적어도 하나의 completion, universal은 모든 completion을 뜻한다.

- **PASS:** 양년의 모든 analytic identified-set completion이 same-sign `M/P ∈ [0.5, 1.5]`를 만족하고, 2022·2023 각각에서 primary CI와 model CI가 같은 0이 아닌 부호를 가지며, bootstrap explanation CI lower bound가 `>= 0.5`다.
- **KILL:** same-sign annual completion 중 `M/P ∈ [0.5, 1.5]`를 만족하는 것이 하나도 없을 때, 그리고 그때에만 KILL이다.
- **UNDETERMINED:** 위 PASS와 KILL 어느 것도 아니거나, cohort/identity/schema/provenance 무결성 실패로 estimand를 만들 수 없는 경우다.

한 연도의 양호한 점추정, pooled 결과, partial range, descriptive statistic, 다른 factor, 또는 사후 해석은 다른 연도의 실패를 rescue하지 않는다.

## 5. 실행 순서와 권한 경계

현재 engine executions=0, DB writes=0, strategy registration=0, promotion=0, outcome executions=0이다. 이 SEALED 문서는 source authority, launch authority, 결과 산출물, attempt, outcome, finalizer가 아니다.

1. **Identity-only commitment는 정확히 한 번:** 이 사전등록의 identity와 계약만 seal하며 outcome-bearing materialized input을 만들거나 읽지 않는다.
2. **Full materialization은 정확히 한 번:** identity seal이 커밋된 뒤 outcome-blind materialized input을 완전 생성하고 커밋한다. 이 단계는 결과 집계, receipt, claim, promotion을 권한화하지 않는다.
3. finalizer는 materialized input이 커밋된 **뒤에만** 발생할 수 있다. finalizer는 promotion을 authorize하지 않는다.
4. 그 뒤 receipt/claim-bound target run은 정확히 한 번만 허용한다. 재시도, rerun, variant, 보정 실행 또는 rescue run은 금지한다.

`target_db` sentinel은 기존의 비승격 경로 `scripts/u7_f0_frame_measure.py`다. 이것은 DB를 열거나 생성하지 않으며 promotion, registration 또는 engine launch를 뜻하지 않는다.

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G002-U7-F0-OFFLINE-FRAME",
  "discovery_window": {
    "start": "2022-03-23",
    "end": "2023-12-31"
  },
  "primary_estimand": "고정 U7-F0 common-entry census에서 year-aware standardized recorded ledger endpoint - sealed L3 net의 연도별 primary effect; 모델 효과 E1D1T1-E0D0T0, residual 및 exact Shapley를 함께 보고",
  "sample_floors": {
    "census_2022": 101,
    "census_2023": 197,
    "census_total": 298
  },
  "multiplicity_family": "G002 U7-F0 단일 2x2x2 common-entry factorial family; 2022·2023 shared-sign 공동 판정",
  "kill_rule": "analytic identified-set completion에서 same-sign annual M/P ∈ [0.5, 1.5]를 만족하는 completion이 하나도 없을 때에만 KILL; PASS는 양년 모든 completion의 universal 구간, 양년 same-nonzero-sign primary/model CI 및 bootstrap explanation=1-abs(P-M)/abs(P) (P=0이면 0)의 CI lower >= 0.5를 모두 요구",
  "ledger_path": "docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl",
  "authority_paths": {
    "seal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/evidence/seals",
    "promotions_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/evidence/promotions",
    "catalog_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/evidence/catalog",
    "journal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/evidence/journal",
    "backup_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/evidence/backups",
    "target_db": "scripts/u7_f0_frame_measure.py"
  },
  "dependency_roots": [
    "scripts/u7_f0_frame_measure.py"
  ],
  "dynamic_python_dependencies": [],
  "non_python_dependencies": [
    "docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/u7_f0_materialized_input.json"
  ]
}
```

이 계약은 outcome-blind design만 고정한다. receipt/claim target run 뒤의 관측, 해석, catalog 또는 promotion은 이 계약 밖의 별도 증거 사슬을 요구하며, 이 문서나 finalizer가 promotion 권한을 부여하지 않는다.
