"""세대 누적 이력 → 다음 세대 프롬프트용 요약 (CONVERGENCE).

문제: 각 세대가 직전 세대의 부검만 보면 비-거래 패턴으로 회귀한다(gen 0→2→5가
모두 0거래). 해결: 지금까지 시도한 전략들의 점수·실패·핵심 진입 조건을 누적으로
들고 다니며, 다음 세대에 "무엇을 회피하고 어느 방향이 점수를 올리는지"를 알려준다.

설계 원칙(SIMPLICITY):
  - GenRecord = 한 세대의 compact 기록 (점수/게이트/거래수/MDD/손익/전략 gist).
  - build_history_summary = 최근 K개 + best-so-far 를 한국어 요약 문자열로.
  - 루프가 매 세대 state에서 이 요약을 만들어 build_messages/generate_strategy에 넘긴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

# 프롬프트에 넣을 최근 세대 기록 수 상한 (best-so-far는 항상 별도로 포함).
DEFAULT_HISTORY_K = 4


@dataclass
class GenRecord:
    """한 세대의 compact 이력 기록.

    gen_no       : 세대 번호.
    graded_score : 등급화 적합도(선택 그래디언트). 게이트 통과면 >=1.0.
    gate_passed  : 하드 게이트 통과 여부.
    gate_reason  : 게이트 실패 사유/근접도 요약 (gate_distance).
    trade_count  : 거래 횟수.
    mdd          : 최대낙폭(%).
    profit       : 총손익(원).
    gist         : 전략 핵심 진입 조건 한 줄 요약.
    """

    gen_no: int
    graded_score: float
    gate_passed: bool
    gate_reason: str
    trade_count: int
    mdd: float
    profit: float
    gist: str = ""


def _fmt_profit(value: float) -> str:
    """손익을 사람이 읽기 좋게 — 부호 + 천단위."""
    return f"{value:,.0f}"


def _record_line(rec: GenRecord) -> str:
    """세대 기록 한 줄."""
    gate = "통과" if rec.gate_passed else "실패"
    line = (
        f"- gen{rec.gen_no}: graded={rec.graded_score:.4g} 게이트={gate} "
        f"거래={rec.trade_count} MDD={rec.mdd:.4g} 손익={_fmt_profit(rec.profit)}"
    )
    if rec.gate_reason and not rec.gate_passed:
        line += f" ({rec.gate_reason})"
    if rec.gist:
        line += f" | 진입: {rec.gist}"
    return line


def build_history_summary(
    records: Sequence[GenRecord],
    *,
    k: int = DEFAULT_HISTORY_K,
    best: Optional[GenRecord] = None,
) -> Optional[str]:
    """누적 세대 기록을 다음 세대 프롬프트용 한국어 요약으로 만든다.

    무엇을 시도했는지·점수/실패·무엇을 회피할지·어느 방향이 graded를 올리는지를
    compact 하게 담는다. 기록이 없으면 None(요약 없음 = 첫 세대).

    Args:
        records: 지금까지의 GenRecord 리스트 (시간순). 최근 K개만 상세히 싣는다.
        k: 상세히 실을 최근 세대 수.
        best: 지금까지 graded 최고 세대 (없으면 records에서 산출).

    Returns:
        요약 문자열 또는 None(기록 없음).
    """
    recs = [r for r in records if r is not None]
    if not recs:
        return None

    if best is None:
        best = max(recs, key=lambda r: r.graded_score)

    recent = recs[-k:] if k > 0 else recs

    lines: List[str] = [
        f"지금까지 {len(recs)}개 세대를 시도했다. 같은 실패를 반복하지 말고 "
        f"graded 점수를 올리는 방향으로 개선하라:",
    ]
    lines += [_record_line(r) for r in recent]

    # best-so-far 강조 (recent에 이미 있어도 명시적으로 방향을 짚는다).
    best_gate = "통과" if best.gate_passed else "실패"
    lines.append(
        f"가장 근접한 시도 = gen{best.gen_no} (graded={best.graded_score:.4g}, "
        f"게이트={best_gate}, 거래={best.trade_count}, MDD={best.mdd:.4g}, "
        f"손익={_fmt_profit(best.profit)}). 이 방향을 기준으로 부족한 제약을 좁혀라."
    )

    # 회피 가이드: 0거래가 반복됐으면 명시적으로 경고.
    zero_trade_gens = [r.gen_no for r in recs if r.trade_count == 0]
    if len(zero_trade_gens) >= 2:
        lines.append(
            f"경고: gen{', gen'.join(str(g) for g in zero_trade_gens)}이 모두 0거래였다 "
            f"→ 진입이 전혀 안 되는 과도하게 좁은 단독 필터(예: 데이터길이<60 단독)를 "
            f"회피하고, 실제로 거래가 발생하도록 진입 문턱을 낮춰라."
        )
    elif zero_trade_gens:
        lines.append(
            f"주의: gen{zero_trade_gens[-1]}이 0거래였다 → 진입 조건이 너무 좁지 않게 하라."
        )

    # 방향 가이드: best가 게이트에 가깝지만 실패면 어느 제약을 좁힐지.
    if not best.gate_passed and best.trade_count > 0:
        lines.append(
            f"방향: 거래는 발생했으니 게이트 실패 원인({best.gate_reason})을 직접 겨냥하라 "
            f"— MDD가 높으면 매도를 더 빨리(손절 강화), 손익이 음수면 진입 품질을 높여라."
        )

    return "\n".join(lines)
