# Research Naming Taxonomy and Visual Label Rules - STOM Reorganization Page 6

Generated: 2026-06-18T22:45:47+09:00

No existing files are renamed by this task. This taxonomy defines future names, aliases, badges, and migration labels.

## Category Rules

| Category | Machine-Name Pattern | Korean Display Alias Pattern | Badge Text | Badge Color | Promotion Meaning | Example |
|---|---|---|---|---|---|---|
| seed | `seed_<source>_<family>` or existing stable id | `<구조명> 시드` | `SEED` | gray | Baseline/input only; not promoted by itself without OOS. | `r8_4` -> `r8 기준 전략` |
| mutation | `<seed>__mut_<change>__<run>` | `<시드> 변이 <핵심변경>` | `MUTATION` | blue | Train-gate candidate; requires frozen OOS. | anchor best +13.93M candidate |
| OOS | `<candidate>__oos_<period>` or run id | `<별칭> 공식 OOS <기간>` | `OFFICIAL OOS` | green | Official engine evidence; can advance promotion. | `r8_4` 2025Q4 official OOS |
| shadow | `<candidate>__shadow_<reason>` | `<별칭> 비교용` | `SHADOW` | amber | Comparison only; cannot promote alone. | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` -> `11월 제외 비교용` |
| portfolio | `<combo>__portfolio_<rule>` | `<조합> 운용 규칙` | `PORTFOLIO` | teal | Portfolio-layer rule; separate from condition expression. | `exit2_full_after_prior_r8r2_loss_else_off` -> `exit2 월별 ON/OFF` |
| defense rule | `<target>_exclude_<risk>__<defense>` | `<위험요인> 제외 방어` | `DEFENSE` | indigo | Candidate can progress if causal/pre-entry and OOS-confirmed. | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` -> `저시총 제외 방어 조합` |
| docs-only | `<topic>-design-<date>` or update log title | `<주제> 설계/기록` | `DOCS` | slate | Documentation or design, no performance claim. | research-docs auto exposure design |
| blocked | `<candidate>__blocked_<reason>` | `<별칭> 보류` | `BLOCKED` | red | Must not execute until blocker removed. | `backtest.py` exit-rule redesign pending |
| csv reanalysis | `<candidate>__csv_reanalysis_<date>` | `<별칭> CSV 재분석` | `CSV` | purple | Derived from existing OOS CSVs; not final official OOS. | post-Q4 3H bulk candidates |
| dashboard record | `<campaign>_summary` | `<캠페인> 대시보드 카드` | `DASHBOARD` | cyan | Visibility/index proof; not performance proof by itself. | `q4-defense-prerule-halfexit-dashboard-20260618_summary.json` |

## Required Examples

| Internal Name | Display Alias | Category | Badge | Promotion Meaning |
|---|---|---|---|---|
| `r8_4` | r8 기준 전략 | seed / official baseline | `SEED`, `BASELINE` | Baseline and Q4 loss source, not final promoted alone. |
| `exit2_balance` | exit2 방어 | OOS baseline / defense component | `OFFICIAL OOS` | Defensive component with Q4 positive evidence. |
| `r2full_mdd` | r2full MDD 방어 | OOS baseline / defense component | `OFFICIAL OOS` | Recent-regime defensive component. |
| `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 저시총 제외 방어 조합 | defense rule + csv reanalysis | `DEFENSE`, `CSV` | Execution priority 1, official OOS pending. |
| `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 11월 제외 비교용 | shadow / November exclusion shadow | `SHADOW` | Raw score winner but high overfit risk; compare only. |
| `exit2_full_after_prior_r8r2_loss_else_off` | exit2 월별 ON/OFF | portfolio | `PORTFOLIO` | Portfolio-layer validation, not condition expression. |

## Visual Label Rules

| Promotion State | Badge Text | Color | Dashboard Copy Rule |
|---|---|---|---|
| `official_oos_passed` | `OOS PASS` | green | May be considered for promotion only if period/trade count sufficient. |
| `official_oos_failed` | `OOS FAIL` | red | Stop or redesign; preserve evidence. |
| `official_oos_pending` | `OOS PENDING` | amber | Queue item; no promotion language. |
| `csv_reanalysis` | `CSV REANALYSIS` | purple | Show as hypothesis narrowing, not final proof. |
| `shadow_oos_pending` | `SHADOW` | amber | Compare only; never rank as recommendation 1. |
| `portfolio_rule` | `PORTFOLIO RULE` | teal | Explain that it is capital/allocation logic. |
| `docs_only` | `DOCS` | slate | Design or note only; no result badge. |
| `blocked` | `BLOCKED` | red | Show blocker and required unblock condition. |

## Migration Map

| Existing Long Name | Future Display Alias | Migration Action |
|---|---|---|
| `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 저시총 제외 방어 조합 | Add alias in registry/dashboard; do not rename evidence files yet. |
| `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 11월 제외 비교용 | Add shadow badge and overfit warning. |
| `exit2_full_after_prior_r8r2_loss_else_off` | exit2 월별 ON/OFF | Add portfolio-rule badge. |
| `q4-defense-prerule-halfexit-dashboard-20260618` | Q4 방어 연구 카드 | Keep campaign id; show display title separately. |

## Destructive Migration Guard

No rename occurs before:
1. registry alias exists,
2. dashboard renders alias while retaining machine name,
3. raw evidence links remain stable,
4. tests assert both alias and machine name are visible.
