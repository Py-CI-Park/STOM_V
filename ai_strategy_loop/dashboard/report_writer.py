# -*- coding: utf-8 -*-
"""Offline, atomic writer for inert research-report HTML and its typed manifest."""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import tempfile
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Any

REPORT_SCHEMA_VERSION = "stom-research-report-v1"
REPORT_STATUS = "complete"
REPORT_GENERATOR = "ai_strategy_loop.dashboard.report_writer"
STANDARD_SECTIONS: tuple[tuple[str, str], ...] = (
    ("hypothesis", "가설 / 원인"), ("method", "방법"), ("results", "결과 (데이터·차트)"),
    ("analysis", "분석"), ("conclusion", "결론"), ("limits", "한계"),
    ("history", "히스토리 (변경 이력)"), ("related_docs", "관련 문서"),
    ("related_commits", "관련 커밋 / 작업"),
)
MAX_REPORTS = 1000
MAX_BYTES_EACH = 2 * 1024 * 1024
_INLINE_STYLE = (
    ":root{color-scheme:light dark}body{--bg:#fff;--ink:#18212b;--muted:#556;--surface:#f4f6f8;--border:#cfd8e3;--accent:#087f5b;--link:#065cc2;font-family:system-ui,'Malgun Gothic',sans-serif;max-width:1040px;margin:0 auto;padding:28px;color:var(--ink);background:var(--bg);line-height:1.65}"
    "body:has(#report-theme-light:checked){color-scheme:light}body:has(#report-theme-dark:checked){color-scheme:dark;--bg:#111820;--ink:#e6edf3;--muted:#b6c2ce;--surface:#19232e;--border:#3b4a59;--accent:#6ee7b7;--link:#8ab4f8}@media(prefers-color-scheme:dark){body:has(#report-theme-system:checked){color-scheme:dark;--bg:#111820;--ink:#e6edf3;--muted:#b6c2ce;--surface:#19232e;--border:#3b4a59;--accent:#6ee7b7;--link:#8ab4f8}}"
    "h1{font-size:26px;border-bottom:2px solid var(--ink);padding-bottom:10px}h2{font-size:17px;margin-top:28px;color:var(--accent)}.summary,.kpis,.callout,dl.meta{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px 16px}.kpis{display:flex;gap:12px;flex-wrap:wrap}.kpis div{min-width:130px}.kpis b{display:block;font-size:18px}.callout{border-left:4px solid var(--accent)}dl.meta dt{font-weight:600;color:var(--muted)}dl.meta dd{margin:0 0 8px}"
    "nav.tabs{position:sticky;top:0;z-index:2;display:flex;gap:6px;overflow-x:auto;padding:10px 0;background:var(--bg);border-bottom:1px solid var(--border)}nav.tabs a{flex:0 0 auto;padding:6px 10px;border:1px solid var(--border);border-radius:999px;text-decoration:none;font-size:12px}.report-theme{display:flex;align-items:center;gap:8px;justify-content:flex-end;font-size:12px;color:var(--muted)}.report-theme fieldset{display:flex;gap:8px;margin:0;padding:4px 8px;border:1px solid var(--border);border-radius:999px}.report-theme legend{padding:0 4px}.report-theme label{cursor:pointer}section{scroll-margin-top:58px}footer{margin-top:32px;padding-top:12px;border-top:1px solid var(--border);font-size:12px;color:var(--muted)}a{color:var(--link)}ul{margin:0;padding-left:18px}pre,code{font-family:ui-monospace,Consolas,monospace;overflow:auto}pre{padding:12px;background:var(--surface);border-radius:6px}table{display:block;max-width:100%;overflow:auto;border-collapse:collapse}th,td{border:1px solid var(--border);padding:6px;text-align:left}"
    "@media(max-width:640px){body{padding:14px}h1{font-size:20px}.report-theme{justify-content:flex-start}}@media print{body{color:#111;background:#fff;max-width:none;padding:0}nav.tabs,.report-theme{position:static;display:none}.summary,.kpis,.callout,dl.meta,pre{background:#fff;color:#111}section{break-inside:avoid}}"
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolved_existing_path(path: str) -> str:
    """Resolve links in every existing parent while retaining a non-existent leaf."""
    path = os.path.abspath(path)
    missing: list[str] = []
    while not os.path.lexists(path):
        parent, leaf = os.path.split(path)
        if parent == path:
            break
        missing.append(leaf)
        path = parent
    resolved = os.path.realpath(path)
    for leaf in reversed(missing):
        resolved = os.path.join(resolved, leaf)
    return os.path.normcase(os.path.normpath(resolved))
_CANONICAL_ENTRY_KEYS = {
    "schema_version", "report_id", "report_type", "research_id", "run_id",
    "generation", "cycle", "status", "publication_status", "generator", "path",
    "content_sha256", "source_sha256", "bytes", "generated_at", "trust",
    "provenance", "toc", "profile", "evidence", "decision", "limitations",
    "step_id", "sha256",
}
_PDF_ENTRY_KEYS = {"pdf_path", "pdf_bytes", "pdf_sha256", "pdf_source_content_sha256"}
_LEGACY_MANIFEST_KEYS = {"generated_at", "count", "reports"}
_LEGACY_ENTRY_KEYS = {"research_id", "step_id", "path", "sha256", "bytes", "trust"}


def _is_exact_int(value: Any, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return value == value and value not in (float("inf"), float("-inf"))
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _canonical_report_relative_path(path: str) -> str:
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or not path.endswith(".html")
        or path.startswith("/")
    ):
        raise ValueError("report destination must be a canonical relative POSIX HTML path")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("report destination must be a canonical relative POSIX HTML path")
    return path


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("manifest contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"manifest contains invalid JSON constant: {value}")


def _contained_report_path(out_dir: str, path: str) -> str:
    canonical = _canonical_report_relative_path(path)
    root = _resolved_existing_path(out_dir)
    candidate = _resolved_existing_path(os.path.join(root, *canonical.split("/")))
    try:
        contained = os.path.commonpath((root, candidate)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"report path escapes output directory: {path}")
    return candidate


def verified_report_html_path(entry: dict, out_dir: str) -> tuple[str, bytes]:
    """Return registered HTML bytes only when their manifest provenance is intact."""
    if not isinstance(entry, dict) or entry.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("report entry is not a registered stom-research-report-v1 record")
    path = entry.get("path")
    expected_hash = entry.get("content_sha256")
    expected_bytes = entry.get("bytes")
    if (
        not isinstance(path, str)
        or not _is_lower_sha256(expected_hash)
        or not _is_exact_int(expected_bytes)
        or expected_bytes > MAX_BYTES_EACH
    ):
        raise ValueError("report entry HTML provenance is invalid")
    target = _contained_report_path(out_dir, path)
    try:
        with open(target, "rb") as handle:
            data = handle.read(MAX_BYTES_EACH + 1)
    except OSError as error:
        raise ValueError(f"registered report HTML is unreadable: {path}") from error
    if len(data) > MAX_BYTES_EACH or len(data) != expected_bytes:
        raise ValueError(f"registered report HTML bytes mismatch: {path}")
    if _sha256_bytes(data) != expected_hash:
        raise ValueError(f"registered report HTML content_sha256 mismatch: {path}")
    return target, data

def verified_report_pdf_path(entry: dict, out_dir: str) -> tuple[str, bytes]:
    """Return registered PDF bytes only when their HTML-bound provenance is intact."""
    if not isinstance(entry, dict) or entry.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("report entry is not a registered stom-research-report-v1 record")
    html_path = entry.get("path")
    pdf_path = entry.get("pdf_path")
    expected_bytes = entry.get("pdf_bytes")
    expected_hash = entry.get("pdf_sha256")
    if (
        not isinstance(html_path, str)
        or pdf_path != html_path[:-5] + ".pdf"
        or entry.get("pdf_source_content_sha256") != entry.get("content_sha256")
        or not _is_exact_int(expected_bytes, minimum=1)
        or not _is_lower_sha256(expected_hash)
    ):
        raise ValueError("report entry PDF provenance is invalid")
    html_target = _contained_report_path(out_dir, html_path)
    root = _resolved_existing_path(out_dir)
    target = _resolved_existing_path(os.path.splitext(html_target)[0] + ".pdf")
    try:
        contained = os.path.commonpath((root, target)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"registered report PDF escapes output directory: {pdf_path}")
    try:
        with open(target, "rb") as handle:
            data = handle.read(MAX_BYTES_EACH + 1)
    except OSError as error:
        raise ValueError(f"registered report PDF is unreadable: {pdf_path}") from error
    if len(data) > MAX_BYTES_EACH or len(data) != expected_bytes:
        raise ValueError(f"registered report PDF bytes mismatch: {pdf_path}")
    if _sha256_bytes(data) != expected_hash:
        raise ValueError(f"registered report PDF pdf_sha256 mismatch: {pdf_path}")
    return target, data




def _atomic_write(path: str, text: str) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _slug(value: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_") else "-" for c in str(value)).strip("-")[:80] or "report"


def _render_link_item(item: Any) -> str:
    text = "" if item is None else str(item)
    if text.endswith(".html") and ".." not in text and not text.startswith(("http://", "https://", "/")):
        return f'<a href="/reports/view?path={quote(text, safe="")}">{_esc(text)}</a>'
    return _esc(text)


def _render_list_or_text(value: Any, *, as_links: bool = False) -> str:
    if isinstance(value, (list, tuple)):
        if not value:
            return "<p class='muted'>(없음)</p>"
        return "<ul>" + "".join(f"<li>{_render_link_item(item) if as_links else _esc(item)}</li>" for item in value) + "</ul>"
    return f"<p>{_esc(value)}</p>"


def render_report_html(spec: dict) -> str:
    """Render escaped, script-free standard report HTML."""
    normalized = dict(spec)
    if normalized.get("limitations") is None and normalized.get("limits") is not None:
        normalized["limitations"] = normalized["limits"]
    normalized["limits"] = normalized.get("limitations")
    title = _esc(normalized.get("title") or normalized.get("research_id") or "연구 리포트")
    sections = "".join(
        f'<section id="sec-{key}"><h2>{_esc(label)}</h2>{_render_list_or_text(normalized.get(key), as_links=key in ("related_docs", "related_commits"))}</section>'
        for key, label in STANDARD_SECTIONS
    )
    tabs = '<nav class="tabs" aria-label="보고서 섹션">' + "".join(
        f'<a href="#sec-{key}">{_esc(label)}</a>' for key, label in STANDARD_SECTIONS
    ) + "</nav>"
    evidence = normalized.get("evidence") if isinstance(normalized.get("evidence"), dict) else {}
    kpis = "".join(f"<div><small>{_esc(key)}</small><b>{_esc(value)}</b></div>" for key, value in list(evidence.items())[:8])
    summary = normalized.get("executive_summary") or normalized.get("decision") or normalized.get("conclusion")
    return (
        '<!DOCTYPE html>\n<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{_INLINE_STYLE}</style></head><body><article><div class=\"report-theme\"><fieldset><legend>표시 모드</legend><label><input id=\"report-theme-system\" type=\"radio\" name=\"report-theme\" checked> 시스템</label><label><input id=\"report-theme-light\" type=\"radio\" name=\"report-theme\"> 밝게</label><label><input id=\"report-theme-dark\" type=\"radio\" name=\"report-theme\"> 어둡게</label></fieldset></div><h1>{title}</h1>"
        f"<div class=\"summary\"><b>경영 요약</b>{_render_list_or_text(summary)}</div>"
        f"{'<div class=\"kpis\"><b>근거 지표</b>' + kpis + '</div>' if kpis else ''}"
        f"<dl class=\"meta\"><dt>연구목적</dt><dd>{_esc(normalized.get('purpose'))}</dd><dt>일자</dt><dd>{_esc(normalized.get('date') or _now_iso())}</dd><dt>research_id</dt><dd>{_esc(normalized.get('research_id'))}</dd><dt>step_id</dt><dd>{_esc(normalized.get('step_id'))}</dd></dl>{tabs}{sections}"
        f"<footer>생성 {_now_iso()} · trust={_esc(normalized.get('trust') or 'derived')} · provenance={_esc(normalized.get('provenance') or normalized.get('source') or '(미기재)')} · 원문 불변 · 읽기 전용(sandbox·CSP 서빙)</footer></article></body></html>"
    )


def _source_sha256(spec: dict) -> str:
    """Hash the supplied source record, not rendered HTML or mutable output metadata."""
    source = {key: value for key, value in spec.items() if key not in {"generated_at", "content_sha256", "sha256", "bytes"}}
    return _sha256(json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str))


def _generation(spec: dict) -> int | None:
    value = spec.get("generation", spec.get("gen"))
    if value is None:
        step = str(spec.get("step_id") or "")
        value = step[3:] if step.startswith("gen") else None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def report_entry(spec: dict, path: str, html_text: str, *, report_type: str = "step") -> dict:
    data = html_text.encode("utf-8")
    if len(data) > MAX_BYTES_EACH:
        raise ValueError(f"report exceeds MAX_BYTES_EACH ({len(data)} > {MAX_BYTES_EACH})")
    research_id = str(spec.get("research_id") or spec.get("run_id") or spec.get("title") or "report")
    step_id = str(spec.get("step_id") or "0")
    content_sha256 = _sha256(html_text)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": str(spec.get("report_id") or f"{report_type}:{research_id}:{step_id}"),
        "report_type": report_type,
        "research_id": research_id,
        "run_id": str(spec.get("run_id") or research_id),
        "generation": _generation(spec),
        "cycle": spec.get("cycle"),
        "status": str(spec.get("status") or REPORT_STATUS),
        "publication_status": REPORT_STATUS,
        "generator": str(spec.get("generator") or REPORT_GENERATOR),
        "path": path,
        "content_sha256": content_sha256,
        "source_sha256": str(spec.get("source_sha256") or _source_sha256(spec)),
        "bytes": len(data),
        "generated_at": _now_iso(),
        "trust": str(spec.get("trust") or "derived"),
        "provenance": spec.get("provenance") or spec.get("source") or None,
        "toc": spec.get("toc") or [{"id": f"sec-{key}", "label": label} for key, label in STANDARD_SECTIONS],
        "profile": spec.get("profile"),
        "evidence": spec.get("evidence"),
        "decision": spec.get("decision"),
        "limitations": spec.get("limitations", spec.get("limits")),
        # Legacy aliases are retained for consumers of the pre-v1 manifest.
        "step_id": step_id,
        "sha256": content_sha256,
    }


def _manifest(entries: list[dict]) -> dict:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": REPORT_STATUS,
        "generator": REPORT_GENERATOR,
        "generated_at": _now_iso(),
        "count": len(entries),
        "limits": {"max_reports": MAX_REPORTS, "max_bytes_each": MAX_BYTES_EACH},
        "reports": entries,
    }
def _validate_v1_entry(entry: Any) -> dict:
    if not isinstance(entry, dict) or set(entry) not in (_CANONICAL_ENTRY_KEYS, _CANONICAL_ENTRY_KEYS | _PDF_ENTRY_KEYS):
        raise ValueError("v1 manifest entry has an invalid field set")
    strings = ("report_id", "report_type", "research_id", "run_id", "status", "generator", "generated_at", "trust", "step_id")
    if (
        entry["schema_version"] != REPORT_SCHEMA_VERSION
        or entry["publication_status"] != REPORT_STATUS
        or any(not isinstance(entry[key], str) or not entry[key] for key in strings)
        or not _is_lower_sha256(entry["content_sha256"])
        or not _is_lower_sha256(entry["source_sha256"])
        or entry["sha256"] != entry["content_sha256"]
        or not _is_exact_int(entry["bytes"])
        or entry["bytes"] > MAX_BYTES_EACH
        or (entry["generation"] is not None and not _is_exact_int(entry["generation"]))
        or (entry["provenance"] is not None and not isinstance(entry["provenance"], str))
        or any(not _is_json_value(entry[key]) for key in ("cycle", "profile", "evidence", "decision", "limitations"))
        or not isinstance(entry["toc"], list)
        or any(not isinstance(item, dict) or set(item) != {"id", "label"} or not all(isinstance(item[key], str) for key in item) for item in entry["toc"])
    ):
        raise ValueError("v1 manifest entry provenance is invalid")
    _canonical_report_relative_path(entry["path"])
    if _PDF_ENTRY_KEYS <= set(entry) and (
        entry["pdf_path"] != entry["path"][:-5] + ".pdf"
        or not _is_exact_int(entry["pdf_bytes"], minimum=1)
        or not _is_lower_sha256(entry["pdf_sha256"])
        or entry["pdf_source_content_sha256"] != entry["content_sha256"]
    ):
        raise ValueError("v1 manifest PDF provenance is invalid")
    return entry


def _validate_v1_manifest(manifest: Any) -> dict:
    required = {"schema_version", "status", "generator", "generated_at", "count", "limits", "reports"}
    if (
        not isinstance(manifest, dict)
        or set(manifest) != required
        or manifest["schema_version"] != REPORT_SCHEMA_VERSION
        or manifest["status"] != REPORT_STATUS
        or manifest["generator"] != REPORT_GENERATOR
        or not isinstance(manifest["generated_at"], str)
        or not manifest["generated_at"]
        or not _is_exact_int(manifest["count"])
        or not isinstance(manifest["reports"], list)
        or manifest["count"] != len(manifest["reports"])
        or len(manifest["reports"]) > MAX_REPORTS
        or not isinstance(manifest["limits"], dict)
        or manifest["limits"] != {"max_reports": MAX_REPORTS, "max_bytes_each": MAX_BYTES_EACH}
    ):
        raise ValueError("v1 manifest envelope is invalid")
    for entry in manifest["reports"]:
        _validate_v1_entry(entry)
    return manifest

def normalize_manifest(manifest: dict) -> dict:
    """Normalize the one recognized schema-less legacy manifest shape to v1."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    if "schema_version" in manifest:
        if manifest["schema_version"] != REPORT_SCHEMA_VERSION:
            raise ValueError("manifest schema_version is not recognized")
        return _validate_v1_manifest(manifest)
    if (
        set(manifest) != _LEGACY_MANIFEST_KEYS
        or not isinstance(manifest["generated_at"], str)
        or not manifest["generated_at"]
        or not _is_exact_int(manifest["count"])
        or not isinstance(manifest["reports"], list)
        or manifest["count"] != len(manifest["reports"])
        or len(manifest["reports"]) > MAX_REPORTS
    ):
        raise ValueError("manifest is not a recognized schema-less legacy shape")
    reports = []
    for legacy in manifest["reports"]:
        if (
            not isinstance(legacy, dict)
            or set(legacy) != _LEGACY_ENTRY_KEYS
            or not all(isinstance(legacy[key], str) and legacy[key] for key in ("research_id", "step_id", "trust"))
            or not _is_lower_sha256(legacy["sha256"])
            or not _is_exact_int(legacy["bytes"])
            or legacy["bytes"] > MAX_BYTES_EACH
        ):
            raise ValueError("legacy manifest report is invalid")
        path = _canonical_report_relative_path(legacy["path"])
        research_id = legacy["research_id"]
        step_id = legacy["step_id"]
        reports.append({
            **legacy,
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_id": f"step:{research_id}:{step_id}",
            "report_type": "step",
            "run_id": research_id,
            "generated_at": manifest["generated_at"],
            "provenance": None,
            "generation": _generation(legacy),
            "cycle": None,
            "status": REPORT_STATUS,
            "publication_status": REPORT_STATUS,
            "generator": REPORT_GENERATOR,
            "path": path,
            "content_sha256": legacy["sha256"],
            "source_sha256": _source_sha256(legacy),
            "toc": [{"id": f"sec-{key}", "label": label} for key, label in STANDARD_SECTIONS],
            "profile": None,
            "evidence": None,
            "decision": None,
            "limitations": None,
        })
    return _validate_v1_manifest({
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": REPORT_STATUS,
        "generator": REPORT_GENERATOR,
        "generated_at": manifest["generated_at"],
        "count": len(reports),
        "limits": {"max_reports": MAX_REPORTS, "max_bytes_each": MAX_BYTES_EACH},
        "reports": reports,
    })


def _load_manifest(path: str, out_dir: str, manifest_paths: set[str]) -> list[dict] | None:
    """Load and fully verify an existing snapshot; absence alone permits first publication."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(
                handle,
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_json_constant,
            )
    except FileNotFoundError:
        if os.path.lexists(path):
            raise ValueError(f"existing manifest is unreadable or corrupt: {path}")
        return None
    except (OSError, TypeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"existing manifest is unreadable or corrupt: {path}") from error
    if not isinstance(raw, dict):
        raise ValueError("existing manifest must be an object")
    try:
        manifest = normalize_manifest(raw)
    except (TypeError, ValueError, KeyError) as error:
        raise ValueError(f"existing manifest is invalid: {path}") from error
    reports = manifest.get("reports")
    if not isinstance(reports, list):
        raise ValueError("existing manifest reports must be a list")

    destinations: set[str] = set()
    for entry in reports:
        target, _data = verified_report_html_path(entry, out_dir)
        if target in manifest_paths:
            raise ValueError("registered report destination collides with a manifest")
        if target in destinations:
            raise ValueError("existing manifest has duplicate report destinations")
        destinations.add(target)
        if _PDF_ENTRY_KEYS <= set(entry):
            verified_report_pdf_path(entry, out_dir)
    return reports


def _verify_published_snapshot(
    manifest: dict,
    out_dir: str,
    manifest_paths: set[str],
    manifest_files: tuple[str, ...],
) -> None:
    """Verify the manifest files and every registered report after publication."""
    expected = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    for path in manifest_files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                if handle.read() != expected:
                    raise ValueError("published manifest bytes do not match the completed snapshot")
        except OSError as error:
            raise ValueError(f"published manifest is unreadable: {path}") from error
    reports = manifest.get("reports")
    if not isinstance(reports, list) or len(reports) != manifest.get("count"):
        raise ValueError("published manifest report catalog is invalid")
    destinations: set[str] = set()
    for entry in reports:
        target, _data = verified_report_html_path(entry, out_dir)
        if target in manifest_paths:
            raise ValueError("published report destination collides with a manifest")
        if target in destinations:
            raise ValueError("published manifest has duplicate report destinations")
        destinations.add(target)
        if _PDF_ENTRY_KEYS <= set(entry):
            verified_report_pdf_path(entry, out_dir)



def publish_reports(rendered_reports: list[tuple[dict, str, str, str]], out_dir: str, manifest_path: str | None = None) -> dict:
    """Publish reports as a manifest-last snapshot, rolling back live replacements on failure.

    ``rendered_reports`` items are ``(spec, relative_path, html, report_type)``.
    All files are rendered before publication.  Existing live files and manifests
    are copied to a private rollback directory before replacement, so an error
    after any replacement restores the prior manifest/file snapshot.
    """
    if len(rendered_reports) > MAX_REPORTS:
        raise ValueError(f"too many reports ({len(rendered_reports)} > {MAX_REPORTS})")
    out_dir = os.path.abspath(out_dir)
    canonical_manifest = _resolved_existing_path(os.path.join(out_dir, "manifest.json"))
    requested_manifest = _resolved_existing_path(manifest_path or canonical_manifest)
    manifest_files = tuple(dict.fromkeys((canonical_manifest, requested_manifest)))
    manifest_paths = set(manifest_files)

    relative_paths = [path for _spec, path, _text, _type in rendered_reports]
    destinations = [_contained_report_path(out_dir, path) for path in relative_paths]
    if len(destinations) != len(set(destinations)):
        raise ValueError("report destinations must be unique within one publication")
    if any(destination in manifest_paths for destination in destinations):
        raise ValueError("report destination collides with a manifest")

    canonical_previous = _load_manifest(canonical_manifest, out_dir, manifest_paths)
    requested_previous = (
        canonical_previous
        if requested_manifest == canonical_manifest
        else _load_manifest(requested_manifest, out_dir, manifest_paths)
    )
    if canonical_previous is not None and requested_previous is not None and canonical_previous != requested_previous:
        raise ValueError("canonical and requested manifests disagree")
    previous = canonical_previous if canonical_previous is not None else (requested_previous or [])
    replacing = set(destinations)
    preserved = [
        entry
        for entry in previous
        if _contained_report_path(out_dir, entry["path"]) not in replacing
    ]
    new_entries = [
        report_entry(spec, path, text, report_type=report_type)
        for spec, path, text, report_type in rendered_reports
    ]
    entries = sorted([*preserved, *new_entries], key=lambda entry: str(entry.get("path") or ""))
    if len(entries) > MAX_REPORTS:
        raise ValueError(f"published report catalog exceeds MAX_REPORTS ({len(entries)} > {MAX_REPORTS})")
    manifest = _manifest(entries)
    _validate_v1_manifest(manifest)
    parent = os.path.dirname(out_dir)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=f".{os.path.basename(out_dir)}.staging.", dir=parent)
    rollback = tempfile.mkdtemp(prefix=f".{os.path.basename(out_dir)}.rollback.", dir=parent)
    replacements: list[tuple[str, str | None]] = []
    manifest_backups: dict[str, str | None] = {}
    preserve_rollback = False

    def backup(path: str, name: str) -> str | None:
        if not os.path.exists(path):
            return None
        saved = os.path.join(rollback, name)
        os.makedirs(os.path.dirname(saved), exist_ok=True)
        with open(path, "rb") as source, open(saved, "xb") as recovery:
            shutil.copyfileobj(source, recovery)
            recovery.flush()
            os.fsync(recovery.fileno())
        return saved

    def restore(replaced: list[tuple[str, str | None]]) -> list[Exception]:
        errors: list[Exception] = []
        for destination, saved in reversed(replaced):
            try:
                if saved is None:
                    if os.path.exists(destination):
                        os.remove(destination)
                else:
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    os.replace(saved, destination)
            except OSError as error:
                errors.append(error)
        return errors

    try:
        for _spec, path, text, _type in rendered_reports:
            _atomic_write(_contained_report_path(staging, path), text)

        os.makedirs(out_dir, exist_ok=True)
        manifest_backups = {
            path: backup(path, f"manifests/{index}")
            for index, path in enumerate(manifest_files)
        }
        for index, ((_spec, path, _text, _type), destination) in enumerate(zip(rendered_reports, destinations)):
            source = _contained_report_path(staging, path)
            saved = backup(destination, f"reports/{index}")
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            os.replace(source, destination)
            replacements.append((destination, saved))

        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        _atomic_write(canonical_manifest, manifest_text)
        if requested_manifest != canonical_manifest:
            _atomic_write(requested_manifest, manifest_text)
        _verify_published_snapshot(manifest, out_dir, manifest_paths, manifest_files)
    except Exception as error:
        rollback_errors = restore(list((path, saved) for path, saved in manifest_backups.items())) + restore(replacements)
        if rollback_errors:
            preserve_rollback = True
            details = "; ".join(str(rollback_error) for rollback_error in rollback_errors)
            recovery_paths = [
                saved
                for _destination, saved in [*manifest_backups.items(), *replacements]
                if saved is not None and os.path.exists(saved)
            ]
            recovery = ", ".join(recovery_paths) or rollback
            raise RuntimeError(
                f"report publication failed and rollback could not restore the prior snapshot: {details}; "
                f"recovery backups retained: {recovery}"
            ) from error
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if not preserve_rollback:
            shutil.rmtree(rollback, ignore_errors=True)
    return manifest


def write_report(spec: dict, out_dir: str) -> dict:
    """Backward-compatible one-report writer without replacing sibling reports."""
    research_id = str(spec.get("research_id") or spec.get("title") or "report")
    step_id = str(spec.get("step_id") or "0")
    path = f"{_slug(research_id)}__{_slug(step_id)}.html"
    html_text = render_report_html(spec)
    _atomic_write(os.path.join(out_dir, path), html_text)
    return report_entry(spec, path, html_text)


def write_reports(specs: list, out_dir: str, manifest_path: str) -> dict:
    """Backward-compatible step report batch writer using atomic snapshot publication."""
    rendered = []
    for spec in specs:
        research_id = str(spec.get("research_id") or spec.get("title") or "report")
        step_id = str(spec.get("step_id") or "0")
        rendered.append((spec, f"{_slug(research_id)}__{_slug(step_id)}.html", render_report_html(spec), "step"))
    return publish_reports(rendered, out_dir, manifest_path)
