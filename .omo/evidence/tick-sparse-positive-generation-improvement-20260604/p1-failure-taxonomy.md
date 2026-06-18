# P1 Failure Taxonomy

## Source
- Prior run: `tick_sel_sparse_p4_train_2023_2025_20260604`
- Canonical artifact: `.omo/evidence/tick-selection-rule-sparse-gen5-research-20260604/p4-selector-blocked.md`
- Selector: `sparse_positive_v1`
- Prior verdict: `NEEDS_MORE_EVIDENCE`
- Prior selection: `selected=false`, `eligible_candidates=0`, `oos_excluded=true`

## Failure Classes

### 1. Timeout or Missing CSV
- gen0: `backtest failed/timeout`, metrics CSV absent.
- gen3: backtest completed without metrics CSV.
- Policy implication: prompt guidance cannot treat missing metrics as a candidate; these rows remain non-candidates.

### 2. Negative Profit
- gen1: profit `-35,206,257`
- gen2: profit `-1,945,943`
- gen4: profit `-2,153,502`
- gen5: profit `-353,764`
- Policy implication: new generation guidance must target positive training profit, but this is advisory only and cannot override selector rejection.

### 3. High MDD
- gen1: MDD `167.56`
- gen2: MDD `43.76`
- gen4: MDD `39.05`
- gen5: MDD `13.4`
- Policy implication: new generation guidance must explicitly steer toward MDD <= 10 before any OOS is considered.

### 4. Overtrade
- gen1: `4212` trades and daily average `5.8`, with severe MDD.
- gen2/gen4: about `687-688` trades with negative profit and high MDD.
- Policy implication: buy-side guidance must discourage high-frequency overtrading and target the `20-250` trade_count corridor.

### 5. Sparse but Still Negative
- gen5 has `111` trades and payoff ratio `1.7467`, but profit is negative and MDD is above the sparse-positive target.
- Policy implication: sparse shape alone is insufficient. The prompt must combine sparse entry, positive profit, MDD control, and payoff quality.

## Non-Relaxation Guardrail
This taxonomy is not a selector change, hard gate change, or final promotion criterion. It is a pre-source-change diagnosis that explains why a default-OFF generation prompt toggle is being added. OOS rows, 2022 metrics, and 2026 metrics are not used here.
