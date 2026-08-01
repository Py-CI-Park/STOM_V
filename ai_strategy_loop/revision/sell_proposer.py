"""Evidence cards for one-intent STOM sell-condition candidates."""

from __future__ import annotations

from dataclasses import dataclass

from ai_strategy_loop.autopsy.trade_path_analysis_models import TradePathAnalysis


@dataclass(frozen=True, slots=True)
class SellProposal:
    proposal_id: str
    title: str
    intent: str
    stom_code: str
    evidence: str
    counterevidence: str
    risk: str
    authority: str = "advisory"


_FORBIDDEN = ("F_", "R_", "S_", "미래", "oracle", "best_future")


def validate_candidate_code(code: str) -> None:
    if any(token in code for token in _FORBIDDEN):
        raise ValueError("future_label_leakage")
    if "self.Sell()" not in code or "매도 = True" not in code:
        raise ValueError("invalid_stom_sell_shape")


def propose_sell_conditions(analysis: TradePathAnalysis) -> tuple[SellProposal, ...]:
    rows = analysis.episodes
    if not rows:
        return ()
    recovered = [row for row in rows if row.actual_profit_krw < 0 and row.recovered_by_boundary]
    forced = [row for row in rows if row.exit_reason.startswith("전략종료")]
    proposals: list[SellProposal] = []
    if recovered:
        code = (
            "매도 = False\n"
            "if 보유시간 >= 90 and 수익률 <= -2 and 현재가 < 최저현재가(90, 1):\n"
            "    매도 = True\n\n"
            "if 매도:\n"
            "    self.Sell()"
        )
        validate_candidate_code(code)
        proposals.append(SellProposal(
            proposal_id="delay_stop_with_breakdown",
            title="초기 손절 지연 + 저점 이탈 확인",
            intent="정상 흔들림 손절을 줄이되 추가하락 확인 시 청산",
            stom_code=code,
            evidence=f"손실 후 전체청산 전 회복 거래 {len(recovered)}건",
            counterevidence=f"회복하지 못한 손실 거래 {sum(1 for row in rows if row.actual_profit_krw < 0) - len(recovered)}건",
            risk="손절 지연 동안 MAE와 MDD가 커질 수 있어 공식 pair 재백테스트가 필수",
        ))
    if forced:
        code = (
            "매도 = False\n"
            "if 보유시간 >= 300 and 수익률 > 0 and 현재가 < 이동평균(30):\n"
            "    매도 = True\n\n"
            "if 매도:\n"
            "    self.Sell()"
        )
        validate_candidate_code(code)
        proposals.append(SellProposal(
            proposal_id="preclose_profitable_fade",
            title="전체청산 전 이익권 추세이탈 청산",
            intent="장 마감 강제청산은 유지하고 그 전에 이익권 반납만 줄임",
            stom_code=code,
            evidence=f"전략종료 청산 {len(forced)}건",
            counterevidence="손실권 포지션에는 적용하지 않아 손실 강제청산을 직접 줄이지 않음",
            risk="이후 재상승 구간을 놓칠 수 있어 시간대·OOS별 검증 필요",
        ))
    return tuple(proposals)
