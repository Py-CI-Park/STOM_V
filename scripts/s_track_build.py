"""S-트랙 통계 지도 파일럿 빌드 + W4-2a 게이트 실행 스크립트(연구 전용).

사전등록: docs/research/condition_research/plans/2026-07-10_s_track_preregistration.md
원본 tick DB는 read-only(URI mode=ro), 엔진 백테 0회. stats_map.db는 커밋 금지
(.gitignore *.db 자동 생성). 산출: stats_map.db + w4_pilot_summary.json.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_build.py \
      [--start 20220323] [--end 20220531] [--db-dir _database] \
      [--out <stats_map.db>] [--workspace <scratchpad>] [--build-id <id>]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.stats_map import builder, config, gates, report  # noqa: E402
_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710" / "stats_map")
_DEFAULT_OUT = _RUN_DIR / "stats_map.db"


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="S-트랙 통계 지도 파일럿 빌드")
    ap.add_argument("--start", default="20220323")
    ap.add_argument("--end", default="20220531")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--out", default=str(_DEFAULT_OUT))
    ap.add_argument("--workspace", default=None,
                    help="일별 추출 npz 체크포인트 디렉토리(기본 scratchpad)")
    ap.add_argument("--build-id", default=None)
    return ap.parse_args(argv)


def _write_gitignore(out_path: Path) -> None:
    """stats_map/.gitignore(*.db) 생성 — DB는 어떤 경우에도 커밋 금지."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    (out_path.parent / ".gitignore").write_text("*.db\n", encoding="utf-8")


def run_gates(result: Dict[str, object], db_dir: str, start: str, end: str,
              workspace: Path) -> Dict[str, object]:
    """4종 게이트 실행 — 재추출 대조는 첫 일자로 수행."""
    sample = result["sample"]  # type: ignore[index]
    built = result["built"]    # type: ignore[index]
    dates = builder.iter_pilot_dates(db_dir, start, end)
    first_date, first_path = dates[0]
    reextract = {"db_path": first_path, "date": first_date,
                 "npz_path": workspace / f"extract_{first_date}.npz"}
    return {
        "reproducibility": gates.gate_reproducibility(
            sample, result["summary_sha"], reextract),  # type: ignore[index]
        "sanity": gates.gate_sanity(sample),
        "censor": gates.gate_censor(built["cells"]["cells_l0"]),  # type: ignore[index]
        "cost_parity": gates.gate_cost_parity(first_path, first_date, 1000),
    }


def build_summary(result: Dict[str, object], gate_report: Dict[str, object],
                  meta: Dict[str, object]) -> Dict[str, object]:
    """w4_pilot_summary.json 페이로드 조립(빌드·게이트·분석 뷰)."""
    sample = result["sample"]      # type: ignore[index]
    l0 = result["built"]["cells"]["cells_l0"]   # type: ignore[index]
    l1 = result["built"]["cells"]["cells_l1"]   # type: ignore[index]
    return {
        "build": meta,
        "gates": gate_report,
        "counts": _counts(sample),
        "analysis": _analysis(l0, l1),
        "corr_matrix": result["built"]["corr"],  # type: ignore[index]
    }


def _counts(sample: Dict[str, np.ndarray]) -> Dict[str, object]:
    """L0 후보·L1 온셋 규모(연도별 포함)."""
    onset = sample["is_onset"].astype(bool)
    years = np.unique(sample["year"])
    by_year = {int(y): {"l0": int((sample["year"] == y).sum()),
                        "l1": int(onset[sample["year"] == y].sum())}
               for y in years}
    l0 = int(sample["off"].size)
    l1 = int(onset.sum())
    return {"l0_candidates": l0, "l1_onsets": l1,
            "onset_pct": round(100.0 * l1 / max(l0, 1), 3), "by_year": by_year}


def _analysis(l0, l1) -> Dict[str, object]:
    """양축·주요 지평(h300)의 상하위·함정·양EV·L0대L1 뷰."""
    out: Dict[str, object] = {}
    for axis in config.AXIS_SETS:
        sel0 = report.select(l0, axis_set=axis, h=300)
        out[axis] = {
            "pooled_mean_net_h300": report.pooled_mean_net(l0, axis_set=axis, h=300),
            "n_judged_cells": len(sel0),
            "top_bottom": report.top_bottom(sel0),
            "positive_ev": report.positive_ev(sel0),
            "ci_positive": report.ci_positive(sel0),
            "trap_cells": report.trap_cells(sel0),
            "l0_vs_l1": report.l0_vs_l1(l0, l1, axis_set=axis, h=300),
        }
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    workspace = Path(args.workspace) if args.workspace else _default_workspace()
    build_id = args.build_id or f"pilot_{args.start}_{args.end}"
    out_path = Path(args.out)
    _write_gitignore(out_path)
    result = builder.build_pilot(
        args.db_dir, args.start, args.end,
        db_path=out_path, workspace=workspace, build_id=build_id)
    gate_report = run_gates(result, args.db_dir, args.start, args.end, workspace)
    meta = {
        "build_id": build_id, "date_start": args.start, "date_end": args.end,
        "input_files": result["input_files"], "row_count": result["row_count"],
        "param_sha": result["param_sha"], "summary_sha": result["summary_sha"],
        "db_path": str(out_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    summary = build_summary(result, gate_report, meta)
    summary_path = out_path.parent.parent / "w4_pilot_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8")
    _print_gate_digest(meta, gate_report, summary["counts"])
    print(f"summary -> {summary_path}")
    return 0


def _default_workspace() -> Path:
    """일별 추출 npz 체크포인트 기본 위치(시스템 임시 — 저장소 밖·커밋 대상 아님)."""
    return Path(tempfile.gettempdir()) / "s_track_extract"


def _print_gate_digest(meta, gate_report, counts) -> None:
    print("=== S-트랙 파일럿 빌드 ===")
    print(f"입력 파일 {meta['input_files']}일  표본(L0) {meta['row_count']:,}")
    print(f"summary_sha {meta['summary_sha'][:16]}  param_sha {meta['param_sha']}")
    print(f"L0 {counts['l0_candidates']:,}  L1 {counts['l1_onsets']:,}"
          f"  온셋 {counts['onset_pct']}%")
    for name, rep in gate_report.items():
        print(f"[{'PASS' if rep['passed'] else 'FAIL'}] {name}: "
              f"{_gate_note(name, rep)}")


def _gate_note(name: str, rep: Dict[str, object]) -> str:
    if name == "reproducibility":
        return f"sha_match={rep['sha_match']} extract_match={rep['extract_match']}"
    if name == "sanity":
        return f"L0 mean_net h300={rep['l0_mean_net_h300']:.5f}"
    if name == "censor":
        return f"early_max={rep['early_bucket_max_censor']} overall={rep['overall_censor_pct']}"
    if name == "cost_parity":
        return f"max_err={rep['max_err']} n={rep['n_pairs']}"
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
