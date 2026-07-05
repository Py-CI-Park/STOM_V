"""alpha_translate — 채택 리프 규칙 → STOM 매수식 번역 CLI.

사용: python -m cli.alpha_translate [--run-dir ...] [--mining-report ...]

흐름: 봉인 검증 → mining_report.json의 채택(adopted=true) 리프만 →
translate_leaf_rule(임계값 소수 1자리 반올림 봉인 + 시간 가드 + 정적 검증 +
저장소 생성 가드) → translation_receipt.json(식·검증 결과·UNTRANSLATABLE
사유·반올림 임계). 번역은 탐색 시도가 아니므로 n_trials 원장에 더하지 않는다.

매도식은 생성하지 않는다(codegen.SELL_POLICY) — 산출 매수식은 기존 게이트
체인에서 고정 매도 정책과 짝지어 무특혜로 평가한다.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from alpha_lab.translate import (
    DEFAULT_TIME_GUARD,
    to_buy_statement,
    translate_leaf_rule,
)
from cli.alpha_common import (
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    add_run_dir_args,
    setup_logging,
    verified_prereg_or_none,
    write_receipt,
)

logger = logging.getLogger(__name__)

REPORT_NAME = "translation_receipt.json"
MINING_REPORT_NAME = "mining_report.json"
SEALED_ROUND_DIGITS = 1  # 임계값 소수 1자리 반올림 — 봉인 규칙.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_translate",
        description="mining_report의 채택 리프를 STOM 매수식으로 번역한다.",
    )
    add_run_dir_args(parser)
    parser.add_argument(
        "--mining-report", default=None,
        help=f"채굴 보고서 경로 (기본 {{run-dir}}/{MINING_REPORT_NAME})",
    )
    return parser


def _rule_tuples(rule: Sequence[Sequence[Any]]) -> List[tuple]:
    """JSON 왕복 규칙([[이름, op, 임계값], ...]) → 3-튜플 리스트."""
    return [(str(name), str(op), thr) for name, op, thr in rule]


def _translate_one(entry: Dict[str, Any]) -> Dict[str, Any]:
    """채택 리프 1건 번역 — 성공 시 매수식·문장, 실패 시 사유를 담는다."""
    rule = _rule_tuples(entry["rule"])
    result = translate_leaf_rule(rule, round_digits=SEALED_ROUND_DIGITS)
    rounded = [
        [name, op, round(float(thr), SEALED_ROUND_DIGITS)] for name, op, thr in rule
    ]
    return {
        "rule_id": entry["rule_id"],
        "rule": [list(cond) for cond in rule],
        "rounded_rule": rounded,
        "expr": result.expr,
        "buy_statement": to_buy_statement(result.expr) if result.expr else None,
        "validated": result.expr is not None,
        "reasons": list(result.reasons),
    }


def _load_adopted(report_path: Path) -> List[Dict[str, Any]]:
    """mining_report에서 adopted=true 리프만 추출(rules 키 계약)."""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    rules = payload.get("rules", [])
    return [r for r in rules if isinstance(r, dict) and r.get("adopted")]


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger)
    if verified is None:
        return EXIT_SEAL
    _prereg, prereg_sha = verified
    report_path = (
        Path(args.mining_report) if args.mining_report
        else run_dir / MINING_REPORT_NAME
    )
    if not report_path.exists():
        logger.error("채굴 보고서 없음 — 먼저 alpha_mine을 실행하라: %s", report_path)
        return EXIT_INPUT
    adopted = _load_adopted(report_path)
    translations = [_translate_one(entry) for entry in adopted]
    n_translated = sum(1 for t in translations if t["expr"] is not None)
    receipt = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "mining_report": str(report_path),
        "round_digits": SEALED_ROUND_DIGITS,
        "time_guard": DEFAULT_TIME_GUARD,
        "n_adopted_input": len(adopted),
        "n_translated": n_translated,
        "n_untranslatable": len(adopted) - n_translated,
        "translations": translations,
    }
    write_receipt(run_dir / REPORT_NAME, receipt)
    for entry in translations:
        if entry["expr"] is None:
            logger.warning(
                "번역 불가 %s: %s", entry["rule_id"], "; ".join(entry["reasons"])
            )
    logger.info(
        "translate 완료: 채택 %d → 번역 %d(불가 %d) — %s",
        len(adopted), n_translated, len(adopted) - n_translated,
        run_dir / REPORT_NAME,
    )
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
