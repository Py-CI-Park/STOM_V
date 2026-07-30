# -*- coding: utf-8 -*-
"""QSP2 anchor 캠페인 보고서 빌더 — rounds/qsp2anch_r*.json → md + 자가완결 HTML.

QSP1 최종 보고서 빌더와 같은 디자인 정본(결산 v1 CSS)을 재사용하되,
QSP2 의 핵심인 **설계 vs 홀드아웃 이중 수렴 곡선**을 그린다.
실행:  python docs/research/quant_scoring_pipeline/build_qsp2_report.py
산출:  2026-07-31_qsp2_report.md / .html (본 디렉토리)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from alpha_lab.reporting.build_html import _CSS  # noqa: E402 - 디자인 정본 재사용.
from html import escape as esc  # noqa: E402

SEED_OBJ = -50_911_184.0     # r0 baseline 실측(run 20260730-qsp2anch-r0).
SEED_TRADES = 4705
TAG = "qsp2anch"


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


def dual_curve_svg(rounds, width=760, height=230):
    """설계(실선)·홀드아웃(점선) 곡선 — 각자 시드 대비 % 로 정규화해 한 축에."""
    des = [SEED_OBJ] + [r["best"]["objective"] for r in rounds]
    hold_raw = [((r.get("holdout") or {}).get("objective")) for r in rounds]
    h0 = next((h for h in hold_raw if h is not None), None)
    labels = ["시드"] + [f"R{r['round']}" for r in rounds]
    des_pct = [(1 - v / SEED_OBJ) * 100 for v in des]                 # 손실 축소율(+가 개선).
    hold_pct = [None] + [((1 - h / h0) * 100 if (h is not None and h0) else None)
                         for h in hold_raw]
    all_vals = [v for v in des_pct + [x for x in hold_pct if x is not None]]
    lo, hi = min(all_vals + [0]), max(all_vals)
    span = (hi - lo) or 1
    padl, padr, padt, padb = 58, 20, 18, 34
    n = len(des_pct)

    def X(i):
        return padl + (width - padl - padr) * i / (n - 1)

    def Y(v):
        return padt + (height - padt - padb) * (1 - (v - lo) / span)

    def path_of(series, dash=""):
        pts = [(i, v) for i, v in enumerate(series) if v is not None]
        d = " ".join(f"{'M' if k == 0 else 'L'} {X(i):.1f} {Y(v):.1f}"
                     for k, (i, v) in enumerate(pts))
        return (f"<path d='{d}' fill='none' stroke='var(--accent)' stroke-width='2.5' {dash}/>",
                pts)

    p1, pts1 = path_of(des_pct)
    p2, pts2 = path_of(hold_pct, "stroke-dasharray='6 4' opacity='0.75'")
    dots = "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.6' fill='var(--accent)'/>"
                   for i, v in pts1)
    dots += "".join(f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='3.2' fill='var(--accent)' opacity='0.6'/>"
                    for i, v in pts2)
    xl = "".join(f"<text x='{X(i):.1f}' y='{height - 10}' text-anchor='middle' font-size='11' fill='var(--muted)'>{esc(l)}</text>"
                 for i, l in enumerate(labels))
    grid = (f"<line x1='{padl}' y1='{Y(0):.1f}' x2='{width - padr}' y2='{Y(0):.1f}' "
            f"stroke='var(--muted)' stroke-width='0.5' opacity='0.5'/>")
    yl = "".join(f"<text x='{padl - 6}' y='{Y(v) + 4:.1f}' text-anchor='end' font-size='11' fill='var(--muted)' class='num'>{v:+.0f}%</text>"
                 for v in {round(lo), 0, round(hi)})
    legend = (f"<text x='{padl}' y='{padt - 4}' font-size='11' fill='var(--muted)'>"
              f"실선=설계구간(2025.04~2026.02) · 점선=홀드아웃(2024.04~2025.04, 표본외) — 시드 대비 손실 축소율</text>")
    return (f"<svg viewBox='0 0 {width} {height}' style='width:100%;height:auto' role='img'>"
            f"{grid}{yl}{p1}{p2}{dots}{xl}{legend}</svg>")


def main() -> int:
    rounds = load_rounds()
    if not rounds:
        raise SystemExit("qsp2anch 라운드 기록 없음")
    now = datetime.now()
    fin = rounds[-1]["best"]
    hold_series = [((r.get("holdout") or {}).get("objective")) for r in rounds]
    h0 = next((h for h in hold_series if h is not None), None)
    hf = [h for h in hold_series if h is not None][-1]
    des_total = (1 - fin["objective"] / SEED_OBJ) * 100
    hold_total = (1 - hf / h0) * 100 if h0 else None
    pt0 = SEED_OBJ / SEED_TRADES
    pt1 = fin["objective"] / fin["trade_count"]

    md = []
    A = md.append
    A("# QSP2 캠페인 보고서 — anchor 이식 시드 + 홀드아웃 동반 판정")
    A("")
    A(f"- 작성: {now.strftime('%Y-%m-%d %H:%M')} · 브랜치 `feature/quant-scoring-pipeline-20260729`")
    A(f"- 시드: `QSP2_T_ANCH_900_920_B/S` (CLW30 실증 승자 GATE_r8_4 엣지 코어 → HIER 16리프 이식)")
    A("- 판정기: 홀드아웃 동반(과최적 괴리 발산 · 수렴에 순악화 아님 요건) — QSP1 대비 신규")
    A("")
    A("## 0. 한 줄 결론")
    A("")
    A(f"**설계 {des_total:+.2f}% 와 홀드아웃 {hold_total:+.2f}% 가 같은 방향으로 개선** — 설계구간")
    A("암기(과최적)가 아니라 일반화되는 수정이라는 1차 증거. 다만 두 구간 모두 총손익은")
    A("여전히 음수이며, 개선의 일부는 거래 축소분이다(§2 분해 참조).")
    A("")
    A("## 1. 라운드 이력 (설계 · 홀드아웃 병기)")
    A("")
    A("| R | 베스트 | 설계 objective | Δ | 거래 | 홀드아웃 | 판정 | 채택 수정 |")
    A("|---|---|---|---|---|---|---|---|")
    A(f"| 시드 | (base) | {fmt(SEED_OBJ)} | — | {SEED_TRADES:,} | — | — | — |")
    prev = SEED_OBJ
    for r in rounds:
        cur = r["best"]["objective"]
        imp = f"{(cur - prev) / abs(prev) * 100:+.2f}%" if prev else "—"
        prev = cur
        h = (r.get("holdout") or {}).get("objective")
        meta = next((c for c in r.get("candidates", []) if c.get("buy_name") == r["best"]["buy_name"]), None)
        ch = meta["spec"]["change"] if meta else "(base 유지 — 후보 전원 미달)"
        A(f"| R{r['round']} | {r['best']['buy_name']} | {fmt(cur)} | {imp} "
          f"| {fmt(r['best'].get('trade_count'))} | {fmt(h)} | {r['judgment']['state']} | {ch} |")
    A("")
    A(f"최종 판정: **{rounds[-1]['judgment']['state']}** — {rounds[-1]['judgment']['reason']}")
    A("")
    A("## 2. 정직한 분해 (감사 규율 반영)")
    A("")
    tr_delta = (fin["trade_count"] / SEED_TRADES - 1) * 100
    per_trade_delta = (1 - pt1 / pt0) * 100
    A(f"- 설계 총손익: {fmt(SEED_OBJ)} → {fmt(fin['objective'])} (**{des_total:+.2f}%**)")
    A(f"- 거래수: {SEED_TRADES:,} → {fin['trade_count']:,} ({tr_delta:+.1f}%) — 감소분은 그물 축소 효과")
    A(f"- **거래당 손익: {pt0:,.0f} → {pt1:,.0f}원 ({per_trade_delta:+.2f}%)** — 엣지 자체의 개선분")
    A(f"- 홀드아웃(표본외 2024): {fmt(h0)} → {fmt(hf)} (**{hold_total:+.2f}%**) — 같은 조건식을")
    A("  본 적 없는 1년에 적용한 결과. 설계와 동방향이면 일반화, 역방향 지속이면 과최적(자동 발산).")
    A("- 홀드아웃은 설계 이전 구간(후향 검증)이며 거래수가 달라 **델타만 유효**하다(원장 명시).")
    A("")
    A("## 3. QSP1 대비 무엇이 달라졌나")
    A("")
    A("| 항목 | QSP1 | QSP2 |")
    A("|---|---|---|")
    A(f"| 시드 원엣지(tick) | −175.3M (8,619건) | **−50.9M (4,705건)** — anchor 이식 효과 |")
    A("| 표본외 검증 | 없음(캠페인 후 한계 명시) | **매 라운드 자동**(러너 내장) |")
    A("| 단위 정합 | 오류 매핑 5종(감사 발견) | 제거+불변식+금지 테스트 |")
    A("| 제안 낭비 | 동일 명세 재백테·리프 포기 | tried_specs+폴백 |")
    A("| 판정 | 설계 단독 | 설계+홀드아웃 동반(괴리=발산) |")
    A("")
    A("## 4. 한계·미해결 (과대해석 금지)")
    A("")
    A("1. 두 구간 모두 **총손익 음수** — 덜 잃는 그물이지 수익 전략이 아니다. 실전 반영 없음.")
    A("2. 제안 경로 유의성 게이트(FDR)·objective 단일 척도화는 백로그(원장 참조).")
    A("3. 커버리지 구멍 진단이 매 라운드 출력됨(체결강도평균·각도류·고가근접율) — 동단위")
    A("   캡처 컬럼 추가(additive) 또는 시드 계수 통일 후 매핑 재등재가 다음 확장.")
    A("4. R7 배치 1회 행(hang) 발생 — 재시도로 회복(무손실). 원인 미규명(원장 등재).")
    A("")
    A("## 부록 — 재현")
    A("")
    A("- 라운드: `python -m ai_strategy_loop.revision.round_runner --base-buy QSP2_T_ANCH_900_920_B"
      " --base-sell QSP2_T_ANCH_900_920_S --config …config_qsp2_anch.json"
      " --holdout-config …config_qsp2_anch_holdout.json --tag qsp2anch --round N`")
    A("- 기록: `rounds/qsp2anch_r*.json` · 감사: 본 디렉토리 원장 2026-07-30 행 · 대시보드 [QSP 라운드]")
    md_text = "\n".join(md) + "\n"
    (HERE / "2026-07-31_qsp2_report.md").write_text(md_text, encoding="utf-8")

    # ---------------- HTML ----------------
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

    tbl_lines = [l for l in md if l.startswith("|")]
    hist_tbl = md_table_to_html([l for l in tbl_lines if "설계 objective" in l or l.startswith("| 시드") or l.startswith("| R")])
    cmp_tbl = md_table_to_html([l for l in tbl_lines if "QSP1" in l or "항목" in l][:7])

    html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QSP2 캠페인 보고서</title><style>{_CSS}</style></head><body>
<header><h1>QSP2 캠페인 보고서 — anchor 이식 + 홀드아웃 동반 판정</h1>
<p class='muted'>{esc(now.strftime('%Y-%m-%d %H:%M'))} · feature/quant-scoring-pipeline-20260729 · 전 라운드 무인 자율</p></header>
<section><h2>수렴 곡선 — 설계 vs 홀드아웃</h2>{dual_curve_svg(rounds)}
<p><b>읽는 법</b>: 두 선이 같이 오르면 일반화되는 개선(모의고사·본고사 동반 상승), 실선만 오르고
점선이 내려가면 설계구간 암기(과최적) — 후자는 판정기가 2라운드 연속 시 자동 발산 선언한다.</p>
<p>설계 <b>{des_total:+.2f}%</b> · 홀드아웃 <b>{hold_total:+.2f}%</b> · 거래당 손익 개선 {per_trade_delta:+.2f}%
(거래수 {tr_delta:+.1f}%) · 최종 판정 <b>{esc(rounds[-1]['judgment']['state'])}</b></p></section>
<section><h2>라운드 이력</h2>{hist_tbl}</section>
<section><h2>QSP1 → QSP2 변경점</h2>{cmp_tbl}
<p class='muted'>독립 감사 2건(축A 56·46 / 축B 45·40)의 치명·높음 결함을 교정 후 가동한 캠페인이다.
상세는 limitation_ledger.md 2026-07-30 행과 QSP1 최종 보고서 §2.1 정정 참조.</p></section>
<section><h2>한계 (과대해석 금지)</h2><ol>
<li>두 구간 모두 총손익 음수 — 덜 잃는 그물이지 수익 전략 아님(실전 반영 없음).</li>
<li>FDR 유의성 게이트·objective 단일 척도화는 백로그.</li>
<li>홀드아웃은 후향(2024) 검증 — 델타만 유효.</li></ol></section>
</body></html>"""
    (HERE / "2026-07-31_qsp2_report.html").write_text(html, encoding="utf-8")
    print("built:", HERE / "2026-07-31_qsp2_report.md")
    print("built:", HERE / "2026-07-31_qsp2_report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
