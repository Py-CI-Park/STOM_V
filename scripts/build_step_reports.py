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
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_strategy_loop.dashboard.report_writer import write_reports  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_OUT = os.path.join(_REPO_ROOT, "docs", "generated_reports")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="스텝별 연구 리포트 오프라인 생성기(G5·G7)")
    ap.add_argument("--specs-json", required=True, help="리포트 spec 리스트 JSON 경로")
    ap.add_argument("--out-dir", default=_DEFAULT_OUT, help="HTML 출력 디렉터리(기본 docs/generated_reports)")
    ap.add_argument("--manifest", default=None, help="manifest 경로(기본 <out-dir>/manifest.json)")
    args = ap.parse_args(argv)

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
