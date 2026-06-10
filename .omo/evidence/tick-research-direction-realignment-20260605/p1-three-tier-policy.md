# P1 Three-Tier Candidate Policy

## Purpose

This policy prevents early overfit rejection from erasing useful research evidence while keeping final proof strict. It replaces a single strict `yearly_sparse_robust_v2` selector with three separate layers.

## Layer 1: Exploration Pool v2

Exploration Pool is loose and OOS-blind. Its job is to keep candidates available for analysis, not to prove quality.

Input:

- 2023-2025 training data only.
- Completed generation records with strategy identity and parseable trade evidence.

Structural rejections only:

- missing buy/sell strategy identity
- missing CSV path
- malformed CSV with no parseable trades
- OOS-year contamination in selector input
- total `trade_count < 10`

Retain candidates even if they fail:

- yearly positivity
- MDD <= 10
- strict trade sufficiency
- PBO/DSR thresholds
- sparse-positive promotion thresholds

Labels:

- `human_like`
- `near_miss`
- `overfit_risk`
- `sparse`
- `mdd_risk`
- `recent_improving`
- `max_hold_unknown`
- `pbo_high`
- `dsr_insufficient`

Max retained candidates: 30.

Sort order:

1. higher training profit
2. lower MDD
3. higher trade_count
4. lower generation number

## Layer 2: Research Pool v2

Research Pool ranks candidates that deserve deeper inspection. It is also OOS-blind.

Input:

- Exploration Pool only.

Retention:

- top 10 by research score
- aggregate `trade_count >= 50` is a ranking preference, not a hard reject
- at least two training years with trades is a ranking preference, not a hard reject

Research score components:

- human morphology score:
  - trade density
  - MDD corridor
  - payoff ratio
  - uptrend R2 or equity smoothness proxy
  - drawdown recovery proxy
  - late-period collapse proxy
  - time-window spread
  - max-hold annotation if reliable
- recent improvement score:
  - `0.2*profit_2023 + 0.3*profit_2024 + 0.5*profit_2025`
  - positive yearly slope annotation
- quant support:
  - variable correlation support
  - feature interaction support
  - feature-importance support
  - BackFinder setup hints
- risk labels:
  - PBO, DSR, and slippage are labels here, not blockers

Human-reference morphology is a research prior only. It is not promotion proof.

## Layer 3: Promotion Gate v2

Promotion Gate is strict. It decides whether a candidate can support a seed/human-level claim. Promotion Gate can select at most one frozen candidate for fixed OOS.

Pre-OOS requirements:

- base sparse-positive quality passes
- aggregate training trades >= 150
- each training year trade_count >= 30
- each training year profit > 0
- aggregate MDD <= 10.0

Fixed OOS requirements:

- OOS 2022 profit > 0
- OOS available 2026 window profit > 0
- combined AI OOS profit >= combined seed OOS profit
- AI max OOS MDD <= seed max OOS MDD
- each AI OOS window trade_count >= 20
- combined AI OOS trades >= 50

Promotion diagnostics:

- slippage-stressed OOS remains positive at 0.1%, 0.2%, and 0.3%
- PBO < 0.20
- DSR > 0
- insufficient PBO or DSR data blocks promotion

## OOS Rules

- Exploration Pool never uses OOS.
- Research Pool never uses OOS for ranking.
- Promotion Gate uses OOS only after one candidate is frozen.
- OOS-after-the-fact reselection is forbidden.
- If no Promotion Gate candidate exists, promotion OOS is skipped by default. Research Pool remains useful evidence.

## Guardrails

- No engine edits.
- No hard-gate relaxation.
- No `backtest/graph` edits.
- No protected path staging.
- No `final_approval`.
- No `export_winner`.
- No live broker, KHOPENAPI, USER_ACK, V3K advancement, or blanket `taskkill`.

## Policy Verdict

This policy weakens early rejection only. It does not weaken final proof.
