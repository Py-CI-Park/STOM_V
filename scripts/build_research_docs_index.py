# -*- coding: utf-8 -*-
"""Build the immutable research-document metadata sidecar consumed by the dashboard.

The dashboard GET path never writes files. Run this script after adding or renaming
allowlisted research Markdown documents. It reads only the first 16 KiB needed for
titles and publishes one atomic JSON snapshot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ai_strategy_loop.dashboard import research_api


def build_index(output: Path) -> dict:
    documents = []
    signature = []
    for path, category in research_api._iter_allowed_docs():
        try:
            content_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        summary = research_api._summary_for(path, category)
        documents.append(summary)
        signature.append((summary["id"], content_sha256))
    documents.sort(key=lambda row: (row["category"], row["id"]))
    signature.sort()
    fingerprint = hashlib.sha256(
        json.dumps(signature, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": research_api._DOC_INDEX_SIDECAR_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": fingerprint,
        "count": len(documents),
        "docs": documents,
    }


def index_matches(output: Path, payload: dict) -> bool:
    try:
        current = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False

    def stable_docs(value: dict) -> list[dict]:
        return [
            {key: item[key] for key in sorted(item) if key != "updated_at"}
            for item in value.get("docs", [])
            if isinstance(item, dict)
        ]

    return (
        current.get("schema_version") == payload.get("schema_version")
        and current.get("source_fingerprint") == payload.get("source_fingerprint")
        and current.get("count") == payload.get("count")
        and stable_docs(current) == stable_docs(payload)
    )


def write_atomic(output: Path, payload: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build STOM dashboard research-doc metadata index")
    parser.add_argument(
        "--output",
        default=str(research_api._DOC_INDEX_SIDECAR),
        help="output JSON path (default: docs/generated_reports/research_docs_index.json)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail without writing when the tracked sidecar differs from current sources",
    )
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    payload = build_index(output)
    if args.check:
        if not index_matches(output, payload):
            print(f"research docs index is stale: {output}")
            return 1
        print(f"research docs index check: PASS ({payload['count']} docs)")
        return 0
    write_atomic(output, payload)
    print(f"research docs index: {payload['count']} docs -> {output}")
    print(f"source fingerprint: {payload['source_fingerprint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
