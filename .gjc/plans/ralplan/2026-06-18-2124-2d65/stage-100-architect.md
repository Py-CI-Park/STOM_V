## Summary
The G001 readout satisfies the requested architecture/product/code quality gate. The paired Markdown/JSON artifacts consolidate the existing combined portfolio simulation with the new official OOS entry-filter result, keep evidence taxonomy explicit, and avoid production/export or pure official buy/sell OOS overclaims.

## Analysis
Spec compliance is clear. `.gjc/ultragoal/goals.json` defines G001 as consolidating `r8_exclude_cap_lt_1500 + exit2 prior-month allocation` with the new official OOS entry-filter result, requiring method, inputs, caveats, exact Korean numbers, and clarification that the combined simulation is portfolio-layer reanalysis rather than a pure official buy/sell OOS pair. The readout JSON lists the required inputs (`official_entry_filter_summary`, `combined_candidate_source`, `portfolio_rule_source`, `decision_card`) and taxonomy; the Markdown presents Korean sections for purpose, evidence type, official OOS standalone result, combined simulation result, interpretation, conclusion, and next recommendation.

The official OOS entry-filter evidence is correctly incorporated: `post-q4-r8-lowcap-official-oos-summary-20260619.json` records Q4 profit 310,886 KRW, Q4 MDD 9.25%, 19 Q4 trades, aggregate 2022-2025 + 2026 YTD profit 7,292,861 KRW, 263 aggregate trades, max MDD 19.09%, all gates passed, and 2026 ending at 2026-02-28. The readout repeats these numbers and caveats 2026 as YTD rather than full-year.

The combined portfolio simulation evidence matches the source candidate in `post-q4-3h-combined-candidates-20260618.json`: total profit 39,402,438 KRW, daily realized MDD 7.6823%, 1,073 trades, annualized return 38.6826%; recent 2025-2026 profit 6,941,830 KRW, MDD 12.6478%, 322 trades; 2025 Q4 profit 952,502 KRW, MDD 11.3583%, 67 trades; yearly profits 2022 6,560,023, 2023 14,757,205, 2024 11,143,380, 2025 5,728,090, 2026 YTD 1,213,740 KRW. The portfolio rule context preserves the causal prior-month exclusion method and changed months.

Architecture boundaries are explicit and maintainable. The readout separates entry-filter official OOS, portfolio rule, and combined CSV/portfolio reanalysis, which prevents conflating validation layers. It also states the combined result is not production/export approval and recommends a fresh exact combined portfolio simulation before any promotion discussion.

Code/data quality is acceptable for a read-only evidence artifact review. JSON and Markdown are consistent on the core numbers and caveats. No tests, linters, formatters, project-wide commands, source edits, or Ultragoal checkpoints were run.

## Root Cause
No defect identified. The primary risk for this kind of artifact is evidence-layer conflation; the report mitigates that by explicitly classifying official OOS versus portfolio-layer reanalysis and by denying production/export approval.

## Findings
None.

## Recommendations
1. Approve G001 quality gate as research readout complete.
2. Keep the current `combined_research_supported_not_production_ready` conclusion.
3. Before any production/export or final promotion decision, run the separately proposed fresh exact combined simulation from official CSVs and carry forward the same evidence taxonomy.
4. Optional non-blocking polish: if the Markdown is intended to stand alone without the JSON, add the explicit source artifact paths there as an input table.

## Architectural Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
- Current paired JSON+Markdown readout: sufficient for G001, compact, evidence-backed, no production overclaim.
- Fresh exact combined simulation from official CSVs: stronger for promotion/export decisions, but outside G001 and correctly deferred.
- Treating combined simulation as pure official OOS: rejected because it would collapse portfolio-layer reanalysis into official buy/sell validation and overstate evidence strength.
