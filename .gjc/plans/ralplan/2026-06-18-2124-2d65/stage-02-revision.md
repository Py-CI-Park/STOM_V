# RALPLAN-DR short revision — dashboard branch

## Summary
Keep Option A: clean-worktree, governed research-index-first dashboard branch. Status remains pending approval. This revision addresses Architect review: current branch-base contract, governed schema, `.omo` exposure limits, cache invalidation, and definition of full-audit feature improvement.

## Branch-base contract
Current observed facts for this plan: source `lazycodex/tick-sparse-positive-generation-improvement-20260604` = `67e57525`; local anchor `STOM_Version_2U_C-ai-strategy-loop` = `7d7187f7`; remote anchor `origin/STOM_Version_2U_C-ai-strategy-loop` = `7d7187f7`.

Treat `.omo/evidence/stom-reorg-20260618/branch-map.md` as stale historical evidence only. It records old source `067ef184`, local anchor `84acb6cb`, and absent remote anchor, so it must not be used as current branch truth.

Future execution preflight, before any worktree creation: run `git fetch origin STOM_Version_2U_C-ai-strategy-loop`; verify local and remote anchor both resolve to `7d7187f7`; if either differs, stop and revise this plan. Then create the clean dashboard worktree from `origin/STOM_Version_2U_C-ai-strategy-loop`. Leave dirty `wt-dev` untouched.

## Principles
1. Verify anchor before branching.
2. Protect dirty `wt-dev`; no reset, stash, stage, branch checkout, or worktree mutation there.
3. Full-audit improvement means governed all-record and evidence-lineage lookup.
4. Preserve divergent-by-design surfaces; HoF components stay separate.
5. No V3K, live broker, final approval, strategy export, protected DB, or dependency changes.

## Decision drivers
1. Correct base at `7d7187f7`.
2. Operator value from all-record lookup and evidence lineage.
3. Reviewable bounded branch over broad route/UI consolidation.

## Options
- Option A — chosen: governed research index plus all-record lookup first. Pros: highest value, low regression risk, preserves HoF divergence, easy rollback. Cons: broad route naming audit and generic UI consolidation are deferred.
- Option B: broad dashboard consolidation and route audit. Pros: visible cleanup. Cons: high regression risk and too many surfaces.
- Option C: process-flow-only. Pros: small. Cons: misses all-record lookup and full-audit goal.

## Scope
In scope: new clean branch after anchor preflight; backwards-compatible `/research_records` and `/research_docs`; new governed index or helper route; all-record lookup UI; source authority and canonicality badges; HoF purpose labels only; realtime process node flowchart reflection; incremental speed work.

Out of scope: broad route naming audit, whole-dashboard UI consolidation, generic duplicate-component merger, V3K gates, live runtime, strategy DB/export, `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/`, dependency additions, project-wide gates.

## Governed index schema
Use namespaced stable IDs:
- `campaign:<name>`
- `doc:<repo-rel-path>`
- `update_log:<repo-rel-path>`
- `registry:<machine_name>`

Every row must include `id`, `kind`, `source_path`, `title`, `updated_at`, `canonicality`, `source_authority`, `detail_available`, `tags`, and `related_ids`. `canonicality` values should distinguish canonical, derived, historical, stale, reference, and candidate. `source_authority` should distinguish raw campaign, curated doc, selected update log, registry entry, and historical planning context. Detail lookup must reject traversal, malformed namespace, missing file, and disallowed stale entries. Existing legacy route IDs remain stable; the governed index uses namespaced IDs to avoid collisions.

## `.omo/evidence/stom-reorg-20260618` exposure
Do not expose the directory wholesale. Allow only explicit registry/source-inventory sources, such as `research-registry.json` entries with machine names, mapped `research-registry.md` reference entries, and `research-source-inventory.md` context. Do not index QA screenshots, browser captures, smoke logs, safety snapshots, dirty status dumps, stale branch maps, split strategy files, or planning files as facts. Registry rows may link to raw evidence as lineage, but authority labels must prevent derived or stale notes from overriding raw campaign evidence.

## File-level plan
- `ai_strategy_loop/dashboard/research_records.py`: preserve campaign index/detail behavior; expose safe helpers for index construction.
- `ai_strategy_loop/dashboard/research_api.py`: keep existing docs/records routes stable; add `/research_index` and `/research_index/detail` or equivalent.
- Candidate `ai_strategy_loop/dashboard/research_index.py`: own ID parsing, allowlists, source authority, related IDs, safe paths, and process-local cache.
- `research-records-panel.jsx`, `research-wiki.jsx`: add lookup entry, source badges, related links, inert rendering, lazy details.
- Candidate `research-index-panel.jsx` or utils module if lookup UI would bloat existing files.
- `chart-hall-of-fame.jsx`, `rp-heatmap.jsx`: labels only; never merge Evolution HoF and Research Pro HoF.
- `phase-detail.jsx`: preserve public exports and timing semantics; extract to `process-flow-diagram.jsx` only if realtime work would grow the file.
- Tests: research records/index backend, records frontend, wiki frontend, phase mapping, process flow, duplicate globals, HoF separation.

## Cache and speed contract
Backend cache is process-local only, with no persistent cache writes. Cache key must include root path plus each included source file path, `mtime_ns`, and size. Rebuild on allowlisted file add, remove, `mtime_ns` change, or size change; separate test roots must not share cache results. Tests must cover add, remove, changed mtime/size, and root isolation. Frontend speed work: metadata-only initial response, lazy detail loads, abort stale requests, debounce search, memoized filters, capped initial rows.

## Sequencing
1. Preflight fetch and verify local plus remote anchor SHA equals `7d7187f7`; stop on mismatch.
2. Create future clean worktree branch from `origin/STOM_Version_2U_C-ai-strategy-loop`; protect dirty `wt-dev`.
3. Baseline focused checks in the clean worktree.
4. Implement backend governed index and allowlist while preserving legacy routes.
5. Implement all-record lookup, related IDs, and source/canonicality badges.
6. Add HoF labels only.
7. Extract process-flow helpers only if needed for realtime flow.
8. Add process-local cache and tests.
9. Run focused verification; PR remains pending explicit user approval.

## Acceptance criteria
- Anchor preflight verifies local and remote `7d7187f7`; stale `.omo` branch-map is not current truth.
- Dirty `wt-dev` remains untouched.
- Legacy docs/records routes remain compatible.
- Governed index returns namespaced IDs and required fields.
- `.omo` exposure is allowlisted and does not promote screenshots, logs, stale branch maps, or planning files as facts.
- All-record lookup covers campaigns, docs, selected update logs, and allowlisted registry entries with related IDs.
- HoF remains separate and purpose-labelled.
- Realtime process flow reflects current node and timings without bloating `phase-detail.jsx`.
- Cache invalidates on file add/remove/mtime/size and writes no persistent files.

## Verification for future execution only
Focused commands: `pytest tests/unit/dashboard/test_research_records.py -q`; `pytest tests/unit/dashboard/test_research_records_frontend.py -q`; `pytest tests/unit/test_dashboard_wiki_frontend.py -q`; `pytest tests/unit/test_dashboard_phase_mapping.py tests/unit/dashboard/test_p11_process_flow.py -q`; `pytest tests/unit/dashboard/test_no_duplicate_globals.py -q`; `cd ai_strategy_loop/dashboard/webui-build; node build-app.mjs`; `node check-missing-imports.mjs`; `node track-z-harness.mjs`. Manual smoke: `/ui/`, `/research_records`, `/research_docs`, `/research_index`, `/research_index/detail`, `/evolution_gui_parity?run_id=&gen_no=-1`, process tab iframe. Skip project-wide build/test/lint/format gates.

## Rollback
Revert only feature-branch commits. If index fails, hide new lookup and keep legacy routes. If `.omo` allowlist is wrong, remove `.omo` rows rather than widening exposure. If process extraction fails, revert extraction and keep existing panel. If HoF labels fail, revert labels only, never merge HoF components.

## Status
Pending approval. No source edits, branch/worktree creation, commit, push, PR, test/build/lint/format gate, or execution delegation is authorized.
