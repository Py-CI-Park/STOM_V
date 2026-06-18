# Draft: Tick Human-Like Research Criteria And Dashboard Plan

## Requirements
- OOS/OOS-like validation meaning must be explained in plain Korean.
- Treat user-written `OSS` as `OOS` unless explicitly corrected.
- OOS must be optional for discovery research: allow `research_oos_mode=disabled` when OOS blocks useful exploration too early.
- Overfit criteria should be relaxed for research: every year does not need to be profitable if the full equity curve is upward.
- Prefer 2024, 2025, and available 2026 results because recent market behavior matters more.
- Study buy strategies over `09:00..09:20` or `09:00..09:30`, split by 5-minute time buckets and market-cap bands.
- Generate buy strategies using existing buy strategy forms as references.
- Generate sell strategies using existing sell strategy forms and cover the broader holding/sell window.
- Increase trade count while seeking maximum upward cumulative return.
- Dashboard should always be active and should show active buy/sell strategy code, diff, current AI prompt, and prompt/code history above or near the fitness trend.
- Backtest CSV analysis should be strengthened.
- Analyze variable correlations, compound relationships, and time bucket x market cap x variable effects on returns.
- Persist analysis results in DB for later use and dashboard visualization.
- Explain difficult terms such as edge ratio directly in the dashboard.
- Accept that most condition edits do not improve results; the purpose is research and discovery, not guaranteed improvement each run.
- Consider daily profit/loss reality: more profitable days, or lower win-rate with larger payoff, can both be valid.

## Technical Decisions
- Use two-tier validation:
  - `research_continue`: loose, human-like, upward aggregate curve criteria.
  - `promotion_claim`: strict, still requires fixed OOS, slippage, PBO/DSR/advisory checks, and no final/export without approval.
- Add OOS modes:
  - `disabled`: no OOS rejection; research-only discovery.
  - `advisory`: show OOS if available, but do not reject research families solely from it.
  - `promotion_only`: fixed OOS only after a candidate is frozen for seed/human-superiority review.
- Keep official engines, hard gates, `backtest/graph`, final/export/live/V3K paths unchanged.
- New criteria, generation modes, analysis persistence, and dashboard panels must be config-gated and default OFF unless they are pure read-only UI explanations.
- Use 5-minute buy windows: `09:00..09:05`, `09:05..09:10`, `09:10..09:15`, `09:15..09:20`, optional `09:20..09:25`, `09:25..09:30`.
- Time baseline and market-cap bands are dynamic: start with `09:00..09:20`, optionally extend to `09:30`, and adjust bands from DB/segment evidence.
- Before long runs, fix or ablate the current C_T buy first-branch timeout blocker.

## Research Findings
- Current dashboard is active at `http://127.0.0.1:8770/ui/`.
- Latest OMO diagnosis isolated C_T timeout to `C_T_900_920_U2_B` buy side, pre-`09:05` branch.
- Prior fixed 2022/2026 OOS rejected the sparse-positive candidate, but that should be interpreted as strict promotion rejection, not research dead-end.
- For this plan's first exploratory run, OOS can be disabled and must be labeled as research-only.
- Existing system already has prompt persistence, strategy diff/code APIs, analysis endpoints, and run DB foundations.

## Scope Boundaries
- INCLUDE: plan for criteria change, generation expansion, dashboard visibility, analysis DB, glossary/tooltips, bounded verification.
- EXCLUDE: immediate source implementation, production strategy DB export, live broker, final approval, V3K gate advancement.

## Open Questions
- Default assumption: use `09:00..09:20` as first research window, with `09:20..09:30` optional after bounded preflight.
- Default assumption: relax yearly-positive and OOS requirements only for research continuation, not for final human-superior claim.
