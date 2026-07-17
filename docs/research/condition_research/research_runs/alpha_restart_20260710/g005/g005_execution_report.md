# G005 family-level terminal 실행 감사 요약

이 문서는 G005 one-shot family의 최종 감사 요약이다. 현재 durable evidence만 합성하며, promotion, engine execution, engine request, strategy registration, retry, rescue를 승인하지 않는다.

## 범위와 실행 HEAD

| 항목 | 값 |
|---|---|
| family | `G005` |
| research run | `alpha_restart_20260710` |
| bound HEAD | `25975531ab966eb113d79bc130b9b4493001b1f6` |
| family terminal state | mixed terminal statuses |
| strategy candidate | 없음 |
| engine request/execution | 없음 |
| registration/promotion | 없음 |
| retry/rescue | 없음 |

## 증거 바인딩

| branch | artifact | path | status |
|---|---|---|---|
| C1 | terminal report | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_terminal_report.md` | durable summary |
| C1 | terminal evidence | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_terminal_evidence.json` | durable evidence |
| C1 | preregistration | `docs/research/condition_research/plans/2026-07-16_g005_c1_time_shift_preregistration.md` | sha256 `af4b8258cebc3442c7cb3749971af7bbf56f0d27fe3f48f8440695eaee1c79d8`, size `11423` |
| C1 | parent-captured transcript | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_builder_attempt_bg_6.txt` | sha256 `8f2ad9f760f5efad49bf14f9cc692dd5c473762176c7a5631795cf939e123d0b`, size `1740`, capture_kind `parent_captured_managed_job_transcript`, source_job `bg_6`, exit_code `1`, not original builder-written log, exact execution timestamp unavailable/not asserted |
| X1 | terminal report | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_terminal_report.md` | durable summary |
| X1 | execution evidence | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_execution_evidence.json` | durable evidence |
| X1 | seal manifest | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/seals/5288392dff3969549a5dc33d7aa6c159a043aab3e7f35c613592b164d20dfe3c.seal.json` | SEALED |
| X1 | receipt | `receipts/618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2.json` | PASS receipt |
| X1 | claim | `claims/618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2.json` | consumed by `g005-x1-sealed-runlab` |
| X1 | run log | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/run/log.txt` | canonical one-line result |
| X1 | run status | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/run/status.json` | `exited`, exit code `0` |
| C2 | terminal report | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2_terminal_report.md` | durable summary |
| C2 | nonidentification evidence | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c2_nonidentification_evidence.json` | durable evidence |
| C2 | preregistration | `docs/research/condition_research/plans/2026-07-16_g005_c2_activation_order_preregistration.md` | sha256 `084928f444d1f7b729fea648c5ba46f2d7f1696d2450c469b895c3e65991fa60` |
| C2 | static dependency guard | `scripts/g005_c2_nonidentification_guard.py` | sha256 `a0273c212922fc93317fb5cdb5b70074ac1c526b8800913a265e71f95633c653`, declarations only |
| ledger | n_trials ledger | `docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl` | G005/X1 receipt/series row 없음 |

## branch별 관측 증거

### C1 — `G005-C1-TIME-SHIFT`

증거:

- C1 preregistration binding은 `docs/research/condition_research/plans/2026-07-16_g005_c1_time_shift_preregistration.md`, sha256 `af4b8258cebc3442c7cb3749971af7bbf56f0d27fe3f48f8440695eaee1c79d8`, size `11423`이다.
- C1 transcript binding은 parent-captured managed-job transcript `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_builder_attempt_bg_6.txt`, sha256 `8f2ad9f760f5efad49bf14f9cc692dd5c473762176c7a5631795cf939e123d0b`, size `1740`, capture_kind `parent_captured_managed_job_transcript`, source_job `bg_6`, exit_code `1`이다. 이 transcript는 original builder-written log가 아니며 정확한 실행 timestamp는 unavailable/not asserted다.
- HEAD `25975531ab966eb113d79bc130b9b4493001b1f6`에서 단일 builder/materializer 시도 `python scripts/build_g005_c1_input.py`가 parent-captured transcript 기준 exit code `1`/nonzero로 종료했다.
- 실패는 `c1_input.json` 생성 전 발생했다. `c1_input.json`은 시도 전/후 모두 absent로 기록되어 있다.
- traceback root는 `ValueError: t0 must be a nonempty string`이며, `_key_columns(l3)`가 `_identity_string`을 호출한 지점에서 발생했다.
- 관측된 L3 key schema는 `t0=int64`, `code=large_string`, `day=int32`, `off=int16`이다.
- `downstream_actions_observed`에서 target, finalizer, receipt, claim, runlab, engine, DB write, registration, promotion, retry, rescue, ledger append 값은 모두 `false`; `false`는 관측되지 않았다는 뜻이며 downstream C1 execution은 없었다.

판정:

- terminal decision: `UNDETERMINED`
- terminal status: `INPUT_SCHEMA_MISMATCH`
- `KILL`/`PASS`: 평가하지 않음
- retry/target/downstream C1 execution: 없음

### X1 — `G005-X1-EXIT-COMPETING-RISK`

증거:

- sole receipt ID는 `618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2` (`618f...bbc2`)이다.
- receipt는 `2026-07-16T17:04:01+00:00`에 HEAD `25975531ab966eb113d79bc130b9b4493001b1f6`에 대해 `PASS`로 발급되었다.
- claim은 `2026-07-16T17:04:02+00:00`에 `g005-x1-sealed-runlab` consumer로 소비되었다.
- runlab status는 `started_utc=2026-07-16T17:05:12+00:00`, `ended_utc=2026-07-16T17:07:55+00:00`, `state=exited`, `exit_code=0`, `target_args=[]`를 기록한다.
- canonical run log의 decision은 `PASS`다.
- residual ratio는 `0.07790204613985911`이다.
- annual raw contrasts는 `2022=0.7027777777777778`, `2023=0.7352685300302375`이고 annual signs는 `+/+`이다.
- `undefined_reasons`, `undetermined_reasons`, `kill_reasons`는 모두 빈 배열이다.
- side-effect counters는 engine calls, DB writes, strategy registrations, promotions, retries, rescue runs 모두 `0`이다.

판정:

- terminal decision: `PASS`
- claim type: descriptive / noncausal / nonpromotable
- 이 PASS는 exit-cause 구성의 기술적 설명 규칙 통과만 의미한다.
- 인과효과, 반사실 exit 채택, 전략 후보, registration, promotion, engine execution을 만들지 않는다.

### C2 — `G005-C2-ACTIVATION-ORDER`

증거:

- HEAD `25975531ab966eb113d79bc130b9b4493001b1f6`의 committed preregistration과 static dependency guard가 현재 binding이다.
- preregistration path는 `docs/research/condition_research/plans/2026-07-16_g005_c2_activation_order_preregistration.md`이고 sha256은 `084928f444d1f7b729fea648c5ba46f2d7f1696d2450c469b895c3e65991fa60`이다.
- static dependency guard path는 `scripts/g005_c2_nonidentification_guard.py`이고 sha256은 `a0273c212922fc93317fb5cdb5b70074ac1c526b8800913a265e71f95633c653`이다.
- static guard는 declarations only이며 invocation은 없다.
- committed sources에는 clause16/37/38의 exact first activation timestamp, outcome, exact pre-existing activation trace authority가 없다.
- D1 bits sentinel은 `code/day/off/t0 + bit_1..bit_39` snapshot만 포함하며 transition timestamp, activation order, outcome, trace authority를 포함하지 않는다.
- invocation, materialization, receipt, claim, target, outcome, n_trials row, engine, DB write, registration, promotion은 모두 `0`이다.

판정:

- terminal decision: `UNDETERMINED`
- terminal status: `nonidentified`
- reason: dependency/schema nonidentification
- H37/H38 모두 `KILL`/`PASS` 미평가
- G005-C2 안에서 future trace attachment, retry/rerun/rescue, 2024+ 확장, 신규 trace 생성/replay는 허용되지 않는다.

## n_trials ledger 설명

- C1은 builder/materializer가 input artifact 생성 전에 실패했으므로 gate-bound measurement가 없다. receipt/claim/runlab/finalizer/target이 없고 n_trials row 대상이 아니다.
- C2는 dependency/schema nonidentification이며 target invocation, materialization, receipt, claim, outcome이 없다. gate-bound measurement가 없고 n_trials row 대상이 아니다.
- X1은 sealed receipt/claim/runlab PASS가 있었지만 descriptive / noncausal / nonpromotable 측정이다. v2 append validation은 ledger mutation 전에 `candidate_set may be empty only for a negative_or_kill measurement` 메시지로 fail-closed 거부되었다.
- X1은 positive descriptive PASS이므로 `negative_or_kill=true`로 속이거나, fake buy/sell hash 및 fake promotable candidate를 만들어 빈 `candidate_set`을 우회할 수 없다.
- ledger 검색 결과 `618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2`, `G005-X1`, `g005-x1`, `alpha_restart_20260710-g005-x1`, `G005/g005` row는 관측되지 않았다.
- 따라서 fake ledger row, fake candidate, promotion proposal은 없다.

## 증거와 추론의 분리

증거:

- C1 terminal report/evidence는 C1 preregistration path/hash/size와 parent-captured transcript path/hash/size/provenance를 바인딩하고, 단일 builder attempt nonzero, `INPUT_SCHEMA_MISMATCH`, artifact absent, no retry/target/downstream C1 execution을 기록한다.
- X1 receipt/claim/seal/run log/status는 sole runlab execution의 exit code `0`, `PASS`, residual ratio `0.07790204613985911`, annual signs `+/+`, side-effect zero counters를 기록한다.
- C2 terminal report/evidence는 current preregistration/static guard binding, no invocation, dependency/schema nonidentification을 기록한다.
- n_trials ledger search는 G005/X1 receipt ID/series row absence를 관측했다.

추론:

- G005 family는 mixed terminal statuses로 닫힌다: C1은 `UNDETERMINED / INPUT_SCHEMA_MISMATCH`, X1은 descriptive `PASS`, C2는 `UNDETERMINED / nonidentified`이다.
- “모든 hypothesis가 통과했다” 또는 “모든 hypothesis가 실패했다”는 결론은 증거와 맞지 않는다.
- 현재 durable evidence에서 strategy candidate, engine request, engine execution, registration, promotion, retry, rescue, fake ledger row를 도출할 수 없다.
