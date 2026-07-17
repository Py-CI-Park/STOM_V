"""연구 리포트 5개 탭 렌더러 — 총괄·연구 상세·결과 보고서·조건식·원장·규율.

수치는 loaders(판정 json)에서, 구조·정적 서사는 registry(결산 v1 계승)에서. 각 탭 하단에 '근거 파일' 각주.
"""
from __future__ import annotations

from typing import List, Optional

from alpha_lab.reporting import loaders, registry
from alpha_lab.reporting.util import badge, barrow, escape, highlight_code, table

__all__ = [
    "render_conditions", "render_ledger", "render_overview", "render_report_index",
    "render_studies",
]


def _num(v, nd=2, sign=False, suffix="") -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return escape(v)
    s = f"{f:+.{nd}f}" if sign else f"{f:,.{nd}f}"
    return s + suffix


def _short_date(seal_doc: str) -> str:
    base = seal_doc.split("/")[-1]
    return base[5:10] if len(base) >= 10 and base[:4].isdigit() else base[:10]


def _evfoot(paths: List[str]) -> str:
    items = " · ".join(f"<code>{escape(loaders.rel_path(*p.split('/')))}</code>" for p in paths)
    return f'<div class="evfoot">근거 파일: {items}</div>'


# ---------------------------------------------------------------------------
# ① 총괄.
# ---------------------------------------------------------------------------

def render_overview() -> str:
    led = loaders.load_ledger()
    total = led.get("total") if led.get("ok") else loaders.MISSING
    vc = registry.verdict_counts()
    verdict = loaders.load_json("d5r_b1_live", "_ab_verdict.json") or {}
    agg = verdict.get("agg_dP")
    kpis = [
        ("측정 시행 (장부)", f"{escape(total)}", "", "전 방향·세션 합산 (n_trials 원장)"),
        ("양성·실전 성과", f"{vc['양성'] + vc['실전이관']}건", "pos",
         "압력 절 · 2절 시너지 · B1(실전 이관)"),
        ("오답 확정 (기각·종결)", f"{vc['기각'] + vc['종결']}축", "",
         f"봉인된 자로 잰 확정 지식 · 미결 {vc['미결']}"),
        ("B1 엔진 A/B 4런", "전체 PASS" if verdict.get("all_pass") else loaders.MISSING, "pos",
         f"2년 ΣΔ {_num(agg, 0, sign=True)}원" if isinstance(agg, (int, float)) else "검증 json 확인"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="label">{escape(l)}</div>'
        f'<div class="value {c} num">{v}</div><div class="sub">{escape(s)}</div></div>'
        for l, v, c, s in kpis)

    tl = "".join(
        f'<li><span class="tdate num">{escape(_short_date(st.seal_doc))}</span>'
        f'{badge(st.verdict, st.badge)}<span><b>{escape(st.name)}</b> — {escape(st.easy)}</span></li>'
        for st in registry.STUDIES)

    funnel = "".join(
        f'<div class="fstep" style="background:{color}"><span>{escape(lab)}</span>'
        f'<b class="num">{escape(str(val).replace("{ledger_total}", str(total)))}</b></div>'
        for lab, val, color in registry.FUNNEL)

    score = "".join(
        f'<div class="srow"><span class="sname">{escape(name)} ({mx})</span>'
        f'<div class="track"><div class="fill {cls}" style="width:{w}%"></div></div>'
        f'<span class="spts num">{pts} / {mx}</span></div>'
        for name, pts, mx, cls, w in registry.SCORE)

    return f"""<section>
  <div class="eyebrow">§0 — 총괄</div>
  <h2>11개 연구, 양성 3건·실전 1건·오답 6축·미결 1건</h2>
  <p class="lede">이 연구소는 새 시장 데이터 없이 <b>존재하는 DB에서 발굴</b>했다. 모든 측정은 사전등록·봉인 후에만 이뤄졌고(번복 0회), 가짜 후보 400여 개가 실전 자본을 만나기 전에 차단됐다. 아래 KPI·타임라인은 판정 장부와 판정 json 에서 로드한 값이다.</p>
  <div class="kpis">{kpi_html}</div>

  <h3>판정 연대기 (전부 사전등록 봉인 후 측정)</h3>
  <ul class="timeline">{tl}</ul>

  <h3>검증 깔때기 — 실전에 가짜를 넣지 않은 것이 이 공장의 실수익</h3>
  <div class="funnel">{funnel}</div>
  <p class="muted" style="font-size:13px">가짜 후보 약 400개가 실전 자본을 만나기 전에 차단됨 — 사전등록·봉인·전수 측정 규율의 직접 효과.</p>

  <h3>냉정한 자체 평가 — {registry.SCORE_TOTAL[0]} / {registry.SCORE_TOTAL[1]} <span class="muted" style="font-size:13px">(결산 v1 §4 계승)</span></h3>
  <div class="score">{score}</div>
  <p class="muted" style="font-size:13px">금광 탐사로는 C(신규 금맥 0·개선 광맥 1) · 지질조사로는 A(오답 지도 완성·측량 도구 전부 코드화). <b style="color:var(--ink)">B1이 실전 30거래일을 통과하면 +10~15점</b> — 최종 점수는 실전이 결정.</p>
  {_evfoot(["n_trials_ledger.jsonl", "d5r_b1_live/_ab_verdict.json"])}
</section>"""


# ---------------------------------------------------------------------------
# ② 연구 상세.
# ---------------------------------------------------------------------------

def render_studies() -> str:
    cards: List[str] = []
    for st in registry.STUDIES:
        ex = loaders.extract_study(st.extractor)
        if "_missing" in ex:
            body = f'<p class="muted" style="font-size:13px">{loaders.MISSING} — <code>{escape(ex["_missing"])}</code></p>'
        else:
            rows = "".join(
                f'<tr><td style="white-space:normal;color:var(--muted)">{escape(k)}</td>'
                f'<td style="white-space:normal;font-weight:600">{escape(v)}</td></tr>'
                for k, v in ex.get("rows", []))
            note = ex.get("note", "")
            body = (f'<div class="tablebox"><table>{rows}</table></div>'
                    + (f'<p class="method">해석: {escape(note)}</p>' if note else ""))
        ev = " · ".join(f"<code>{escape(loaders.rel_path(*p.split('/')))}</code>" for p in st.evidence)
        cards.append(f"""<div class="studycard">
  <div class="shead"><h3>{escape(st.name)}</h3><span>{badge(st.verdict, st.badge)}<a href="{escape(st.detail_href)}"><b>전체 보고서 →</b></a></span></div>
  <p class="easy">{escape(st.easy)}</p>
  <p class="method"><b>방법.</b> {escape(st.method)}</p>
  {body}
  <div class="ev">봉인 커밋 <span class="sha">{escape(st.commit)}</span> · 봉인 문서 <code>{escape(registry.PLANS + "/" + st.seal_doc)}</code> · 증거 {ev}</div>
</div>""")
    return f"""<section>
  <div class="eyebrow">§1 — 연구 상세</div>
  <h2>연구별 카드 — 목적·방법·핵심 수치·판정</h2>
  <p class="lede">각 카드의 핵심 수치는 해당 연구의 판정 json 에서 로드한 값이다(파일 부재 시 '{loaders.MISSING}' 표기). 판정 배지와 봉인 커밋은 봉인된 프로그램 사실이다.</p>
  {"".join(cards)}
</section>"""


# ---------------------------------------------------------------------------
# ③ 결과 보고서 관리 — 연구별 상세 보고서 인덱스(카드 그리드).
# ---------------------------------------------------------------------------

def render_report_index() -> str:
    cards: List[str] = []
    for st in registry.STUDIES:
        ex = loaders.extract_study(st.extractor)
        if "_missing" in ex:
            one, extra_badge = "증거 미수록 — 개요만 제공", '<span class="badge hold">증거 미수록</span>'
        else:
            r = ex.get("rows", [])
            one, extra_badge = (f"{escape(r[0][0])}: {escape(r[0][1])}" if r else escape(st.easy)), ""
        cards.append(f"""<div class="repcard">
  <div class="rtitle">{escape(st.name)}</div>
  <div>{badge(st.verdict, st.badge)}{extra_badge}</div>
  <div class="rone">{one}</div>
  <div class="rmeta">봉인 {escape(st.date)} · <span class="sha">{escape(st.commit)}</span></div>
  <a class="open" href="{escape(st.detail_href)}">보고서 열기 →</a>
</div>""")
    # B1 결산 v1 도 목록 한 항목으로(정본 링크).
    cards.append("""<div class="repcard">
  <div class="rtitle">B1 결산 보고서 v1</div>
  <div><span class="badge live">결산</span></div>
  <div class="rone">B1 백테스트 성과 + 프로그램 결산 — 디자인 정본</div>
  <div class="rmeta">발행 2026-07-16</div>
  <a class="open" href="2026-07-16_b1_program_report.html">보고서 열기 →</a>
</div>""")
    return f"""<section>
  <div class="eyebrow">§2 — 결과 보고서 관리</div>
  <h2>연구별 상세 보고서 — {len(registry.STUDIES)}종 + 결산 v1</h2>
  <p class="lede">각 카드는 별도 HTML 상세 보고서(개요·방법·봉인·결과·수치 전표·판정·한정·증거·재현 6탭)로 이동한다. 데이터 없는 연구는 '증거 미수록' 배지 + 개요만. 폴더째 wt-dev 로 복사 가능한 상대 링크.</p>
  <div class="repgrid">{"".join(cards)}</div>
  {_evfoot(["n_trials_ledger.jsonl"])}
</section>"""


# ---------------------------------------------------------------------------
# ④ 조건식.
# ---------------------------------------------------------------------------

def _code_block(side: dict, title: str, extra: str) -> str:
    if not side or "_missing" in side:
        return f'<p class="muted">{loaders.MISSING} — <code>{escape((side or {}).get("_missing", "strategy.db"))}</code></p>'
    match = "sha 일치" if side.get("sha_match") else "sha 불일치(주의)"
    head = (f'<div class="codehead"><b>{escape(title)}</b>'
            f'<span>sha256 <span class="sha">{escape(side.get("sha_short", "?"))}</span> · {escape(match)}</span>'
            f'<span>{extra}</span></div>')
    return head + f"<pre>{highlight_code(side.get('text', ''))}</pre>"


def render_conditions() -> str:
    cond = loaders.load_conditions()
    if cond.get("_error"):
        inner = f'<p class="muted">{loaders.MISSING} — strategy.db 접근 오류: <code>{escape(cond["_error"])}</code></p>'
    else:
        inner = (_code_block(cond.get("buy"), "① 매수 조건식 — ALP_V4_RR8_12",
                             "구조: <b>시간 분리 2가지</b> — 개장 첫 2분(902) / 09:02~09:07(905)")
                 + _code_block(cond.get("sell"), "② 매도 조건식 — ALP_D5R_B1_S",
                               '= 챔피언 매도 원문 + <b style="color:var(--mark-line)">B1 저활력 절단 절 1개</b>(하이라이트)'))
    return f"""<section>
  <div class="eyebrow">§3 — 조건식 전문 (실전 등록본)</div>
  <h2>매수·매도 조건식 — strategy.db 등록 원문 (생성 시점 추출)</h2>
  <p class="lede">STOM GUI에서 <b>매수 <span class="sha">ALP_V4_RR8_12</span> + 매도 <span class="sha">ALP_D5R_B1_S</span></b> 페어로 선택하면 아래 그대로 작동한다. 원문은 <code>_database/strategy.db</code>에서 read-only 로 추출하고 sha 를 검증했다(&lt; 등 HTML 이스케이프 완료).</p>
  {inner}
  <div class="callout"><b>운용 주의</b> — ① 원본 매도식과 <b>동시 병렬 운용 금지</b>(매수식 같아 중복 주문). ② 실전 개시 시 절차서(<code>plans/2026-07-12_b1_supervised_live_protocol.md</code>)의 킬스위치·30거래일 채점표가 정본.</div>
  <div class="evfoot">근거: <code>_database/strategy.db</code> (stockbuy/stocksell, read-only)</div>
</section>"""


# ---------------------------------------------------------------------------
# ⑤ 원장·규율.
# ---------------------------------------------------------------------------

def render_ledger() -> str:
    led = loaders.load_ledger()
    if led.get("ok"):
        by = led.get("by_series", {})
        rows = sorted(by.items(), key=lambda kv: -(kv[1].get("n", 0) if isinstance(kv[1], dict) else 0))
        series_tbl = table(["계열", "시행 수", "√(2·ln n)"],
                           [[escape(k), f'<span class="num">{v.get("n", "?")}</span>',
                             f'<span class="num">{_num(v.get("sqrt_2_ln_n"), 2)}</span>'] for k, v in rows])
        total_line = f'합계 <b class="num">{led.get("total")}</b>행 · known 창 접촉 <b class="num">{led.get("known_contacts", 0)}</b>'
    else:
        series_tbl = f'<p class="muted">{loaders.MISSING} — n_trials_ledger.jsonl</p>'
        total_line = ""

    win = table(["창", "지위", "사용 규칙"],
                [[escape(a), escape(b), escape(c)] for a, b, c in registry.WINDOW_LEDGER])
    sop = "".join(
        f'<li><span class="tdate">{escape(step)}</span><span></span><span>{escape(desc)}</span></li>'
        for step, desc in registry.SOP_STEPS)
    honesty = "".join(f"<p><b>{escape(b)}</b> {escape(t)}</p>" for b, t in registry.HONESTY)

    return f"""<section>
  <div class="eyebrow">§4 — 원장·규율</div>
  <h2>측정 장부·창-지위·SOP·정직한 한정</h2>

  <h3>계열별 시행 (n_trials 원장 — discipline.ledger.aggregate)</h3>
  {series_tbl}
  <p class="muted" style="font-size:13px">{total_line}</p>

  <h3>창-지위 원장 요약 (모든 측정의 관문)</h3>
  {win}
  <p class="muted" style="font-size:13px">발견창(2022-2023)만 측정에 사용 — known 창(2024/2025)은 veto 전용, blind 주장 금지.</p>

  <h3>SOP-M 측정 사이클 9단계 (실행 계획 정본 §3)</h3>
  <ul class="timeline">{sop}</ul>

  <h3>정직한 한정 — 이 숫자들을 믿어도 되는 범위 <span class="muted" style="font-size:13px">(결산 v1 §5 계승)</span></h3>
  <div class="lede">{honesty}</div>
  {_evfoot(["n_trials_ledger.jsonl"])}
</section>"""
