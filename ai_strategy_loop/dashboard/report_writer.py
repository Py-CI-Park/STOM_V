# -*- coding: utf-8 -*-
"""Offline, atomic writer for inert research-report HTML and its typed manifest."""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import tempfile
import re
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Any, TypedDict

REPORT_SCHEMA_VERSION = "stom-research-report-v1"
REPORT_STATUS = "complete"
REPORT_GENERATOR = "ai_strategy_loop.dashboard.report_writer"
RENDERER_VERSION = "v5.11"
TEMPLATE_IDS = ("executive", "quant_research", "research_journal")
THEMES = ("system", "light", "dark", "print")
STANDARD_SECTIONS: tuple[tuple[str, str], ...] = (
    ("hypothesis", "가설 / 원인"), ("method", "방법"), ("results", "결과 (데이터·차트)"),
    ("analysis", "분석"), ("conclusion", "결론"), ("limits", "한계"),
    ("history", "히스토리 (변경 이력)"), ("related_docs", "관련 문서"),
    ("related_commits", "관련 커밋 / 작업"),
)
MAX_REPORTS = 1000
MAX_BYTES_EACH = 2 * 1024 * 1024
_INLINE_STYLE = (
    ":root{color-scheme:light dark;--bg:#fff;--ink:#18212b;--muted:#52606d;--surface:#f5f7fa;--border:#cbd5e1;--accent:#087f5b;--link:#075dc4}"
    "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,'Malgun Gothic',sans-serif}.layout{max-width:1440px;margin:auto;padding:clamp(14px,3vw,48px);display:grid;grid-template-columns:minmax(160px,230px) minmax(0,1fr);gap:clamp(16px,3vw,42px)}article{min-width:0}.toc{position:sticky;top:0;align-self:start;padding:14px 0}.toc a{display:block;padding:5px 8px;color:var(--muted);text-decoration:none;border-left:2px solid transparent}.toc a:hover,.toc a:focus{color:var(--accent);border-color:var(--accent)}.theme{font-size:12px;color:var(--muted);margin-bottom:12px}.theme label{margin-right:8px}.cover,.hero,.card,.callout,.decision,dl.meta{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:clamp(14px,2vw,28px);margin-bottom:20px}.cover{border-top:5px solid var(--accent)}.eyebrow{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.1em}.hero h1{font-size:clamp(25px,4vw,46px);line-height:1.15;margin:.2em 0}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin:20px 0}.kpi{padding:14px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}.kpi b{display:block;font-size:22px}.callout{border-left:5px solid var(--accent)}.decision{border-left:5px solid #b7791f;font-weight:600}h2{font-size:21px;margin:38px 0 12px;color:var(--accent);scroll-margin-top:20px}h3{font-size:16px}section{scroll-margin-top:20px}.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px}table{width:100%;min-width:520px;border-collapse:collapse}th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}th{background:var(--surface)}.signed-positive{color:#087f5b}.signed-negative,.risk-high{color:#b42318}.status-pass{color:#087f5b}.status-fail{color:#b42318}svg.chart{display:block;max-width:100%;height:auto;border:1px solid var(--border);border-radius:8px;background:var(--surface)}dl.meta{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px}dl.meta dt{font-weight:700;color:var(--muted)}dl.meta dd{margin:0}a{color:var(--link)}footer{font-size:12px;color:var(--muted);margin-top:34px}.template-journal .history-item{border-left:2px solid var(--border);padding:4px 0 12px 14px}.template-quant_research .hero{border-radius:0}.template-executive .method-detail{display:none}body:has(#report-theme-light:checked){color-scheme:light}body:has(#report-theme-dark:checked){color-scheme:dark;--bg:#101820;--ink:#e6edf3;--muted:#b6c2ce;--surface:#19232e;--border:#3b4a59;--accent:#6ee7b7;--link:#8ab4f8}@media(prefers-color-scheme:dark){body:has(#report-theme-system:checked){color-scheme:dark;--bg:#101820;--ink:#e6edf3;--muted:#b6c2ce;--surface:#19232e;--border:#3b4a59;--accent:#6ee7b7;--link:#8ab4f8}}@media(max-width:700px){.layout{display:block}.toc{position:sticky;z-index:2;background:var(--bg);overflow-x:auto;white-space:nowrap;border-bottom:1px solid var(--border);margin-bottom:18px}.toc a{display:inline-block}.theme{white-space:nowrap}}@media print{body{color:#111;background:#fff}.layout{display:block;padding:0}.toc,.theme{display:none}.cover,.hero,.card,.callout,.decision,dl.meta{background:#fff}.page-break{break-before:page}.print-break{break-before:page}section{break-inside:avoid}}"
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
_RENDERED_ENTRY_KEYS = _CANONICAL_ENTRY_KEYS | {"renderer_version", "template_id", "theme"}
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


class ReportBlock(TypedDict, total=False):
    """Escaped-data document block accepted by the offline renderer."""
    type: str
    id: str
    title: str
    text: Any
    items: list[Any]
    rows: list[list[Any]]
    columns: list[str]
    values: dict[str, Any]
    svg: str
    level: str
    page_break: bool


def _safe_svg(value: Any) -> str:
    """Allow only inert inline SVG produced by the adapter; reject executable markup."""
    svg = "" if value is None else str(value)
    if not svg.lstrip().startswith("<svg") or re.search(r"<script\b|<foreignobject\b|on[a-z]+\s*=|(?:href|xlink:href)\s*=|javascript:", svg, re.IGNORECASE):
        return "<p class='muted'>(차트를 안전하게 표시할 수 없음)</p>"
    return svg


def _cell_class(value: Any) -> str:
    text = str(value).strip().lower()
    if text.startswith("-"):
        return "signed-negative"
    if text.startswith("+"):
        return "signed-positive"
    if text in {"pass", "passed", "complete", "통과"}:
        return "status-pass"
    if text in {"fail", "failed", "blocked", "high", "실패", "높음"}:
        return "status-fail risk-high"
    return ""


def _render_block(block: ReportBlock) -> str:
    kind, block_id = block.get("type", "text"), _esc(block.get("id", "section"))
    title = _esc(block.get("title", ""))
    if kind == "kpis":
        return '<div class="kpis">' + "".join(f'<div class="kpi"><small>{_esc(key)}</small><b>{_esc(value)}</b></div>' for key, value in block.get("values", {}).items()) + "</div>"
    if kind == "table":
        columns = block.get("columns", [])
        rows = block.get("rows", [])
        head = "".join(f"<th scope=\"col\">{_esc(column)}</th>" for column in columns)
        body = "".join("<tr>" + "".join(f'<td class="{_cell_class(cell)}">{_esc(cell)}</td>' for cell in row) + "</tr>" for row in rows)
        return f'<section id="{block_id}" class="card"><h2>{title}</h2><div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>'
    if kind == "svg":
        return f'<section id="{block_id}"><h2>{title}</h2>{_safe_svg(block.get("svg"))}</section>'
    if kind == "history":
        return f'<section id="{block_id}"><h2>{title}</h2>' + "".join(f'<div class="history-item">{_esc(item)}</div>' for item in block.get("items", [])) + "</section>"
    if kind == "links":
        return f'<section id="{block_id}"><h2>{title}</h2>{_render_list_or_text(block.get("items", []), as_links=True)}</section>'
    css = "decision" if kind == "decision" else "callout" if kind in {"callout", "finding", "limitations", "provenance"} else "card"
    content = _render_list_or_text(block.get("items") if "items" in block else block.get("text"))
    return f'<section id="{block_id}" class="{css}{" print-break" if block.get("page_break") else ""}"><h2>{title}</h2>{content}</section>'


def _document_blocks(spec: dict) -> list[ReportBlock]:
    blocks = spec.get("blocks")
    if isinstance(blocks, list):
        return [block for block in blocks if isinstance(block, dict) and isinstance(block.get("type"), str)]
    return [
        {
            "type": "links" if key in {"related_docs", "related_commits"} else "text",
            "id": f"sec-{key}",
            "title": label,
            **({"items": spec.get(key)} if key in {"related_docs", "related_commits"} else {"text": spec.get(key)}),
        }
        for key, label in STANDARD_SECTIONS
    ]


def render_report_html(spec: dict) -> str:
    """Render a typed, inert document. All data is escaped; SVG is explicitly inert."""
    normalized = dict(spec)
    if normalized.get("limitations") is None and normalized.get("limits") is not None:
        normalized["limitations"] = normalized["limits"]
    normalized["limits"] = normalized.get("limitations")
    template_id = str(normalized.get("template_id") or "executive")
    if template_id not in TEMPLATE_IDS:
        raise ValueError(f"unknown report template_id: {template_id}")
    theme = str(normalized.get("theme") or "system")
    if theme not in THEMES:
        raise ValueError(f"unknown report theme: {theme}")
    title = _esc(normalized.get("title") or normalized.get("research_id") or "연구 리포트")
    blocks = _document_blocks(normalized)
    toc = [{"id": str(block.get("id", "")), "label": str(block.get("title", ""))} for block in blocks if block.get("id") and block.get("title")]
    navigation = "".join(f'<a href="#{_esc(item["id"])}">{_esc(item["label"])}</a>' for item in toc)
    kpis = normalized.get("kpis") or (normalized.get("evidence") if isinstance(normalized.get("evidence"), dict) else {})
    hero = f'<header class="hero"><div class="eyebrow">{_esc(template_id.replace("_", " ").upper())} · {RENDERER_VERSION}</div><h1>{title}</h1><p>{_esc(normalized.get("executive_summary") or normalized.get("purpose") or "")}</p></header>'
    cover = f'<header class="cover"><div class="eyebrow">SOURCE-BACKED RESEARCH REPORT</div><h1>{title}</h1><p>연구 ID: {_esc(normalized.get("research_id"))}</p></header>'
    body = "".join(_render_block(block) for block in blocks)
    if template_id == "executive":
        body = f'<section id="executive-summary" class="card"><h2>경영 요약</h2>{_render_list_or_text(normalized.get("executive_summary") or normalized.get("decision"))}</section>' + _render_block({"type": "kpis", "values": kpis}) + body
    elif template_id == "quant_research":
        body = _render_block({"type": "kpis", "values": kpis}) + body
    else:
        body = '<section id="journal-context" class="card"><h2>연구 맥락</h2>' + _render_list_or_text(normalized.get("purpose")) + "</section>" + body
    meta = f'<dl class="meta"><dt>template_id</dt><dd>{_esc(template_id)}</dd><dt>theme</dt><dd>{_esc(theme)}</dd><dt>provenance</dt><dd>{_esc(normalized.get("provenance") or normalized.get("source") or "(미기재)")}</dd><dt>trust</dt><dd>{_esc(normalized.get("trust") or "derived")}</dd></dl>'
    theme_controls = (
        '<div class="theme"><label><input id="report-theme-system" type="radio" name="report-theme"'
        + (" checked" if theme in {"system", "print"} else "") + '> 시스템</label><label><input id="report-theme-light" type="radio" name="report-theme"'
        + (" checked" if theme == "light" else "") + '> 밝게</label><label><input id="report-theme-dark" type="radio" name="report-theme"'
        + (" checked" if theme == "dark" else "") + '> 어둡게</label><span>인쇄는 브라우저 인쇄 모드에서 최적화됩니다.</span></div>'
    )
    lead = cover if template_id == "research_journal" else hero
    return f'<!DOCTYPE html><html lang="ko" class="template-{_esc(template_id)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{_INLINE_STYLE}</style></head><body><main class="layout"><nav class="toc" aria-label="보고서 목차">{navigation}</nav><article>{theme_controls}{lead}{meta}{body}<footer>renderer={RENDERER_VERSION} · generated {_now_iso()} · 원문 불변 · 읽기 전용(sandbox·CSP 서빙)</footer></article></main></body></html>'


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
        "renderer_version": RENDERER_VERSION,
        "template_id": str(spec.get("template_id") or "executive"),
        "theme": str(spec.get("theme") or "system"),
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
    if not isinstance(entry, dict) or set(entry) not in (
        _CANONICAL_ENTRY_KEYS, _CANONICAL_ENTRY_KEYS | _PDF_ENTRY_KEYS,
        _RENDERED_ENTRY_KEYS, _RENDERED_ENTRY_KEYS | _PDF_ENTRY_KEYS,
    ):
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
        or ({"renderer_version", "template_id", "theme"} <= set(entry) and (
            entry["renderer_version"] != RENDERER_VERSION
            or entry["template_id"] not in TEMPLATE_IDS
            or entry["theme"] not in THEMES
        ))
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
