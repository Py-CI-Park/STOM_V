"""ledger-lint CLI (백로그 A4) — known 창 접촉 문서 린터, **보고 전용**.

사용:
    python scripts/ledger_lint.py                 # 기본 코퍼스(plans + alpha_restart_20260710)
    python scripts/ledger_lint.py --json 경로.json # 결과 JSON 병행 저장(선택)
    python scripts/ledger_lint.py 파일_또는_디렉토리 ...  # 대상 지정

채택 조건(A4): 보고 전용 고정 — 차단(fail) 모드는 구현하지 않으며,
플래그가 있어도 exit code는 항상 0이다(내부 오류 제외). 합격 기준은
창-지위 원장 §6 위반 V-1(W3 known 2025 표본 접촉)의 재검출이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from alpha_lab.discipline import lint  # noqa: E402  (경로 부트스트랩 후 임포트)

DEFAULT_TARGETS = (
    _ROOT / "docs" / "research" / "condition_research" / "plans",
    _ROOT
    / "docs"
    / "research"
    / "condition_research"
    / "research_runs"
    / "alpha_restart_20260710",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="known 창 날짜의 측정 문맥 접촉 보고(차단 없음 — A4 보고 전용)"
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="스캔할 md 파일/디렉토리(생략 시 plans + alpha_restart_20260710)",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="스캔 결과를 JSON으로도 저장할 경로(선택)",
    )
    return parser


def main(argv=None) -> int:
    """스캔 → 보고 출력. 반환은 항상 0(보고 전용 — 차단 모드 없음)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # 콘솔 코드페이지 보호
    args = _build_parser().parse_args(argv)
    targets = [Path(t) for t in args.targets] if args.targets else list(DEFAULT_TARGETS)
    missing = [str(t) for t in targets if not Path(t).exists()]
    if missing:
        print(f"경고: 존재하지 않는 대상 제외 — {missing}")
        targets = [t for t in targets if Path(t).exists()]
    result = lint.scan_paths(targets)
    print(lint.render_report(result))
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"JSON 저장: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
