"""기록 계약(B7, 2026-06-10): record_generation의 reason은 fit.reason 원문이어야 한다.

배경: sparse_positive_v1의 sparse 버킷 판정은 gate_reason 문자열
`daily_avg_trades X < min_daily_trades Y`의 **전체일치(fullmatch)**다. reason에
접두사/접미사를 붙이는 어떤 기록 도구든 버킷 분류가 조용히 깨진다(2026-06-10
배치 도구 1차본에서 실제 발생·수정). 이 테스트는 그 계약을 고정한다.
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller._candidate_selection_core import (  # noqa: E402
    DAILY_FAILURE_RE,
)
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    parse_candidate_generation,
    select_sparse_positive_v1,
)

DAILY_ONLY_REASON = "daily_avg_trades 0.2 < min_daily_trades 0.3"


def _row(reason: str) -> dict:
    """배치 도구/루프가 기록하는 generations 행과 동일한 형태의 dict."""
    return {
        "gen_no": 1,
        "status": "ok",
        "score": 1.0,
        "gate_passed": False,
        "reason": reason,
        "profit": 1_000_000.0,
        "total_profit_pct": 20.0,
        "mdd": 8.0,
        "trade_count": 120,
        "daily_avg_trades": 0.2,
        "payoff_ratio": 1.4,
        "max_hold_count": 0.0,
        "buy_name": "B",
        "sell_name": "S",
        "csv_path": "",
    }


def test_daily_failure_regex_is_fullmatch_only() -> None:
    assert DAILY_FAILURE_RE.fullmatch(DAILY_ONLY_REASON) is not None
    # 접두사/접미사가 붙으면 fullmatch가 깨진다 — 기록 도구는 reason 원문을 보존해야 한다.
    assert DAILY_FAILURE_RE.fullmatch(f"[LABEL] {DAILY_ONLY_REASON}") is None
    assert DAILY_FAILURE_RE.fullmatch(f"{DAILY_ONLY_REASON} (note)") is None


def test_verbatim_reason_reaches_sparse_bucket_and_prefixed_does_not() -> None:
    ok = select_sparse_positive_v1(
        (parse_candidate_generation(_row(DAILY_ONLY_REASON)),),
        run_id="r", config_path="c", config_hash="h",
    )
    assert ok.selected is True
    assert ok.selected_bucket == "sparse_positive"

    broken = select_sparse_positive_v1(
        (parse_candidate_generation(_row(f"[C7_SEEDPLUS] {DAILY_ONLY_REASON}")),),
        run_id="r", config_path="c", config_hash="h",
    )
    assert broken.selected is False


def test_batch_eval_tool_records_verbatim_reason() -> None:
    """배치 평가 도구 소스가 reason 원문 보존 계약을 지키는지 정적 검사로 고정한다.

    (성공 행은 `reason=fit.reason` 그대로 — 라벨은 strategy_gist로만. error 행의
    접두사는 status!='ok'라 선택기에서 이미 제외되므로 허용.)
    """
    path = os.path.join(
        PROJECT_ROOT, "ai_strategy_loop", "scripts", "claude_candidate_batch_eval.py"
    )
    source = open(path, encoding="utf-8").read()
    assert "reason=fit.reason" in source
    assert 'reason=f"[{label}] {fit.reason}"' not in source
