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


# 홀드아웃(표본외) 규격 — QSP2 확장(마스터플랜 §2 "홀드아웃 동반 개선" 실장, R7 교훈):
#   과최적 괴리: 설계가 이만큼 좋아지는데(각 +1%↑) 홀드아웃이 이만큼 나빠지는(각 −5%↓)
#   라운드가 연속 2회면 발산 선언(설계 구간 암기 신호).
OVERFIT_DESIGN_UP_PCT = 1.0
OVERFIT_HOLDOUT_DOWN_PCT = -5.0
OVERFIT_STREAK = 2


def judge(history: Sequence[RoundStat], seed_trades: int, *,
          eps_pct: float = DEFAULT_EPS_PCT,
          converge_streak: int = DEFAULT_CONVERGE_STREAK,
          trade_collapse_ratio: float = DEFAULT_TRADE_COLLAPSE_RATIO,
          oscillation_flips: int = DEFAULT_OSCILLATION_FLIPS,
          oscillation_amp_pct: float = DEFAULT_OSCILLATION_AMP_PCT,
          holdout: Optional[Sequence[Optional[float]]] = None) -> Judgment:
    """라운드 이력 → 판정. history 는 round_no 오름차순(0=시드 기준 라운드).

    holdout: history 와 정렬된 표본외 objective(라운드별 베스트를 홀드아웃 구간에서
    재평가한 값). None 항목 허용(미평가 라운드). 있으면 두 규칙이 추가된다:
      ① 과최적 괴리 발산(설계↑·홀드아웃↓ 연속) — R7 에서 손으로 잡았던 판정의 자동화.
      ② 수렴 선언에 '홀드아웃 순악화 아님' 요건 — 악화 상태의 정체는 수렴이 아니라
         과최적 정체이므로 diverged 로 정직하게 보고한다.
    """
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

    # ①-b 발산: 과최적 괴리 — 설계 개선·홀드아웃 악화 연속(홀드아웃 제공 시에만).
    hold = list(holdout or [])
    if len(hold) == len(history):
        h_deltas = []
        for i in range(1, len(history)):
            if hold[i] is None or hold[i - 1] is None:
                h_deltas.append(None)
            else:
                h_deltas.append(_improvement_pct(hold[i - 1], hold[i]))
        streak = 0
        for d_design, d_hold in zip(deltas[::-1], h_deltas[::-1]):
            if (d_hold is not None and d_design > OVERFIT_DESIGN_UP_PCT
                    and d_hold < OVERFIT_HOLDOUT_DOWN_PCT):
                streak += 1
                if streak >= OVERFIT_STREAK:
                    return Judgment(
                        "diverged",
                        f"과최적 괴리 — 설계 개선(+{d_design:.1f}% 등)·홀드아웃 악화"
                        f"({d_hold:.1f}% 등) {OVERFIT_STREAK}라운드 연속")
            else:
                break

    # ② 발산: 진동 — 개선율 부호가 크게 교대(파라미터가 안정점을 못 찾음).
    if len(deltas) >= oscillation_flips + 1:
        recent = deltas[-(oscillation_flips + 1):]
        flips = sum(1 for a, b in zip(recent, recent[1:])
                    if a * b < 0 and abs(a) > oscillation_amp_pct and abs(b) > oscillation_amp_pct)
        if flips >= oscillation_flips:
            return Judgment("diverged",
                            f"진동 — 최근 개선율 {['%+.1f%%' % d for d in recent]} 부호 교대")

    # ③ 수렴: 연속 converge_streak 라운드 개선 < eps (+홀드아웃 순악화 아님 요건).
    if len(deltas) >= converge_streak:
        tail = deltas[-converge_streak:]
        # abs(): 큰 음의 델타(붕괴)가 '< ε' 를 만족해 수렴으로 오판되는 것 방지
        #   (감사 BUG-C — 이 루프에선 base 상시 포함으로 δ≥0 이지만 judge 는 순수 함수).
        if all(abs(d) < eps_pct for d in tail):
            hold_vals = [h for h in hold if h is not None]
            # 허용오차(OVERFIT_HOLDOUT_DOWN_PCT): 초반 하락 후 회복 궤적을 정체로
            #   오판하지 않도록, 순악화가 유의(−5% 초과)할 때만 발산 처리(감사 B6).
            if (len(hold_vals) >= 2
                    and _improvement_pct(hold_vals[0], hold_vals[-1]) < OVERFIT_HOLDOUT_DOWN_PCT):
                return Judgment(
                    "diverged",
                    f"설계 정체(개선 {['%+.2f%%' % d for d in tail]} < ε) 인데 홀드아웃은 "
                    f"순악화({hold_vals[0]:,.0f}→{hold_vals[-1]:,.0f}) — 과최적 정체")
            return Judgment(
                "converged",
                f"개선 {['%+.2f%%' % d for d in tail]} — {converge_streak}라운드 연속 "
                f"< ε({eps_pct}%)"
                + (" · 홀드아웃 순유지" if len(hold_vals) >= 2 else ""),
                improvement_pct=deltas[-1])

    return Judgment("continue", f"직전 개선 {deltas[-1]:+.2f}% — 계속",
                    improvement_pct=deltas[-1])
