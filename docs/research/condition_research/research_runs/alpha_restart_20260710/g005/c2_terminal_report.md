# G005-C2 활성화 순서 terminal nonidentification 보고

## 최종 판정

- hypothesis_id: `G005-C2-ACTIVATION-ORDER`
- repository HEAD: `25975531ab966eb113d79bc130b9b4493001b1f6`
- terminal_decision: `UNDETERMINED`
- terminal_reason: `dependency/schema nonidentification`
- H37 identified: `false`
- H38 identified: `false`
- `KILL`/`PASS`: 평가하지 않음

HEAD `25975531`의 committed preregistration은 authoritative source이며, 이 보고서는 그 계약을 약화하거나 재해석하지 않는다. G005-C2는 통계적 `KILL`이 아니라, 필수 activation trace 의존성과 schema가 식별되지 않아 terminal `UNDETERMINED / nonidentified`로 닫힌다.

## 현재 committed source 바인딩

| source | path | sha256 | size_bytes | notes |
|---|---|---:|---:|---|
| prereg | `docs/research/condition_research/plans/2026-07-16_g005_c2_activation_order_preregistration.md` | `084928f444d1f7b729fea648c5ba46f2d7f1696d2450c469b895c3e65991fa60` | `12220` | G005-C2 authoritative sealed contract |
| agenda | `docs/research/condition_research/2026-07-14_alpha_lab_full_audit_and_research_agenda.md` | `3aeebffb511bf6f9a1114602ec35d05edb3917bf2346c64aba48ebc9ee08e14b` | `21373` | C2 Activation Order agenda source |
| D1 bits sentinel | `docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet` | `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56` | `6783855` | rows `863446`; schema `code/day/off/t0 + bit_1..bit_39` |
| static dependency guard | `scripts/g005_c2_nonidentification_guard.py` | `a0273c212922fc93317fb5cdb5b70074ac1c526b8800913a265e71f95633c653` | `573` | authority `static_nonexecution_dependency_sentinel`; declarations only, no invocation |

이 바인딩 갱신은 metadata-only refresh이며, C2 rerun, 신규 experiment, target invocation 또는 materialization이 아니다.

## 비식별 근거

사전등록의 identified design record가 요구한 필수 입력 중 다음이 현재 committed sources에 없다.

- clause16의 exact first activation timestamp
- clause37의 exact first activation timestamp
- clause38의 exact first activation timestamp
- outcome
- exact pre-existing activation trace authority

Safe sentinel인 D1 bits parquet는 `code`, `day`, `off`, `t0`, `bit_1`..`bit_39` snapshot만 가진다. 이는 transition timestamp, activation order, outcome을 포함하지 않으므로 `16->37`, `37->16`, `16->38`, `38->16` 순서를 식별할 수 없다.

따라서 snapshot/flat final bit, `off`, D1 pairwise interaction, C1 tie logic, 또는 final 39-bit snapshot proxy로 activation order를 대체하는 것은 금지된다. 이러한 proxy 금지는 terminal dependency/schema nonidentification을 통계적 `KILL`로 바꾸지 않는다.

## sibling별 상태

| sibling | comparison | identified | evaluated |
|---|---|---:|---|
| H37 | `16->37 minus 37->16` | `false` | `KILL`/`PASS` 미평가 |
| H38 | `16->38 minus 38->16` | `false` | `KILL`/`PASS` 미평가 |

H37/H38 모두 estimand가 식별되지 않았다. Matched-set denominator, annual estimate, pooled CI, sign agreement, bootstrap replicate는 산출하지 않으며 outcome claim도 만들지 않는다.

## side-effect zero counters

| counter | value |
|---|---:|
| invocation | `0` |
| materialization | `0` |
| receipt | `0` |
| claim | `0` |
| target | `0` |
| outcome | `0` |
| n_trials | `0` |
| engine | `0` |
| db_write | `0` |
| registration | `0` |
| promotion | `0` |

Target invocation, materialization, receipt, claim, n_trials row, engine run, DB write, strategy registration, promotion은 모두 없다.

## no-future-attachment 경계

이 hypothesis에는 나중에 어떤 trace도 attach할 수 없다. 향후 activation-order 연구는 G005 밖의 새로운 hypothesis와 새로운 preregistration을 요구한다. G005-C2 안에서는 retry, rerun, rescue, 2024+ 확장, 신규 trace 생성, trace replay, engine 실행, DB write, registration, promotion을 수행하지 않는다.
