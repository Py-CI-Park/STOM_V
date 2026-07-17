# G005-X1 terminal PASS 실행 증거 보고

## 정본과 범위

정본 결과는 `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/run/log.txt`의 한 줄 JSON이다. 이 보고서와 `x1_execution_evidence.json`은 그 로그와 `status.json`에서 파생한 요약이며 정본을 대체하지 않는다.

G005-X1의 라벨은 **descriptive / noncausal / nonpromotable**이다. PASS는 exit-cause 구성의 기술적 설명 규칙 통과만 뜻하며, 인과효과 주장, 반사실 exit 채택, 전략 후보, 등록, promotion 제안을 만들지 않는다.

## 최종 판정

- hypothesis_id: `G005-X1-EXIT-COMPETING-RISK`
- repository HEAD: `25975531ab966eb113d79bc130b9b4493001b1f6`
- receipt_id: `618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2` (`618f...bbc2`)
- decision: `PASS`
- runlab state: `exited`
- exit_code: `0`
- undefined reasons: 없음 (`[]`)
- kill reasons: 없음 (`[]`)
- engine/DB/registration/promotion/retry/rescue: 모두 `0`

## seal / receipt / claim / input / log / status 바인딩

| artifact | path | sha256 | size_bytes |
|---|---|---:|---:|
| seal_manifest | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/evidence/seals/5288392dff3969549a5dc33d7aa6c159a043aab3e7f35c613592b164d20dfe3c.seal.json` | `7662e99882f7938ce899ea29184dea76cfc09ec587b3f8538fc9d72237afb2de` | `1512` |
| receipt | `receipts/618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2.json` | `d511fb13363e7e918765954c321cdb8ff2a090314ed23f280d20b9bc1c249509` | `3532` |
| claim | `claims/618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2.json` | `42a0864453d4b5357c4cc6e0a146ec11ede8e9858143190b263825466338ca5f` | `571` |
| input | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json` | `d60a0ba7d02437d7fce625280f2b890d9667ea3785956e236084194a2aed0790` | `473456` |
| run_log | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/run/log.txt` | `de7b2fe04be4fd0ae406f7bcb79e3a3057fc2cf9f6c48713d2af5697fb2cae6e` | `3580` |
| run_status | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1/run/status.json` | `20060f061fbf9503435caaf12e6ac6c0e35d0a752d1c422058ec669842c48b2e` | `474` |

## 한 번의 승인된 receipt / claim / runlab 실행

Receipt `618f...bbc2`는 `2026-07-16T17:04:01+00:00`에 HEAD `25975531ab966eb113d79bc130b9b4493001b1f6`에 대해 발급되었고 status는 `PASS`였다. Claim은 `2026-07-16T17:04:02+00:00`에 `g005-x1-sealed-runlab` consumer로 소비되었다.

Runlab status는 `started_utc=2026-07-16T17:05:12+00:00`, `ended_utc=2026-07-16T17:07:55+00:00`, `state=exited`, `exit_code=0`, `target_args=[]`를 기록한다. target은 sealed copy인 `.../g005/x1/run/sealed-stage-5_9s62mi/scripts/g005_x1_competing_risk.py`였다.

## 정본 log에서 복사한 PASS 지표

| metric | value |
|---|---:|
| raw_group_mean RR8 | `0.6783137254901961` |
| raw_group_mean GPTAUTH_G8 | `-0.05538633818589026` |
| raw_contrast | `0.7337000636760863` |
| standardized_contrast | `-0.05715673621331205` |
| residual_ratio | `0.07790204613985911` |
| annual_raw_contrast 2022 | `0.7027777777777778` |
| annual_raw_contrast 2023 | `0.7352685300302375` |
| annual signs | `+/+` |
| annual_sign_conflict | `false` |

Bootstrap CI도 정본 log에서 그대로 복사했다.

| statistic | ci_low | ci_high |
|---|---:|---:|
| raw_contrast | `0.38820495748256595` | `1.0944880054895207` |
| standardized_contrast | `-0.29575337442010086` | `0.1925503562417116` |
| residual_ratio | `0.005367655904344311` | `0.683941685075269` |

Decision diagnostics의 `pass_rule`은 `pooled residual_ratio < 0.8 and 2022/2023 annual raw signs agree nonzero`이다. `undefined_reasons`, `undetermined_reasons`, `kill_reasons`는 모두 빈 배열이다.

## side-effect zero counters

| counter | value |
|---|---:|
| engine_calls | `0` |
| db_writes | `0` |
| strategy_registrations | `0` |
| promotions | `0` |
| retries | `0` |
| rescue_runs | `0` |
| ledger_append | `0` |

따라서 이 실행은 engine 실행, DB write, strategy registration, promotion, retry, rescue를 수행하지 않았다.

## v2 ledger attempt rejection

v2 ledger append 시도는 다음 정확한 메시지로 거부되었다.

`candidate_set may be empty only for a negative_or_kill measurement`

Ledger row는 append되지 않았다. 이유는 이 결과가 `PASS`인 descriptive 측정이므로 빈 `candidate_set`을 사실처럼 append할 수 없고, 이를 우회하려고 전략 후보를 조작하거나 `negative_or_kill=true`로 설정하는 것은 금지되기 때문이다. 따라서 fake candidate, fake ledger row, promotion proposal은 없다.

## 증거와 추론의 분리

증거는 receipt/claim/runlab status/log 및 위 artifact hash/size 바인딩이다. 추론은 그 증거로부터 “사전등록된 descriptive competing-risk 규칙은 PASS였지만 noncausal/nonpromotable이며 ledger row와 전략 후보를 만들 수 없다”는 해석에 한정한다.
