"""D1 2절 교호작용 측정 CLI — 봉인본 §11·§14 (측정 착수 순서 봉인).

phase:
  gate  = §4 무결성 지문 대조 + §5 자격 게이트(비트 11열+연도만, L3 접촉 전) → gate_report.json.
  judge = §4-3 D1 재현 대조(L3) → 자격 짝 DiD 판정 → interaction_summary.json + report.md
          + 자격 짝 수만큼 n_trials(discipline.ledger.append_trial).
  all   = gate → judge.

§14 운영 봉인: 측정 코드 선커밋 → measure_gate → gate → judge. 게이트/판정 실행은 메인 세션.
지문 대조(read-only sha)만 --phase gate 로 스모크 허용(계수·L3 미접촉은 자격 게이트 이후 단계).
원본 read-only. 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from alpha_lab.clause_lab import pair_gate, pair_judge, pair_report  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_BANK = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_BITS = _RUN_DIR / "stats_map" / "d1_onset_clause_bits.parquet"
_DEFAULT_D1_SUMMARY = _RUN_DIR / "d1_clause_ablation_summary.json"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="D1 2절 교호작용 측정")
    ap.add_argument("--phase", choices=("gate", "judge", "all"), default="all")
    ap.add_argument("--bank", default=str(_DEFAULT_BANK))
    ap.add_argument("--bits", default=str(_DEFAULT_BITS))
    ap.add_argument("--d1-summary", default=str(_DEFAULT_D1_SUMMARY))
    ap.add_argument("--out-dir", default=str(_RUN_DIR))
    ap.add_argument("--ledger", default=None,
                    help="n_trials 원장 경로(judge 완료 시 append; 미지정=기본 원장, 스모크는 무시)")
    ap.add_argument("--smoke", action="store_true",
                    help="스모크 딱지 + n_trials 미기입")
    return ap.parse_args(argv)


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1,
                                   allow_nan=False), encoding="utf-8")


def run_gate(args) -> dict:
    integrity = pair_gate.check_integrity(args.bank, args.bits)
    if not integrity["all_match"]:
        report = pair_report.build_gate_report(integrity, {
            "kind": "d1_pairwise_qualification", "halted": True,
            "reason": "무결성 지문 불일치 — 재검증 전 자격 게이트 미실행(§4-2·kill-3)",
            "n_pairs_total": len(pair_gate.PAIRS), "n_qualified": 0,
            "fdr_denominator": 0, "qualified_pairs": [], "per_pair": {}})
        _write(Path(args.out_dir) / "d1_pairwise_gate_report.json", report)
        print(f"[GATE] integrity FAIL — bank sha_match={integrity['bank'].get('sha_match')} "
              f"bits sha_match={integrity['bits'].get('sha_match')}; 자격 게이트 미실행")
        return report
    qualification = pair_gate.qualification_gate(args.bits)
    report = pair_report.build_gate_report(integrity, qualification)
    _write(Path(args.out_dir) / "d1_pairwise_gate_report.json", report)
    print(f"[GATE] integrity PASS · 자격 짝 {qualification['n_qualified']}/{len(pair_gate.PAIRS)} "
          f"(FDR 분모={qualification['fdr_denominator']})")
    return report


def _load_labeled(bank_path, bits_path):
    """은행+비트(위치 조인) → 라벨된 (net_pp, days, years, bits{n:배열})."""
    bank = pd.read_parquet(bank_path, columns=["code", "day", "off", "t0", "year",
                                               "l3_net", "l3_labeled"])
    bit_cols = [f"bit_{n}" for n in pair_gate.USED_CLAUSES]
    bits = pd.read_parquet(bits_path, columns=["code", "day", "off", "t0"] + bit_cols)
    if bank.shape[0] != bits.shape[0]:
        raise SystemExit("은행/비트 행수 불일치(kill-3)")
    m = bank["l3_labeled"].to_numpy().astype(bool)
    net_pp = bank["l3_net"].to_numpy(dtype=np.float64)[m] * 100.0
    days = bank["day"].to_numpy(dtype=np.int64)[m]
    years = bank["year"].to_numpy(dtype=np.int64)[m]
    bit_map = {n: bits[f"bit_{n}"].to_numpy().astype(bool)[m] for n in pair_gate.USED_CLAUSES}
    return net_pp, days, years, bit_map


def run_judge(args, gate_report: dict) -> dict:
    repro = pair_gate.d1_reproduction_check(args.bank, args.bits, args.d1_summary)
    if not repro["pass"]:
        print(f"[JUDGE] D1 재현 대조 실패(max_err={repro['max_abs_err']:.2e} > 1e-6) — 중단(kill-3)")
        summary = pair_report.build_summary({"per_pair": {}, "n_qualified": 0,
                                             "fdr_denominator": 0}, gate_report, repro)
        _write(Path(args.out_dir) / "d1_pairwise_interaction_summary.json", summary)
        return summary
    qualified_ids = gate_report["qualification"]["qualified_pairs"]
    per_pair_meta = gate_report["qualification"]["per_pair"]
    qualified = [(per_pair_meta[pid]["a"], per_pair_meta[pid]["b"]) for pid in qualified_ids]
    net_pp, days, years, bits = _load_labeled(args.bank, args.bits)
    judgment = pair_judge.judge_all_pairs(qualified, net_pp, days, years, bits)
    summary = pair_report.build_summary(judgment, gate_report, repro)
    _write(Path(args.out_dir) / "d1_pairwise_interaction_summary.json", summary)
    _write(Path(args.out_dir) / "d1_pairwise_interaction_report.md",
           pair_report.render_report(summary, smoke=args.smoke))
    n_appended = 0
    if not args.smoke:
        n_appended = pair_report.append_n_trials(args.ledger, judgment)
    verdict = ("kill-1(미검출)" if judgment["kill1_no_interaction_detected"]
               else f"시너지 {len(judgment['synergy_pairs'])}·간섭 {len(judgment['interference_pairs'])}")
    print(f"[JUDGE] repro PASS · 자격 {judgment['n_qualified']}짝 · {verdict} · "
          f"n_trials_appended={n_appended}")
    return summary


def main(argv=None) -> int:
    args = parse_args(argv)
    gate_report = None
    if args.phase in ("gate", "all"):
        gate_report = run_gate(args)
    if args.phase in ("judge", "all"):
        if gate_report is None:
            gp = Path(args.out_dir) / "d1_pairwise_gate_report.json"
            if not gp.exists():
                raise SystemExit("gate_report 없음 — 먼저 --phase gate 를 실행하라")
            gate_report = json.loads(gp.read_text(encoding="utf-8"))
        if not gate_report["integrity"]["all_match"]:
            raise SystemExit("무결성 불일치 — judge 진입 금지(kill-3)")
        run_judge(args, gate_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
