"""S-트랙 통계 지도 본 적재(W4-3) — 발견 가용 창 전체 빌드 + 4종 게이트.

사전등록: docs/research/condition_research/plans/2026-07-10_s_track_preregistration.md
  §1 본 적재 창 = tick 2022-03-23 ~ 2023-12-31(발견 가용). 파일럿 창을 포함하므로
  "동일 창 포함 재빌드"로 파일럿 데이터를 자연 포섭한다(build_receipts에 명시).

파일럿 s_track_build.py와 동일 파이프라인(builder/gates/report 재사용, 봉인 스펙
불변). 차이만:
  - 본 적재 창 · build_id=main_<start>_<end>.
  - 일별 진행률을 w4_full_progress.txt에 기록(장시간 배치 관측·재시작 확인).
  - 재현성 스팟체크를 임의 3일 재추출로 확장(팀리드 요구).
  - 요약을 w4_full_build.json에 기록(파일럿 요약 w4_pilot_summary.json 보존).

원본 tick DB는 read-only(URI mode=ro), 엔진 백테 0회. stats_map.db는 커밋 금지.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_build_main.py \
      [--start 20220323] [--end 20231231] [--workspace C:/Temp/s_track_extract_main]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.stats_map import builder, config, gates, report  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "stats_map" / "stats_map.db"
_DEFAULT_PROGRESS = _RUN_DIR / "w4_full_progress.txt"
_DEFAULT_WORKSPACE = Path("C:/Temp/s_track_extract_main")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="S-트랙 통계 지도 본 적재")
    ap.add_argument("--start", default="20220323")
    ap.add_argument("--end", default="20231231")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--out", default=str(_DEFAULT_OUT))
    ap.add_argument("--workspace", default=str(_DEFAULT_WORKSPACE))
    ap.add_argument("--progress", default=str(_DEFAULT_PROGRESS))
    ap.add_argument("--build-id", default=None)
    return ap.parse_args(argv)


def _log(progress: Path, msg: str) -> None:
    """진행률 파일에 타임스탬프 줄 추가(즉시 flush)."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}  {msg}\n")
        fh.flush()


def extract_with_progress(dates: List[Tuple[str, Path]], workspace: Path,
                          progress: Path) -> List[Path]:
    """일별 추출(재시작 가능) — builder._extract_one 재사용 + 진행률 기록."""
    workspace.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    total = len(dates)
    cum_rows = 0
    for i, (date, db_path) in enumerate(dates, start=1):
        npz = workspace / f"extract_{date}.npz"
        cached = npz.exists()
        if not cached:
            builder._extract_one(date, db_path, npz)
        paths.append(npz)
        cum_rows += _npz_rowcount(npz)
        if i == 1 or i == total or i % 10 == 0 or not cached:
            _log(progress, f"extract {i}/{total} date={date} "
                 f"{'cache' if cached else 'new'} cum_L0={cum_rows:,}")
    _log(progress, f"extract DONE {total} days cum_L0={cum_rows:,}")
    return paths


def _npz_rowcount(npz: Path) -> int:
    """부분 영수증(.done.json)에서 그 일자 표본수 — 없으면 npz에서 직접."""
    done = npz.with_suffix(".done.json")
    if done.exists():
        try:
            return int(json.loads(done.read_text(encoding="utf-8"))["n"])
        except Exception:
            pass
    with np.load(npz) as data:
        return int(data["off"].size)


def reproducibility_3day(sample: Dict[str, np.ndarray], first_sha: str,
                         dates: List[Tuple[str, Path]], workspace: Path
                         ) -> Dict[str, object]:
    """sha 재조립 일치 + 임의 3일(첫·중간·끝) 재추출 배열 동일성."""
    sha2 = gates._sha(builder.build_all(sample))
    picks = _spot_dates(dates)
    day_checks = []
    for date, db_path in picks:
        npz = workspace / f"extract_{date}.npz"
        match = gates._reextract_match(
            {"db_path": db_path, "date": date, "npz_path": npz})
        day_checks.append({"date": date, "extract_match": bool(match)})
    return {
        "sha_build_1": first_sha, "sha_build_2": sha2,
        "sha_match": first_sha == sha2,
        "spot_days": day_checks,
        "passed": bool(first_sha == sha2)
        and all(c["extract_match"] for c in day_checks),
    }


def _spot_dates(dates: List[Tuple[str, Path]]) -> List[Tuple[str, Path]]:
    """첫·중간·끝 3일(비어있지 않은 결정론 표본)."""
    if len(dates) <= 3:
        return list(dates)
    return [dates[0], dates[len(dates) // 2], dates[-1]]


def run_gates(sample, built, first_sha, dates, workspace, db_dir) -> Dict:
    """재현성(3일)·sanity·절단·비용식 패리티 — 파일럿 게이트 재사용."""
    first_date, first_path = dates[0]
    return {
        "reproducibility": reproducibility_3day(
            sample, first_sha, dates, workspace),
        "sanity": gates.gate_sanity(sample),
        "censor": gates.gate_censor(built["cells"]["cells_l0"]),
        "cost_parity": gates.gate_cost_parity(first_path, first_date, 1000),
    }


def counts(sample: Dict[str, np.ndarray]) -> Dict[str, object]:
    """L0 후보·L1 온셋 규모(연도별 포함) — 파일럿 _counts 동형."""
    onset = sample["is_onset"].astype(bool)
    years = np.unique(sample["year"])
    by_year = {int(y): {"l0": int((sample["year"] == y).sum()),
                        "l1": int(onset[sample["year"] == y].sum())}
               for y in years}
    l0 = int(sample["off"].size)
    l1 = int(onset.sum())
    return {"l0_candidates": l0, "l1_onsets": l1,
            "onset_pct": round(100.0 * l1 / max(l0, 1), 3), "by_year": by_year}


def analysis(built: Dict[str, object]) -> Dict[str, object]:
    """양축·h300 상하위·함정·양EV·CI양·L0대L1 — 파일럿 _analysis 동형."""
    l0 = built["cells"]["cells_l0"]
    l1 = built["cells"]["cells_l1"]
    out: Dict[str, object] = {}
    for axis in config.AXIS_SETS:
        sel0 = report.select(l0, axis_set=axis, h=300)
        out[axis] = {
            "pooled_mean_net_h300": report.pooled_mean_net(l0, axis_set=axis, h=300),
            "pooled_mean_net_l1_h300": report.pooled_mean_net(l1, axis_set=axis, h=300),
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
    workspace = Path(args.workspace)
    progress = Path(args.progress)
    progress.parent.mkdir(parents=True, exist_ok=True)
    progress.write_text("", encoding="utf-8")  # 새 배치 진행률 초기화.
    build_id = args.build_id or f"main_{args.start}_{args.end}"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    (out_path.parent / ".gitignore").write_text("*.db\n", encoding="utf-8")

    _log(progress, f"START build_id={build_id} window={args.start}..{args.end}")
    dates = builder.iter_pilot_dates(args.db_dir, args.start, args.end)
    _log(progress, f"dates resolved: {len(dates)} tick DBs")
    npz_paths = extract_with_progress(dates, workspace, progress)

    _log(progress, "load_samples ...")
    sample = builder.load_samples(npz_paths)
    if not sample:
        _log(progress, "ABORT: empty sample")
        return 2
    _log(progress, f"build_all ... (L0={sample['off'].size:,})")
    built = builder.build_all(sample)
    meta = {
        "build_id": build_id, "date_start": args.start, "date_end": args.end,
        "input_files": len(dates), "row_count": int(sample["off"].size),
        "l1_onsets": int(sample["is_onset"].sum()),
    }
    _log(progress, "write_db ...")
    sha = builder.write_db(out_path, built, meta)
    _log(progress, f"write_db done summary_sha={sha[:16]}")

    _log(progress, "gates ...")
    gate_report = run_gates(sample, built, sha, dates, workspace, args.db_dir)
    payload = {
        "build": {
            "build_id": build_id, "date_start": args.start,
            "date_end": args.end, "input_files": len(dates),
            "row_count": meta["row_count"], "param_sha": config.param_sha(),
            "summary_sha": sha, "db_path": str(out_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": "본 적재 창은 파일럿 창(20220323-20220531)을 포함 — 동일 창 포함 재빌드",
        },
        "gates": gate_report,
        "counts": counts(sample),
        "analysis": analysis(built),
        "corr_matrix": built["corr"],
    }
    out_json = _RUN_DIR / "w4_full_build.json"
    out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8")
    _digest(payload)
    _log(progress, f"ALL DONE -> {out_json.name}  "
         f"gates={[k for k,v in gate_report.items() if v['passed']]}")
    print(f"build summary -> {out_json}")
    return 0


def _digest(payload: Dict[str, object]) -> None:
    b = payload["build"]
    c = payload["counts"]
    print("=== S-트랙 본 적재 ===")
    print(f"입력 {b['input_files']}일  L0 {c['l0_candidates']:,}  "
          f"L1 {c['l1_onsets']:,} ({c['onset_pct']}%)")
    print(f"summary_sha {b['summary_sha'][:16]}  param_sha {b['param_sha']}")
    for name, rep in payload["gates"].items():
        print(f"[{'PASS' if rep['passed'] else 'FAIL'}] {name}")


if __name__ == "__main__":
    raise SystemExit(main())
