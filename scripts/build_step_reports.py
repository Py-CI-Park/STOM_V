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

from ai_strategy_loop.dashboard.report_writer import render_report_html, write_reports  # noqa: E402

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




def _flow_svg(gens: list) -> str:
    """Return a deterministic, inert score-flow SVG from successful measurements."""
    scored = [g for g in gens if str(g.get("status") or "").lower() in {"ok", "success", "done", "complete"} and isinstance(g.get("score"), (int, float))]
    if not scored:
        return ""
    width, height, pad = 760, 220, 34
    x_values, y_values = [g["gen_no"] for g in scored], [g["score"] for g in scored]
    x0, x1, y0, y1 = min(x_values), max(x_values), min(y_values), max(y_values)
    x1 = x1 if x1 != x0 else x0 + 1
    y1 = y1 if y1 != y0 else y0 + 1
    x = lambda value: pad + (value - x0) / (x1 - x0) * (width - 2 * pad)
    y = lambda value: height - pad - (value - y0) / (y1 - y0) * (height - 2 * pad)
    points = " ".join(f"{x(g['gen_no']):.1f},{y(g['score']):.1f}" for g in scored)
    circles = "".join(
        f'<circle cx="{x(g["gen_no"]):.1f}" cy="{y(g["score"]):.1f}" r="{"5" if g.get("gate_passed") else "3.5"}" fill="{"#087f5b" if g.get("gate_passed") else "#8892a6"}"><title>gen {g["gen_no"]} · score {g["score"]}</title></circle>'
        for g in scored
    )
    return f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="세대별 score 개선 흐름도"><text x="{pad}" y="18" font-size="12">score 개선 흐름</text><polyline points="{points}" fill="none" stroke="#087f5b" stroke-width="2"/>{circles}</svg>'

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
            generation_rows = [
                [
                    g.get("gen_no"), "통과" if g.get("gate_passed") else "실패",
                    g.get("parent_gen") if g.get("parent_gen") is not None else "—",
                    g.get("score"), g.get("mdd"), g.get("profit"), g.get("profit_pct"),
                    g.get("trades"), _hypothesis_summary(g.get("hypotheses_json") or g.get("gist")),
                    g.get("reason") or "(사유 미기재)",
                ]
                for g in gens
            ]
            measured = [
                g for g in gens
                if str(g.get("status") or "").lower() in {"ok", "success", "done", "complete"}
                and isinstance(g.get("score"), (int, float))
            ]
            excluded_measurements = len(gens) - len(measured)
            average_score = (
                sum(float(g["score"]) for g in measured) / len(measured)
                if measured else None
            )
            gate_n = sum(1 for g in gens if g["gate_passed"])
            lineage_n = sum(1 for g in gens if g.get("parent_gen") is not None)
            evidence.update({"generations": len(gens), "lineage_links": lineage_n, "gate_passed": gate_n})
            availability = evidence.get("availability", {})
            evidence_kpis = {
                key: availability.get(key, "unavailable") if value is None else value
                for key, value in evidence.items() if key != "availability"
            }
            if status != "complete":
                decision = f"run 상태가 {status or 'unknown'}이므로 승격·성과 결론을 금지하고 원인 검토가 필요합니다."
            elif gate_n == 0:
                decision = "gate 통과 후보가 없어 승격할 수 없습니다. 실패 근거를 다음 연구 가설로 연결해야 합니다."
            else:
                decision = f"gate 통과 {gate_n}건이 있으나 표본 내 결과입니다. human review와 OOS 검증 전 승격할 수 없습니다."
            limitations = [
                "표본 내 지표이며 성능 증명이 아님",
                f"성과 집계 제외: {excluded_measurements}건 (실패·측정 누락)",
                "human review와 운영 export는 별도 경계",
                "profile hash가 다른 run의 단순 delta 비교 금지",
            ]
            report_spec = {
                "title": f"Run 종합 보고서 — {rid}",
                "research_id": rid, "run_id": rid, "step_id": "run",
                "status": status or "unknown", "provenance": "ai_strategy_loop/state/loop_runs.db (SELECT-only)",
                "trust": "derived", "source_sha256": source_sha256, "template_id": "quant_research",
                "executive_summary": f"기간 {fmt_ts(started)} ~ {fmt_ts(finished)} · 상태 {status or 'unknown'}",
                "kpis": {
                    "세대": len(gens),
                    "GATE 통과": gate_n,
                    "BEST GEN": best_gen,
                    "BEST SCORE": best_score,
                    "평균 score": f"{average_score:.2f}" if average_score is not None else "unavailable",
                },
                "profile": profile, "evidence": evidence, "decision": decision, "limitations": limitations,
                "blocks": [
                    {"type": "table", "id": "sec-profile", "title": "실행 프로파일", "columns": ["설정", "값"], "rows": [[key, value] for key, value in profile.items()] or [["공개 가능한 실행 설정", "없음"]]},
                    {"type": "kpis", "id": "sec-evidence", "title": "근거·비용·검증 자산", "values": evidence_kpis},
                    {"type": "svg", "id": "sec-flow", "title": "다중 세대 개선 흐름도", "svg": _flow_svg(gens)},
                    {"type": "table", "id": "sec-gens", "title": "세대별 스텝 기록 (생성→백테스트→채점→부검→반영)", "columns": ["세대", "gate", "부모", "score", "MDD", "profit", "return", "trades", "가설", "부검/다음 반영"], "rows": generation_rows},
                    {"type": "decision", "id": "sec-conclusion", "title": "결론·다음 행동", "text": decision, "page_break": True},
                    {"type": "limitations", "id": "sec-safety", "title": "안전·한계", "items": limitations},
                ],
                "toc": [
                    {"id": "sec-profile", "label": "실행 프로파일"}, {"id": "sec-evidence", "label": "근거·비용·검증 자산"},
                    {"id": "sec-flow", "label": "개선 흐름도"}, {"id": "sec-gens", "label": "세대별 스텝 기록"},
                    {"id": "sec-conclusion", "label": "결론·다음 행동"}, {"id": "sec-safety", "label": "안전·한계"},
                ],
            }
            fname = f"run_report_{rid}.html"
            rendered.append((report_spec, fname, render_report_html(report_spec), "run"))
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
