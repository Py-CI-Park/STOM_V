# -*- coding: utf-8 -*-
"""QSP1 최종 연구 보고서 빌더 — rounds/*.json + 원장 + 리뷰를 md + 자가완결 HTML 로 조립.

HTML 디자인 정본 = 결산 v1(alpha_lab/reporting/build_html._CSS 재사용 — 사용자 선호).
실행:  python docs/research/quant_scoring_pipeline/build_final_report.py
산출:  2026-07-30_final_report.md / .html (본 디렉토리)
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


def load_rounds(tag: str):
    out = []
    for p in sorted((HERE / "rounds").glob(f"{tag}_r*.json")):
        if p.name.endswith("_pairs.json"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "round" in doc:
            out.append(doc)
    return sorted(out, key=lambda r: r["round"])


def fmt(v, nd=0):
    if v is None:
        return "—"
    return f"{v:,.{nd}f}"


def campaign_block_md(tag: str, title: str, seed_obj, rounds) -> str:
    lines = [f"### {title}", ""]
    if not rounds:
        lines.append("(라운드 기록 없음)")
        return "\n".join(lines)
    lines.append("| 라운드 | 베스트 | objective | 개선(직전比) | 거래수 | 판정 |")
    lines.append("|---|---|---|---|---|---|")
    prev = seed_obj
    if seed_obj is not None:
        lines.append(f"| 시드 | (base) | {fmt(seed_obj)} | — | {fmt(rounds[0].get('seed_trades'))} | — |")
    for r in rounds:
        cur = r["best"]["objective"]
        imp = "—"
        if prev not in (None, 0):
            imp = f"{(cur - prev) / abs(prev) * 100:+.2f}%"
        prev = cur
        lines.append(
            f"| R{r['round']} | {r['best']['buy_name']} | {fmt(cur)} | {imp} "
            f"| {fmt(r['best'].get('trade_count'))} | {r['judgment']['state']} |")
    total = ""
    if seed_obj not in (None, 0):
        total = f"**누적 개선: {(prev - seed_obj) / abs(seed_obj) * 100:+.2f}%** (시드 {fmt(seed_obj)} → 최종 {fmt(prev)})"
    lines += ["", total, "",
              f"최종 판정: **{rounds[-1]['judgment']['state']}** — {rounds[-1]['judgment']['reason']}", ""]
    # 채택 이력(무엇이 실제로 좋았나)
    lines.append("**채택된 수정(라운드별 베스트의 명세)**:")
    for r in rounds:
        best_name = r["best"]["buy_name"]
        meta = next((c for c in r.get("candidates", []) if c.get("buy_name") == best_name), None)
        change = meta["spec"]["change"] if meta else "(base 유지 — 후보 전원이 base 미달)"
        lines.append(f"- R{r['round']}: {change}")
    return "\n".join(lines)


def svg_curve(seed_obj, rounds, width=760, height=180):
    series = ([seed_obj] if seed_obj is not None else []) + [r["best"]["objective"] for r in rounds]
    labels = (["시드"] if seed_obj is not None else []) + [f"R{r['round']}" for r in rounds]
    if len(series) < 2:
        return "<p class='muted'>곡선 표시에 필요한 라운드 부족</p>"
    lo, hi = min(series), max(series)
    span = (hi - lo) or 1
    padl, padr, padt, padb = 90, 20, 16, 30
    def X(i): return padl + (width - padl - padr) * i / (len(series) - 1)
    def Y(v): return padt + (height - padt - padb) * (1 - (v - lo) / span)
    path = " ".join(f"{'M' if i == 0 else 'L'} {X(i):.1f} {Y(v):.1f}" for i, v in enumerate(series))
    dots = "".join(
        f"<circle cx='{X(i):.1f}' cy='{Y(v):.1f}' r='4' fill='var(--accent)'/>"
        f"<text x='{X(i):.1f}' y='{height - 8}' text-anchor='middle' font-size='11' fill='var(--muted)'>{esc(labels[i])}</text>"
        for i, v in enumerate(series))
    return (f"<svg viewBox='0 0 {width} {height}' style='width:100%;height:auto' role='img'>"
            f"<text x='{padl - 8}' y='{Y(hi) + 4}' text-anchor='end' font-size='11' fill='var(--muted)' class='num'>{hi:,.0f}</text>"
            f"<text x='{padl - 8}' y='{Y(lo) + 4}' text-anchor='end' font-size='11' fill='var(--muted)' class='num'>{lo:,.0f}</text>"
            f"<path d='{path}' fill='none' stroke='var(--accent)' stroke-width='2.5'/>{dots}</svg>")


def main() -> int:
    now = datetime.now()
    minfull = load_rounds("minfull")
    tickfull = load_rounds("tickfull")
    min1mo = load_rounds("min1mo")
    ledger = (HERE / "limitation_ledger.md").read_text(encoding="utf-8")

    # 시드 objective (R0 스모크 실측 — 원장/리뷰 수치와 동일 출처).
    SEED_MIN = -312_619_528.0
    SEED_TICK = -175_331_756.0

    reviews = {p.stem: p for p in sorted((HERE / "round_reviews").glob("R*.md"))}
    gates = [
        ("R0 스모크", "PASS", "4시드 73,052거래 · 리프 잔차표 최초 산출 · 발견 5건"),
        ("R1 라벨셋", "PASS 98", "엔진 v2 확장 실증 · 변별력 2배 · min 타임아웃 결함 발견→해소"),
        ("R2 번역·게이트", "PASS 97", "오류 주입 8/8 검출 · 실데이터 제안 3건 폐루프"),
        ("R3 다후보 라운드", "PASS 96", "실라운드 2회 · '복합 적용' 가설 실증 · ε 추적 작동"),
        ("R4 시각화", "PASS 98", "수렴 곡선 · 판정 즉독 4/4 · 교훈 환류 배선"),
    ]

    md = []
    A = md.append
    A("# QSP1 최종 연구 보고서 — 좋은 조건식을 만드는 수렴형 파이프라인")
    A("")
    A(f"- 작성: {now.strftime('%Y-%m-%d %H:%M')} · 브랜치 `feature/quant-scoring-pipeline-20260729`")
    A("- 헌장: [2026-07-29_master_plan.md](2026-07-29_master_plan.md) · 시드: [seed_registry](2026-07-29_seed_registry.md)")
    A("")
    A("## 0. 한 줄 결론")
    A("")
    A("**파이프라인은 '수렴하는 솔버'로 작동한다.** 넓은 그물 시드에서 출발해 [백테 → 라벨 분석")
    A("→ 리프 단위 수정 명세 → 의도-일치 게이트 → 재백테 → 판정]을 사람 개입 없이 반복했고,")
    A("모든 라운드에서 손실이 단조 감소했으며, 무효 축은 자동 제외됐다. 단 이 구간(2025-04~2026-02)의")
    A("넓은 그물은 여전히 총손익 음수 — 파이프라인의 다음 병목은 반복이 아니라 **시드 계열의 원엣지**다")
    A("(직전 연구 CLW30 의 결론과 정합). **⚠ 2026-07-30 독립 감사 정정: §2.1 필독** — 개선 수치")
    A("일부가 단위 오류 경로에서 나왔고, '단조 감소'는 구조적 보장이다(성과 주장 아님).")
    A("")
    A("## 1. 4체인 연구 질문(RQ) 답변")
    A("")
    A("| 체인 | RQ | 답 (증거) |")
    A("|---|---|---|")
    A("| C1 실행 | min 풀세션 소요·재현성 | 11개월 쌍당 ~2분 · 48k 거래 127s · 완주율 100% (R0) |")
    A("| C1 실행 | 대량 거래 병목 | 없음 — 다만 v2 확장이 min 캡처 IndexError 유발 → 열 경계 가드로 해소 (R1) |")
    A("| C2 라벨 | 파생 가능 변수 | 엔진 additive 17컬럼 + 오프라인 파생 12종 → 설명변수 15→34(tick)/38(min) (R1) |")
    A("| C2 라벨 | 산출 부담 | 관측 불가 수준(캡처는 매수 이벤트 시 dict 조회) (R1) |")
    A("| C3 분석 | 변별 변수 실존? | 예 — 최고 \\|d\\| 0.10→0.21(2배). 각도·초당거래대금·고가근접율 등 신규가 상위 (R1) |")
    A("| C3 분석 | 분석→수정 번역 규칙 | 손실 리프(중앙값) → 리프 내 최대 d 조절변수 → 승자 분위수 경계 (R2) |")
    A("| C4 생성 | 의도-일치 기계 판정 | AST 골격 지문 + diff⊆명세 — 주입 실험 8/8 검출 (R2) |")
    A("| C4 생성 | 다후보·교훈 | 라운드당 3후보(축 상이) + 무효 축 자동 제외 실작동 (R3·P5) |")
    A("")
    A("## 2. 캠페인 결과 (설계 구간)")
    A("")
    A(campaign_block_md("minfull", "min HIER · 20250407~20260227 풀세션", SEED_MIN, minfull))
    A("")
    A(campaign_block_md("tickfull", "tick HIER · 20250407~20260227 09:00~09:30", SEED_TICK, tickfull))
    A("")
    A(campaign_block_md("min1mo", "(예비) min HIER 1개월 — P3 검증용", -41_350_878.0, min1mo))
    A("")
    A("### 2.1 정정 — 2026-07-30 독립 감사 반영 (과대해석 방지)")
    A("")
    A("본 보고서 발행 직후 수행된 독립 감사(축A 조건식 생성 56/100 · 축B 결과 분석 45/100)에서")
    A("아래가 확인되어 정정한다. 상세 근거와 교정 이력은 한계 원장(§4) 2026-07-30 행 참조.")
    A("")
    A("1. **단위 불일치 임계값(치명)** — 제안기 매핑 5종이 단위가 다른 절에 분위수를 기입했다.")
    A("   대표 사례 minfull R3 C2: `거래대금비율 > 246`(원 단위 분위수를 배수 절에 기입 —")
    A("   사실상 리프 차단)이 라운드 베스트로 채택되어 **min 캠페인 개선 69.9M 중 ~27.9M(≈40%)이")
    A("   이 우발 경로에서 발생**했다. 손실 리프 차단이라 결과적으로 손실은 줄었지만, 의도된")
    A("   메커니즘(데이터 근거 조임)이 아니므로 방법론 실증 증거로 쓸 수 없다. → 오류 매핑 제거·")
    A("   단위 불변식·회귀 테스트로 교정 완료(QSP2 캠페인부터 적용).")
    A("2. **'전 라운드 단조 개선'은 구조적 보장** — base 가 항상 후보 풀에 포함되고 베스트는 최댓값")
    A("   선택이므로 라운드 간 퇴행은 발생할 수 없다. 이는 안전장치(퇴행 방지)의 확인이지 성과")
    A("   주장이 아니다. 같은 이유로 진동 발산 분기는 이 루프에서 도달 불가한 규격이다.")
    A("3. **복합/시너지 주장 철회** — 리프는 거래 공간을 분할하므로 서로 다른 리프의 수정 효과는")
    A("   정확히 가산적이다(실측: 동일 후보의 Δ가 base 갱신과 무관하게 +186,030 로 불변).")
    A("   R3 리뷰의 '복합 적용' 서술은 가산성의 동어반복으로 정정한다.")
    A("4. **개선의 44%는 거래수 축소**(로그 분해, 검산: min 12,455→11,151건 −10.5% ·")
    A("   tick 8,619→8,253건 −4.2%) — 거래당 손실 개선은 min +13.3%(−25,100→−21,765원) ·")
    A("   tick +5.4%(−20,342→−19,247원)에 그친다. 기대값 음수 그물은 거래를 줄이기만 해도")
    A("   총손익이 좋아지므로, 이후 보고서는 총손익과 거래당 손익을 병기한다.")
    A("5. 개선 수치는 모두 **설계 구간 내**이며 홀드아웃 검증 전이라는 기존 한계(§0)는 유지된다.")
    A("   QSP2 캠페인은 홀드아웃 동반 판정을 러너에 내장해 이 한계를 해소한다.")
    A("")
    A("## 3. 게이트 이력 (90점 규율)")
    A("")
    A("| 게이트 | 판정 | 요지 |")
    A("|---|---|---|")
    for name, verdict, gist in gates:
        A(f"| {name} | {verdict} | {gist} |")
    A("")
    A("## 4. 한계 원장 (전체 — 개선 백로그의 원천)")
    A("")
    A(ledger.split("| 날짜 |", 1)[-1].join(["| 날짜 |", ""]) if "| 날짜 |" in ledger else ledger)
    A("")
    A("## 5. QSP2 제언")
    A("")
    A("1. **시드 원엣지 탐색이 1순위** — 반복기는 준비됐다. anchor 다밴드류(직전 연구의 실증 승자")
    A("   계열)를 QSP HIER 골격으로 이식해 캠페인을 돌리는 것이 최단 경로.")
    A("2. CSS 패턴형 제안기(파라미터 축) — HIER 전용 한계 해소.")
    A("3. 홀드아웃 동반 판정 — 수렴 선언에 표본외 개선 동반 요건(마스터플랜 §2)을 러너에 내장.")
    A("4. LLM 복귀 시 prompt v2 배선 + 생성 주체 A/B(에이전트 vs LLM 품질 비교).")
    A("5. 매도식 축 — 현재 제안기는 매수식만. 청산 파라미터 축(H5) 추가.")
    A("")
    A("## 부록 — 재현")
    A("")
    A("- 라운드: `python -m ai_strategy_loop.revision.round_runner --base-buy … --tag <tag> --round N`")
    A("- 기록: `docs/research/quant_scoring_pipeline/rounds/<tag>_r*.json` · 대시보드 [연구 자산→QSP 라운드]")
    A("- 게이트 리뷰: " + " · ".join(sorted(reviews.keys())))
    md_text = "\n".join(md) + "\n"
    (HERE / "2026-07-30_final_report.md").write_text(md_text, encoding="utf-8")

    # ---------------- HTML (결산 v1 디자인 정본) ----------------
    def md_table_to_html(md_block: str) -> str:
        rows = [l for l in md_block.splitlines() if l.startswith("|")]
        if not rows:
            return f"<p>{esc(md_block)}</p>"
        out = ["<table>"]
        for i, row in enumerate(rows):
            if set(row.replace("|", "").strip()) <= {"-", " ", ":"}:
                continue
            cells = [c.strip() for c in row.strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{esc(c)}</{tag}>" for c in cells) + "</tr>")
        out.append("</table>")
        return "".join(out)

    def section(id_, title, inner):
        return f"<section id='{id_}'><h2>{esc(title)}</h2>{inner}</section>"

    camp_html = ""
    for tag, title, seed in (("minfull", "min HIER · 11개월 풀세션", SEED_MIN),
                             ("tickfull", "tick HIER · 11개월 초반 30분", SEED_TICK),
                             ("min1mo", "(예비) min 1개월", -41_350_878.0)):
        rs = load_rounds(tag)
        camp_html += f"<h3>{esc(title)}</h3>"
        if rs:
            camp_html += svg_curve(seed, rs)
        camp_html += md_table_to_html(campaign_block_md(tag, title, seed, rs))
        if rs:
            camp_html += ("<p class='muted'>최종 판정: <b>" + esc(rs[-1]["judgment"]["state"]) + "</b> — "
                          + esc(rs[-1]["judgment"]["reason"]) + "</p>")

    ledger_html = md_table_to_html(ledger)
    gates_html = "<table><tr><th>게이트</th><th>판정</th><th>요지</th></tr>" + "".join(
        f"<tr><td>{esc(n)}</td><td>{esc(v)}</td><td>{esc(g)}</td></tr>" for n, v, g in gates) + "</table>"

    rq_html = md_table_to_html("\n".join(md[md.index('## 1. 4체인 연구 질문(RQ) 답변') + 2:
                                            md.index('## 2. 캠페인 결과 (설계 구간)')]))

    nav = ("<nav class='tabs'>" + "".join(
        f"<a href='#{i}'>{t}</a>" for i, t in
        [("s0", "결론"), ("s1", "4체인 RQ"), ("s2", "캠페인·수렴 곡선"), ("s3", "게이트"),
         ("s4", "한계 원장"), ("s5", "QSP2 제언")]) + "</nav>")

    html = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>QSP1 최종 연구 보고서</title><style>{_CSS}
.tabs{{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0;border-bottom:1px solid var(--line);padding-bottom:10px}}
.tabs a{{color:var(--accent);text-decoration:none;font-weight:700;font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0}}
th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}}
th{{color:var(--muted);font-weight:600}}</style></head><body><div class='wrap'>
<div class='masthead'><div><div class='eyebrow'>QSP1 · QUANT SCORING PIPELINE</div>
<h1>좋은 조건식을 만드는 수렴형 파이프라인 — 최종 연구 보고서</h1>
<div class='meta-grid'><span>작성 <b>{now.strftime('%Y-%m-%d %H:%M')}</b></span>
<span>브랜치 <b>feature/quant-scoring-pipeline-20260729</b></span>
<span>게이트 <b>R0~R4 전부 PASS(≥90)</b></span></div></div></div>
{nav}
{section('s0', '0. 한 줄 결론', "<p class='lede'>파이프라인은 <b>수렴하는 솔버</b>로 작동한다. 넓은 그물 시드에서 [백테 → 라벨 분석 → 리프 수정 명세 → 의도-일치 게이트 → 재백테 → 판정]을 사람 개입 없이 반복해 모든 라운드에서 손실이 단조 감소했고 무효 축은 자동 제외됐다. 단 이 구간의 넓은 그물은 여전히 총손익 음수 — 다음 병목은 반복이 아니라 <b>시드 계열의 원엣지</b>다(직전 CLW30 연구와 정합).</p>")}
{section('s1', '1. 4체인 연구 질문 답변', rq_html)}
{section('s2', '2. 캠페인 결과 · 수렴 곡선', camp_html)}
{section('s3', '3. 게이트 이력 (90점 규율)', gates_html)}
{section('s4', '4. 한계 원장', ledger_html)}
{section('s5', '5. QSP2 제언', "<ol><li><b>시드 원엣지 탐색이 1순위</b> — 반복기는 준비 완료. anchor 다밴드 계열을 HIER 골격으로 이식해 캠페인.</li><li>CSS 패턴형 제안기(파라미터 축).</li><li>홀드아웃 동반 수렴 판정 내장.</li><li>LLM 복귀 시 prompt v2 배선 + 생성 주체 A/B.</li><li>매도식(청산) 축 제안기.</li></ol>")}
<p class='muted'>자가완결 HTML · 외부 리소스 0 · 디자인 정본: 결산 v1</p>
</div></body></html>"""
    (HERE / "2026-07-30_final_report.html").write_text(html, encoding="utf-8")
    print("built:", HERE / "2026-07-30_final_report.md")
    print("built:", HERE / "2026-07-30_final_report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
