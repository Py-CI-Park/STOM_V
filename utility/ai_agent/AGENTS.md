# AI AGENT STRATEGY TEXT KNOWLEDGE BASE

## OVERVIEW
`utility/ai_agent/` is the branch-local text workspace for STOM condition-expression generation. It contains the source examples and rules that must be read before generating strategy syntax.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Strategy examples | `strategy.txt` | Existing branch-local strategy text format. |
| Generation rules | `rules.txt` | Syntax/constraint rules for generated conditions. |
| Generated outputs | this directory | Save generated strategies here unless a task says otherwise. |

## CONVENTIONS
- Read `strategy.txt` and `rules.txt` before writing generated STOM syntax.
- Generate in the branch-local text format; do not invent a new schema.
- Keep generated strategy artifacts reviewable and named clearly.
- If using AI loop/research results, distinguish evidence-backed changes from hypotheses.

## ANTI-PATTERNS
- Do not write generated strategy text into production DBs from here.
- Do not use result/label leakage variables as condition inputs.
- Do not bypass human review or dashboard/final approval boundaries.

## LOCAL GOTCHAS
- This directory is for text-format strategy generation, not a runtime database.
- Keep generated files human-readable; include enough context to review the condition.
- If a strategy comes from a backtest/research result, name the source run or report.
- Do not overwrite `strategy.txt` or `rules.txt` casually; they are source references.
- Avoid mixing multiple unrelated generated strategies into one file.
- Generated text should still pass the relevant STOM syntax/contract expectations.
- When uncertain, save a new clearly named artifact rather than editing canonical examples.
- Keep buy/sell condition sections distinguishable.
- Do not encode approval-gated V3K live behavior in generated text.
- Review generated output for variable leakage before using it in research loops.
- Avoid committing temporary scratch output unless the task asks for a durable artifact.
- Pair strategy-generation work with an explanation of the intended edge hypothesis.
