# Expansion Log

## Wave 0

- Core question: 왜 최근 조건식 실험이 실패했고, AI loop가 목적에 맞게 창의적·데이터 기반으로 학습하지 못하는지, 사람 Hall of Fame과의 차이를 포함해 무엇을 어떻게 고쳐야 하는가.
- Axes: handoff/chronology, original purpose/history, runtime architecture, generation grammar/prompts, data lineage/leakage, quantitative results, Hall of Fame comparability, state DB, statistical methodology, dashboard truthfulness, git history, agent sessions, external primary research, red-team countercauses.
- Codebase relevant: yes.
- External research: yes, primary sources only.
- Verification likely: yes.
- Final format: Korean Markdown synthesis plus self-contained HTML report if evidence converges.

## Wave 1 — runtime and experiment identity

- Expanded from v2 outcomes into controller, CLI research, GA, capability gates, export binding, current state, and HOF projection.
- Corrected the initial overbroad “context pack has no consumer” claim: it has a real CLI research consumer, but not the latest batch or ordinary controller generation.
- Eliminated gate strictness, low frequency, tail-only loss, report parsing, and global engine non-output as sufficient causes.

## Wave 2 — cross-ref history and reproducibility

- Followed context-review lead into `git log --all`; found and reconciled sibling `585051e` rather than treating the current branch handoff as repository-global latest.
- Persisted HOF DB filter/hash/run-id receipt and v2 AST/source-hash receipt after reviewers challenged terminal-only evidence.
- Separated observed screen/DB metric gap from unproven human-versus-AI development-system alpha gap.
- Final convergence: no further source search changed the bounded causal verdict or the design-only safety recommendation.
