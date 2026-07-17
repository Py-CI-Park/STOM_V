# -*- coding: utf-8 -*-
"""매도식 D1 측정 CLI — 봉인 bd5bb3c4 §14 이행.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/sell_d1_measure.py --phase gate
  ... --phase run [--days 20220517 ...]     # 재현 게이트 + ablation (체크포인트)
  ... --phase spot                          # full-mask 스팟 가드
  ... --phase judge                         # 절별 Δ·FDR·판정·리포트
  ... --phase all
전 창 run 은 분리 러너(detached_runner)로 기동한다(SOP-M). 원장 type-b 기입은
메인 세션이 discipline.ledger 단일 경로로 수행(판정 후).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_lab.sell_clause_lab import judge_s, measure  # noqa: E402

_RUN_DIR = (_REPO / "docs" / "research" / "condition_research"
            / "research_runs" / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "sell_d1"
_DEFAULT_BANK = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_GITIGNORE = "parts/\n*.parquet\n*progress.txt\nrun_ctl/\n*.log\n"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="매도식 D1 절-단위 ablation")
    ap.add_argument("--phase", choices=("gate", "run", "spot", "judge", "all"),
                    default="all")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--bank", default=str(_DEFAULT_BANK))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--days", nargs="*", default=None,
                    help="스모크/부분 실행 일자(YYYYMMDD). 미지정=발견창 전체")
    ap.add_argument("--spot-n", type=int, default=200)
    ap.add_argument("--engine", choices=("vector", "pure"), default="vector")
    ap.add_argument("--commit", default="미기록")
    return ap.parse_args(argv)


def _ensure_out(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    gi = out_dir / ".gitignore"
    if not gi.exists():
        gi.write_text(_GITIGNORE, encoding="utf-8")


def main(argv=None) -> int:
    args = parse_args(argv)
    out = Path(args.out_dir)
    _ensure_out(out)

    fp = measure.check_bank_fingerprint(args.bank)
    print(f"[GATE] bank sha_match={fp['sha_match']} rows={fp['rows']:,} "
          f"labeled={fp['labeled']:,} → gate_pass={fp['gate_pass']}")
    if not fp["gate_pass"]:
        print("[ABORT] 은행 지문 불일치 — §4 재검증 경로 필요")
        return 2
    if args.phase == "gate":
        return 0

    bank = measure.load_bank(args.bank)
    run_summary = None
    if args.phase in ("run", "all"):
        rs = measure.run_days(bank, args.db_dir, out, days=args.days,
                              engine=args.engine)
        run_summary = measure.consolidate(out)
        print(f"[RUN] days={rs['days_done']}/{rs['days_total']} "
              f"rows={run_summary['rows']:,} fired={run_summary['fired_rows']:,}")

    spot = None
    if args.phase in ("spot", "all"):
        spot = measure.fullmask_spot(bank, args.db_dir, n_sample=args.spot_n,
                                     engine=args.engine)
        print(f"[SPOT] full-mask n={spot['n_sample']} cap={spot['forced_cap']} "
              f"leak={spot['leaked_fire']} → gate_pass={spot['gate_pass']}")
        if not spot["gate_pass"]:
            print("[ABORT] full-mask 누출 — 하니스 결함 의심(§14-F2)")
            return 2

    if args.phase in ("judge", "all"):
        import pandas as pd
        deltas_path = out / "sell_d1_deltas.parquet"
        if not deltas_path.exists():
            measure.consolidate(out)
        deltas = pd.read_parquet(deltas_path)
        if run_summary is None:
            run_summary = json.loads(
                (out / "sell_d1_run_summary.json").read_text(encoding="utf-8"))
        judgment = judge_s.judge_all(deltas)
        judge_s.write_outputs(out, judgment, run_summary, spot,
                              commit=args.commit)
        print(f"[JUDGE] 정식 {len(judgment['formal_clauses'])}절 · "
              f"제거-개선 {judgment['removal_candidates'] or '없음'} · "
              f"load-bearing {judgment['load_bearing'] or '없음'} · "
              f"kill1={judgment['kill1_local_optimum']} · "
              f"sanity={judgment['sanity_flat_tripped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
