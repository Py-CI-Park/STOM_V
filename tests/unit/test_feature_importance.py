"""세그먼트별 승리-변수 피처 중요도 단위 테스트
(분석 전용 — 네트워크/실LLM/실백테/실DB 없음, tmp만).

검증:
  - compute_feature_importance: 한 피처가 승자를 깨끗이 분리(승자=높은 B_회전율) →
    cohens_d 양수 & 랭킹 1위; 상수 피처는 건너뜀; win_rate_top_q/win_rate_bot_q 분리;
    수익률/B_* 컬럼 부재 graceful([]).
  - feature_importance_by_segment: 시총축으로 셀 분할, 저(min_cell)빈도 셀 제외,
    '미분류' 제외; 시간축; 잘못된 axis → {}.
  - feature_importance_from_csvs: tmp CSV 2개 풀링 → pooled_trades=합, global/by_segment
    존재; 없는 파일 무예외 건너뜀; 빈 풀 → insufficient.

실DB/백테 미사용: tmp 경로 CSV + 손계산 DataFrame만 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.feature_importance import (  # noqa: E402
    compute_feature_importance,
    feature_importance_by_segment,
    feature_importance_from_csvs,
)


# ---------------------------------------------------------------------------
# compute_feature_importance
# ---------------------------------------------------------------------------
def _separating_df(n=40):
    """한 피처(B_회전율)가 승/패를 깨끗이 가르는 df.

    승자 n건(수익률 +1.0, B_회전율 높음 ~10), 패자 n건(수익률 -1.0, B_회전율 낮음 ~1).
    B_등락율은 승/패 무관(노이즈), B_상수는 상수(변별 0 → 건너뜀)로 둔다.
    """
    rows = []
    for i in range(n):
        # 승자: 높은 회전율(10 근방, 약간의 분산).
        rows.append({"수익률": 1.0 + (i % 3) * 0.1, "B_회전율": 10.0 + (i % 5) * 0.2,
                     "B_등락율": (i % 7) * 1.0, "B_상수": 5.0})
    for i in range(n):
        # 패자: 낮은 회전율(1 근방).
        rows.append({"수익률": -1.0 - (i % 3) * 0.1, "B_회전율": 1.0 + (i % 5) * 0.2,
                     "B_등락율": (i % 7) * 1.0, "B_상수": 5.0})
    return pd.DataFrame(rows)


def test_compute_feature_importance_ranks_separating_feature_first():
    """승자를 깨끗이 가르는 B_회전율이 cohens_d 양수 & 랭킹 1위; 상수 피처는 제외."""
    ranked = compute_feature_importance(_separating_df(), min_per_group=10)
    assert len(ranked) >= 1
    # 회전율이 가장 잘 가른다(abs(d) 최대) → 1위.
    assert ranked[0]["feature"] == "B_회전율"
    # 승자가 높은 회전율 → mean_win > mean_lose → cohens_d 양수.
    assert ranked[0]["cohens_d"] > 0
    assert ranked[0]["mean_win"] > ranked[0]["mean_lose"]
    # n = 유효 win+lose 거래 수(40+40).
    assert ranked[0]["n"] == 80
    # 상수 피처(B_상수)는 합동표준편차 ~0 → 변별 불가 → 결과에서 제외.
    assert all(r["feature"] != "B_상수" for r in ranked)
    # 랭킹은 abs(cohens_d) 내림차순.
    abs_ds = [abs(r["cohens_d"]) for r in ranked]
    assert abs_ds == sorted(abs_ds, reverse=True)


def test_compute_feature_importance_quartile_win_rates():
    """B_회전율 상위 사분위 승률 > 하위 사분위 승률(승자가 고회전율이므로)."""
    ranked = compute_feature_importance(_separating_df(), min_per_group=10)
    rec = next(r for r in ranked if r["feature"] == "B_회전율")
    assert rec["win_rate_top_q"] is not None
    assert rec["win_rate_bot_q"] is not None
    # 상위 사분위(고회전율=승자)는 승률 높고, 하위 사분위(저회전율=패자)는 낮다.
    assert rec["win_rate_top_q"] > rec["win_rate_bot_q"]


def test_compute_feature_importance_min_per_group_filters():
    """양 그룹 중 한쪽이라도 min_per_group 미달이면 그 피처는 제외."""
    df = _separating_df(n=40)
    # min_per_group=50 → win/lose 각 40건 < 50 → 모든 피처 제외 → 빈 리스트.
    assert compute_feature_importance(df, min_per_group=50) == []


def test_compute_feature_importance_missing_return_column_graceful():
    """'수익률' 컬럼이 없으면 승패를 가를 수 없어 빈 리스트(무예외)."""
    df = pd.DataFrame({"B_회전율": [1.0, 2.0, 3.0], "B_등락율": [0.1, 0.2, 0.3]})
    assert compute_feature_importance(df) == []


def test_compute_feature_importance_no_b_columns_graceful():
    """B_* 진입 피처가 하나도 없으면 빈 리스트(무예외)."""
    df = pd.DataFrame({"수익률": [1.0, -1.0, 2.0], "종목명": ["A", "B", "C"]})
    assert compute_feature_importance(df) == []


def test_compute_feature_importance_empty_df_graceful():
    """빈 df는 빈 리스트(무예외)."""
    assert compute_feature_importance(pd.DataFrame()) == []
    assert compute_feature_importance(None) == []


# ---------------------------------------------------------------------------
# feature_importance_by_segment
# ---------------------------------------------------------------------------
def _segment_df():
    """2개 시총 tier(초소형<1000·중형 3000~10000)별로 분리 신호가 다른 df.

    초소형: B_회전율이 승/패를 가른다(승자 고회전율). 30건씩 승/패.
    중형: B_등락율이 승/패를 가른다(승자 고등락율). 30건씩 승/패.
    각 셀 60건(min_cell=20 통과). B_시분초/B_시가총액은 라벨링용.
    """
    rows = []
    # 초소형(시총 500): 승자=고회전율, 패자=저회전율. 등락율은 노이즈.
    for i in range(30):
        rows.append({"수익률": 1.0, "B_회전율": 10.0 + (i % 5) * 0.2, "B_등락율": (i % 4) * 1.0,
                     "B_시분초": 90100, "B_시가총액": 500.0})
    for i in range(30):
        rows.append({"수익률": -1.0, "B_회전율": 1.0 + (i % 5) * 0.2, "B_등락율": (i % 4) * 1.0,
                     "B_시분초": 90100, "B_시가총액": 500.0})
    # 중형(시총 5000): 승자=고등락율, 패자=저등락율. 회전율은 노이즈.
    for i in range(30):
        rows.append({"수익률": 1.0, "B_회전율": (i % 5) * 0.2, "B_등락율": 8.0 + (i % 4) * 0.3,
                     "B_시분초": 100000, "B_시가총액": 5000.0})
    for i in range(30):
        rows.append({"수익률": -1.0, "B_회전율": (i % 5) * 0.2, "B_등락율": 1.0 + (i % 4) * 0.3,
                     "B_시분초": 100000, "B_시가총액": 5000.0})
    return pd.DataFrame(rows)


def test_feature_importance_by_segment_market_cap_splits():
    """시총축 → 초소형/중형 셀 존재, 각 셀에서 다른 피처가 가른다."""
    out = feature_importance_by_segment(_segment_df(), axis="market_cap", min_cell=20)
    assert "초소형" in out
    assert "중형" in out
    # 초소형 셀은 B_회전율이 가장 잘 가른다(랭킹 1위).
    assert out["초소형"][0]["feature"] == "B_회전율"
    # 중형 셀은 B_등락율이 가장 잘 가른다(랭킹 1위) — 세그먼트별 신호 차이.
    assert out["중형"][0]["feature"] == "B_등락율"


def test_feature_importance_by_segment_skips_low_count_and_unclassified():
    """min_cell 미달 셀 + '미분류'(시총 라벨 부재) 셀은 제외된다."""
    df = _segment_df()
    # 표본 5건짜리(min_cell 미달) 대형 셀 추가 → market_cap '대형' 셀은 제외돼야 한다.
    extra = pd.DataFrame([
        {"수익률": 1.0, "B_회전율": 5.0, "B_등락율": 5.0, "B_시분초": 90100, "B_시가총액": 20000.0}
        for _ in range(5)
    ])
    out = feature_importance_by_segment(pd.concat([df, extra], ignore_index=True),
                                        axis="market_cap", min_cell=20)
    assert "대형" not in out  # 5건 < min_cell=20.
    assert "미분류" not in out


def test_feature_importance_by_segment_time_axis():
    """시간축 → 시간대 셀(장초반/오전) 분할; 라벨 키 존재."""
    out = feature_importance_by_segment(_segment_df(), axis="time", min_cell=20)
    # 초소형은 09:01(장초반), 중형은 10:00(오전)에 거래.
    assert "장초반" in out
    assert "오전" in out


def test_feature_importance_by_segment_bad_axis_empty():
    """알 수 없는 axis는 빈 dict(무예외)."""
    assert feature_importance_by_segment(_segment_df(), axis="bogus") == {}
    assert feature_importance_by_segment(pd.DataFrame(), axis="market_cap") == {}


# ---------------------------------------------------------------------------
# feature_importance_from_csvs
# ---------------------------------------------------------------------------
_HEADER = "종목명,수익률,B_회전율,B_등락율,B_시분초,B_시가총액\n"


def _write_csv(path, rows):
    """rows(=(수익률,회전율,등락율,시분초,시총) 튜플 리스트)를 utf-8-sig CSV로 떨군다."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(_HEADER)
        for ret, turn, chg, sigun, mcap in rows:
            fh.write(f"A종목,{ret},{turn},{chg},{sigun},{mcap}\n")


def _csv_rows(n, win, mcap):
    """n건: win=True면 수익률+1.0·고회전율, False면 -1.0·저회전율(초소형/중형 라벨용 mcap)."""
    out = []
    for i in range(n):
        if win:
            out.append((1.0, 10.0 + (i % 5) * 0.2, (i % 4) * 1.0, 90100, mcap))
        else:
            out.append((-1.0, 1.0 + (i % 5) * 0.2, (i % 4) * 1.0, 90100, mcap))
    return out


def test_feature_importance_from_csvs_pools_two_files(tmp_path):
    """CSV 2개 풀링 → pooled_trades = 합, global/by_segment 키 존재."""
    p1 = os.path.join(str(tmp_path), "a.csv")
    p2 = os.path.join(str(tmp_path), "b.csv")
    _write_csv(p1, _csv_rows(15, True, 500.0) + _csv_rows(15, False, 500.0))   # 초소형 30건.
    _write_csv(p2, _csv_rows(15, True, 5000.0) + _csv_rows(15, False, 5000.0))  # 중형 30건.

    rep = feature_importance_from_csvs([p1, p2], axis="market_cap")
    assert rep["sources"] == 2
    assert rep["pooled_trades"] == 60
    assert rep["axis"] == "market_cap"
    assert "global" in rep
    assert "by_segment" in rep
    # global: B_회전율이 가장 잘 가른다(승자 고회전율).
    assert rep["global"][0]["feature"] == "B_회전율"
    # by_segment: 초소형/중형 셀 존재.
    assert "초소형" in rep["by_segment"]
    assert "중형" in rep["by_segment"]


def test_feature_importance_from_csvs_skips_missing_file(tmp_path):
    """없는 파일 경로는 무예외로 건너뛰고 존재하는 파일만 풀링한다."""
    p1 = os.path.join(str(tmp_path), "a.csv")
    _write_csv(p1, _csv_rows(15, True, 500.0) + _csv_rows(15, False, 500.0))
    missing = os.path.join(str(tmp_path), "nope_xyz.csv")
    rep = feature_importance_from_csvs([p1, missing])
    assert rep["sources"] == 1
    assert rep["pooled_trades"] == 30


def test_feature_importance_from_csvs_empty_pool_insufficient():
    """전부 없는 파일 → 빈 풀 → insufficient(무예외)."""
    rep = feature_importance_from_csvs(["does_not_exist_1.csv", "does_not_exist_2.csv"])
    assert rep == {"insufficient": True, "pooled_trades": 0}
    # 빈 리스트도 insufficient.
    assert feature_importance_from_csvs([]) == {"insufficient": True, "pooled_trades": 0}
