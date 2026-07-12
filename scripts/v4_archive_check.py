"""Fail-closed installed-Chrome archive selector and screenshot checker."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RUN_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def product_identity_valid(
    bundle_url: str,
    bundle_bytes: bytes,
    expected_bundle_sha256: str,
    *,
    html_sha256: str = "",
    expected_html_sha256: str = "",
    css_sha256: list[str] | None = None,
    expected_css_sha256: list[str] | None = None,
    source_graph_sha256: str = "",
    expected_source_graph_sha256: str = "",
) -> bool:
    version = parse_qs(urlparse(bundle_url).query).get("v", [""])[0]
    digest = hashlib.sha256(bundle_bytes).hexdigest()
    text = bundle_bytes.decode("utf-8", errors="replace")
    return (
        digest == expected_bundle_sha256
        and version == digest[:8]
        and all(marker in text for marker in ("winner_gen", "review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"))
        and bool(html_sha256) and html_sha256 == expected_html_sha256
        and bool(css_sha256) and css_sha256 == expected_css_sha256
        and bool(source_graph_sha256) and source_graph_sha256 == expected_source_graph_sha256
    )


def _source_graph_hash(frontend: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in frontend.rglob("*") if path.is_file() and "bundle" not in path.relative_to(frontend).parts)
    for path in files:
        digest.update(path.relative_to(frontend).as_posix().encode("utf-8")); digest.update(b"\0"); digest.update(path.read_bytes()); digest.update(b"\0")
    return digest.hexdigest()


def _origin(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.path not in {"", "/"}:
        raise ValueError("base must be a loopback origin")
    return raw.rstrip("/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        base = _origin(args.base)
        run_ids = [item.strip() for item in args.runs.split(",") if item.strip()]
        if not run_ids or len(run_ids) != len(set(run_ids)) or any(RUN_ID.fullmatch(item) is None for item in run_ids):
            raise ValueError("runs must be unique safe identifiers")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    if out.exists():
        print("ERROR: --out must be fresh", file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    check_id = f"archive-{uuid.uuid4().hex[:12]}"
    started_ns = time.time_ns()
    errors: list[str] = []
    captures: list[dict[str, str | int | bool]] = []
    identity: dict[str, str | bool] | None = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            page = context.new_page()
            page.on("console", lambda msg: errors.append(f"console:{msg.text}") if msg.type == "error" else None)
            page.on("pageerror", lambda exc: errors.append(f"page:{exc}"))
            page.on("requestfailed", lambda req: errors.append(f"request:{req.method} {req.url} {req.failure}"))
            page.on("response", lambda resp: errors.append(f"response:{resp.request.method} {resp.url} {resp.status}") if resp.status >= 400 else None)
            for run_id in run_ids:
                page.goto(f"{base}/ui/v4/?tab=research&run={run_id}&uat_run_id={check_id}", wait_until="domcontentloaded", timeout=15_000)
                if identity is None:
                    bundle_url = page.evaluate("() => [...performance.getEntriesByType('resource')].map(e=>e.name).find(u=>u.includes('/ui/bundle/app.js')) || ''")
                    bundle_bytes = page.request.get(bundle_url).body()
                    bundle_hash = hashlib.sha256(bundle_bytes).hexdigest()
                    frontend = Path(__file__).resolve().parents[1] / "ai_strategy_loop" / "dashboard" / "frontend"
                    source = frontend / "v4-research.jsx"
                    expected_bundle_hash = hashlib.sha256((frontend / "bundle" / "app.js").read_bytes()).hexdigest()
                    html_bytes = page.request.get(f"{base}/ui/v4/").body()
                    html_hash = hashlib.sha256(html_bytes).hexdigest()
                    expected_html_hash = hashlib.sha256((frontend / "v4.html").read_bytes()).hexdigest()
                    css_urls = sorted(page.evaluate("() => [...performance.getEntriesByType('resource')].map(e=>e.name).filter(u=>new URL(u).pathname.endsWith('.css'))"))
                    css_hashes = [hashlib.sha256(page.request.get(url).body()).hexdigest() for url in css_urls]
                    expected_css_hashes = [hashlib.sha256((frontend / urlparse(url).path.split('/ui/', 1)[1]).read_bytes()).hexdigest() for url in css_urls]
                    source_graph_hash = _source_graph_hash(frontend)
                    valid_identity = product_identity_valid(bundle_url, bundle_bytes, expected_bundle_hash, html_sha256=html_hash, expected_html_sha256=expected_html_hash, css_sha256=css_hashes, expected_css_sha256=expected_css_hashes, source_graph_sha256=source_graph_hash, expected_source_graph_sha256=source_graph_hash)
                    identity = {"bundle_url": bundle_url, "bundle_sha256": bundle_hash, "expected_bundle_sha256": expected_bundle_hash, "html_sha256": html_hash, "expected_html_sha256": expected_html_hash, "css_urls": css_urls, "css_sha256": css_hashes, "expected_css_sha256": expected_css_hashes, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source_graph_sha256": source_graph_hash, "valid": valid_identity}
                selector = page.locator(".v4-runsel select")
                selector.wait_for(state="visible", timeout=10_000)
                selector.select_option(run_id)
                page.wait_for_function("rid => document.querySelector('.v4-view-title')?.textContent.includes('archive') && document.querySelector('.v4-runsel select')?.value === rid", run_id)
                destination = out / f"{check_id}-{run_id}.png"
                page.screenshot(path=str(destination), full_page=True)
                stat = destination.stat()
                digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                captures.append({"run": run_id, "path": str(destination), "sha256": digest, "size": stat.st_size, "captured_at_ns": stat.st_mtime_ns, "fresh": stat.st_size > 100 and stat.st_mtime_ns >= started_ns})
            context.close(); browser.close()
    except Exception as exc:  # noqa: BROAD_EXCEPT_OK - CLI boundary emits a failure report.
        errors.append(f"harness:{type(exc).__name__}:{exc}")
    valid = len(captures) == len(run_ids) and all(bool(item["fresh"]) for item in captures) and len({str(item["sha256"]) for item in captures}) == len(run_ids) and bool(identity and identity["valid"]) and not errors
    (out / "archive-report.json").write_text(json.dumps({"run_id": check_id, "browser": {"channel": "chrome", "fallback": False}, "product_identity": identity, "captures": captures, "errors": errors, "status": "executed" if valid else "failed"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
