"""조건식 발굴 프로세스 시각화 — 인터랙티브 self-contained HTML 생성기.

실제 산출물(p5 프롬프트·챔피언 조건식·백테 결과·환류 피드백·게이트 판정·라이브 상태)을
읽어 하나의 HTML로 임베드한다. 재실행하면 최신 데이터로 갱신. 엔진 무수정(읽기 전용).

사용:  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.build_process_flow_html
출력:  docs/process_flow.html  (브라우저로 열기)
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVID = REPO / ".omo/evidence/tmap-walkforward"
TD = REPO / "ai_strategy_loop/tmap/templates"
OUT = REPO / "docs/process_flow.html"


def _esc(s: str) -> str:
    return html.escape(s or "")


def _read(p: Path, default: str = "(없음)") -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return default


def prompt_excerpt() -> str:
    raw = _read(REPO / "ai_strategy_loop/brain/prompts/p5_template_hypothesis.md")
    m = re.search(r"```\n(.*?)```", raw, re.DOTALL)
    body = m.group(1).strip() if m else raw
    return body[:2400]


def champion_condition() -> str:
    try:
        d = json.loads((TD / "seed_902905_t2late.json").read_text(encoding="utf-8"))
        return d.get("buy_code", "(없음)")[:2600]
    except Exception:
        return "(없음)"


def sample_generated() -> str:
    import glob
    import os
    fs = sorted(glob.glob(str(TD / "llmgen_*theta*discrete*.json")), key=os.path.getmtime, reverse=True)
    if not fs:
        fs = sorted(glob.glob(str(TD / "llmgen_*.json")), key=os.path.getmtime, reverse=True)
    if not fs:
        return "(없음)", "—"
    d = json.loads(Path(fs[0]).read_text(encoding="utf-8"))
    return d.get("buy_code", "")[:1800], d.get("name", "?")


def feedback_now() -> str:
    try:
        import sys
        sys.path.insert(0, str(REPO))
        import ai_strategy_loop.bootstrap  # noqa
        from ai_strategy_loop.scripts.tmap_multiband_discovery import build_feedback
        j = EVID / "full_stateful_n40.jsonl"
        recs = [json.loads(l) for l in j.read_text(encoding="utf-8").splitlines() if l.strip()] if j.is_file() else []
        return build_feedback(recs) or "(ledger 비어있음)"
    except Exception as e:
        return f"(피드백 생성 오류: {e})"


def run_status() -> dict:
    j = EVID / "full_stateful_n40.jsonl"
    recs = [json.loads(l) for l in j.read_text(encoding="utf-8").splitlines() if l.strip()] if j.is_file() else []
    verd = Counter((r.get("eval") or {}).get("verdict", "gen-fail" if not r.get("template") else "?") for r in recs)
    surv = sum(verd.get(k, 0) for k in ("train-pass", "train-only", "★PROMISING"))
    spass = sum(verd.get(k, 0) for k in ("smoke-pass", "train-pass", "train-only", "★PROMISING"))
    done = (EVID / "full_stateful_n40_summary.json").is_file()
    return {"iter": len(recs), "verd": dict(verd), "surv": surv, "spass": spass, "done": done}


def var_to_profit_rows() -> str:
    """loop_runs.db에서 '변수값 → 수익/거래수' 실제 추적 예시(한 스윕)."""
    try:
        c = sqlite3.connect(str(REPO / "ai_strategy_loop/state/loop_runs.db"))
        cur = c.cursor()
        cur.execute("SELECT run_id FROM generations WHERE run_id LIKE 'mbdisc_%_q1' AND strategy_gist LIKE 'TMAP %=%' "
                    "GROUP BY run_id ORDER BY rowid DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return ""
        rid = row[0]
        cur.execute("SELECT strategy_gist, profit, trade_count, mdd FROM generations WHERE run_id=? "
                    "AND strategy_gist LIKE 'TMAP %=%' ORDER BY profit DESC LIMIT 8", (rid,))
        out = []
        for g, p, t, m in cur.fetchall():
            out.append(f"<tr><td>{_esc(str(g).replace('TMAP ',''))}</td><td>{p:,.0f}</td><td>{t}</td><td>{m}</td></tr>")
        c.close()
        return "".join(out)
    except Exception:
        return ""


def _fmt_won(v) -> str:
    try:
        return f"{float(v):,.0f}"
    except Exception:  # noqa: BLE001
        return "—"


def overnight_tree() -> str:
    """밤샘 앵커변이 발굴(ovn_anchor.jsonl)을 hill-climb 트리 HTML로 렌더(없으면 안내)."""
    p = EVID / "ovn_anchor.jsonl"
    if not p.is_file():
        return '<div class="note">아직 밤샘 발굴 데이터가 없습니다(런 시작 직후).</div>'
    rounds: dict = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        ev = o.get("event")
        if ev == "cand":
            rounds.setdefault(o.get("round"), {"cands": []})["cands"].append(o)
        elif ev == "round_done":
            rounds.setdefault(o.get("round"), {"cands": []})["done"] = o
    keys = sorted(k for k in rounds if isinstance(k, int))
    if not keys:
        return '<div class="note">발굴 진행 중 — 첫 라운드 백테 중(결과 집계 전, ~40분).</div>'
    rows = []
    for r in keys:
        cands = rounds[r].get("cands", [])
        npass = sum(1 for c in cands if c.get("gate"))
        passers = [c for c in cands if c.get("gate") and float(c.get("profit") or 0) > 0]
        best = (max(passers, key=lambda c: float(c.get("profit") or 0)) if passers
                else (max(cands, key=lambda c: float(c.get("profit") or -1e18)) if cands else None))
        dots = "".join(
            f'<i class="dot {"pass" if c.get("gate") else "fail"}" '
            f'title="{_esc(str(c.get("label")))} · profit {_fmt_won(c.get("profit"))} · mdd {c.get("mdd")}"></i>'
            for c in cands)
        if best:
            bmark = "✅" if best.get("gate") else "·"
            bsum = (f'best {bmark} <b>{_esc(str(best.get("label")))}</b> '
                    f'+{_fmt_won(best.get("profit"))} (mdd {best.get("mdd")})')
        else:
            bsum = "집계 중"
        rows.append(
            f'<div class="trow"><span class="rbadge">R{r}</span>'
            f'<span class="dots">{dots}</span>'
            f'<span class="bsum">통과 <b>{npass}</b>/{len(cands)} → {bsum}</span></div>')
    return '<div class="tree">' + "".join(rows) + "</div>"


def main() -> int:
    st = run_status()
    badge = (f'<span class="b ok">iter {st["iter"]}/40</span>'
             f'<span class="b {"good" if st["surv"] else "muted"}">전체기간 생존 {st["surv"]}</span>'
             f'<span class="b">smoke-pass {st["spass"]}</span>'
             f'<span class="b {"done" if st["done"] else "run"}">{"완료" if st["done"] else "진행중"}</span>')
    verd_rows = "".join(f"<tr><td>{_esc(k)}</td><td>{v}</td></tr>" for k, v in sorted(st["verd"].items()))
    spname_buy, spname = sample_generated()

    html_doc = _TEMPLATE
    repl = {
        "%%GEN_TIME%%": time.strftime("%Y-%m-%d %H:%M:%S"),
        "%%BADGES%%": badge,
        "%%VERD_ROWS%%": verd_rows or "<tr><td>—</td><td>0</td></tr>",
        "%%PROMPT%%": _esc(prompt_excerpt()),
        "%%CHAMPION%%": _esc(champion_condition()),
        "%%SAMPLE_NAME%%": _esc(spname),
        "%%SAMPLE%%": _esc(spname_buy),
        "%%FEEDBACK%%": _esc(feedback_now()),
        "%%VAR_ROWS%%": var_to_profit_rows() or "<tr><td>(데이터 없음)</td><td>—</td><td>—</td><td>—</td></tr>",
        "%%TREE%%": overnight_tree(),
    }
    for k, v in repl.items():
        html_doc = html_doc.replace(k, v)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"[OK] {OUT}  ({len(html_doc):,} bytes)  iter={st['iter']}/40 생존={st['surv']}")
    return 0


_TEMPLATE = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STOM 조건식 발굴 프로세스 — 쉽게 보는 조건식 발굴 루프</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--bd:#30363d;--fg:#e6edf3;--mut:#8b949e;--acc:#58a6ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--mag:#bc8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:'Segoe UI',Malgun Gothic,sans-serif;line-height:1.5}
header{position:sticky;top:0;background:#0d1117ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--bd);padding:14px 22px;z-index:10}
h1{margin:0;font-size:20px}h2{font-size:17px;border-left:4px solid var(--acc);padding-left:10px;margin:30px 0 12px}
.sub{color:var(--mut);font-size:13px;margin-top:4px}
.wrap{max-width:1100px;margin:0 auto;padding:0 22px 60px}
.b{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px;background:#21262d;border:1px solid var(--bd)}
.b.ok{border-color:var(--acc);color:var(--acc)}.b.good{border-color:var(--ok);color:var(--ok)}.b.muted{color:var(--mut)}
.b.run{border-color:var(--warn);color:var(--warn)}.b.done{border-color:var(--ok);color:var(--ok)}
.goal{background:linear-gradient(90deg,#1f2a44,#161b22);border:1px solid var(--acc);border-radius:10px;padding:14px 18px;margin:18px 0}
.goal b{color:var(--acc)}
.flow{display:flex;flex-direction:column;gap:0;margin:10px 0}
.node{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px 16px;position:relative}
.node .tag{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px}
.node .ttl{font-weight:600;font-size:15px;margin:2px 0}
.node .desc{font-size:13px;color:var(--mut)}
.node.gen{border-left:4px solid var(--mag)}.node.bt{border-left:4px solid var(--acc)}
.node.gate{border-left:4px solid var(--ok)}.node.fb{border-left:4px solid var(--warn)}
.arrow{text-align:center;color:var(--mut);font-size:20px;line-height:1;padding:5px 0}
.loop{text-align:center;color:var(--warn);font-size:13px;border:1px dashed var(--warn);border-radius:8px;padding:8px;margin:8px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
details{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:10px 14px}
details summary{cursor:pointer;font-weight:600}details[open]{border-color:var(--acc)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
.tab{padding:7px 14px;background:#21262d;border:1px solid var(--bd);border-radius:8px 8px 0 0;cursor:pointer;font-size:13px}
.tab.active{background:var(--card);border-bottom-color:var(--card);color:var(--acc)}
.panel{display:none;background:var(--card);border:1px solid var(--bd);border-radius:0 8px 8px 8px;padding:14px}
.panel.active{display:block}
pre{background:#010409;border:1px solid var(--bd);border-radius:6px;padding:12px;overflow:auto;font-size:12px;color:#c9d1d9;max-height:420px}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{border:1px solid var(--bd);padding:6px 9px;text-align:left}
th{background:#21262d}.mono{font-family:Consolas,monospace}
.k{color:var(--mag)}.note{color:var(--mut);font-size:12px;margin-top:6px}
.verdict{background:linear-gradient(90deg,#10331c,#161b22);border:1px solid var(--ok);border-radius:10px;padding:14px 18px;margin:14px 0}
.verdict b{color:var(--ok)}
.stage{background:var(--card);border:1px solid var(--bd);border-radius:10px;overflow:hidden;margin:10px 0}
.stage .h{display:flex;align-items:center;gap:10px;padding:9px 14px;font-weight:600;border-bottom:1px solid var(--bd);font-size:14px}
.stage .num{display:inline-flex;width:24px;height:24px;border-radius:50%;align-items:center;justify-content:center;font-size:12px;background:#21262d;border:1px solid var(--bd);flex:0 0 auto}
.stage .h .tagm{margin-left:auto;font-size:11px;color:var(--mut);font-family:Consolas,monospace}
.stage .body{padding:10px 14px;font-size:13px;color:var(--fg)}
.stage .ex{font-family:Consolas,monospace;font-size:12px;color:#c9d1d9;background:#010409;border:1px solid var(--bd);border-radius:6px;padding:7px 10px;margin-top:8px;white-space:pre-wrap}
.stage.gen{border-left:4px solid var(--mag)}.stage.bt{border-left:4px solid var(--acc)}
.stage.gate{border-left:4px solid var(--ok)}.stage.fb{border-left:4px solid var(--warn)}
.hm td.pos{background:rgba(63,185,80,.18)}.hm td.neg{background:rgba(248,81,73,.16)}.hm td.s{font-weight:700}
.pass{color:var(--ok);font-weight:700}.fail{color:var(--bad);font-weight:700}
.v2 .node.an{border-left:4px solid var(--mag)}.v2 .node.dec{border-left:4px solid #d2a8ff}
.flow{position:relative}
.flowtok{position:absolute;left:3px;top:0;width:11px;height:11px;border-radius:50%;background:var(--acc);box-shadow:0 0 12px 4px var(--acc);animation:flowdown 7s cubic-bezier(.6,0,.4,1) infinite;z-index:5}
@keyframes flowdown{0%{top:0;opacity:0}6%{opacity:1}90%{opacity:1}100%{top:calc(100% - 11px);opacity:0}}
.flowcap{font-size:12px;color:var(--acc);margin:2px 0 6px;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
.tree{display:flex;flex-direction:column;gap:6px;margin:10px 0}
.trow{display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:7px 11px;font-size:12px;flex-wrap:wrap;animation:fadein .4s ease}
@keyframes fadein{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.rbadge{flex:0 0 auto;font-weight:700;color:var(--acc);font-family:Consolas,monospace}
.dots{display:flex;gap:3px;flex-wrap:wrap}
.dot{width:11px;height:11px;border-radius:3px;display:inline-block;cursor:help}
.dot.pass{background:var(--ok);box-shadow:0 0 4px var(--ok)}.dot.fail{background:#5a2a2a;border:1px solid #6e3030}
.bsum{margin-left:auto;color:var(--mut)}.bsum b{color:var(--ok)}
</style></head><body>
<header><h1>🔬 STOM 조건식 발굴 프로세스 — 쉽게 보는 조건식 발굴 루프</h1>
<div class="sub">생성일 %%GEN_TIME%% · %%BADGES%%</div></header>
<div class="wrap">

<div class="goal"><b>🎯 목표 &amp; 마인드셋</b> — 광산에서 <b>수익 나는 매수/매도 조건식(실매매용 per-stock if-Buy)</b>을 캐낸다.
<b>데이터에 알파는 실재</b>한다 — 검증 챔피언이 발굴 게이트로 +9.5~11M을 재현(§1.5). "데이터 천장"이 아니다.
병목은 <b>콜드 LLM 생성</b>이고, 다음은 검증 앵커를 변이하는 <b>v2 레짐인식 루프</b>(§1.6). 엔진/CLI 무수정.</div>

<h2>🪙 이게 무슨 연구인가요? (아주 쉬운 설명)</h2>
<div class="cards">
<div class="node gen"><div class="ttl">조건식 = 금광맥 ⛏️</div><div class="desc">"이런 종목을·이 시간에·이 신호가 뜨면 사라(팔아라)"는 <b>매수/매도 규칙</b>(코드). 우리가 캐려는 광석. 실매매 프로그램에 바로 넣는 산출물.</div></div>
<div class="node bt"><div class="ttl">백테스트 = 금 감정사 🔍</div><div class="desc">그 규칙을 <b>과거 데이터에 적용</b>해 "진짜 돈이 됐나" 계산. <b>가짜 금(과적합)</b>을 골라냄.</div></div>
<div class="node fb"><div class="ttl">이 시스템 = 자동 채굴기 🤖</div><div class="desc">AI가 규칙을 만들고 → 백테로 검증하고 → <b>실패에서 배워</b> 다음엔 더 잘 캐도록 *스스로 반복*.</div></div>
</div>
<div class="note" style="font-size:14px;line-height:1.7">
<b>한눈에 흐름</b> — ① AI가 규칙을 만든다 → ② 과거 2분기로 <b>빠르게</b> 본다 → ③ 통과하면 <b>3년 전체</b>로 본다 → ④ <b>다른 해(미래)</b>로도 본다 → ⑤ 가짜면 <b>검문소(게이트)</b>가 막는다 → ⑥ 실패를 <b>기억</b>해 다음엔 안 만든다 → <b>↻ 반복</b>.<br>
💡 <b>지금 상태(2026-06-16)</b>: P0~P5 폐루프 구현완료. 양성대조 진단으로 <b>알파 실재·게이트 정상·병목=콜드 생성</b> 확정(§1.5). 콜드 LLM 신규 발굴은 0이지만 검증 챔피언은 게이트 통과 → <b>다음 = 앵커 변이(v2)로 ①생성 단계 교체</b>. "없다"가 아니라 "콜드 생성으론 아직".</div>
<div class="note">🎨 <b>색상 범례</b>: <span style="color:var(--mag)">●보라=생성</span> · <span style="color:var(--acc)">●파랑=백테</span> · <span style="color:var(--ok)">●초록=게이트</span> · <span style="color:var(--warn)">●주황=환류</span></div>

<h2>1. 전체 파이프라인 (데이터마이닝 폐루프)</h2>
<div class="flowcap">🔵 조건식 한 개가 단계를 따라 흐르는 모습(애니메이션) — 탈락 시 그 단계서 멈춤</div>
<div class="flow">
<div class="flowtok"></div>
<div class="node gen"><div class="tag">① 생성 · gen_template_hypothesis.py</div><div class="ttl">AI가 다밴드 조건식 생성</div>
<div class="desc">시간대×시총 이산분기(시초/중반/후반) 조건식을 LLM이 생성. 직전 결과(회피/선호) 환류 + 검증 가드(밴드당≤10·비용·금지변수).</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">② 스모크 백테 · tmap_sweep.py (32엔진)</div><div class="ttl">2분기 동시 흑자 게이트</div>
<div class="desc">변수(θ)를 스윕하며 백테. q1∧q2 같은 좌표가 둘 다 흑자여야 통과(체리피킹 차단).</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">③ 전체기간 백테 · 3년 train</div><div class="ttl">일반화 검증 (과적합 차단)</div>
<div class="desc">2분기 통과분만 3년 전체기간 재백테. 여기서 음전(과적합)이면 탈락 = 착시 차단.</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">④ OOS · 2022·2026</div><div class="ttl">미래 재현성</div>
<div class="desc">전체기간 통과분만 다른 해(OOS)로 최종 검증. ★PROMISING = 전부 흑자(THETA급 바).</div></div>
<div class="arrow">↓</div>
<div class="node gate"><div class="tag">⑤ 게이트 · refine_gate.py (P0b)</div><div class="ttl">재백테 음전 REFUSE</div>
<div class="desc">in-sample 흑자라도 재백테 음전이면 기각. 검증됨: known-good +2.17M PASS · 사후포켓 −1.15M REFUSE.</div></div>
<div class="loop">↻ ⑥ 환류 (P2 build_feedback) — no-go=회피·과적합=회피·전체기간생존=선호 → <b>다음 생성(①)으로</b> · 무작위 추첨을 "학습하는 발굴"로</div>
</div>
<div class="note">정직지표 = OOS 통과 후보 수(현재 baseline 0). 점수가 아니라 *일반화 생존*만 합격.</div>

<h2>⚡ 1.5 최신 진단 — "천장이 아니라 생성기가 병목" (2026-06-16)</h2>
<div class="verdict"><b>✅ 양성대조 확정</b> — 검증된 챔피언 4종을 발굴 게이트(mdd&lt;20·daily≥0.05)로 그대로 재백테 → <b>4/4 전원 통과</b>.
즉 데이터에 알파는 <b>실재</b>하고(+9.5~11M 재현), 게이트도 <b>정상 교정</b>됨. ∴ 자동발굴 gate-pass=0은 천장·게이트가 아니라 <b>콜드 LLM 생성기가 약한 것</b>이다.</div>
<table><tr><th>챔피언</th><th>profit</th><th>MDD (&lt;20)</th><th>daily (≥0.05)</th><th>거래</th><th>판정</th></tr>
<tr><td>FROZEN_THETA</td><td>+10,965,479</td><td>10.04</td><td>0.40</td><td>272</td><td class="pass">✓ 통과</td></tr>
<tr><td>T2C1</td><td>+9,550,593</td><td>13.76</td><td>0.40</td><td>317</td><td class="pass">✓ 통과</td></tr>
<tr><td>T2C2</td><td>+9,642,207</td><td>13.89</td><td>0.40</td><td>322</td><td class="pass">✓ 통과</td></tr>
<tr><td>T2C3 (다밴드 챔피언)</td><td>+9,866,240</td><td>11.30</td><td>0.50</td><td>356</td><td class="pass">✓ 통과</td></tr></table>

<h2>📉 1.5b 경향성은 레짐(상황)마다 변한다 — 챔피언 거래 연도별</h2>
<table class="hm"><tr><th>변수</th><th>2023</th><th>2024</th><th>2025</th><th>해석</th></tr>
<tr><td>시가총액</td><td class="neg">−34%p</td><td class="neg s">−41%p</td><td class="neg">−25%p</td><td>작은 시총 유리 — 방향 유지·강도 변동</td></tr>
<tr><td>시간(시분초)</td><td class="neg">−16%p</td><td class="neg s">−44%p</td><td class="neg">−11%p</td><td>빨리 진입 유리 — 2024 압도→2025 거의 소멸</td></tr>
<tr><td>회전율</td><td>+3%p</td><td class="pos">+22%p</td><td class="pos s">+34%p</td><td>★2023 무의미 → 2025 최강 신호로 <b>부상</b></td></tr></table>
<div class="note">(격차 = 그 변수 상위25% 승률 − 하위25% 승률) → "빨리·작게가 이긴다"는 <b>항상 참이 아님</b>. 회전율처럼 <b>때에 따라 부상</b>하는 변수가 있어, 오늘의 top만 좇는 greedy는 놓친다. 그래서 v2는 <b>넓게·레짐별로</b> 본다.</div>

<h2>🔁 1.6 다음 방향 — v2 레짐 인식 폐루프 (콜드 생성 → 앵커 변이)</h2>
<div class="flow v2">
<div class="node an"><div class="tag">① 레짐별 분석</div><div class="ttl">변수 영향성을 레짐(연도·변동성·시총/시간)별로</div>
<div class="desc">feature_importance/히트맵/상관으로 변수별 영향·<b>안정성</b>·<b>부상/소멸</b>(회전율型) 탐지. 전역 1장이 아니라 레짐별.</div></div>
<div class="arrow">↓</div>
<div class="node dec"><div class="tag">② 타겟 결정 = 탐색 + 활용</div><div class="ttl">AI 질문 + 사람 사전지식</div>
<div class="desc"><b>활용</b>(영향 크고 안정적 변수→고원 중심) + <b>탐색</b>(예산 일부를 약하지만 부상 가능·더 넓은 범위·미검증 상호작용·레짐별 경향에 의무 배정).</div></div>
<div class="arrow">↓</div>
<div class="node gen"><div class="tag">③ 다축 변이 (mutator + grid)</div><div class="ttl">시간·시총·익절·트레일… 여러 축 동시</div>
<div class="desc">앵커(검증 챔피언)에서 출발해 한 칸씩 + 2축 grid. <b>전 범위 형태</b> 탐색(방향 단정 X). 신규 컬럼·횡단면 항 0.</div></div>
<div class="arrow">↓</div>
<div class="node gate"><div class="tag">④ 레짐-robust 게이트</div><div class="ttl">넓힌 만큼 강하게: WF + OOS + 다중검정보정</div>
<div class="desc">채택 = <b>여러 레짐에서 robust</b>한 것만(한 해 최고는 기각). 탐색 폭↑ → 검증 강도↑ (과적합 비례 차단).</div></div>
<div class="loop">↻ ⑤ 반복 — 영향성 지도 갱신(부상 변수 재포착) → ②로. 사장님 수동법("조금씩 바꿔보고 영향 큰 것 찾아 바꾸기")의 자동화.</div>
</div>
<div class="note"><b>v2는 별도 프로세스가 아니라 위 폐루프의 ①생성 단계 업그레이드</b>(콜드 LLM → 검증 앵커 변이) — ②~⑥ 게이트·OOS·환류는 그대로 재사용. v1(greedy)과 차이: 분석=레짐별·타겟=탐색+활용·방향=전범위·채택=레짐robust. <b>"넓은 탐색 ↔ 강한 검증"은 한 쌍.</b></div>

<h2>2. 단계별 상세 (시각)</h2>
<div class="stage gen"><div class="h"><span class="num">①</span>생성<span class="tagm">gen_template_hypothesis.py</span></div>
<div class="body">LLM(gpt_auth)이 프롬프트+직전 환류를 받아 if/elif <b>다밴드 매수코드</b> 생성 → 검증 가드(compile·scope·cost·밴드밀도) 통과분만 템플릿 저장.
<div class="ex">환류 주입 예: "THETA 앵커 고정 + 다른 시간대 탐색, 밴드당 조건 ≤10"</div></div></div>
<div class="stage bt"><div class="h"><span class="num">②</span>스모크 백테 (2분기)<span class="tagm">tmap_sweep.py · 32엔진</span></div>
<div class="body">θ를 스윕하며 백테. <b>같은 좌표</b>가 q1∧q2 둘 다 흑자여야 통과 = 체리피킹 차단.
<div class="ex">예: q1 +785,449 · q2 +1,402,966 → smoke-pass ✅ (단, 아직 진짜인지 모름)</div></div></div>
<div class="stage bt"><div class="h"><span class="num">③</span>전체기간 (3년 train)<span class="tagm">일반화 검증</span></div>
<div class="body">2분기 통과분만 3년 전체 재백테. <b>여기서 과적합이 드러남</b> — smoke-pass의 대부분이 −10~−21M로 탈락.
<div class="ex">예: 위 후보 → 3년 전체 −10,470,576 ❌ = 2분기에만 맞은 가짜 금</div></div></div>
<div class="stage bt"><div class="h"><span class="num">④</span>OOS (2022·2026)<span class="tagm">미래 재현성</span></div>
<div class="body">전체기간 통과분만 학습에 안 쓴 다른 해로 최종 검증. tick 한정(min은 OOS 오염). <b>전부 흑자라야 ★PROMISING</b>.</div></div>
<div class="stage gate"><div class="h"><span class="num">⑤</span>재백테 게이트 (P0b)<span class="tagm">refine_gate.py</span></div>
<div class="body">in-sample 흑자라도 <b>진짜 재백테가 음전이면 기각</b>(사후 포켓 편향 차단).
<div class="ex">검증: known-good +2,167,239 ⇒ PASS / 사후포켓 −1,152,966 ⇒ REFUSE</div></div></div>
<div class="stage fb"><div class="h"><span class="num">⑥</span>환류 폐루프 (P2~P5)<span class="tagm">build_feedback · --stateful</span></div>
<div class="body">결과 ledger → <b>회피</b>(과적합 코너)·<b>선호</b>(전체기간 생존) + FDR·feature_importance·Exit Regret/False-Break를 다음 생성에 주입. 무작위 추첨 → <b>학습하는 발굴</b>.</div></div>

<h2>3. 실제 산출물 예시 (탭)</h2>
<div class="tabs">
<div class="tab active" onclick="sw(0)">📝 생성 프롬프트</div>
<div class="tab" onclick="sw(1)">🧬 챔피언 조건식(T2C3)</div>
<div class="tab" onclick="sw(2)">🤖 최근 생성물</div>
<div class="tab" onclick="sw(3)">📊 변수→수익 추적(DB)</div>
<div class="tab" onclick="sw(4)">↻ 환류 피드백</div>
<div class="tab" onclick="sw(5)">🚦 게이트 판정</div>
</div>
<div class="panel active"><div class="note">LLM에게 주는 실제 지시(시간대 분할·앵커·밀도·비용 규칙). 숫자는 슬롯({})으로 비움.</div><pre>%%PROMPT%%</pre></div>
<div class="panel"><div class="note">검증된 다밴드 챔피언 = 902 소형주 + 905 소형주 + 09:05~ 시총반전 3밴드. OOS에서 THETA 능가.</div><pre>%%CHAMPION%%</pre></div>
<div class="panel"><div class="note">최근 AI 생성물: <span class="k mono">%%SAMPLE_NAME%%</span></div><pre>%%SAMPLE%%</pre></div>
<div class="panel"><div class="note">한 변수(예: b1_cap_hi)를 바꾸면 수익·거래수가 어떻게 변하나 — loop_runs.db에 세대별 기록.</div>
<table><tr><th>변수=값</th><th>수익(원)</th><th>거래수</th><th>MDD</th></tr>%%VAR_ROWS%%</table></div>
<div class="panel"><div class="note">직전 결과로 조립된 환류(다음 생성에 주입). 회피=실패 구조, 선호=전체기간 생존.</div><pre>%%FEEDBACK%%</pre></div>
<div class="panel"><div class="note">재백테 게이트가 사후 포켓 편향을 거른 실증.</div>
<pre>[게이트 로직] decide(in_sample_lift, rebacktest_profit)
  · H사례: in-sample +1,070,000 → 재백테 −1,152,966  ⇒ REFUSE (부호반전=착시)
  · known-good(THETA θ*): 재백테 +2,167,239 (2회 동일=결정론) ⇒ PASS
  · 새 후보(야간 no-go): 재백테 −3,048,898 ⇒ REFUSE
결론: 2분기만 흑자인 과적합 후보를 전체기간이 정확히 기각. 자기기만 0.</pre></div>

<h2>🎬 4. 조건식 한 개의 "일생" (실제 사례로 따라가기)</h2>
<div class="flow">
<div class="node gen"><div class="tag">생성</div><div class="ttl">AI가 다밴드 조건식 생성</div><div class="desc">환류 지시("THETA 앵커 고정 + 다른 시간대 탐색")를 받아 → <span class="mono">llmgen_theta_anchor_midcap_upperlate</span> 같은 3밴드 조건식 생성.</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">2분기 스모크</div><div class="ttl">q1 +785,449 · q2 +1,402,966 → smoke-pass ✅</div><div class="desc">짧은 2분기에선 같은 좌표가 둘 다 흑자! "오, 금인가?" — <b>하지만 아직 모름.</b></div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">3년 전체기간</div><div class="ttl">−10,470,576 ❌ 과적합 드러남</div><div class="desc">3년 전체로 보니 큰 적자 = 2분기에만 우연히 맞은 <b>가짜 금(과적합)</b>.</div></div>
<div class="arrow">↓</div>
<div class="node gate"><div class="tag">게이트</div><div class="ttl">REFUSE (기각) 🚦</div><div class="desc">검문소가 정확히 막음. OOS까지 못 감. → "진짜 금 아님" 확정.</div></div>
<div class="arrow">↓</div>
<div class="node fb"><div class="tag">환류(학습)</div><div class="ttl">"이 좌표는 과적합 — 회피" 기록 ↻</div><div class="desc">다음 생성은 이 과적합 코너를 <b>피하고</b> 더 보수적으로. = 같은 실수 반복 안 함(무작위와의 차이).</div></div>
</div>
<div class="note">★이 사례의 교훈: 2분기만 보면 <b>속는다</b>. 3년 전체+미래(OOS)까지 통과해야 진짜. 게이트가 없으면 이 가짜를 "발견!"이라 오판했을 것 — <b>정직성의 핵심.</b></div>

<h2>📖 5. 용어 사전 (쉽게)</h2>
<div class="cards">
<div class="node"><div class="ttl">조건식</div><div class="desc">매수/매도 규칙 코드. <span class="mono">if 시간·시총·신호: 매수</span></div></div>
<div class="node"><div class="ttl">다밴드</div><div class="desc">한 조건식에 <b>여러 시간대×시총</b> 분기(시초/중반/후반). 챔피언 T2C3가 이 구조.</div></div>
<div class="node"><div class="ttl">θ(세타) 슬롯</div><div class="desc">조건식의 숫자(임계값)를 비워둔 자리 <span class="mono">{cap_max}</span> — 백테가 최적값을 찾음.</div></div>
<div class="node"><div class="ttl">smoke-pass</div><div class="desc">짧은 2분기로 <b>빠른 1차</b> 통과. 같은 좌표가 양분기 흑자(체리피킹 방지).</div></div>
<div class="node"><div class="ttl">전체기간(train)</div><div class="desc">3년 전체로 검증 = <b>일반화</b> 됐나. 과적합을 여기서 잡음.</div></div>
<div class="node"><div class="ttl">OOS</div><div class="desc">학습에 <b>안 쓴 다른 해</b>(2022·2026)로 미래 재현성 검증.</div></div>
<div class="node"><div class="ttl">과적합</div><div class="desc">과거 일부에만 맞고 다른 기간엔 무너지는 <b>가짜 금</b>.</div></div>
<div class="node"><div class="ttl">앵커(THETA)</div><div class="desc">이미 <b>검증된 챔피언</b> 조건식. 새 탐색의 기준점(밴드1 고정).</div></div>
<div class="node"><div class="ttl">게이트(P0b)</div><div class="desc">가짜를 거르는 <b>검문소</b> — 재백테로 흑/적 판정.</div></div>
<div class="node"><div class="ttl">환류(피드백)</div><div class="desc">직전 결과(회피/선호)로 <b>다음 생성을 개선</b>. 무작위→학습.</div></div>
<div class="node"><div class="ttl">★PROMISING</div><div class="desc">스모크+전체기간+OOS <b>전부 통과</b>한 진짜 후보(목표).</div></div>
<div class="node"><div class="ttl">no-go</div><div class="desc">2분기부터 흑자 코너 없음 = 탈락(가장 흔함).</div></div>
</div>

<h2>6. 현재 연구 상태 (라이브)</h2>
<table><tr><th>판정</th><th>건수</th></tr>%%VERD_ROWS%%</table>
<div class="note"><b>진행: P0~P5 전 단계 구현완료(7/7)</b> + 양성대조 진단으로 <b>"천장 아님 = 생성기 병목"</b> 확정(§1.5). 콜드 생성(A·P5 런)은 gate-pass 0이었으나 검증 챔피언은 4/4 통과 → <b>다음 = v2 레짐인식 앵커변이 루프</b>(§1.6). <b>"없다"가 아니라 "콜드 생성으론 아직 — 앵커 변이로 전환".</b></div>

<h2>🌳 7. 밤샘 발굴 라이브 트리 (앵커 변이 hill-climb)</h2>
<div class="note">검증 앵커(seed)에서 변이를 가지치며 — <span style="color:var(--ok)">■초록=게이트 통과</span> · <span style="color:#8a4a4a">■빨강=탈락</span>. 라운드마다 최선(best)이 다음 앵커가 되어 트리가 아래로 자란다. 이 페이지를 새로고침하면 밤새 자라는 발굴이 그대로 보인다(LLM 0회·진짜 재백테 게이트).</div>
%%TREE%%
<div class="note">각 점에 마우스를 올리면 변이 라벨·profit·MDD. best가 ✅(게이트 통과)면 그 조건식이 다음 라운드의 출발 앵커가 된다 = "성공한 자리 옆을 더 판다".</div>

<div class="note" style="margin-top:30px">↻ 갱신: <span class="mono">PYTHONUTF8=1 python -m ai_strategy_loop.scripts.build_process_flow_html</span> · 밤샘 런: <span class="mono">overnight_anchor_mutation.py</span></div>
</div>
<script>
function sw(i){document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i===j));
document.querySelectorAll('.panel').forEach((p,j)=>p.classList.toggle('active',i===j));}
</script>
</body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
