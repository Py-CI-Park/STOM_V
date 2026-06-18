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
    }
    for k, v in repl.items():
        html_doc = html_doc.replace(k, v)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"[OK] {OUT}  ({len(html_doc):,} bytes)  iter={st['iter']}/40 생존={st['surv']}")
    return 0


_TEMPLATE = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STOM 조건식 발굴 프로세스</title>
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
</style></head><body>
<header><h1>🔬 STOM 조건식 발굴 프로세스 — 라이브 흐름</h1>
<div class="sub">생성일 %%GEN_TIME%% · %%BADGES%%</div></header>
<div class="wrap">

<div class="goal"><b>🎯 목표 &amp; 마인드셋</b> — 광산에서 <b>수익 나는 매수/매도 조건식(실매매용 per-stock if-Buy)</b>을 캐낸다.
<b>아직 답을 못 찾았고 프로세스도 미완성</b>이다. 인간은 고빈도 우상향 백테를 찾는다 = <b>가능하다</b>.
"데이터 천장"이 아니라 <b>프로세스를 계속 발전</b>시켜 찾는 게 목표. 엔진/CLI 무수정.</div>

<h2>🪙 이게 무슨 연구인가요? (아주 쉬운 설명)</h2>
<div class="cards">
<div class="node gen"><div class="ttl">조건식 = 금광맥 ⛏️</div><div class="desc">"이런 종목을·이 시간에·이 신호가 뜨면 사라(팔아라)"는 <b>매수/매도 규칙</b>(코드). 우리가 캐려는 광석. 실매매 프로그램에 바로 넣는 산출물.</div></div>
<div class="node bt"><div class="ttl">백테스트 = 금 감정사 🔍</div><div class="desc">그 규칙을 <b>과거 데이터에 적용</b>해 "진짜 돈이 됐나" 계산. <b>가짜 금(과적합)</b>을 골라냄.</div></div>
<div class="node fb"><div class="ttl">이 시스템 = 자동 채굴기 🤖</div><div class="desc">AI가 규칙을 만들고 → 백테로 검증하고 → <b>실패에서 배워</b> 다음엔 더 잘 캐도록 *스스로 반복*.</div></div>
</div>
<div class="note" style="font-size:14px;line-height:1.7">
<b>한눈에 흐름</b> — ① AI가 규칙을 만든다 → ② 과거 2분기로 <b>빠르게</b> 본다 → ③ 통과하면 <b>3년 전체</b>로 본다 → ④ <b>다른 해(미래)</b>로도 본다 → ⑤ 가짜면 <b>검문소(게이트)</b>가 막는다 → ⑥ 실패를 <b>기억</b>해 다음엔 안 만든다 → <b>↻ 반복</b>.<br>
💡 <b>지금 상태</b>: 아직 진짜 금(전체기간+미래 다 통과하는 새 조건식)은 못 찾았습니다. 하지만 <b>인간 트레이더는 찾으니 가능</b>하고, 우리는 채굴기(프로세스)를 계속 개량하는 중입니다 — "없다"가 아니라 "이 방법으론 아직".</div>
<div class="note">🎨 <b>색상 범례</b>: <span style="color:var(--mag)">●보라=생성</span> · <span style="color:var(--acc)">●파랑=백테</span> · <span style="color:var(--ok)">●초록=게이트</span> · <span style="color:var(--warn)">●주황=환류</span></div>

<h2>1. 전체 파이프라인 (데이터마이닝 폐루프)</h2>
<div class="flow">
<div class="node gen"><div class="tag">① 생성 · gen_template_hypothesis.py</div><div class="ttl">AI가 다밴드 조건식 생성</div>
<div class="desc">시간대×시총 이산분기(시초/중반/후반) 조건식을 LLM이 생성. 직전 결과(회피/선호) 환류 + 검증 가드(밴드당≤10·비용·금지변수).</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">② 스모크 백테 · tmap_sweep.py (32엔진)</div><div class="ttl">2분기 · 같은 좌표 양분기 흑자 게이트</div>
<div class="desc">변수(θ)를 스윕하며 백테. q1∧q2 같은 좌표가 둘 다 흑자여야 통과(체리피킹 차단).</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">③ 전체기간 백테 · 3년 train</div><div class="ttl">일반화 검증 (과적합 차단)</div>
<div class="desc">2분기 통과분만 3년 전체기간 재백테. 여기서 음전(과적합)이면 탈락 = 착시 차단.</div></div>
<div class="arrow">↓</div>
<div class="node bt"><div class="tag">④ OOS · 2022·2026</div><div class="ttl">미래 재현성</div>
<div class="desc">전체기간 통과분만 다른 해(OOS)로 최종 검증. ★PROMISING = 전부 흑자(THETA급 바).</div></div>
<div class="arrow">↓</div>
<div class="node gate"><div class="tag">⑤ 게이트 · refine_gate.py (P0b)</div><div class="ttl">사후슬라이스 착시 REFUSE</div>
<div class="desc">in-sample 흑자라도 재백테 음전이면 기각. 검증됨: known-good +2.17M PASS · 사후포켓 −1.15M REFUSE.</div></div>
<div class="loop">↻ ⑥ 환류 (P2 build_feedback) — no-go=회피·과적합=회피·전체기간생존=선호 → <b>다음 생성(①)으로</b> · 무작위 추첨을 "학습하는 발굴"로</div>
</div>
<div class="note">정직지표 = OOS 통과 후보 수(현재 baseline 0). 점수가 아니라 *일반화 생존*만 합격.</div>

<h2>2. 단계별 상세 (클릭하여 펼치기)</h2>
<div class="cards">
<details><summary>① 생성</summary><div class="note">LLM(gpt_auth)이 프롬프트+환류 받아 if/elif 다밴드 매수코드 생성 → 검증 가드(compile/scope/cost/밀도) 통과분만 템플릿 저장(llmgen_*).</div></details>
<details><summary>② 스모크 게이트</summary><div class="note">tmap_sweep가 핵심축 5개·40점 스윕. 같은좌표 min(q1,q2)&gt;0 = smoke-pass. 선택편향 차단.</div></details>
<details><summary>③ 전체기간</summary><div class="note">train-3y 재백테. smoke-pass의 ~전부가 여기서 −10~−21M 과적합으로 드러나 탈락(격상 게이트의 가치).</div></details>
<details><summary>④ OOS</summary><div class="note">2022·2026 재현성. tick 한정(min은 OOS 오염). 전부 흑자라야 ★PROMISING.</div></details>
<details><summary>⑤ 재백테 게이트(P0b)</summary><div class="note">claude_candidate_batch_eval 배선. 결정론 검증→1회 충분. 새 후보를 진짜 재백테로 흑/적 판정.</div></details>
<details><summary>⑥ 환류 폐루프(P2)</summary><div class="note">ledger→회피(홍수/과적합)/선호(전체기간 생존) 조립해 다음 생성에 주입. --stateful 토글.</div></details>
</div>

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
<div class="panel"><div class="note">재백테 게이트가 사후슬라이스 착시를 거른 실증.</div>
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
<div class="note">전체기간 생존(train-pass+)이 1건이라도 나오면 = 일반화 금맥 발굴. 0이면 = 다음 프로세스 개선(P3: 조건별 기여도 분석·불필요 제거)이 필요하다는 신호. <b>"없다"가 아니라 "이 방법으론 아직".</b></div>

<div class="note" style="margin-top:30px">↻ 갱신: <span class="mono">PYTHONUTF8=1 python -m ai_strategy_loop.scripts.build_process_flow_html</span></div>
</div>
<script>
function sw(i){document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',i===j));
document.querySelectorAll('.panel').forEach((p,j)=>p.classList.toggle('active',i===j));}
</script>
</body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
