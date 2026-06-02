"""MFE/MAE 엣지비율 + 다-run 풀링 파노라마 세그먼트 단위 테스트
(분석 전용 — 네트워크/실LLM/실백테/실DB 없음, tmp만).

검증:
  - compute_edge_metrics: edge_ratio = 평균MFE/평균|MAE| 정확값; mae_efficiency;
    win_rate; mean_mae<=0 또는 컬럼 부재 시 None 가드; 손/익 trade별 평균 역행 깊이.
  - 컬럼 폴백: R_MFE/R_MAE 없이 R_매수후최고/최저수익률만 있어도 edge_ratio 산출.
  - edge_by_segment: 2개 시총 tier + 2개 시간대에 걸친 df → 셀 존재, '미분류' 제외,
    저(低)표본 셀 제외.
  - edge_report_from_csvs: tmp_path에 작은 CSV 2개 → 풀링 pooled_trades=합, global/
    segments 존재; 없는 파일은 무예외로 건너뜀; 빈 풀 → insufficient.

실DB/백테 미사용: tmp 경로 CSV + 손계산 DataFrame만 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.edge_ratio import (  # noqa: E402
    compute_edge_metrics,
    edge_by_segment,
    edge_report_from_csvs,
)


# ---------------------------------------------------------------------------
# compute_edge_metrics
# ---------------------------------------------------------------------------
def test_compute_edge_metrics_exact_edge_ratio():
    """edge_ratio = 평균MFE / 평균|MAE| 정확값 + mae_efficiency + win_rate.

    수익률 [2.0, -1.0, 3.0, -0.5] → win_rate = 2/4 = 0.5, avg_return = 0.875.
    R_MFE [4.0, 1.0, 6.0, 1.0] → mean_mfe = 3.0.
    R_MAE [-1.0, -3.0, -0.5, -2.5] → |MAE| 평균 = (1.0+3.0+0.5+2.5)/4 = 1.75.
    edge_ratio = 3.0 / 1.75. mae_efficiency = 0.875 / 3.0.
    """
    df = pd.DataFrame({
        "수익률": [2.0, -1.0, 3.0, -0.5],
        "수익금": [200.0, -100.0, 300.0, -50.0],
        "R_MFE": [4.0, 1.0, 6.0, 1.0],
        "R_MAE": [-1.0, -3.0, -0.5, -2.5],
    })
    m = compute_edge_metrics(df)
    assert m["count"] == 4
    assert m["win_rate"] == 0.5
    assert abs(m["avg_return"] - 0.875) < 1e-9
    assert m["total_profit"] == 350.0
    assert m["mean_mfe"] == 3.0
    assert m["mean_mae"] == 1.75
    assert abs(m["edge_ratio"] - (3.0 / 1.75)) < 1e-9
    assert abs(m["mae_efficiency"] - (0.875 / 3.0)) < 1e-9
    # 손실 거래(수익률<=0) |MAE|: [-3.0,-2.5] → 평균 2.75; 이익 거래: [-1.0,-0.5] → 0.75.
    assert m["mean_mae_losers"] == 2.75
    assert m["mean_mae_winners"] == 0.75


def test_compute_edge_metrics_none_guard_when_mae_zero():
    """평균 |MAE| <= 0 이면 edge_ratio = None(0 나눗셈 가드)."""
    df = pd.DataFrame({
        "수익률": [1.0, -1.0],
        "R_MFE": [2.0, 3.0],
        "R_MAE": [0.0, 0.0],  # |MAE| 평균 0 → edge_ratio None.
    })
    m = compute_edge_metrics(df)
    assert m["mean_mae"] == 0.0
    assert m["edge_ratio"] is None
    # mean_mfe>0 이므로 mae_efficiency는 여전히 산출된다.
    assert m["mae_efficiency"] is not None


def test_compute_edge_metrics_no_mfe_mae_columns():
    """MFE/MAE 컬럼이 전혀 없으면 mfe/mae/edge는 None, count/win_rate/avg_return은 산출."""
    df = pd.DataFrame({"수익률": [1.0, -2.0, 3.0]})
    m = compute_edge_metrics(df)
    assert m["count"] == 3
    assert abs(m["win_rate"] - (2.0 / 3.0)) < 1e-9
    assert m["mean_mfe"] is None
    assert m["mean_mae"] is None
    assert m["edge_ratio"] is None
    assert m["mae_efficiency"] is None
    assert m["total_profit"] is None  # 수익금 컬럼 없음.


def test_compute_edge_metrics_column_fallback():
    """R_MFE/R_MAE 없이 R_매수후최고/최저수익률만 있어도 edge_ratio 산출(폴백 경로)."""
    df = pd.DataFrame({
        "수익률": [1.0, -1.0],
        "R_매수후최고수익률": [4.0, 2.0],   # mean = 3.0.
        "R_매수후최저수익률": [-1.0, -2.0],  # |.| 평균 = 1.5.
    })
    m = compute_edge_metrics(df)
    assert m["mean_mfe"] == 3.0
    assert m["mean_mae"] == 1.5
    assert abs(m["edge_ratio"] - (3.0 / 1.5)) < 1e-9


# ---------------------------------------------------------------------------
# edge_by_segment
# ---------------------------------------------------------------------------
def _segment_df():
    """2개 시총 tier(초소형<1000·중형 3000~10000) × 2개 시간대(장초반·오전) 거래 df.

    각 (tier, time) 셀에 6건씩(min_samples=5 통과). B_시분초=HHMMSS, B_시가총액=억원.
    """
    rows = []
    # 초소형(시총 500) × 장초반(09:01) — 6건.
    for i in range(6):
        rows.append({"수익률": 1.0 + i * 0.1, "수익금": 100.0, "R_MFE": 3.0, "R_MAE": -1.0,
                     "B_시분초": 90100, "B_시가총액": 500.0})
    # 초소형(시총 500) × 오전(10:00) — 6건.
    for i in range(6):
        rows.append({"수익률": -0.5, "수익금": -50.0, "R_MFE": 2.0, "R_MAE": -2.0,
                     "B_시분초": 100000, "B_시가총액": 500.0})
    # 중형(시총 5000) × 장초반(09:02) — 6건.
    for i in range(6):
        rows.append({"수익률": 2.0, "수익금": 200.0, "R_MFE": 5.0, "R_MAE": -1.0,
                     "B_시분초": 90200, "B_시가총액": 5000.0})
    # 중형(시총 5000) × 오전(10:30) — 6건.
    for i in range(6):
        rows.append({"수익률": 0.5, "수익금": 50.0, "R_MFE": 2.0, "R_MAE": -0.5,
                     "B_시분초": 103000, "B_시가총액": 5000.0})
    return pd.DataFrame(rows)


def test_edge_by_segment_cells_present_and_low_count_skipped():
    """2 시총 × 2 시간대 → 각 축 셀 존재, 셀에 edge_ratio 산출, 저표본 셀은 제외."""
    df = _segment_df()
    # 표본 3건짜리(min_samples 미달) 대형 셀 추가 → market_cap '대형' 셀은 제외돼야 한다.
    extra = pd.DataFrame([
        {"수익률": 1.0, "수익금": 100.0, "R_MFE": 3.0, "R_MAE": -1.0,
         "B_시분초": 90100, "B_시가총액": 20000.0}
        for _ in range(3)
    ])
    df = pd.concat([df, extra], ignore_index=True)

    out = edge_by_segment(df, min_samples=5)
    mcap_labels = {r["label"] for r in out["market_cap"]}
    time_labels = {r["label"] for r in out["time"]}

    # 초소형/중형 두 tier가 잡힌다(각 12건). 대형(3건)은 min_samples 미달로 제외.
    assert "초소형" in mcap_labels
    assert "중형" in mcap_labels
    assert "대형" not in mcap_labels
    # 시간대 장초반/오전 둘 다 잡힌다(각 12건).
    assert "장초반" in time_labels
    assert "오전" in time_labels
    # 각 시총 셀에 edge_ratio가 산출됐다(MFE/MAE 컬럼 존재).
    for r in out["market_cap"]:
        assert r["edge_ratio"] is not None
    # cross 셀: "{time}×{mcap}" 라벨 형식.
    cross_labels = {r["label"] for r in out["cross"]}
    assert "장초반×초소형" in cross_labels
    assert "오전×중형" in cross_labels


def test_edge_by_segment_skips_unclassified():
    """라벨링 실패 행('미분류')은 세그먼트에서 제외된다."""
    # B_시분초 범위밖(15:40=154000 > 장마감 153000) → 시간대 '미분류'.
    rows = [
        {"수익률": 1.0, "수익금": 100.0, "R_MFE": 3.0, "R_MAE": -1.0,
         "B_시분초": 154000, "B_시가총액": 500.0}
        for _ in range(8)
    ]
    out = edge_by_segment(pd.DataFrame(rows), min_samples=5)
    time_labels = {r["label"] for r in out["time"]}
    assert "미분류" not in time_labels


# ---------------------------------------------------------------------------
# edge_report_from_csvs
# ---------------------------------------------------------------------------
_HEADER = "종목명,수익률,수익금,R_MFE,R_MAE,B_시분초,B_시가총액\n"


def _write_csv(path, n, ret, mfe, mae, sigun, mcap):
    """n건 동일 거래(손계산 풀링 단언용)를 utf-8-sig per-trade CSV로 떨군다."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HEADER)
        for _ in range(n):
            fh.write(f"A종목,{ret},100.0,{mfe},{mae},{sigun},{mcap}\n")


def test_edge_report_from_csvs_pools_two_files(tmp_path):
    """CSV 2개 풀링 → pooled_trades = 합, global/segments 키 존재."""
    p1 = os.path.join(str(tmp_path), "a.csv")
    p2 = os.path.join(str(tmp_path), "b.csv")
    _write_csv(p1, 8, 2.0, 4.0, -1.0, 90100, 500.0)   # 초소형 장초반 8건.
    _write_csv(p2, 6, 1.0, 2.0, -2.0, 100000, 5000.0)  # 중형 오전 6건.

    rep = edge_report_from_csvs([p1, p2])
    assert rep["sources"] == 2
    assert rep["pooled_trades"] == 14
    assert "global" in rep
    assert "segments" in rep
    # global edge_ratio: 풀 평균MFE=(8*4+6*2)/14=44/14; 평균|MAE|=(8*1+6*2)/14=20/14.
    assert abs(rep["global"]["edge_ratio"] - ((44 / 14) / (20 / 14))) < 1e-9
    # 세그먼트 축 키 존재.
    for axis in ("market_cap", "time", "cross"):
        assert axis in rep["segments"]


def test_edge_report_from_csvs_skips_missing_file(tmp_path):
    """없는 파일 경로는 무예외로 건너뛰고 존재하는 파일만 풀링한다."""
    p1 = os.path.join(str(tmp_path), "a.csv")
    _write_csv(p1, 5, 1.0, 3.0, -1.0, 90100, 500.0)
    missing = os.path.join(str(tmp_path), "nope_xyz.csv")
    rep = edge_report_from_csvs([p1, missing])
    assert rep["sources"] == 1
    assert rep["pooled_trades"] == 5


def test_edge_report_from_csvs_empty_pool_insufficient():
    """전부 없는 파일 → 빈 풀 → insufficient(무예외)."""
    rep = edge_report_from_csvs(["does_not_exist_1.csv", "does_not_exist_2.csv"])
    assert rep == {"insufficient": True, "pooled_trades": 0}
    # 빈 리스트도 insufficient.
    assert edge_report_from_csvs([]) == {"insufficient": True, "pooled_trades": 0}
