# STOM_Version_2 AI Agent Guide

## pyd ?? ?? ?? ???

- `STOM_Version_2`? ?? upstream ??? `.pyd` ?? ??? ????.
- `2U`/`2U_C`??? `.pyd`? `.py` ????? ????.
- `.pyd`? `.py`? ??? ?? ?? `.py` ??? ???? ?? ??? ?? ????.
  - `set_*.py`? `self.ui.*` ???/?? ??
  - `ui_button_clicked_*.py`? MainWindow wrapper ??
  - ???? `activated`, ?? `clicked`, ????? show/close ??
  - wildcard import ??? ?? ??? ???
- ?? import/py_compile ????? ?? ???? ???. ?? GUI ????? ??? ???? wrapper? ?? ???? ??.
- `sactivated_*`/`cactivated_*`?? ???? ?? alias? ???? ??? ??? ??. ?? ??? ??? `activated_XX(self, 'stock'/'coin')`?? ?? ??? ?? ????.
- 2U?? ??? pyd ?? ??? ?? ??? ??? 2U_C? ?? ????.
- ?? ??? ?? ?? ??? ???? ??? `scripts/verify_pyd_gui_contract.py`, `scripts/smoke_offline_gui.py`, ?? ??? ? ?? ??? ?? ???? ????.


> Detailed guide: `docs/stom_v2_update_guide.md`

## Formal Update Entry Points

Read in this order before official update work:
1. `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`
2. `docs/UPSTREAM_SYNC_STRATEGY.md`
3. `docs/WORKTREE_STRATEGY.md`
4. `docs/CARRY_FORWARD_REGISTRY.md`
5. latest cycle status under `docs/update_log/`


## V3 Kick-off Entry Points

V3 진입은 전략 kick-off가 완료된 상태이며, 아직 실제 V3 branch/worktree 생성이나 V3 파일 반영은 시작하지 않았다.

V3 관련 작업을 시작하기 전에는 반드시 아래 문서를 순서대로 읽는다:
1. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
2. `docs/update_log/2026-05-04_v3_transition_strategy_review.md`
3. `docs/WORKTREE_STRATEGY.md`
4. `docs/CARRY_FORWARD_REGISTRY.md`

V3 전환기 목표 worktree 지도:

```text
STOM_V/          -> STOM_Version_2       # V2 공식 유지
STOM_V.wt-2u/    -> STOM_Version_2U      # V2 pyd-free 유지
STOM_V.wt-dev/   -> STOM_Version_2U_C    # Kiwoom 유지 custom/backport
STOM_V.wt-3/     -> STOM_Version_3       # V3 공식 ingress, 신규 예정
STOM_V.wt-3u/    -> STOM_Version_3U      # V3 pyd-free, 신규 예정
STOM_V.wt-2uc/   -> integration archive  # active lane 아님
```

V3 공식 lane에는 upstream 파일과 `.pyd`를 보존한다. V3 pyd 제거는 `STOM_Version_3U`에서만 수행한다. `STOM_Version_2U_C`는 V3 branch가 아니라 Kiwoom 유지 custom lane이며, V3 기능은 선별 backport로만 반영한다. `STOM_Version_3U_C`는 아직 만들지 않는다.

새 V3/V3U worktree를 만든 뒤에는 ignored runtime directory인 `_database`와 `_log`를 별도로 생성한다. V3의 초기 DB seed는 필요 시 `STOM_V/_database`를 백업 후 복사하고, V3U는 준비된 `STOM_V.wt-3/_database`를 seed로 맞춘다. DB 파일은 커밋하지 않는다. 3U는 `STOM_Version_3`에서 분기하되, pyd 제거 구현은 `STOM_Version_2U`의 pyd-to-py 추론 산출물과 검증 도구를 참고해 이식한다.

Current resume context:
`docs/update_log/2026-04-30_v279_update_resume_context.md`

Previous closed cycle status:
`docs/update_log/2026-04-05_v274_v277_cycle_status.md`

Current promoted state:
`V2 -> 2U -> 2U_C`

`STOM_Version_2` remains the release-ingress branch. `STOM_V.wt-dev/` is the active `STOM_Version_2U_C` checkout location, and `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/transition lane. `research/init` is excluded from the current official V2.79 propagation chain. Do not restore the retired live CLI child-lane model.

## Branch Parity Invariants

- `STOM_Version_2` / `*_2`: official upstream update reflection lane. Keep upstream update files as official source, including upstream `.pyd` files.
- `STOM_Version_2U`: pyd-to-py inference lane derived from V2. Non-pyd official runtime files must stay identical to `STOM_Version_2`; inference defects are fixed in inferred `.py` files, MainWindow wrappers, process wrappers, or verification contracts.
- `STOM_Version_2U_C`: custom update lane derived from 2U. Custom changes may proceed here, but they must be documented as 2U_C custom carry-forward/allowlist items and do not imply changes to V2 or 2U unless explicitly promoted.
- Default audit direction: `2U` vs `V2` allows only pyd-to-py inference differences; `2U_C` vs `2U` allows only documented custom differences.
- When a GUI/runtime problem appears in 2U, inspect pyd-inferred `.py` and wrapper boundaries before editing official `.py` files. Official-file exceptions require an explicit decision record.

## Commit Language Rules

New commits in this repository use these defaults:

- Commit title first line is written in Korean.
- Commit body is written in Korean markdown.
- Recommended body sections:
  - `## 배경`
  - `## 변경 사항`
  - `## 검증`
  - `## 주의사항` when needed
- Prefer Korean trailer values when trailers are useful.
- Do not use English type-prefix-only titles such as `docs: ...` or `fix: ...` as the default format.
- Formal release commits are the exception: title `STOM V{major}.{minor}`, body is the full matching `_update.txt` section.

## Core Rules

1. Official source for the V2.79 wave is GitHub `refs/tags/V2.0`.
2. Remaining official V2 intake targets are exactly `STOM V2.78` and `STOM V2.79`.
3. One official version equals one commit.
4. Formal release commit title exception: `STOM V{major}.{minor}`.
5. Formal release commit body: the full matching `_update.txt` section from `refs/tags/V2.0`.
6. Version order must remain ascending with no skips.
7. V3 refs, V3 update sections, and `research/init` are out of scope for this wave.

## V2.79 Update Workflow

Do not use the legacy zip workflow for the V2.79 wave. The legacy `scripts/stom_v2_update.py` and `C:/System_Trading/stom_v2_update.py` paths are retained only for historical zip-based updates.

Recommended start:

```bash
git fetch https://github.com/devstom/STOM.git refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
git show refs/remotes/devstom_tmp/tags/V2.0:_update.txt
python scripts/verify_release_sync.py
```

Then apply `STOM V2.78` and `STOM V2.79` one version at a time through:

```text
V2 -> 2U -> 2U_C
```

## Agent Checklist

- [ ] Work from `STOM_Version_2` for official release ingress.
- [ ] Confirm `refs/tags/V2.0` contains the V2.78/V2.79 source sections.
- [ ] Run release preflight before claiming the release lane is clean.
- [ ] Confirm no V3 section enters the V2 wave.
- [ ] Confirm a clean `2U_C` work location before downstream propagation.
- [ ] Verify final commits with `git log STOM_Version_2 --oneline -5`.

## Absolute Prohibitions

- Do not use `git add -A`.
- Do not combine multiple formal versions into one commit.
- Do not use `git rebase` or `git reset --hard`.
- Do not commit development-code changes directly to `STOM_Version_2` as part of a formal release commit.
- Do not treat `backtest/graph/` as release input.

## Current State

- Active official release branch: `STOM_Version_2`
- Active downstream chain: `V2 -> 2U -> 2U_C`
- Legacy zip updater: `scripts/stom_v2_update.py` / `C:/System_Trading/stom_v2_update.py`
- Detailed guide: `docs/stom_v2_update_guide.md`
