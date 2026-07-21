# -*- coding: utf-8 -*-
"""V5.6 (G5·G7) 스텝별 연구 리포트 오프라인 생성 CLI.

명시적/수동 실행 전용. 서버(GET/WS) 경로에서 호출 금지.
입력 JSON(리포트 spec 리스트)을 받아 표준양식 HTML 리포트와 manifest 를
docs/generated_reports/ (allowlisted, /reports 열거·CSP 서빙 대상)에 atomic write 한다.

사용:
  python scripts/build_step_reports.py --specs-json <specs.json>
  python scripts/build_step_reports.py --specs-json specs.json --out-dir docs/generated_reports

specs.json 형식:
  [{"research_id": "...", "step_id": "...", "title": "...", "purpose": "...",
    "date": "...", "hypothesis": "...", "method": "...", "results": [...],
    "analysis": "...", "conclusion": "...", "limits": "...", "history": [...],
    "related_docs": ["some_report.html"], "related_commits": ["abc1234 ..."],
    "provenance": "...", "trust": "derived"}]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_strategy_loop.dashboard.report_writer import write_reports  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_OUT = os.path.join(_REPO_ROOT, "docs", "generated_reports")
def _source_sha256(rows: object) -> str:
    """Hash the canonical rows read from one readonly SQLite snapshot."""
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()




def specs_from_loop_runs(db_path: str) -> list:
    """loop_runs.db(runs·generations)에서 세대별 스텝 리포트 spec 을 자동 구성한다.
    읽기 전용(SELECT-only)·오프라인. 0 runs 면 빈 리스트(정직 메시지는 호출부)."""
    import sqlite3
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        run_rows = conn.execute(
            "SELECT run_id, status, best_gen, best_score FROM runs ORDER BY run_id"
        ).fetchall()
        runs = {
            row["run_id"]: {
                "status": row["status"], "best_gen": row["best_gen"], "best_score": row["best_score"],
            }
            for row in run_rows
        }
        generation_rows = conn.execute(
            "SELECT run_id, gen_no, buy_name, sell_name, status, score, mdd, profit, trade_count, "
            "gate_passed, reason, strategy_gist, created_at FROM generations ORDER BY run_id, gen_no"
        ).fetchall()
        source_sha256 = _source_sha256({
            "runs": [dict(row) for row in run_rows],
            "generations": [dict(row) for row in generation_rows],
        })
        specs: list = []
        from datetime import datetime, timezone
        for row in generation_rows:
            run_id, gen_no, buy, sell, status, score, mdd, profit, trades, gate, reason, gist, created = row
            date = (datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")
                    if isinstance(created, (int, float)) and created and created > 1e9 else "")
            run_meta = runs.get(run_id, {})
            specs.append({
                "research_id": run_id, "step_id": f"gen{gen_no}",
                "title": f"{run_id} 세대 {gen_no} 스텝 리포트",
                "purpose": "AI 루프 세대별 조건식 생성·백테스트·채점 결과의 표준양식 기록",
                "date": date,
                "hypothesis": gist or "(strategy_gist 미기재)",
                "method": f"조건식 생성(LLM) → 공식 백테스트 → 채점/게이트 · 매수 {buy or '—'} · 매도 {sell or '—'}",
                "results": [
                    f"score {score if score is not None else '—'}",
                    f"MDD {mdd if mdd is not None else '—'}",
                    f"profit {profit if profit is not None else '—'}",
                    f"trades {trades if trades is not None else '—'}",
                    f"gate {'통과' if gate else '미통과'}",
                ],
                "analysis": reason or "(부검 사유 미기재)",
                "conclusion": ("게이트 통과 후보" if gate else "게이트 미통과 — 다음 세대 피드백") +
                              (f" · run best gen {run_meta.get('best_gen')}" if run_meta.get("best_gen") is not None else ""),
                "limits": "단일 run 내부 지표 — 표본 외/승격 증거 아님(performance_proved=false)",
                "history": [f"run status {status or run_meta.get('status') or '—'}"],
                "related_docs": [], "related_commits": [],
                "provenance": "ai_strategy_loop/state/loop_runs.db (SELECT-only)",
                "source_sha256": source_sha256,
                "trust": "derived",
            })
        return specs
    finally:
        conn.close()


def _esc(v) -> str:
    import html as _h
    return _h.escape("" if v is None else str(v), quote=True)


def _successful_measurements(gens: list) -> tuple[list[dict], list[dict]]:
    """Keep only canonical successful rows with a numeric score for performance summaries."""
    successful_statuses = {"ok", "success", "done", "complete"}  # Canonical plus legacy aliases.
    measured: list[dict] = []
    excluded: list[dict] = []
    for generation in gens:
        status = str(generation.get("status") or "").lower()
        if status not in successful_statuses:
            excluded.append({"gen_no": generation.get("gen_no"), "reason": f"status={status or 'missing'}"})
        elif not isinstance(generation.get("score"), (int, float)):
            excluded.append({"gen_no": generation.get("gen_no"), "reason": "score unavailable"})
        else:
            measured.append(generation)
    return measured, excluded

def _flow_svg(gens: list) -> str:
    """세대별 score 개선 흐름도 — 인라인 SVG(무script). gate 통과=teal 원, best=보라 큰 원."""
    W, H, PAD = 760, 220, 34
    gens, _excluded = _successful_measurements(gens)
    scores = [(g["gen_no"], g["score"]) for g in gens]
    if len(scores) < 1:
        return "<p>(score 데이터 없음)</p>"
    xs = [s[0] for s in scores]; ys = [s[1] for s in scores]
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
    if x1 == x0: x1 = x0 + 1
    if y1 == y0: y1 = y0 + 1
    px = lambda x: PAD + (x - x0) / (x1 - x0) * (W - 2 * PAD)
    py = lambda y: H - PAD - (y - y0) / (y1 - y0) * (H - 2 * PAD)
    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in scores)
    best = max(scores, key=lambda s: s[1])
    dots = []
    for g in gens:
        if not isinstance(g.get("score"), (int, float)):
            continue
        cx, cy = px(g["gen_no"]), py(g["score"])
        if g.get("gate_passed"):
            dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#4cd6b3"><title>gen {g["gen_no"]} gate 통과 · score {g["score"]}</title></circle>')
        else:
            dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="#8892a6"><title>gen {g["gen_no"]} score {g["score"]}</title></circle>')
    dots.append(f'<circle cx="{px(best[0]):.1f}" cy="{py(best[1]):.1f}" r="8" fill="none" stroke="#a594ff" stroke-width="2.5"><title>best gen {best[0]}</title></circle>')
    return (
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="세대별 score 개선 흐름도" '
        f'style="width:100%;max-width:{W}px;background:#f7f9fb;border:1px solid #dde;border-radius:8px">'
        f'<text x="{PAD}" y="18" font-size="12" fill="#556">score 개선 흐름 (gen {x0}→{x1} · ● gate 통과 · ◯ best)</text>'
        f'<polyline points="{pts}" fill="none" stroke="#2a9d8f" stroke-width="2" />'
        + "".join(dots) + "</svg>"
    )


def _viz_section(gens: list) -> str:
    """v5.4 R2 — 표준 포맷 v2 성과 시각화: KPI 표 + score 바차트 + MDD×score 산점도(무script SVG)."""
    scored, excluded = _successful_measurements(gens)
    if not scored:
        return "<p>(성공한 score 데이터 없음; 실패/측정 누락 세대는 성과 집계에서 제외)</p>"
    n = len(scored)
    avg = lambda arr: (sum(arr) / len(arr)) if arr else 0.0
    scores = [g["score"] for g in scored]
    mdds = [g["mdd"] for g in scored if isinstance(g.get("mdd"), (int, float))]
    trades = [g["trades"] for g in scored if isinstance(g.get("trades"), (int, float))]
    profits = [g["profit"] for g in scored if isinstance(g.get("profit"), (int, float))]
    profit_sorted = sorted(profits)
    profit_median = (
        profit_sorted[len(profit_sorted) // 2]
        if len(profit_sorted) % 2
        else (profit_sorted[len(profit_sorted) // 2 - 1] + profit_sorted[len(profit_sorted) // 2]) / 2
    ) if profit_sorted else None
    gate_n = sum(1 for g in scored if g.get("gate_passed"))
    kpi = (
        '<table style="border-collapse:collapse;width:100%;margin:8px 0">'
        "<tr>" + "".join(
            f'<td style="border:1px solid #dde;padding:8px 12px;text-align:center"><div style="font-size:11px;color:#889">{k}</div>'
            f'<div style="font-size:18px;font-weight:700">{v}</div></td>'
            for k, v in [
                ("세대", f"{n}"), ("gate 통과율", f"{gate_n}/{n} ({gate_n / n * 100:.0f}%)"),
                ("평균 score", f"{avg(scores):.2f}"), ("최고 score", f"{max(scores):.2f}"),
                ("평균 MDD", f"{avg(mdds):.1f}%" if mdds else "—"),
                ("profit 표본", f"n={len(profits)}"),
                ("profit 중앙값", f"{profit_median:,.0f}" if profit_median is not None else "—"),
                ("최고 profit", f"{max(profits):,.0f}" if profits else "—"),
                ("best−중앙값", f"{max(profits) - profit_median:,.0f}" if profit_median is not None else "—"),
                ("평균 거래", f"{avg(trades):.0f}건" if trades else "—"),
            ]) + "</tr></table>")
    # score 바차트
    W, H, PAD = 760, 200, 34
    bw = max(3.0, (W - 2 * PAD) / max(1, n) * 0.72)
    smax = max(scores) or 1
    bars = []
    for i, g in enumerate(scored):
        x = PAD + (W - 2 * PAD) * (i + 0.14) / max(1, n)
        h = max(2.0, (g["score"] / smax) * (H - 2 * PAD))
        color = "#4cd6b3" if g.get("gate_passed") else "#a9b4c6"
        bars.append(f'<rect x="{x:.1f}" y="{H - PAD - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{color}">'
                    f'<title>gen {g["gen_no"]} · score {g["score"]}</title></rect>')
    bar_svg = (
        f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="세대별 score 바차트" '
        f'style="width:100%;max-width:{W}px;background:#f7f9fb;border:1px solid #dde;border-radius:8px">'
        f'<text x="{PAD}" y="18" font-size="12" fill="#556">세대별 score (초록=gate 통과)</text>'
        + "".join(bars) + "</svg>")
    # MDD × score 산점도
    pts_src = [g for g in scored if isinstance(g.get("mdd"), (int, float))]
    scatter_svg = ""
    if len(pts_src) >= 3:
        mx0, mx1 = min(g["mdd"] for g in pts_src), max(g["mdd"] for g in pts_src)
        sy0, sy1 = min(g["score"] for g in pts_src), max(g["score"] for g in pts_src)
        if mx1 == mx0: mx1 = mx0 + 1
        if sy1 == sy0: sy1 = sy0 + 1
        px = lambda v: PAD + (v - mx0) / (mx1 - mx0) * (W - 2 * PAD)
        py = lambda v: H - PAD - (v - sy0) / (sy1 - sy0) * (H - 2 * PAD)
        dots = "".join(
            f'<circle cx="{px(g["mdd"]):.1f}" cy="{py(g["score"]):.1f}" r="4.5" '
            f'fill="{"#4cd6b3" if g.get("gate_passed") else "#8892a6"}" fill-opacity="0.8">'
            f'<title>gen {g["gen_no"]} · MDD {g["mdd"]} · score {g["score"]}</title></circle>'
            for g in pts_src)
        scatter_svg = (
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="MDD 대 score 산점도; 좌상단은 저위험 고성과" '
            f'style="width:100%;max-width:{W}px;background:#f7f9fb;border:1px solid #dde;border-radius:8px;margin-top:10px">'
            f'<text x="{PAD}" y="18" font-size="12" fill="#556">x축 MDD(%, 오른쪽일수록 위험) · y축 score(높을수록 성과) · 표본 n={len(pts_src)} · threshold: gate 통과 · 좌상단=저위험·고성과</text>'
            + dots + "</svg>")
    excluded_note = (
        f"<p class='muted'>성과 집계 제외: {len(excluded)}건 (실패 또는 score 측정 누락)</p>"
        if excluded else ""
    )
    return excluded_note + kpi + bar_svg + scatter_svg


def _table_columns(conn, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _safe_profile(config_json: str | None) -> dict:
    try:
        config = json.loads(config_json or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(config, dict):
        return {}
    blocked = ("secret", "token", "password", "cookie", "authorization", "api_key", "path", "database")
    profile = {}
    for key, value in sorted(config.items()):
        key_text = str(key)
        if any(term in key_text.lower() for term in blocked):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            profile[key_text] = value
        if len(profile) >= 24:
            break
    return profile


def _run_evidence_counts(conn, run_id: str) -> dict:
    specs = {
        "prompts": ("prompts", "COUNT(*), COALESCE(SUM(total_tokens), 0)"),
        "evaluation_manifests": ("evaluation_manifests", "COUNT(*), 0"),
        "candidate_passports": ("candidate_passports", "COUNT(*), 0"),
        "run_receipts": ("run_receipts", "COUNT(*), 0"),
    }
    result: dict = {}
    availability: dict[str, str] = {}
    for key, (table, expression) in specs.items():
        try:
            if not _table_columns(conn, table):
                raise RuntimeError("table unavailable")
            row = conn.execute(
                f"SELECT {expression} FROM {table} WHERE run_id = ?", (run_id,)
            ).fetchone()
            result[key] = int(row[0] or 0)
            if key == "prompts":
                result["total_tokens"] = int(row[1] or 0)
            availability[key] = "available"
        except Exception as error:
            result[key] = None
            if key == "prompts":
                result["total_tokens"] = None
            availability[key] = f"unavailable: {type(error).__name__}"
    result.setdefault("total_tokens", 0)
    result["availability"] = availability
    return result


def _hypothesis_summary(raw) -> str:
    if not raw:
        return "(미기재)"
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return str(raw)[:500]
    if isinstance(value, list):
        return " / ".join(str(item) for item in value[:4]) or "(미기재)"
    if isinstance(value, dict):
        return " / ".join(f"{key}: {value[key]}" for key in list(value)[:4]) or "(미기재)"
    return str(value)[:500]


def build_run_report(db_path: str, out_dir: str, run_id: str | None = None, manifest_path: str | None = None) -> list:
    """run 1개당 종합 HTML 1개(U4): 표지·개선 흐름도·세대별 스텝 블록·최종 후보·안전 문구.
    loop_runs.db SELECT-only · 오프라인 · 무script(인라인 SVG). 생성 파일 경로 리스트 반환."""
    import sqlite3
    from datetime import datetime, timezone
    from ai_strategy_loop.dashboard.report_writer import publish_reports  # noqa: PLC0415
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rendered: list = []
    try:
        conn.execute("BEGIN")
        runs = conn.execute(
            "SELECT run_id, started_at, config_json, status, best_gen, best_score, finished_at FROM runs"
            + (" WHERE run_id = ?" if run_id else ""),
            ((run_id,) if run_id else ()),
        ).fetchall()
        generation_columns = _table_columns(conn, "generations")
        requested_generation_fields = [
            ("gen_no", "gen_no"), ("buy_name", "buy"), ("sell_name", "sell"),
            ("status", "status"), ("score", "score"), ("mdd", "mdd"),
            ("profit", "profit"), ("trade_count", "trades"),
            ("gate_passed", "gate_passed"), ("reason", "reason"),
            ("strategy_gist", "gist"), ("parent_gen", "parent_gen"),
            ("diff_from_parent", "diff"), ("total_profit_pct", "profit_pct"),
            ("payoff_ratio", "payoff_ratio"), ("give_back_rate", "give_back_rate"),
            ("hypotheses_json", "hypotheses_json"),
        ]
        generation_select = ", ".join(
            f"{source if source in generation_columns else 'NULL'} AS {alias}"
            for source, alias in requested_generation_fields
        )
        for run in runs:
            rid = run["run_id"]
            started = run["started_at"]
            status = run["status"]
            best_gen = run["best_gen"]
            best_score = run["best_score"]
            finished = run["finished_at"]
            profile = _safe_profile(run["config_json"])
            evidence = _run_evidence_counts(conn, rid)
            rows = conn.execute(
                f"SELECT {generation_select} FROM generations WHERE run_id = ? ORDER BY gen_no",
                (rid,),
            ).fetchall()
            gens = [dict(row) for row in rows]
            source_sha256 = _source_sha256({
                "run": dict(run),
                "generations": gens,
                "evidence": evidence,
            })
            fmt_ts = lambda t: (datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if isinstance(t, (int, float)) and t and t > 1e9 else "—")
            blocks = []
            for g in gens:
                parent = f'부모 gen {_esc(g["parent_gen"])}' if g.get("parent_gen") is not None else "부모 없음/미기재"
                diff = _esc(g.get("diff") or "(변경 근거 미기재)")
                hypothesis = _esc(_hypothesis_summary(g.get("hypotheses_json") or g.get("gist")))
                blocks.append(
                    f'<section class="gen" id="gen-{g["gen_no"]}">'
                    f'<h3 id="h-gen-{g["gen_no"]}">세대 {g["gen_no"]} {"· gate 통과 ✓" if g["gate_passed"] else ""}</h3>'
                    f'<p><b>계보</b> {parent}<br><b>부모 대비 변경</b> {diff}</p>'
                    f'<p><b>조건식</b> 매수 {_esc(g["buy"])} · 매도 {_esc(g["sell"])}<br>'
                    f'<b>가설</b> {hypothesis}</p>'
                    f'<p><b>백테 결과</b> score {_esc(g["score"])} · MDD {_esc(g["mdd"])}% · '
                    f'profit {_esc(g["profit"])}원 · return {_esc(g["profit_pct"])}% · trades {_esc(g["trades"])} · '
                    f'payoff {_esc(g["payoff_ratio"])} · give-back {_esc(g["give_back_rate"])}%</p>'
                    f'<p><b>부검/다음 세대 반영</b> {_esc(g["reason"] or "(사유 미기재)")}</p>'
                    "</section>")
            gate_n = sum(1 for g in gens if g["gate_passed"])
            lineage_n = sum(1 for g in gens if g.get("parent_gen") is not None)
            evidence.update({
                "generations": len(gens),
                "lineage_links": lineage_n,
                "gate_passed": gate_n,
            })
            profile_rows = "".join(
                f"<tr><th>{_esc(key)}</th><td>{_esc(value)}</td></tr>"
                for key, value in profile.items()
            ) or '<tr><td colspan="2">(공개 가능한 실행 설정 없음)</td></tr>'
            availability = evidence.get("availability", {})
            evidence_rows = "".join(
                f'<div><span class="k">{_esc(key)}</span><b>{_esc(availability.get(key, "unavailable") if value is None else value)}</b></div>'
                for key, value in evidence.items() if key != "availability"
            )
            if status != "complete":
                decision = f"run 상태가 {status or 'unknown'}이므로 승격·성과 결론을 금지하고 원인 검토가 필요합니다."
            elif gate_n == 0:
                decision = "gate 통과 후보가 없어 승격할 수 없습니다. 실패 근거를 다음 연구 가설로 연결해야 합니다."
            else:
                decision = f"gate 통과 {gate_n}건이 있으나 표본 내 결과입니다. human review와 OOS 검증 전 승격할 수 없습니다."
            # v5.6 U12 — run-comprehensive-v3: design.md §7 계약(네이비/골드 리포트 톤·마스트헤드·KPI 카드).
            html_text = (
                '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>Run 종합 보고서 — {_esc(rid)}</title>"
                "<style>"
                ":root{--navy:#122036;--navy2:#1b3050;--gold:#c8a14a;--ink:#1a2028;--mut:#66738a;--line:#dfe4ec;--bg:#f4f5f7;--card:#ffffff}"
                "*{box-sizing:border-box}body{font-family:system-ui,'Malgun Gothic',sans-serif;background:var(--bg);color:var(--ink);margin:0;line-height:1.65}"
                ".wrap{max-width:1020px;margin:0 auto;padding:0 24px 40px}"
                "header.mast{background:linear-gradient(135deg,var(--navy),var(--navy2));color:#f2f5fa;padding:34px 28px 26px;border-radius:0 0 14px 14px}"
                "header.mast .kicker{font-size:11px;letter-spacing:.22em;color:var(--gold);text-transform:uppercase}"
                "header.mast h1{font-size:26px;margin:6px 0 4px}"
                "header.mast .sub{font-size:12.5px;color:#b9c4d6}"
                ".mastkpi{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}"
                ".mastkpi div{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:10px 16px;min-width:130px}"
                ".mastkpi .k{font-size:10.5px;color:#9fb0c8;letter-spacing:.08em}.mastkpi .v{font-size:19px;font-weight:700;color:#fff}"
                "h2{font-size:17px;margin:34px 0 12px;color:var(--navy);border-left:4px solid var(--gold);padding-left:10px}"
                "section.gen{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:12px 0;box-shadow:0 1px 2px rgba(16,24,40,.04)}"
                "section.gen h3{margin:0 0 8px;font-size:14.5px;color:var(--navy)}"
                "table{border-collapse:collapse;width:100%}td{background:var(--card)}"
                "table.profile th,table.profile td{padding:7px 10px;border:1px solid var(--line);text-align:left;font-size:12px}"
                ".evidence{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}.evidence div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}.evidence .k{display:block;color:var(--mut);font-size:10px}.evidence b{font-size:18px}"
                ".decision{background:var(--card);border:1px solid var(--gold);border-left:5px solid var(--gold);border-radius:8px;padding:14px 16px;font-weight:600}"
                "a{color:#155acb;text-decoration:none}a:hover{text-decoration:underline}"
                "nav.tabs{position:sticky;top:0;z-index:3;display:flex;gap:7px;overflow-x:auto;padding:10px 0;background:var(--bg);border-bottom:1px solid var(--line)}"
                "nav.tabs a{flex:0 0 auto;padding:6px 11px;border:1px solid #cbd5e3;border-radius:999px;background:var(--card)}"
                "h2{scroll-margin-top:64px}"
                "footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:var(--mut)}"
                "@media(max-width:680px){.wrap{padding:0 14px 28px}header.mast{padding:24px 16px}.mastkpi div{min-width:calc(50% - 6px)}table{display:block;overflow-x:auto}svg{width:100%;height:auto}}"
                "@media print{header.mast{border-radius:0}nav.tabs{display:none}section.gen{break-inside:avoid}svg{max-width:100%}}"
                "</style></head><body>"
                '<header class="mast"><div class="kicker">V2UC DASHBOARD · RUN COMPREHENSIVE REPORT</div>'
                f"<h1>Run 종합 보고서 — {_esc(rid)}</h1>"
                f'<div class="sub">기간 {fmt_ts(started)} ~ {fmt_ts(finished)} · 상태 {_esc(status)}</div>'
                '<div class="mastkpi">'
                f'<div><div class="k">세대</div><div class="v">{len(gens)}</div></div>'
                f'<div><div class="k">GATE 통과</div><div class="v">{gate_n}</div></div>'
                f'<div><div class="k">BEST GEN</div><div class="v">{_esc(best_gen)}</div></div>'
                f'<div><div class="k">BEST SCORE</div><div class="v">{_esc(best_score)}</div></div>'
                "</div></header>"
                '<div class="wrap">'
                '<nav class="tabs" aria-label="보고서 섹션"><a href="#sec-profile">실행 프로파일</a><a href="#sec-evidence">근거</a><a href="#sec-flow">개선 흐름</a><a href="#sec-viz">성과</a><a href="#sec-gens">세대 기록</a><a href="#sec-conclusion">결론</a><a href="#sec-safety">한계</a></nav>'
                '<h2 id="sec-profile">1. 실행 프로파일</h2><table class="profile"><tbody>' + profile_rows + '</tbody></table>'
                '<h2 id="sec-evidence">2. 근거·비용·검증 자산</h2><div class="evidence">' + evidence_rows + '</div>'
                '<h2 id="sec-flow">3. 다중 세대 개선 흐름도</h2>' + _flow_svg(gens) +
                '<h2 id="sec-viz">4. 성과 시각화 (KPI · score 바차트 · 위험-성과 산점도)</h2>' + _viz_section(gens) +
                '<h2 id="sec-gens">5. 세대별 스텝 기록 (생성→백테스트→채점→부검→반영)</h2>' + ("".join(blocks) or "<p>(세대 없음)</p>") +
                f'<h2 id="sec-conclusion">6. 결론·다음 행동</h2><div class="decision">{_esc(decision)}</div>'
                '<h2 id="sec-safety">7. 안전·한계</h2><p>표본 내 지표 요약이며 성능 증명이 아닙니다(performance_proved=false). '
                "운영 export는 human 승인 절차와 분리되어 있으며 profile이 다른 run 사이의 단순 delta 비교는 금지합니다.</p>"
                f"<footer>생성 {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} · 포맷 run-comprehensive-v3(design.md §7) · 원천 loop_runs.db(SELECT-only) · 읽기 전용(sandbox·CSP 서빙)</footer>"
                "</div></body></html>")
            fname = f"run_report_{rid}.html"
            rendered.append((
                {
                    "research_id": rid, "run_id": rid, "step_id": "run",
                    "status": status or "unknown", "provenance": "ai_strategy_loop/state/loop_runs.db (SELECT-only)",
                    "trust": "derived", "source_sha256": source_sha256,
                    "toc": [
                        {"id": "sec-profile", "label": "실행 프로파일"},
                        {"id": "sec-evidence", "label": "근거·비용·검증 자산"},
                        {"id": "sec-flow", "label": "개선 흐름도"},
                        {"id": "sec-viz", "label": "성과 시각화"},
                        {"id": "sec-gens", "label": "세대별 스텝 기록"},
                        {"id": "sec-conclusion", "label": "결론·다음 행동"},
                        {"id": "sec-safety", "label": "안전·한계"},
                    ],
                    "profile": profile,
                    "evidence": evidence,
                    "decision": decision,
                    "limitations": [
                        "표본 내 지표이며 성능 증명이 아님",
                        "human review와 운영 export는 별도 경계",
                        "profile hash가 다른 run의 단순 delta 비교 금지",
                    ],
                },
                fname, html_text, "run",
            ))
        if not rendered:
            return []
        manifest = publish_reports(rendered, out_dir, manifest_path)
        published_paths = {path for _spec, path, _html, _type in rendered}
        return [entry for entry in manifest["reports"] if entry.get("path") in published_paths]
    finally:
        conn.close()


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="스텝별 연구 리포트 오프라인 생성기(G5·G7)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--specs-json", help="리포트 spec 리스트 JSON 경로")
    src.add_argument("--from-loop-runs", nargs="?", const="", metavar="DB",
                     help="loop_runs.db 에서 세대별 스텝 리포트 자동 구성(기본 ai_strategy_loop/state/loop_runs.db)")
    src.add_argument("--run-report", nargs="?", const="", metavar="RUN_ID",
                     help="run 종합 보고서(U4) 생성 — RUN_ID 미지정 시 전체 run. loop_runs.db SELECT-only")
    ap.add_argument("--db", default=None, help="loop_runs.db 경로 오버라이드")
    ap.add_argument("--out-dir", default=_DEFAULT_OUT, help="HTML 출력 디렉터리(기본 docs/generated_reports)")
    ap.add_argument("--manifest", default=None, help="manifest 경로(기본 <out-dir>/manifest.json)")
    args = ap.parse_args(argv)

    if args.run_report is not None:
        db = args.db or os.path.join(_REPO_ROOT, "ai_strategy_loop", "state", "loop_runs.db")
        if not os.path.exists(db):
            print(f"ERROR: loop_runs.db 없음: {db}", file=sys.stderr)
            return 2
        written = build_run_report(db, args.out_dir, args.run_report or None, args.manifest)
        if not written:
            print(f"0 runs — 생성할 run 종합 보고서가 없습니다(정직 종료): {db}")
            return 0
        print(f"run 종합 보고서 {len(written)}개 생성 → {args.out_dir}")
        for w in written:
            print(f"  - {w['path']} (run={w['run_id']} sha={w['sha256'][:12]} {w['bytes']}B)")
        return 0

    if args.from_loop_runs is not None:
        db = args.from_loop_runs or os.path.join(_REPO_ROOT, "ai_strategy_loop", "state", "loop_runs.db")
        if not os.path.exists(db):
            print(f"ERROR: loop_runs.db 없음: {db}", file=sys.stderr)
            return 2
        specs = specs_from_loop_runs(db)
        if not specs:
            print(f"0 runs — 생성할 스텝 리포트가 없습니다(정직 종료): {db}")
            return 0
    else:
        with open(args.specs_json, "r", encoding="utf-8") as fh:
            specs = json.load(fh)
        if not isinstance(specs, list):
            print("ERROR: specs-json 최상위는 리스트여야 합니다.", file=sys.stderr)
            return 2

    manifest_path = args.manifest or os.path.join(args.out_dir, "manifest.json")
    manifest = write_reports(specs, args.out_dir, manifest_path)
    print(f"생성 완료: {manifest['count']}개 리포트 → {args.out_dir}")
    print(f"manifest: {manifest_path}")
    for e in manifest["reports"]:
        print(f"  - {e['path']} (research_id={e['research_id']} step={e['step_id']} sha={e['sha256'][:12]} {e['bytes']}B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
