"""리포트 HTML 헬퍼 — 이스케이프·조건식 하이라이터·컴포넌트(순환 import 차단용 공용 모듈)."""
from __future__ import annotations

import html
import re
from typing import List, Sequence, Tuple

__all__ = ["badge", "barrow", "escape", "highlight_code", "table"]


def escape(s: object) -> str:
    return html.escape(str(s), quote=False)


_KW = re.compile(r"^(\s*)(if|elif|else)\b")


def highlight_code(text: str) -> str:
    """조건식 원문 → HTML(이스케이프 필수) — 주석 span.c·키워드 span.k·B1 저활력절단 절 mark(3줄)."""
    out: List[str] = []
    mark_left = 0
    for ln in text.replace("\r\n", "\n").split("\n"):
        if "보유시간 >= 120" in ln and "최고수익률 < 1.0" in ln:
            mark_left = 3
        esc = escape(ln)
        stripped = ln.strip()
        if stripped.startswith("#"):
            rendered = f'<span class="c">{esc}</span>'
        else:
            m = _KW.match(ln)
            if m:
                indent, kw = m.group(1), m.group(2)
                rendered = f'{indent}<span class="k">{kw}</span>{escape(ln[len(indent) + len(kw):])}'
            else:
                rendered = esc
        if mark_left > 0:
            rendered, mark_left = f"<mark>{rendered}</mark>", mark_left - 1
        out.append(rendered)
    return "\n".join(out)


def badge(verdict: str, cls: str) -> str:
    return f'<span class="badge {cls}">{escape(verdict)}</span>'


def barrow(label: str, width_pct: float, fill_cls: str, value: str, *, val_cls: str = "") -> str:
    w = max(0.0, min(100.0, float(width_pct)))
    return (f'<div class="barrow"><span class="blabel">{escape(label)}</span>'
            f'<div class="track"><div class="fill {fill_cls}" style="width:{w:.1f}%"></div></div>'
            f'<span class="bval num {val_cls}">{escape(value)}</span></div>')


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """rows 의 셀은 이미 이스케이프/마크업 완료 문자열(호출부 책임)."""
    thead = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablebox"><table><tr>{thead}</tr>{body}</table></div>'
