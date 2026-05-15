"""V3K Kiwoom sentinel mock scenario matrix (plan v2 §C T04a, §D V03a/V03b/V04a/V04b).

Verifies the V07 invariant `khopenapi_compatible == primary_signal.exists` across
all 4 corner cases of the (S1, S2, S3) signal cube, using monkey-patched probe
helpers so this smoke runs on both lanes (V2 / V2U_C) without depending on the
host's actual Kiwoom installation. T04b live-audit on a real PC is committed as
a separate audit-trail artifact.

Scenarios (plan §D):
- V03a: S1=True, S2=False, S3=False -> compatible=True, corroboration_count=0
- V03b: S1=False, S2=True, S3=True -> compatible=False, corroboration_count=2  (R4 핵심)
- V04a: S1=True, S2=True, S3=True -> compatible=True, corroboration_count=2
- V04b: S1=False, S2=False, S3=False -> compatible=False, corroboration_count=0
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_kiwoom_dryrun_hook import V3KKiwoomDryrunHook, V3KSentinelResult  # noqa: E402


def _make_primary(exists: bool) -> dict[str, Any]:
    return {
        "source": "ActiveX ProgID",
        "path": "HKEY_CLASSES_ROOT\\KHOPENAPI.KHOpenAPICtrl.1",
        "exists": exists,
    }


def _make_corroborating(s2_exists: bool, s3_exists: bool) -> tuple[dict[str, Any], ...]:
    s2 = {
        "source": "OPENAPI_PATH directory",
        "path": "C:/OpenAPI" if s2_exists else "(unresolvable)",
        "exists": s2_exists,
        "dll_count": 6 if s2_exists else 0,
    }
    s3 = {
        "source": "legacy DLL",
        "path": "C:/OpenAPI/khopenapi.dll",
        "exists": s3_exists,
    }
    return (s2, s3)


def _run_scenario(
    label: str,
    *,
    s1: bool,
    s2: bool,
    s3: bool,
    expected_compatible: bool,
    expected_corroboration_count: int,
) -> None:
    primary = _make_primary(s1)
    corroborating = _make_corroborating(s2, s3)

    with patch(
        "strategy.v3k_kiwoom_dryrun_hook.probe_primary_signal", return_value=primary
    ), patch(
        "strategy.v3k_kiwoom_dryrun_hook.collect_corroborating_signals",
        return_value=corroborating,
    ):
        hook = V3KKiwoomDryrunHook()
        result = hook.resolve_khopenapi_sentinel()

    if not isinstance(result, V3KSentinelResult):
        raise AssertionError(f"{label}: resolve_khopenapi_sentinel did not return V3KSentinelResult")
    if result.primary_exists != s1:
        raise AssertionError(f"{label}: primary_exists={result.primary_exists}, expected {s1}")
    if result.compatible != expected_compatible:
        raise AssertionError(
            f"{label}: compatible={result.compatible}, expected {expected_compatible} (V07)",
        )
    # V07 invariant: compatible MUST equal primary_exists, independent of corroboration
    if result.compatible != result.primary_exists:
        raise AssertionError(
            f"{label}: V07 invariant violation - compatible={result.compatible} != primary_exists={result.primary_exists}",
        )
    if result.corroboration_count != expected_corroboration_count:
        raise AssertionError(
            f"{label}: corroboration_count={result.corroboration_count}, expected {expected_corroboration_count}",
        )
    if len(result.corroborating_signals) != 2:
        raise AssertionError(
            f"{label}: expected exactly 2 corroborating signals, got {len(result.corroborating_signals)}",
        )
    print(
        f"  {label} PASS: S1={s1} S2={s2} S3={s3} -> "
        f"compatible={result.compatible}, corroboration_count={result.corroboration_count}",
    )


def main() -> None:
    print("v3k Kiwoom sentinel mock scenario matrix (V07 invariant: compatible == primary_exists)")
    _run_scenario(
        "V03a (primary only)",
        s1=True, s2=False, s3=False,
        expected_compatible=True, expected_corroboration_count=0,
    )
    _run_scenario(
        "V03b (corroborating only, R4 boundary)",
        s1=False, s2=True, s3=True,
        expected_compatible=False, expected_corroboration_count=2,
    )
    _run_scenario(
        "V04a (both primary + corroborating)",
        s1=True, s2=True, s3=True,
        expected_compatible=True, expected_corroboration_count=2,
    )
    _run_scenario(
        "V04b (neither)",
        s1=False, s2=False, s3=False,
        expected_compatible=False, expected_corroboration_count=0,
    )
    print("v3k Kiwoom sentinel mock scenario matrix smoke passed (4/4)")
    print("V07 invariant verified across all (S1, S2, S3) corner cases")


if __name__ == "__main__":
    main()
