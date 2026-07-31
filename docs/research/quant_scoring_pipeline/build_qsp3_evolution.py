# -*- coding: utf-8 -*-
"""QSP3 세대 진화 시각화 — 액션별 개선 기여 + 리프 지형 변화(base vs 최종).

QSP2 진화 페이지의 후속: 이번엔 "무엇을 어떻게 바꿨는가"가 3종(제거/필터/조임)이라
액션 유형별 기여를 분해해 보여준다. 사용자 방법론('크게 제거 → 필터 → 미세 조임')이
실제로 그 순서와 크기로 작동했는지가 한 화면에서 읽혀야 한다.

실행: python docs/research/quant_scoring_pipeline/build_qsp3_evolution.py
산출: 2026-07-31_qsp3_evolution.html
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

SEED_OBJ = -43_984_965.0
SEED_TRADES = 4489
SEED_HOLD = -83_096_562.0
BASE_CSV = "backtest/csv/stock_bt_QSP2ANCH_R8C2_B_20260731061034.csv"
TIME_ROWS = ["B1_900_902", "B2_902_905", "B3_905_910", "B4_910_920"]
TIME_LABEL = {"B1_900_902": "09:00~02분", "B2_902_905": "02~05분",
              "B3_905_910": "05~10분", "B4_910_920": "10~20분"}
CAP_COLS = ["S_3000미만", "M1_3000_5000", "M2_5000_10000", "L_10000이상"]
CAP_LABEL = {"S_3000미만": "소형 <3000억", "M1_3000_5000": "3000~5000억",
             "M2_5000_10000": "5000억~1조", "L_10000이상": "대형 ≥1조"}
WARM, COOL, NEUT = (217, 118, 43), (74, 127, 181), (242, 240, 236)
ACT_LABEL = {"drop_leaf": "제거", "add_filter": "필터", "tighten": "조임"}


def load_rounds():
    out = []
    for p in sorted((HERE / "rounds").glob("qsp3map_r*.json")):
        if p.name.endswith("_pairs.json"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "round" in doc:
            out.append(doc)
    return sorted(out, key=lambda r: r["round"])


def leaf_table(csv_rel: str):
    path = REPO / csv_rel if not Path(csv_rel).is_absolute() else Path(csv_rel)
    df = enrich(pd.read_csv(path, encoding="utf-8-sig")).df
    return df.groupby(["leaf_time", "leaf_cap"]).agg(n=("수익금", "size"), pnl=("수익금", "sum"))


def tint(pnl, vmax):
    if pnl is None:
        return "#fff", 0.0
    t = min(1.0, abs(pnl) / vmax) ** 0.7 * 0.85
    base = WARM if pnl < 0 else COOL
    r, g, b = (round(n + (c - n) * t) for c, n in zip(base, NEUT))
    return f"rgb({r},{g},{b})", t


def heat_panel(title, tbl, vmax):
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
            val = "제거됨" if pnl is None else f"{pnl/1e6:+.1f}M"
            cells.append(f"<div class='hm-c' style='background:{bg};color:{ink}'"
                         f" title='{esc(tr)}×{esc(c)} · {n:,}건'>"
                         f"<b>{val}</b><span>{n:,}건</span></div>")
    cells.append("</div>")
    return "".join(cells)


def main() -> int:
    rounds = load_rounds()
    if not rounds:
        raise SystemExit("qsp3map 기록 없음")
    now = datetime.now()

    # 액션별 기여 분해.
    contrib = {"제거": 0.0, "필터": 0.0, "조임": 0.0, "유지": 0.0}
    counts = dict(contrib)
    prev = SEED_OBJ
    rows_hist = []
    for r in rounds:
        cur = r["best"]["objective"]
        delta = cur - prev
        meta = next((c for c in r.get("candidates", []) if c.get("buy_name") == r["best"]["buy_name"]), None)
        act = ACT_LABEL.get((meta or {}).get("spec", {}).get("action", "tighten"), "조임") if meta else "유지"
        contrib[act] += delta
        counts[act] += 1
        h = (r.get("holdout") or {}).get("objective")
        dec = r.get("decomposition") or {}
        rows_hist.append((r["round"], act, cur, delta, r["best"].get("trade_count"), h,
                          (meta or {}).get("spec", {}).get("change", "(base 유지)"),
                          dec.get("best_per_trade")))
        prev = cur
    total_gain = prev - SEED_OBJ

    base_tbl = leaf_table(BASE_CSV)
    fin_tbl = leaf_table(rounds[-1]["best"]["csv_path"])
    vmax = max(abs(float(base_tbl["pnl"].min())), abs(float(fin_tbl["pnl"].min())),
               abs(float(base_tbl["pnl"].max())), abs(float(fin_tbl["pnl"].max())))

    # 액션 기여 막대.
    bar_w = 700
    bars = []
    for k in ("제거", "필터", "조임", "유지"):
        v = contrib[k]
        if counts[k] == 0:
            continue
        frac = v / total_gain if total_gain else 0
        bars.append(
            f"<div class='cb-row'><span class='cb-lab'>{esc(k)} <em>{counts[k]}R</em></span>"
            f"<span class='cb-track'><span class='cb-fill' style='width:{max(0.5, frac*100):.1f}%'></span></span>"
            f"<span class='cb-val'>{v/1e6:+.1f}M · {frac*100:.0f}%</span></div>")

    hist_rows = "".join(
        f"<tr><td>R{n}</td><td><span class='tag tag-{'d' if a=='제거' else ('f' if a=='필터' else 't')}'>{esc(a)}</span></td>"
        f"<td class='num'>{obj:,.0f}</td><td class='num'>{dl/1e6:+.2f}M</td><td class='num'>{tr:,}</td>"
        f"<td class='num'>{'—' if h is None else format(h, ',.0f')}</td>"
        f"<td class='num'>{'—' if pt is None else format(pt, ',.0f')}</td><td class='chg'>{esc(ch[:78])}</td></tr>"
        for n, a, obj, dl, tr, h, ch, pt in rows_hist)

    fin = rounds[-1]["best"]
    hf = [((r.get("holdout") or {}).get("objective")) for r in rounds
          if (r.get("holdout") or {}).get("objective")][-1]
    css_extra = """
.hm-title{font-weight:600;margin:14px 0 6px}
.hm-grid{display:grid;grid-template-columns:110px repeat(4,1fr);gap:2px}
.hm-h{font-size:12px;color:var(--muted);align-self:center;padding:2px 4px}
.hm-c{padding:8px 6px;border-radius:4px;text-align:center;font-size:13px}
.hm-c span{display:block;font-size:11px;opacity:.75}
.cb-row{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:13px}
.cb-lab{width:96px;color:var(--muted)}.cb-lab em{font-style:normal;opacity:.7;font-size:11px}
.cb-track{flex:1;height:14px;background:rgba(128,128,128,.15);border-radius:7px;overflow:hidden}
.cb-fill{display:block;height:100%;background:var(--accent);border-radius:7px}
.cb-val{width:150px;text-align:right;font-variant-numeric:tabular-nums}
.tag{font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--line-1)}
.tag-d{color:#d9762b}.tag-f{color:#4a7fb5}.tag-t{color:var(--muted)}
td.chg{font-size:11px;color:var(--muted)}
table.ev{width:100%;border-collapse:collapse;font-size:12.5px}
table.ev th,table.ev td{padding:5px 8px;border-bottom:1px solid var(--line-1);text-align:left}
table.ev td.num{text-align:right;font-variant-numeric:tabular-nums}
"""
    html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QSP3 세대 진화</title><style>{_CSS}{css_extra}</style></head><body>
<header><h1>QSP3 세대 진화 — 제거·필터·조임이 각각 얼마나 기여했나</h1>
<p class='muted'>{esc(now.strftime('%Y-%m-%d %H:%M'))} · {len(rounds)}라운드 · base=QSP2 챔피언</p></header>

<section><h2>1. 액션 유형별 개선 기여</h2>
{''.join(bars)}
<p><b>읽는 법</b>: 사용자 방법론대로 <b>큰 제거가 먼저</b> 지형을 바꾸고, 필터가 남은 손실 구역을
정밀 차단하며, 조임이 마무리한다. 막대 길이는 총개선 {total_gain/1e6:+.1f}M 중 각 액션의 몫이다.</p></section>

<section><h2>2. 라운드 이력</h2>
<table class='ev'><tr><th>R</th><th>액션</th><th>설계 손익</th><th>Δ</th><th>거래</th><th>홀드아웃</th><th>거래당</th><th>채택 수정</th></tr>
{hist_rows}</table></section>

<section><h2>3. 리프 지형 변화 (설계구간)</h2>
{heat_panel('base — QSP2 챔피언 (16리프)', base_tbl, vmax)}
{heat_panel(f"최종 — QSP3 R{rounds[-1]['round']} (제거된 리프는 '제거됨')", fin_tbl, vmax)}
<p>손실이 몰려 있던 소형주 열과 후반 밴드가 제거·필터로 사라지고, 남은 지형이 훨씬 옅어졌다.
QSP2 때는 8라운드를 조여도 지형 모양이 그대로였다는 점과 대비된다.</p></section>

<section><h2>4. 정직한 한계</h2><ol>
<li>설계 {(1-fin['objective']/SEED_OBJ)*100:+.1f}% · 홀드아웃 {(1-hf/SEED_HOLD)*100:+.1f}%지만
<b>두 구간 모두 총손익은 여전히 음수</b> — 실전 반영 없음.</li>
<li>거래수 {SEED_TRADES:,}→{fin['trade_count']:,}({(fin['trade_count']/SEED_TRADES-1)*100:+.1f}%) —
개선의 상당분은 '덜 사서 덜 잃은' 효과다. 거래당 손익을 함께 보라(위 표).</li>
<li>QSP3 홀드아웃은 후보 <b>선정에도 사용</b>되어 순수 표본외가 아니다(독립 감사 B-1).</li>
<li>독립 감사 재채점 축A 59·75 / 축B 55·58 — <b>95점 미달</b>. 병목은 통계 규율(원장 참조).</li>
</ol></section>
</body></html>"""
    out = HERE / "2026-07-31_qsp3_evolution.html"
    out.write_text(html, encoding="utf-8")
    print("built:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
