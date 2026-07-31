# -*- coding: utf-8 -*-
"""QSP2 세대 진화 시각화 — 라운드별 무엇이 바뀌었고 리프 손익 지형이 어떻게 변했는가.

패널: ① 용어 1장 ② 설계·홀드아웃 이중 곡선 ③ 라운드별 채택 수정 이력
     ④ 리프 손익 히트맵 3패널(r0설계/r8설계/r8홀드아웃, 공유 스케일)
     ⑤ '크게 제거' 시나리오 실측(사용자 가설 검증).
색: 다이버징(손실=주황 / 이익=파랑 / 중립=회색 중점), 셀에 수치 병기(색 단독 의존 금지).
실행: python docs/research/quant_scoring_pipeline/build_qsp2_evolution.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402

from alpha_lab.reporting.build_html import _CSS  # noqa: E402
from ai_strategy_loop.autopsy.label_dataset import enrich  # noqa: E402
from html import escape as esc  # noqa: E402

SEED_OBJ = -50_911_184.0
FILES = {
    "r0설계": "backtest/csv/stock_bt_QSP2_T_ANCH_900_920_B_20260730225730.csv",
    "r8설계": "backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731061034.csv",
    "r8홀드": "backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731061424.csv",
}
TIME_ROWS = ["B1_900_902", "B2_902_905", "B3_905_910", "B4_910_920"]
TIME_LABEL = {"B1_900_902": "09:00~02분", "B2_902_905": "02~05분",
              "B3_905_910": "05~10분", "B4_910_920": "10~20분"}
CAP_COLS = ["S_3000미만", "M1_3000_5000", "M2_5000_10000", "L_10000이상"]
CAP_LABEL = {"S_3000미만": "소형 <3000억", "M1_3000_5000": "3000~5000억",
             "M2_5000_10000": "5000억~1조", "L_10000이상": "대형 ≥1조"}
# 다이버징: 손실(주황)↔이익(파랑), 중점 중립 — CVD 안전 쌍.
WARM = (217, 118, 43)   # 손실
COOL = (74, 127, 181)   # 이익
NEUT = (242, 240, 236)


def leaf_tables():
    out = {}
    for k, f in FILES.items():
        df = enrich(pd.read_csv(REPO / f, encoding="utf-8-sig")).df
        g = df.groupby(["leaf_time", "leaf_cap"]).agg(n=("수익금", "size"), pnl=("수익금", "sum"))
        out[k] = g
    return out


def tint(pnl, vmax):
    if pnl is None:
        return "#fff", 0.0
    t = min(1.0, abs(pnl) / vmax) ** 0.7 * 0.85
    base = WARM if pnl < 0 else COOL
    r, g, b = (round(n + (c - n) * t) for c, n in zip(base, NEUT))
    return f"rgb({r},{g},{b})", t


def heat_panel(title, tbl, vmax, drop_leaves):
    cells = [f"<div class='hm-title'>{esc(title)}</div>", "<div class='hm-grid'>", "<div class='hm-corner'></div>"]
    for c in CAP_COLS:
        cells.append(f"<div class='hm-h'>{esc(CAP_LABEL[c])}</div>")
    for tr in TIME_ROWS:
        cells.append(f"<div class='hm-h'>{esc(TIME_LABEL[tr])}</div>")
        for c in CAP_COLS:
            try:
                row = tbl.loc[(tr, c)]
                pnl, n = float(row["pnl"]), int(row["n"])
            except KeyError:
                pnl, n = None, 0
            bg, t = tint(pnl, vmax)
            ink = "#fff" if t > 0.55 else "var(--ink, #222)"
            mark = " hm-drop" if f"{tr}×{c}" in drop_leaves else ""
            val = "—" if pnl is None else f"{pnl/1e6:+.1f}M"
            cells.append(f"<div class='hm-c{mark}' style='background:{bg};color:{ink}'"
                         f" title='{esc(tr)}×{esc(c)} · {n:,}건 · {0 if pnl is None else pnl:,.0f}원'>"
                         f"<b>{val}</b><span>{n:,}건</span></div>")
    cells.append("</div>")
    return "".join(cells)


def main() -> int:
    now = datetime.now()
    tabs = leaf_tables()
    rounds = []
    for p in sorted((HERE / "rounds").glob("qsp2anch_r*.json")):
        if p.name.endswith("_pairs.json"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "round" in d:
            rounds.append(d)
    rounds.sort(key=lambda r: r["round"])

    vmax = max(abs(float(t["pnl"].min())) for t in tabs.values())
    vmax = max(vmax, max(float(t["pnl"].max()) for t in tabs.values()))

    # 제거 시나리오(설계 오름차순, 홀드아웃 동시 확인).
    m = tabs["r8설계"].join(tabs["r8홀드"], lsuffix="_d", rsuffix="_h", how="outer").fillna(0)
    m = m.sort_values("pnl_d")
    tot_d, tot_h = m["pnl_d"].sum(), m["pnl_h"].sum()
    drop3 = {f"{t}×{c}" for (t, c) in m.index[:3]}
    scen = []
    cd = ch = 0
    for i, (idx, row) in enumerate(m.iterrows(), 1):
        if i > 8:
            break
        cd += row["pnl_d"]; ch += row["pnl_h"]
        scen.append((i, f"{idx[0]}×{idx[1]}", tot_d - cd, (1 - (tot_d - cd) / tot_d) * 100,
                     tot_h - ch, (1 - (tot_h - ch) / tot_h) * 100))

    # 이중 곡선(% 개선, 시드=0).
    des = [SEED_OBJ] + [r["best"]["objective"] for r in rounds]
    hold_raw = [((r.get("holdout") or {}).get("objective")) for r in rounds]
    h0 = next(h for h in hold_raw if h is not None)
    des_pct = [(1 - v / SEED_OBJ) * 100 for v in des]
    hold_pct = [None] + [(1 - h / h0) * 100 if h is not None else None for h in hold_raw]
    labels = ["시드"] + [f"R{r['round']}" for r in rounds]
    W, H, padl, padr, padt, padb = 760, 210, 52, 16, 16, 30
    allv = des_pct + [x for x in hold_pct if x is not None]
    lo, hi = min(allv + [0]), max(allv)
    span = (hi - lo) or 1
    X = lambda i: padl + (W - padl - padr) * i / (len(des_pct) - 1)
    Y = lambda v: padt + (H - padt - padb) * (1 - (v - lo) / span)

    def path(series, dash=""):
        pts = [(i, v) for i, v in enumerate(series) if v is not None]
        dstr = " ".join(f"{'M' if k == 0 else 'L'} {X(i):.1f} {Y(v):.1f}" for k, (i, v) in enumerate(pts))
        return f"<path d='{dstr}' fill='none' stroke='var(--accent)' stroke-width='2.5' {dash}/>", pts

    p1, pts1 = path(des_pct)
    p2, pts2 = path(hold_pct, "stroke-dasharray='6 4' opacity='0.7'")
    dots = "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.5' fill='var(--accent)'>"
                   f"<title>{esc(labels[i])} 설계 {v:+.2f}%</title></circle>" for i, v in pts1)
    dots += "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.2' fill='var(--accent)' opacity='0.55'>"
                    f"<title>{esc(labels[i])} 홀드아웃 {v:+.2f}%</title></circle>" for i, v in pts2)
    xl = "".join(f"<text x='{X(i):.1f}' y='{H-9}' text-anchor='middle' font-size='11' fill='var(--muted)'>{esc(l)}</text>"
                 for i, l in enumerate(labels))
    curve = (f"<svg viewBox='0 0 {W} {H}' style='width:100%;height:auto'>"
             f"<line x1='{padl}' y1='{Y(0):.1f}' x2='{W-padr}' y2='{Y(0):.1f}' stroke='var(--muted)' stroke-width='0.5' opacity='0.5'/>"
             + "".join(f"<text x='{padl-6}' y='{Y(v)+4:.1f}' text-anchor='end' font-size='11' fill='var(--muted)' class='num'>{v:+.0f}%</text>"
                       for v in {0.0, round(hi, 0)})
             + p1 + p2 + dots + xl + "</svg>")

    ev_rows = "".join(
        "<tr><td>R{r}</td><td>{ch}</td><td class='num'>{d:,.0f}</td><td class='num'>{h}</td><td>{st}</td></tr>".format(
            r=rec["round"],
            ch=esc((next((c["spec"]["change"] for c in rec.get("candidates", [])
                          if c.get("buy_name") == rec["best"]["buy_name"]), "(base 유지 — 후보 전원 미달)"))),
            d=rec["best"]["objective"],
            h=("{:,.0f}".format((rec.get("holdout") or {}).get("objective"))
               if (rec.get("holdout") or {}).get("objective") is not None else "—"),
            st=esc(rec["judgment"]["state"])) for rec in rounds)

    scen_rows = "".join(
        f"<tr><td>{i}</td><td>{esc(leaf)}</td><td class='num'>{nd:,.0f}</td><td class='num'>{pd_:+.1f}%</td>"
        f"<td class='num'>{nh:,.0f}</td><td class='num'>{ph:+.1f}%</td></tr>"
        for i, leaf, nd, pd_, nh, ph in scen)

    extra_css = """
.hm-title{font-weight:600;margin:14px 0 6px}
.hm-grid{display:grid;grid-template-columns:110px repeat(4,1fr);gap:2px}
.hm-h{font-size:12px;color:var(--muted);align-self:center;padding:2px 4px}
.hm-c{padding:8px 6px;border-radius:4px;text-align:center;font-size:13px}
.hm-c span{display:block;font-size:11px;opacity:.75}
.hm-drop{outline:2px dashed #8a4a1f;outline-offset:-2px}
.legend-dv{display:flex;gap:14px;align-items:center;font-size:12px;color:var(--muted);margin:8px 0}
.sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:4px}
"""
    html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QSP2 세대 진화 시각화</title><style>{_CSS}{extra_css}</style></head><body>
<header><h1>QSP2 세대 진화 — 라운드별로 무엇이 바뀌었나</h1>
<p class='muted'>{esc(now.strftime('%Y-%m-%d %H:%M'))} · 전 라운드 무인 자율 · 데이터: rounds/qsp2anch_r1~r8.json + 거래 CSV 재집계</p></header>

<section><h2>0. 용어 한 장</h2>
<p><b>QSP</b> = Quant Scoring Pipeline(퀀트 채점 파이프라인) — "백테스트 결과를 라벨(정답지)로 삼아
조건식을 스스로 고치는 시스템"의 연구 이름. <b>QSP1</b> = 1차: 이 기계 자체를 만들고 검증한 프로그램.
<b>QSP2</b> = 2차: 검증된 기계에 <b>좋은 시드</b>(과거 실증 승자 anchor 조건식을 16리프 골격에 이식)를 넣고
<b>홀드아웃</b>(본 적 없는 2024년 = 본고사)을 매 라운드 자동 응시시킨 캠페인.
<b>리프(leaf)</b> = 시간 4밴드 × 시총 4단계로 나눈 16개의 진입 구역 — 아래 히트맵의 칸 하나.</p></section>

<section><h2>1. 수렴 곡선 — 설계(실선) vs 홀드아웃(점선)</h2>{curve}
<p class='muted'>시드 대비 손실 축소율. 두 선이 같이 오르면 일반화, 실선만 오르면 암기(과최적) 신호.</p></section>

<section><h2>2. 라운드별 채택 수정 (세대 진화 이력)</h2>
<table><tr><th>R</th><th>채택된 수정</th><th>설계 손익</th><th>홀드아웃 손익</th><th>판정</th></tr>{ev_rows}</table>
<p class='muted'>전부 "절 상수를 승자 통계 위치로 조이기" — 한 라운드 +1~3% 수준의 미세 조정이었다.</p></section>

<section><h2>3. 리프 손익 지형 (히트맵, 공유 스케일)</h2>
<div class='legend-dv'><span><span class='sw' style='background:rgb({WARM[0]},{WARM[1]},{WARM[2]})'></span>손실</span>
<span><span class='sw' style='background:rgb({NEUT[0]},{NEUT[1]},{NEUT[2]})'></span>0 근처</span>
<span><span class='sw' style='background:rgb({COOL[0]},{COOL[1]},{COOL[2]})'></span>이익</span>
<span>· 점선 테두리 = 제거 후보(하위 3리프)</span></div>
{heat_panel('r0 시드 · 설계구간', tabs['r0설계'], vmax, drop3)}
{heat_panel('r8 챔피언 · 설계구간 (8라운드 조임 후)', tabs['r8설계'], vmax, drop3)}
{heat_panel('r8 챔피언 · 홀드아웃(표본외 2024)', tabs['r8홀드'], vmax, drop3)}
<p><b>읽는 법</b>: 8라운드를 조여도 손실 지형의 모양은 거의 그대로다 — 손실은 <b>소형주(&lt;3000억) 열</b>에
구조적으로 몰려 있고, 조임은 이 기둥을 얇게 깎을 뿐 제거하지 못했다. 홀드아웃 패널에서도 같은 열이
가장 붉다 = 우연이 아니라 구조.</p></section>

<section><h2>4. "크게 제거" 실측 — 사용자 가설 검증</h2>
<table><tr><th>하위 k개 제거</th><th>마지막 제거 리프</th><th>설계 손익</th><th>개선</th><th>홀드아웃 손익</th><th>개선</th></tr>{scen_rows}</table>
<p><b>하위 3개(전부 소형주 밴드) 제거만으로 설계 +79.8% · 홀드아웃 +56.9%</b> — 8라운드 조임 전체
(+13.6%/+9.2%)의 약 6배가 한 번의 제거에서 나온다. 단, 설계가 흑자 전환되는 7개 제거 구간에서도
홀드아웃은 여전히 적자(−26.6M) — 제거는 강력하지만 만능이 아니며, 홀드아웃 동방향 확인이 항상 필요하다.</p></section>

<section><h2>5. 주의 — 반대 사례도 있다</h2>
<p>B3_905~910분×3000~5000억 리프는 <b>설계 +1.0M(흑자)인데 홀드아웃 −9.4M</b> — 설계구간만 보고
"남길 리프"를 고르면 이런 가짜 흑자 리프에 속는다. 제거/유지 판단 모두 홀드아웃 병행이 필수인 이유.</p></section>
</body></html>"""
    out = HERE / "2026-07-31_qsp2_evolution.html"
    out.write_text(html, encoding="utf-8")
    print("built:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
