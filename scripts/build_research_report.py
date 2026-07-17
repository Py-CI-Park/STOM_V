"""탭형 연구 리포트 HTML 생성 CLI — 단일 자가완결 파일.

사용: STOM_ALLOW_MINIMAL_SETTING=1 python scripts/build_research_report.py [--commit <hash>]
산출: docs/research/condition_research/reports/research_lab_report.html
원본 read-only(판정 json·원장·strategy.db) · 엔진 0회 · git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.reporting.build_html import build_all  # noqa: E402

_DEFAULT_OUT = _REPO / "docs/research/condition_research/reports"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="계층형 연구 리포트 HTML 생성(허브 + 상세 11)")
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT),
                    help="reports/ 디렉토리(허브 + research/<id>.html 생성)")
    ap.add_argument("--commit", default=None, help="생성 커밋 해시(미지정=미기록 — git 호출 금지)")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    files = build_all(commit=args.commit)
    total = 0
    for rel, html_text in files.items():
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html_text, encoding="utf-8")
        total += len(html_text.encode("utf-8"))
    print(f"[REPORT] {out_dir} · 파일 {len(files)}개(허브 1 + 상세 {len(files)-1}) · "
          f"총 {total:,} bytes · commit={args.commit or '미기록'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
