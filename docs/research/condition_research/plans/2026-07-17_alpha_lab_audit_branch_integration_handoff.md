# Alpha Lab audit branch 통합 핸드오프 — 2026-07-17

## 0. 필수 선행 읽기

1. **먼저 읽을 문서:** `docs/research/condition_research/2026-07-17_alpha_lab_full_research_report.md`
   - 이 통합 핸드오프는 위 standalone 연구 종합 보고서 이후에 읽는 실행 설계 문서다.
   - 보고서의 핵심 경계는 그대로 유지한다: audit branch는 승격 후보 0건, B1은 prior target의 유일한 empirical improvement이지만 30거래일 supervised scoring 전 성공 주장이 금지, sell D1은 load-bearing/no-removal 지식, target X1 buy clause-drop은 sealed/implemented but pre-measurement다.
2. **구조 근거:** `agent://367-BranchIntegrationHandoffMap`
   - 이 문서는 위 map의 통합 설계를 한국어 standalone handoff로 확장한다.
3. **작성 경계:** 본 문서 작성 작업은 통합을 실행하지 않았다. git 명령, 테스트, 포매터, gate, engine, DB read/write, live/workflow mutation, merge/cherry-pick/rebase/stash/reset/clean/delete/worktree mutation을 실행하지 않았다.

---

## 1. 목적 / 비목표

### 1.1 목적

- `research/alpha-lab-audit-ideas-20260714` audit branch의 산출물을 future maintainer가 `research/alpha-lab-idea5-foundation-20260707` target branch에 안전하게 반영할 수 있도록 절차를 문서화한다.
- 통합의 의미를 “새 전략 반영”이 아니라 **감사·거버넌스·비승격 지식·보고 체계 보강**으로 고정한다.
- 현재 dirty foundation worktree의 사용자 변경을 보존하면서, 별도 승인된 clean integration worktree에서 `cherry-pick -x`로 provenance를 보존하는 경로를 제시한다.
- preflight/read-only command, conflict manifest, approval-required mutation, per-batch verification, stop/rollback/retirement gate를 한 문서에 모은다.

### 1.2 비목표

- 이 문서는 audit integration을 승인하거나 실행하지 않는다. Audit integration은 future separately approved operation이다.
- 현재 worktree에서 merge/cherry-pick/rebase/stash/reset/clean/delete/commit/push/worktree mutation을 하지 않는다.
- 현재 dirty 사용자 작업을 commit/stash하라고 요구하지 않는다. 사용자 작업의 보존·분기·커밋 여부는 owner가 별도 결정한다.
- overlay merge, broad `ours`/`theirs`, directory copy, squash merge를 기본 해법으로 쓰지 않는다.
- `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, runtime sidecars, live/broker/strategy registration/promotion을 열지 않는다.
- G002/G004/G005-C1/G005-C2/G006의 nonidentified 상태를 KILL/PASS/FAIL로 재분류하지 않는다.
- Audit G005-X1 descriptive PASS를 causal/actionable strategy로 승격하지 않는다.
- Target X1 buy clause-drop을 측정 완료/PASS/후보 승격으로 말하지 않는다.

---

## 2. Source manifest

| Alias | Source | 용도 |
|---|---|---|
| [FIRST-READ] | `docs/research/condition_research/2026-07-17_alpha_lab_full_research_report.md` | 본 handoff의 필수 선행 보고서. 연구 결론, approval boundary, forbidden overclaim, current observation을 종합한 정본. |
| [MAP] | `agent://367-BranchIntegrationHandoffMap` | 통합 설계의 구조 계약: clean worktree, conflict ownership, logical ranges, verification, rollback, retirement criteria. |
| [PARENT-FACTS] | 현재 assignment가 제공한 live facts | target/audit HEAD, merge-base, divergence, dirty inventory, audit diff scope, required logical anchors. Fresh preflight 전까지 report-time 사실로 취급한다. |
| [SYN] | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_final_research_synthesis.md` | Audit G001~G010 final synthesis. [FIRST-READ]가 인용한 durable source. |
| [BRF] | `C:/System_Trading/STOM/STOM_V.wt-alpha-audit/docs/research/condition_research/2026-07-16_alpha_lab_management_briefing.md` | Management no-candidate register, approval/protected-surface boundary. [FIRST-READ]가 인용한 durable source. |
| [H3] | `docs/research/condition_research/plans/2026-07-12_program_handoff_v3.md` | Prior target program 정본: B1, D1, O-series, B-track/B-ext, sell D1 handoff row. |
| [SD1] | `docs/research/condition_research/research_runs/alpha_restart_20260710/sell_d1/sell_d1_report.md` | Post-audit target sell D1 clause ablation: load-bearing [1,3,6,8,9], removal-improvement candidate 0. |
| [X1P] | `docs/research/condition_research/plans/2026-07-17_x1_buy_clause_drop_ab_preregistration.md` | Current target X1 buy clause-drop preregistration: DROP5/DROP15/DROP29/DROP31, type-a ≤10, scratch-only boundary. |
| [POLICY] | `AGENTS.md`, `docs/AGENTS.md` | Docs는 durable decision/history layer이고, fake approvals/gates/protected result mutation 금지. |

---

## 3. Current live facts

아래 값은 [PARENT-FACTS]가 제공한 현재 관측값이다. Future integration 직전에는 반드시 read-only preflight로 fresh 확인한다.

| 항목 | 값 |
|---|---|
| Target branch | `research/alpha-lab-idea5-foundation-20260707` |
| Target HEAD | `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d` |
| Audit branch | `research/alpha-lab-audit-ideas-20260714` |
| Audit HEAD | `e808015ce4bd62601dd75a535a57b36532d55fd5` |
| Merge-base | `541a8d70cb8904cc33f3f325b37e60f6ea1591d3` |
| Divergence | target-only 8 / audit-only 114 |
| Audit diff scope | 113 files, +58,675 / -1,688 |

주의:

- [SYN]/[BRF]의 과거 baseline은 historical record다. 실제 통합 권한과 범위는 위 live facts와 fresh preflight가 우선한다.
- Current target worktree가 dirty이므로 현재 worktree에 직접 integration을 수행하면 안 된다.
- Fresh preflight 결과가 위 값과 다르면 stop gate를 열고 이 handoff를 갱신한다.

---

## 4. Dirty-worktree inventory — 정확히 보존

현재 foundation worktree의 dirty inventory는 아래와 같다. Future operator는 이 목록을 통합 입력으로 덮어쓰거나 정리하면 안 된다.

### 4.1 Modified

- `alpha_lab/registry.py`
- `tests/unit/test_alpha_registry.py`

### 4.2 Untracked

- `.gjc/`
- `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`
- `scripts/u7_f0_frame_measure.py`
- `scripts/u7_f0_materialize.py`
- `tests/unit/test_alpha_g002_frame_measure.py`
- `tests/unit/test_alpha_g002_materialize.py`

### 4.3 보존 규칙

- No stash, no reset, no clean, no overwrite.
- 현재 사용자 작업을 통합 prerequisite으로 commit하거나 stash하라고 요구하지 않는다.
- Current dirty worktree는 observation/source로만 보고, integration은 승인된 별도 clean worktree에서 수행한다.
- `.gjc/`와 `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`는 workflow/evidence state이므로 audit branch에서 가져오거나 덮지 않는다.

---

## 5. Audit scope — 113 files, +58,675/-1,688

Audit branch scope는 [PARENT-FACTS] 기준 `541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5`이다.

- Commit divergence: target-only 8 / audit-only 114.
- File diff: 113 files.
- Line diff: +58,675 / -1,688.
- 이 규모는 overlay merge나 broad `ours`/`theirs`로 처리할 수 없는 통합이다.
- Audit chain은 receipt/review/test provenance를 commit chain에 묶고 있으므로 squash가 기본값이면 안 된다.
- Exact commit list는 read-only `git log --reverse`로 생성해야 한다. 아래 logical anchors는 grouping aids이며 intermediate commit을 건너뛰는 권한이 아니다.

---

## 6. Six exact code/test collisions

아래 여섯 code/test paths는 현재 target dirty inventory와 audit changes가 겹치는 충돌 지점이다. 모두 수동 ownership이 필요하며 overwrite 금지다.

| # | Path | 현재 상태 | 충돌 처리 원칙 |
|---|---|---|---|
| 1 | `alpha_lab/registry.py` | modified | Target 사용자 변경을 baseline으로 보존한다. Audit registry/evidence-chain additions는 tests가 요구하는 최소 단위로 수동 병합한다. Broad `ours`/`theirs` 금지. |
| 2 | `tests/unit/test_alpha_registry.py` | modified | Target test 변경을 유지하고 audit terminal/governance assertions를 추가한다. Nonidentified work를 PASS/KILL/FAIL로 바꾸는 assertion 금지. |
| 3 | `scripts/u7_f0_frame_measure.py` | untracked | Overwrite 금지. Audit G002/U7-F0 계열 script와 이름/역할이 겹치면 namespace split 또는 explicit deconflict commit 필요. |
| 4 | `scripts/u7_f0_materialize.py` | untracked | Overwrite 금지. Current target script가 owner work이므로 audit script를 그대로 checkout하지 않는다. |
| 5 | `tests/unit/test_alpha_g002_frame_measure.py` | untracked | Overwrite 금지. G002는 terminal identity failure/UNDETERMINED 지위를 보존해야 한다. |
| 6 | `tests/unit/test_alpha_g002_materialize.py` | untracked | Overwrite 금지. Audit test 추가는 target untracked test와 차이를 비교해 수동 reconcile한다. |

---

## 7. Protected / excluded paths

다음 경로는 audit integration 대상이 아니거나 별도 운영 승인 없이는 접근·변경할 수 없다.

| Path / surface | 처리 |
|---|---|
| `.gjc/**` | workflow/session state. Cherry-pick/merge/import 제외. |
| `.omo/evidence/tmap-walkforward/_discovery_feedback.txt` | 현재 사용자 evidence state. Audit version으로 덮지 않음. |
| `_database/`, `_database_v3k_shadow/`, `*.db` | Protected DB. Read/write/registration 모두 별도 승인 없이는 금지. |
| `_log/`, `backup/`, `backtest/graph/`, `.omx/reports/` | Runtime/output/protected evidence 영역. Integration diff에 나타나면 stop. |
| `v3k_settings*.json`, runtime sidecars | Runtime sidecar. Integration 대상 아님. |
| `docs/research/condition_research/source_reports/**` | 원본 보존본. README 원칙상 trailing whitespace 같은 비의미 변경도 피한다. |
| live broker, engine/backtest run, strategy registration/promotion | 문서 통합과 무관. 별도 explicit approval 필요. |

---

## 8. Audit research conclusions that must survive

통합 후에도 아래 research conclusions는 그대로 보존되어야 한다.

1. **Audit G001~G010의 promotable STOM strategy candidate는 0건이다.**
   - Audit branch 산출물은 governance closure, discarded family, unresolved/nonidentified work, nonpromotable knowledge다.
2. **G001은 G008로 superseded/resolved되었다.**
   - Evidence-chain v2 closure는 receipt/claim/manifest fencing과 reproducibility foundation이다. Strategy authority가 아니다.
3. **G003 fixed static `O3 OR O4` veto는 FAIL/retired다.**
   - `delta_profit=-8,453,880`, retained 120/298, false-dropped positives 112/173.
   - 같은 family를 reweight/reselect/rescue로 부활시키지 않는다.
4. **G002/G004/G005-C1/G005-C2/G006은 nonidentified/UNDETERMINED 계열이다.**
   - G002: 671 ledger rows → 298 fixed cohort 후 timestamp identity failure.
   - G004: G002 common cohort 부재로 dependency nonidentification.
   - G005-C1: `INPUT_SCHEMA_MISMATCH`, `t0 must be a nonempty string`.
   - G005-C2: clause16/37/38 exact first-activation timestamp/trace authority 없음.
   - G006: D1 rows 863,446, schema `code/day/off/t0 + bit_1..bit_39`, final-bit snapshot only; DNF authority 아님.
5. **G005-X1은 descriptive/noncausal/nonpromotable PASS다.**
   - residual ratio `0.07790204613985911`.
   - raw contrasts 2022 `0.7027777777777778`, 2023 `0.7352685300302375`, signs +/+.
   - Counterfactual exit adoption, strategy registration, promotion 권한 없음.
6. **G005 original은 G009/G010으로 superseded되었다.**
   - G009 HEAD `81901b3d`, focused 61 passed.
   - G010 completion HEAD `61d26005`, parent-reported 449 tests passed.
   - G010도 no promotion/no DB/no engine/no live authority다.
7. **Activation-trace authority project는 future research idea이지 현재 통합 작업이 아니다.**
   - Flat D1 bits/off/t0로 activation order를 복원했다고 말하면 안 된다.

---

## 9. Target newer work that must survive

Audit integration은 target의 더 최신 work를 덮어쓰면 안 된다.

1. **B1 supervised live handoff**
   - Prior target program의 유일한 empirical improvement.
   - 2022 Δ+947,387원, 2023 Δ+591,485원, ΣΔ+1,538,872원.
   - Buy sha `348c5181`, sell sha `48018620`.
   - 30거래일 supervised small live scoring 전 live success claim 금지.
2. **Sell D1 post-audit target result**
   - Seal `bd5bb3c4`, generated commit `9937d6cc`, judgment reference `50383772`.
   - Load-bearing clauses [1, 3, 6, 8, 9].
   - Removal-improvement/B2 candidates: 0.
   - Exit clause deletion recommendation으로 바꾸면 안 된다.
3. **Current target X1 buy clause-drop preregistration**
   - Sealed/implemented but pre-measurement.
   - Candidates: DROP5, DROP15, DROP29, DROP31.
   - Type-a ≤10, scratch strategy.db only, no 2024/2025 measurement.
   - X1 PASS, measured result, candidate promotion을 말하지 않는다.
4. **Current dirty user work**
   - Section 4/6의 modified/untracked files는 integration prerequisite으로 정리하지 않는다.
5. **Reporting chronology**
   - Audit “candidate 0” 결론은 prior B1 handoff를 취소하지 않는다.
   - Audit G005-X1과 target X1 buy clause-drop은 이름만 비슷한 별개 work다.

---

## 10. Options and recommendation

### Option A — 권장: clean integration worktree + commit-preserving `cherry-pick -x`

- 승인 후 target HEAD `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`에서 별도 integration worktree/branch를 만든다.
- Audit commits를 exact log order로 작은 logical batches에 나누어 `cherry-pick -x` 한다.
- 여섯 code/test collisions는 owner rules에 따라 수동 병합한다.
- Docs/reporting reconciliation과 tests/protected-path checks를 batch마다 수행한다.

장점:

- 현재 dirty worktree 보존.
- Audit commit provenance와 `-x` trailer 보존.
- Batch rollback이 가능.
- Broad overlay/squash보다 review가 정확하다.

단점:

- 114 audit-only commits / 113 files diff라 conflict resolution 비용이 크다.

### Option B — docs/reporting만 먼저 편입, code/test는 후속 승인

- Audit final synthesis, README/index reconciliation, integration handoff 같은 docs-only changes만 별도 승인으로 먼저 반영한다.
- Code/test governance cherry-pick은 후속 gate로 넘긴다.

장점:

- Protected/runtime 위험이 낮고 report clarity를 빨리 확보한다.

단점:

- Audit branch 전체 integration은 완료되지 않는다.

### Option C — overlay merge, broad `ours`/`theirs`, squash

- 기본적으로 금지한다.
- `git checkout audit -- .`, directory copy, broad `restore --source`, broad conflict side selection, squash merge는 provenance와 user-work protection을 훼손한다.
- Maintainer가 explicit exception을 승인하지 않는 한 선택하지 않는다.

**Recommendation:** Option A. 별도 clean integration worktree에서 exact commit list를 생성하고, commit-preserving `cherry-pick -x`를 small logical batches로 수행한다.

---

## 11. Preflight / conflict-manifest commands — read-only preparation

아래 command blocks는 future operator용이다. 본 문서 작성 중 실행하지 않았다.

### 11.1 Fresh branch facts

```bash
# [읽기 전용/준비] 현재 값 재확인. 실행 전 결과를 handoff receipt에 기록한다.
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha status --short --branch --untracked-files=all
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha rev-parse HEAD
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit rev-parse HEAD
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha merge-base HEAD research/alpha-lab-audit-ideas-20260714
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha rev-list --left-right --count HEAD...research/alpha-lab-audit-ideas-20260714
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit diff --stat 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit diff --name-status --find-renames 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit log --reverse --oneline --decorate 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5
```

Gate:

- Target HEAD가 `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`가 아니면 stop.
- Audit HEAD가 `e808015ce4bd62601dd75a535a57b36532d55fd5`가 아니면 stop.
- Merge-base가 `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`가 아니면 stop.
- target-only/audit-only가 8/114가 아니거나 diff가 113 files +58,675/-1,688가 아니면 stop and update this handoff.

### 11.2 Dirty and collision manifest

```bash
# [읽기 전용/준비] 현재 dirty inventory와 여섯 collision paths를 manifest로 고정한다.
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha status --short --untracked-files=all
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha diff --name-status
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha status --short --untracked-files=all -- alpha_lab/registry.py tests/unit/test_alpha_registry.py scripts/u7_f0_frame_measure.py scripts/u7_f0_materialize.py tests/unit/test_alpha_g002_frame_measure.py tests/unit/test_alpha_g002_materialize.py .gjc .omo/evidence/tmap-walkforward/_discovery_feedback.txt
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit diff --name-status --find-renames 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5 -- alpha_lab/registry.py tests/unit/test_alpha_registry.py scripts/u7_f0_frame_measure.py scripts/u7_f0_materialize.py tests/unit/test_alpha_g002_frame_measure.py tests/unit/test_alpha_g002_materialize.py
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit diff --name-status --find-renames 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5 -- _database _database_v3k_shadow _log backup backtest/graph .omx/reports
```

Gate:

- Section 4 dirty inventory가 달라졌으면 owner에게 확인하고 handoff를 갱신한다.
- Six code/test collisions가 사라지거나 새 collision이 생기면 manifest를 갱신한다.
- Protected path가 audit diff에 포함되면 integration stop.

### 11.3 Exact commit list generation

```bash
# [읽기 전용/준비] Cherry-pick 전에 exact commit list를 생성한다. Anchors는 grouping aids일 뿐 skip 권한이 아니다.
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit log --reverse --format='%H %s' 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-audit log --reverse --format='%H %s' 541a8d70cb8904cc33f3f325b37e60f6ea1591d3..e808015ce4bd62601dd75a535a57b36532d55fd5 -- docs/research/condition_research alpha_lab tests scripts
```

---

## 12. Clean integration worktree creation — mutation / approval-required

현재 `C:/System_Trading/STOM/STOM_V.wt-alpha`가 dirty이므로 그 자리에서 통합하지 않는다. Maintainer explicit approval 후 별도 worktree를 만든다.

```bash
# [변경/승인 필요] 승인 전 실행 금지. Current dirty worktree를 건드리지 않는 별도 integration worktree 생성.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha worktree add -b integration/alpha-lab-audit-20260717 C:/System_Trading/STOM/STOM_V.wt-alpha-integrate ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d
```

Post-create check:

```bash
# [읽기 전용/준비] 원래 dirty worktree가 그대로인지 비교한다.
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha status --short --untracked-files=all
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate status --short --branch --untracked-files=all
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate rev-parse HEAD
```

Gate:

- Original `STOM_V.wt-alpha` dirty inventory가 바뀌면 stop.
- Integration worktree가 clean이 아니면 stop.
- Integration worktree HEAD가 target HEAD `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`가 아니면 stop.

---

## 13. Logical commit batches with exact audit anchors

정확한 commit list는 Section 11.3 read-only log로 생성한다. 아래 anchors/ranges는 logical grouping aids이며, intermediate commits를 건너뛰거나 cherry-pick 순서를 바꾸는 권한이 아니다.

| Batch | Exact anchor / range | 목적 | Cherry-pick rule | Primary risks |
|---|---|---|---|---|
| B0 | `a994d9fe` audit agenda | Audit program agenda/initial framing 보존 | Exact log의 해당 commit부터 시작. 단일 anchor라도 surrounding setup commits를 log로 확인한다. | Agenda가 strategy authority처럼 보이면 안 됨. |
| B1 | evidence chain through `9db36cbd` | G001→G008 evidence-chain foundation, receipt/claim/manifest fencing | `a994d9fe` 이후 `9db36cbd`까지의 exact members를 log order로 `cherry-pick -x`. | Registry/test collisions; evidence-chain을 promotion authority로 오해. |
| B2 | G003 `b25c5d06..b5019c43` | Static `O3 OR O4` veto FAIL/retire evidence | Range 안 intermediate commits를 모두 포함해 log order pick. | FAIL을 rescue/reweight로 바꾸는 문구 금지. |
| B3 | G002/G004 `0fbc9a10..74688f2c` | G002 identity failure, G004 dependency nonidentification | Exact list를 생성한 뒤 G002/G004 scripts/tests 충돌을 수동 해결. | Current untracked U7-F0 files overwrite 금지. |
| B4 | G005/G009 `a29ec0e7..81901b3d` | G005 original supersession, G009 contract repair | G005-X1 descriptive/noncausal/nonpromotable wording 보존. | X1 PASS를 strategy/candidate로 승격하는 오류. |
| B5 | G006/G010 `25975531..61d26005` | G006 DNF_UNIDENTIFIED/C4 closure, G010 final replacement | D1 bit snapshot authority limits를 유지. G010 final replacement를 보존. | Flat bit/off/t0로 activation trace를 만든 척하는 오류. |
| B6 | G007 docs `f10e41d7..e808015c` | Final reporting/integration-prep docs, audit HEAD closure | Docs/reporting/index reconciliation과 함께 pick. | Stale baseline을 current live fact로 오해. |

Mutation command template:

```bash
# [변경/승인 필요] Exact commit list를 만든 뒤, 각 commit 또는 작은 sub-batch마다 실행한다.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate cherry-pick -x <exact_commit_sha_from_read_only_log>

# [변경/승인 필요] Conflict 수동 해결 후. Broad ours/theirs 금지.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate cherry-pick --continue
```

Forbidden:

- `git cherry-pick <range>`를 log 검토 없이 한 번에 실행하지 않는다.
- `git merge`, `git rebase`, `git checkout audit -- .`, broad `git restore --source`, directory copy, squash는 사용하지 않는다.
- Protected path나 current dirty user files를 해결하기 위해 `stash/reset/clean`을 쓰지 않는다.

---

## 14. Conflict ownership

| 영역 | 1차 owner | 병합 원칙 |
|---|---|---|
| `alpha_lab/registry.py` | Target foundation/registry maintainer | Target 사용자 변경 우선 보존. Audit governance/registry additions는 tests가 요구하는 최소 단위로 수동 병합. Broad `ours`/`theirs` 금지. |
| `tests/unit/test_alpha_registry.py` | Registry test owner + audit QA owner | Target test changes를 유지하고 audit terminal/governance assertions를 추가. Nonidentified work를 PASS/KILL로 바꾸지 않는다. |
| `scripts/u7_f0_frame_measure.py` | Current target script owner + audit G002 owner | Untracked target file overwrite 금지. 둘 다 필요하면 rename/namespace split. |
| `scripts/u7_f0_materialize.py` | Current target script owner + audit G002 owner | Materialize semantics와 audit identity-failure status를 분리. |
| `tests/unit/test_alpha_g002_frame_measure.py` | Current target test owner + audit measurement owner | G002 identity failure를 terminal truth로 보존. |
| `tests/unit/test_alpha_g002_materialize.py` | Current target test owner + audit measurement owner | Audit test import는 current untracked test와 수동 reconcile. |
| `docs/research/condition_research/**` | Reporting/documentation owner | Audit report를 “strategy promotion”이 아니라 “audit/governance terminal closure”로 색인. 2026-07-12 handoff와 current report를 덮지 않음. |
| `.gjc/**` | Workflow/session owner | 통합 제외. |
| `.omo/evidence/tmap-walkforward/_discovery_feedback.txt` | User evidence owner | 통합 제외. |
| Protected runtime/DB paths | Operations owner | Diff에 나타나면 stop; 통합 대상 아님. |

---

## 15. Reporting / index reconciliation

1. **Current full report를 first reading으로 색인한다.**
   - `2026-07-17_alpha_lab_full_research_report.md`는 audit/target/current-state 구분의 정본이다.
2. **Audit final synthesis는 audit closure로 분류한다.**
   - “최신 전략 후보”나 “승격 가능한 조건”이 아니라 “G001~G010 감사/거버넌스 terminal closure”로 표시한다.
3. **B1과 audit candidate 0을 동시에 보존한다.**
   - Audit branch candidate 0은 audit scope 결론이다.
   - Prior target B1은 supervised live workflow로 넘겨진 유일한 empirical improvement다.
4. **두 X1 이름을 분리한다.**
   - Audit G005-X1: exit competing-risk descriptive/noncausal/nonpromotable PASS.
   - Target X1 buy clause-drop: pre-measurement A/B preregistration.
5. **Supersession chain을 보존한다.**
   - G001→G008.
   - G005 original→G009→G010.
6. **Ledger reconciliation rules**
   - Audit G005-X1은 nonpromotable이므로 candidate row를 만들지 않는다.
   - C1/C2/G006/G002 nonidentified statuses를 negative row나 fake result row로 만들지 않는다.
   - `n_trials_ledger.jsonl`에 fake buy/sell hash, fake candidate, fake kill/pass row 금지.
7. **Stale baseline 처리**
   - Historical baseline 문구는 보존하되, future integration은 current live facts와 fresh preflight를 authority로 삼는다.
8. **Forbidden overclaim lint**
   - “audit found strategy”, “G005-X1 actionable”, “target X1 passed”, “B1 live successful”, “sell D1 says remove exits” 같은 문구가 index/report에 들어가면 stop.

---

## 16. Per-batch tests and checks

아래는 future approved integration에서 batch마다 수행할 checks다. 본 문서 작성 중 실행하지 않았다.

| Batch | Focus | 승인 후 checks |
|---|---|---|
| B0 `a994d9fe` | Audit agenda/docs framing | `[읽기 전용/준비] git diff --name-status ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d..HEAD`; no protected paths; no promotion wording. |
| B1 through `9db36cbd` | Evidence-chain/registry foundation | `[승인 후 test] python -m pytest tests/unit/test_alpha_registry.py -q`; if batch adds evidence-chain test files, run those exact files. |
| B2 `b25c5d06..b5019c43` | G003 FAIL/retired static veto | `[승인 후 test] run exact G003/O3/O4 test files introduced or touched by the batch`; verify report wording keeps FAIL/retired. |
| B3 `0fbc9a10..74688f2c` | G002/G004 nonidentified | `[승인 후 test] run exact G002/G004 unit tests introduced or touched by the batch`; verify six collision files were not overwritten. |
| B4 `a29ec0e7..81901b3d` | G005/G009 repair | `[승인 후 test] run exact G005/G009 contract tests introduced or touched by the batch`; verify G005-X1 remains descriptive/noncausal/nonpromotable. |
| B5 `25975531..61d26005` | G006/G010 final replacement | `[승인 후 test] run exact G006/G010 tests introduced or touched by the batch`; verify flat D1 bit snapshot is not trace authority. |
| B6 `f10e41d7..e808015c` | G007 final docs/reporting | `[읽기 전용/준비] diff/index review`; if docs-only, test not required, but protected-path and forbidden-overclaim checks are required. |
| Final | Integrated alpha/research surface | `[승인 후 test] python -m pytest tests/unit/test_alpha_registry.py -q`; `[승인 후 test] python -m pytest tests/unit -k alpha -q` or exact touched test files if narrower and sufficient. |

Rule:

- If a batch has no tests selected, that is not a pass. Record “no tests selected” and run exact touched test files or escalate.
- Do not run engine/backtest/live, DB read/write, strategy registration, C4 outcome read, sealed attempt retry/rescue as part of these checks.

---

## 17. Full verification matrix

| Stage | Goal | Classification | Example command / action | Pass condition |
|---|---|---|---|---|
| Preflight branch facts | HEAD/base/divergence/diff 재확인 | 읽기 전용/준비 | Section 11.1 commands | Target/audit/base/count/diff match [PARENT-FACTS]. |
| Dirty manifest | Current user work 보존 범위 확정 | 읽기 전용/준비 | Section 11.2 status/path commands | Section 4 inventory preserved exactly or handoff updated. |
| Commit list | Exact audit commit order 생성 | 읽기 전용/준비 | Section 11.3 log commands | 114 audit-only commits listed in chronological oldest-to-newest order via `--reverse`. |
| Worktree create | Clean integration workspace 확보 | 변경/승인 필요 | Section 12 `git worktree add` | Original dirty worktree unchanged; integration worktree clean at target HEAD. |
| Batch cherry-pick | Provenance-preserving integration | 변경/승인 필요 | `git cherry-pick -x <sha>` | `-x` trailer retained; no broad ours/theirs; conflicts resolved by owner. |
| Docs/reporting check | Audit closure and target state separation | 읽기 전용/준비 | diff/review | No forbidden overclaim; current full report first-reading relation preserved. |
| Registry check | Registry behavior and audit additions coexist | 승인 후 test | `python -m pytest tests/unit/test_alpha_registry.py -q` | Pass; target registry changes preserved. |
| Batch-specific tests | G00x semantics preserved | 승인 후 test | Exact touched test files per batch | Pass; nonidentified statuses not relabeled. |
| Alpha focused regression | Existing alpha unit surface intact | 승인 후 test | `python -m pytest tests/unit -k alpha -q` or exact sufficient touched tests | Pass; no unexpected deselection. |
| Protected path check | DB/runtime/workflow state excluded | 읽기 전용/준비 | `git diff --name-status ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d..HEAD` | No `.gjc`, `.omo`, DB/runtime/protected path unless explicitly approved and documented. |
| Final log/provenance | Commit chain preserved | 읽기 전용/준비 | `git log --oneline --decorate ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d..HEAD` | Cherry-picked commits retain `-x`; no squash unless explicit exception. |
| Target application | Reviewed integration reaches target | 변경/승인 필요 | Section 21 commands or PR/FF process | Only after all checks green and maintainer approval. |
| Retirement | Integration/audit worktrees cleanup | 변경/승인 필요 | Section 22 criteria and commands | No unique evidence; deletion separately approved. |

---

## 18. Stop gates

즉시 중단하고 maintainer/user review를 받아야 하는 조건:

- Fresh preflight가 target HEAD, audit HEAD, merge-base, divergence, diff stats 중 하나라도 [PARENT-FACTS]와 다르게 나온다.
- Current dirty inventory가 Section 4와 다르고 owner 확인이 없다.
- Six code/test collisions를 broad `ours`/`theirs`, overwrite, checkout, restore, copy로 해결하려 한다.
- `.gjc/**`, `.omo/evidence/tmap-walkforward/_discovery_feedback.txt`, DB/runtime/protected path가 integration diff에 들어온다.
- Current user work를 commit/stash/reset/clean/delete해야만 진행 가능하다는 결론이 나온다.
- Audit candidate 0 결론이 B1 handoff를 취소하는 문구로 바뀐다.
- G005-X1 descriptive PASS가 strategy candidate/promotion/registration authority로 바뀐다.
- Target X1 buy clause-drop을 measured/PASS/candidate promoted로 말한다.
- Nonidentified statuses가 KILL/PASS/FAIL로 변환된다.
- Flat D1 bit/off/t0 snapshot으로 activation trace authority를 대체한다.
- Test failure를 해결하려고 engine/backtest/live/DB read/write/strategy registration을 열어야 한다.
- Exact commit list 없이 anchor ranges만 보고 cherry-pick을 시작하려 한다.

---

## 19. Rollback

Rollback도 mutation이므로 approval-required다. Reset/clean/force-push는 기본 금지다.

### 19.1 Cherry-pick conflict 중단

```bash
# [변경/승인 필요] Conflict resolution 전 또는 중단 가능한 cherry-pick을 되돌린다.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate cherry-pick --abort
```

### 19.2 Integration branch에서 일부 commit 철회

```bash
# [변경/승인 필요] 이미 commit된 integration branch의 잘못된 commit은 revert로 철회한다.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha-integrate revert <bad_commit_sha>
```

### 19.3 Integration branch 전체 폐기

- Target branch에 반영 전이면 integration branch/worktree를 폐기하는 것이 가장 안전할 수 있다.
- 단, branch delete와 `git worktree remove`도 별도 approval-required다.
- 삭제 전 status/log를 기록하고 unique evidence가 없는지 확인한다.

### 19.4 Target branch 반영 후

- Reset/force-push 금지.
- Revert commit으로 되돌린다.
- Current dirty user work와 충돌하면 먼저 owner가 별도 보존/분기 정책을 정한다.

---

## 20. Approval gates

| Gate | 필요한 승인 | 열리는 작업 | 닫히는 조건 |
|---|---|---|---|
| G0 Documentation-only | 현재 handoff 생성 승인 | 이 문서 작성만 | 본 문서 생성. Integration 실행 없음. |
| G1 Read-only preflight | Maintainer/operator approval | Section 11 read-only commands | Fresh receipt 기록, mismatch 없음. |
| G2 Clean worktree creation | Explicit mutation approval | Section 12 worktree add | Original dirty worktree unchanged, clean integration worktree confirmed. |
| G3 Batch cherry-pick | Batch-level integration approval | `cherry-pick -x` exact commits | Batch tests/checks green, no protected paths. |
| G4 Conflict resolution | Owner approval for each collision | Six code/test collision manual merge | Owner rules satisfied, no overwrite. |
| G5 Final verification | Maintainer review | Full verification matrix | Tests/checks/reporting/provenance accepted. |
| G6 Target application | Explicit target branch mutation approval | PR/fast-forward/merge into target | Clean target application path, rollback plan ready. |
| G7 Worktree retirement | Separate cleanup approval | worktree remove / branch delete | Section 22 criteria satisfied. |

---

## 21. Final target application

Target application은 integration branch가 green이고 review가 끝난 뒤에만 수행한다. Current dirty `STOM_V.wt-alpha`는 직접 target application 장소로 쓰지 않는다. Maintainer는 PR/remote fast-forward 또는 별도 clean application worktree를 선택한다.

### 21.1 Preferred path: PR or controlled fast-forward

- Integration branch를 review 대상으로 올린다.
- Reviewer가 Section 17 verification matrix와 Section 18 stop gates를 확인한다.
- Target branch mutation approval 후 fast-forward 또는 PR merge를 수행한다.
- Current dirty user work의 보존/재적용/분기 여부는 owner가 별도 결정한다. Integration prerequisite이 아니다.

### 21.2 Clean application worktree command shape

```bash
# [변경/승인 필요] Current dirty worktree 대신 별도 clean target-application worktree를 사용한다.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha worktree add C:/System_Trading/STOM/STOM_V.wt-alpha-apply research/alpha-lab-idea5-foundation-20260707

# [읽기 전용/준비] Apply worktree가 clean target인지 확인한다.
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-apply status --short --branch --untracked-files=all
GIT_OPTIONAL_LOCKS=0 git -C C:/System_Trading/STOM/STOM_V.wt-alpha-apply rev-parse HEAD

# [변경/승인 필요] Integration branch가 fast-forward 가능한 경우에만 target 적용.
git -C C:/System_Trading/STOM/STOM_V.wt-alpha-apply merge --ff-only integration/alpha-lab-audit-20260717
```

Gate:

- Apply worktree가 dirty이면 stop.
- Fast-forward가 안 되면 stop and review; no rebase/merge commit/squash without explicit approval.
- Protected path diff가 있으면 stop.

---

## 22. Worktree-retirement criteria

Audit worktree 또는 integration/application worktree 삭제는 별도 승인 없이는 하지 않는다.

Retirement 전 조건:

1. Audit branch `e808015ce4bd62601dd75a535a57b36532d55fd5`까지의 통합 여부가 manifest로 정리되어 있다.
2. Intentionally excluded commits/paths가 있으면 이유가 docs/review note에 남아 있다.
3. Target branch에 필요한 docs/index/evidence references가 존재한다.
4. No protected path mutation이 검증되어 있다.
5. `git status --short --untracked-files=all` 기준 worktree에 uncommitted/untracked unique evidence가 없다.
6. Peer/user 작업이 해당 worktree를 사용 중이지 않다.
7. Rollback window와 backup/remote policy를 maintainer가 승인했다.
8. 삭제 명령 자체가 approval-required로 승인되었다.

```bash
# [변경/승인 필요] Criteria 충족 전 실행 금지.
git worktree remove C:/System_Trading/STOM/STOM_V.wt-alpha-audit
git worktree remove C:/System_Trading/STOM/STOM_V.wt-alpha-integrate
git worktree remove C:/System_Trading/STOM/STOM_V.wt-alpha-apply
```

---

## 23. Handoff completion checklist

Future maintainer는 통합 승인 전후에 아래를 체크한다.

- [ ] `docs/research/condition_research/2026-07-17_alpha_lab_full_research_report.md`를 먼저 읽었다.
- [ ] 이 handoff가 integration execution이 아니라 future approved operation 문서임을 확인했다.
- [ ] Target HEAD `ccc6d7c746cf8b154c65356d3d3ff1d90ca0010d`, audit HEAD `e808015ce4bd62601dd75a535a57b36532d55fd5`, merge-base `541a8d70cb8904cc33f3f325b37e60f6ea1591d3`를 fresh rechecked했다.
- [ ] target-only 8 / audit-only 114, audit diff 113 files +58,675/-1,688를 fresh rechecked했다.
- [ ] Current dirty inventory를 Section 4와 비교했고, no stash/reset/clean/overwrite 원칙을 확인했다.
- [ ] Six code/test collisions를 Section 6 그대로 manifest에 올렸다.
- [ ] `.gjc`, `.omo`, DB/runtime/protected paths가 integration 대상에서 제외되었다.
- [ ] Exact commit list를 read-only log로 생성했다.
- [ ] Logical anchors `a994d9fe`, through `9db36cbd`, `b25c5d06..b5019c43`, `0fbc9a10..74688f2c`, `a29ec0e7..81901b3d`, `25975531..61d26005`, `f10e41d7..e808015c`를 grouping aids로만 사용했다.
- [ ] Every cherry-picked commit retained `-x` provenance unless explicit exception was approved.
- [ ] Overlay merge, broad `ours`/`theirs`, squash, directory copy를 사용하지 않았다.
- [ ] Audit G001~G010 candidate count 0이 보존되었다.
- [ ] G003 FAIL/retired, G005-X1 descriptive/noncausal/nonpromotable, G002/G004/G005-C1/C2/G006 nonidentified statuses가 보존되었다.
- [ ] B1 supervised live handoff, sell D1 load-bearing/no-removal, target X1 pre-measurement 지위가 보존되었다.
- [ ] README/reporting/index reconciliation이 audit closure와 target current-state를 분리한다.
- [ ] Batch-specific tests/checks와 final verification matrix가 green이다.
- [ ] Target application은 별도 explicit approval 뒤 clean path에서만 수행되었다.
- [ ] Worktree retirement는 Section 22 criteria 충족 후 별도 승인으로만 수행되었다.

---

## 24. Final safe summary

이 handoff의 안전한 한 줄 결론은 다음이다.

> Audit branch integration은 새 전략을 가져오는 일이 아니라 audit/governance/knowledge/reporting을 provenance-preserving 방식으로 target에 편입하는 future approved operation이다. 현재 dirty worktree는 보존하고, exact log로 commit list를 만든 뒤 별도 clean integration worktree에서 `cherry-pick -x` small batches로 처리하며, no stash/reset/clean/overwrite, no overlay/ours/theirs/squash, no protected DB/runtime/live/registration, no forbidden overclaim 원칙을 지킨다.
