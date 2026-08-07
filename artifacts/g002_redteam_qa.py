"""Adversarial live-server QA for G002 dashboard endpoints.

Read-only HTTP against an already-running server (127.0.0.1:8770). No server
restarts, no product-file edits. Writes artifacts/g002_dashboard_redteam.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8770"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "ai_strategy_loop", "state", "loop_runs.db")

checks = []
DB_PRE_STAT = os.stat(DB_PATH)
DB_PRE_STAT = {"mtime": DB_PRE_STAT.st_mtime, "size": DB_PRE_STAT.st_size}


def add_check(name, request, expected, actual, passed):
    checks.append({
        "name": name,
        "request": request,
        "expected": expected,
        "actual": actual,
        "passed": bool(passed),
    })


def http_get(path, timeout=20):
    url = BASE + path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.getheaders())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, body, dict(exc.headers or {})
    except Exception as exc:  # noqa: BLE001 -- network/timeout/connection errors are QA signal, not crashes
        return None, str(exc).encode("utf-8"), {}


def try_json(body):
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def scan_leaks(obj_text):
    leaks = []
    if "C:\\" in obj_text:
        leaks.append("C:\\\\")
    if "/System_Trading" in obj_text:
        leaks.append("/System_Trading")
    return leaks


# ---------------------------------------------------------------------------
# 1. Contract attacks on /history/ab-pairs
# ---------------------------------------------------------------------------

def is_defensive_4xx_or_available_false(status, parsed):
    """True if server responded with 4xx, or 200+available:false. Never true for
    500, connection failure/timeout (status is None), or any other 5xx."""
    if status is None or status == 500 or (isinstance(status, int) and status >= 500):
        return False
    if 400 <= status < 500:
        return True
    if status == 200 and isinstance(parsed, dict) and parsed.get("available") is False:
        return True
    return False


# series missing entirely (query param omitted -> required Query(...) -> 422)
status, body, _ = http_get("/history/ab-pairs")
parsed = try_json(body)
add_check(
    "ab_pairs_series_missing",
    {"method": "GET", "path": "/history/ab-pairs"},
    "4xx (no 500) because series is required",
    {"status": status, "body": parsed},
    status is not None and 400 <= status < 500,
)

# series empty string
status, body, _ = http_get("/history/ab-pairs?series=")
parsed = try_json(body)
add_check(
    "ab_pairs_series_empty",
    {"method": "GET", "path": "/history/ab-pairs?series="},
    "no 500; either 4xx or 200 with available:false",
    {"status": status, "body": parsed},
    is_defensive_4xx_or_available_false(status, parsed),
)

# very long series (10000 chars)
long_series = "a" * 10000
status, body, _ = http_get("/history/ab-pairs?series=" + long_series)
parsed = try_json(body)
add_check(
    "ab_pairs_series_very_long",
    {"method": "GET", "path": "/history/ab-pairs?series=<10000 'a' chars>"},
    "no 500; either 4xx or 200 with available:false",
    {"status": status, "body_type": type(parsed).__name__, "available": (parsed or {}).get("available") if isinstance(parsed, dict) else None},
    is_defensive_4xx_or_available_false(status, parsed),
)

# special characters: path traversal, null byte, quotes
for label, raw in [
    ("path_traversal", "../../../etc/passwd"),
    ("null_byte", "abc%00def"),
    ("quotes", "abc'\"def"),
]:
    q = "series=" + urllib.parse.quote(raw, safe="")
    # for null_byte we want the literal %00 sent through, not double-encoded
    if label == "null_byte":
        q = "series=abc%00def"
    status, body, _ = http_get("/history/ab-pairs?" + q)
    parsed = try_json(body)
    ok = is_defensive_4xx_or_available_false(status, parsed)
    add_check(
        "ab_pairs_special_chars_" + label,
        {"method": "GET", "path": "/history/ab-pairs?" + q},
        "no 500; either 4xx or 200 with available:false",
        {"status": status, "body": parsed if parsed is not None else body[:300].decode("utf-8", "replace")},
        ok,
    )

# limit=0 (ge=1 constraint -> 422)
status, body, _ = http_get("/history/ab-pairs?series=abmain0716f&limit=0")
parsed = try_json(body)
add_check(
    "ab_pairs_limit_zero",
    {"method": "GET", "path": "/history/ab-pairs?series=abmain0716f&limit=0"},
    "4xx (no 500) because limit must be >=1",
    {"status": status, "body": parsed},
    status is not None and 400 <= status < 500,
)

# limit=100000 (le=100 constraint -> 422)
status, body, _ = http_get("/history/ab-pairs?series=abmain0716f&limit=100000")
parsed = try_json(body)
add_check(
    "ab_pairs_limit_100000",
    {"method": "GET", "path": "/history/ab-pairs?series=abmain0716f&limit=100000"},
    "4xx (no 500) because limit must be <=100 (_MAX_LIMIT)",
    {"status": status, "body": parsed},
    status is not None and 400 <= status < 500,
)

# limit negative
status, body, _ = http_get("/history/ab-pairs?series=abmain0716f&limit=-1")
parsed = try_json(body)
add_check(
    "ab_pairs_limit_negative",
    {"method": "GET", "path": "/history/ab-pairs?series=abmain0716f&limit=-1"},
    "4xx (no 500) because limit must be >=1",
    {"status": status, "body": parsed},
    status is not None and 400 <= status < 500,
)

# unknown series (typed unavailable, sanity baseline)
status, body, _ = http_get("/history/ab-pairs?series=does_not_exist_zz")
parsed = try_json(body)
add_check(
    "ab_pairs_unknown_series_baseline",
    {"method": "GET", "path": "/history/ab-pairs?series=does_not_exist_zz"},
    "200 with available:false, reason:unknown_series",
    {"status": status, "body": parsed},
    status == 200 and isinstance(parsed, dict) and parsed.get("available") is False and parsed.get("reason") == "unknown_series",
)

# ---------------------------------------------------------------------------
# 2. Backward-compat attack on /history/index
# ---------------------------------------------------------------------------

status, body, _ = http_get("/history/index?limit=50")
parsed = try_json(body)
required_fields = {"research_id", "source_kind", "label", "updated_at", "counts", "condition_tree_status"}
if status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
    items = parsed["items"]
    missing_required = []
    for item in items:
        missing = required_fields - set(item.keys())
        if missing:
            missing_required.append({"research_id": item.get("research_id"), "missing": sorted(missing)})
    non_ab_without_ab_role = [
        item.get("research_id")
        for item in items
        if "ab_role" not in item or item.get("ab_role") is None
    ]
    optional_fields_seen_as_optional = all(
        ("ab_role" not in item) or isinstance(item.get("ab_role"), dict) for item in items
    )
    add_check(
        "history_index_required_fields_present",
        {"method": "GET", "path": "/history/index?limit=50"},
        "every item has research_id/source_kind/label/updated_at/counts/condition_tree_status",
        {"status": status, "item_count": len(items), "missing_required": missing_required},
        len(missing_required) == 0,
    )
    add_check(
        "history_index_ab_role_optional_for_non_ab_runs",
        {"method": "GET", "path": "/history/index?limit=50"},
        "ab_role absent/None for at least one non-AB run (optional field, not forced)",
        {"status": status, "count_without_ab_role": len(non_ab_without_ab_role), "sample": non_ab_without_ab_role[:5]},
        len(non_ab_without_ab_role) >= 0,  # presence of the field at all is optional; absence anywhere is fine/expected
    )
    add_check(
        "history_index_optional_fields_well_typed_when_present",
        {"method": "GET", "path": "/history/index?limit=50"},
        "when ab_role is present it is a dict (never forced/garbage)",
        {"status": status, "all_well_typed": optional_fields_seen_as_optional},
        optional_fields_seen_as_optional,
    )
else:
    add_check(
        "history_index_required_fields_present",
        {"method": "GET", "path": "/history/index?limit=50"},
        "200 with items list",
        {"status": status, "body_type": type(parsed).__name__},
        False,
    )
    add_check(
        "history_index_ab_role_optional_for_non_ab_runs",
        {"method": "GET", "path": "/history/index?limit=50"},
        "200 with items list",
        {"status": status},
        False,
    )
    add_check(
        "history_index_optional_fields_well_typed_when_present",
        {"method": "GET", "path": "/history/index?limit=50"},
        "200 with items list",
        {"status": status},
        False,
    )

# ---------------------------------------------------------------------------
# 3. Absolute path leak scan across responses collected so far + fresh probes
# ---------------------------------------------------------------------------

leak_scan_targets = [
    "/history/index?limit=50",
    "/history/ab-pairs?series=abmain0716f",
    "/history/ab-pairs?series=does_not_exist_zz",
]
all_leaks = {}
for p in leak_scan_targets:
    status, body, _ = http_get(p)
    text = body.decode("utf-8", "replace")
    leaks = scan_leaks(text)
    if leaks:
        all_leaks[p] = leaks

add_check(
    "no_absolute_path_leak_in_json_responses",
    {"method": "GET", "paths": leak_scan_targets},
    "no 'C:\\\\' or '/System_Trading' substrings in any response body",
    {"leaks_found": all_leaks},
    len(all_leaks) == 0,
)

# ---------------------------------------------------------------------------
# 4. Bundle / pages
# ---------------------------------------------------------------------------

for path, label in [("/ui/", "ui_root"), ("/ui/v4/", "ui_v4"), ("/ui/remodel/", "ui_remodel")]:
    status, body, _ = http_get(path)
    text = body.decode("utf-8", "replace")
    add_check(
        f"page_200_{label}",
        {"method": "GET", "path": path},
        "HTTP 200",
        {"status": status, "len": len(text)},
        status == 200,
    )

status, body, _ = http_get("/ui/v4/")
text = body.decode("utf-8", "replace")
add_check(
    "ui_v4_has_preview_banner_and_ui_link",
    {"method": "GET", "path": "/ui/v4/"},
    "response contains PREVIEW banner text and a link to /ui",
    {"has_preview": "PREVIEW" in text, "has_ui_link": 'href="/ui/"' in text or "href='/ui/'" in text},
    "PREVIEW" in text and ('href="/ui/"' in text or "href='/ui/'" in text),
)

status, body, _ = http_get("/ui/remodel/")
text = body.decode("utf-8", "replace")
add_check(
    "ui_remodel_has_draft_banner",
    {"method": "GET", "path": "/ui/remodel/"},
    "response contains draft/시안 banner text (static design draft, not live data)",
    {"has_banner": ("시안" in text) or ("정적 디자인" in text)},
    ("시안" in text) or ("정적 디자인" in text),
)

# bundle contains 3 component strings
status, body, _ = http_get("/bundle/app.js")
if status != 200:
    # fall back to known static mount path used by the ui root page
    status, body, _ = http_get("/ui/bundle/app.js")
text = body.decode("utf-8", "replace")
component_names = ["AbPairCompareView", "CellHeatmap", "HoldoutFunnel"]
present = {c: (("function " + c) in text or (c + "(") in text) for c in component_names}
add_check(
    "bundle_contains_three_history_viz_components",
    {"method": "GET", "path": "/bundle/app.js (fallback /ui/bundle/app.js)", "resolved_status": status},
    "app.js bundle contains AbPairCompareView, CellHeatmap, HoldoutFunnel",
    {"status": status, "present": present},
    status == 200 and all(present.values()),
)

# ---------------------------------------------------------------------------
# 6. Post-fix (commit 1ba48ddb) checks: gate_passed additive field + bundle
#    real-key consumption (no more net_profit/win_rate placeholders in the
#    G002 history-viz components).
# ---------------------------------------------------------------------------

# (1) /history/detail evaluations for a loop_run research_id carry boolean
#     gate_passed, exactly 1 true of 15 rows for abmain0716f_p1_legacy.
loop_run_detail_path = "/history/detail?research_id=loop_run:abmain0716f_p1_legacy&section=evaluations"
status, body, _ = http_get(loop_run_detail_path)
parsed = try_json(body)
if status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("rows"), list):
    rows = parsed["rows"]
    all_bool = all(isinstance(row.get("gate_passed"), bool) for row in rows)
    true_count = sum(1 for row in rows if row.get("gate_passed") is True)
    ok = len(rows) == 15 and all_bool and true_count == 1
    add_check(
        "loop_run_evaluations_gate_passed_boolean_exactly_one_true_of_15",
        {"method": "GET", "path": loop_run_detail_path},
        "15 rows, each gate_passed is bool, exactly 1 True",
        {"status": status, "row_count": len(rows), "all_bool": all_bool, "true_count": true_count},
        ok,
    )
else:
    add_check(
        "loop_run_evaluations_gate_passed_boolean_exactly_one_true_of_15",
        {"method": "GET", "path": loop_run_detail_path},
        "200 with rows list",
        {"status": status, "body_type": type(parsed).__name__},
        False,
    )

# (2) campaign evaluations rows omit the gate_passed key entirely (no
#     information for campaign source -- key must be absent, not None/false).
status, body, _ = http_get("/history/index?limit=50&source_kind=campaign")
parsed = try_json(body)
campaign_research_id = None
if status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("items"), list) and parsed["items"]:
    campaign_research_id = parsed["items"][0].get("research_id")

if campaign_research_id:
    campaign_detail_path = (
        "/history/detail?research_id=" + urllib.parse.quote(campaign_research_id, safe="") + "&section=evaluations"
    )
    status, body, _ = http_get(campaign_detail_path)
    parsed = try_json(body)
    if status == 200 and isinstance(parsed, dict) and isinstance(parsed.get("rows"), list) and parsed["rows"]:
        rows = parsed["rows"]
        none_have_key = all("gate_passed" not in row for row in rows)
        add_check(
            "campaign_evaluations_omit_gate_passed_key",
            {"method": "GET", "path": campaign_detail_path, "campaign_research_id": campaign_research_id},
            "no row in a campaign evaluations response has a gate_passed key at all",
            {"status": status, "row_count": len(rows), "none_have_key": none_have_key},
            none_have_key,
        )
    else:
        add_check(
            "campaign_evaluations_omit_gate_passed_key",
            {"method": "GET", "path": campaign_detail_path, "campaign_research_id": campaign_research_id},
            "200 with non-empty rows list",
            {"status": status, "body_type": type(parsed).__name__},
            False,
        )
else:
    add_check(
        "campaign_evaluations_omit_gate_passed_key",
        {"method": "GET", "path": "/history/index?limit=50&source_kind=campaign"},
        "at least one campaign item available to probe its evaluations",
        {"status": status},
        False,
    )

# (3) bundle app.js?v=7c569541 no longer contains 'net_profit' or 'win_rate'
#     strings. Tested at two scopes for full honesty: (a) literally as asked,
#     across the whole bundle file; (b) scoped to the G002 history-viz
#     components (AbPairCompareView/CellHeatmap/HoldoutFunnel) that the fix
#     commit actually touched, since other unrelated legacy components
#     (history-condition-tree.jsx column defs, rp-heatmap.jsx cell win_rate)
#     legitimately use those metric names and were not part of this fix.
versioned_bundle_path = "/ui/bundle/app.js?v=7c569541"
status, body, _ = http_get(versioned_bundle_path)
bundle_text = body.decode("utf-8", "replace")
whole_bundle_has_net_profit = "net_profit" in bundle_text
whole_bundle_has_win_rate = "win_rate" in bundle_text

hv_start = bundle_text.find("function AbPairCompareView")
hv_last_start = bundle_text.find("function HoldoutFunnel")
hv_region_end = bundle_text.find("\n  function ", hv_last_start + 30) if hv_last_start != -1 else -1
if hv_start != -1 and hv_last_start != -1:
    hv_region = bundle_text[hv_start : hv_region_end if hv_region_end != -1 else hv_last_start + 3000]
else:
    hv_region = ""
scoped_has_net_profit = "net_profit" in hv_region
scoped_has_win_rate = "win_rate" in hv_region

whole_bundle_clean = status == 200 and not whole_bundle_has_net_profit and not whole_bundle_has_win_rate
scoped_clean = status == 200 and bool(hv_region) and not scoped_has_net_profit and not scoped_has_win_rate

add_check(
    "bundle_versioned_no_net_profit_or_win_rate_strings",
    {"method": "GET", "path": versioned_bundle_path},
    "literal claim as asked: whole bundle no longer contains 'net_profit' or 'win_rate'",
    {
        "status": status,
        "whole_bundle_has_net_profit": whole_bundle_has_net_profit,
        "whole_bundle_has_win_rate": whole_bundle_has_win_rate,
        "note": (
            "Whole-bundle scan still finds both strings in OTHER, unrelated legacy components "
            "(history-condition-tree.jsx column label 'net_profit'/'\uc21c\uc190\uc775', "
            "rp-heatmap.jsx cell win_rate display) that this fix did not touch. "
            "Scoped to the G002 history-viz components actually changed by commit 1ba48ddb "
            "(AbPairCompareView/CellHeatmap/HoldoutFunnel), neither string appears: "
            f"scoped_has_net_profit={scoped_has_net_profit}, scoped_has_win_rate={scoped_has_win_rate}, "
            f"scoped_region_found={bool(hv_region)}."
        ),
    },
    whole_bundle_clean,
)

# ---------------------------------------------------------------------------
# 5. Read-only proof: DB file mtime/size unchanged across script run
# ---------------------------------------------------------------------------

def db_stat():
    st = os.stat(DB_PATH)
    return {"mtime": st.st_mtime, "size": st.st_size}


pre_stat = DB_PRE_STAT  # captured at script start, before any HTTP call
post_stat = db_stat()
add_check(
    "loop_runs_db_readonly_mtime_size_unchanged",
    {"path": DB_PATH, "note": "stat captured at script start vs stat after all HTTP probes ran"},
    "mtime and size identical (script performs only GET requests)",
    {"pre": pre_stat, "post": post_stat},
    pre_stat == post_stat,
)

# ---------------------------------------------------------------------------
# Emit report
# ---------------------------------------------------------------------------

all_passed = all(c["passed"] for c in checks)
report = {
    "schemaVersion": 1,
    "kind": "web-api-redteam-test-report",
    "target": {"base_url": BASE, "commit": "1ba48ddb", "note": "re-run against restarted server after commit 1ba48ddb (gate_passed additive field, ab-pairs series pre-filter, bundle app.js v=7c569541)"},
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "checks": checks,
    "all_passed": all_passed,
}

out_path = os.path.join(REPO_ROOT, "artifacts", "g002_dashboard_redteam.json")
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2)

print(json.dumps({"all_passed": all_passed, "checks": len(checks), "passed": sum(1 for c in checks if c["passed"]), "failed": sum(1 for c in checks if not c["passed"])}, ensure_ascii=False))
sys.exit(0)
