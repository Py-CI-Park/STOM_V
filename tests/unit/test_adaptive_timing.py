"""적응형 레짐-타이밍 오버레이 단위 테스트 (분석 전용 — 네트워크/실LLM/실백테/실DB 없음, tmp만).

검증:
  - apply_adaptive_timing: 워밍업 달은 원본 유지; 직전 윈도우 음수 다음 달 → 0(FLAT);
    직전 윈도우 비음수 다음 달 → 원본 유지. 손계산 시퀀스로 정확한 출력 단언.
  - _equity_mdd: 알려진 시퀀스 → 알려진 (총수익, MDD_절대값).
  - adaptive_timing_report: tmp_path에 3개월 걸친 작은 CSV → 기대 키·월 수, 타이밍이
    도움되는 시퀀스에서 timed_mdd <= raw_mdd.
  - 데이터 부족(1개월 CSV) → {"insufficient": True, ...}.
  - monthly_pnl_from_csv: 빠진 달은 0.0으로 채운 연속 시계열·파일 없음 → [].
  - config.adaptive_timing_enabled/lookback 기본값(False/2).

실DB/백테 미사용: tmp 경로 CSV만 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.fitness.adaptive_timing import (  # noqa: E402
    _equity_mdd,
    adaptive_timing_report,
    apply_adaptive_timing,
    monthly_pnl_from_csv,
)

# 결과 CSV 헤더는 utf-8-sig·Korean 컬럼명. 파서가 쓰는 두 컬럼(매수시간/수익금)만 채운다.
_HEADER = "종목명,매수시간,수익률,수익금\n"


def _write_csv(path, rows):
    """rows=[(buy_time_str, profit_float), ...] 를 utf-8-sig per-trade CSV로 떨군다."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HEADER)
        for buy_time, profit in rows:
            fh.write(f"A종목,{buy_time},1.0,{profit}\n")


# ---------------------------------------------------------------------------
# apply_adaptive_timing
# ---------------------------------------------------------------------------
def test_apply_adaptive_timing_warmup_and_flat():
    """[100,-50,-80,60,70] lookback=2 → 정확한 출력.

    i0,i1: 워밍업(max(1,2)=2개월) → 원본 유지(100, -50).
    i2: sum(seq[0:2])=50 >= 0 → 원본 유지(-80).
    i3: sum(seq[1:3])=-130 < 0 → 0(FLAT).
    i4: sum(seq[2:4])=-20 < 0 → 0(FLAT).
    """
    out = apply_adaptive_timing([100, -50, -80, 60, 70], lookback=2)
    assert out == [100, -50, -80, 0.0, 0.0]


def test_apply_adaptive_timing_keeps_after_positive_window():
    """직전 윈도우가 양수면 그 달은 유지된다(lookback=1)."""
    # lookback=1, warmup=max(1,1)=1.
    # i0: 워밍업 → 100.
    # i1: sum(seq[0:1])=100 >= 0 → 유지(50).
    # i2: sum(seq[1:2])=50 >= 0 → 유지(-30).
    # i3: sum(seq[2:3])=-30 < 0 → 0(FLAT).
    out = apply_adaptive_timing([100, 50, -30, 40], lookback=1)
    assert out == [100, 50, -30, 0.0]


# ---------------------------------------------------------------------------
# _equity_mdd
# ---------------------------------------------------------------------------
def test_equity_mdd_known_sequence():
    """[100,-30,-50,80] → 총수익 100, MDD 80.

    누적: 100, 70, 20, 100. peak=100. 최대 반납 = 100-20 = 80.
    """
    total, mdd = _equity_mdd([100.0, -30.0, -50.0, 80.0])
    assert total == 100.0
    assert mdd == 80.0


def test_equity_mdd_monotonic_up_has_zero_mdd():
    """단조 증가 시퀀스는 MDD=0."""
    total, mdd = _equity_mdd([10.0, 20.0, 30.0])
    assert total == 60.0
    assert mdd == 0.0


# ---------------------------------------------------------------------------
# monthly_pnl_from_csv
# ---------------------------------------------------------------------------
def test_monthly_pnl_fills_gap_months(tmp_path):
    """첫 월~마지막 월 사이 빠진 달은 0.0으로 채운 연속 시계열을 만든다."""
    csv_path = os.path.join(str(tmp_path), "trades.csv")
    # 202501과 202503만 거래(202502는 빠짐 → 0.0으로 채워져야 한다).
    _write_csv(csv_path, [
        ("20250103090403", 100.0),
        ("20250115091200", 50.0),
        ("20250310090700", -40.0),
    ])
    seq = monthly_pnl_from_csv(csv_path)
    assert seq == [("202501", 150.0), ("202502", 0.0), ("202503", -40.0)]


def test_monthly_pnl_missing_file_returns_empty():
    """파일 없음 → 빈 리스트(무예외)."""
    assert monthly_pnl_from_csv("does_not_exist_xyz.csv") == []
    assert monthly_pnl_from_csv("") == []


# ---------------------------------------------------------------------------
# adaptive_timing_report
# ---------------------------------------------------------------------------
def test_adaptive_timing_report_keys_and_timing_helps(tmp_path):
    """3개월+ 걸친 CSV → 기대 키·월 수, 타이밍이 도움되면 timed_mdd <= raw_mdd.

    월별 손익 [100, -200, -300, 50] (202501~202504), lookback=2:
      raw 누적: 100, -100, -400, -350 → peak 100, MDD 500.
      i2: sum([100,-200])=-100<0 → 0 (원래 -300, 큰 손실 회피).
      i3: sum([-200,-300])=-500<0 → 0 (원래 50).
      timed 누적: 100, -100, -100, -100 → peak 100, MDD 200.
    → timed_mdd(200) < raw_mdd(500). off_months=2.
    """
    csv_path = os.path.join(str(tmp_path), "trades.csv")
    _write_csv(csv_path, [
        ("20250103090403", 100.0),
        ("20250210090700", -200.0),
        ("20250318091000", -300.0),
        ("20250405090500", 50.0),
    ])
    rep = adaptive_timing_report(csv_path, lookback=2)

    # 기대 키 전부 존재.
    for key in (
        "months", "lookback", "raw_total", "raw_mdd", "timed_total", "timed_mdd",
        "off_months", "raw_ratio", "timed_ratio", "monthly",
    ):
        assert key in rep

    assert rep["months"] == 4
    assert rep["lookback"] == 2
    assert rep["raw_total"] == -350.0
    assert rep["raw_mdd"] == 500.0
    assert rep["timed_total"] == -100.0
    assert rep["timed_mdd"] == 200.0
    assert rep["off_months"] == 2
    # 타이밍이 MDD를 개선한다.
    assert rep["timed_mdd"] <= rep["raw_mdd"]
    # monthly 길이·구조.
    assert len(rep["monthly"]) == 4
    assert rep["monthly"][0] == {"ym": "202501", "raw": 100.0, "timed": 100.0}
    assert rep["monthly"][2] == {"ym": "202503", "raw": -300.0, "timed": 0.0}


def test_adaptive_timing_report_ratio_zero_when_no_mdd(tmp_path):
    """MDD가 0이면 ratio는 0.0(0 나눗셈 회피)."""
    csv_path = os.path.join(str(tmp_path), "up.csv")
    # 매월 양수 → 단조 증가 → raw_mdd=0. lookback=2 warmup이라 전부 유지 → timed_mdd=0.
    _write_csv(csv_path, [
        ("20250103090403", 100.0),
        ("20250210090700", 100.0),
        ("20250318091000", 100.0),
    ])
    rep = adaptive_timing_report(csv_path, lookback=2)
    assert rep["raw_mdd"] == 0.0
    assert rep["raw_ratio"] == 0.0
    assert rep["timed_ratio"] == 0.0


def test_adaptive_timing_report_insufficient_single_month(tmp_path):
    """1개월 CSV → insufficient 가드."""
    csv_path = os.path.join(str(tmp_path), "one.csv")
    _write_csv(csv_path, [
        ("20250103090403", 100.0),
        ("20250115091200", -20.0),
    ])
    rep = adaptive_timing_report(csv_path, lookback=2)
    assert rep == {"insufficient": True, "months": 1}


def test_adaptive_timing_report_missing_file_insufficient():
    """파일 없음 → months 0의 insufficient(무예외)."""
    rep = adaptive_timing_report("does_not_exist_xyz.csv", lookback=2)
    assert rep == {"insufficient": True, "months": 0}


# ---------------------------------------------------------------------------
# config 기본값 (byte-identity)
# ---------------------------------------------------------------------------
def test_config_defaults_off():
    """adaptive_timing 토글/lookback 기본값(False/2) — 분석 전용이라 루프 동작 불변."""
    cfg = LoopConfig()
    assert cfg.adaptive_timing_enabled is False
    assert cfg.adaptive_timing_lookback == 2
