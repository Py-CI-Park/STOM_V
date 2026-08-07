# Verification - Condition Self-Improvement Score Rereview (2026-06-17)

## Deliverables
| File | Status |
|---|---|
| `.omo/evidence/condition-self-improvement-score-rereview-20260617/source_delta.md` | created |
| `.omo/evidence/condition-self-improvement-score-rereview-20260617/score_matrix.json` | created |
| `.omo/evidence/condition-self-improvement-score-rereview-20260617/improvement_plan.md` | created |
| `docs/update_log/2026-06-17_condition_self_improvement_score_update.md` | created |

## Automated Checks
| Check | Result |
|---|---|
| JSON parse | `JSON_OK` |
| Score math | `BAD=[] AVG=68 PREV=56 REC=68 DELTA=12 ROWS=12` |
| Report section/table check | required terms present; markdown table count = 9 |
| `$start-work` recommendation search | section and two commands present |
| Focused pytest | `81 passed in 8.84s` |
| `git diff --check` | exit 0; LF/CRLF warnings only |
| Protected path status | empty output |

## Focused Test Command
```powershell
python -m pytest tests/unit/test_feedback_toggles_on.py tests/unit/test_grid_refine.py tests/unit/test_lift.py tests/unit/test_mutator.py tests/unit/test_p5_exit_forensics.py tests/unit/test_research_presets.py tests/unit/test_backtest_timeseries.py tests/unit/test_tmap_autopsy_loop.py -q -p no:cacheprovider
```

## Findings Verified
| Finding | Verification |
|---|---|
| Overall score 56% -> 68% | `score_matrix.json` math check |
| OOS proof still 0 | `full_stateful_n40_summary.json` has empty `promising`; report states OOS pending |
| Anchor mutation train-gate best | `ovn_anchor_summary.json` and `ovn_anchor.jsonl` show +13,928,386 / MDD 9.62 |
| t2late evidence drift | `ovn_t2late.jsonl` has +10,582,342 best while `ovn_t2late_summary.json` says best null |
| Champion positive control | `champion_diag_discovery.log` shows 4/4 gate=True |

## Dirty Worktree Handling
| Category | Result |
|---|---|
| Pre-existing dirty/untracked code/evidence/templates/docs | preserved |
| Files created by this work | this evidence folder, new 2026-06-17 update doc, new plan |
| State files touched | `.omo/boulder.json`, `.omo/start-work/ledger.jsonl` |

## Adversarial QA
| Class | Result |
|---|---|
| malformed input | JSON parse and score math checks passed |
| prompt injection | Not applicable; no LLM prompt execution |
| cancel/resume | Boulder active work used with `codex:` session id |
| stale state | Latest docs/evidence/source deltas were reread before scoring |
| dirty worktree | Existing dirty worktree preserved and separated |
| hung or long commands | No long backtest/LLM run; focused pytest completed |
| flaky tests | Focused tests reran and passed 81/81 |
| misleading success output | Report explicitly says OOS proof remains 0 and train-gate is not final success |
| repeated interruptions | State recoverable from Boulder, ledger, plan, evidence files |

## Cleanup
| Resource | Receipt |
|---|---|
| Runtime processes | none spawned |
| Temp dirs | none created |
| Browser/server/tmux | none spawned |
| Protected DB | not touched |

## Closeout
| Check | Result |
|---|---|
| Boulder JSON | `BOULDER_JSON_OK` |
| Ledger JSONL | `LEDGER_JSONL_LINES=230 BAD=[]` |
| Top-level unchecked plan boxes | `UNCHECKED_TOP=0` |
| Boulder active work | cleared; work marked completed |
