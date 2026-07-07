# Lattice Rereview And Rank03 R2 Boundary Plan

## Scope

Run one bounded rank03 R2 cycle after the lattice rereview. This plan does not
replace `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`; it narrows the
next Plan D action and defines a hard stop if rank03 R2 does not improve.

## Read-First Sources

- `docs/update_log/2026-07-07_lattice_research_rereview_and_rank03_r2_recommendation.md`
- `docs/update_log/2026-07-07_plan_d_rank03_r1_selected_oos_retry03_survivor_handoff.md`
- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_d_selected_oos_20260707/plan_d_rank03_r1_selected_oos_retry03_result_20260707.json`
- `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank03_20260707/r_d_selected_oos_20260707/plan_d_rank03_r1_next_seed_readiness_20260707.json`
- `docs/research/condition_research/generated_conditions/plan_d_seed_pool_20260706/passports/plan_d_rank03_r1_oos_20260707_01.md`
- `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md`
- `utility/ai_agent/strategy.txt`
- `utility/ai_agent/rules.txt`

## Invariants

- Research lane only; every new candidate keeps the `hypothesis_seed` label.
- No portfolio, export, live, final promotion, or A3/promotion-review path.
- No full tick 288 or full min 288.
- No DB UPDATE/DELETE.
- No `git add -A`.
- Do not stage dashboard seven files, `.gjc`, or unrelated `.omo` residue.
- OOS is forbidden unless freeze/preregistration is written first.
- If rank03 R2 has no improvement, stop Plan D and write a condition-generation redesign handoff.

## TODOs

- [ ] R2-1. Source reread and parent freeze check

  Purpose: confirm that the active parent is exactly
  `plan_d_rank03_r1_oos_20260707_01` and that the rank03 R1 survivor metrics
  are still the baseline for improvement.

  Acceptance:
  - Source receipt records line_count and sha256 for all Read-First Sources.
  - Parent buy/sell sha and DB mapping match the passport and survivor result.
  - Positive control or latest gate-health receipt is checked before candidate generation.

- [ ] R2-2. Generate rank03 R2 8-slot candidates, static gate, dry-run registration

  Purpose: create only one bounded R2 candidate set from the rank03 R1 active
  parent, without replay or DB apply until syntax and registration dry-run pass.

  Acceptance:
  - Exactly 8 or fewer candidates are generated.
  - Candidates are sanitized, research-only, and labelled `hypothesis_seed`.
  - `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt` are applied.
  - Static gate and DB registration dry-run pass.
  - No official replay, OOS, portfolio, or export is run in this step.

- [ ] R2-3. INSERT-only apply and official min warm64 limited replay

  Purpose: evaluate only the R2 candidates that passed static gate, using the
  official min full-period warm64 profile.

  Acceptance:
  - DB registration is INSERT-only with backup and collision check.
  - Limited replay uses only rank03 R2 candidates and does not exceed 8 pairs
    unless the report explicitly proves fewer/more static-pass rows within a
    max cap of 24.
  - Results classify every row as `improved`, `flat`, or `no_go` against the
    rank03 R1 baseline.
  - If `improved=0`, write the redesign handoff and stop.

- [ ] R2-4. Optional selected OOS only if improved exists

  Purpose: if replay has improved candidates, freeze and preregister selected
  candidates before a small OOS-style robustness check.

  Acceptance:
  - Selected candidates are max 1-2 unless the handoff justifies otherwise.
  - Freeze ledger and preregistration exist before OOS.
  - OOS uses official min warm64 and only selected candidates.
  - Results classify `survivor|hold|no_go`.
  - If no selected OOS survivor exists, stop Plan D and write redesign handoff.

- [ ] R2-5. Boundary decision and handoff

  Purpose: decide whether Plan D can continue or must stop for lattice and
  condition-generation redesign.

  Acceptance:
  - If survivor exists, append-only survivor/seed_pool records are written, but
    R3 is not opened without a new user command.
  - If survivor does not exist, Plan D is marked stopped for redesign.
  - Handoff includes what the lattice taught, what rank03 R2 changed, and the
    next recommended command.
  - Korean commit is created with explicit file staging only.

## Recommended Command Text

```text
$start-work .omo/plans/lattice-rereview-rank03-r2-boundary-20260707.md

범위는 rank03-r2-one-cycle-boundary-no-portfolio-export까지만 진행한다.
목표는 Plan D를 무제한 계속하지 않고 rank03 R2 한 사이클만 수행한 뒤,
개선이 없으면 lattice/condition-generation 설계 재검토로 전환하는 것이다.

진행:
1. Read-First Sources를 EOF까지 다시 읽고 source receipt를 기록한다.
2. active parent `plan_d_rank03_r1_oos_20260707_01`의 passport, buy/sell sha, DB mapping, R1 survivor metrics를 재확인한다.
3. rank03 R2 8-slot 후보를 research lane 전용, hypothesis_seed 라벨, sanitized 이름으로 설계한다.
4. strategy.txt/rules.txt 기준 static gate와 DB registration dry-run을 수행한다.
5. static gate 통과 후보만 INSERT-only로 등록한다.
6. 공식 min 전체기간 warm64 limited replay를 rank03 R2 후보에 한정해 실행한다.
7. 결과를 improved/flat/no_go로 분류한다.
8. improved 후보가 없으면 Plan D를 중단하고 lattice/condition-generation redesign handoff를 작성한다.
9. improved 후보가 있으면 freeze/preregistration 후 selected max 1~2개만 OOS-style robustness check를 실행한다.
10. selected OOS survivor가 없으면 Plan D를 중단하고 redesign handoff를 작성한다.
11. survivor가 있으면 append-only 기록만 남기고 R3/portfolio/export/live/final은 열지 않는다.

금지:
- Plan D R3 자동 진행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- full tick 288 실행 금지
- full min 288 실행 금지
- preregistration 없는 OOS 실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```
