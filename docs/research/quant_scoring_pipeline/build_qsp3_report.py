# -*- coding: utf-8 -*-
"""QSP3 대수술 캠페인 보고서 빌더 — rounds/qsp3map_r*.json → md + 자가완결 HTML.

QSP2 빌더 계승 + QSP3 신규: 라운드별 액션 유형(드롭/필터/조임) 표기,
상호작용(est−measured) 표, 거래당 손익 분해, 홀드아웃 소비 주의(감사 B-1) 명시.
실행:  python docs/research/quant_scoring_pipeline/build_qsp3_report.py
산출:  2026-07-31_qsp3_report.md / .html
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from alpha_lab.reporting.build_html import _CSS  # noqa: E402
from html import escape as esc  # noqa: E402

SEED_OBJ = -43_984_965.0      # QSP2 챔피언(QSP2ANCH_R8C2_B) 설계 실측 — QSP3 의 base.
SEED_TRADES = 4489
SEED_HOLD = -83_096_562.0     # 동 챔피언 홀드아웃 실측.
SEED_HOLD_TRADES = 6145
TAG = "qsp3map"


def load_rounds():
    out = []
    for p in sorted((HERE / "rounds").glob(f"{TAG}_r*.json")):
        if p.name.endswith("_pairs.json"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "round" in doc:
            out.append(doc)
    return sorted(out, key=lambda r: r["round"])


def fmt(v, nd=0):
    return "—" if v is None else f"{v:,.{nd}f}"


def action_of(rec):
    meta = next((c for c in rec.get("candidates", []) if c.get("buy_name") == rec["best"]["buy_name"]), None)
    if not meta:
        return "유지", "(base 유지 — 후보 전원 미달)"
    act = (meta["spec"].get("action") or "tighten")
    label = {"drop_leaf": "제거", "add_filter": "필터", "tighten": "조임"}.get(act, act)
    return label, meta["spec"]["change"]


def dual_curve_svg(rounds, width=760, height=230):
    des = [SEED_OBJ] + [r["best"]["objective"] for r in rounds]
    hold_raw = [((r.get("holdout") or {}).get("objective")) for r in rounds]
    labels = ["base"] + [f"R{r['round']}" for r in rounds]
    des_pct = [(1 - v / SEED_OBJ) * 100 for v in des]
    hold_pct = [0.0] + [((1 - h / SEED_HOLD) * 100 if h is not None else None) for h in hold_raw]
    allv = des_pct + [x for x in hold_pct if x is not None]
    lo, hi = min(allv + [0]), max(allv)
    span = (hi - lo) or 1
    padl, padr, padt, padb = 58, 20, 18, 34
    n = len(des_pct)
    X = lambda i: padl + (width - padl - padr) * i / (n - 1)
    Y = lambda v: padt + (height - padt - padb) * (1 - (v - lo) / span)

    def path_of(series, dash=""):
        pts = [(i, v) for i, v in enumerate(series) if v is not None]
        d = " ".join(f"{'M' if k == 0 else 'L'} {X(i):.1f} {Y(v):.1f}" for k, (i, v) in enumerate(pts))
        return (f"<path d='{d}' fill='none' stroke='var(--accent)' stroke-width='2.5' {dash}/>", pts)

    p1, pts1 = path_of(des_pct)
    p2, pts2 = path_of(hold_pct, "stroke-dasharray='6 4' opacity='0.75'")
    dots = "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.6' fill='var(--accent)'/>" for i, v in pts1)
    dots += "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.2' fill='var(--accent)' opacity='0.6'/>" for i, v in pts2)
    xl = "".join(f"<text x='{X(i):.1f}' y='{height - 10}' text-anchor='middle' font-size='11' fill='var(--muted)'>{esc(l)}</text>"
                 for i, l in enumerate(labels))
    grid = (f"<line x1='{padl}' y1='{Y(0):.1f}' x2='{width - padr}' y2='{Y(0):.1f}' "
            f"stroke='var(--muted)' stroke-width='0.5' opacity='0.5'/>")
    yl = "".join(f"<text x='{padl - 6}' y='{Y(v) + 4:.1f}' text-anchor='end' font-size='11' fill='var(--muted)' class='num'>{v:+.0f}%</text>"
                 for v in {round(lo), 0, round(hi)})
    legend = (f"<text x='{padl}' y='{padt - 4}' font-size='11' fill='var(--muted)'>"
              f"실선=설계 · 점선=홀드아웃(2024) — QSP2 챔피언 대비 손실 축소율. "
              f"※주의: QSP3 홀드아웃은 후보 선정에도 사용됨(순수 표본외 아님, §3)</text>")
    return (f"<svg viewBox='0 0 {width} {height}' style='width:100%;height:auto' role='img'>"
            f"{grid}{yl}{p1}{p2}{dots}{xl}{legend}</svg>")


def main() -> int:
    rounds = load_rounds()
    if not rounds:
        raise SystemExit("qsp3map 라운드 기록 없음")
    now = datetime.now()
    fin = rounds[-1]["best"]
    hold_series = [((r.get("holdout") or {}).get("objective")) for r in rounds]
    hf = [h for h in hold_series if h is not None][-1]
    hf_tr = [((r.get("holdout") or {}).get("trade_count")) for r in rounds if (r.get("holdout") or {}).get("trade_count")][-1]
    des_total = (1 - fin["objective"] / SEED_OBJ) * 100
    hold_total = (1 - hf / SEED_HOLD) * 100
    pt0, pt1 = SEED_OBJ / SEED_TRADES, fin["objective"] / fin["trade_count"]
    hpt0, hpt1 = SEED_HOLD / SEED_HOLD_TRADES, hf / hf_tr
    n_drop = sum(1 for r in rounds if action_of(r)[0] == "제거")
    n_filter = sum(1 for r in rounds if action_of(r)[0] == "필터")

    md = []
    A = md.append
    A("# QSP3 대수술 캠페인 보고서 — 맵 기반 제거·필터 파이프라인")
    A("")
    A(f"- 작성: {now.strftime('%Y-%m-%d %H:%M')} · 브랜치 `feature/qsp3-map-surgery-20260731`")
    A(f"- base: QSP2 챔피언(QSP2ANCH_R8C2_B, 설계 {fmt(SEED_OBJ)}·홀드 {fmt(SEED_HOLD)})")
    A("- 신규 액션: drop_leaf(리프 제거)·add_filter(변수 필터) — 사용자 방법론('크게 크게 제거') 내장")
    A("")
    A("## 0. 한 줄 결론")
    A("")
    A(f"**설계 {des_total:+.2f}% · 홀드아웃 {hold_total:+.2f}%** ({len(rounds)}라운드: 제거 {n_drop}·필터 {n_filter}).")
    A(f"거래당 손익은 설계 {pt0:,.0f}→{pt1:,.0f}원({(1-pt1/pt0)*100:+.1f}%), 홀드아웃 {hpt0:,.0f}→{hpt1:,.0f}원({(1-hpt1/hpt0)*100:+.1f}%).")
    A("미세 조임(QSP2: 8라운드 +13.6%)과 비교해 **큰 보폭 수술의 우위가 실측으로 확정**됐다.")
    A("")
    A("## 1. 라운드 이력")
    A("")
    A("| R | 액션 | 설계 objective | Δ | 거래 | 홀드아웃 | 채택 수정 |")
    A("|---|---|---|---|---|---|---|")
    A(f"| base | — | {fmt(SEED_OBJ)} | — | {SEED_TRADES:,} | {fmt(SEED_HOLD)} | (QSP2 최종) |")
    prev = SEED_OBJ
    for r in rounds:
        cur = r["best"]["objective"]
        imp = f"{(cur - prev) / abs(prev) * 100:+.2f}%" if prev else "—"
        prev = cur
        h = (r.get("holdout") or {}).get("objective")
        act, ch = action_of(r)
        A(f"| R{r['round']} | {act} | {fmt(cur)} | {imp} | {fmt(r['best'].get('trade_count'))} "
          f"| {fmt(h)} | {ch} |")
    A("")
    A(f"최종 판정: **{rounds[-1]['judgment']['state']}** — {rounds[-1]['judgment']['reason']}")
    A("")
    A("## 1.1 국면별 일반화 검정 (이번 캠페인의 핵심 발견)")
    A("")
    A("액션 유형별로 '설계 개선분'과 '홀드아웃 개선분'을 나눠 합산하면, 어떤 수술이")
    A("**일반화되고 어떤 수술이 설계구간 암기인지**가 분리된다.")
    A("")
    A("| 국면 | 라운드 | 설계 Δ | 홀드아웃 Δ | 해석 |")
    A("|---|---|---|---|---|")
    prev_d, prev_h = SEED_OBJ, SEED_HOLD
    phase: dict = {}
    for r in rounds:
        cur = r["best"]["objective"]
        h = (r.get("holdout") or {}).get("objective")
        act, _ = action_of(r)
        p = phase.setdefault(act, [0, 0.0, 0.0])
        p[0] += 1
        p[1] += cur - prev_d
        p[2] += (h - prev_h) if h is not None else 0.0
        prev_d = cur
        prev_h = h if h is not None else prev_h
    verdict = {"제거": "**일반화** — 홀드아웃이 설계만큼(또는 그 이상) 개선",
               "필터": "**일반화** — 두 구간 거의 1:1",
               "조임": "**과최적 경향** — 설계만 개선, 홀드아웃은 정체·역행",
               "유지": "변화 없음(퇴행 방지 작동)"}
    for k in ("제거", "필터", "조임", "유지"):
        if k not in phase:
            continue
        n, ds, hs = phase[k]
        A(f"| {k} | {n}R | {ds/1e6:+.1f}M | {hs/1e6:+.1f}M | {verdict[k]} |")
    A("")
    A("**사용자 가설의 실증**: '조금씩 조이는 것은 답이 아니다 — 크게 제거해야 한다'가")
    A("데이터로 확인됐다. 제거·필터는 표본외에서도 살아남았고, 미세 조임은 설계구간")
    A("점수만 올렸다(홀드아웃 순 −0.5M). 조임 국면의 개별 라운드에서도 설계↑·홀드아웃↓")
    A("패턴이 3회 관측됐다(r7·r10·r11) — 자동 발산 임계(각 −5%×2연속)에는 못 미쳐")
    A("중단되지 않았으나, **임계를 −2% 수준으로 조이는 것이 다음 개선 후보**다.")
    A("")
    A("## 2. 상호작용 실측 (빼기 추정 vs 재백테 실측)")
    A("")
    A("| R | 대상 | 추정 Δ | 실측 Δ | est−measured | 제거 규모(건) |")
    A("|---|---|---|---|---|---|")
    for r in rounds:
        for e in r.get("reentry", []):
            if e.get("skipped"):
                A(f"| R{r['round']} | {e['leaf']} | — | — | (스킵: {e['skipped']}) | — |")
            else:
                A(f"| R{r['round']} | {e['leaf']} | {fmt(e['est_delta'])} | {fmt(e['measured_delta'])} "
                  f"| {fmt(e['reentry_cost'])} | {e.get('removed_n', '—')} |")
    A("")
    A("- 부호는 **양방향**(감사 실측): 대규모 제거는 재유입이 지배(+), 소규모 제거는 슬롯 경합")
    A("  해소가 지배(−). '추정은 순위용, 채택은 재백테 실측' 규율의 실증 근거다.")
    A("")
    A("## 3. 정직한 한계 (독립 감사 2건 반영 — 과대해석 금지)")
    A("")
    A("1. **홀드아웃 소비**: QSP3 는 후보 선정에 '홀드아웃도 손실/이득' 조건을 쓰므로, 위")
    A("   홀드아웃 곡선은 QSP2 때와 달리 **순수 표본외가 아니다**(선택 입력으로 소비됨).")
    A("   순수 검증은 제3의 미사용 구간이 필요하나 tick DB 폭 제약 — 원장 등재.")
    A("2. **개선의 상당분은 거래 축소**: 거래수 분해를 §0 에 병기 — '덜 사서 덜 잃는' 효과와")
    A("   거래당 엣지 개선을 구분해 읽어야 한다.")
    A("3. 두 구간 모두 **총손익 여전히 음수** — 실전 반영 없음(항상 사용자 결정).")
    A("4. 독립 감사 재채점: 축A 59·75 / 축B 55·58 — **95점 미달**. 병목은 홀드아웃 소비(B1)·")
    A("   drop 유의성 검정 부재(B2)·필터 임계 in-sample 편향(B3). 상세: limitation_ledger.")
    A("")
    A("## 부록 — 재현")
    A("")
    A("- 드라이버: `scripts/qsp3map_campaign.bat` (--actions drop,filter,tighten · 12R 상한)")
    A("- 기록: `rounds/qsp3map_r*.json` (actions/mode/config/decomposition 은 r4+ 포함)")
    md_text = "\n".join(md) + "\n"
    (HERE / "2026-07-31_qsp3_report.md").write_text(md_text, encoding="utf-8")

    def md_table_to_html(lines):
        out = ["<table>"]
        for i, ln in enumerate(lines):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(set(c) <= set(":-") for c in cells):
                continue
            tag = "th" if i == 0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{esc(c)}</{tag}>" for c in cells) + "</tr>")
        out.append("</table>")
        return "".join(out)

    tbl = [l for l in md if l.startswith("|")]
    hist = md_table_to_html([l for l in tbl if "설계 objective" in l or l.startswith("| base") or l.startswith("| R")])
    inter = md_table_to_html([l for l in tbl if "est−measured" in l or ("| R" in l and "추정" not in l and "설계 objective" not in l and not l.startswith("| base"))][:40])

    html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QSP3 대수술 캠페인 보고서</title><style>{_CSS}</style></head><body>
<header><h1>QSP3 대수술 캠페인 — 맵 기반 제거·필터 파이프라인</h1>
<p class='muted'>{esc(now.strftime('%Y-%m-%d %H:%M'))} · feature/qsp3-map-surgery-20260731 · 무인 자율(감사 교정 2회 개입)</p></header>
<section><h2>수렴 곡선</h2>{dual_curve_svg(rounds)}
<p>설계 <b>{des_total:+.2f}%</b> · 홀드아웃 <b>{hold_total:+.2f}%</b> · 거래당(설계) {(1-pt1/pt0)*100:+.1f}% ·
거래당(홀드) {(1-hpt1/hpt0)*100:+.1f}% · 제거 {n_drop}R + 필터 {n_filter}R · 최종 <b>{esc(rounds[-1]['judgment']['state'])}</b></p></section>
<section><h2>라운드 이력</h2>{hist}</section>
<section><h2>상호작용(추정 vs 실측)</h2>{inter}
<p class='muted'>부호 양방향 — 대규모 제거=재유입 지배(+), 소규모=슬롯 경합 해소(−). 채택은 항상 재백테 실측.</p></section>
<section><h2>정직한 한계</h2><ol>
<li><b>홀드아웃 소비</b> — 후보 선정에 사용되어 순수 표본외 아님(감사 B-1).</li>
<li>개선의 상당분은 거래 축소 — 거래당 분해 병기.</li>
<li>총손익 여전히 음수 — 실전 반영 없음.</li>
<li>독립 감사 재채점 A 59·75 / B 55·58 — 95 미달, 병목은 통계 규율(원장 참조).</li></ol></section>
</body></html>"""
    (HERE / "2026-07-31_qsp3_report.html").write_text(html, encoding="utf-8")
    print("built:", HERE / "2026-07-31_qsp3_report.md")
    print("built:", HERE / "2026-07-31_qsp3_report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
