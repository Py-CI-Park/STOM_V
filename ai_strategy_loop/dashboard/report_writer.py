# -*- coding: utf-8 -*-
"""V5.6 (G5·G7) 스텝별 연구 리포트 자동생성 writer.

오프라인/수동 전용. GET/WS 요청 경로에서 절대 호출하지 않는다(쓰기 금지 계약).
표준양식(§5) HTML 을 escape 된 inert 마크업(<script> 없음)으로 렌더하고,
allowlisted output(docs/generated_reports)에 atomic write 하며,
stable research_id/step_id·sha256·provenance·trust·크기/개수 한도를 manifest 로 남긴다.

Reports 탭(/reports·/reports/view)이 docs/ 하위 *.html 을 CSP+sandbox 로 서빙하므로
생성물은 그 규약 안에서만 열람된다(원문 링크는 /reports/view 로 재작성).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

# 표준 연구 보고서 섹션(문서 §5). 순서 고정.
STANDARD_SECTIONS: tuple[tuple[str, str], ...] = (
    ("hypothesis", "가설 / 원인"),
    ("method", "방법"),
    ("results", "결과 (데이터·차트)"),
    ("analysis", "분석"),
    ("conclusion", "결론"),
    ("limits", "한계"),
    ("history", "히스토리 (변경 이력)"),
    ("related_docs", "관련 문서"),
    ("related_commits", "관련 커밋 / 작업"),
)

# 안전 한도(manifest 로 노출).
MAX_REPORTS = 1000
MAX_BYTES_EACH = 2 * 1024 * 1024

_INLINE_STYLE = (
    "body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:960px;margin:0 auto;"
    "padding:24px;color:#1a2028;background:#fff;line-height:1.6}"
    "h1{font-size:22px;border-bottom:2px solid #2a3441;padding-bottom:8px}"
    "h2{font-size:16px;margin-top:24px;color:#0b5}"
    "dl.meta{background:#f4f6f8;border:1px solid #dde;border-radius:8px;padding:12px 16px}"
    "dl.meta dt{font-weight:600;color:#556}dl.meta dd{margin:0 0 8px}"
    "footer{margin-top:32px;padding-top:12px;border-top:1px solid #dde;font-size:12px;color:#889}"
    "a{color:#06c}ul{margin:0;padding-left:18px}"
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_list_or_text(value: Any, *, as_links: bool = False) -> str:
    """리스트면 <ul>, 스칼라면 <p>. as_links 이고 항목이 내부 리포트 경로면 /reports/view 로 재작성."""
    if isinstance(value, (list, tuple)):
        if not value:
            return "<p class='muted'>(없음)</p>"
        lis = []
        for item in value:
            lis.append(f"<li>{_render_link_item(item) if as_links else _esc(item)}</li>")
        return "<ul>" + "".join(lis) + "</ul>"
    return f"<p>{_esc(value)}</p>"


def _render_link_item(item: Any) -> str:
    """내부 리포트 경로(*.html)면 allowlisted /reports/view 앵커로, 아니면 escape 텍스트."""
    text = "" if item is None else str(item)
    if text.endswith(".html") and ".." not in text and not text.startswith(("http://", "https://", "/")):
        href = "/reports/view?path=" + _esc(text)
        return f'<a href="{href}">{_esc(text)}</a>'
    return _esc(text)


def render_report_html(spec: dict) -> str:
    """표준양식 HTML 렌더. 모든 사용자 내용은 escape 되고 <script> 를 포함하지 않는다."""
    title = _esc(spec.get("title") or spec.get("research_id") or "연구 리포트")
    purpose = _esc(spec.get("purpose"))
    date = _esc(spec.get("date") or _now_iso())
    research_id = _esc(spec.get("research_id"))
    step_id = _esc(spec.get("step_id"))

    body_sections = []
    for key, label in STANDARD_SECTIONS:
        raw = spec.get(key)
        as_links = key in ("related_docs", "related_commits")
        # v5.3.9: 섹션 앵커 id — 뷰어 목차(TOC)/fragment 점프 소비.
        body_sections.append(
            f'<section id="sec-{key}"><h2>{_esc(label)}</h2>{_render_list_or_text(raw, as_links=as_links)}</section>'
        )

    generated_at = _now_iso()
    provenance = _esc(spec.get("provenance") or spec.get("source") or "(미기재)")
    trust = _esc(spec.get("trust") or "derived")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko"><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{_INLINE_STYLE}</style></head><body><article>"
        f"<h1>{title}</h1>"
        '<dl class="meta">'
        f"<dt>연구목적</dt><dd>{purpose}</dd>"
        f"<dt>일자</dt><dd>{date}</dd>"
        f"<dt>research_id</dt><dd>{research_id}</dd>"
        f"<dt>step_id</dt><dd>{step_id}</dd>"
        "</dl>"
        + "".join(body_sections)
        + f"<footer>생성 {generated_at} · trust={trust} · provenance={provenance} · "
        "원문 불변 · 읽기 전용(sandbox·CSP 서빙)</footer>"
        "</article></body></html>"
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path: str, text: str) -> None:
    """같은 디렉터리 임시파일에 쓰고 os.replace 로 원자 교체."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _slug(value: str) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "-" for c in str(value)]
    return "".join(keep).strip("-")[:80] or "report"


def write_report(spec: dict, out_dir: str) -> dict:
    """단일 리포트를 렌더·atomic write 하고 manifest 항목(dict)을 반환."""
    html_text = render_report_html(spec)
    data = html_text.encode("utf-8")
    if len(data) > MAX_BYTES_EACH:
        raise ValueError(f"report exceeds MAX_BYTES_EACH ({len(data)} > {MAX_BYTES_EACH})")
    research_id = str(spec.get("research_id") or spec.get("title") or "report")
    step_id = str(spec.get("step_id") or "0")
    fname = f"{_slug(research_id)}__{_slug(step_id)}.html"
    full = os.path.join(out_dir, fname)
    _atomic_write(full, html_text)
    return {
        "research_id": research_id,
        "step_id": step_id,
        "path": fname,
        "sha256": _sha256(html_text),
        "bytes": len(data),
        "generated_at": _now_iso(),
        "trust": str(spec.get("trust") or "derived"),
        "provenance": spec.get("provenance") or spec.get("source") or None,
    }


def write_reports(specs: list, out_dir: str, manifest_path: str) -> dict:
    """여러 스텝 리포트를 생성하고 manifest 를 atomic write. manifest dict 반환."""
    if len(specs) > MAX_REPORTS:
        raise ValueError(f"too many reports ({len(specs)} > {MAX_REPORTS})")
    entries = [write_report(s, out_dir) for s in specs]
    manifest = {
        "generated_at": _now_iso(),
        "count": len(entries),
        "limits": {"max_reports": MAX_REPORTS, "max_bytes_each": MAX_BYTES_EACH},
        "reports": entries,
    }
    _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest
