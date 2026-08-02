"""Evidence cards for diverse, human-readable STOM sell-condition candidates."""

from __future__ import annotations

from dataclasses import dataclass

from ai_strategy_loop.autopsy.trade_path_analysis_models import TradePathAnalysis
from ai_strategy_loop.autopsy.trade_path_models import Timeframe


@dataclass(frozen=True, slots=True)
class SellProposal:
    proposal_id: str
    title: str
    family: str
    timeframe: str
    intent: str
    stom_code: str
    evidence: str
    counterevidence: str
    risk: str
    authority: str = "advisory"


_FORBIDDEN = ("F_", "R_", "S_", "미래", "oracle", "best_future")


class CandidateValidationError(ValueError):
    """Raised when a generated candidate violates the STOM research contract."""


def validate_candidate_code(code: str) -> None:
    if any(token in code for token in _FORBIDDEN):
        raise CandidateValidationError("future_label_leakage")
    if "self.Sell()" not in code or "매도 = True" not in code:
        raise CandidateValidationError("invalid_stom_sell_shape")


def _profile(timeframe: Timeframe) -> dict[str, int]:
    if timeframe is Timeframe.MIN:
        return {"delay": 3, "breakdown": 5, "trend": 20, "stagnant": 5, "preclose": 10}
    return {"delay": 90, "breakdown": 60, "trend": 60, "stagnant": 180, "preclose": 300}


def _proposal(*, proposal_id: str, title: str, family: str, intent: str,
              code: str, evidence: str, counterevidence: str, risk: str,
              timeframe: Timeframe) -> SellProposal:
    validate_candidate_code(code)
    return SellProposal(
        proposal_id=proposal_id, title=title, family=family,
        timeframe=timeframe.value, intent=intent, stom_code=code,
        evidence=evidence, counterevidence=counterevidence, risk=risk,
    )


def propose_sell_conditions(analysis: TradePathAnalysis) -> tuple[SellProposal, ...]:
    rows, timeframe = analysis.episodes, analysis.source.timeframe
    if not rows:
        return ()
    losses = [row for row in rows if row.actual_profit_krw < 0]
    wins = [row for row in rows if row.actual_profit_krw > 0]
    recovered = [row for row in losses if row.recovered_by_boundary]
    forced = [row for row in rows if row.exit_reason.startswith("전략종료")]
    trailing = [row for row in rows if "최고수익률" in row.exit_reason or "이동평균" in row.exit_reason]
    early_losses = [row for row in losses if row.hold_seconds <= 120]
    profile, unit = _profile(timeframe), ("분" if timeframe is Timeframe.MIN else "초")
    proposals: list[SellProposal] = []
    if recovered:
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {profile['delay']} and 수익률 <= -2 "
            f"and 현재가 < 최저현재가({profile['breakdown']}, 보유시간):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="delay_stop_with_breakdown", title="초기 손절 지연 + 진입 전 저점 이탈",
            family="손실 방어", timeframe=timeframe,
            intent=f"최소 {profile['delay']}{unit} 흔들림을 허용하고 구조 이탈 때만 청산",
            code=code, evidence=f"손실 후 전체청산 전 회복 거래 {len(recovered)}건",
            counterevidence=f"회복하지 못한 손실 거래 {len(losses) - len(recovered)}건",
            risk="손절 지연 동안 MAE와 MDD가 커질 수 있어 공식 pair 재백테스트가 필수",
        ))
    if trailing and wins:
        code = (
            "매도 = False\n"
            "if 최고수익률 >= 3.0 and 최고수익률 * 0.65 >= 수익률:\n"
            "    매도 = True\n"
            f"elif 최고수익률 >= 2.0 and 현재가N(1) >= 이동평균({profile['trend']}, 1) "
            f"and 이동평균({profile['trend']}) > 현재가:\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="lower_profit_trigger_dual_trail", title="3% 이익 트리거 + 이평 반납 이중 확인",
            family="이익 보존", timeframe=timeframe,
            intent="고수익 트레일링의 발동 구간을 낮추되 단순 고정 익절은 피함",
            code=code, evidence=f"이익 거래 {len(wins)}건 · 트레일링/이평 청산 {len(trailing)}건",
            counterevidence="낮은 트리거는 큰 추세의 조기 이탈을 늘릴 수 있음",
            risk="3.0·0.65·이평 창은 설계/OOS 공동 스윕 전 확정값이 아님",
        ))
    if recovered:
        code = (
            "매도 = False\n"
            "if 최고수익률 >= 1.5 and 수익률 <= 0 "
            f"and 현재가 < 이동평균({profile['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="mfe_breakeven_guard", title="한때 이익 거래의 본전 재진입 방어",
            family="수익 반납", timeframe=timeframe,
            intent="한때 +1.5% 이상 간 거래만 본전 아래 추세이탈에서 정리",
            code=code, evidence=f"실제 손실 뒤 경계 전 회복 {len(recovered)}건",
            counterevidence="MFE가 낮은 정상 손실 거래에는 발동하지 않음",
            risk="+1.5% 도달 전 큰 하락은 별도 손실 방어군이 담당해야 함",
        ))
    if early_losses:
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {profile['stagnant']} and 최고수익률 < 1.0 and 수익률 < 0 "
            f"and 현재가N(1) >= 이동평균({profile['trend']}, 1) "
            f"and 이동평균({profile['trend']}) > 현재가:\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="stagnation_trend_decay", title="저성과 정체 + 이평 하향 전환",
            family="시간 가치", timeframe=timeframe,
            intent=f"{profile['stagnant']}{unit} 동안 1%도 못 간 손실권 거래만 추세 전환 시 청산",
            code=code, evidence=f"2분 이내 손실 거래 {len(early_losses)}건",
            counterevidence="초기 구간 자체를 제거하지 않고 경로 상태를 함께 요구함",
            risk="1~2분 우량 패턴도 있으므로 매수시점 변수와 교차 검증해야 함",
        ))
    if forced:
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {profile['preclose']} and 수익률 > 0 "
            f"and 현재가 < 이동평균({profile['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="preclose_profitable_fade", title="전체청산 전 이익권 추세이탈 청산",
            family="마감 관리", timeframe=timeframe,
            intent=f"최소 {profile['preclose']}{unit} 보유 뒤 이익권 반납만 조기 정리",
            code=code,
            evidence=f"전략종료 청산 {len(forced)}건 · 합계 {sum(row.actual_profit_krw for row in forced):,}원",
            counterevidence="손실권 포지션에는 적용하지 않아 손실 강제청산을 직접 줄이지 않음",
            risk="이후 재상승 구간을 놓칠 수 있어 시간대·OOS별 검증 필요",
        ))
    return tuple(proposals)
