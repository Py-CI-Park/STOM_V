"""부검 결과 → 다음 세대 프롬프트용 한국어 자연어 피드백.

목표: AutopsyResult를 곧바로 generate_strategy(autopsy_feedback=...)에 넣을 수 있는
짧고 실행 가능한 한국어 가이드로 바꾼다.

  - status ok               : 변별력 상위 ~3개 진입 변수를 방향+수치와 함께 짚고,
                              그 변수의 진입 기준을 어느 쪽으로 조이라고 지시한다.
  - status insufficient     : "거래가 너무 적었다 → 진입 조건을 완화해 빈도를 높여라".
  - status single_class     : "전부 수익/손실 → 변별 불가 → 진입 조건을 바꿔 다양성 확보".
"""

from __future__ import annotations

from typing import Any, List, Optional

from .analyze import (
    STATUS_INSUFFICIENT,
    STATUS_OK,
    STATUS_SINGLE_CLASS,
    AutopsyResult,
    B_TO_STOM_VAR,
    Discriminator,
    ExitAutopsyResult,
)
from .segment import SegmentAutopsyResult, SegmentStat, ThresholdStat

# 요약에 포함할 상위 변별 변수 개수.
TOP_K = 3

# 세그먼트 요약에 포함할 상위 세그먼트/임계값 개수(토큰 폭증 방지).
SEG_TOP_SEGMENTS = 2
SEG_TOP_THRESHOLDS = 2

# 세그먼트가 "손실 집중"으로 지목되려면 전체 평균 대비 이 값(%p) 이상 낮아야 한다.
_SEGMENT_LOSS_DIFF_PCT = 0.2

# 부검 피드백 토큰 회귀 게이트(P1 수용기준): 세그먼트 강화로 피드백이 무한정
#   길어지지 않도록 합성 결과에 절대 문자 상한을 둔다. 초과하면 꼬리를 자른다.
#   (한국어는 char≈token 근사라 char 상한이 토큰 상한 프록시로 충분하다.)
MAX_FEEDBACK_CHARS = 1400

# 백테스트 실패 원인 분류 (다음 세대 피드백 + 이력 라인용).
#   no_trades     : 진입이 한 번도 안 됨(0거래) → metrics/CSV 없음. 가장 흔한 케이스.
#   runtime_error : 자식 프로세스 크래시/exec 예외/엔진 오류 → 코드 자체가 깨짐.
#   timeout       : 제한 시간 초과.
#   other         : 위 어디에도 안 맞는 경우(raw 원문 노출).
ERR_NO_TRADES = "no_trades"
ERR_RUNTIME = "runtime_error"
ERR_TIMEOUT = "timeout"
ERR_OTHER = "other"

# runner.run_backtest가 0거래(=metrics 없음)일 때 내는 표준 message.
#   (cli/runner.py: result['message'] = 'backtest completed without metrics')
_NO_TRADES_MARKERS = (
    "completed without metrics",   # CLI/runner: 0거래 → metrics 없음.
    "without metrics",
    "no trades",
)
# 자식 프로세스 크래시/예외를 나타내는 마커.
_RUNTIME_MARKERS = (
    "exited with code",            # runner: Backtest child process exited with code N
    "moneytop query failed",       # runner: 자식 moneytop 쿼리 실패
    "traceback",
    "exception",
    "nameerror",
    "typeerror",
    "valueerror",
    "keyerror",
    "indexerror",
    "attributeerror",
    "zerodivision",
    "syntaxerror",
    "spawn failed",                # loop: backtest spawn failed
    "raised",                      # loop: backtest raised
)
_TIMEOUT_MARKERS = (
    "timeout",
    "시간 초과",
    "timed out",
)


def classify_backtest_error(reason: str) -> str:
    """백테스트 실패 reason 문자열을 actionable 카테고리로 분류한다.

    reason은 BacktestOutcome.reason (가능하면 runner의 message + last_checkpoint를
    포함한 구체 원인). 우선순위: timeout > runtime_error > no_trades > other.
    (timeout/runtime을 먼저 봐서, '0거래'로 오분류되는 것을 막는다.)
    """
    text = (reason or "").lower()
    if any(m in text for m in _TIMEOUT_MARKERS):
        return ERR_TIMEOUT
    if any(m in text for m in _RUNTIME_MARKERS):
        return ERR_RUNTIME
    if any(m in text for m in _NO_TRADES_MARKERS):
        return ERR_NO_TRADES
    return ERR_OTHER


def backtest_error_feedback(reason: str, *, min_trades: int = 0) -> str:
    """백테스트 실패 원인을 분류해 다음 세대용 actionable 한국어 피드백을 만든다.

    '왜 실패했는지'를 모델이 보고 맹목 변이 대신 원인을 직접 겨냥하게 한다:
      - no_trades     : 진입 조건이 너무 엄격 → 완화하라.
      - runtime_error : exec/엔진 오류 → 그 오류(변수/로직)를 피하라(원문 포함).
      - timeout       : 너무 무겁다 → 단순화하라.
      - other         : raw 원문을 그대로 노출(정보 손실 없이).

    항상 비어 있지 않은 문자열을 반환한다.
    """
    category = classify_backtest_error(reason)
    raw = (reason or "").strip() or "(원인 미상)"

    if category == ERR_NO_TRADES:
        min_hint = f"(최소 {min_trades}건 필요) " if min_trades else ""
        return (
            f"직전 세대 백테스트 실패 원인 = 거래 0건(진입이 한 번도 발생하지 않음) {min_hint}"
            f"→ 진입 조건이 너무 엄격하다. 진입 조건을 완화하라: 과도하게 좁은 "
            f"임계값·AND 조건을 줄이고 진입 문턱을 낮춰 실제로 거래가 발생하게 하라."
        )

    if category == ERR_RUNTIME:
        return (
            f"직전 세대 백테스트 실패 원인 = 런타임 오류(전략 코드 실행 중 예외/엔진 오류): "
            f"{raw} → 이 변수명/로직 오류를 피하라. 정의되지 않은 변수나 잘못된 연산을 "
            f"쓰지 말고, 검증된 진입 변수만 사용하라."
        )

    if category == ERR_TIMEOUT:
        return (
            f"직전 세대 백테스트 실패 원인 = 시간 초과: {raw} → 전략이 너무 무겁다. "
            f"조건 수를 줄이고 단순화하라."
        )

    return (
        f"직전 세대 백테스트 실패 원인 = {raw} → 이 오류를 직접 겨냥해 개선하라."
    )


def backtest_error_history_line(reason: str) -> str:
    """실패 세대가 누적 이력(GenRecord.gate_reason)에 남길 구체 사유 라인.

    이력 요약에 '백테스트 실패/거래 0건' 같은 공백 라인 대신 분류된 구체 사유를 남겨,
    다음 세대가 'gen N: backtest error — <구체 원인>'을 보게 한다.
    """
    category = classify_backtest_error(reason)
    raw = (reason or "").strip() or "원인 미상"
    label = {
        ERR_NO_TRADES: "거래 0건(진입 조건 과엄격)",
        ERR_RUNTIME: f"런타임 오류({raw})",
        ERR_TIMEOUT: f"시간 초과({raw})",
        ERR_OTHER: raw,
    }[category]
    return f"백테스트 실패 — {label}"


def _fmt(value: float) -> str:
    """평균값을 사람이 읽기 좋은 형태로 — 정수면 정수, 아니면 유효숫자 4자리."""
    if abs(value) >= 1000 or value == int(value):
        return f"{value:,.0f}"
    return f"{value:.4g}"


def _discriminator_line(d: Discriminator) -> str:
    """변별 변수 한 줄: 방향 + 수치 + 튜닝 지시."""
    stom_var = B_TO_STOM_VAR.get(d.column, d.column)
    win_s = _fmt(d.win_mean)
    loss_s = _fmt(d.loss_mean)
    if d.std_mean_diff > 0:
        # 수익 거래에서 더 컸다 → 손실 거래는 이 값이 낮았다 → 기준을 높여라.
        return (
            f"- 손실 거래는 진입 시 {d.column}가 낮았다"
            f"(손실 평균 {loss_s} vs 수익 평균 {win_s})"
            f" → {stom_var} 진입 기준을 높여라."
        )
    # 손실 거래에서 더 컸다 → 기준을 낮춰라.
    return (
        f"- 손실 거래는 진입 시 {d.column}가 높았다"
        f"(손실 평균 {loss_s} vs 수익 평균 {win_s})"
        f" → {stom_var} 진입 기준을 낮춰라."
    )


def gate_failure_directive(
    *,
    gate_passed: bool,
    gate_reason: str,
    mdd: float = 0.0,
    mdd_cap: float = 0.0,
    total_profit: float = 0.0,
    trade_count: int = 0,
    min_trades: int = 0,
) -> str:
    """게이트 실패 '원인'을 직접 겨냥하는 한 줄 지시문을 만든다.

    MDD/손익 실패는 **매도(SELL) 전략**이 핵심이므로 매도를 고치라고 명시한다.
    거래 부족은 진입을 완화하라고 한다. 통과 시엔 빈 문자열.

    이 문자열은 summarize의 변별 변수 가이드와 합쳐져, 다음 세대가 (1) 게이트
    실패 원인과 (2) 승패 변별 변수를 동시에 보게 한다.
    """
    if gate_passed:
        return ""

    parts: List[str] = []
    if min_trades > 0 and trade_count < min_trades:
        parts.append(
            f"거래가 {trade_count}건(<{min_trades})으로 너무 적다 → 진입 조건을 완화해 "
            f"거래 빈도를 높여라."
        )
    if mdd_cap > 0 and abs(mdd) > mdd_cap:
        parts.append(
            f"MDD가 {abs(mdd):.4g}로 한도({mdd_cap:.4g})를 초과한다 → 매도(SELL) 전략에서 "
            f"손절을 강화하고 더 빨리 청산하라(트레일링/고정 손절 추가). 거래수는 유지하라."
        )
    if total_profit < 0:
        parts.append(
            f"총손익이 음수({total_profit:,.0f})다 → 진입 품질을 높이고(승률 낮은 진입 제거), "
            f"매도(SELL)에서 손실 거래를 더 빨리 끊어라."
        )
    if not parts:
        # gate_reason만 있는 경우(드묾) 그대로 노출.
        if gate_reason:
            return f"게이트 실패 원인: {gate_reason} → 이를 직접 겨냥해 개선하라."
        return ""
    return "게이트 실패 원인을 직접 겨냥하라:\n" + "\n".join(f"- {p}" for p in parts)


def summarize(result: AutopsyResult, config: Any = None) -> str:
    """AutopsyResult를 다음 세대 프롬프트용 한국어 피드백 문자열로 변환한다.

    Args:
        result: analyze_trades 결과.
        config: LoopConfig 등 (현재는 미사용 — 인터페이스 안정성용 슬롯).

    Returns:
        몇 줄짜리 한국어 가이드. 항상 비어 있지 않은 문자열.
    """
    min_trades = result.min_trades

    if result.status == STATUS_INSUFFICIENT:
        return (
            f"직전 전략은 거래 {result.trade_count}건(<최소 {min_trades})으로 너무 적었다 "
            f"→ 진입 조건을 완화해 거래 빈도를 높여라. "
            f"(과도하게 좁은 임계값·AND 조건을 줄이고 진입 문턱을 낮춰라.)"
        )

    if result.status == STATUS_SINGLE_CLASS:
        only = "수익" if result.loss_count == 0 else "손실"
        return (
            f"직전 전략은 거래 {result.trade_count}건이 모두 {only}이었다 "
            f"→ 수익/손실 변별이 불가하다. 진입 조건을 바꿔 거래 다양성을 확보하라."
        )

    # status ok
    top = result.discriminators[:TOP_K]
    if not top:
        # 거래는 충분하지만 분석 가능한 B_ 컬럼이 없던 드문 경우.
        return (
            f"직전 전략은 거래 {result.trade_count}건(수익 {result.win_count}/"
            f"손실 {result.loss_count})이었으나 분석 가능한 진입 변수가 없었다 "
            f"→ 진입 조건을 더 명시적인 변수(체결강도/등락율/당일거래대금 등)로 구성하라."
        )

    lines: List[str] = [
        f"직전 백테스트 부검: 거래 {result.trade_count}건"
        f"(수익 {result.win_count}/손실 {result.loss_count}). "
        f"수익과 손실을 가장 잘 가른 진입 조건은 다음과 같다. 이를 반영해 개선하라:",
    ]
    lines += [_discriminator_line(d) for d in top]
    return "\n".join(lines)


# =====================================================================
# 청산(EXIT) 부검 요약 — 매도(SELL) 전략을 직접 겨냥한 한국어 가이드.
# =====================================================================
# give-back gap이 이 값(%p) 이상이면 "익절을 놓치고 반납"으로 지목한다.
_GIVEBACK_ALERT_PCT = 1.0
# 손실 거래 평균 MAE가 이 값(%)보다 깊으면 "손절이 느슨하다"로 지목한다.
_MAE_ALERT_PCT = -2.0
# 손실 거래 보유시간이 수익 거래의 이 배수 이상이면 "시간 청산 추가"를 권한다.
_HOLD_RATIO_ALERT = 1.3


def _short_rule(rule: str, max_len: int = 60) -> str:
    """매도조건 원문을 한 줄로 짧게 — 피드백에 넣기 위함."""
    one = " ".join((rule or "").split())
    return one if len(one) <= max_len else one[: max_len - 1] + "…"


def summarize_exits(result: ExitAutopsyResult, config: Any = None) -> str:
    """ExitAutopsyResult를 **매도(SELL) 전략용** 다음 세대 한국어 피드백으로 변환한다.

    give-back(익절 반납) / MAE depth(손절 느슨) / 보유시간 / 손실 집중 매도규칙을
    구체 수치와 함께 짚고, 익절·손절·시간청산 같은 매도 조건을 어떻게 바꾸라고
    지시한다. 항상 비어 있지 않은 문자열.
    """
    if result.status == STATUS_INSUFFICIENT:
        return (
            f"직전 전략은 거래 {result.trade_count}건(<최소 {result.min_trades})으로 "
            f"청산 분석이 무의미했다 → 진입 조건을 완화해 거래 빈도를 먼저 확보하라."
        )

    lines: List[str] = [
        f"직전 백테스트 청산(매도) 부검: 거래 {result.trade_count}건"
        f"(수익 {result.win_count}/손실 {result.loss_count}). "
        f"매도(SELL) 전략을 다음과 같이 개선하라:",
    ]

    # 1) give-back (익절 반납) — 수익 거래가 고점 대비 얼마를 반납했는가.
    if result.win_count > 0 and result.giveback_gap_winners >= _GIVEBACK_ALERT_PCT:
        tp = max(round(result.avg_mfe_winners * 0.6, 1), 0.5)  # 고점의 60% 근처 익절 제안.
        lines.append(
            f"- 수익 거래 평균 MFE(고점) {result.avg_mfe_winners:.2g}%인데 "
            f"실현 {result.avg_realized_winners:.2g}% "
            f"({result.giveback_gap_winners:.2g}%p 반납) → 익절을 놓치고 되돌림에 당했다. "
            f"익절 기준(예: 수익률 >= {tp}%)을 추가해 고점 부근에서 차익을 확정하라."
        )
    elif result.win_count > 0 and result.giveback_gap_all >= _GIVEBACK_ALERT_PCT:
        lines.append(
            f"- 전체 평균 MFE {result.avg_mfe_all:.2g}% 대비 실현 "
            f"{result.avg_realized_all:.2g}% ({result.giveback_gap_all:.2g}%p 반납) "
            f"→ 익절 기준을 추가해 되돌림 반납을 줄여라."
        )

    # 2) MAE depth (손절 느슨) — 손실 거래가 청산 전 얼마나 깊이 물렸는가.
    if result.loss_count > 0 and result.avg_mae_losers <= _MAE_ALERT_PCT:
        # 평균 MAE의 절반 수준으로 손절을 조이라고 제안(과하게 깊지 않게).
        sl = round(result.avg_mae_losers / 2.0, 1)
        lines.append(
            f"- 손실 거래 평균 MAE(최저) {result.avg_mae_losers:.2g}% "
            f"(최악 {result.worst_mae_losers:.2g}%) → 손절이 느슨하다. "
            f"손절을 {sl}% 부근(예: -2~-3%)으로 조여 손실을 빨리 끊어라."
        )

    # 3) 보유시간 — 손실 거래가 더 오래 끌었는가(시간 청산 필요).
    if (result.avg_hold_winners > 0 and result.avg_hold_losers > 0
            and result.avg_hold_losers >= result.avg_hold_winners * _HOLD_RATIO_ALERT):
        lines.append(
            f"- 손실 거래 평균 보유시간({result.avg_hold_losers:.3g})이 "
            f"수익 거래({result.avg_hold_winners:.3g})보다 길다 → 손실이 시간을 끌며 "
            f"악화된다. 시간 기반 청산(예: 보유시간 >= N이면 청산)을 추가하라."
        )

    # 4) 손실 집중 매도규칙 — 어떤 청산 룰이 손실을 닫고 있는가.
    if result.worst_sell_rule:
        worst = next((s for s in result.sell_rules if s.rule == result.worst_sell_rule), None)
        if worst is not None:
            lines.append(
                f"- 손실 집중 매도규칙: `{_short_rule(worst.rule)}` "
                f"({worst.count}건, 손실 {worst.loss_count}건, 평균 {worst.avg_return:.2g}%) "
                f"→ 이 규칙이 너무 늦거나 손실을 키운다. 이 매도 조건을 재설계하라."
            )

    # give-back/MAE/시간/규칙 어느 것도 경보가 안 잡힌 경우(드묾) — 일반 가이드.
    if len(lines) == 1:
        lines.append(
            "- 뚜렷한 청산 결함은 없으나 총손익이 음수라면 익절 기준을 약간 높이고 "
            "손절을 약간 조여 손익비를 개선하라."
        )
    return "\n".join(lines)


# =====================================================================
# 세그먼트 강화 부검 요약 — "어디서·왜 손실인지"를 NL로 framing (P1).
# =====================================================================
def _fmt_threshold(t: ThresholdStat) -> str:
    """임계값 한 변수의 구체 경계를 사람이 읽는 한 줄로."""
    if t.operator == "<=" and t.threshold is not None:
        cond = f"{t.stom_var} <= {_fmt(t.threshold)}"
    elif t.operator in (">=", ">") and t.threshold is not None:
        cond = f"{t.stom_var} {t.operator} {_fmt(t.threshold)}"
    elif t.operator == "between" and (t.lower_bound is not None or t.upper_bound is not None):
        lo = _fmt(t.lower_bound) if t.lower_bound is not None else "-∞"
        hi = _fmt(t.upper_bound) if t.upper_bound is not None else "∞"
        cond = f"{t.stom_var} ∈ [{lo}, {hi}]"
    else:
        cond = f"{t.stom_var} (경계 미상)"
    return (
        f"- 손실 집중 구간 `{cond}` "
        f"({t.count}건, 승률 {t.win_rate * 100:.0f}%, 평균 {t.mean_return:.2g}%) "
        f"→ 이 구간을 진입에서 배제하거나 반대 임계값으로 조여라."
    )


def _segment_loss_line(s: SegmentStat, kind: str) -> str:
    """손실 집중 세그먼트 한 줄: 어느 밴드/시간대에서 손실이 몰렸는가 + 지시."""
    if kind == "time":
        action = "그 시간대 진입을 거르는 시간 필터를 추가하라"
    elif kind == "market_cap":
        action = "그 시총 밴드를 진입에서 배제하거나 시총 조건을 조여라"
    else:  # cross
        action = "그 시간대×시총 조합을 진입 조건에서 배제하라"
    return (
        f"- {s.label} 세그먼트가 손실 집중 "
        f"({s.count}건, 승률 {s.win_rate * 100:.0f}%, 평균 {s.avg_return:.2g}%, "
        f"전체대비 {s.return_diff:+.2g}%p) → {action}."
    )


def summarize_segments(result: SegmentAutopsyResult, config: Any = None) -> str:
    """SegmentAutopsyResult를 다음 세대 프롬프트용 한국어 세그먼트 피드백으로 변환한다.

    단변량 부검(summarize/summarize_exits)과 **합성**해 쓴다: 이 함수는 "어느
    세그먼트·시간대에서 손실이 집중되고, 어느 변수의 어느 구간이 손실인지"를
    구체 임계값과 함께 짚는다. 손실 집중 신호가 하나도 없으면 빈 문자열을 반환해
    (피드백 토큰을 아끼고) 합성기가 건너뛰게 한다.
    """
    if result.status != STATUS_OK:
        return ""

    lines: List[str] = []

    # 1) 시간대 손실 집중(가장 낮은 return_diff부터).
    worst_time = sorted(result.time_segments, key=lambda s: s.return_diff)
    for s in worst_time[:SEG_TOP_SEGMENTS]:
        if s.return_diff <= -_SEGMENT_LOSS_DIFF_PCT:
            lines.append(_segment_loss_line(s, "time"))

    # 2) 시총 밴드 손실 집중.
    worst_mcap = sorted(result.market_cap_segments, key=lambda s: s.return_diff)
    for s in worst_mcap[:SEG_TOP_SEGMENTS]:
        if s.return_diff <= -_SEGMENT_LOSS_DIFF_PCT:
            lines.append(_segment_loss_line(s, "market_cap"))

    # 3) 교차(시간대×시총) — 가장 나쁜 한 조합만(상호작용 신호).
    worst_cross = sorted(result.cross_segments, key=lambda s: s.return_diff)
    if worst_cross and worst_cross[0].return_diff <= -_SEGMENT_LOSS_DIFF_PCT:
        lines.append(_segment_loss_line(worst_cross[0], "cross"))

    # 4) 구체 임계값(분위수/t검정 경계) — 변수의 어느 값이 손실인가.
    for t in result.thresholds[:SEG_TOP_THRESHOLDS]:
        if t.mean_return < result.overall_avg_return:
            lines.append(_fmt_threshold(t))

    if not lines:
        return ""

    header = (
        f"세그먼트 부검(거래 {result.trade_count}건, 전체 승률 "
        f"{result.overall_win_rate * 100:.0f}%): 손실이 어디에 몰렸는지와 구체 "
        f"임계값이다. 이를 반영해 진입을 정밀화하라:"
    )
    return "\n".join([header] + lines)


def cap_feedback(text: Optional[str], *, max_chars: int = MAX_FEEDBACK_CHARS) -> Optional[str]:
    """합성 피드백 문자열에 절대 문자 상한을 적용한다(P1 토큰 회귀 게이트).

    부검 강화로 피드백이 무한정 길어져 프롬프트 토큰을 폭증시키는 것을 막는다.
    상한 초과 시 꼬리를 자르고 절단 표식을 붙인다. None/빈 입력은 그대로 통과한다.
    """
    if not text:
        return text
    if len(text) <= max_chars:
        return text
    marker = "\n…(피드백 길이 상한 적용)"
    keep = max(max_chars - len(marker), 0)
    return text[:keep] + marker
