"""라벨 공장 실행기 — 설계 구간 일별 parquet 생성 (멱등·증분).

사용:
    python -m ai_strategy_loop.labeling.build_labels --start 20240304 --end 20250822

- 홀드아웃(20250825~)은 **기본 차단** — 규율 L2. `--allow-holdout` 없이는 만들지 않는다.
- 산출: ai_strategy_loop/state/labels/<lane>/day=YYYYMMDD.parquet (float32, snappy)
- 이미 있는 날은 건너뛴다(멱등). 실패한 날은 기록하고 계속 간다(전량 기록 규율).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import time

import pandas as pd

from ai_strategy_loop.labeling.label_factory import build_day_labels

_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_database")
_OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "state", "labels")
_HOLDOUT_START = 20250825


def _tick_days(start: int, end: int) -> list[int]:
    files = glob.glob(os.path.join(_DB_DIR, "stock_tick_2*.db"))
    days = sorted(int(os.path.basename(f)[11:19]) for f in files)
    return [d for d in days if start <= d <= end]


def _downcast(frame: pd.DataFrame) -> pd.DataFrame:
    for col in frame.columns:
        if frame[col].dtype == "float64":
            frame[col] = frame[col].astype("float32")
    return frame


def run(start: int, end: int, *, allow_holdout: bool = False, out_name: str = "design") -> dict:
    if end >= _HOLDOUT_START and not allow_holdout:
        raise SystemExit(
            f"홀드아웃({_HOLDOUT_START}~) 라벨 생성은 규율 L2 로 봉인되어 있다. "
            "M-5 검증 단계에서만 --allow-holdout 으로 해제한다."
        )
    out_dir = os.path.abspath(os.path.join(_OUT_DIR, out_name))
    os.makedirs(out_dir, exist_ok=True)
    days = _tick_days(start, end)
    done, skipped, failed = [], [], []
    t0 = time.time()
    for i, day in enumerate(days):
        target = os.path.join(out_dir, f"day={day}.parquet")
        if os.path.exists(target):
            skipped.append(day)
            continue
        try:
            frame = build_day_labels(os.path.join(_DB_DIR, f"stock_tick_{day}.db"), day=day)
            if frame.empty:
                failed.append({"day": day, "reason": "empty"})
                continue
            _downcast(frame).to_parquet(target, compression="snappy", index=False)
            done.append(day)
        except Exception as error:  # noqa: BLE001 — 실패도 전량 기록하고 계속 간다
            failed.append({"day": day, "reason": f"{type(error).__name__}: {error}"})
        if (i + 1) % 25 == 0:
            print(f"[{i + 1}/{len(days)}] done={len(done)} skip={len(skipped)} fail={len(failed)} "
                  f"{time.time() - t0:.0f}s", flush=True)
    summary = {
        "start": start, "end": end, "days": len(days), "done": len(done),
        "skipped": len(skipped), "failed": failed, "elapsed_sec": round(time.time() - t0, 1),
        "out_dir": out_dir,
    }
    with open(os.path.join(out_dir, "_build_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps({**summary, "failed": len(failed)}, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--allow-holdout", action="store_true")
    parser.add_argument("--out-name", default="design")
    args = parser.parse_args()
    run(args.start, args.end, allow_holdout=args.allow_holdout, out_name=args.out_name)


if __name__ == "__main__":
    main()
