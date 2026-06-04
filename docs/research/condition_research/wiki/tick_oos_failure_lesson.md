# Tick OOS Failure Lesson

This note records the current TICK OOS lesson from the 2026-06-03 validation work.

## Current Verdict

Final evidence says `REJECT_CANDIDATE`. The selected AI candidate was generation 4 from `tick_oos_p2_train_2023_2025_20260603`, but it was training-negative and gate-false before OOS.

## What Failed

The AI candidate made profit in 2022 OOS but remained far below the Tick_902 seed result. It was negative in 2026 OOS. Combined OOS profit was far below the seed combined result, so it failed the fixed seed-superiority rule.

## Why This Matters

The loop infrastructure, dashboard analysis, strategy diff, prompt metadata, and OOS execution all worked. The research candidate did not prove human-level or seed-superior condition generation. This distinction matters: infrastructure success is not strategy success.

## Lessons

1. A short-window or training-window graded score cannot override OOS.
2. Segment feedback must be visible in prompt logging before claiming it affected generation.
3. Low drawdown is not enough when combined final profit and OOS sign fail.
4. PBO and DSR remain advisory blockers until implemented and run.
5. BackFinder and band seeds are hypothesis tools; they need forward-only validation.

## Next Experiments

Run a toggles-ON multiyear tick campaign with explicit segment feedback evidence, bounded time dispersion, few-shot seed examples, and direct 2022/2026 OOS comparison against Tick_902. Keep engine, hard gate, and graph code unchanged.
