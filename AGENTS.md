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


## V3 / V3U / 2U_C Backport Entry Points

V3 전략 kick-off, `STOM_Version_3` 공식 ingress, `STOM_Version_3U` pyd-free 전환, 3U vs 3 최종 parity audit은 완료된 상태다. 기존 safe micro-candidate backport queue는 closure 되었지만, 이는 V3 신기능 전체 반영 완료가 아니다. 현재 새 목표는 `V3K = V3 기능 + Kiwoom 유지`로, `STOM_Version_2U_C`에 LS증권 직접 의존성을 제외한 V3 학습/분석/DB/backtest/realtime 기능을 설계 기반으로 이행하는 것이다.

V3, 3U, 또는 2U_C V3 backport 관련 작업을 시작하기 전에는 반드시 아래 문서를 순서대로 읽는다:
1. `docs/V3_UPDATE_OPERATING_SYSTEM.md`
2. `docs/update_log/2026-05-06_v3_v3u_final_handoff.md`
3. `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
4. `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md`
5. `docs/update_log/2026-05-04_v3_transition_strategy_review.md`
6. `docs/WORKTREE_STRATEGY.md`
7. `docs/CARRY_FORWARD_REGISTRY.md`
8. 최신 2U_C backport queue/status 문서 under `docs/update_log/`

현재 전환기 worktree 지도:

```text
STOM_V/          -> STOM_Version_2       # V2 공식 유지 / root orchestration
STOM_V.wt-2u/    -> STOM_Version_2U      # V2 pyd-free 유지
STOM_V.wt-dev/   -> STOM_Version_2U_C    # Kiwoom 유지 custom/backport
STOM_V.wt-3/     -> STOM_Version_3       # V3 공식 ingress 완료
STOM_V.wt-3u/    -> STOM_Version_3U      # V3 pyd-free 완료
STOM_V.wt-2uc/   -> integration archive  # active lane 아님
```

V3 공식 lane에는 upstream 파일과 `.pyd`를 보존한다. V3 pyd 제거는 `STOM_Version_3U`에서만 수행한다. `STOM_Version_3U_C`는 아직 만들지 않는다.

`STOM_Version_2U_C`는 V3 branch가 아니라 V2/Kiwoom 유지 custom lane이다. V3 기능은 broker-neutral 후보부터 선별 backport하고, LS API 전제/DB 비호환 변경은 migration spec과 별도 검토 전에는 제외한다. 각 backport는 source V3 version/commit, 제외한 LS 의존성, Kiwoom 유지 보정, 검증 결과를 `docs/CARRY_FORWARD_REGISTRY.md` 또는 active `docs/update_log/` 문서에 기록해야 한다.

2026-05-08 이후 새 V3K 목표에서는 DB/학습/분석/backtest/realtime 기능도 적용 대상이다. 단, 즉시 broad merge하지 말고 `V3K-DESIGN-0`부터 시작해 DB migration spec, Kiwoom data-shape mapping, analyzer contract, feature flag, rollback plan, mock/regression tests를 먼저 작성한다. `DESIGN-LS`/`LS-IMPL` 명칭은 LS증권과 혼동되므로 사용하지 말고 `V3K-DESIGN`/`V3K-IMPL`을 사용한다.

V3/V3U runtime `_database`, `_log`, `*.db` 파일은 커밋하지 않는다. 3U는 `STOM_Version_3`에서 분기했으며, pyd 제거 구현은 `STOM_Version_2U`의 pyd-to-py 추론 산출물과 검증 도구를 참고해 V3 구조에 맞게 이식한 상태다.
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
