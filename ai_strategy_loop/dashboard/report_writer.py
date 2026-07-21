# -*- coding: utf-8 -*-
"""Offline, atomic writer for inert research-report HTML and its typed manifest."""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import tempfile
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
    "body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:960px;margin:0 auto;"
    "padding:24px;color:#1a2028;background:#fff;line-height:1.6}"
    "h1{font-size:22px;border-bottom:2px solid #2a3441;padding-bottom:8px}"
    "h2{font-size:16px;margin-top:24px;color:#0b5}"
    "dl.meta{background:#f4f6f8;border:1px solid #dde;border-radius:8px;padding:12px 16px}"
    "dl.meta dt{font-weight:600;color:#556}dl.meta dd{margin:0 0 8px}"
    "nav.tabs{position:sticky;top:0;z-index:2;display:flex;gap:6px;overflow-x:auto;padding:10px 0;background:#fff;border-bottom:1px solid #dde}"
    "nav.tabs a{flex:0 0 auto;padding:6px 10px;border:1px solid #ccd5e2;border-radius:999px;text-decoration:none;font-size:12px}"
    "section{scroll-margin-top:58px}footer{margin-top:32px;padding-top:12px;border-top:1px solid #dde;font-size:12px;color:#667}"
    "a{color:#06c}ul{margin:0;padding-left:18px}"
    "@media(max-width:640px){body{padding:14px}dl.meta{padding:10px}h1{font-size:19px}}"
    "@media print{nav.tabs{position:static;display:none}section{break-inside:avoid}body{max-width:none;padding:0}}"
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        return f'<a href="/reports/view?path={_esc(text)}">{_esc(text)}</a>'
    return _esc(text)


def _render_list_or_text(value: Any, *, as_links: bool = False) -> str:
    if isinstance(value, (list, tuple)):
        if not value:
            return "<p class='muted'>(없음)</p>"
        return "<ul>" + "".join(f"<li>{_render_link_item(item) if as_links else _esc(item)}</li>" for item in value) + "</ul>"
    return f"<p>{_esc(value)}</p>"


def render_report_html(spec: dict) -> str:
    """Render escaped, script-free standard report HTML."""
    title = _esc(spec.get("title") or spec.get("research_id") or "연구 리포트")
    sections = "".join(
        f'<section id="sec-{key}"><h2>{_esc(label)}</h2>{_render_list_or_text(spec.get(key), as_links=key in ("related_docs", "related_commits"))}</section>'
        for key, label in STANDARD_SECTIONS
    )
    tabs = '<nav class="tabs" aria-label="보고서 섹션">' + "".join(
        f'<a href="#sec-{key}">{_esc(label)}</a>' for key, label in STANDARD_SECTIONS
    ) + "</nav>"
    return (
        '<!DOCTYPE html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{_INLINE_STYLE}</style></head><body><article>"
        f"<h1>{title}</h1><dl class=\"meta\"><dt>연구목적</dt><dd>{_esc(spec.get('purpose'))}</dd>"
        f"<dt>일자</dt><dd>{_esc(spec.get('date') or _now_iso())}</dd>"
        f"<dt>research_id</dt><dd>{_esc(spec.get('research_id'))}</dd>"
        f"<dt>step_id</dt><dd>{_esc(spec.get('step_id'))}</dd></dl>{tabs}{sections}"
        f"<footer>생성 {_now_iso()} · trust={_esc(spec.get('trust') or 'derived')} · provenance={_esc(spec.get('provenance') or spec.get('source') or '(미기재)')} · 원문 불변 · 읽기 전용(sandbox·CSP 서빙)</footer>"
        "</article></body></html>"
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
        "limitations": spec.get("limitations"),
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
def normalize_manifest(manifest: dict) -> dict:
    """Read a pre-v1 manifest as v1 metadata without mutating its legacy fields."""
    if manifest.get("schema_version") == REPORT_SCHEMA_VERSION:
        return manifest
    reports = []
    for legacy in manifest.get("reports", []):
        if not isinstance(legacy, dict):
            raise ValueError("legacy manifest contains a non-object report")
        path = legacy.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("legacy manifest report path is invalid")
        research_id = str(legacy.get("research_id") or "report")
        step_id = str(legacy.get("step_id") or "0")
        content_sha256 = str(legacy.get("content_sha256") or legacy.get("sha256") or "")
        if len(content_sha256) != 64:
            raise ValueError("legacy manifest report hash is invalid")
        reports.append({
            **legacy,
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_id": f"step:{research_id}:{step_id}",
            "report_type": "step",
            "research_id": research_id,
            "run_id": research_id,
            "generation": _generation(legacy),
            "cycle": legacy.get("cycle"),
            "status": REPORT_STATUS,
            "publication_status": REPORT_STATUS,
            "generator": REPORT_GENERATOR,
            "content_sha256": content_sha256,
            "source_sha256": str(legacy.get("source_sha256") or _source_sha256(legacy)),
            "toc": legacy.get("toc") or [{"id": f"sec-{key}", "label": label} for key, label in STANDARD_SECTIONS],
            "sha256": content_sha256,
        })
    return {
        **manifest,
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": REPORT_STATUS,
        "generator": REPORT_GENERATOR,
        "reports": reports,
        "count": len(reports),
    }


def _preserved_manifest_entries(manifest_path: str, out_dir: str, replacing: set[str]) -> list[dict]:
    """Keep only previously published entries whose current files still match their hashes."""

    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            previous = normalize_manifest(json.load(handle))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return []

    preserved: list[dict] = []
    out_dir_abs = os.path.abspath(out_dir)
    for entry in previous.get("reports", []):
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        expected = entry.get("content_sha256") or entry.get("sha256")
        if not isinstance(path, str) or path in replacing or not isinstance(expected, str):
            continue
        target = os.path.abspath(os.path.join(out_dir_abs, path))
        if os.path.commonpath((out_dir_abs, target)) != out_dir_abs:
            continue
        try:
            with open(target, "rb") as handle:
                data = handle.read(MAX_BYTES_EACH + 1)
        except OSError:
            continue
        if len(data) > MAX_BYTES_EACH or hashlib.sha256(data).hexdigest() != expected:
            continue
        preserved.append(entry)
    return preserved



def publish_reports(rendered_reports: list[tuple[dict, str, str, str]], out_dir: str, manifest_path: str | None = None) -> dict:
    """Publish reports as a manifest-last snapshot, rolling back live replacements on failure.

    ``rendered_reports`` items are ``(spec, relative_path, html, report_type)``.
    All files are rendered before publication.  Existing live files and manifests
    are copied to a private rollback directory before replacement, so an error
    after any replacement restores the prior manifest/file snapshot.
    """
    if len(rendered_reports) > MAX_REPORTS:
        raise ValueError(f"too many reports ({len(rendered_reports)} > {MAX_REPORTS})")
    relative_paths = [path for _spec, path, _text, _type in rendered_reports]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("report paths must be unique within one publication")
    out_dir = os.path.abspath(out_dir)
    canonical_manifest = os.path.join(out_dir, "manifest.json")
    requested_manifest = os.path.abspath(manifest_path or canonical_manifest)
    new_entries = [report_entry(spec, path, text, report_type=report_type) for spec, path, text, report_type in rendered_reports]
    preserved = _preserved_manifest_entries(canonical_manifest, out_dir, set(relative_paths))
    entries = sorted([*preserved, *new_entries], key=lambda entry: str(entry.get("path") or ""))
    if len(entries) > MAX_REPORTS:
        raise ValueError(f"published report catalog exceeds MAX_REPORTS ({len(entries)} > {MAX_REPORTS})")
    manifest = _manifest(entries)
    parent = os.path.dirname(out_dir)
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=f".{os.path.basename(out_dir)}.staging.", dir=parent)
    rollback = tempfile.mkdtemp(prefix=f".{os.path.basename(out_dir)}.rollback.", dir=parent)
    replacements: list[tuple[str, str | None]] = []
    manifest_backups: dict[str, str | None] = {}

    def backup(path: str, name: str) -> str | None:
        if not os.path.exists(path):
            return None
        saved = os.path.join(rollback, name)
        os.makedirs(os.path.dirname(saved), exist_ok=True)
        shutil.copy2(path, saved)
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
            destination = os.path.abspath(os.path.join(staging, path))
            if os.path.commonpath((staging, destination)) != staging:
                raise ValueError(f"report path escapes output directory: {path}")
            _atomic_write(destination, text)

        os.makedirs(out_dir, exist_ok=True)
        manifest_backups = {
            path: backup(path, f"manifests/{index}.json")
            for index, path in enumerate(dict.fromkeys((canonical_manifest, requested_manifest)))
        }
        for index, path in enumerate(relative_paths):
            source = os.path.join(staging, path)
            destination = os.path.abspath(os.path.join(out_dir, path))
            if os.path.commonpath((out_dir, destination)) != out_dir:
                raise ValueError(f"report path escapes output directory: {path}")
            saved = backup(destination, f"reports/{index}")
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            os.replace(source, destination)
            replacements.append((destination, saved))

        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        _atomic_write(canonical_manifest, manifest_text)
        if requested_manifest != canonical_manifest:
            _atomic_write(requested_manifest, manifest_text)
    except Exception as error:
        rollback_errors = restore(list((path, saved) for path, saved in manifest_backups.items())) + restore(replacements)
        if rollback_errors:
            raise RuntimeError("report publication failed and rollback could not restore the prior snapshot") from error
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
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
