# Evidence Lineage and Drift Guard Rules - STOM Reorganization Page 7

Generated: 2026-06-18T22:45:47+09:00

## Goal

Every future research campaign must be reproducible from preregistration to dashboard card, with raw evidence separated from derived summaries and narrative claims.

## Mandatory Campaign Files

| Stage | Required File | Class | Source of Truth | Notes |
|---|---|---|---|---|
| preregistration | `.omo/evidence/<campaign>/preregistration.md` or `.omo/evidence/tmap-walkforward/<campaign>_preregistration.md` | narrative plan | yes for intent | Must define hypothesis, period, inputs, stop conditions, expected dashboard label. |
| raw run stream | `.omo/evidence/<campaign>/<campaign>.jsonl` | raw evidence | yes for candidate rows | Candidate events must include label, round, gate, profit, mdd, trades where available. |
| summary | `.omo/evidence/<campaign>/<campaign>_summary.json` | derived summary | no | Must be reproducible from raw jsonl or cited raw JSON/CSV. |
| log | `.omo/evidence/<campaign>/<campaign>_log.txt` | execution log | yes for command trace | Include commands, timestamps, warnings, timeout info. |
| official OOS result | `.omo/evidence/<campaign>/<candidate>_official_oos.json` or existing OOS JSON path | raw/derived official result | yes for promotion | Must identify official engine/config, period, run_id, gate, CSV path. |
| dashboard card | `.omo/evidence/tmap-walkforward/<campaign>_summary.json` plus optional `.jsonl` | dashboard index | no | Must not be the only performance proof. |
| update_log | `docs/update_log/YYYY-MM-DD_<campaign>.md` | narrative report | no | Must cite raw files and distinguish official OOS from CSV reanalysis. |
| registry entry | `.omo/evidence/stom-reorg-20260618/research-registry.json` or successor | canonical index | no | Index only; raw evidence remains source of truth. |
| promotion decision | `.omo/evidence/<campaign>/<candidate>_promotion_decision.md` | decision record | yes for decision | Must say promote, reject, shadow, blocked, or continue. |

## Evidence Class Distinctions

| Class | Can Support Promotion? | Required Label |
|---|---|---|
| raw official OOS | yes, if period/trades/MDD sufficient | `OFFICIAL OOS` |
| raw jsonl candidate stream | no by itself | `TRAIN/SEARCH` |
| CSV reanalysis of completed OOS | no by itself | `CSV REANALYSIS` |
| portfolio aggregation | no condition-expression promotion by itself | `PORTFOLIO RULE` |
| dashboard summary | no by itself | `DASHBOARD` |
| narrative update_log | no by itself | `REPORT` |
| design note | no | `DOCS` |
| blocked/deferred note | no | `BLOCKED` |

## Drift Check Design

Run before any registry update or promotion claim:

```powershell
python -m json.tool .omo/evidence/tmap-walkforward/<campaign>_summary.json
Get-Content .omo/evidence/tmap-walkforward/<campaign>.jsonl | % { $_ | ConvertFrom-Json } | Measure-Object
Select-String -Path docs/update_log/YYYY-MM-DD_<campaign>.md -Pattern '<candidate>|official OOS|CSV 재분석|promotion'
```

Required comparisons:

| Check | Pass Condition | Failure Action |
|---|---|---|
| summary parses | `python -m json.tool` exit 0 | mark campaign `blocked:summary_parse_error`; do not promote. |
| jsonl parses | every nonblank line parses | create repair task; do not update dashboard card from broken rows. |
| candidate count | summary `rounds`/candidate count agrees with jsonl or explains why not | mark drift and repair summary. |
| best candidate | summary best exists in raw jsonl or cited source JSON | mark `summary_drift`; regenerate summary from raw. |
| official OOS label | narrative distinguishes official OOS from CSV reanalysis | fix report labels before dashboard exposure. |
| registry metrics | registry values match cited source file | block registry commit until corrected. |

## Drift Response

When summary and jsonl disagree:

1. Do not delete old summaries.
2. Add `drift_detected` note to the campaign's registry entry.
3. Create a repair artifact: `.omo/evidence/<campaign>/drift-repair-YYYYMMDD.md`.
4. Regenerate derived summary only from raw jsonl/official JSON/CSV.
5. Re-run dashboard `/research_records` check.
6. Update update_log with "drift repaired" or "drift unresolved".

## Promotion Gate

A candidate can move from queued to promoted only when:

1. preregistration exists,
2. official OOS raw result exists,
3. summary/jsonl drift check passes,
4. dashboard card is visible,
5. registry entry has alias, evidence type, OOS status, promotion status,
6. stop conditions are evaluated,
7. promotion decision file exists.

## Stop Conditions

Stop or block promotion if:

- official OOS fails gate,
- MDD cap fails,
- trade count is insufficient,
- annualized return is based on too short a period without warning,
- raw score advantage comes from a high-overfit calendar exclusion,
- summary drift is unresolved,
- branch attribution is unknown for an AND/OR candidate,
- candidate requires live/V3K/protected path work.

Cleanup receipt:
- Rules only; no old summaries deleted and no repair task executed in this Page 7 work.
