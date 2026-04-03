# Upstream Worktree Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codify the approved `STOM_Version_2 -> STOM_Version_2U -> STOM_Version_2U_C -> STOM_Version_2U_C_CLI_v267 -> research/init` propagation policy into release-side code and docs so future official updates have a repeatable preflight and accurate operator guidance.

**Architecture:** Add one small release-side policy module and one preflight verifier in `STOM_V`, then update the operator docs to match the real worktree topology and the new verifier. Keep the implementation focused on the current repository: define the chain, protect `backtest/graph/` as non-git output, and make the docs describe `V2` as the only upstream ingress instead of trying to automate downstream propagation in the same change.

**Tech Stack:** Python 3.12, `pytest`, PowerShell, git porcelain status parsing, Markdown docs.

---

## File Structure

- Create: `utility/upstream_sync_policy.py`
- Create: `scripts/verify_release_sync.py`
- Create: `tests/unit/test_upstream_sync_policy.py`
- Create: `tests/unit/test_verify_release_sync.py`
- Create: `tests/unit/test_upstream_sync_docs.py`
- Modify: `.gitignore`
- Modify: `CLAUDE.md`
- Modify: `docs/WORKTREE_STRATEGY.md`
- Modify: `docs/UPSTREAM_SYNC_STRATEGY.md`

`utility/upstream_sync_policy.py` owns the canonical chain definition, upstream source values, release overlay excludes, and protected non-git paths.  
`scripts/verify_release_sync.py` owns release-side preflight checks for worktree branch mapping, tracked edits, and allowed untracked assets.  
`tests/unit/test_upstream_sync_policy.py` locks the policy constants and helper behavior.  
`tests/unit/test_verify_release_sync.py` locks porcelain parsing and allowed-untracked-path behavior for the release verifier.  
`tests/unit/test_upstream_sync_docs.py` locks the operator docs to the approved policy so the docs do not drift back to the older topology.  
`.gitignore` must explicitly ignore `backtest/graph/` because current runtime code writes there and the policy treats it as protected result data.  
`CLAUDE.md`, `docs/WORKTREE_STRATEGY.md`, and `docs/UPSTREAM_SYNC_STRATEGY.md` must be updated together so the release worktree does not present conflicting operator instructions.

## Task 1: Add A Canonical Release-Side Policy Module

**Files:**
- Create: `tests/unit/test_upstream_sync_policy.py`
- Create: `utility/upstream_sync_policy.py`

- [ ] **Step 1: Write the failing policy tests**

Create `tests/unit/test_upstream_sync_policy.py` with this content:

```python
from utility.upstream_sync_policy import (
    LOCAL_UPSTREAM_MIRROR,
    PROPAGATION_CHAIN,
    PROTECTED_NON_GIT_PATHS,
    RELEASE_OVERLAY_EXCLUDES,
    UPSTREAM_REMOTE_URL,
    expected_branch_for_worktree,
    is_protected_non_git_path,
)


def test_propagation_chain_matches_the_real_worktree_layout():
    assert PROPAGATION_CHAIN == (
        ("STOM_Version_2", "C:/System_Trading/STOM/STOM_V"),
        ("STOM_Version_2U", "C:/System_Trading/STOM/STOM_V.wt-2u"),
        ("STOM_Version_2U_C", "C:/System_Trading/STOM/STOM_V.wt-2uc"),
        ("STOM_Version_2U_C_CLI_v267", "C:/System_Trading/STOM/STOM_V.wt-dev"),
        ("research/init", "C:/System_Trading/STOM/STOM_V.wt-lab"),
    )


def test_release_policy_prefers_real_upstream_before_local_mirror():
    assert UPSTREAM_REMOTE_URL == "https://github.com/devstom/STOM.git"
    assert LOCAL_UPSTREAM_MIRROR == "C:/System_Trading/STOM/STOM_devstom"


def test_backtest_graph_is_a_protected_non_git_asset():
    assert PROTECTED_NON_GIT_PATHS == ("backtest/graph/",)
    assert is_protected_non_git_path("backtest/graph")
    assert is_protected_non_git_path("backtest/graph/run-2026-04-03")
    assert is_protected_non_git_path("./backtest/graph/output.png")
    assert not is_protected_non_git_path("backtester/graph/output.png")


def test_expected_branch_lookup_uses_exact_worktree_roots():
    assert expected_branch_for_worktree("C:/System_Trading/STOM/STOM_V") == "STOM_Version_2"
    assert expected_branch_for_worktree("C:/System_Trading/STOM/STOM_V.wt-dev") == "STOM_Version_2U_C_CLI_v267"


def test_release_overlay_excludes_cover_docs_scripts_and_branch_only_surfaces():
    assert RELEASE_OVERLAY_EXCLUDES == (
        ".git/",
        ".gitignore",
        "CLAUDE.md",
        "AGENTS.md",
        "docs/",
        "scripts/",
        "tests/",
        "cli/",
        "research/",
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/unit/test_upstream_sync_policy.py -q
```

Expected:
- FAIL with `ModuleNotFoundError: No module named 'utility.upstream_sync_policy'`

- [ ] **Step 3: Write the minimal policy module**

Create `utility/upstream_sync_policy.py` with this content:

```python
UPSTREAM_REMOTE_URL = "https://github.com/devstom/STOM.git"
LOCAL_UPSTREAM_MIRROR = "C:/System_Trading/STOM/STOM_devstom"

PROPAGATION_CHAIN = (
    ("STOM_Version_2", "C:/System_Trading/STOM/STOM_V"),
    ("STOM_Version_2U", "C:/System_Trading/STOM/STOM_V.wt-2u"),
    ("STOM_Version_2U_C", "C:/System_Trading/STOM/STOM_V.wt-2uc"),
    ("STOM_Version_2U_C_CLI_v267", "C:/System_Trading/STOM/STOM_V.wt-dev"),
    ("research/init", "C:/System_Trading/STOM/STOM_V.wt-lab"),
)

RELEASE_OVERLAY_EXCLUDES = (
    ".git/",
    ".gitignore",
    "CLAUDE.md",
    "AGENTS.md",
    "docs/",
    "scripts/",
    "tests/",
    "cli/",
    "research/",
)

PROTECTED_NON_GIT_PATHS = ("backtest/graph/",)


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def expected_branch_for_worktree(worktree_path: str) -> str:
    normalized = _normalize_path(worktree_path).rstrip("/")
    for branch, root in PROPAGATION_CHAIN:
        if normalized == root.rstrip("/"):
            return branch
    raise KeyError(f"unknown worktree path: {worktree_path}")


def is_protected_non_git_path(path: str) -> bool:
    normalized = _normalize_path(path).lstrip("./")
    for protected in PROTECTED_NON_GIT_PATHS:
        prefix = protected.rstrip("/")
        if normalized == prefix or normalized.startswith(f"{prefix}/"):
            return True
    return False
```

- [ ] **Step 4: Run the policy test to verify it passes**

Run:

```powershell
pytest tests/unit/test_upstream_sync_policy.py -q
```

Expected:
- PASS

- [ ] **Step 5: Commit the policy module**

Run:

```powershell
git add tests/unit/test_upstream_sync_policy.py utility/upstream_sync_policy.py
git commit -m "feat: codify upstream worktree policy"
```

Expected:
- one commit containing only the new policy module and its test

## Task 2: Add Release Preflight Verification And Result-Data Protection

**Files:**
- Create: `tests/unit/test_verify_release_sync.py`
- Create: `scripts/verify_release_sync.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing release-verifier tests**

Create `tests/unit/test_verify_release_sync.py` with this content:

```python
from scripts.verify_release_sync import ParsedStatus, parse_porcelain, validate_status


def test_parse_porcelain_splits_branch_tracked_and_untracked_entries():
    parsed = parse_porcelain(
        [
            "## STOM_Version_2U_C_CLI_v267...origin/STOM_Version_2U_C_CLI_v267 [ahead 18]",
            " M docs/WORKTREE_STRATEGY.md",
            "?? backtest/graph",
            "?? scratch.txt",
        ]
    )

    assert parsed.branch == "STOM_Version_2U_C_CLI_v267"
    assert parsed.tracked == ["docs/WORKTREE_STRATEGY.md"]
    assert parsed.untracked == ["backtest/graph", "scratch.txt"]


def test_validate_status_allows_only_protected_untracked_paths():
    parsed = ParsedStatus(
        branch="STOM_Version_2U_C_CLI_v267",
        tracked=[],
        untracked=["backtest/graph"],
    )

    assert validate_status("C:/System_Trading/STOM/STOM_V.wt-dev", parsed) == []


def test_validate_status_rejects_branch_mismatch_tracked_edits_and_unknown_untracked_paths():
    parsed = ParsedStatus(
        branch="wrong-branch",
        tracked=["ui/set_widget.py"],
        untracked=["scratch.txt"],
    )

    failures = validate_status("C:/System_Trading/STOM/STOM_V.wt-dev", parsed)

    assert any("expected branch" in failure for failure in failures)
    assert any("tracked edits" in failure for failure in failures)
    assert any("scratch.txt" in failure for failure in failures)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
pytest tests/unit/test_verify_release_sync.py -q
```

Expected:
- FAIL with `ModuleNotFoundError` or `ImportError` for `scripts.verify_release_sync`

- [ ] **Step 3: Implement the verifier and ignore the protected graph output**

Add this block to `.gitignore` near the existing temporary/runtime output rules:

```gitignore
# Backtest result data must survive worktree propagation
backtest/graph/
```

Create `scripts/verify_release_sync.py` with this content:

```python
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from utility.upstream_sync_policy import (
    PROPAGATION_CHAIN,
    expected_branch_for_worktree,
    is_protected_non_git_path,
)


@dataclass(frozen=True)
class ParsedStatus:
    branch: str
    tracked: list[str]
    untracked: list[str]


def parse_porcelain(lines: list[str]) -> ParsedStatus:
    branch_line = next(line for line in lines if line.startswith("## "))
    branch = branch_line[3:].split("...")[0].strip()
    tracked: list[str] = []
    untracked: list[str] = []

    for line in lines[1:]:
        if not line:
            continue
        path = line[3:]
        if line.startswith("?? "):
            untracked.append(path)
        else:
            tracked.append(path)

    return ParsedStatus(branch=branch, tracked=tracked, untracked=untracked)


def validate_status(worktree_path: str, parsed: ParsedStatus) -> list[str]:
    failures: list[str] = []
    expected_branch = expected_branch_for_worktree(worktree_path)

    if parsed.branch != expected_branch:
        failures.append(
            f"{worktree_path}: expected branch {expected_branch}, got {parsed.branch}"
        )
    if parsed.tracked:
        failures.append(f"{worktree_path}: tracked edits present: {', '.join(parsed.tracked)}")

    unexpected_untracked = [
        path for path in parsed.untracked if not is_protected_non_git_path(path)
    ]
    if unexpected_untracked:
        failures.append(
            f"{worktree_path}: unexpected untracked paths: {', '.join(unexpected_untracked)}"
        )

    return failures


def git_status_lines(worktree_path: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", worktree_path, "status", "--porcelain=v1", "--branch"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="C:/System_Trading/STOM/STOM_V")
    args = parser.parse_args(argv)

    failures: list[str] = []
    gitignore_text = (Path(args.root) / ".gitignore").read_text(encoding="utf-8")
    if "backtest/graph/" not in gitignore_text:
        failures.append(".gitignore must ignore backtest/graph/")

    for _branch, worktree_path in PROPAGATION_CHAIN:
        parsed = parse_porcelain(git_status_lines(worktree_path))
        failures.extend(validate_status(worktree_path, parsed))

    if failures:
        print("\n".join(failures))
        return 1

    print("release sync preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the verifier tests to verify they pass**

Run:

```powershell
pytest tests/unit/test_verify_release_sync.py -q
```

Expected:
- PASS

- [ ] **Step 5: Run the new release preflight against the current workspace**

Run:

```powershell
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V
```

Expected:
- `release sync preflight passed`

- [ ] **Step 6: Commit the verifier and graph protection**

Run:

```powershell
git add .gitignore scripts/verify_release_sync.py tests/unit/test_verify_release_sync.py
git commit -m "feat: add release sync preflight verifier"
```

Expected:
- one commit containing the release verifier, its test, and the `.gitignore` protection

## Task 3: Update Operator Docs And Lock Them With Tests

**Files:**
- Create: `tests/unit/test_upstream_sync_docs.py`
- Modify: `CLAUDE.md`
- Modify: `docs/WORKTREE_STRATEGY.md`
- Modify: `docs/UPSTREAM_SYNC_STRATEGY.md`

- [ ] **Step 1: Write the failing doc-policy tests**

Create `tests/unit/test_upstream_sync_docs.py` with this content:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_worktree_strategy_mentions_the_actual_worktree_layout():
    text = read_text("docs/WORKTREE_STRATEGY.md")

    assert "STOM_V.wt-2uc/" in text
    assert "STOM_V.wt-dev/" in text
    assert "research/init" in text
    assert "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init" in text


def test_upstream_sync_strategy_uses_v2_only_ingress_and_release_preflight():
    text = read_text("docs/UPSTREAM_SYNC_STRATEGY.md")

    assert "python scripts/verify_release_sync.py" in text
    assert "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init" in text
    assert "https://github.com/devstom/STOM.git" in text
    assert "STOM_devstom" in text


def test_claude_guide_uses_the_current_worktree_mapping():
    text = read_text("CLAUDE.md")

    assert "STOM_V.wt-2uc/" in text
    assert "STOM_V.wt-dev/" in text
    assert "STOM_Version_2U_C_CLI_v267" in text
    assert "python scripts/verify_release_sync.py" in text
```

- [ ] **Step 2: Run the doc test to verify it fails**

Run:

```powershell
pytest tests/unit/test_upstream_sync_docs.py -q
```

Expected:
- FAIL because the current docs still describe the older topology and do not mention `verify_release_sync.py`

- [ ] **Step 3: Update the docs to the approved policy**

Apply these concrete doc changes.

In `CLAUDE.md`, replace the current `V2.59 이후` operator block with this one:

````markdown
### 방법 2: V2.59 이후 (devstom git 기반, release ingress only)

```bash
# 1. 실제 upstream 최신 확인
git fetch https://github.com/devstom/STOM.git master:refs/remotes/devstom_tmp/master
git show --stat --oneline devstom_tmp/master -- _update.txt

# 2. release worktree preflight
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V

# 3. 공식 버전은 STOM_Version_2에서만 반영
# 4. 전파 순서: V2 -> 2U -> 2U_C -> CLI_v267 -> research/init
```
````

In `docs/WORKTREE_STRATEGY.md`, replace the current worktree topology table with this one and add the protected-asset rule:

````markdown
| 디렉토리 | 브랜치 | 역할 |
|----------|--------|------|
| `STOM_V/` | `STOM_Version_2` | 공식 upstream ingress 전용 |
| `STOM_V.wt-2u/` | `STOM_Version_2U` | 첫 번째 비정식 안정화 레이어 |
| `STOM_V.wt-2uc/` | `STOM_Version_2U_C` | 커스텀 통합 브랜치 |
| `STOM_V.wt-dev/` | `STOM_Version_2U_C_CLI_v267` | CLI 호환성 기준선 |
| `STOM_V.wt-lab/` | `research/init` | CLI 다음 단계의 research 브랜치 |

전파 순서: `V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`

보호 자산:
- `backtest/graph/`는 결과 데이터 경로다.
- 공식 업데이트 전파 시 삭제하거나 git 전파 대상으로 취급하지 않는다.
- 전파 전후 존재 여부를 확인만 한다.
````

In `docs/UPSTREAM_SYNC_STRATEGY.md`, add this override section near the top of the document:

````markdown
## 0. Current operating overrides (2026-04-03)

- upstream 최신 판정은 `https://github.com/devstom/STOM.git` 기준으로 한다.
- `C:/System_Trading/STOM/STOM_devstom`는 로컬 미러이므로 참조용이지 최신 기준 자체는 아니다.
- 공식 업데이트는 `STOM_Version_2`만 직접 받는다.
- 전파 순서는 `V2 -> 2U -> 2U_C -> CLI_v267 -> research/init`이다.
- `backtest/graph/`는 보호 대상 비-git 결과 자산이다.
- 공식 버전 반영 전에 `python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V`를 실행한다.
````

- [ ] **Step 4: Run the doc-policy test to verify it passes**

Run:

```powershell
pytest tests/unit/test_upstream_sync_docs.py -q
```

Expected:
- PASS

- [ ] **Step 5: Run the full policy smoke suite**

Run:

```powershell
pytest tests/unit/test_upstream_sync_policy.py tests/unit/test_verify_release_sync.py tests/unit/test_upstream_sync_docs.py -q
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V
```

Expected:
- all three pytest files PASS
- `release sync preflight passed`

- [ ] **Step 6: Commit the doc rollout**

Run:

```powershell
git add CLAUDE.md docs/WORKTREE_STRATEGY.md docs/UPSTREAM_SYNC_STRATEGY.md tests/unit/test_upstream_sync_docs.py
git commit -m "docs: codify upstream worktree propagation policy"
```

Expected:
- one docs-focused commit containing only the doc updates and their guard test

## Self-Review Checklist

- Spec coverage:
  - release ingress only on `STOM_Version_2` is covered in Tasks 1-3
  - protected result asset handling for `backtest/graph/` is covered in Task 2 and reinforced in Task 3
  - actual worktree topology and full-chain order are covered in Task 1 and Task 3
  - release-side preflight verification is covered in Task 2
- Placeholder scan:
  - no `TODO`, `TBD`, or unresolved commit-hash placeholders remain
  - every code-changing step includes exact code or exact command blocks
- Type consistency:
  - `ParsedStatus`, `parse_porcelain`, and `validate_status` names are consistent between tests and implementation
  - `PROPAGATION_CHAIN`, `PROTECTED_NON_GIT_PATHS`, and `RELEASE_OVERLAY_EXCLUDES` are referenced consistently across tests, module, and verifier

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-03-upstream-worktree-propagation.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
