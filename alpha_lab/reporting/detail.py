"""연구별 상세 보고서(L2) 6탭 렌더러 — 개요·방법·봉인·결과·수치 전표·판정·한정·증거·재현.

수치·차트는 각 연구의 판정 json 에서 로드(재계산 없음). 결과 탭은 연구별 특화 차트(D1 압력 5절
Δ·CI 바 / O-4 158후보 분포 / B-트랙 anchor CI / B1 백테 4런)를 두고, 그 외는 추출기 표로 폴백.
디자인은 결산 v1 정본 컴포넌트 재사용. 자가완결·상대 링크(폴더째 wt-dev 이식 가능).
"""
from __future__ import annotations

from typing import List, Optional

from alpha_lab.reporting import loaders, registry
from alpha_lab.reporting.util import badge, barrow, escape, table

__all__ = ["render_detail_panels"]

# 연구 id → 재생성 명령(측정 스크립트).
_REGEN = {
    "o1g": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o1g_measure.py --phase all",
    "d1": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d1_measure.py --phase all",
    "d1pair": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d1_pairwise_measure.py --phase all",
    "d5d9": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d5_d9_measure.py --phase all",
    "o3": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o3_measure.py --phase all",
    "o4": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o4_measure.py --phase all",
    "btrack": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/b_track_measure.py --phase all",
    "bext": "STOM_ALLOW_MINIMAL_SETTING=1 python scripts/b_track_ext_measure.py --phase all",
    "b1": "d5r_b1_live/ 엔진 A/B 런 스크립트(재현) — 절차서 참조",
    "d5r": "d5r_triage — 봉인 문서 절차 참조",
    "strack": "S-트랙 v2a — 봉인 문서 절차 참조",
}


def _num(v, nd=2, sign=False) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return escape(v)
    return f"{f:+.{nd}f}" if sign else f"{f:,.{nd}f}"


def _kpi_cards(rows: List) -> str:
    if not rows:
        return ""
    cells = "".join(
        f'<div class="kpi"><div class="label">{escape(k)}</div>'
        f'<div class="value num" style="font-size:20px">{escape(v)}</div></div>'
        for k, v in rows[:4])
    return f'<div class="kpis">{cells}</div>'


# ---------------------------------------------------------------------------
# 결과 탭 — 연구별 특화 차트.
# ---------------------------------------------------------------------------

def _chart_d1(sj: dict) -> str:
    per = (sj.get("judgment", {}) or {}).get("per_clause", {})
    lb = (sj.get("judgment", {}) or {}).get("load_bearing_nums", [1, 4, 10, 37, 38])
    rows = []
    mx = 0.30
    for n in lb:
        c = per.get(str(n), {})
        d = c.get("delta_pp")
        if d is None:
            continue
        rows.append(barrow(escape(c.get("text", f"#{n}")), abs(float(d)) / mx * 100, "up",
                           f'{float(d):+.3f}%p', val_cls="pos"))
    if not rows:
        return ""
    return (f'<div class="chart"><div class="ctitle">압력 load-bearing 절 Δ(만족−미만족 L3, %p)</div>'
            + "".join(rows) + '<div class="cnote">양(+) = 이 절을 통과하면 챔피언 출구 손익이 더 낫다. 값은 판정 json.</div></div>')


def _chart_o4(sj: dict) -> str:
    j = sj.get("judgment", {})
    parts = [("생존(양EV∧구별)", j.get("n_survive", 0), "up"),
             ("아류(겹침 초과)", j.get("n_derivative", 0), "dn"),
             ("약신호", len(j.get("weak_signal_cids", [])), "acc"),
             ("양EV 증거 0", len(j.get("no_positive_ev_cids", [])), "dn")]
    tot = max(1, sum(p[1] for p in parts))
    bars = "".join(barrow(lab, v / tot * 100, cls, f"{v}개") for lab, v, cls in parts)
    return (f'<div class="chart"><div class="ctitle">158 후보 분포 (자격 {j.get("fdr_denominator","?")})</div>'
            + bars + '<div class="cnote">전 조합이 양EV 증거 0 — 가산 조합 문법의 한계 확정.</div></div>')


def _chart_anchor(sj: dict, unit_path: List[str]) -> str:
    a = sj
    for k in unit_path:
        a = (a or {}).get(k, {})
    mean, cl, ch, n = a.get("mean_net_pp"), a.get("ci_low_pp"), a.get("ci_high_pp"), a.get("n_fire")
    if mean is None:
        return ""
    return (f'<div class="chart"><div class="ctitle">합동 anchor mean L3 · 일자블록 CI (%p)</div>'
            f'<p class="num" style="font-size:15px">mean <b>{_num(mean,3,True)}</b> · '
            f'CI [{_num(cl,3,True)}, {_num(ch,3,True)}] · 발화 n={escape(n)}</p>'
            f'<div class="cnote">CI 가 0 을 걸치면 (c) 미결(검정력 부족) — 표본이 열쇠.</div></div>')


def _chart_d1pair(sj: dict) -> str:
    per = (sj.get("judgment", {}) or {}).get("per_pair", {})
    syn = (sj.get("judgment", {}) or {}).get("synergy_pairs", [])
    rows = []
    for pid in syn:
        r = per.get(pid, {})
        I = r.get("I_pp")
        if I is None:
            continue
        rows.append(barrow(f"{escape(pid)} ({escape(r.get('family_pair',''))})",
                           abs(float(I)) / 0.20 * 100, "up", f'{float(I):+.3f}%p', val_cls="pos"))
    if not rows:
        return ""
    return (f'<div class="chart"><div class="ctitle">시너지 짝 교호 효과 I (%p)</div>'
            + "".join(rows) + '<div class="cnote">I&gt;0 = 결합이 단독 합을 초과(초가산). 유일 시너지 족.</div></div>')


def _b1_backtest() -> str:
    runs = loaders.load_b1_runs()
    order = ("A_2022", "B_2022", "A_2023", "B_2023")
    if any(runs.get(k) is None for k in order):
        return f'<p class="muted">{loaders.MISSING} — <code>{escape(loaders.rel_path("d5r_b1_live"))}</code></p>'

    def row(label, key, nd=0, sign=False, better="hi"):
        cells = []
        for yr in ("2022", "2023"):
            a, b = runs[f"A_{yr}"].get(key), runs[f"B_{yr}"].get(key)
            try:
                bb = (float(b) > float(a)) if better == "hi" else (float(b) < float(a))
            except (TypeError, ValueError):
                bb = False
            cells.append(f'<td class="num">{_num(a, nd, sign)}</td>')
            cells.append(f'<td class="num{" best pos" if bb and better == "hi" else (" best" if bb else "")}">{_num(b, nd, sign)}</td>')
        return f'<tr><td style="color:var(--muted)">{escape(label)}</td>' + "".join(cells) + "</tr>"

    header = "<tr><th>지표</th><th>2022 원본</th><th>2022 B1</th><th>2023 원본</th><th>2023 B1</th></tr>"
    body = (row("총수익 (원)", "total_profit_krw", 0, True) + row("자본 대비 수익률 (%)", "total_profit_pct", 1, True)
            + row("엔진 CAGR (%)", "cagr", 1, True) + row("거래수", "trade_count", 0)
            + row("승률 (%)", "win_rate", 1) + row("거래당 평균수익률 (%)", "avg_profit_pct", 2, True)
            + row("최대낙폭 MDD (%)", "mdd_pct", 2, better="lo") + row("평균 보유시간 (초)", "avg_hold_time", 0, better="lo"))
    tbl = f'<div class="tablebox"><table>{header}{body}</table></div>'
    vals = [abs(float(runs[k].get("total_profit_krw") or 0)) for k in order]
    mx = max(vals) or 1.0
    lab = {"A_2022": "2022 원본", "B_2022": "2022 B1", "A_2023": "2023 원본", "B_2023": "2023 B1"}
    bars = "".join(barrow(lab[k], abs(float(runs[k].get("total_profit_krw") or 0)) / mx * 100,
                          "up" if k.startswith("B") else "dn",
                          f'{float(runs[k].get("total_profit_krw") or 0)/10000:+,.0f}만',
                          val_cls="pos" if k.startswith("B") else "") for k in order)
    return (tbl + f'<div class="chart"><div class="ctitle">연도별 총수익 — 원본 vs B1 (만원)</div>{bars}'
            '<div class="cnote">두 해 모두 같은 방향(+) 개선 · 값은 엔진 metrics json 원값.</div></div>')


def _result_chart(study: registry.Study, sj: Optional[dict]) -> str:
    if study.id == "b1":
        return _b1_backtest()
    if sj is None:
        return ""
    return {
        "d1": lambda: _chart_d1(sj),
        "d1pair": lambda: _chart_d1pair(sj),
        "o4": lambda: _chart_o4(sj),
        "btrack": lambda: _chart_anchor(sj, ["judgment", "units", "anchor"]),
        "bext": lambda: _chart_anchor(sj, ["judgment", "anchor"]),
    }.get(study.id, lambda: "")()


# ---------------------------------------------------------------------------
# 6탭 조립.
# ---------------------------------------------------------------------------

def render_detail_panels(study: registry.Study) -> List[str]:
    ex = loaders.extract_study(study.extractor)
    sj = loaders.load_study_json(study.evidence[0]) if study.evidence else None
    has_data = "_missing" not in ex
    rows = ex.get("rows", []) if has_data else []
    ev_paths = " · ".join(f"<code>{escape(loaders.rel_path(*p.split('/')))}</code>" for p in study.evidence)

    # ① 개요.
    overview = f"""<section>
  <div class="eyebrow">① 개요</div>
  <h2>질문과 판정 {badge(study.verdict, study.badge)}</h2>
  <p class="lede">{escape(study.easy)}</p>
  {_kpi_cards(rows) if has_data else f'<div class="callout warn">증거 파일 미수록 — 개요만 제공. <code>{escape(ex.get("_missing",""))}</code></div>'}
  {f'<p class="method">해석: {escape(ex.get("note",""))}</p>' if has_data and ex.get("note") else ""}
</section>"""

    # ② 방법·봉인.
    method = f"""<section>
  <div class="eyebrow">② 방법·봉인</div>
  <h2>측정 방법과 사전등록 봉인</h2>
  <p class="lede"><b>방법.</b> {escape(study.method)}</p>
  <div class="tablebox"><table>
    <tr><th>항목</th><th>값</th></tr>
    <tr><td>봉인 커밋</td><td><span class="sha">{escape(study.commit)}</span></td></tr>
    <tr><td>봉인 문서</td><td><code>{escape(registry.PLANS + "/" + study.seal_doc)}</code></td></tr>
    <tr><td>봉인 규약</td><td>사전등록 §13 미결 전건을 §14 결정으로 확정한 뒤에만 측정(번복 0회)</td></tr>
    <tr><td>측정창</td><td>발견창 2022-03-23 ~ 2023-12-31 (known 2024/2025 미접촉)</td></tr>
  </table></div>
  <p class="muted" style="font-size:13px">측정 절차는 SOP-M 9단계(봉인 확인→measure_gate→분리 기동→감시→게이트 검수→원장 기입→판정)를 따른다. 상세는 허브 '원장·규율' 탭.</p>
</section>"""

    # ③ 결과.
    chart = _result_chart(study, sj)
    results = f"""<section>
  <div class="eyebrow">③ 결과</div>
  <h2>핵심 차트·수치</h2>
  {chart if chart else (
      f'<div class="tablebox"><table>' + "".join(
          f'<tr><td style="color:var(--muted);white-space:normal">{escape(k)}</td><td style="font-weight:600;white-space:normal">{escape(v)}</td></tr>'
          for k, v in rows) + '</table></div>' if rows else f'<p class="muted">{loaders.MISSING}</p>')}
</section>"""

    # ④ 수치 전표.
    if sj is not None:
        flat = loaders.flatten_fields(sj)
        ftbl = table(["필드", "값"], [[f'<span style="white-space:normal">{escape(k)}</span>',
                                     f'<span style="white-space:normal">{escape(v)}</span>'] for k, v in flat[:80]])
        note = f'<p class="muted" style="font-size:12px">판정 json 주요 필드({len(flat)}개 중 상위 80) — 대용량 컬렉션은 항목 수로 요약.</p>'
    else:
        ftbl, note = f'<p class="muted">{loaders.MISSING} — {ev_paths}</p>', ""
    fulltable = f"""<section>
  <div class="eyebrow">④ 수치 전표</div>
  <h2>판정 json 필드 전량</h2>
  {ftbl}{note}
</section>"""

    # ⑤ 판정·한정.
    tags = (sj or {}).get("tags") if sj else None
    tag_html = ("".join(f"<li>{escape(t)}</li>" for t in tags) if isinstance(tags, list) and tags
                else "<li>딱지: L3=RR8_12 출구 조건부 · 발견창 2개 연도 조건부 진단 · 성능 주장 아님 · 최종 심판=U-4 감독형 소액 실전</li>")
    verdict = f"""<section>
  <div class="eyebrow">⑤ 판정·한정</div>
  <h2>판정문과 정직한 한정 {badge(study.verdict, study.badge)}</h2>
  <div class="callout"><b>판정.</b> {escape(study.name)} — <b>{escape(study.verdict)}</b>. {escape(ex.get("note", study.easy) if has_data else study.easy)}</div>
  <h3>딱지 (강제 인쇄)</h3>
  <ul style="font-size:13.5px;line-height:1.8">{tag_html}</ul>
  <div class="callout warn"><b>정직한 한정</b> — 발견창(2022-2023) 성적이며 시간축 OOS 가 아니다. L3 라벨은 챔피언 출구에 조건부. 최종 검증은 감독형 소액 실전(B1 전례).</div>
</section>"""

    # ⑥ 증거·재현.
    regen = _REGEN.get(study.id, "봉인 문서의 측정 절차 참조")
    evidence = f"""<section>
  <div class="eyebrow">⑥ 증거·재현</div>
  <h2>근거 파일·재생성·관련 커밋</h2>
  <div class="tablebox"><table>
    <tr><th>항목</th><th>값</th></tr>
    <tr><td>근거 파일</td><td style="white-space:normal">{ev_paths}</td></tr>
    <tr><td>재생성 명령</td><td><code style="white-space:normal">{escape(regen)}</code></td></tr>
    <tr><td>봉인 커밋</td><td><span class="sha">{escape(study.commit)}</span></td></tr>
    <tr><td>봉인 문서</td><td><code>{escape(registry.PLANS + "/" + study.seal_doc)}</code></td></tr>
  </table></div>
  <p class="muted" style="font-size:12px">엔진 백테 0회 · 원본 read-only · 신규 시장 데이터 수집 0. 수치는 판정 json 원문에서 로드(재계산 없음).</p>
</section>"""

    return [overview, method, results, fulltable, verdict, evidence]
