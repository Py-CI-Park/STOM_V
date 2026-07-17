"""배치 워치독 CLI — run_dir 상태 보고 전용(자동 재시작 금지, WBS v3 P1-4).

runlab 계약(run_dir: pid.txt/heartbeat.txt/status.json/log.txt)을 검사해
RUNNING / STALLED / DEAD / EXITED / MISSING 판정을 한 줄씩 출력한다.
어떤 경우에도 프로세스를 죽이거나 재시작하지 않는다 — 재기동 결정은 사람 몫.

사용:
    python scripts/batch_watch.py <run_dir> [run_dir...] [--stall-sec 180] [--scan] [--json]

  --scan       준 경로를 부모로 보고, 바로 아래에서 status.json을 가진
               하위 디렉토리를 전부 검사한다(배치 묶음 폴더용).
  --stall-sec  심박 정체 임계(초, 기본 180) — 초과 시 STALLED.
  --json       기계용 json 배열 출력(대시보드/후속 도구 연동).

종료코드: 0=전부 정상(RUNNING 또는 exit_code=0 EXITED),
          2=문제 존재(STALLED/DEAD/MISSING/실패 EXITED). 보고 전용 그대로다.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_lab.runlab import contract, watchdog  # noqa: E402


def _collect_run_dirs(paths: Sequence[str], scan: bool) -> List[Path]:
    """검사 대상 수집 — --scan이면 부모 아래 status.json 보유 디렉토리 전개."""
    if not scan:
        return [Path(p) for p in paths]
    found: List[Path] = []
    for parent in paths:
        base = Path(parent)
        if not base.is_dir():
            found.append(base)  # 존재하지 않아도 MISSING으로 보고되게 남긴다.
            continue
        for child in sorted(base.iterdir()):
            if (child / contract.STATUS_FILE).is_file():
                found.append(child)
    return found


def _is_healthy(report: watchdog.RunReport) -> bool:
    """정상 기준: 구동 중이거나 exit_code=0으로 끝난 경우만."""
    if report.verdict == watchdog.VERDICT_RUNNING:
        return True
    return report.verdict == watchdog.VERDICT_EXITED and report.exit_code == 0


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="python scripts/batch_watch.py",
        description="runlab run_dir 상태 보고(자동 재시작 없음)")
    ap.add_argument("run_dirs", nargs="+", help="검사할 run_dir(복수 가능)")
    ap.add_argument("--stall-sec", type=float,
                    default=watchdog.DEFAULT_STALL_SEC,
                    help="심박 정체 임계(초, 기본 180)")
    ap.add_argument("--scan", action="store_true",
                    help="run_dirs를 부모 폴더로 보고 하위 run_dir 전개")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="json 배열로 출력")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    targets = _collect_run_dirs(args.run_dirs, args.scan)
    if not targets:
        print("검사 대상 run_dir 없음(--scan 부모 아래 status.json 미발견)")
        return 2
    reports = [watchdog.inspect_run(d, stall_sec=args.stall_sec)
               for d in targets]
    if args.as_json:
        print(json.dumps([dataclasses.asdict(r) for r in reports],
                         ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(watchdog.format_report(report))
    return 0 if all(_is_healthy(r) for r in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
