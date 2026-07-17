# 2026-07-16 Alpha Lab 최종 연구 종합 보고서 (G007)

> 본 문서는 G007의 최종 연구 종합·합류 준비 산출물이다. 이 보고서는 `agent://357-G007EvidenceMapA`, `agent://358-G007EvidenceMapB`가 동결한 동일 evidence map과 그들이 인용한 durable source를 종합한다. 본 content-generation executor는 테스트·게이트·포매터·엔진·연구 재실행·DB 접근·git 명령·커밋을 실행했다는 주장을 하지 않는다. Primary G007 documentation commit `f10e41d7` now follows the pre-G007-documentation baseline, and this self-referential wording correction will be committed afterward; neither documentation commit is a maintainer integration approval gate.

## 1. 제목, 범위, source manifest

### 1.1 결론 요약

- **프로모션 가능한 STOM 전략 후보는 없다.** 최종 산출물의 성격은 감사·지식 정리·합류 준비이다.
- terminal distinction은 다음처럼 고정한다.
  - `G002`, `G004`, `G005-C1`, `G005-C2`, `G006-C3/C4`: 미해결 또는 비식별 terminal closure이다.
  - `G003`: `FAIL`, 고정 static `O3 OR O4` veto family retire.
  - `G005-X1`: descriptive / noncausal / nonpromotable `PASS`; 전략 후보나 인과·반사실 증거가 아니다.
  - `G008`, `G009`, `G010`: governance/contract/measurement closure 증거이며 운영·DB·engine/live authority가 아니다.
- supersession chain은 **G001→G008**, **G005→G009(contract repair)+G010(final measurement)** 로 보존한다.

### 1.2 source key

| Key | Source | 사용 범위 |
|---|---|---|
| `[M-A]` | `agent://357-G007EvidenceMapA` | G001/G008, G002, G003, G004 evidence map 및 금지 추론 cross-check |
| `[M-B]` | `agent://358-G007EvidenceMapB` | G001~G010 supersession map, G005/G006/G009/G010 final synthesis plan, 15개 section 요구사항 |
| `[B]` | `.gjc/_session-019f6093-0be6-7000-b496-a9b6b2305f30/ultragoal/brief.md` | 원 승인 제약: 기존 DB read-only, 2025~2026/known-2024 selection ban, 보호 DB·실전·등록·엔진 별도 승인 필요 |
| `[G]` | `.gjc/_session-019f6093-0be6-7000-b496-a9b6b2305f30/ultragoal/goals.json` | goal status, supersession, completion receipt, review/test history |
| `[G008-R]` | `docs/research/condition_research/2026-07-14_alpha_lab_evidence_chain_v2_execution.md` | G001/G008 evidence-chain v2 closure, tests, non-claims |
| `[G002-R]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g002/g002_u7_f0_terminal_report.md` | G002 identity terminal failure |
| `[G004-R]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g004/g004_terminal_report.md` | G004 dependency nonidentification and G002 hashes |
| `[G003-R]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g003/g003_veto_report.md` | G003 fixed veto FAIL metrics |
| `[G005-R]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/g005_execution_report.md` | G005 C1/X1/C2 terminal branch report and ledger explanation |
| `[G005-J]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/g005_terminal_summary.json` | G005 structured terminal summary, artifact hashes, zero counters |
| `[G010-J]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g005/g010_terminal_audit_report.json` | G010 QA red-team report and parent-reported 449-test evidence |
| `[G006-R]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_c3_terminal_report.md` | G006 C3/C4 terminal report |
| `[G006-J]` | `docs/research/condition_research/research_runs/alpha_restart_20260710/g006/g006_terminal_audit_report.json` | G006 algorithm-boundary QA report, contract coverage, adversarial cases |

Underlying durable files remain the source of truth. The two `agent://` maps are frozen synthesis inputs, not substitutes for the durable reports and goal receipts.

## 2. Executive briefing table

| Goal / branch | Final status | Terminal decision | Actionability | Candidate status | Risk label | Source |
|---|---|---|---|---|---|---|
| G001 | Superseded by G008 | implementation/review/verification closure only | Governance foundation only | No strategy candidate | `NO_PROMOTION_AUTHORITY` | `[G:goals.G001,G008]`, `[G008-R]` |
| G002 | Complete | `UNDETERMINED`, identity integrity failure | Future new prereg only; no rerun/rescue | None | `UNIDENTIFIED_SCHEMA` | `[G:goals.G002]`, `[G002-R]`, `[G004-R]` |
| G003 | Complete | `FAIL`, fixed static `O3 OR O4` veto retired | Discard fixed veto family | `[]` | `NO_PROMOTION_AUTHORITY` | `[G:goals.G003]`, `[G003-R]` |
| G004 | Complete | `UNDETERMINED`, dependency nonidentification | Reopen only after separately authorized common-cohort authority | None | `UNIDENTIFIED_SCHEMA` | `[G:goals.G004]`, `[G004-R]` |
| G005 | Superseded | Review-blocked original; resolved by G009/G010 | Do not use original G005 as measurement authority | None | `NO_PROMOTION_AUTHORITY` | `[G:goals.G005,G009,G010]` |
| G005-C1 | Closed under G010 | `UNDETERMINED / INPUT_SCHEMA_MISMATCH` | Schema authority follow-up only under new approval | None | `UNIDENTIFIED_SCHEMA` | `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G005-X1 | Closed under G010 | descriptive / noncausal / nonpromotable `PASS` | Knowledge-only explanatory fact | Nonpromotable knowledge item only | `DESCRIPTIVE_NONCAUSAL` | `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G005-C2 | Closed under G010 | `UNDETERMINED / nonidentified` | Needs exact activation trace/timestamp authority in future | None | `UNIDENTIFIED_SCHEMA` | `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G006 | Complete | `UNDETERMINED / DNF_UNIDENTIFIED`; C4 `CLOSED` metadata-only | Needs true-DNF/stateful activation authority in future | None | `DNF_AUTHORITY_ABSENT`, `C4_CLOSED` | `[G:goals.G006]`, `[G006-R]`, `[G006-J]` |
| G007 | Active until this report is reviewed | Final synthesis/integration-prep only | Integration prepared, not executed | No promotable candidate | `MERGE_APPROVAL_REQUIRED` | `[G:goals.G007]`, current assignment |
| G008 | Complete | Evidence-chain v2 closure | Supports governance only | No strategy candidate | `PROTECTED_SURFACE_ZERO` | `[G:goals.G008]`, `[G008-R]` |
| G009 | Complete | G005 sealed-measurement contract repair only | Enables G010 evidence story; no measurement authority by itself | None | `NO_PROMOTION_AUTHORITY` | `[G:goals.G009]` |
| G010 | Complete | Authoritative final G005 replacement | Mixed terminal G005 closure; no promotion | No strategy candidate | `NO_PROMOTION_AUTHORITY` | `[G:goals.G010]`, `[G010-J]` |

## 3. Ultragoal cross-audit matrix: G001~G010

| Goal | Cross-audit disposition | Commit / HEAD distinction | Test/review receipt history | Protected-surface statement |
|---|---|---|---|---|
| G001 | Superseded. Treat as resolved by G008, not independently open. | Goal receipt records G001 resolved by G008 evidence at `HEAD 9db36cbd`; G008 report itself records code contribution HEAD `86e3ee7`. This report preserves both as historical receipts without reconciling by git execution. | Authority review `153 PASS`, runner `190 PASS`; focused `13`, evidence-chain `396`, full alpha `921 passed, 5 skipped, 4238 deselected` in cited history. | No protected DB/engine authority. `[G]`, `[G008-R]` |
| G002 | Complete as terminal identity failure, not statistical pass/fail. | Terminal report HEAD `6bf93002aeda356da66c68ded322a2b83b7a0efd`; goal completion evidence references later closure HEAD `cfe5f4ab`. | Reviews `272/276/282 CLEAR`; regression union `157 passed, 1 skipped` in goal receipt. | engine/DB-write/registration/promotion/full/target/outcome counters zero. `[G]`, `[G002-R]` |
| G003 | Complete. Fixed static veto family failed and retired. | Durable report has no repository HEAD; goal receipt records `HEAD b5019c43` and evidence_id `ce7c1174e445127077704c8fe626aefd899464892b967864dffb98f0d80e6e5c`. | Reviews `234/237 CLEAR`; evidence/runtime `385`-pass union, gates `38`, runlab `14`, target `4` in goal receipt. | engine/DB/registration/promotion zero. `[G]`, `[G003-R]` |
| G004 | Complete as dependency nonidentification. | Terminal report HEAD `cfe5f4ab283bd5bfaf9301d04fc2c2879ccc3986`; goal receipt records later closure HEAD `74688f2`. | Architect review `289 CLEAR`; direct hash/absence/zero-counter verification and diff check passed in goal receipt. | invocation, engine, DB write, registration, promotion, outcome, receipt/claim, n_trials append all zero. `[G]`, `[G004-R]` |
| G005 | Superseded. Original goal should not be treated as final measurement authority. | Goal receipt records G005 resolved by G009 at `HEAD 81901b3d`; G010 later supplies final measurement replacement at `HEAD 61d26005`. | G009 focused `61 passed`, cleaners `327/326`, reviews `328/329`, QA `330/331`. | C1 input/materializer/target not executed by G009; protected DB untouched. `[G]` |
| G006 | Complete as authority-identification failure. | Goal receipt and terminal artifacts bind completion at `HEAD 25975531`; D1/clause hashes are explicit durable bindings. | JSON/terminal/diff checks passed; cleaner `338`, review `339`, QA `340` in goal receipt/QA report. | motif mining, C4 metrics, engine, DB writes, registration, promotion, retry, rescue all zero. `[G]`, `[G006-R]`, `[G006-J]` |
| G007 | This report is the synthesis deliverable. | Pre-G007-documentation integration baseline records audit branch at `61d26005a26799e9e13ddaca423873850fae834f`; primary G007 documentation commit `f10e41d7` now follows that baseline, and this correction will be committed later, so this report does not assert a final post-correction HEAD/count. | This executor did not run tests. Review/testing must cite historical receipts or future maintainer-approved checks. | Integration prep only; no protected path authority. `[G]`, current assignment |
| G008 | Complete. Evidence-chain v2 bypass removal/closure. | Report HEAD `86e3ee7`; goal receipt evidence `9db36cbd`; representative hardening commits `98fc8469`, `a634ff74`, `098e90ca`, `c197df20`, `d3a47b3f`. | `13`, `396`, `921 passed` histories; reviews `153/190 PASS/CLEAR`. | No strategy promotion, protected DB, engine, live, or G001/G002 state-change authority. `[G008-R]`, `[G]` |
| G009 | Complete contract repair only. | `HEAD 81901b3d`. | Focused `61 passed after commit`; authoritative X1/C2 manifests and C1 probe passed; cleaners/reviews/QA as above. | No final measurement execution; protected DB untouched. `[G]` |
| G010 | Complete authoritative final G005 replacement. | Completion HEAD `61d26005`; G005 terminal artifacts are bound to `25975531ab966eb113d79bc130b9b4493001b1f6`. This distinction is material: artifacts record measurement custody at bound HEAD, while G010 receipt records final post-commit verification/review closure. | Parent-reported `449 passed in 418.64s` after commit, JSON/hash/absence/ledger and X1 receipt/claim validation passed, cleaners `350/351`, reviews `352/353/354/356 CLEAR APPROVE`, QA artifact passed. This report does not claim executor reran them. | engine/DB/registration/promotion/retry/rescue zero. `[G]`, `[G010-J]` |

## 4. Evidence chain and reproducibility manifest

| Artifact / receipt | Binding | Reproducibility implication | Boundary |
|---|---|---|---|
| G008 canonical chain | `finalize_prereg → issue_gate_receipt_v2 → claim_gate_receipt_v2 → append_trial_v2 → issue_promotion_manifest_v2 → catalog PRE receipt → verify_promotion_manifest` | Supported runlab paths bind schema-v2 receipt/claim, sealed dependency roots, manifest-only stage. | Legacy registry/Ledger v1/B1 archive are read/history compatibility only. `[G008-R]` |
| G002 terminal report | experiment `alpha_restart_20260710-g002`; identity attempt `...identity-attempt-001` reserved; full attempt not created; exit `1`; exception `ValueError: timestamp must be an exact integer or digit string` | Failure happened before crosswalk/materialization/factorial/bootstrap/result. | No paired-factorial estimand or outcome metric. `[G002-R]` |
| G002 dependency hashes bound by G004 | report SHA `fdbffdcd...d552`; evidence SHA `abce305b...c712`; identity attempt SHA `b178ccdc...c1cc`; identity status SHA `0e43be2f...bd50` | G004 reuses G002 terminal failure as dependency fact. | No fabricated common cohort. `[G004-R]` |
| G003 run status/log | `run_ctl/v1/status.json` exit `0`; `run_ctl/v1/log.txt`; run `2026-07-16T05:10:36+00:00`~`05:11:03+00:00`; receipt/claim/seal paths in `g003_veto_evidence.json` | One authority target execution for fixed veto family. | No live/OOS/dynamic-capital inference. `[G003-R]` |
| G005-C1 | prereg SHA `af4b8258...79d8`; transcript SHA `8f2ad9f...d0b`; bound HEAD `25975531...b1f6`; builder exit `1` | One parent-captured transcript, no original builder-written log, exact timestamp unavailable/not asserted. | No retry, no target, no input artifact, no KILL/PASS. `[G005-R]`, `[G005-J]` |
| G005-X1 | receipt ID `618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2`; receipt SHA `d511fb...9509`; claim SHA `42a086...ca5f`; run status SHA `20060f...8b2e`; log SHA `de7b2f...ae6e` | Sole receipt/claim/runlab execution, exit code `0`, decision `PASS`. | Descriptive/noncausal/nonpromotable only. `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G005-C2 | prereg SHA `084928f...fa60`; guard SHA `a0273c...c653`; declarations-only guard | Required exact first-activation timestamps/outcome/trace authority absent. | No proxy substitution, no invocation/materialization/receipt/claim/n_trials. `[G005-R]`, `[G005-J]` |
| G005 n_trials ledger | `docs/research/condition_research/research_runs/alpha_restart_20260710/n_trials_ledger.jsonl`; no X1 receipt/G005 series row observed | X1 positive descriptive PASS could not truthfully append empty candidate set; validation rejected before mutation. | No fake negative_or_kill, fake buy/sell hash, fake candidate, fake ledger row. `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G006 D1 bits | path `.../stats_map/d1_onset_clause_bits.parquet`; SHA `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56`; size `6,783,855`; rows `863,446`; schema `code/day/off/t0 + bit_1..bit_39` | Static final-bit snapshot only. | No true-DNF transition, first activation timestamp, activation trace, or outcome authority. `[G006-R]`, `[G006-J]` |
| G006 clause dictionary | `alpha_lab/clause_lab/clauses.py`; SHA `def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4`; size `21,405`; 39 predicates | Predicate dictionary authority only. | No activation timestamp/trace authority. `[G006-R]`, `[G006-J]` |
| G006 terminal/C4 artifacts | `g006_c3_identifiability_evidence.json`, `g006_c3_terminal_report.md`, `c4_gate_status.json`; terminal `UNDETERMINED / DNF_UNIDENTIFIED`, C4 `CLOSED` | Phase 0 authority absence is terminal. | Terminal artifacts are not self-authorizing trace authority; no C4 outcome/metric read. `[G006-R]`, `[G006-J]` |

## 5. G005 final synthesis

### 5.1 G009 vs G010 distinction

- `G009` is **sealed measurement contract repair** only: `HEAD 81901b3d`, focused `61 passed after commit`, authoritative X1/C2 manifests and C1 probe passed, cleaners `327/326`, reviews `328/329`, QA `330/331`; C1 input/materializer/target not executed and protected DB untouched. `[G:goals.G009]`
- `G010` is **authoritative final G005 replacement**: completion HEAD `61d26005`, parent-reported `449 tests passed after commit`, JSON/hash/absence/ledger and receipt/claim validation passed, cleaners `350/351`, reviews `352/353/354/356 CLEAR APPROVE`, QA `g010_terminal_audit_report.json` passed. `[G:goals.G010]`, `[G010-J]`
- G005 terminal artifacts themselves bind to `bound_head=25975531ab966eb113d79bc130b9b4493001b1f6`; G010 completion HEAD is later verification/review closure, not a different strategy result. `[G005-J]`, `[G010-J]`

### 5.2 Branch table

| Branch | Terminal status | Evidence facts | Allowed inference | Forbidden inference |
|---|---|---|---|---|
| C1 time-shift | `UNDETERMINED / INPUT_SCHEMA_MISMATCH`; KILL/PASS not evaluated | One builder/materializer attempt `python scripts/build_g005_c1_input.py`, exit `1`; failure before `c1_input.json`; root `ValueError: t0 must be a nonempty string`; observed L3 schema `t0=int64`, `code=large_string`, `day=int32`, `off=int16`; downstream target/finalizer/receipt/claim/runlab/engine/DB/registration/promotion/retry/rescue/ledger all not observed. | C1 is unresolved due fail-closed input schema mismatch. | Treating C1 as failed synergy, passed synergy, retry-approved, measured, or attachable to a future target run. `[G005-R]`, `[G005-J]` |
| X1 exit competing risk | `PASS`, descriptive / noncausal / nonpromotable | Receipt issued `2026-07-16T17:04:01+00:00`; claim consumed `2026-07-16T17:04:02+00:00`; runlab `started_utc=2026-07-16T17:05:12+00:00`, `ended_utc=2026-07-16T17:07:55+00:00`, exit `0`; residual ratio `0.07790204613985911`; raw contrasts `2022=0.7027777777777778`, `2023=0.7352685300302375`; signs `+/+`; side-effect counters zero. | Descriptive composition finding about exit-cause/competing-risk structure. | Causal effect, counterfactual exit adoption, strategy candidate, registration, promotion, engine execution, DB write. `[G005-R]`, `[G005-J]`, `[G010-J]` |
| C2 activation order | `UNDETERMINED / nonidentified`; H37/H38 KILL/PASS not evaluated | Exact first activation timestamp for clause16/37/38, outcome, and pre-existing activation trace authority absent; D1 bits are `code/day/off/t0 + bit_1..bit_39` snapshot only; static guard is declarations-only and not invoked; invocation/materialization/receipt/claim/target/outcome/n_trials/engine/DB/registration/promotion all `0`. | C2 remains unresolved pending authoritative activation trace/timestamp authority. | Using snapshot bits/off/t0/D1 pairwise/C1 logic/generated traces/later attachments as activation order authority. `[G005-R]`, `[G005-J]`, `[G010-J]` |

### 5.3 n_trials ledger and candidate boundary

C1 and C2 have no gate-bound measurement and are not n_trials row targets. X1 had a sealed receipt/claim/runlab `PASS`, but it is positive descriptive/nonpromotable; v2 append validation rejected ledger mutation before write with `candidate_set may be empty only for a negative_or_kill measurement`. Therefore no truthful G005/X1 series row exists, and no fake `negative_or_kill`, fake buy/sell hash, fake candidate, or fake ledger row may be made. `[G005-R]`, `[G005-J]`, `[G010-J]`

## 6. G006 final synthesis

### 6.1 Terminal decision

`G006-C3` closes at Phase 0 as `UNDETERMINED / DNF_UNIDENTIFIED`; formal candidate count is `0`; `KILL`/`PASS` were not evaluated; C4 is `closed`; `c4_outcome_read_allowed=false`. This is **absence-of-identification** for formal true-DNF/stateful activation authority, not negative motif evidence or poor P&L evidence. `[G006-R]`, `[G006-J]`

### 6.2 D1/clause binding and authority search

- D1 descriptor: `d1_onset_clause_bits.parquet`, SHA `4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56`, size `6,783,855`, rows `863,446`, schema `code/day/off/t0 + bit_1..bit_39`, day range `20220323..20231228`, off range `11..1799`, nulls none. It is final-bit snapshot authority only. `[G006-R]`
- Clause dictionary: `alpha_lab/clause_lab/clauses.py`, SHA `def0f5c8750c19c02b52f026461422572641b36730d28e5bdfa97f20deabb7d4`, size `21,405`, 39 predicate mappings; no first-activation trace/timestamp authority. `[G006-R]`, `[G006-J]`
- Pre-artifact authority search at HEAD `81901b3d` under `docs/research/condition_research/research_runs/alpha_restart_20260710` found no authoritative true-DNF/stateful activation timestamp/trace artifact; no protected DB or outcome scan was performed; later G006 terminal artifacts are excluded from authority-source status. `[G006-R]`, `[G006-J]`

### 6.3 C4 closure and adversarial boundaries

C4 remains `CLOSED` metadata-only. It was not opened/executed, and no incremental total profit, MDD, scheduler, overlap, portfolio metric, C4 outcome read, or C4 computation was generated. Zero counters cover engine, DB writes, registration, promotion, retry, rescue, candidate-selection outcome reads, C4 outcome reads/computations, motif mining, C4 metrics, ledger rows, receipts, and claims. `[G006-R]`, `[G006-J]`

Adversarial cases rejected by the G006 QA report include: D1/clause tamper, absent authority reclassified as KILL, post-search self-authority, generic outcome-read overclaim, flat39/off/t0 proxy use, dormant parameter mislabeled as result, C4 open/read attempts, QA metadata presented as receipt/claim/ledger, side-effect inference, and inconsistent terminal field mixing. `[G006-J]`

## 7. Confirmed knowledge

1. G008 confirms the evidence-chain v2 governance contract: canonical receipt/claim, sealed dependency roots, manifest-only stage, PRE/POST/catalog/promotion fencing, and legacy write fencing are established as infrastructure closure only. `[G008-R]`
2. G002 confirms the U7-F0 bridge did not reach estimand construction: 671 champion ledger rows parsed, 298 fixed cohort rows selected, then float `매수시간=20220323090127.0` was selected before exact `진입시각='090127'` fallback because `진입시각` was not in candidate/fallback order. `[G002-R]`
3. G003 confirms the fixed static `O3 OR O4` veto is harmful in the measured drop-only diagnostic: combined `delta_profit=-8,453,880`, retained `120/298`, false-dropped positive trades `112/173`, O4 equivalence mismatch `0`. `[G003-R]`
4. G004 confirms P1/M1/S1 cannot be identified without the G002 common cohort; all three are `identified=false`. `[G004-R]`
5. G005 confirms a mixed terminal family: C1 schema-blocked, X1 descriptive PASS, C2 nonidentified; aggregate is neither all-PASS nor all-FAIL. `[G005-R]`, `[G005-J]`
6. G006 confirms true-DNF/stateful activation timestamp/trace authority is absent from current durable sources; C4 must remain closed. `[G006-R]`, `[G006-J]`
7. Across G002/G003/G004/G005/G006/G008/G009/G010, protected DB writes, strategy registration, promotion, unauthorized engine execution, retry, rescue, and fake ledger/candidate creation remain outside authority. `[B]`, `[G]`, `[G005-J]`, `[G006-J]`

## 8. Discarded hypotheses / failed results

| Hypothesis / inference | Disposition | Reason | Source |
|---|---|---|---|
| Fixed static `O3 OR O4` veto as entry drop driver | Discarded / retired | Both-year profit kill fired; 2023 MDD worsened; candidate set `[]`. | `[G003-R]` |
| “G005 all passed” | Rejected | C1 and C2 are `UNDETERMINED`; only X1 is descriptive PASS. | `[G005-R]`, `[G005-J]` |
| “G005 all failed” | Rejected | X1 descriptive PASS exists; C1/C2 are unresolved/nonidentified, not statistical failures. | `[G005-R]`, `[G005-J]` |
| X1 as causal/promotable strategy evidence | Rejected | Explicit descriptive/noncausal/nonpromotable claim type; no candidate or promotion. | `[G005-R]`, `[G010-J]` |
| Flat final 39-bit snapshot/off/t0 as activation timestamp authority | Rejected | G005-C2 and G006-C3/C4 explicitly ban these proxies. | `[G005-J]`, `[G006-J]` |
| Fake ledger row or candidate fabrication | Rejected | X1 append rejection before mutation; candidate/negative_or_kill/buy/sell hash fabrication prohibited. | `[G005-R]`, `[G005-J]`, `[G010-J]` |
| G006 absent authority as negative motif evidence | Rejected | Terminal cause is authority absence, not motif/outcome failure. | `[G006-R]`, `[G006-J]` |

## 9. Unresolved / nonidentified items

| Item | Current terminal label | Missing authority | Next permissible framing |
|---|---|---|---|
| G002 U7-F0 bridge | `UNDETERMINED` | Common-entry identity crosswalk, L3/D1 materialization, factorial estimates, bootstrap/result | New preregistration and new attempt ID only; no rescue/rerun of sealed attempt. `[G002-R]` |
| G004 P1/M1/S1 | `UNDETERMINED / dependency nonidentification` | G002 common cohort, denominator, estimand, invocation, outcome support | Revisit only after separately authorized successful common-cohort attempt. `[G004-R]` |
| G005-C1 | `UNDETERMINED / INPUT_SCHEMA_MISMATCH` | Valid `t0` identity/schema handling and input artifact | New approved/sealed path only; closed C1 attempt itself is not retry-approved. `[G005-J]` |
| G005-C2 | `UNDETERMINED / nonidentified` | Exact first-activation timestamps for clause16/37/38, outcome, pre-existing activation trace authority | Highest-value future trace authority project. `[G005-J]` |
| G006-C3/C4 | `UNDETERMINED / DNF_UNIDENTIFIED`; C4 `CLOSED` | Formal true-DNF/stateful activation trace/timestamp authority and formal C3 survivor | C4 cannot open until formal C3 survivor plus exact timestamp gate. `[G006-R]`, `[G006-J]` |
| X1 strategy/causal implication | Unresolved by design | Counterfactual/causal exit adoption authority, strategy candidate identity, engine/OOS evidence | Keep as explanatory descriptive knowledge only. `[G005-R]` |

## 10. Surviving candidates register

| Candidate type | Status | Notes | Source |
|---|---|---|---|
| Promotable STOM strategy candidate | **0 / none** | No branch yields promotion authority, buy/sell candidate hash pair, registration proposal, or engine request authority. | `[G005-J]`, `[G006-R]`, `[G]` |
| G003 static `O3 OR O4` veto | Retired | Candidate set `[]`; no promotion. | `[G003-R]` |
| X1 descriptive knowledge item | Survives as nonpromotable knowledge only | It may inform research explanation of exit-cause composition but cannot be used as candidate or causal action rule. | `[G005-R]`, `[G010-J]` |
| Future follow-up candidate | Research infrastructure candidate only | Outcome-blind authoritative activation trace / exact first-activation timestamp source could unlock G005-C2 and G006-C3/C4, but requires separate approval. | `[M-B]`, `[G005-J]`, `[G006-R]` |

## 11. Approval needs and forbidden inferences

### 11.1 Requires explicit future maintainer/user approval

- Any protected DB read/write beyond already cited read-only/source-authority contexts.
- Any engine execution, engine request, supervised/live trading, broker/runtime path, strategy registration, or promotion.
- Any retry/rescue/rerun/variant of sealed C1/C2/C3/G002 attempts.
- Any creation or attachment of new activation traces, exact timestamp authority, C4 opening, C4 outcome/metric read, or portfolio computation.
- Any fake or derived receipt/claim/ledger row/candidate identity.
- Git integration actions require explicit future maintainer/user approval: merge, push, rebase/squash/cherry-pick into the target branch, target-branch mutation, or worktree deletion. Primary G007 documentation commit `f10e41d7` and this later correction commit are documentation-only and are not such integration actions.

### 11.2 Forbidden inferences for this report

- G008/G009/G010 tests/reviews do not imply trading profitability, live success, DB authority, or engine authority.
- G002/G004/C1/C2/G006 `UNDETERMINED` statuses must not be relabeled as `PASS`, `KILL`, or `FAIL`.
- G003 `FAIL` must not be rescued by reweighting/reselecting the same family.
- X1 `PASS` must remain descriptive, noncausal, and nonpromotable.
- G006 C4 `CLOSED` metadata-only status must not be used to infer C4 metrics or opportunity portfolio performance.

## 12. Risk labels

| Label | Applies to | Meaning |
|---|---|---|
| `NO_PROMOTION_AUTHORITY` | All goals/branches | No strategy promotion, registration, engine request, or live authority is created. |
| `DESCRIPTIVE_NONCAUSAL` | G005-X1 | PASS is explanatory composition evidence only, not causal or actionable. |
| `UNIDENTIFIED_SCHEMA` | G002, G004, G005-C1, G005-C2 | Required identity/schema/trace inputs are absent or incompatible. |
| `DNF_AUTHORITY_ABSENT` | G006-C3 | Formal true-DNF/stateful activation authority is missing. |
| `C4_CLOSED` | G006-C4 | Downstream C4 is closed metadata-only; no outcome/metric read. |
| `PROTECTED_SURFACE_ZERO` | G002/G003/G004/G005/G006/G008/G009/G010 | Cited evidence records zero or no authority for protected DB write, engine, registration, promotion, retry/rescue. |
| `MERGE_APPROVAL_REQUIRED` | Branch integration | Integration is prepared but not executed; maintainer approval is required before merge, push, rebase/squash/cherry-pick into the target branch, target-branch mutation, or worktree deletion. |

## 13. Highest-information-value follow-up

The highest-information follow-up is **an outcome-blind, separately approved activation-trace authority project**:

1. Define or recover a source-hashed, pre-existing authority for exact first activation timestamps / stateful activation traces.
2. Keep it outcome-blind: no 2025~2026 or liquidation-known 2024 selection/reranking; no C4 outcome/metric inspection during authority construction.
3. Seal a new preregistration and new attempt IDs before any C2/C3/C4 measurement.
4. Bind D1/clause inputs and trace source hashes; explicitly reject flat39/off/t0/row-order/proxy reconstruction.
5. Only after a formal C3 survivor and exact timestamp gate may a C4 opportunity portfolio be considered.

This follow-up is not a trading candidate and is not approved by this report. It is the highest information-value next question because it blocks both G005-C2 and G006-C3/C4. `[G005-J]`, `[G006-R]`, `[G006-J]`

## 14. Merge-ready branch integration checklist

### 14.1 Pre-G007-documentation baseline and integration-time recheck
아래 값은 G007 assignment가 제공한 **pre-G007-documentation baseline**으로 기록하며, 본 보고서 작성자가 git 명령으로 재검증했다는 주장을 하지 않는다. Primary G007 documentation commit `f10e41d7` now follows this baseline; this correction itself will be committed afterward, so this report intentionally does **not** assert a final post-correction audit HEAD or divergence count.

- Audit branch pre-G007-documentation baseline: `research/alpha-lab-audit-ideas-20260714` at `61d26005a26799e9e13ddaca423873850fae834f`.
- Original alpha branch previously observed target baseline: `research/alpha-lab-idea5-foundation-20260707` at `bd5bb3c4bc9253034326eadfe8afdfd4605258c4`.
- Previously observed merge base: `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`.
- Pre-G007-documentation divergence baseline: target-only `2`, audit-only `112`.
- Target-only commits observed at that baseline: `bd5bb3c4`, `ff251f9a`.
- Integration operator must freshly run read-only `git rev-parse HEAD`, `git merge-base HEAD research/alpha-lab-idea5-foundation-20260707`, and `git rev-list --left-right --count research/alpha-lab-idea5-foundation-20260707...HEAD` immediately before any approved target integration.
- Integration is **prepared but not executed**. This report does not perform or authorize a merge.

### 14.2 Checklist before any maintainer-approved integration action

- [ ] Maintainer explicitly approves target integration. Without this, no merge, push, rebase, squash, cherry-pick into the target branch, target-branch mutation, or worktree deletion. This does not block the already-created primary G007 documentation commit `f10e41d7` or this later documentation correction commit.
- [ ] Immediately before any approved target integration, integration operator freshly runs read-only `git rev-parse HEAD`, `git merge-base HEAD research/alpha-lab-idea5-foundation-20260707`, and `git rev-list --left-right --count research/alpha-lab-idea5-foundation-20260707...HEAD`; use those fresh values for final integration-time HEAD/base/count, not the pre-G007-documentation baseline above.
- [ ] Preserve detailed evidence commit chain by default. **No squash recommendation by default** because receipt/review/test provenance is audit material.
- [ ] Reconfirm target-only commits `bd5bb3c4`, `ff251f9a` are intentionally preserved or integrated according to maintainer decision.
- [ ] Reconfirm protected paths remain untouched: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, runtime sidecars.
- [ ] Treat G007 report and management briefing as audit documents only; do not convert them into strategy registration or engine run instructions.
- [ ] Keep G001→G008 and G005→G009→G010 supersession chain visible in commit/review notes.
- [ ] Confirm all terminal distinctions remain intact: G002/G004/C1/C2/G006 unresolved/unidentified, G003 FAIL/retired, X1 descriptive noncausal nonpromotable PASS, no promotable strategy candidates.
- [ ] If future verification is requested, distinguish newly run checks from historical checks cited here.
- [ ] Worktree cleanup/deletion is a separate post-merge approval step and must not happen while user/peer work or unmerged evidence remains.

## 15. Appendix: citation, terminology, artifact, test, review matrix

### 15.1 Terminology

| Term | Meaning in this report |
|---|---|
| `UNDETERMINED` | Terminal closure without statistical PASS/KILL/FAIL because required identity/schema/authority was absent or incompatible. |
| `nonidentified` / `DNF_UNIDENTIFIED` | Required estimand or trace authority is not identified; no negative result is implied. |
| `descriptive / noncausal / nonpromotable PASS` | Measurement passed its descriptive rule but cannot be used for causal, counterfactual, strategy, promotion, registration, or engine claims. |
| `artifact-bound HEAD` | HEAD/hash recorded inside measurement artifacts at the time of terminal evidence custody. |
| `completion HEAD` | Later goal receipt HEAD for verification/review/closure. It may differ from artifact-bound HEAD and must not be treated as a different measurement result. |

### 15.2 Test/review history matrix (cited history only)

| Scope | Cited checks | Source | Executor ran now? |
|---|---|---|---|
| G008 | `13 passed`; `396 passed`; `921 passed, 5 skipped, 4238 deselected`; authority `153 PASS/CLEAR`; runner `190 PASS/CLEAR` | `[G008-R]`, `[G]` | No |
| G002 | reviews `272/276/282 CLEAR`; regression union `157 passed, 1 skipped`; protected tick DB/source POST hashes equal | `[G]` | No |
| G003 | reviews `234/237 CLEAR`; evidence/runtime `385`-pass union, gates `38`, runlab `14`, target `4` | `[G]` | No |
| G004 | architect review `289 CLEAR`; direct hash/absence/zero-counter verification and git diff check passed | `[G]` | No |
| G009 | focused `61 passed after commit`; authoritative X1/C2 manifests and C1 probe passed; cleaners `327/326`; reviews `328/329 CLEAR APPROVE`; QA `330/331` passed | `[G]` | No |
| G006 | JSON/terminal/diff checks; cleaner `338`; review `339 CLEAR APPROVE`; QA `340 PASS` | `[G]`, `[G006-J]` | No |
| G010 | `449 passed in 418.64s` after commit; JSON/hash/absence/ledger and X1 receipt/claim validation passed; diff check passed; cleaners `350/351`; reviews `352/353/354/356 CLEAR APPROVE`; QA artifact passed | `[G]`, `[G010-J]` | No |

### 15.3 Artifact/receipt index

| Area | Key artifact / receipt |
|---|---|
| G002 | `g002_u7_f0_terminal_report.md`; `g002_identity_failure_evidence.json`; `identity_attempt.json`; `identity_status.json` |
| G003 | `g003_veto_report.md`; `g003_veto_evidence.json`; `run_ctl/v1/status.json`; `run_ctl/v1/log.txt` |
| G004 | `g004_terminal_report.md`; G002 hash bindings in section `G002 의존성 증거 바인딩` |
| G005-C1 | `c1_terminal_report.md`; `c1_terminal_evidence.json`; `c1_builder_attempt_bg_6.txt`; prereg SHA `af4b8258...79d8` |
| G005-X1 | receipt/claim `618f8aeb2ea25d65291f41040a38234d985d6ca4896434e35b7b2c58fd44bbc2`; `x1_execution_evidence.json`; `x1_terminal_report.md`; run status/log |
| G005-C2 | `c2_terminal_report.md`; `c2_nonidentification_evidence.json`; `scripts/g005_c2_nonidentification_guard.py`; prereg SHA `084928f...fa60` |
| G005 family/G010 | `g005_execution_report.md`; `g005_terminal_summary.json`; `g010_terminal_audit_report.json`; `n_trials_ledger.jsonl` absence search |
| G006 | `g006_c3_terminal_report.md`; `g006_c3_identifiability_evidence.json`; `c4_gate_status.json`; `g006_terminal_audit_report.json`; D1/clause hashes |

### 15.4 Final audit assertion

The frozen evidence supports only this final G007 conclusion: **no promotable strategy candidate exists; integration is audit/knowledge/prep-only; future progress requires separate maintainer-approved authority work, especially activation trace / exact first-activation timestamp authority.**
