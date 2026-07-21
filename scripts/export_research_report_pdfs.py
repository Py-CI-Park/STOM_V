# -*- coding: utf-8 -*-
"""Publish offline PDF companions for registered dashboard research reports.

The input catalog is never fetched or served by this tool.  HTML is verified against
its registered bytes and SHA-256 before a local Chromium instance renders a staged
copy; the manifest is the last file replaced.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urldefrag

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ai_strategy_loop.dashboard.report_writer import (  # noqa: E402
    MAX_BYTES_EACH,
    MAX_REPORTS,
    REPORT_SCHEMA_VERSION,
    _validate_v1_manifest,
    verified_report_html_path,
)

PdfRenderer = Callable[[Path, Path], None]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_exact_int(value: Any, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _canonical_relative_path(root: Path, relative: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative:
        raise ValueError("report companion path is invalid")
    candidate = Path(relative)
    if candidate.is_absolute() or "\\" in relative or any(part in ("", ".", "..") for part in candidate.parts):
        raise ValueError("report companion path is not canonical")
    canonical = candidate.as_posix()
    if relative != canonical:
        raise ValueError("report companion path is not canonical")
    target = (root / candidate).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("report companion path escapes output directory") from error
    return canonical, target


def _safe_path(root: Path, relative: str) -> Path:
    _canonical, target = _canonical_relative_path(root, relative)
    return target


def _path_identity(path: Path) -> str:
    return str(path.resolve()).casefold()


def _pdf_path(html_path: str) -> str:
    if not html_path.lower().endswith(".html"):
        raise ValueError("registered report path is not HTML")
    return html_path[:-5] + ".pdf"


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("report manifest contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"report manifest contains invalid JSON constant: {value}")


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            manifest_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("report manifest is unreadable") from error
    try:
        _validate_v1_manifest(payload)
    except ValueError as error:
        raise ValueError(f"report manifest is not a strict stom-research-report-v1 envelope: {error}") from error
    return payload


def _validate_html_entries(manifest: dict[str, Any], out_dir: Path) -> list[tuple[dict[str, Any], Path, bytes]]:
    validated: list[tuple[dict[str, Any], Path, bytes]] = []
    destinations: dict[str, str] = {}
    for entry in manifest["reports"]:
        if not isinstance(entry, dict):
            raise ValueError("report manifest entry is invalid")
        relative = entry.get("path")
        canonical, html_path = _canonical_relative_path(out_dir, relative)
        if relative != canonical or not canonical.endswith(".html"):
            raise ValueError("registered report path is not canonical HTML")
        if (
            entry.get("schema_version") != REPORT_SCHEMA_VERSION
            or not _is_lower_sha256(entry.get("content_sha256"))
            or not _is_lower_sha256(entry.get("source_sha256"))
            or entry.get("sha256") != entry["content_sha256"]
            or not _is_exact_int(entry.get("bytes"))
            or entry["bytes"] > MAX_BYTES_EACH
        ):
            raise ValueError(f"report entry provenance is invalid: {relative}")
        pdf_relative = _pdf_path(canonical)
        for label, destination in ((f"HTML:{canonical}", html_path), (f"PDF:{pdf_relative}", _safe_path(out_dir, pdf_relative))):
            identity = _path_identity(destination)
            if identity in destinations:
                raise ValueError(f"registered report destinations collide: {destinations[identity]} and {label}")
            destinations[identity] = label
        html_name, html_bytes = verified_report_html_path(entry, str(out_dir))
        if _path_identity(Path(html_name)) != _path_identity(html_path):
            raise ValueError(f"registered report path alias: {relative}")
        validated.append((entry, html_path, html_bytes))
    return validated


def _render_pdf_locally(
    html_path: Path,
    pdf_path: Path,
    *,
    allowed_assets: set[Path] | None = None,
) -> None:
    """Render one staged document while allowing only explicitly registered staged files."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("local Playwright is required for PDF publication") from error

    allowed_urls = {(asset.resolve().as_uri()) for asset in (allowed_assets or {html_path})}
    document_url = html_path.resolve().as_uri()
    if document_url not in allowed_urls:
        raise ValueError("rendered document is not a registered staged asset")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            try:
                page = context.new_page()

                def block_unregistered_request(route: Any) -> None:
                    request_url, _fragment = urldefrag(route.request.url)
                    if request_url in allowed_urls:
                        route.continue_()
                    else:
                        route.abort()

                page.route("**/*", block_unregistered_request)
                page.goto(document_url, wait_until="load")
                page.pdf(path=str(pdf_path), format="A4", print_background=True)
            finally:
                context.close()
        finally:
            browser.close()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _assert_manifest_destination(manifest_path: Path, out_dir: Path, reports: list[tuple[dict[str, Any], Path, bytes]]) -> None:
    manifest_identity = _path_identity(manifest_path)
    for entry, html_path, _html_bytes in reports:
        pdf_path = _safe_path(out_dir, _pdf_path(entry["path"]))
        if manifest_identity in {_path_identity(html_path), _path_identity(pdf_path)}:
            raise ValueError("manifest destination collides with a registered HTML or PDF destination")


def validate_pdf_companions(out_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Validate registered HTML and PDF bytes without modifying any file."""
    manifest = _load_manifest(manifest_path)
    reports = _validate_html_entries(manifest, out_dir)
    _assert_manifest_destination(manifest_path, out_dir, reports)
    for entry, _html_path, _html_bytes in reports:
        content_hash = entry["content_sha256"]
        pdf_relative = _pdf_path(entry["path"])
        if (
            entry.get("pdf_path") != pdf_relative
            or entry.get("pdf_source_content_sha256") != content_hash
            or not _is_lower_sha256(entry.get("pdf_sha256"))
            or not _is_exact_int(entry.get("pdf_bytes"), minimum=1)
        ):
            raise ValueError(f"registered PDF provenance is invalid: {entry['path']}")
        pdf_path = _safe_path(out_dir, pdf_relative)
        try:
            pdf_bytes = pdf_path.read_bytes()
        except OSError as error:
            raise ValueError(f"registered PDF is unreadable: {pdf_relative}") from error
        if len(pdf_bytes) != entry["pdf_bytes"] or _sha256_bytes(pdf_bytes) != entry["pdf_sha256"]:
            raise ValueError(f"registered PDF bytes mismatch: {pdf_relative}")
    return manifest


def _verify_published_pdf_snapshot(out_dir: Path, manifest_path: Path, expected: dict[str, Any]) -> None:
    expected_bytes = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        live_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise ValueError("published PDF manifest is unreadable") from error
    if live_bytes != expected_bytes:
        raise ValueError("published PDF manifest bytes do not match the completed snapshot")
    verified = validate_pdf_companions(out_dir, manifest_path)
    if verified != expected:
        raise ValueError("published PDF manifest does not match the completed snapshot")

def _durable_backup_copy(source: Path, backup: Path) -> None:
    """Copy an existing live file to a fsynced recovery artifact before replacement."""
    backup.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_handle, backup.open("xb") as output_handle:
        shutil.copyfileobj(input_handle, output_handle)
        output_handle.flush()
        os.fsync(output_handle.fileno())


def _rollback_replacements(replacements: list[tuple[Path, Path | None]]) -> list[OSError]:
    failures: list[OSError] = []
    for destination, backup in reversed(replacements):
        try:
            if backup is None:
                if destination.exists():
                    destination.unlink()
            else:
                os.replace(backup, destination)
        except OSError as error:
            failures.append(error)
    return failures


def publish_pdf_companions(out_dir: Path, manifest_path: Path, *, renderer: PdfRenderer = _render_pdf_locally) -> dict[str, Any]:
    """Render all verified report HTML to PDFs and commit PDF metadata manifest-last."""
    manifest = _load_manifest(manifest_path)
    reports = _validate_html_entries(manifest, out_dir)
    _assert_manifest_destination(manifest_path, out_dir, reports)
    parent = out_dir.resolve().parent
    staging = Path(tempfile.mkdtemp(prefix=".report-pdf-staging.", dir=parent))
    rollback = Path(tempfile.mkdtemp(prefix=".report-pdf-rollback.", dir=parent))
    replacements: list[tuple[Path, Path | None]] = []
    preserve_rollback = False
    try:
        staged_htmls: dict[str, Path] = {}
        for entry, _html_path, html_bytes in reports:
            staged_html = _safe_path(staging, entry["path"])
            _atomic_write_bytes(staged_html, html_bytes)
            staged_htmls[entry["path"]] = staged_html

        updates: list[dict[str, Any]] = []
        for entry, _html_path, _html_bytes in reports:
            html_relative = entry["path"]
            staged_pdf = _safe_path(staging, _pdf_path(html_relative))
            if renderer is _render_pdf_locally:
                _render_pdf_locally(staged_htmls[html_relative], staged_pdf, allowed_assets=set(staged_htmls.values()))
            else:
                renderer(staged_htmls[html_relative], staged_pdf)
            try:
                pdf_bytes = staged_pdf.read_bytes()
            except OSError as error:
                raise RuntimeError(f"renderer did not create PDF: {_pdf_path(html_relative)}") from error
            if not pdf_bytes:
                raise RuntimeError(f"renderer created empty PDF: {_pdf_path(html_relative)}")
            updates.append({
                "pdf_path": _pdf_path(html_relative),
                "pdf_bytes": len(pdf_bytes),
                "pdf_sha256": _sha256_bytes(pdf_bytes),
                "pdf_source_content_sha256": entry["content_sha256"],
            })

        updated = copy.deepcopy(manifest)
        for entry, fields in zip(updated["reports"], updates):
            entry.update(fields)

        for index, fields in enumerate(updates):
            destination = _safe_path(out_dir, fields["pdf_path"])
            backup = rollback / f"{index}.backup" if destination.exists() else None
            if backup is not None:
                _durable_backup_copy(destination, backup)
            replacements.append((destination, backup))
            _atomic_write_bytes(destination, _safe_path(staging, fields["pdf_path"]).read_bytes())

        if not manifest_path.is_file():
            raise RuntimeError("live PDF manifest disappeared before commit")
        manifest_backup = rollback / "manifest.json.backup"
        _durable_backup_copy(manifest_path, manifest_backup)
        replacements.append((manifest_path, manifest_backup))
        _atomic_write_bytes(manifest_path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        _verify_published_pdf_snapshot(out_dir, manifest_path, updated)
        return updated
    except Exception as error:
        failures = _rollback_replacements(replacements)
        if failures:
            preserve_rollback = True
            details = "; ".join(str(failure) for failure in failures)
            recovery_paths = [str(backup) for _destination, backup in replacements if backup is not None and backup.exists()]
            recovery = ", ".join(recovery_paths) or str(rollback)
            raise RuntimeError(
                f"PDF publication failed and rollback failed: {details}; recovery backups retained: {recovery}"
            ) from error
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if not preserve_rollback:
            shutil.rmtree(rollback, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish or verify offline research-report PDF companions")
    parser.add_argument("--out-dir", type=Path, default=Path("docs/generated_reports"))
    parser.add_argument("--manifest", type=Path, default=None, help="default: <out-dir>/manifest.json")
    parser.add_argument("--check", action="store_true", help="validate HTML/PDF provenance without rewriting")
    args = parser.parse_args(argv)
    out_dir = args.out_dir.resolve()
    manifest_path = (args.manifest or out_dir / "manifest.json").resolve()
    try:
        if args.check:
            manifest = validate_pdf_companions(out_dir, manifest_path)
            print(f"PDF provenance verified: {len(manifest['reports'])} reports")
        else:
            manifest = publish_pdf_companions(out_dir, manifest_path)
            print(f"PDF companions published: {len(manifest['reports'])} reports")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"PDF companion publication failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
