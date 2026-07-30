"""수렴/발산 판정기 (QSP1 P3) — 마스터플랜 §2 규격의 코드 구현.

구조해석 솔버의 수렴 판정과 같은 역할: 라운드 이력만 보고
  continue   : 더 돌 가치가 있다
  converged  : 개선이 허용오차(ε) 아래로 3라운드 연속 — 답 제출
  diverged   : 과조임(거래 급감)·진동 — 중단하고 원인 보고
를 결정한다. 순수 함수 — 어떤 I/O 도 없다(단위테스트 전제).

객관값(objective): 러너가 넘긴다. 게이트 통과 세대가 있으면 공식 score
(calmar×uptrend_r2×gate), 전원 미통과(음수 구간)면 총손익 — 어느 쪽이든
"클수록 좋다" 반불변만 요구한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

# 수렴 허용오차 — 직전 best 대비 상대 개선율(%). 3라운드 연속 미만이면 수렴.
DEFAULT_EPS_PCT = 2.0
DEFAULT_CONVERGE_STREAK = 3
# 발산: 거래수가 시드 대비 이 비율 미만으로 급감하면 과조임.
DEFAULT_TRADE_COLLAPSE_RATIO = 0.30
# 발산: 개선율 부호가 이 횟수 연속 교대하고 진폭이 크면 진동.
DEFAULT_OSCILLATION_FLIPS = 3
DEFAULT_OSCILLATION_AMP_PCT = 15.0


@dataclass
class RoundStat:
    round_no: int
    objective: float          # 클수록 좋음(score 또는 총손익)
    best_trades: int          # 그 라운드 베스트 후보의 거래수
    label: str = ""


@dataclass
class Judgment:
    state: str                # "continue" | "converged" | "diverged"
    reason: str
    improvement_pct: Optional[float] = None   # 직전 대비(참고)


def _improvement_pct(prev: float, cur: float) -> float:
    """직전 대비 상대 개선율(%). 기준 0 근처는 절대차로 폴백(폭주 방지)."""
    base = abs(prev)
    if base < 1e-9:
        return (cur - prev) * 100.0
    return (cur - prev) / base * 100.0


def judge(history: Sequence[RoundStat], seed_trades: int, *,
          eps_pct: float = DEFAULT_EPS_PCT,
          converge_streak: int = DEFAULT_CONVERGE_STREAK,
          trade_collapse_ratio: float = DEFAULT_TRADE_COLLAPSE_RATIO,
          oscillation_flips: int = DEFAULT_OSCILLATION_FLIPS,
          oscillation_amp_pct: float = DEFAULT_OSCILLATION_AMP_PCT) -> Judgment:
    """라운드 이력 → 판정. history 는 round_no 오름차순(0=시드 기준 라운드)."""
    if not history:
        return Judgment("continue", "이력 없음 — 첫 라운드 진행")
    cur = history[-1]

    # ① 발산: 과조임(거래 급감). 그물을 너무 조여 표본이 사라지면 통계 자체가 무효.
    if seed_trades > 0 and cur.best_trades < seed_trades * trade_collapse_ratio:
        return Judgment(
            "diverged",
            f"과조임 — 거래 {cur.best_trades}건 < 시드 {seed_trades}건의 "
            f"{trade_collapse_ratio:.0%} (그물이 통계 불능 수준으로 좁아짐)")

    if len(history) < 2:
        return Judgment("continue", "표본 라운드 부족(1) — 계속")

    deltas = [_improvement_pct(history[i - 1].objective, history[i].objective)
              for i in range(1, len(history))]

    # ② 발산: 진동 — 개선율 부호가 크게 교대(파라미터가 안정점을 못 찾음).
    if len(deltas) >= oscillation_flips + 1:
        recent = deltas[-(oscillation_flips + 1):]
        flips = sum(1 for a, b in zip(recent, recent[1:])
                    if a * b < 0 and abs(a) > oscillation_amp_pct and abs(b) > oscillation_amp_pct)
        if flips >= oscillation_flips:
            return Judgment("diverged",
                            f"진동 — 최근 개선율 {['%+.1f%%' % d for d in recent]} 부호 교대")

    # ③ 수렴: 연속 converge_streak 라운드 개선 < eps.
    if len(deltas) >= converge_streak:
        tail = deltas[-converge_streak:]
        if all(d < eps_pct for d in tail):
            return Judgment(
                "converged",
                f"개선 {['%+.2f%%' % d for d in tail]} — {converge_streak}라운드 연속 "
                f"< ε({eps_pct}%)", improvement_pct=deltas[-1])

    return Judgment("continue", f"직전 개선 {deltas[-1]:+.2f}% — 계속",
                    improvement_pct=deltas[-1])
