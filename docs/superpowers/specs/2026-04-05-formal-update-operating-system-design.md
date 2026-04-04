# Formal Update Operating System Design

**Date:** 2026-04-05
**Scope:** the long-term operating system for official version intake, downstream propagation, blocker handling, carry-forward recording, and documentation responsibilities across `STOM_Version_2`, `2U`, `2U_C`, `CLI_v267`, and `research/init`
**Out of Scope:** executing a specific new version wave in this document; replacing the existing directory layout; collapsing branch-local behavior into a single generic rule

## Goal

Define a durable operating system for how official STOM versions should be received, propagated, documented, audited, corrected, and remembered across the entire branch/worktree chain.

The purpose of this design is not only to make the current cycle understandable. The purpose is to ensure future official versions can be applied repeatedly with increasing consistency, less improvisation, and clearer reasoning when branch-local behavior must diverge from blind upstream parity.

## Why This Is Needed

Recent work exposed that the project now has a real multi-stage operational lifecycle:

- release intake on `STOM_Version_2`
- downstream propagation through `2U -> 2U_C -> CLI_v267 -> research/init`
- baseline documentation before propagation
- blocker audit when newly touched surfaces turn red
- branch-local corrective fixes where needed
- carry-forward classification for known but intentionally deferred issues
- protected result-data handling (`backtest/graph/`)

Without a clear operating system, each new version wave would require rediscovering:

- which branch is authoritative
- which branch is merely downstream
- which files/behaviors are protected locally
- when to stop propagation
- what to document versus what to fix

## Design Principles

1. **Official versions enter only through `STOM_Version_2`.**
2. **Version boundaries remain explicit.**
3. **Downstream branches are stabilization layers, not disposable mirrors.**
4. **Newly touched red gates require blocker audit before continuing.**
5. **Untouched red gates may be carried forward, but only with written justification.**
6. **Documentation is part of the operating procedure, not an afterthought.**
7. **`AGENTS.md` and `CLAUDE.md` must act as execution entrypoints into the operating system.**

## Canonical Branch Model

### Release ingress

- `STOM_Version_2`

Role:

- authoritative official intake lane
- only branch allowed to receive official upstream versions directly

### Downstream chain

1. `STOM_Version_2U`
2. `STOM_Version_2U_C`
3. `STOM_Version_2U_C_CLI_v267`
4. `research/init`

Role:

- each branch consumes the completed version result of its parent
- each branch preserves its own verified local behavior where required

## Operational Lifecycle

The operating system is a repeating lifecycle:

### Phase 1: release intake

On `STOM_Version_2`:

- check real upstream freshness
- identify the next official version boundary from `_update.txt`
- apply one version at a time
- commit as `STOM Vx.y`
- use the full matching `_update.txt` section as the commit body

### Phase 2: downstream baseline check

Before a downstream wave begins:

- confirm branch/worktree state
- confirm local baseline notes are present and current enough to guide conflict handling
- confirm protected non-git data is identified

### Phase 3: version-wave propagation

For one version at a time:

- `2U`
- `2U_C`
- `CLI_v267`
- `research/init`

Do not advance to the next version until the full chain has either:

- passed, or
- been explicitly paused by blocker audit

### Phase 4: blocker audit

If a newly touched verification surface turns red:

- stop the wave
- isolate the exact failing contract surface
- classify the problem as one of:
  - real propagation break
  - intentional release-side change
  - unresolved ambiguity requiring narrower design

### Phase 5: branch-local corrective fix

If the blocker audit concludes a real propagation break exists:

- fix upstream-most affected downstream branch first
- verify that branch fully
- apply the minimum corresponding fix in lower affected branches if needed

### Phase 6: carry-forward recording

If a problem remains intentionally unfixed:

- record it explicitly
- say why it is being deferred
- say where it applies
- say what would trigger reclassification later

### Phase 7: cycle closeout

At the end of a cycle:

- record final SHAs
- record final green/red state
- record carry-forward list
- record next starting point

## Documentation Hierarchy

The design keeps the current directory layout as much as possible and clarifies responsibility instead of relocating everything.

### 1. Top-level operating system document

Recommended path:

- `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`

Responsibility:

- highest-level lifecycle
- branch roles
- blocker/carry-forward rules
- documentation map

### 2. Central strategy documents

- `docs/UPSTREAM_SYNC_STRATEGY.md`
- `docs/WORKTREE_STRATEGY.md`
- `docs/stom_v2_update_guide.md`

Responsibility:

- stable domain-specific rules
- branch topology
- update mechanics

### 3. Decision documents

- `docs/superpowers/specs/*`

Responsibility:

- why a particular strategy or correction was chosen
- rationale, boundaries, and tradeoffs

### 4. Execution documents

- `docs/superpowers/plans/*`

Responsibility:

- exact execution order
- exact commands
- exact verification checkpoints

### 5. Operational history

- `docs/update_log/*`
- branch-local `docs/update_log/*`

Responsibility:

- what actually happened
- blocker audit results
- corrective-fix outcomes
- baseline notes

### 6. Carry-forward registry

Recommended path:

- `docs/CARRY_FORWARD_REGISTRY.md`
  or cycle-specific registry entries under `docs/update_log/`

Responsibility:

- unresolved but known issues
- branch-specific deferred failures
- why they were not fixed yet

## AGENTS.md And CLAUDE.md Responsibilities

### AGENTS.md

Role:

- top-level execution entrypoint
- short, forceful policy summary
- documentation routing hub

It should answer:

- what is the authoritative release branch
- what is the propagation order
- what must never be done
- which operating document must be read first

Recommended content shape:

- concise mandatory rules
- links to:
  - operating system document
  - upstream strategy
  - worktree strategy
  - carry-forward registry
  - current cycle status/update log

### Central CLAUDE.md (`STOM_Version_2`)

Role:

- official intake execution guide

It should answer:

- how to verify upstream freshness
- how to run release preflight
- how to create official `STOM Vx.y` commits
- which documents to check before downstream work begins

### Worktree-local CLAUDE.md

Role:

- branch-local execution guide

It should answer:

- the branch's parent/canonical base
- protected files and behaviors
- branch-local verification commands
- branch-local note/update-log entry to read first

## Update Rules For AGENTS.md / CLAUDE.md

When the operating system changes:

- update `AGENTS.md`
- update the central `CLAUDE.md`

When branch-local execution rules change:

- update that worktree’s `CLAUDE.md`
- update that branch’s baseline note

When a cycle closes:

- verify that entrypoint links still point to the right strategy/status documents

## Required Branch-Local Note Structure

Each downstream branch note should always contain three axes:

1. **정규 업데이트 이후 개발 동향**
2. **보호 대상**
3. **다음 반영 시 우선순위**

Axis 3 must always include:

- parent/canonical base
- branch-local priority rule
- branch-local verification gate

## Carry-Forward Policy

Carry-forward is allowed only when all of the following are true:

1. the failing surface was not newly touched by the current wave, or
2. the blocker audit explicitly classified it as intentionally deferred
3. the issue is recorded in a registry/update log

Carry-forward is **not** allowed when:

- the current wave touched the failing surface
- the resulting red gate has not yet been audited

## Success Criteria

This operating system is successful if future official updates can be handled with the following pattern:

1. intake on `STOM_Version_2`
2. baseline check
3. version-wave propagation
4. blocker audit if needed
5. minimal corrective fix if needed
6. carry-forward update
7. cycle closeout

And if:

- new operators/agents can enter through `AGENTS.md` / `CLAUDE.md`
- branch-local exceptions are documented before they are needed
- blocker decisions are evidence-based instead of improvised

## Explicit Non-Goals

- replacing every existing doc with one mega-document
- forcing all downstream branches into byte-identical parity with release
- eliminating branch-local divergence altogether
- solving every carry-forward issue immediately
