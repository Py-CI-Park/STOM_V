"""research_assets 카탈로그 빌드 CLI — WBS v3 P0 (계획 §3, 2026-07-12).

산출(둘 다 run 디렉토리):
  research_assets.db                  카탈로그 DB(git 제외 — .gitignore 자동 보장)
  research_assets_build_receipt.json  빌드 영수증(테이블별 건수·원천 sha256·누락/스킵)

원칙: 원본 파일이 정본, DB는 카탈로그+요약 계층 — 언제든 본 CLI로 재생성 가능.
원천은 전부 read-only 접근(엔진 백테 0회·신규 데이터 수집 0회·git 미호출).

사용:
  python scripts/build_research_catalog.py
  python scripts/build_research_catalog.py --run-dir <경로> [--db <경로>] [--receipt <경로>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from alpha_lab.catalog.builder import build_all  # noqa: E402

_DEFAULT_RUN = (_ROOT / "docs" / "research" / "condition_research"
                / "research_runs" / "alpha_restart_20260710")


def _parse_args(argv) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="research_assets 카탈로그 빌드")
    ap.add_argument("--run-dir", default=str(_DEFAULT_RUN),
                    help="연구 run 디렉토리(기본: alpha_restart_20260710)")
    ap.add_argument("--db", default=None,
                    help="출력 DB 경로(기본: <run-dir>/research_assets.db)")
    ap.add_argument("--receipt", default=None,
                    help="영수증 경로(기본: <run-dir>/research_assets_build_receipt.json)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 방어
    args = _parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"[실패] run 디렉토리 없음: {run_dir}")
        return 2
    receipt = build_all(run_dir, db_path=args.db, receipt_path=args.receipt)
    print("=== research_assets 카탈로그 빌드 완료 ===")
    print(f"DB      : {receipt['db_path']}")
    print(f"생성시각: {receipt['generated_at']}")
    print("테이블별 적재 건수:")
    for table, count in receipt["table_counts"].items():
        print(f"  {table:14s} {count:6d}")
    print(f"원천 기록 {len(receipt['sources'])}건 / 누락 {len(receipt['missing'])}건"
          f" / 스킵 {len(receipt['skipped'])}건 / 노트 {len(receipt['notes'])}건")
    gi = receipt.get("gitignore") or {}
    print(f".gitignore: {gi.get('action', '?')} ({gi.get('path', '')})")
    if receipt["missing"]:
        print("누락 목록:")
        for m in receipt["missing"]:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
