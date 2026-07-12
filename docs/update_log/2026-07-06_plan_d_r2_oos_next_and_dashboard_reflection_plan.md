# Plan D R2 OOS Next And Dashboard Reflection Plan (2026-07-06)

## 1. Current Research Checkpoint

| item | status |
|---|---|
| active worktree | `C:/System_Trading/STOM/STOM_V.wt-dev` |
| active branch | `loop/process-research-pipeline` |
| current research HEAD | `f8f4860c 연구: Plan D rank01 R2 limited replay` |
| latest completed scope | `plan-d-rank01-rd-freeze-r2-limited-replay-no-portfolio-export` |
| handoff | `docs/update_log/2026-07-06_plan_d_rank01_r2_limited_replay_handoff.md` |
| result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank01_20260706/r_d_freeze_r2_limited_20260706/plan_d_rank01_r2_limited_replay_result_20260706.json` |

Plan D rank01 R2 limited replay is complete and committed. The scope used official min full-period warm64 replay with a 24-pair limit. It did not execute OOS, portfolio, export/live/final promotion, DB UPDATE/DELETE, or any run beyond 24 pairs.

| metric | value |
|---|---:|
| designed R2 pairs | 24 |
| static gate passed | 24/24 |
| DB registration | INSERT-only 48 rows |
| replay rows | 24/24 ok |
| gate_passed | 24/24 |
| improved vs slot04 | 9 |
| flat | 15 |
| no_go | 0 |

Top next-freeze candidates:

| reason | label | profit | MDD | trades | daily |
|---|---|---:|---:|---:|---:|
| best_profit | `plan_d_r1_rank01_r2_15_l14_amt14000_default_tp3_sl3_hold90` | 2,773,694 | 15.75 | 192 | 0.90 |
| lowest_mdd_among_improved | `plan_d_r1_rank01_r2_21_l14_rate_floor85_default_tp3_sl3_hold90` | 2,515,910 | 15.57 | 188 | 0.90 |
| nearby_amount_axis_confirmation | `plan_d_r1_rank01_r2_12_l14_amt13000_default_tp3_sl3_hold90` | 2,550,258 | 15.75 | 197 | 0.90 |

## 2. Next Research Page

The next useful page is a bounded selected OOS/preregistration page. This is worth running because R2 is no longer a no-go-only exploration: 9/24 candidates improved against the frozen slot04 parent, and the best candidates improved profit while reducing MDD.

However, the R2 replay is still full-period/in-sample style evidence. It is not enough for portfolio/export. The next page should only test whether the selected frozen R2 candidates survive an OOS-style validation.

Recommended command:

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 plan-d-rank01-r2-selected-oos-prereg-no-portfolio-export까지만 진행한다.
목표는 R2 limited replay improved 후보 중 selected freeze 후보만 preregistration으로 고정하고,
공식 OOS만 제한 실행해 Plan D 다음 라운드 진행 가능 여부를 판단하는 것이다.

금지:
- portfolio 산출 금지
- export/live/final promotion 금지
- preregistration 없는 OOS 금지
- selected freeze 후보 외 OOS 실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
```

Expected time: 45 to 120 minutes, depending on the OOS config and warm prepare time.

## 3. Dashboard Reflection Feasibility

Dashboard reflection is possible, but it should not be done blindly from the current dirty state.

| worktree | branch | HEAD | current status |
|---|---|---|---|
| `STOM_V.wt-dev` | `loop/process-research-pipeline` | `f8f4860c` | research checkpoint committed; dashboard 7 files are still locally modified and excluded from research commits |
| `STOM_V.wt-dashboard-remodel` | `feature/dashboard-v4-20260704` | `f5faf53a` | branch has dashboard V4 commits; also has untracked `.omo/evidence/...` and `ai_strategy_loop/dashboard/design-system/` |
| `STOM_V.wt-alpha` | `research/alpha-lab-v2-20260706` | `d2b3c768` | alpha branch has its own research commits; untracked tmap evidence exists |

Branch delta snapshot:

| target | target-only commits | dashboard-only commits | direct reflection status |
|---|---:|---:|---|
| `loop/process-research-pipeline` vs `feature/dashboard-v4-20260704` | 17 | 31 | possible, but expect dashboard file conflicts because `wt-dev` has dirty dashboard frontend files |
| `research/alpha-lab-v2-20260706` vs `feature/dashboard-v4-20260704` | 25 | 31 | possible, but alpha has separate research history and should receive dashboard changes after dev reflection is validated |

## 4. Recommended Order

1. Keep the current Plan D research state frozen at `f8f4860c` plus this planning commit.
2. Do not start the selected OOS page until dashboard reflection is either completed or explicitly deferred.
3. In `wt-dashboard-remodel`, decide whether the untracked `ai_strategy_loop/dashboard/design-system/` and `.omo/evidence/dashboard-v4-*` files are intentional dashboard deliverables. Commit them there if they are required; otherwise leave them untracked and do not propagate them.
4. In `wt-dev`, handle the existing dirty dashboard 7 files before merging dashboard V4. They should be explicitly committed, stashed, or reviewed as local residue. Do not reset or discard them without user approval.
5. Reflect `feature/dashboard-v4-20260704` into `wt-dev` first. Validate dashboard/frontend behavior and run project gates relevant to touched files.
6. Reflect the same validated dashboard changes into `wt-alpha` second. This keeps alpha from becoming the first conflict-resolution surface.
7. After dashboard reflection, return to the Plan D selected OOS command above.

## 5. Safety Rules For Reflection

- Use explicit path staging only; do not use `git add -A`.
- Do not stage runtime DBs, CSV outputs, backup DBs, `.gjc`, or unrelated `.omo` residue.
- Do not overwrite the dirty dashboard 7 files in `wt-dev` without first inspecting and preserving them.
- Prefer merge/cherry-pick commits from `feature/dashboard-v4-20260704` rather than manual file overlays.
- If conflicts occur, resolve only dashboard/frontend conflicts and leave research artifacts untouched unless the conflict requires a documented decision.

## 6. Reflection Command Skeleton

Inspection first:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-dashboard-remodel status --short
git -C C:\System_Trading\STOM\STOM_V.wt-dev status --short
git -C C:\System_Trading\STOM\STOM_V.wt-alpha status --short
```

After dirty-file decisions are made, use a non-fast-forward merge or a controlled cherry-pick series. Do not run this while `wt-dev` dashboard files are dirty unless the dirty files have been intentionally preserved:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-dev merge --no-ff feature/dashboard-v4-20260704
python C:\System_Trading\STOM\STOM_V.wt-dev\scripts\verify_nonrelease_sync.py
git -C C:\System_Trading\STOM\STOM_V.wt-dev diff --check
```

Then repeat for alpha only after `wt-dev` has passed validation:

```powershell
git -C C:\System_Trading\STOM\STOM_V.wt-alpha merge --no-ff feature/dashboard-v4-20260704
python C:\System_Trading\STOM\STOM_V.wt-alpha\scripts\verify_nonrelease_sync.py
git -C C:\System_Trading\STOM\STOM_V.wt-alpha diff --check
```

If either merge reports conflicts, stop and document the conflicting paths before resolving them.
