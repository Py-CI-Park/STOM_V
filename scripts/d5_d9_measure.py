"""D5 · D9 전이 온셋 × L3 출구 접목 측정 CLI — 봉인본 §11·§14.

phase 분리:
  r1  = 전이 온셋 추출(437일 루프, 일별 체크포인트·재시작) → d9_transition_bank.parquet
        + 패리티(§14-7)·재현(§4.2)·겹침(§8)·서브모집단 하한 R1 리포트.
  r3  = d9_transition_bank + 기존 onset_l3_bank(서지 기준선) → 3 서브모집단 Δ 판정.
  all = r1 → r3.

산출물은 research_runs/alpha_restart_20260710/d5_d9/ (파티션·parts 는 git 제외).
전 창 본 측정은 분리형 러너(메인 세션)가 기동한다 — 본 스크립트는 --days 스모크만 직접 실행 권장.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d5_d9_measure.py --phase r1 --days 20220517 --spot-days 20220517 --smoke
  (전 창은 메인 세션: python scripts/d5_d9_measure.py --phase all)
원본 tick DB read-only. 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import pandas as pd  # noqa: E402

from alpha_lab.clause_lab.bank import champion_sell_text, day_list  # noqa: E402
from alpha_lab.d9lab import overlap, report, run  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "d5_d9"
_DEFAULT_SURGE = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_STRATEGY = _REPO / "_database" / "strategy.db"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="D5 · D9 전이 온셋 × L3 접목 측정")
    ap.add_argument("--phase", choices=("r1", "r3", "all"), default="all")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--strategy-db", default=str(_DEFAULT_STRATEGY))
    ap.add_argument("--surge-bank", default=str(_DEFAULT_SURGE))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--days", nargs="*", default=None,
                    help="측정 일자(YYYYMMDD) 제한 — 스모크/부분 실행용. 미지정=발견창 전체")
    ap.add_argument("--spot-days", nargs="*", default=[],
                    help="재현 게이트(순수/벡터 L3)용 스팟 일자")
    ap.add_argument("--smoke", action="store_true",
                    help="스모크 관통 — 리포트에 스모크 딱지, 서지 기준선 일자 매칭, n_trials 미기입")
    ap.add_argument("--ledger", default=None,
                    help="n_trials 원장 경로(전 창 R3 완료 시에만 append; 스모크는 무시)")
    return ap.parse_args(argv)


def _resolve_days(db_dir: str, days):
    """--days 지정 시 발견창 목록에서 그 일자만; 미지정 시 전체."""
    full = day_list(db_dir)
    if not days:
        return full
    want = set(days)
    picked = [(d, p) for (d, p) in full if d in want]
    missing = want - {d for d, _ in picked}
    if missing:
        raise SystemExit(f"발견창에 없는 일자: {sorted(missing)}")
    return picked


def _pct(v) -> str:
    return "—" if v is None or (isinstance(v, float) and v != v) else f"{v * 100:.4f}%"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ensure_gitignore(out_dir: Path) -> None:
    """파티션·parts·진행 로그는 git 제외; json/md 리포트는 evidence 로 커밋 가능."""
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\n", encoding="utf-8")


def run_phase_r1(args, sell_text: str) -> dict:
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    parts_dir = out_dir / "parts"
    bank_path = out_dir / "d9_transition_bank.parquet"
    days = _resolve_days(args.db_dir, args.days)
    run.run_r1(args.db_dir, out_dir, parts_dir, sell_text,
               days=days, spot_days=args.spot_days)
    cons = run.consolidate_r1(parts_dir, bank_path)
    repro = run.spot_reproduction_check(parts_dir, args.spot_days) if args.spot_days \
        else {"spot_days": [], "reproduction_pass": None}
    ov = overlap.compute_overlap(pd.read_parquet(bank_path), args.surge_bank)
    summary = run.build_r1_summary(cons, ov, repro, days_measured=len(days))
    _write(out_dir / "d5_d9_r1_summary.json",
           json.dumps(summary, ensure_ascii=False, indent=1, allow_nan=False))
    _write(out_dir / "d5_d9_r1_report.md",
           report.render_r1_report(summary, smoke=args.smoke))
    print(f"[R1] days={len(days)} onsets={cons['n_onsets']} obs={cons['n_observable']} "
          f"parity={_pct(cons['parity_match_pct'])} gate={cons['parity_gate_pass']} "
          f"overlap±30={_pct(ov['primary_pooled_rate'])} -> {bank_path.name}")
    return summary


def run_phase_r3(args) -> dict:
    out_dir = Path(args.out_dir)
    bank_path = out_dir / "d9_transition_bank.parquet"
    r1_json = out_dir / "d5_d9_r1_summary.json"
    if not r1_json.exists():
        raise SystemExit("R1 summary 없음 — 먼저 --phase r1 을 실행하라")
    r1_summary = json.loads(r1_json.read_text(encoding="utf-8"))
    result = run.run_r3(bank_path, args.surge_bank, r1_summary["consolidate"],
                        match_surge_days=args.smoke)
    _write(out_dir / "d5_d9_r3_summary.json",
           json.dumps(result, ensure_ascii=False, indent=1, allow_nan=False))
    _write(out_dir / "d5_d9_r3_report.md",
           report.render_r3_report(result, smoke=args.smoke))
    n_appended = 0
    if not args.smoke and args.ledger:
        n_appended = report.append_n_trials(args.ledger, result)
    verdict = ("판정 정지" if not result["proceed_to_judgment"]
               else ("kill-4(구별 EV 없음)" if result["judgment"]["kill4_no_distinct"]
                     else f"구별 {result['judgment']['n_distinct']}건"))
    print(f"[R3] proceed={result['proceed_to_judgment']} verdict={verdict} "
          f"n_trials_appended={n_appended}")
    return result


def main(argv=None) -> int:
    args = parse_args(argv)
    sell_text = champion_sell_text(args.strategy_db)  # sha 봉인 검증(8ef01e0e).
    if args.phase in ("r1", "all"):
        run_phase_r1(args, sell_text)
    if args.phase in ("r3", "all"):
        run_phase_r3(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
