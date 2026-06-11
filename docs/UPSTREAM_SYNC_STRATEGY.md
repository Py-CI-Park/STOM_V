# Upstream Sync Strategy

> This document is subordinate to `docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`.

- Updated: 2026-04-30
- Scope: release ingestion and downstream propagation from the official STOM upstream

## Source Of Truth

Upstream freshness is judged by the official upstream remote:

- Official freshness authority: `https://github.com/devstom/STOM.git`
- Local reference mirror: `C:/System_Trading/STOM/STOM_devstom`
- Current V2 wave source: `refs/tags/V2.0`

The local mirror is reference-only. It is useful for inspection and fallback access, but it is not the sole freshness authority. When deciding whether the release lane is current, compare against the GitHub upstream first.

For the V2.79 wave, use the terminal V2 tag:

```text
refs/tags/V2.0 -> 873d51eed3f581daa1925bcd9e3672254f525f0a
```

Do not use `refs/heads/V3.00` or `refs/tags/V3.0` for the V2.79 wave.

## Ingress Policy

- Official updates enter only through `STOM_Version_2`.
- `STOM_V/` is the only release-ingress worktree.
- Downstream branches receive propagated changes only after `STOM_Version_2` is updated and checked.
- Remaining V2 targets for the current wave are exactly `STOM V2.78` and `STOM V2.79`.

## Worktree Propagation Chain

### Current promoted state

```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```

Current propagation flow:

```text
V2 -> 2U -> 2U_C
```

`STOM_V.wt-dev/` is the active `STOM_Version_2U_C` checkout location. `STOM_V.wt-2uc/` remains on `integration/adopt-cli-v267-into-2uc` as an archive/history/transition checkout and is not part of the active canonical flow. `research/init` is not part of the current V2.79 propagation wave. Do not import upstream changes directly into downstream or research lanes. Every release-originated change must enter through V2 and move one lane at a time.

## Release Overlay Boundaries

Release overlays intentionally exclude branch-only surfaces such as docs, scripts, tests, CLI-only files, and research-only content. They also exclude protected result data.

- Protected result-data path: `backtest/graph/`
- Policy: `backtest/graph/` is not a git-propagated source path

If that directory is present as untracked output, it is allowed as result data. It must not be treated as release input or as evidence that propagation is incomplete.

## Preflight Workflow

Before release propagation, lane verification, or final handoff, run:

```bash
python scripts/verify_release_sync.py
```

To verify from another checkout root, use:

```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```

The preflight must pass before claiming the release sync is clean. A branch mismatch on `STOM_V.wt-dev/` means a clean `STOM_Version_2U_C` work location still needs to be prepared before propagation.

## Practical Operator Notes

- Use `STOM_devstom` for convenient local inspection when network access is unavailable or when comparing file history locally.
- Reconfirm against `https://github.com/devstom/STOM.git` before declaring the release lane current.
- Keep `CLAUDE.md` and the local worktree strategy docs aligned with the promoted `2U_C` baseline, the archive role of `wt-2uc`, and the exclusion of `research/init`.

## V3 Wave Source Of Truth

V3 lane은 V2 lane과 별도 freshness 권원을 가진다. V3 lane은 V3.18 intake로 활성화되었고, 본 절의 권원으로 V3.30~V3.32까지 흡수했다.

- 공식 freshness 권원: `https://github.com/devstom/STOM.git`
- 로컬 reference mirror: `C:/System_Trading/STOM/STOM_devstom`
- V3 wave source: `refs/heads/V3.00` (현재 STOM_Version_3 head는 로컬 `3dea3b94 STOM V3.32`)
- `refs/tags/V3.0`은 2026-04-23 V3.08에서 멈춘 **stale tag**로 확인됨 (2026-06-11 점검,
  `docs/update_log/2026-06-11_upstream_freshness_and_2uc_backport_review.md` §2.1) —
  freshness 권원으로 사용하지 않는다.

V3 freshness 점검 시 다음 시퀀스로 `_update.txt` 마커를 비교해 흡수를 결정한다.

```bash
git fetch https://github.com/devstom/STOM.git refs/heads/V3.00:refs/remotes/devstom_tmp/heads/V3.00 --force
git show refs/remotes/devstom_tmp/heads/V3.00:_update.txt | head -5
```

## V3 Wave Exclusion Note

CLAUDE.md "Upstream Ingress Policy"에 따라 다음을 reaffirm한다.

- 본 V2.79 웨이브에서는 `refs/heads/V3.00`, `refs/tags/V3.0`, V3 update section을 흡수하지 않는다.
- V3 lane(`STOM_Version_3`, `STOM_Version_3U`)은 별도 운영되며, V2 propagation chain에 영향을 주지 않는다.
- V3 wave 시작 시 본 문서의 "V3 Ingress Policy" 절을 적용한다.

## V3 Ingress Policy

V3 lane도 V2 lane과 동일하게 단일 ingress 원칙을 따른다.

- V3 official 업데이트는 `STOM_Version_3`로만 진입한다.
- `STOM_V.wt-3/`이 V3 release-ingress 워크트리.
- `STOM_Version_3U`(pyd-free 추론 lane)는 `STOM_Version_3` 흡수 후에만 머지/리베이스로 흡수한다.
- V3 흡수 후 다음 통합 게이트를 통과해야 V3U lane이 clean으로 판정된다.

```bash
python scripts/verify_v3u_pyd_gui_contract.py \
    --branch STOM_Version_3U --version <V3.X> \
    --upstream-ref STOM_Version_3 \
    --manifest .omx/logs/v3u/verify_<date>.json
```

이 게이트는 V3 official source 0줄 수정 invariant를 자동 검증하며, 위반 시 즉시 fail 한다. fail 발생 시 `ui/main_window.py` 또는 `tests/v3u/`에서만 수정하고 V3 official 디렉토리(`backtest/`, `strategy/`, `trade/`, `utility/`, `stom.py`, `ui/create_widget/`, `ui/update_widget/`, `ui/draw_chart/`, `ui/event_click/`, `ui/etcetera/`)는 절대 수정하지 않는다.

### V3 Release Overlay Boundaries (V2 동일 패턴 적용)

V3 release overlay도 다음을 제외한다.

- 보호 결과 데이터 경로: `backtest/graph/` (V2/V3 공통)
- branch-only 표면: `tests/v3u/`, `scripts/v3u_*.py`, `docs/V3U_*`, `requirements-dev.txt`, `pytest.ini`
- V3U 전용 추론 본체: `ui/main_window.py` (V3는 `ui/main_window.pyd` 보존)
