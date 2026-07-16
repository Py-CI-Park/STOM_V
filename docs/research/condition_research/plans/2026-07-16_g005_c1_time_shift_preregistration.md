# G005-C1 Time-Shift 사전등록 (2026-07-16)

> 지위: **SEALED**
>
> 이 문서는 `G005-C1-TIME-SHIFT`의 결과 관측 전 설계를 봉인한다. 기존 또는 향후 교호작용 결과값을 포함하지 않으며, 2022--2023 역사 진단만 고정한다. 이는 fresh OOS, live 전략 성과, 매수·매도 규칙 승격 또는 실전 proof가 아니다.

## 1. 고정 가설과 발견창

- 가설 ID: **`G005-C1-TIME-SHIFT`**.
- 발견창은 정확히 **2022-03-23..2023-12-31**이다. 2024년 이후 데이터, 엔진 재실행, DB 쓰기, 전략 등록, promotion은 모두 금지한다.
- 고정 family는 두 쌍 **`(16,37)`**, **`(16,38)`**뿐이다. 두 쌍은 하나의 C1 time-shift family로 공동 판정하며, 한 쌍의 성공이 다른 쌍의 실패를 rescue하지 않는다.
- 각 쌍의 귀무/대립은 outcome 관측 전에 고정한다: bit16과 압력 bit37 또는 bit38의 관측 교호작용이 시간-구조 보존 placebo보다 크고, 2022·2023 각각에서도 양의 일자블록 하한을 가져야 한다.

## 2. 고정 입력, 조인, denominator

### 2.1 원천 파일 지문

측정 전 builder/materialization과 finalizer는 아래 원천의 **pre/post bytes**를 모두 묶어야 한다. 어느 한 지문이라도 불일치하면 결과를 집계하지 않고 `UNDETERMINED`로 중단한다.

| 원천 | 경로 | 행수 | SHA-256 | 크기(bytes) |
|---|---|---:|---|---:|
| L3 onset bank | `C:/System_Trading/STOM/STOM_V.wt-alpha/docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet` | 863,446 | `0b6268e0eff8e73831539aba8ff83b8a02608405269732a33c78565c3bfa22fd` | 11,741,034 |
| local D1 bits | `docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet` | 863,446 | `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56` | 6,783,855 |

### 2.2 조인과 eligibility

- 두 원천은 정확히 `(code, day, off, t0)` 키로 **1:1 전수 조인**한다. 누락, 중복, 다중 매칭, 타입 변환에 따른 키 변경, nearest-neighbor, fill, 보간, 대체 매칭은 금지한다.
- 조인 후 고정 sample floor는 `joined_rows = 863446`이다.
- 판정 eligible row는 `year ∈ {2022, 2023}`이고 `l3_labeled == true`인 행만이다. 고정 labeled floor는 `labeled_rows = 862932`이다.
- `Y`는 `l3_net`이며 단위는 percentage points(%p)다. `Y`, bit16, bit37, bit38, year, code, day, off, t0 중 필수값이 nonfinite 또는 결측이면 identified measurement가 아니므로 `UNDETERMINED`다.
- 관측 교호작용 denominator는 각 쌍의 eligible labeled rows 전체다. placebo 판정 support는 아래 §4의 shift 가능한 `(code,day)` 그룹 행만이며, 그룹 크기 `<2` 행은 변경하지 않고 수량만 보고하며 placebo-decision support에서는 제외한다.

### 2.3 셀 floor와 day support

각 고정 쌍 `(16,B)`에 대해 관측 4셀 `(bit16, bitB) ∈ {00,01,10,11}`이 모두 다음을 만족해야 한다.

- pooled 2022--2023 각 셀 `n >= 2000`.
- 2022와 2023 각각에서 각 셀 `n >= 400`.
- 각 연도 일자블록 bootstrap을 식별할 수 있도록 연도별 eligible day support가 충분해야 하며, 사전 고정 bootstrap draw에서 필요한 4셀 평균이 하나라도 비거나 nonfinite가 되면 `UNDETERMINED`다.

셀 floor, day support, schema, provenance, 조인 무결성은 outcome 값으로 완화하거나 재정의하지 않는다.

## 3. 관측 estimand

각 쌍 `(16,B)`에서 `B ∈ {37,38}`로 고정한다. 셀 평균을 `μab = mean(Y | bit16=a, bitB=b)`로 두고, 관측 교호작용은 다음 하나뿐이다.

```text
I(16,B) = μ11 - μ10 - μ01 + μ00
```

- `I`의 단위는 `%p`다.
- bit 극성, 쌍 목록, denominator, year filter, labeled filter는 측정 후 변경하지 않는다.
- code-cluster leave-one-code-out 민감도는 descriptive only다. 어떤 code 제외 결과도 PASS, KILL, rescue, 재측정 또는 promotion 근거가 아니다.

## 4. Time-shift placebo 설계

- placebo offset RNG는 Python `random.Random(2026071601)` 하나로 고정한다. replicate는 `0..399` 순서로 정확히 400개 처리한다.
- 각 replicate 안에서 `(code, day)` 그룹은 `(str(code), int(day))`의 lexicographic 오름차순으로 처리하고, 각 그룹 내부 행은 `(off, t0)` 오름차순으로 정렬한다.
- 그룹 크기 `n >= 2`이면 해당 그룹에서 `rng.randrange(1,n)`을 정확히 한 번 호출해 deterministic nonzero circular offset을 선택한다. offset 후보는 `1..n-1`뿐이며 zero offset, offset retry, 결과 기반 offset 선택은 금지한다.
- 그룹 크기 `<2`에서는 offset을 만들지 않고 RNG도 호출하지 않으며 count만 보고한다. 이 행들은 placebo 95th percentile의 decision support에서 제외하며, 제외율을 보고하되 PASS/KILL rescue에 쓰지 않는다.
- 같은 그룹·replicate의 bit37과 bit38은 **동일 offset으로 함께 shift**한다. 이렇게 하여 bit37--bit38의 joint pressure 구조를 보존한다.
- bit16과 `Y=l3_net`은 고정한다. `(16,37)` placebo에는 shifted bit37을, `(16,38)` placebo에는 shifted bit38을 사용한다.
- placebo offset 생성 경로에는 위 `rng.randrange(1,n)` 외 다른 RNG 호출이 없다(no other RNG calls).
- 각 쌍의 placebo 기준값은 400개 placebo `I`를 오름차순 정렬한 nearest-rank `Q(.95)`다. sorted `n` values `x`에 대해 `Q(p)=x[ceil(p*n)-1]`로 고정하며, interpolation, trimming, replicate 제외, offset 재시도 또는 seed 변경을 하지 않는다.

## 5. 일자블록 bootstrap과 민감도

- day-block bootstrap seed는 **`2026071602`**이며, draw 수는 정확히 **20,000**이다.
- bootstrap은 2022와 2023 annual strata를 분리한다. 각 연도에서 관측 eligible day cluster 수와 같은 개수의 day를 복원추출하고, 선택된 whole-day rows로 4셀 평균과 `I(16,B)`를 재계산한다.
- 각 쌍·연도별 관측 `I`의 percentile 95% CI는 bootstrap draw를 오름차순 정렬한 nearest-rank `[Q(.025), Q(.975)]`다. sorted `n` values `x`에 대해 `Q(p)=x[ceil(p*n)-1]`로 고정한다. PASS 판정에는 각 쌍의 2022 lower CI와 2023 lower CI가 모두 `> 0`이어야 한다.
- 400개 placebo replicate 중 하나라도, 또는 20,000개 bootstrap draw 중 하나라도 필요한 4셀 finite mean을 모두 만들지 못하면 PASS/KILL 평가 전에 terminal `UNDETERMINED`로 중단한다. 어떤 placebo replicate나 bootstrap draw도 drop할 수 없다.
- code-cluster leave-one-code-out은 각 code를 하나씩 제외한 descriptive sensitivity만 산출한다. 이 결과는 설명용이며 판정 문턱, denominator 또는 family를 바꾸지 않는다.

## 6. 판정 규칙

- **PASS:** 두 쌍 `(16,37)`과 `(16,38)` 모두에서 관측 pooled `I`가 해당 쌍의 placebo 95th percentile보다 **strictly greater**이고, 각 쌍의 2022 및 2023 day-block bootstrap 95% CI lower bound가 모두 `> 0`일 때만 PASS다.
- **KILL:** provenance/schema/join/cell floor/nonfinite/insufficient day support가 통과되어 identified measurement가 성립한 뒤, 위 PASS 조건 중 하나라도 실패하면 KILL이다. 한 쌍, 한 연도, 한 threshold의 실패도 전체 C1 family KILL이다.
- **UNDETERMINED:** 유효한 결과값을 만들기 전 provenance, schema, 1:1 join, sample floor, cell floor, nonfinite, 또는 insufficient day support 실패가 발생한 경우에만 사용한다.

KILL 뒤 pair rescue, offset retry, seed 변경, denominator 재정의, 셀 병합, 2024+ 확장, 추가 family 분리, 엔진 실행, DB write, strategy registration, catalog promotion은 모두 금지한다.

## 7. 실행 경계와 sealed materialization 순서

현재 이 문서는 source authority, outcome 산출물, finalizer, receipt, claim 또는 promotion이 아니다.

1. **Seal only:** 이 문서와 고정 계약만 커밋한다. 이 단계에서 outcome read, measurement, ledger append, DB write, engine action은 금지한다.
2. **Builder/materialization:** future input `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_input.json.gz`을 정확히 한 번 만들 수 있다. builder는 §2.1 원천의 pre bytes와 materialization 후 post bytes를 finalizer 전에 evidence로 묶어야 한다.
3. **Finalizer:** materialized input과 source pre/post binding이 커밋된 뒤에만 가능하다. finalizer는 promotion 또는 registration 권한을 부여하지 않는다.
4. **Receipt/claim target run:** `scripts/g005_c1_time_shift.py` target execution은 receipt/claim-bound로 정확히 한 번만 허용한다. rerun, retry, variant run, 보정 실행 또는 rescue run은 금지한다.

`target_db` sentinel은 기존 비승격 코드 경로 `scripts/g005_c1_time_shift.py`를 가리키는 authority-schema 자리일 뿐이며, DB 생성·쓰기·등록·promotion을 뜻하지 않는다.

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G005-C1-TIME-SHIFT",
  "discovery_window": {
    "start": "2022-03-23",
    "end": "2023-12-31"
  },
  "primary_estimand": "Eligible 2022-2023 l3_labeled rows에서 fixed pairs (16,37), (16,38)의 I=mean(Y|11)-mean(Y|10)-mean(Y|01)+mean(Y|00), Y=l3_net percentage points; pooled observed I를 time-shift placebo 95th percentile과 비교하고 2022 및 2023 annual day-block bootstrap lower CI > 0을 공동 요구",
  "sample_floors": {
    "joined_rows": 863446,
    "labeled_rows": 862932
  },
  "multiplicity_family": "G005-C1-TIME-SHIFT 단일 family; fixed pairs (16,37) and (16,38), conjunctive PASS with no pair rescue",
  "kill_rule": "Identified measurement 후 두 fixed pair 중 하나라도 observed pooled I <= its placebo 95th percentile 이거나 어느 pair-year의 day-block 95% CI lower bound <= 0이면 전체 C1 family KILL; provenance/schema/join/cell floor/nonfinite/insufficient day support 실패만 UNDETERMINED",
  "ledger_path": "docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl",
  "authority_paths": {
    "seal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1/evidence/seals",
    "promotions_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1/evidence/promotions",
    "catalog_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1/evidence/catalog",
    "journal_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1/evidence/journal",
    "backup_dir": "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1/evidence/backups",
    "target_db": "scripts/g005_c1_time_shift.py"
  },
  "dependency_roots": [
    "scripts/g005_c1_time_shift.py"
  ],
  "dynamic_python_dependencies": [],
  "non_python_dependencies": [
    "docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md",
    "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_input.json.gz"
  ]
}
```

이 SEALED 계약은 outcome-independent design만 고정한다. 측정값, 해석, catalog, promotion, 전략 적용은 별도 evidence chain 없이는 이 문서에서 승인되지 않는다.
