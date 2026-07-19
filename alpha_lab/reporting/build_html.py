"""연구 리포트 HTML 빌더 — 단일 자가완결 파일(외부 의존 0), 스크립트 없는 해시 앵커 탐색.

디자인 정본 = 결산 v1(`reports/2026-07-16_b1_program_report.html`)의 CSS 토큰·타이포(명조 표제+고딕
본문)·색 관례(상승=적 --up·하락=청 --down·액센트 jade)·컴포넌트(kpi/barrow/timeline/funnel/badge/
pre/score)를 그대로 재사용하고, 탭 셸은 안정적인 `#tab-*` 앵커만 사용한다.
"""
from __future__ import annotations

import posixpath
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from alpha_lab.reporting import detail, loaders, registry, tabs
from alpha_lab.reporting.util import escape

# wt-dev 이식: 이 폴더(reports/)를 통째 복사 + 대시보드에서 iframe/정적 서빙(해시/allowlist 링크·자가완결).
__all__ = ["build", "build_all", "build_detail", "build_hub", "extract_report_links"]

# 결산 v1 CSS 토큰·컴포넌트 그대로 + 스크립트 없는 탭 앵커 셸 추가(주석으로 출처 명기).
_CSS = """
:root{--bg:#FAF9F4;--card:#FFFFFF;--ink:#22261F;--muted:#6E7466;--line:#DEDCD0;
  --accent:#1E6B58;--accent-soft:#E4EFEA;--up:#C4453C;--up-soft:#F7E9E7;--down:#33619E;
  --down-soft:#E8EEF6;--code-bg:#F3F2EB;--code-dim:#8B9082;--mark:#FFF3C2;--mark-line:#C9A227;}
@media (prefers-color-scheme:dark){:root{--bg:#141712;--card:#1B1F19;--ink:#E7EAE1;--muted:#9AA192;
  --line:#2E332B;--accent:#54AD92;--accent-soft:#1E2C26;--up:#E0705F;--up-soft:#33201C;--down:#7AA3DA;
  --down-soft:#1C2635;--code-bg:#10130D;--code-dim:#767D6E;--mark:#3A3416;--mark-line:#C9A227;}}
:root[data-theme="light"]{--bg:#FAF9F4;--card:#FFFFFF;--ink:#22261F;--muted:#6E7466;--line:#DEDCD0;
  --accent:#1E6B58;--accent-soft:#E4EFEA;--up:#C4453C;--up-soft:#F7E9E7;--down:#33619E;
  --down-soft:#E8EEF6;--code-bg:#F3F2EB;--code-dim:#8B9082;--mark:#FFF3C2;--mark-line:#C9A227;}
:root[data-theme="dark"]{--bg:#141712;--card:#1B1F19;--ink:#E7EAE1;--muted:#9AA192;--line:#2E332B;
  --accent:#54AD92;--accent-soft:#1E2C26;--up:#E0705F;--up-soft:#33201C;--down:#7AA3DA;
  --down-soft:#1C2635;--code-bg:#10130D;--code-dim:#767D6E;--mark:#3A3416;--mark-line:#C9A227;}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);margin:0;font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:15px;line-height:1.7}
.wrap{max-width:980px;margin:0 auto;padding:32px 22px 80px}
h1,h2,h3{font-family:"Batang","Nanum Myeongjo","Apple Myungjo",serif;text-wrap:balance;line-height:1.35}
h1{font-size:30px;margin:10px 0 6px}
h2{font-size:22px;margin:0 0 4px;padding-top:8px}
h3{font-size:17px;margin:22px 0 8px}
.eyebrow{font-size:11.5px;letter-spacing:.14em;color:var(--accent);font-weight:700}
.muted{color:var(--muted)}.num{font-variant-numeric:tabular-nums}
section{margin-top:36px;border-top:2px solid var(--accent);padding-top:14px}
.lede{font-size:15.5px;max-width:70ch}
.masthead{border-bottom:3px double var(--ink);padding-bottom:18px;display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap}
.meta-grid{display:flex;flex-wrap:wrap;gap:6px 26px;font-size:12.5px;color:var(--muted);margin-top:10px}
.meta-grid b{color:var(--ink);font-weight:600}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:22px 0 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.kpi .label{font-size:12px;color:var(--muted);letter-spacing:.06em}
.kpi .value{font-family:"Batang",serif;font-size:26px;margin-top:2px;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:12px;color:var(--muted);margin-top:2px}
.pos{color:var(--up)}.neg{color:var(--down)}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card)}
.tablebox{overflow-x:auto;border:1px solid var(--line);border-radius:6px;margin:14px 0}
th{background:var(--accent-soft);color:var(--ink);text-align:left;font-weight:700;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px 12px;border-bottom:1px solid var(--line);white-space:nowrap;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
td.best{font-weight:700}
.barrow{display:grid;grid-template-columns:172px 1fr 118px;gap:10px;align-items:center;margin:7px 0}
.barrow .blabel{font-size:13px;text-align:right;color:var(--muted)}
.barrow .bval{font-size:13px;font-weight:700;font-variant-numeric:tabular-nums}
.track{background:var(--code-bg);border-radius:4px;height:22px;position:relative;overflow:hidden}
.fill{height:100%;border-radius:4px 3px 3px 4px}
.fill.acc{background:var(--accent)}.fill.up{background:var(--up)}.fill.dn{background:var(--down)}
.fill.ghost{background:var(--muted);opacity:.45}
.chart{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px 18px;margin:14px 0}
.chart .ctitle{font-size:13px;font-weight:700;margin-bottom:10px}
.chart .cnote{font-size:12px;color:var(--muted);margin-top:10px}
.callout{border-left:4px solid var(--accent);background:var(--accent-soft);padding:12px 16px;border-radius:0 6px 6px 0;margin:16px 0;font-size:14px}
.callout.warn{border-left-color:var(--mark-line);background:var(--mark)}
.badge{display:inline-block;font-size:11.5px;font-weight:700;border-radius:20px;padding:2px 11px;margin-right:6px;vertical-align:1px}
.badge.kill{background:var(--down-soft);color:var(--down)}
.badge.posv{background:var(--up-soft);color:var(--up)}
.badge.hold{background:var(--code-bg);color:var(--muted)}
.badge.live{background:var(--accent-soft);color:var(--accent)}
pre{background:var(--code-bg);border:1px solid var(--line);border-radius:6px;padding:16px;overflow-x:auto;font-family:"Consolas","D2Coding",monospace;font-size:12.5px;line-height:1.62;margin:10px 0}
pre .c{color:var(--code-dim)}pre .k{color:var(--accent);font-weight:700}
pre mark{background:var(--mark);color:inherit;border-radius:3px;padding:1px 2px;outline:1px solid var(--mark-line)}
.codehead{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;font-size:12.5px;color:var(--muted);margin-top:14px}
.codehead b{color:var(--ink);font-size:14px}
.sha{font-family:"Consolas",monospace;background:var(--code-bg);padding:1px 7px;border-radius:4px;font-size:11.5px}
.timeline{list-style:none;margin:14px 0;padding:0}
.timeline li{display:grid;grid-template-columns:96px 92px 1fr;gap:12px;padding:9px 0;border-bottom:1px dashed var(--line);font-size:13.5px;align-items:baseline}
.timeline li:last-child{border-bottom:none}
.timeline .tdate{color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.funnel{display:flex;flex-direction:column;gap:8px;margin:14px 0}
.fstep{border-radius:5px;padding:9px 14px;color:#fff;font-size:13.5px;display:flex;justify-content:space-between;gap:12px;font-variant-numeric:tabular-nums}
.score{display:grid;gap:8px;margin:14px 0}
.srow{display:grid;grid-template-columns:minmax(150px,220px) 1fr 84px;gap:10px;align-items:center;font-size:13px}
.srow .sname{text-align:right;color:var(--muted)}
.srow .spts{font-weight:700;font-variant-numeric:tabular-nums}
.studycard{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px;margin:14px 0}
.studycard .shead{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.studycard h3{margin:0;font-size:16px}
.studycard .easy{font-size:13.5px;margin:8px 0 4px}
.studycard .method{font-size:12.5px;color:var(--muted);margin:6px 0 10px}
.studycard .ev{font-size:11.5px;color:var(--muted);margin-top:10px;word-break:break-all}
.evfoot{font-size:11.5px;color:var(--muted);margin-top:16px;border-top:1px dashed var(--line);padding-top:8px;word-break:break-all}
.repgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;margin:16px 0}
.repcard{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.repcard .rtitle{font-family:"Batang",serif;font-size:15px;font-weight:700}
.repcard .rone{font-size:12.5px;color:var(--muted);flex:1}
.repcard .rmeta{font-size:11.5px;color:var(--muted)}
.repcard a.open{font-size:13px;font-weight:700;color:var(--accent);text-decoration:none}
a{color:var(--accent)}
footer{margin-top:56px;border-top:1px solid var(--line);padding-top:14px;font-size:12px;color:var(--muted)}
footer code{font-family:"Consolas",monospace;font-size:11.5px}
.tabs{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:4px;background:var(--bg);border-bottom:2px solid var(--accent);padding:10px 0 0;margin-top:18px}
.tabbtn{background:transparent;border:1px solid var(--line);border-bottom:none;color:var(--muted);border-radius:6px 6px 0 0;padding:8px 15px;font-size:13.5px;font-weight:700;font-family:inherit;text-decoration:none}
.tabbtn.active,.tabbtn:hover,.tabbtn:focus{background:var(--card);color:var(--accent);border-color:var(--accent)}
.tabpanel{padding-top:6px;scroll-margin-top:74px}
.tabpanel>section:first-of-type{border-top:none}
@media (max-width:640px){.barrow{grid-template-columns:110px 1fr 96px}.timeline li{grid-template-columns:78px 76px 1fr}h1{font-size:24px}.masthead{flex-direction:column}}
@media (prefers-reduced-motion:no-preference){.fill{transition:width .5s ease}}
"""

_REPORTS_DOCS_PREFIX = "research/condition_research/reports"
_HREF_RE = re.compile(r"""href=(["'])(.*?)\1""", re.IGNORECASE)


def _report_view_href(report_rel_path: str) -> str:
    docs_path = f"{_REPORTS_DOCS_PREFIX}/{report_rel_path}"
    return f"/reports/view?path={quote(docs_path, safe='/._-')}"


def _normalize_report_href(href: str, current_path: str) -> str:
    if href.startswith("#"):
        return href
    lowered = href.strip().lower()
    if (
        "://" in lowered
        or lowered.startswith("//")
        or lowered.startswith("javascript:")
        or lowered.startswith("data:")
        or lowered.startswith("mailto:")
        or lowered.startswith("\\")
        or "\x00" in href
    ):
        raise ValueError(f"disallowed report link: {href!r}")

    path, sep, fragment = href.partition("#")
    base_dir = posixpath.dirname(current_path)
    joined = posixpath.normpath(posixpath.join(base_dir, path)) if base_dir else posixpath.normpath(path)
    if joined == "." or joined.startswith("../") or joined.startswith("/") or not joined.lower().endswith(".html"):
        raise ValueError(f"disallowed report link: {href!r}")
    rewritten = _report_view_href(joined)
    return f"{rewritten}#{fragment}" if sep else rewritten


def _rewrite_report_links(html: str, current_path: str) -> str:
    def repl(match: re.Match[str]) -> str:
        quote_char, href = match.groups()
        rewritten = _normalize_report_href(href, current_path)
        return f"href={quote_char}{escape(rewritten)}{quote_char}"

    return _HREF_RE.sub(repl, html)


def extract_report_links(html: str) -> List[str]:
    """Return generated href targets in document order without duplicates."""
    seen = set()
    links: List[str] = []
    for _quote, href in _HREF_RE.findall(html):
        if href not in seen:
            seen.add(href)
            links.append(href)
    return links

_HUB_TABS = (("overview", "총괄"), ("studies", "연구 상세"), ("reports", "결과 보고서 관리"),
             ("conditions", "조건식"), ("ledger", "원장·규율"))
_DETAIL_TABS = (("overview", "개요"), ("method", "방법·봉인"), ("results", "결과"),
                ("fulltable", "수치 전표"), ("verdict", "판정·한정"), ("evidence", "증거·재현"))


def _gen_ts() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def _page(title: str, masthead: str, nav_tabs: Tuple[Tuple[str, str], ...],
          panels_html: List[str], footer: str, current_path: str) -> str:
    """공유 셸(자가완결) — hub·detail 공통. CSS 인라인 중복 허용(템플릿 공유·비용 0)."""
    nav = "".join(
        f'<a class="tabbtn{" active" if i == 0 else ""}" href="#tab-{tid}">{escape(label)}</a>'
        for i, (tid, label) in enumerate(nav_tabs))
    panels = "".join(
        f'<div id="tab-{tid}" class="tabpanel">{panels_html[i]}</div>'
        for i, (tid, _l) in enumerate(nav_tabs))
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
{masthead}
<nav class="tabs" role="tablist">{nav}</nav>
{panels}
{footer}
</div>

</body>
</html>
"""
    return _rewrite_report_links(html, current_path)


def _footer(commit: Optional[str], back: Optional[str] = None) -> str:
    home = f' · <a href="{back}">← 허브로</a>' if back else ""
    return f"""<footer>
  단일 자가완결 HTML(외부 의존 0·스크립트 0·허용 링크만 사용) · 디자인 정본 = 결산 v1 · 생성기 <code>alpha_lab/reporting/</code> ·
  생성 커밋 <code>{escape(commit or "미기록")}</code> · 생성 시각 <code>{escape(_gen_ts())}</code>{home}<br>
  수치는 판정 json 원문에서 로드(재계산 없음·원장 count 만 aggregate). 정적 서사는 결산 v1 계승.
  <span class="muted">wt-dev 이식: reports/ 폴더 복사 + 대시보드 iframe/정적 서빙.</span>
</footer>"""


def build_hub(commit: Optional[str] = None) -> str:
    """L1 허브 — 탭 5개(총괄·연구 상세·결과 보고서 관리·조건식·원장·규율)."""
    total = (loaders.load_ledger().get("total")) or loaders.MISSING
    masthead = f"""<header class="masthead">
  <div>
    <div class="eyebrow">STOM ALPHA LAB · 연구 리포트 허브</div>
    <h1>알파 재시작 연구소 — 계층형 연구 리포트</h1>
    <div class="meta-grid">
      <span>측정창 <b class="num">2022-03-23 ~ 2023-12-31 (발견창 437거래일)</b></span>
      <span>워크트리 <b>STOM_V.wt-alpha</b></span>
      <span>측정 장부 <b class="num">{escape(total)}행</b></span>
      <span>연구 <b class="num">{len(registry.STUDIES)}건</b> · 상세 보고서 <b class="num">{len(registry.STUDIES)}종</b></span>
    </div>
  </div>

</header>"""
    panels = [tabs.render_overview(), tabs.render_studies(), tabs.render_report_index(),
              tabs.render_conditions(), tabs.render_ledger()]
    return _page("알파 재시작 연구소 — 연구 리포트 허브", masthead, _HUB_TABS, panels, _footer(commit),
                 current_path="research_lab_report.html")


def build_detail(study: registry.Study, commit: Optional[str] = None) -> str:
    """L2 연구별 상세 — 탭 6개(개요·방법·봉인·결과·수치 전표·판정·한정·증거·재현)."""
    from alpha_lab.reporting.util import badge
    masthead = f"""<header class="masthead">
  <div>
    <div class="eyebrow"><a href="../research_lab_report.html">← 허브로</a> · 연구 상세 보고서</div>
    <h1>{escape(study.name)} {badge(study.verdict, study.badge)}</h1>
    <div class="meta-grid">
      <span>연구 ID <b>{escape(study.id)}</b></span>
      <span>봉인 <b class="num">{escape(study.date)}</b> · <span class="sha">{escape(study.commit)}</span></span>
      <span>판정 <b>{escape(study.verdict)}</b></span>
    </div>
  </div>
</header>"""
    panels = detail.render_detail_panels(study)
    return _page(f"{study.name} — 연구 상세", masthead, _DETAIL_TABS, panels,
                 _footer(commit, back="../research_lab_report.html"), current_path=f"research/{study.id}.html")


def build_all(commit: Optional[str] = None) -> Dict[str, str]:
    """허브 + 연구별 상세 → {reports 상대경로: HTML}. 생성기가 한 번에 전부 산출."""
    out: Dict[str, str] = {"research_lab_report.html": build_hub(commit)}
    for st in registry.STUDIES:
        out[f"research/{st.id}.html"] = build_detail(st, commit)
    return out


def build(commit: Optional[str] = None) -> str:
    """하위호환 — 허브 HTML(단일)."""
    return build_hub(commit)
