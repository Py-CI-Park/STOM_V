# G005-C2 활성화 순서 사전등록 (2026-07-16)

> 지위: **SEALED**
>
> 이 문서는 `G005-C2-ACTIVATION-ORDER`의 outcome-blind 설계와 기각된 identified design record만 고정한다. 정확한 pre-existing activation trace 권위가 발견되지 않았으므로 이 SEALED family의 현재 terminal status는 **UNDETERMINED / nonidentified**이며, 결과값, target/materialization, receipt, claim, ledger row, promotion 또는 target invocation을 만들지 않는다.

## 1. 고정 가설과 발견 창

- 발견 창은 **2022-03-23..2023-12-31**로 고정한다. 2024년 이후 데이터, live, engine 재생, 신규 DB 산출물은 모두 제외한다.
- C2는 **동시활성 tie가 아닌 활성화 순서**만 검정한다. 정확한 첫 활성화 timestamp가 같은 경우는 C2에서 제외하고 C1 계열에 속한다.
- 고정 sibling hypothesis는 정확히 두 개다.
  - **H37:** clause16과 pressure clause37의 첫 활성화 순서가 outcome과 관련되는지, `16->37 minus 37->16`으로 평가한다.
  - **H38:** clause16과 pressure clause38의 첫 활성화 순서가 outcome과 관련되는지, `16->38 minus 38->16`으로 평가한다.
- H37과 H38은 서로 대체·구제하지 않는다. 한 비교의 common support, 부호, CI 또는 판정은 다른 비교의 설계 변경 근거가 될 수 없다.

## 2. 필수 입력과 현재 권한 제한

기각된 identified design record에서 C2 target input은 각 row마다 다음 필드를 모두 가져야 했다.

1. `code`, `day`, `t0`
2. clause16, clause37, clause38의 **정확한 첫 활성화 timestamp**
3. 최종 full 39-bit state (`bit_1`..`bit_39` 전체 벡터)
4. outcome
기각된 identified design record에서 요구한 각 activation timestamp는 Asia/Seoul wall-clock seconds의 정확한 14자리 숫자 문자열 `YYYYMMDDHHMMSS`여야 했다. fractional/subsecond 값의 반올림·절삭·보정은 금지한다. 각 timestamp의 첫 8자리는 정확한 `day`(`YYYYMMDD`)와 같아야 하며, 비교되는 clause16과 pressure timestamp는 모두 같은 day를 공유해야 한다. timezone conversion, day-rollover repair, 자정 넘김 보정은 금지한다.

현재 권한으로 확인된 safe sentinel인 `docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet`는 `code/day/off/t0`와 `bit_1`..`bit_39`만 보유하며, transition timestamp, activation order, outcome을 보유하지 않는다. 정확한 pre-existing pre-outcome activation trace authority는 발견되지 않았다. 따라서 이 family는 지금 **terminal UNDETERMINED / nonidentified**로 닫으며, target invocation, materialization, receipt, claim 또는 ledger row를 만들지 않는다.

이 관측 이후에는 결측 trace를 만들기 위해 새 trace를 구성하거나 engine/DB를 replay하지 않는다. snapshot bit, flat final bit, `off`, D1 interaction 결과, D1 pairwise 재사용, C1 tie logic, 또는 final 39-bit snapshot proxy로 activation order를 대체하는 것은 모두 금지한다.

## 3. 기각된 design record: denominator, 매칭, offset 고정
아래 denominator, matching, estimand, bootstrap, kill rule은 exact trace authority가 있었다면 사용할 **hypothetical identified logic**의 기록일 뿐이며, 이 hypothesis에 대한 실행 권한을 부여하지 않는다.

- C2 eligible row는 해당 pressure id별로 clause16과 pressure clause의 정확한 첫 활성화 timestamp가 모두 존재하고, tie가 아니며, 최종 full 39-bit state와 outcome이 존재하는 row뿐이다.
- pressure id는 **37과 38을 분리**한다. `16 vs 37`의 denominator와 matched set, `16 vs 38`의 denominator와 matched set은 독립적으로 산정한다.
- order label은 `t16 < t_pressure`이면 `16->pressure`, `t_pressure < t16`이면 `pressure->16`이다. `t16 == t_pressure`는 tie로 C2에서 제외한다.
- absolute activation lag는 `abs(t16 - t_pressure)` 초로 계산하고, match bucket은 고정된 여섯 구간 `[0,1]`, `[2,5]`, `[6,15]`, `[16,30]`, `[31,60]`, `61+` seconds만 사용한다. 정확히 같은 timestamp인 tie는 `[0,1]` bucket에 넣지 않는다.
- opposite order는 pressure id별로 다음 key가 모두 정확히 같은 경우에만 같은 matched set으로 묶는다: `pressure_id`, `year`, `code`, `full final 39-bit state`, `t0 minute bucket`, `absolute activation-lag bucket`.
- `t0`는 exact 14-digit `YYYYMMDDHHMMSS`이고 같은 `day` 위에 있어야 한다. `t0 minute bucket`은 `t0`의 첫 12자리에 `00`을 붙인 값이다. nearest-neighbor, fill, interpolation, 다른 offset, timezone conversion, day rollover 보정, 결과 기반 bucket 재선택은 금지한다.
- matched set floor는 pressure id별 `matched_sets >= 1`이다. 이 floor를 충족하지 못하거나 양 order의 common support가 없으면 해당 비교는 outcome을 읽지 않고 **UNDETERMINED**다.

## 4. estimand, bootstrap, 연도별 보고

- 각 matched set `s`의 contrast는 `mean(outcome | 16->pressure, s) - mean(outcome | pressure->16, s)`다.
- pressure id별 primary estimate는 matched-set contrast의 산술평균이다. row count 차이, outcome 크기, 연도별 사후 가중치로 재가중하지 않는다.
- annual estimate와 CI는 2022와 2023을 각각 보고한다. pooled estimate와 CI도 pressure id별로 보고하되, H37과 H38을 서로 합치지 않는다.
- CI는 whole-day block bootstrap 20,000회로 계산하고 seed는 **2026071604**로 고정한다. bootstrap은 day cluster를 단위로 하며, 결과 확인 뒤 replicate 수, seed, cluster 단위, matched-set 가중, pressure 비교군을 바꾸지 않는다. bootstrap CI는 nearest-rank quantile로만 계산한다: `Q(p)=sorted_x[ceil(p*n)-1]`, CI는 `[Q(.025), Q(.975)]`다. bootstrap replicate가 하나라도 undefined이면 그 replicate를 drop하거나 보정하지 않고 PASS/KILL보다 먼저 **UNDETERMINED**로 종료한다.

## 5. PASS / KILL / UNDETERMINED 규칙

각 pressure id 비교(H37, H38)를 독립적으로 판정한다. 판정 우선순위는 integrity·nonidentification·undefined bootstrap replicate에 따른 UNDETERMINED가 먼저이고, 그 다음에만 KILL/PASS를 평가한다.

- **PASS:** integrity가 통과하고 undefined bootstrap replicate가 없으며, pooled CI가 0을 제외하고, 2022 annual estimate와 2023 annual estimate의 부호가 같은 0이 아닌 부호다.
- **KILL:** integrity가 통과하고 estimand가 식별된 뒤, pooled CI가 0을 포함하거나, 어느 annual estimate가 정확히 0이거나, 2022와 2023의 annual sign이 충돌하면 KILL이다.
- **UNDETERMINED:** exact activation timestamps, outcome, full final 39-bit state, required identity, matched-set floor, 또는 opposite-order common support가 measurement 전에 확보되지 않아 estimand를 만들 수 없는 경우다. activation timestamp나 `t0`가 exact 14-digit `YYYYMMDDHHMMSS`가 아니거나, 첫 8자리가 `day`와 다르거나, 비교 timestamp들이 같은 day를 공유하지 않는 경우도 UNDETERMINED다. bootstrap replicate가 하나라도 undefined인 경우도 drop 없이 UNDETERMINED다.

Absent activation timestamps나 absent common support는 KILL이 아니라 UNDETERMINED이며, snapshot bits 또는 flat final-bit proxy로 구제할 수 없다. 한 연도의 우수한 점추정, 다른 pressure id의 PASS, descriptive count, D1 interaction, C1 tie 결과, 또는 사후 family redesign은 KILL/UNDETERMINED를 rescue하지 않는다.

## 6. 실행·권한·no-retry 경계

- `execution_authorized:false`다. 이 문서는 source authority, launch authority, materialization authority, receipt, claim, result report, ledger append 또는 promotion이 아니다.
- 이 family는 정확한 pre-existing trace authority 부재로 이미 terminal nonidentified이므로 **target invocation, materialization, receipt, claim, ledger row를 만들지 않는다**.
- 이 hypothesis에는 나중에 어떤 trace도 attach할 수 없다. 향후 activation-order 연구는 G005 밖의 새로운 hypothesis와 새로운 preregistration을 요구한다.
- 신규 trace 생성, later trace attachment, trace replay, snapshot/flat-bit proxy, D1 interaction reuse, family redesign, 2024+ 확장, engine 실행, DB write, strategy registration, promotion, retry, rerun, variant run, 또는 rescue run은 금지한다.
- 아래 authority directory들은 sealed namespace 기록일 뿐이며, 이 사전등록 자체가 directory 생성, target DB 생성, ledger append 또는 protected artifact 생성을 승인하지 않는다.
- `scripts/g005_c2_nonidentification_guard.py`는 strict parser schema를 만족시키기 위한 static schema sentinel이며 executable entrypoint가 없다. 이 정적 선언은 `execution_authorized:false` 상태를 바꾸지 않고 authorized target, invocation, materialization, receipt, claim, ledger row 또는 promotion이 아니다.

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G005-C2-ACTIVATION-ORDER",
  "discovery_window": {
    "start": "2022-03-23",
    "end": "2023-12-31"
  },
  "primary_estimand": "Rejected design record only, not execution authority: pressure id 37 and 38 separately; within-matched-set mean outcome difference, 16->pressure minus pressure->16, matched exactly on pressure_id, year, code, full final 39-bit state, t0 minute bucket, and fixed absolute activation-lag bucket; activation timestamps and t0 must be exact 14-digit Asia/Seoul YYYYMMDDHHMMSS strings on the same day, with t0 minute bucket equal to first 12 chars plus 00",
  "sample_floors": {
    "matched_sets": 1
  },
  "multiplicity_family": "G005-C2 activation-order family with exactly two fixed sibling comparisons: clause16 vs pressure clause37 and clause16 vs pressure clause38; no proxy, no redesign, no cross-comparison rescue",
  "kill_rule": "Rejected identified logic only: for each pressure comparison separately, PASS requires integrity, no undefined bootstrap replicate, pooled CI excludes 0, and 2022/2023 annual signs agree and are nonzero; after integrity, KILL if pooled CI includes 0, any annual estimate is exactly 0, or annual signs conflict; UNDETERMINED first if exact activation timestamps, exact 14-digit same-day t0, outcome, full final 39-bit state, matched_sets>=1, opposite-order common support, or bootstrap replicate definition is absent, or if timestamp format/day equality fails; absent timestamps/common support cannot be proxied by snapshot bits",
  "ledger_path": "docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl",
  "authority_paths": {
    "seal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2/evidence/seals",
    "promotions_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2/evidence/promotions",
    "catalog_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2/evidence/catalog",
    "journal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2/evidence/journal",
    "backup_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2/evidence/backups",
    "target_db": "scripts/g005_c2_nonidentification_guard.py"
  },
  "dependency_roots": [
    "scripts/g005_c2_nonidentification_guard.py"
  ],
  "dynamic_python_dependencies": [],
  "non_python_dependencies": [
    "docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet"
  ]
}
```

이 SEALED 계약은 C2의 사전 확정 가설, denominator, seed, matching/offset, kill/UNDETERMINED rule, no-retry boundary를 기각된 design record로 보존한다. 현재 static schema sentinel에는 order와 outcome authority가 없고 executable entrypoint도 없으며 정확한 pre-existing activation trace authority도 발견되지 않았으므로 이 hypothesis는 지금 terminal UNDETERMINED / nonidentified다. 이후 어떤 trace도 이 hypothesis에 붙일 수 없고 어떤 measurement artifact나 outcome claim도 만들 수 없다.
