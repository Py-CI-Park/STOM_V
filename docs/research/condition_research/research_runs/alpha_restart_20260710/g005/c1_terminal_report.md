# G005-C1 terminal materializer evidence 보고

## 최종 판정

- hypothesis_id: `G005-C1-TIME-SHIFT`
- repository HEAD at attempt: `25975531ab966eb113d79bc130b9b4493001b1f6`
- terminal_decision: `UNDETERMINED`
- terminal_status: `INPUT_SCHEMA_MISMATCH`
- `KILL`/`PASS`: 평가하지 않음
- outcome/statistical evidence: 없음

이 보고서는 단일 허용 builder/materializer 시도의 terminal evidence만 보존한다. 시도 증거는 parent-captured managed job transcript `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_builder_attempt_bg_6.txt` (sha256 `8f2ad9f760f5efad49bf14f9cc692dd5c473762176c7a5631795cf939e123d0b`, size `1740`, source job `bg_6`, exit code `1`)에 바인딩한다. 이 transcript는 after-the-fact parent capture이며 builder가 직접 작성한 original log가 아니고, 정확한 실행 timestamp는 unavailable/not asserted다. Builder 실패는 C1 무결성을 `UNDETERMINED`로 남기는 입력 스키마 불일치이며, 부정적인 통계 증거가 아니다.

## 관측된 증거

| 항목 | 관측값 |
|---|---|
| 단일 명령 | `python scripts/build_g005_c1_input.py` |
| 시도 수 | `1` |
| 종료 | nonzero |
| artifact 생성 | 실패 전 중단 |
| traceback root | `ValueError: t0 must be a nonempty string` |
| root 위치 | `_identity_string`, `_key_columns(l3)`에서 호출 |
| C1 preregistration | path `docs/research/condition_research/plans/2026-07-16_g005_c1_time_shift_preregistration.md`; sha256 `af4b8258cebc3442c7cb3749971af7bbf56f0d27fe3f48f8440695eaee1c79d8`; size `11423`; fingerprint unchanged |
| parent-captured transcript | path `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_builder_attempt_bg_6.txt`; sha256 `8f2ad9f760f5efad49bf14f9cc692dd5c473762176c7a5631795cf939e123d0b`; size `1740`; capture_kind `parent_captured_managed_job_transcript`; source_job `bg_6`; exit_code `1`; not an original builder-written log; exact execution timestamp unavailable/not asserted |
| `c1_input.json` before | absent |
| `c1_input.json` after | absent |

현재 L3 key schema 관측값은 다음과 같다.

| column | type |
|---|---|
| `t0` | `int64` |
| `code` | `large_string` |
| `day` | `int32` |
| `off` | `int16` |

## `downstream_actions_observed` (false = not observed)

`false`는 해당 downstream C1 action이 관측되지 않았다는 뜻이며 성공/실패 판정값이 아니다.

| action | observed |
|---|---:|
| target | false |
| finalizer | false |
| receipt | false |
| claim | false |
| runlab | false |
| engine | false |
| DB write | false |
| registration | false |
| promotion | false |
| retry | false |
| rescue | false |
| ledger append | false |

공식 receipt, claim, ledger row, runlab 산출물 및 downstream C1 execution은 생성되거나 관측되지 않았다. 이 보고서와 JSON evidence는 그 산출물을 대체하지 않는다.

## 추론과 경계

`_key_columns(l3)`가 `_identity_string`을 호출한 지점에서 `t0`가 nonempty string identity가 아니라 `int64`로 들어왔기 때문에 builder/materializer가 입력 스키마 불일치로 중단된 것으로 분류한다. 이 중단은 `c1_input.json` 생성 전 발생했으므로 target, finalizer, 통계 측정, receipt/claim 단계로 진행하지 않았다.

따라서 terminal 상태는 `INPUT_SCHEMA_MISMATCH`, terminal decision은 `UNDETERMINED`다. PASS 조건도, 실패 조건도, pooled interaction, placebo 95th percentile, annual day-block bootstrap lower CI도 평가하지 않았다.

## one-shot story 제한

이 story 안에서는 retry, fix, rematerialization, target 실행, rescue를 허용하지 않는다. 이후 값을 붙여 C1 결과로 보정하거나 `KILL`/`PASS`로 재해석하지 않는다.
