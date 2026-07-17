# G006-C3 Temporal Motif 사전등록 및 Phase 0 종결 기록 (2026-07-16)

> 지위: **SEALED / candidate-selection outcome-independent / Phase 0 terminal**
>
> 이 문서는 `G006-C3-TEMPORAL-MOTIF`와 조건부 `G006-C4`의 사전등록 경계만 봉인한다. 현재 감사 가능한 권한 안에는 formal true-DNF와 stateful exact activation timestamp authority가 없으므로, 이 branch는 C3 motif mining 또는 C4 outcome/metric 산출 전에 **UNDETERMINED / DNF_UNIDENTIFIED**로 닫힌다. 조건부 C4는 열리거나 실행되지 않았고, C4 outcome/metric은 생성되지 않으며, 감사 산출물은 `CLOSED` status metadata뿐이다. 아래 통계 파라미터는 identified path가 존재했을 때의 dormant preregistration 값일 뿐이며 실행 결과가 아니다.

## 1. 증거와 추론의 분리

### 1.1 관측 증거

- 감사 worktree: `C:/System_Trading/STOM/STOM_V.wt-alpha-audit`.
- D1 source parquet와 clause dictionary의 byte 지문은 아래 §2에 묶인 값과 일치한다.
- D1 source parquet의 스키마는 `code/day/off/t0 + bit_1..bit_39`뿐이다. 이 스키마에는 true-DNF branch, per-atom state transition, first activation timestamp, transition order, L3, outcome이 없다.
- Planner 332는 기존 D1 ablation summary/report를 prior provenance context로 확인했으므로, 이 문서는 generic planning-session outcome-read zero counter를 주장하지 않는다.
- 현재 방어 가능한 scope는 C3 candidate generation에 outcome/L3/h300 field를 사용하지 않았음(실제로 candidate generation 없음), C4 outcome/metric read·computation이 없었음, outcome-dependent motif selection이 없었음이다.

### 1.2 이 문서의 추론

- static snapshot bit matrix와 clause dictionary만으로는 temporal motif의 stateful activation sequence를 식별할 수 없다.
- `off`와 `t0`는 row identity/time index fact일 뿐이며, atom/절의 first activation timestamp가 아니다.
- 따라서 Phase 0 authority/schema gate가 실패한다. 이 실패는 통계적 KILL, C3 효과 부재, C4 효과 부재, 또는 PASS 실패가 아니라 **식별 불능(UNDETERMINED / DNF_UNIDENTIFIED)**이다.

## 2. 고정 원천 바인딩

### 2.1 D1 source parquet

| 항목 | 고정값 |
|---|---|
| 상대 경로 | `docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet` |
| 절대 경로 | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet` |
| SHA-256 | `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56` |
| 크기(bytes) | `6,783,855` |
| row count | `863,446` |
| row groups | `1` |
| ordered schema | `code`, `day`, `off`, `t0`, `bit_1`..`bit_39` |
| schema type groups | `code: large_string`; `day: int32`; `off: int16`; `t0: int64`; `bit_1`..`bit_39: bool` |
| null fact | 전체 43개 컬럼의 measured null count 합계 `0` |
| bit domain fact | `bit_1`..`bit_39`는 bool domain; `bit_22`는 관측상 `[true]` only, 나머지 bit는 `[false,true]`; 모든 bit null count `0` |

### 2.2 D1 day/off/t0 identity facts

| 필드 | 관측 fact | C3/C4 해석 제한 |
|---|---|---|
| `day` | null `0`; `YYYYMMDD` int; min `20220323`; max `20231228`; unique days `437`; 모든 row가 `20220323..20231231` 범위 | 발견창 identity fact일 뿐이며 motif 선택이나 outcome selection 근거가 아니다. |
| `off` | null `0`; int; non-negative; min `11`; max `1799`; unique values `1789` | **activation timestamp가 아니다.** `off`를 atom/절 first activation time, order, lag, C4 timestamp로 대체하는 것은 금지한다. |
| `t0` | null `0`; 14자리 int count `863,446`; min `20220323090017`; max `20231228092957`; 모든 row에서 첫 8자리가 `day`와 일치 | row timestamp/identity fact일 뿐이다. atom별 transition timestamp나 true-DNF branch timestamp가 아니다. |
| `code` | null `0`; unique codes `1,946` | row identity fact일 뿐이며 candidate selection에 L3/outcome을 결합하지 않는다. |

### 2.3 Clause dictionary

| 항목 | 고정값 |
|---|---|
| 상대 경로 | `alpha_lab/clause_lab/clauses.py` |
| 절대 경로 | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/alpha_lab/clause_lab/clauses.py` |
| SHA-256 | `def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4` |
| 크기(bytes) | `21,405` |
| 역할 | RR8_12 계보의 39 unique clause dictionary, `CLAUSE_SPECS`, `RAW_EXPR`, `PURE_DUPLICATE_PAIRS=((15,39),)` 정의 |

이 dictionary는 static predicate 정의 권한이다. 이것만으로 row별 stateful true-DNF activation history 또는 exact first activation timestamp authority가 생기지 않는다.

## 3. Phase 0: authoritative true-DNF/stateful timestamp gate

Phase 0은 C3 motif mining, C3 support counting, C3 p-value 계산, C4 gate, C4 outcome read보다 반드시 먼저 끝나야 한다.

Phase 0 PASS에 필요한 최소 권한은 다음 모두다.

1. D1 row key `(code, day, off, t0)`에 1:1로 묶이는 pre-outcome artifact.
2. clause dictionary SHA-256 `def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4`와 동일한 atom numbering 및 polarity.
3. atom universe `1..39`에서 `22`와 `39`를 제외한 각 atom의 signed state transition을 row별로 제공하는 formal true-DNF 또는 그와 동치인 stateful activation authority.
4. 각 signed flip의 exact activation timestamp. timestamp는 `YYYYMMDDHHMMSS` 14자리 Asia/Seoul wall-clock second여야 하며, 첫 8자리는 해당 row의 `day`와 같아야 한다.
5. timestamp order, tie, missing transition, duplicate transition을 outcome 관측 전에 fail-closed로 판정할 schema.
6. C3 candidate generation에 L3, outcome, 2024+ 데이터, engine replay, DB reconstruction, strategy registration 결과가 섞이지 않았음을 증명하는 source manifest.

현재 묶인 D1 parquet와 clause dictionary는 위 3--5를 제공하지 않는다. 따라서 현재 branch의 authoritative Phase 0 판정은 **UNDETERMINED / DNF_UNIDENTIFIED**이며, 이후 단계는 실행되지 않는다.

## 4. Dormant identified-path C3 설계값

아래 값은 Phase 0이 PASS했을 때만 사용할 수 있는 봉인 파라미터다. 현재 terminal branch에서는 어떤 C3 motif도 채굴하지 않았고, 어떤 C3 count/p-value/lift도 계산하지 않았다.

| 항목 | 봉인값 |
|---|---|
| hypothesis id | `G006-C3-TEMPORAL-MOTIF` |
| discovery window | `2022-03-23..2023-12-31` only |
| snapshots | `K = 2` state snapshots, authority artifact에서만 읽음 |
| atom universe | `1..39 excluding 22 and 39` |
| signs | signed flips only: `+atom`과 `-atom`을 구분; unsigned/flat coarsening 금지 |
| support floor | pooled support `>= 2,000`; annual support `>= 400` per year |
| annual day floor | annual supporting days `>= 20` per year |
| support cap | support `<= 20%` |
| similarity/dedup | signed Jaccard only |
| statistical test family | Fisher/Simes threshold `0.01`, BH-FDR `0.10` |
| lift floors | pooled lift `>= 1.5`; annual lift `>= 1.25` |
| reconstruction | formal reconstruction required before PASS claim |
| downstream gate | conditional C4 exact timestamp gate required before any C4 metric |

Dormant identified path의 순서는 고정한다.

1. Phase 0 authority/schema gate PASS.
2. outcome-blind C3 motif universe generation from formal true-DNF/stateful activation authority only.
3. support floors, annual day floor, support cap, signed-Jaccard dedup 적용.
4. Fisher/Simes `0.01` 및 BH `0.10` 적용.
5. pooled/annual lift floors 적용.
6. formal reconstruction으로 surviving motif를 원 authority의 row-level signed activation sequence에 다시 대응.
7. formal survivor가 있을 때만 conditional C4 exact timestamp gate로 이동.

현재는 1번에서 종료되므로 2--7은 dormant preregistration이며 실행 결과가 아니다.

## 5. Conditional C4 gate

조건부 `G006-C4`는 C3 formal survivor가 있을 때만 열리는 downstream branch다. C4는 C3 survivor의 exact activation timestamp가 별도 C4 gate에서 다시 확인된 뒤에만 metric/outcome을 읽을 수 있다.

- C4 gate path: `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/c4_gate_status.json`.
- gate requirement: survivor motif의 모든 signed atom/transition timestamp가 exact 14-digit same-day `YYYYMMDDHHMMSS`로 재확인되어야 한다.
- flat final 39-bit snapshot, D1 pairwise interaction, C1/C2 result, `off`, `t0`, row order, nearest-neighbor, fill, interpolation, timezone conversion은 C4 timestamp authority가 아니다.
- 현재는 C3 formal survivor가 없고 Phase 0이 DNF_UNIDENTIFIED이므로 C4는 열거나 실행하지 않는다. C4 outcome/metric read·computation 및 metric generation은 없으며, 감사용으로 emit되는 것은 `CLOSED` status metadata JSON뿐이다.

## 6. Decision ladder

판정 우선순위는 아래 순서로 고정한다.

1. **authority/schema insufficiency → `UNDETERMINED / DNF_UNIDENTIFIED`**  
   formal true-DNF/stateful exact activation timestamp authority가 없거나, schema가 atom id/sign/timestamp/order를 outcome-blind로 보증하지 못하면 여기서 terminal stop이다. 현재 G006 branch가 이 경우다.
2. **identified statistical failure → `KILL`**  
   Phase 0이 PASS하고 C3/C4가 식별된 뒤에만 평가한다. support floor, annual day floor, support cap, Fisher/Simes, BH, lift floors, formal reconstruction, C4 exact timestamp gate 중 하나라도 실패하면 KILL이다.
3. **formal survivor → `PASS`**  
   authority/schema, support, multiplicity, lift, formal reconstruction, C4 exact timestamp gate를 모두 통과한 survivor만 PASS다. PASS는 strategy registration, promotion, DB write, live proof를 의미하지 않는다.

`UNDETERMINED / DNF_UNIDENTIFIED`는 KILL이나 PASS보다 먼저 적용한다. 식별되지 않은 branch에서 statistical failure나 success를 주장하지 않는다.

## 7. 명시적 금지

다음 행위는 이 사전등록과 현재 terminal branch에서 모두 금지한다.

- flat-39 final bit vector를 temporal motif 또는 true-DNF 대체물로 쓰기.
- `off`를 activation timestamp, first activation order, lag, C4 timestamp로 쓰기.
- `t0` row timestamp를 atom/절 transition timestamp로 쓰기.
- 2024년 이후 데이터, live 데이터, later replay, future trace attachment 사용.
- L3 또는 outcome으로 C3 candidate를 선택, 필터, 구조화, rescue하기.
- D1 pairwise, G005 C1 tie/time-shift, G005 C2 activation-order logic으로 G006 C3/C4를 proxy하기.
- C3 motif mining count, p-value, lift, survivor, C4 metric을 fabricated 또는 descriptive placeholder로 만들기.
- engine 실행, DB write, strategy registration, promotion, retry, rerun, variant run, rescue run.
- `.gjc` 또는 protected runtime/DB artifact를 touching하여 권한을 만든 것처럼 기록하기.

## 8. Terminal evidence/report/C4 gate path names

이 사전등록은 아래 path를 이름으로만 고정한다. 이 파일 자체는 그 path들을 생성하거나 수정하지 않으며, ledger append나 DB write authority도 아니다.

| 용도 | exact path |
|---|---|
| G006 C3 identifiability evidence | `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_c3_identifiability_evidence.json` |
| G006 C3 terminal report | `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_c3_terminal_report.md` |
| conditional C4 exact timestamp gate status | `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/c4_gate_status.json` |

## 9. prereg contract

```json prereg-contract-v2
{
  "schema_version": 2,
  "hypothesis_id": "G006-C3-TEMPORAL-MOTIF",
  "preregistration_status": "SEALED",
  "terminal_decision": "UNDETERMINED",
  "status": "DNF_UNIDENTIFIED",
  "candidate_selection_outcome_independent": true,
  "candidate_selection_outcome_reads": 0,
  "c4_status": "CLOSED",
  "c4_opened": false,
  "c4_executed": false,
  "c4_status_metadata_emitted": true,
  "c4_status_metadata_scope": "CLOSED status metadata only; not C4 execution or metric generation.",
  "c4_outcome_reads": 0,
  "c4_outcome_computations": 0,
  "c4_metrics_generated": false,
  "outcome_scope_note": "Planner inspected existing D1 ablation summary/report only as provenance context; no outcome/L3/h300 field was used for C3 candidate generation (none occurred), no C4 outcome/metric read or computation occurred, and no outcome-dependent motif selection occurred.",
  "current_terminal_branch": "Phase 0 only",
  "terminal_reason": "Formal true-DNF/stateful exact activation timestamp authority is absent before C3 candidate generation and C4 outcome/metric work.",
  "discovery_window": {
    "start": "2022-03-23",
    "end": "2023-12-31",
    "forbid_2024_plus": true
  },
  "source_bindings": {
    "d1_bits": {
      "path": "docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet",
      "sha256": "4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56",
      "size_bytes": 6783855,
      "rows": 863446,
      "schema": "ordered: code large_string, day int32, off int16, t0 int64, bit_1..bit_39 bool",
      "day_fact": "min 20220323; max 20231228; unique 437; nulls 0; YYYYMMDD ints",
      "off_fact": "int16; nonnegative; min 11; max 1799; unique 1789; nulls 0; not an activation timestamp",
      "t0_fact": "int64; all 863446 values are 14-digit; min 20220323090017; max 20231228092957; first 8 digits equal day for every row; not an atom transition timestamp",
      "null_fact": "total null count across all 43 columns is 0"
    },
    "clause_dictionary": {
      "path": "alpha_lab/clause_lab/clauses.py",
      "sha256": "def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4",
      "size_bytes": 21405
    }
  },
  "phase0_gate": {
    "must_precede": ["C3 motif mining", "C3 support counting", "C3 statistical testing", "C4 gate", "C4 metric/outcome read"],
    "required_authority": "pre-outcome formal true-DNF/stateful row-level signed atom activation sequence with exact same-day YYYYMMDDHHMMSS timestamps",
    "current_authority_present": false,
    "terminal_decision": "UNDETERMINED",
    "status": "DNF_UNIDENTIFIED"
  },
  "dormant_identified_parameters": {
    "executed": false,
    "snapshots_k": 2,
    "atoms": "1..39 excluding 22 and 39",
    "signed_flips": true,
    "pooled_support_floor": 2000,
    "annual_support_floor": 400,
    "annual_days_floor": 20,
    "support_cap_fraction": 0.20,
    "similarity": "signed Jaccard",
    "tests": "Fisher/Simes 0.01/BH 0.10",
    "lift_floors": {
      "pooled": 1.5,
      "annual": 1.25
    },
    "formal_reconstruction_required": true,
    "conditional_c4_exact_timestamp_gate_required": true
  },
  "decision_ladder": [
    "authority/schema insufficiency -> terminal_decision UNDETERMINED; status DNF_UNIDENTIFIED",
    "identified statistical failure -> KILL",
    "formal survivor -> PASS"
  ],
  "authority_paths": {
    "terminal_evidence": "docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_c3_identifiability_evidence.json",
    "terminal_report": "docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_c3_terminal_report.md",
    "c4_gate_status": "docs/research/condition_research/research_runs/alpha_restart_20260710/g006/c4_gate_status.json"
  },
  "prohibitions": [
    "flat-39 proxy",
    "off-as-timestamp",
    "t0-as-activation-timestamp",
    "2024+",
    "L3/outcome candidate selection",
    "engine run",
    "DB write",
    "registration",
    "promotion",
    "retry/rerun/rescue"
  ]
}
```

이 SEALED 문서의 핵심 효력은 Phase 0 precedence와 terminal nonidentification이다. Dormant statistical parameters are preregistered only; they are not executed C3/C4 evidence, not a metric table, and not a promotion authority.
