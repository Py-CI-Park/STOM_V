# Post-Q4 3H Bulk Research

## TL;DR
> **Summary**: Reanalyze completed official OOS CSVs in bulk to select the next official OOS and implementation candidates after the 2025 Q4 stress failure.
> **Deliverables**: baseline registry, exit2 allocation grid, r8 pre-entry filter grid, combined candidate scoreboard, official OOS recommendations, hourly progress record, dashboard campaign record, research journal.
> **Effort**: Medium research batch.
> **Parallel**: Root-process only in this harness; no subagent tools are available.
> **Critical Path**: baseline -> rule grids -> combined scoring -> dashboard/journal -> verification.

## Context
### Original Request
The user asked to directly plan and proceed, report every hour with research purpose and performance, and provide final tables.

### Scope
- Use completed official OOS CSV/JSON artifacts only.
- Do not generate new trading conditions in this plan.
- Do not modify `backtest.py`, live trading paths, V3K gate state, or protected runtime paths.
- Treat entry-time filters as deployable candidates and post-exit/stock-name cuts as diagnostic unless a causal prior-lookback rule is explicitly defined.

## Work Objectives
### Core Objective
Reduce the next research search space by ranking robust, causal, evidence-backed candidates for official OOS verification.

### Definition of Done
- JSON artifacts parse successfully.
- Research journal is written in UTF-8 with readable Korean.
- Dashboard Research Records can see the campaign.
- Protected/runtime paths and `*.db` are not modified by this plan.
- Boulder state is completed and no top-level checkboxes remain unchecked.

## TODOs
- [x] 1. Prepare plan/Boulder state, source registry, and hourly progress ledger.
- [x] 2. Build normalized trade dataset and baseline portfolio metrics from completed annual and Q4 OOS CSVs.
- [x] 3. Run bulk `exit2_balance` allocation rule grid across all/recent/Q4 segments.
- [x] 4. Run bulk `r8_4` pre-entry filter grid and separate diagnostic-only loss cuts.
- [x] 5. Run combined r8-filter plus exit2-allocation candidate grid.
- [x] 6. Score candidates and select official OOS/implementation recommendations.
- [x] 7. Write research journal and dashboard campaign record.

## Final Verification Wave
- [x] F1. Validate JSON artifacts, dashboard visibility, journal encoding, protected paths, process cleanup, and Boulder completion.

## Expected Artifacts
- `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-baseline-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-rule-grid-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-r8-filter-grid-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-combined-candidates-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-hourly-progress-20260618.jsonl`
- `.omo/evidence/tmap-walkforward/post-q4-3h-duration-20260618.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-research-20260618_summary.json`
- `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-research-20260618.jsonl`
- `.omo/evidence/tmap-walkforward/post-q4-3h-bulk-research-20260618_log.txt`
- `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md`

## Acceptance Notes
- Hourly reporting is recorded in the progress JSONL. If the whole batch finishes before one hour, record start and completion checkpoints instead of fabricating hourly updates.
- Annualized return must be included for candidate comparison.
- The final report must explain the research purpose in plain Korean and include elapsed time per step.
