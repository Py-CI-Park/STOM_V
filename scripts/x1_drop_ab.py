"""X1 매수식 역생산 절 삭제 엔진 A/B CLI — 봉인본 cb8a9d6a §4·§6·§7·§8·§14.

phase 분리:
  variants = 원문(348c5181) 로드 → 후보 4 변형 생성·bit-diff·컴파일·sha → buy.txt + variants_report.json. **엔진 0.**
  register = scratch strategy.db 복사 + 변형 4종 등록(실 DB 미접촉). run phase 전제.
  run      = claude_candidate_batch_eval 배치(연도별) — B 런 metrics 산출·체크포인트. **메인 세션 전용**(measure_gate 후 분리 러너).
  judge    = 기준 A(B1 A_2022/A_2023 재사용) + B metrics → C1~C4 판정 → summary.json + report.md.
  all      = variants → register → run → judge.

산출: research_runs/alpha_restart_20260710/x1/ (.gitignore 5줄 선생성 — parquet·parts·progress·run_ctl·log git 제외).
git 커밋은 메인 몫. 원본 read-only. STOM_ALLOW_MINIMAL_SETTING=1.

사용(변형 생성만 — 엔진 0):
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/x1_drop_ab.py --phase variants
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.x1lab import judge_x1, orchestrate, variants  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "x1"
_DEFAULT_DB = _REPO / "_database" / "strategy.db"
_DEFAULT_A_DIR = _RUN_DIR / "d5r_b1_live"      # B1 A_2022/A_2023 재사용(기준 A).
_SCRATCH = Path(r"C:\Temp\claude\C--System-Trading-STOM-STOM-V-wt-alpha"
                r"\f12d90e9-de14-41e1-89a7-5a5a21c801fb\scratchpad\x1_scratch_strategy.db")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, obj) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def _ensure_gitignore(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\nrun_ctl/\n*.log\n", encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="X1 매수 절 삭제 엔진 A/B")
    ap.add_argument("--phase", choices=("variants", "register", "run", "judge", "all"),
                    default="variants")
    ap.add_argument("--db", default=str(_DEFAULT_DB))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--a-dir", default=str(_DEFAULT_A_DIR))
    ap.add_argument("--base-config", default=None,
                    help="A 런과 동일한 base 엔진 config(연도창만 덮어씀, §14-F8)")
    ap.add_argument("--loop-runs-db", default=None, help="run phase 산출 loop_runs.db")
    ap.add_argument("--run-id-prefix", default="x1_drop_ab")
    ap.add_argument("--smoke", action="store_true")
    return ap.parse_args(argv)


def run_variants(args) -> dict:
    """후보 4 변형 생성·검증·buy.txt 산출 (엔진 0)."""
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    txt = variants.champion_buy_text(args.db)
    results = variants.generate_all(txt)
    report = {
        "kind": "x1_variants_report",
        "champion_buy_sha256": variants.sha256_of(txt),
        "candidates": {},
    }
    vdir = out_dir / "variants"
    vdir.mkdir(parents=True, exist_ok=True)
    for cand, r in results.items():
        fpath = vdir / f"{variants.strategy_name(cand)}.buy.txt"
        fpath.write_text(r.text, encoding="utf-8", newline="")
        report["candidates"][cand] = {
            "strategy_name": variants.strategy_name(cand),
            "clause": variants.CANDIDATE_META[cand]["clause"],
            "kind": variants.CANDIDATE_META[cand]["kind"],
            "branch": variants.CANDIDATE_META[cand]["branch"],
            "buy_variant_sha256": r.sha256,
            "compile_ok": r.compile_ok,
            "removed_lines": [l.strip() for l in r.removed_lines],
            "added_lines": [l.strip() for l in r.added_lines],
            "buy_txt": str(fpath),
        }
    _dump(out_dir / "x1_variants_report.json", report)
    for cand, c in report["candidates"].items():
        print(f"[VARIANTS] {cand} {c['strategy_name']} sha={c['buy_variant_sha256'][:12]} "
              f"compile={c['compile_ok']} -Δ{len(c['removed_lines'])}/+{len(c['added_lines'])}")
    return report


def run_register(args) -> dict:
    """scratch DB 복사 + 변형 등록(실 DB 미접촉). run phase 전제 — 엔진 0."""
    txt = variants.champion_buy_text(args.db)
    results = variants.generate_all(txt)
    # 원본 매도(8ef01e0e) 텍스트 로드(등록 쌍 sell 미러).
    import sqlite3
    con = sqlite3.connect(f"file:{Path(args.db).as_posix()}?mode=ro", uri=True)
    try:
        sell_text = con.execute('SELECT "전략코드" FROM stocksell WHERE "index"=?',
                                (orchestrate.SELL_NAME,)).fetchone()[0]
    finally:
        con.close()
    prep = orchestrate.prepare_scratch_db(args.db, _SCRATCH)
    reg = orchestrate.register_variants(_SCRATCH, results, champion_sell_text=sell_text)
    out = {"kind": "x1_register", "scratch_prep": prep, "register": reg}
    _dump(Path(args.out_dir) / "x1_register_report.json", out)
    print(f"[REGISTER] scratch={prep['scratch_db']} sell_sha_ok={prep['sell_sha_ok']} "
          f"inserted={reg['inserted']}")
    return out


def run_judge(args) -> dict:
    """기준 A(B1) + B metrics → 판정. B metrics 부재 시 안내(run phase 선행 필요)."""
    a_dir = Path(args.a_dir)
    A_by_year = {}
    for yr in judge_x1.YEARS:
        p = a_dir / f"A_{yr}.json"
        if p.exists():
            A_by_year[yr] = json.loads(p.read_text(encoding="utf-8"))
    B_dir = Path(args.out_dir) / "b_metrics"
    B_by_cand = {}
    for cand in variants.CANDIDATES:
        B_by_cand[cand] = {}
        for yr in judge_x1.YEARS:
            bp = B_dir / f"B_{cand}_{yr}.json"
            if bp.exists():
                B_by_cand[cand][yr] = json.loads(bp.read_text(encoding="utf-8"))
    have_b = any(B_by_cand[c].get(yr) for c in variants.CANDIDATES for yr in judge_x1.YEARS)
    if not have_b:
        print("[JUDGE] B metrics 부재 — run phase(메인 세션 엔진 A/B) 선행 필요. 판정 생략.")
        return {"status": "no_b_metrics"}
    # 변형 sha(리포트 메타).
    vtxt = variants.champion_buy_text(args.db)
    vres = variants.generate_all(vtxt)
    vsha = {variants.strategy_name(c): vres[c].sha256 for c in variants.CANDIDATES}
    summary = judge_x1.judge_all(A_by_year, B_by_cand, variant_sha=vsha, smoke=args.smoke)
    _dump(Path(args.out_dir) / "x1_summary.json", summary)
    _write(Path(args.out_dir) / "x1_report.md", judge_x1.render_report(summary))
    print(f"[JUDGE] X1 후보 {summary['n_x1_candidates']} · 식붕괴 {summary['formula_collapse']} · "
          f"kill1(대칭)={summary['kill1_no_x1_candidate']}")
    return summary


def run_engine_phase(args) -> dict:
    """엔진 A/B(배치) — 본 스크립트에서 실행 금지. 메인 세션이 measure_gate 후 분리 러너로.

    조립 산출물(pairs.json·연도 config·배치 명령·인자 대조)만 만들어 두고 중단한다.
    """
    out_dir = Path(args.out_dir)
    pairs = orchestrate.build_pairs_json()
    _dump(out_dir / "x1_pairs.json", pairs)
    plan = {"kind": "x1_run_plan", "pairs": pairs,
            "year_windows": {str(y): list(w) for y, w in orchestrate.YEAR_WINDOWS.items()},
            "sell_fixed": orchestrate.SELL_NAME,
            "note": "엔진 실행은 메인 세션(measure_gate 후 분리 러너). base-config 필요 시 "
                    "build_year_config 로 연도창 덮어씀 + arg_parity_check(§14-F8)."}
    if args.base_config:
        for yr in orchestrate.YEAR_WINDOWS:
            cfg = orchestrate.build_year_config(args.base_config, yr)
            _dump(out_dir / f"x1_config_{yr}.json", cfg)
            plan.setdefault("configs", {})[str(yr)] = str(out_dir / f"x1_config_{yr}.json")
    _dump(out_dir / "x1_run_plan.json", plan)
    print("[RUN] 조립만 완료(pairs·plan). 엔진 실행 금지 — 메인 세션 분리 러너로 기동.")
    return plan


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.phase in ("variants", "all"):
        run_variants(args)
    if args.phase in ("register", "all"):
        run_register(args)
    if args.phase in ("run", "all"):
        run_engine_phase(args)
    if args.phase in ("judge", "all"):
        run_judge(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
