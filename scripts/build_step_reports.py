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
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_strategy_loop.dashboard.report_writer import write_reports  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_OUT = os.path.join(_REPO_ROOT, "docs", "generated_reports")


def specs_from_loop_runs(db_path: str) -> list:
    """loop_runs.db(runs·generations)에서 세대별 스텝 리포트 spec 을 자동 구성한다.
    읽기 전용(SELECT-only)·오프라인. 0 runs 면 빈 리스트(정직 메시지는 호출부)."""
    import sqlite3
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        runs = {r[0]: {"status": r[1], "best_gen": r[2], "best_score": r[3]}
                for r in conn.execute("SELECT run_id, status, best_gen, best_score FROM runs")}
        specs: list = []
        cur = conn.execute(
            "SELECT run_id, gen_no, buy_name, sell_name, status, score, mdd, profit, trade_count, "
            "gate_passed, reason, strategy_gist, created_at FROM generations ORDER BY run_id, gen_no")
        from datetime import datetime, timezone
        for (run_id, gen_no, buy, sell, status, score, mdd, profit, trades, gate, reason, gist, created) in cur.fetchall():
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
                "trust": "derived",
            })
        return specs
    finally:
        conn.close()


def _esc(v) -> str:
    import html as _h
    return _h.escape("" if v is None else str(v), quote=True)


def _flow_svg(gens: list) -> str:
    """세대별 score 개선 흐름도 — 인라인 SVG(무script). gate 통과=teal 원, best=보라 큰 원."""
    W, H, PAD = 760, 220, 34
    scores = [(g["gen_no"], g["score"]) for g in gens if isinstance(g.get("score"), (int, float))]
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


def build_run_report(db_path: str, out_dir: str, run_id: str | None = None) -> list:
    """run 1개당 종합 HTML 1개(U4): 표지·개선 흐름도·세대별 스텝 블록·최종 후보·안전 문구.
    loop_runs.db SELECT-only · 오프라인 · 무script(인라인 SVG). 생성 파일 경로 리스트 반환."""
    import sqlite3
    from datetime import datetime, timezone
    from ai_strategy_loop.dashboard.report_writer import _atomic_write, _sha256  # noqa: PLC0415
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    written: list = []
    try:
        runs = conn.execute("SELECT run_id, started_at, status, best_gen, best_score, finished_at FROM runs"
                            + (" WHERE run_id = ?" if run_id else ""),
                            ((run_id,) if run_id else ())).fetchall()
        for (rid, started, status, best_gen, best_score, finished) in runs:
            rows = conn.execute(
                "SELECT gen_no, buy_name, sell_name, status, score, mdd, profit, trade_count, gate_passed, reason, strategy_gist "
                "FROM generations WHERE run_id = ? ORDER BY gen_no", (rid,)).fetchall()
            gens = [dict(zip(["gen_no", "buy", "sell", "status", "score", "mdd", "profit", "trades", "gate_passed", "reason", "gist"], r)) for r in rows]
            fmt_ts = lambda t: (datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if isinstance(t, (int, float)) and t and t > 1e9 else "—")
            blocks = []
            for g in gens:
                blocks.append(
                    f'<section style="border:1px solid #dde;border-radius:8px;padding:12px 16px;margin:10px 0">'
                    f'<h3>세대 {g["gen_no"]} {"· gate 통과 ✓" if g["gate_passed"] else ""}</h3>'
                    f'<p><b>조건식</b> 매수 {_esc(g["buy"])} · 매도 {_esc(g["sell"])}<br>'
                    f'<b>가설</b> {_esc(g["gist"] or "(미기재)")}</p>'
                    f'<p><b>백테 결과</b> score {_esc(g["score"])} · MDD {_esc(g["mdd"])} · profit {_esc(g["profit"])} · trades {_esc(g["trades"])}</p>'
                    f'<p><b>부검/다음 세대 반영</b> {_esc(g["reason"] or "(사유 미기재)")}</p>'
                    f'<p><a href="/reports/view?path=generated_reports/{_esc(rid)}__gen{g["gen_no"]}.html">세대 상세 스텝 리포트</a></p>'
                    "</section>")
            gate_n = sum(1 for g in gens if g["gate_passed"])
            html_text = (
                '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
                f"<title>Run 종합 보고서 — {_esc(rid)}</title>"
                "<style>body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:980px;margin:0 auto;padding:24px;color:#1a2028;line-height:1.6}"
                "h1{font-size:22px;border-bottom:2px solid #2a3441;padding-bottom:8px}h2{font-size:16px;margin-top:26px;color:#0b5}"
                "dl{background:#f4f6f8;border:1px solid #dde;border-radius:8px;padding:12px 16px}dt{font-weight:600;color:#556}dd{margin:0 0 6px}"
                "footer{margin-top:30px;padding-top:12px;border-top:1px solid #dde;font-size:12px;color:#889}a{color:#06c}</style></head><body>"
                f"<h1>Run 종합 보고서 — {_esc(rid)}</h1>"
                f"<dl><dt>기간</dt><dd>{fmt_ts(started)} ~ {fmt_ts(finished)}</dd>"
                f"<dt>상태</dt><dd>{_esc(status)}</dd>"
                f"<dt>세대</dt><dd>{len(gens)}세대 · gate 통과 {gate_n}</dd>"
                f"<dt>best</dt><dd>gen {_esc(best_gen)} · score {_esc(best_score)}</dd></dl>"
                "<h2>1. 개선 흐름도</h2>" + _flow_svg(gens) +
                "<h2>2. 세대별 스텝 기록 (생성→백테스트→채점→부검→반영)</h2>" + ("".join(blocks) or "<p>(세대 없음)</p>") +
                "<h2>3. 안전·한계</h2><p>표본 내 지표 요약이며 성능 증명이 아닙니다(performance_proved=false). "
                "우승 후보의 운영 export 는 human 승인 절차와 분리되어 있으며 이 보고서는 어떤 승격 권한도 없습니다.</p>"
                f"<footer>생성 {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} · 원천 loop_runs.db(SELECT-only) · 읽기 전용(sandbox·CSP 서빙)</footer>"
                "</body></html>")
            fname = f"run_report_{rid}.html"
            full = os.path.join(out_dir, fname)
            _atomic_write(full, html_text)
            written.append({"path": fname, "sha256": _sha256(html_text), "bytes": len(html_text.encode('utf-8')), "run_id": rid})
        return written
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
        written = build_run_report(db, args.out_dir, args.run_report or None)
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
