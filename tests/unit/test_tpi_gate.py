"""매매성능지수(tpi) 하드게이트 옵션 단위 테스트 (마스터 로드맵 R1 과제 B).

배경: 우수전략 보고서 기준 winner 판정의 핵심은 매매성능지수(tpi)>=1.25다.
compute_fitness 하드게이트에 tpi 조건을 **옵션(토글)** 으로 추가한다.

검증:
  (1) tpi_gate_enabled=False(기본): tpi 무관 — 기존 게이트 동작 불변.
  (2) tpi_gate_enabled=True + tpi<gate: gate_passed=False(사유에 tpi 명시).
  (3) tpi_gate_enabled=True + tpi>=gate: 통과(다른 제약 충족 시).
  (4) tpi_gate_enabled=True인데 metrics에 tpi 키 없음: 무영향(하위호환).
  (5) tpi 게이트는 빈도·MDD·흑자 다음의 마지막 AND 절 — 앞 제약 실패가 우선한다.

실DB/백테 미사용: metrics dict + LoopConfig만 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.fitness.score import compute_fitness  # noqa: E402

# 꾸준히 우상향(R²>0) 곡선 — score>0 검증용(gate=1일 때 score=calmar*r2*1>0).
_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _metrics(*, tpi=None, daily_avg=0.6, cagr=30.0, mdd=10.0, trades=50, profit=1_000_000):
    """빈도·MDD·흑자 게이트는 통과하도록 구성한 metrics. tpi=None이면 키 자체를 뺀다."""
    m = {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "daily_avg_trades": daily_avg,
        "total_profit_krw": profit,
    }
    if tpi is not None:
        m["tpi"] = tpi
    return m


# =====================================================================
# (1) 기본 OFF: tpi 무관 — 기존 게이트 불변.
# =====================================================================
def test_default_disabled_tpi_does_not_affect_gate():
    """tpi_gate_enabled 기본값은 False — tpi가 낮아도 게이트에 영향 없다."""
    cfg = LoopConfig(min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25)
    assert cfg.tpi_gate_enabled is False
    # tpi 0.1(<<1.25)인데도 OFF라 빈도·MDD·흑자만으로 통과해야 한다.
    res = compute_fitness(_metrics(tpi=0.1), _STEADY, cfg)
    assert res.gate_passed is True
    assert res.reason == "ok"


def test_disabled_gate_byte_identical_with_or_without_tpi():
    """OFF에서는 tpi 키 유무가 게이트 결과를 바꾸지 않는다(기존 동작 보존)."""
    cfg = LoopConfig(min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25)
    with_low_tpi = compute_fitness(_metrics(tpi=0.1), _STEADY, cfg)
    no_tpi = compute_fitness(_metrics(tpi=None), _STEADY, cfg)
    assert with_low_tpi.gate_passed == no_tpi.gate_passed is True
    assert with_low_tpi.score == no_tpi.score


# =====================================================================
# (2) ON + tpi<gate → 탈락(사유에 tpi).
# =====================================================================
def test_enabled_fails_when_tpi_below_gate():
    """tpi_gate_enabled=True이고 tpi<tpi_gate면 게이트 탈락."""
    cfg = LoopConfig(
        min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25, tpi_gate_enabled=True
    )
    # 빈도·MDD·흑자는 통과하지만 tpi 1.0 < 1.25 → 탈락.
    res = compute_fitness(_metrics(tpi=1.0), _STEADY, cfg)
    assert res.gate_passed is False
    assert res.score == 0.0
    assert "tpi" in res.reason


# =====================================================================
# (3) ON + tpi>=gate → 통과.
# =====================================================================
def test_enabled_passes_when_tpi_meets_gate():
    """tpi_gate_enabled=True이고 tpi>=tpi_gate면(타 제약 충족) 통과."""
    cfg = LoopConfig(
        min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25, tpi_gate_enabled=True
    )
    res = compute_fitness(_metrics(tpi=1.30), _STEADY, cfg)
    assert res.gate_passed is True
    assert res.reason == "ok"
    assert res.score > 0.0


def test_enabled_passes_when_tpi_exactly_at_gate():
    """경계: tpi == tpi_gate면 통과(>= 비교)."""
    cfg = LoopConfig(
        min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25, tpi_gate_enabled=True
    )
    res = compute_fitness(_metrics(tpi=1.25), _STEADY, cfg)
    assert res.gate_passed is True


# =====================================================================
# (4) ON인데 tpi 키 없음 → 무영향(하위호환).
# =====================================================================
def test_enabled_no_tpi_key_is_noop():
    """tpi_gate_enabled=True여도 metrics에 tpi 키가 없으면 게이트에 영향 없다."""
    cfg = LoopConfig(
        min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25, tpi_gate_enabled=True
    )
    res = compute_fitness(_metrics(tpi=None), _STEADY, cfg)
    assert res.gate_passed is True
    assert res.reason == "ok"


# =====================================================================
# (5) 순서: 앞 제약(빈도/MDD/흑자) 실패가 tpi보다 우선한다.
# =====================================================================
def test_prior_constraints_take_precedence_over_tpi():
    """빈도 게이트가 먼저 실패하면 reason은 tpi가 아닌 빈도여야 한다(마지막 AND 절)."""
    cfg = LoopConfig(
        min_daily_trades=0.5, mdd_cap=50.0, tpi_gate=1.25, tpi_gate_enabled=True
    )
    # 일평균 0.1 < 0.5(빈도 실패) + tpi 0.1 < 1.25(tpi도 실패). 빈도가 우선.
    res = compute_fitness(_metrics(tpi=0.1, daily_avg=0.1), _STEADY, cfg)
    assert res.gate_passed is False
    assert "daily_avg_trades" in res.reason
    assert "tpi" not in res.reason
