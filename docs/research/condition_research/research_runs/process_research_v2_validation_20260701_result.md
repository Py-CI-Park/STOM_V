# Improved Process Research Validation Result — process_research_v2_validation_20260701

## Executive summary

개선된 조건식 연구 프로세스를 research-only로 실제 실행했다. 이번 실행은 **즉시 승격 목적이 아니라** 다음 항목이 실제로 연결되는지 검증했다.

- full parent buy/sell condition code + sha256 기반 Context Pack
- STOM source/rule assets 포함
- Analysis Card v2
- 2 repair + 2 discovery multi-hypothesis candidate pack
- strict validation
- 64-engine official full-period replay/backtest
- prompt/backtest/safety/dashboard receipts
- 연구 계획서/관리 보고서/결과 보고서

## Boundary

| Item | Value |
|---|---|
| process | `process-research` |
| preset | `research` |
| export | `False` |
| live | `False` |
| finalPromotion | `False` |
| slippage | `3_tick_advisory_only` |
| engine | `64` |
| fallbackUsed | `False` |
| baselineCsv | `backtest/csv\stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701170259.csv` |
| contextPack | `artifacts/process-research-validation-20260701/research_context_pack.json` |

## Baseline official result

| Profit KRW | MDD % | Trades | Daily | Win % | TPI |
|---:|---:|---:|---:|---:|---:|
| 518,822 | 20.54 | 175 | 0.7 | 52.57 | 1.13 |

## Candidate official results

> Note: candidate expressions are **reject filters** inserted into the parent buy strategy as `if <expression>: 매수 = False`. For example, `등락율 >= 7.2` means “reject overextended entries,” not “buy only overextended entries.”


| Candidate | Reject filter expression | Profit KRW | ΔProfit | MDD % | ΔMDD | Trades | Win % |
|---|---|---:|---:|---:|---:|---:|---:|
| `prv2_20260701_e64__cand001` | `시가총액 < 700 and 등락율 < 3.0` | 518,822 | +0 | 20.54 | +0.00 | 175 | 52.57 |
| `prv2_20260701_e64__cand002` | `체결강도 < 120` | 419,904 | -98,918 | 14.68 | -5.86 | 121 | 51.24 |
| `prv2_20260701_e64__cand003` | `등락율 >= 7.2` | -25,668 | -544,490 | 12.56 | -7.98 | 55 | 43.64 |
| `prv2_20260701_e64__cand004` | `거래대금증감 < -5_000_000_000` | 439,000 | -79,822 | 5.0 | -15.54 | 36 | 66.67 |

## Quant interpretation

| Finding | Interpretation |
|---|---|
| Best MDD candidate | `prv2_20260701_e64__cand004` / `거래대금증감 < -5_000_000_000` achieved MDD 5.0%, ΔMDD -15.54p vs baseline. |
| Best profit candidate | `prv2_20260701_e64__cand001` / `시가총액 < 700 and 등락율 < 3.0` had the highest candidate profit 518,822 KRW. |
| Trade-off | Lower MDD candidates also reduced trades/profit. This is a useful promotion-review queue signal, not final proof. |
| Process result | The improved process successfully produced multiple distinct hypotheses and official receipts. |

## Next research queue

1. Keep `거래대금증감 < -5_000_000_000` as a risk-control branch candidate for fresh/frozen holdout review because MDD dropped sharply, but do not promote.
2. Re-test `체결강도 < 120` with a less aggressive threshold ladder because it reduced MDD while preserving more trades than candidate 004.
3. Reject or deprioritize `등락율 >= 7.2` as too aggressive for this seed: profit turned negative despite MDD improvement.
4. Treat `시가총액 < 700 and 등락율 < 3.0` as near-baseline/no-op for this 2025 sample because metrics matched baseline-level behavior.
5. Next iteration should generate threshold ladder candidates around turnover-decay and strength filters, still one-axis per branch.

## Artifact map

| Artifact | Path |
|---|---|
| Context Pack | `artifacts/process-research-validation-20260701/research_context_pack.json` |
| Candidate cards | `artifacts/process-research-validation-20260701/candidate_cards.jsonl` |
| Analysis cards | `artifacts/process-research-validation-20260701/analysis_cards.jsonl` |
| Prompt receipts | `artifacts/process-research-validation-20260701/prompt_mutation_receipts.jsonl` |
| Backtest receipts | `artifacts/process-research-validation-20260701/full_period_backtest_receipts.json` |
| Engine fallback receipt | `artifacts/process-research-validation-20260701/engine_fallback_receipt.json` |
| Safety receipt | `artifacts/process-research-validation-20260701/safety_receipt.json` |
| HTML report | `artifacts/process-research-validation-20260701/process_research_validation_report.html` |

## Caveat

This run validates the improved process and finds risk-control branches. It does **not** authorize export, live trading, or final promotion. Any candidate with better risk profile must go through zero-generation promotion-review with frozen/fresh holdout, OOS/WF, slippage advisory, and evidence-health review.
