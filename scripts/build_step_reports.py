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


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="스텝별 연구 리포트 오프라인 생성기(G5·G7)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--specs-json", help="리포트 spec 리스트 JSON 경로")
    src.add_argument("--from-loop-runs", nargs="?", const="", metavar="DB",
                     help="loop_runs.db 에서 세대별 스텝 리포트 자동 구성(기본 ai_strategy_loop/state/loop_runs.db)")
    ap.add_argument("--out-dir", default=_DEFAULT_OUT, help="HTML 출력 디렉터리(기본 docs/generated_reports)")
    ap.add_argument("--manifest", default=None, help="manifest 경로(기본 <out-dir>/manifest.json)")
    args = ap.parse_args(argv)

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
