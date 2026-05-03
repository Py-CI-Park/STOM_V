# STOM_Version_2 Update Guide

> Current status: this guide is now a V2.79 wave entry guide. The old zip-based process is legacy-only and must not be used for the current official V2.79 wave.

## Current Source Boundary

- Official upstream: `https://github.com/devstom/STOM.git`
- Current V2 source ref: `refs/tags/V2.0`
- Terminal V2 tag commit: `873d51eed3f581daa1925bcd9e3672254f525f0a`
- Expected top marker in `refs/tags/V2.0:_update.txt`: `2026-04-08 V2.79`
- Current local official release state: updated through `STOM V2.77`
- Remaining official intake targets: `STOM V2.78`, then `STOM V2.79`

Do not use `refs/heads/V3.00`, `refs/tags/V3.0`, or any V3 `_update.txt` section for this wave.

## Active Propagation Chain

```text
V2 -> 2U -> 2U_C
```

Worktree roles:

- `C:/System_Trading/STOM/STOM_V` -> `STOM_Version_2` -> official release ingress
- `C:/System_Trading/STOM/STOM_V.wt-2u` -> `STOM_Version_2U` -> pyd-to-py translation lane
- `C:/System_Trading/STOM/STOM_V.wt-dev` -> `STOM_Version_2U_C` -> active downstream runtime compatibility lane
- `C:/System_Trading/STOM/STOM_V.wt-2uc` -> `integration/adopt-cli-v267-into-2uc` -> archive/transition only

Branch parity rule:

- `STOM_Version_2` / `*_2` reflects official upstream updates and keeps upstream `.pyd` files.
- `STOM_Version_2U` is the pyd-to-py inference result. Non-pyd official runtime files should remain identical to `STOM_Version_2`; fix inference defects in inferred `.py` or wrapper boundaries first.
- `STOM_Version_2U_C` is the custom update lane derived from 2U. Custom updates may be made here, but intentional differences from 2U must be documented in `docs/CARRY_FORWARD_REGISTRY.md` or the active update-log status.

`research/init` is excluded from the current official propagation chain.

## Preflight

Refresh the V2 terminal tag from the authoritative upstream:

```powershell
git fetch https://github.com/devstom/STOM.git `
  refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
```

Check the terminal V2 marker:

```powershell
git show refs/remotes/devstom_tmp/tags/V2.0:_update.txt |
  Select-String -Pattern '^\d{4}-\d{2}-\d{2} V[0-9]+\.[0-9]+' |
  Select-Object -First 20
```

Run the release preflight:

```powershell
python scripts/verify_release_sync.py
```

If preflight reports that `STOM_V.wt-dev` is on a preparation feature branch, prepare a clean `STOM_Version_2U_C` work location before downstream propagation.

## Formal Release Commit Rules

- One official version equals one commit.
- Commit title: `STOM V{major}.{minor}`
- Commit body: the full matching `_update.txt` section from `refs/tags/V2.0`
- Apply versions in ascending order with no skips.
- For the current wave, intake exactly `STOM V2.78` and `STOM V2.79`.

## Legacy Zip Workflow

The previous workflow used:

```text
C:/Users/parkc/Downloads/STOM_temp/STOM_V{version}.zip
scripts/stom_v2_update.py
C:/System_Trading/stom_v2_update.py
```

That process is stale for the V2.79 wave because the official source is the GitHub `V2.0` tag, not local zip files. Keep the zip scripts for historical reference only unless a future task explicitly reactivates them.
