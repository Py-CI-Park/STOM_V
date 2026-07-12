from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "stable_id",
    "page",
    "route",
    "item_type",
    "label",
    "owner",
    "source_refs",
    "dom_selectors",
    "endpoint_action",
    "safety_classification",
    "v2_evidence",
    "v3_evidence",
    "parity_status",
    "failure_rules",
    "closure_evidence",
}

REQUIRED_PAGES = {
    "shell",
    "condition",
    "process",
    "history",
    "lab",
    "workbench",
    "audit",
    "backtest",
    "chart_replay",
}

REQUIRED_ITEM_TYPES = {
    "route",
    "section",
    "button",
    "form",
    "modal",
    "function",
    "api_endpoint",
    "data_field",
    "network_call",
    "asset",
    "cache_policy",
    "safety_boundary",
}

REQUIRED_STABLE_IDS = {
    "dash.condition.button.start_stop.v1",
    "dash.audit.section.append_only_ledger.v1",
    "dash.backtest.api.run.manual_gate.v1",
    "dash.chart_replay.ws.sim_ws.manual_gate.v1",
    "dash.shell.selector.v3_preview_link.v1",
    "dash.shell.route.v2_default.v1",
    "dash.shell.route.v3_remodel_explicit.v1",
}

CLEAN_PARITY = {"covered", "improved", "superseded", "not_applicable"}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_inventory(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    items = _as_list(payload.get("items"))
    if payload.get("schemaVersion") != 1:
        failures.append("schemaVersion must be 1")
    if not items:
        failures.append("items must be a non-empty array")

    stable_ids: set[str] = set()
    pages: set[str] = set()
    item_types: set[str] = set()
    safety_classes: set[str] = set()

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            failures.append(f"items[{idx}] must be an object")
            continue
        missing = sorted(field for field in REQUIRED_FIELDS if field not in item)
        if missing:
            failures.append(f"{item.get('stable_id', f'items[{idx}]')} missing fields: {', '.join(missing)}")
            continue
        sid = str(item.get("stable_id") or "")
        if not sid:
            failures.append(f"items[{idx}] stable_id is empty")
        elif sid in stable_ids:
            failures.append(f"duplicate stable_id: {sid}")
        stable_ids.add(sid)

        pages.add(str(item.get("page")))
        item_types.add(str(item.get("item_type")))
        safety_classes.update(str(value) for value in _as_list(item.get("safety_classification")))

        for list_field in ["source_refs", "dom_selectors", "safety_classification", "failure_rules", "closure_evidence"]:
            if not _as_list(item.get(list_field)):
                failures.append(f"{sid} {list_field} must be a non-empty array")
        for evidence_field in ["v2_evidence", "v3_evidence"]:
            evidence = item.get(evidence_field)
            if not isinstance(evidence, dict) or not evidence.get("status") or not _as_list(evidence.get("refs")):
                failures.append(f"{sid} {evidence_field} must include status and refs")
        if str(item.get("parity_status")) not in CLEAN_PARITY:
            failures.append(f"{sid} parity_status must be one of {sorted(CLEAN_PARITY)}")

    missing_pages = sorted(REQUIRED_PAGES - pages)
    if missing_pages:
        failures.append("missing required pages: " + ", ".join(missing_pages))
    missing_types = sorted(REQUIRED_ITEM_TYPES - item_types)
    if missing_types:
        failures.append("missing required item types: " + ", ".join(missing_types))
    missing_ids = sorted(REQUIRED_STABLE_IDS - stable_ids)
    if missing_ids:
        failures.append("missing required stable IDs: " + ", ".join(missing_ids))
    if "manual_gated" not in safety_classes:
        failures.append("manual_gated safety classification is required")
    if "human_gate" not in safety_classes:
        failures.append("human_gate safety classification is required")
    if "append_only" not in safety_classes:
        failures.append("append_only safety classification is required")

    summary = {
        "items": len(items),
        "pages": sorted(pages),
        "itemTypes": sorted(item_types),
        "safetyClasses": sorted(safety_classes),
        "failures": len(failures),
    }
    return failures, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify STOM dashboard V2/V3 stable inventory gate.")
    parser.add_argument("--inventory", required=True, help="Path to v2-v3-inventory.json")
    parser.add_argument("--route-matrix", default=None, help="Optional route-version-matrix.json to require as evidence")
    parser.add_argument("--out", required=True, help="Path to write gate-result.json")
    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    failures, summary = validate_inventory(payload)

    if args.route_matrix:
        route_matrix_path = Path(args.route_matrix)
        if not route_matrix_path.is_file():
            failures.append(f"route matrix not found: {route_matrix_path}")
        else:
            route_payload = json.loads(route_matrix_path.read_text(encoding="utf-8"))
            route_failures = route_payload.get("summary", {}).get("failures")
            if route_failures is None:
                route_failures = len(route_payload.get("failures", []))
            if route_failures != 0:
                failures.append("route matrix summary failures must be 0")
            summary["routeMatrix"] = str(route_matrix_path)

    result = {
        "schemaVersion": 1,
        "kind": "dashboard-v2-v3-inventory-gate",
        "status": "passed" if not failures else "failed",
        "inventory": str(inventory_path),
        "summary": summary,
        "failures": failures,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "failures": len(failures), "items": summary["items"]}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
