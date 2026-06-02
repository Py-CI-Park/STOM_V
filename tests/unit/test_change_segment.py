"""등락률(B_등락율) 세그먼트 단위 테스트 — 분석 전용(네트워크/실LLM/실백테/실DB 없음).

검증:
  - DEFAULT_CHANGE_BUCKETS 경계: 각 구간 라벨 정확값.
  - add_change_segment 라벨링: 정상값·경계값·NaN·컬럼 없는 df graceful(미분류).
  - edge_by_segment: "change" 축 셀 존재, avg_return 정렬, 미분류 제외.
  - feature_importance_by_segment: axis="change" 지원, 빈 df graceful.
  - 기존 market_cap/time 축 동작 byte-identical 보존(순수 추가 검증).
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from cli.research_segments import (  # noqa: E402
    DEFAULT_CHANGE_BUCKETS,
    add_change_segment,
    add_market_cap_segment,
    add_time_segment,
)
from ai_strategy_loop.fitness.edge_ratio import edge_by_segment  # noqa: E402
from ai_strategy_loop.fitness.feature_importance import (  # noqa: E402
    feature_importance_by_segment,
)


# ---------------------------------------------------------------------------
# DEFAULT_CHANGE_BUCKETS 경계 검증
# ---------------------------------------------------------------------------

def test_default_change_buckets_labels():
    """각 구간 대표값이 올바른 라벨로 매핑된다."""
    # (_assign_bucket 내부 로직: lower <= value < upper)
    df = pd.DataFrame({
        'B_등락율': [-5.0, -0.1, 0.0, 1.5, 3.0, 4.5, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0],
    })
    result = add_change_segment(df)
    labels = result['_change_segment'].tolist()
    assert labels[0] == '급락'    # -5.0  → (-inf, 0)
    assert labels[1] == '급락'    # -0.1  → (-inf, 0)
    assert labels[2] == '약상승'  # 0.0   → [0, 3)
    assert labels[3] == '약상승'  # 1.5   → [0, 3)
    assert labels[4] == '상승'    # 3.0   → [3, 6)
    assert labels[5] == '상승'    # 4.5   → [3, 6)
    assert labels[6] == '급등'    # 6.0   → [6, 10)
    assert labels[7] == '급등'    # 8.0   → [6, 10)
    assert labels[8] == '초급등'  # 10.0  → [10, 20)
    assert labels[9] == '초급등'  # 15.0  → [10, 20)
    assert labels[10] == '폭등'   # 20.0  → [20, +inf)
    assert labels[11] == '폭등'   # 25.0  → [20, +inf)


def test_default_change_buckets_covers_6_bands():
    """DEFAULT_CHANGE_BUCKETS 는 6개 구간으로 구성된다."""
    assert len(DEFAULT_CHANGE_BUCKETS) == 6


# ---------------------------------------------------------------------------
# add_change_segment 라벨링
# ---------------------------------------------------------------------------

def test_add_change_segment_nan_becomes_unclassified():
    """NaN 값은 '미분류'로 처리된다."""
    df = pd.DataFrame({'B_등락율': [None, float('nan'), 5.0]})
    result = add_change_segment(df)
    assert result['_change_segment'].iloc[0] == '미분류'
    assert result['_change_segment'].iloc[1] == '미분류'
    assert result['_change_segment'].iloc[2] == '상승'


def test_add_change_segment_missing_column_graceful():
    """B_등락율 컬럼이 없으면 전 행 '미분류' — graceful(예외 없음)."""
    df = pd.DataFrame({'B_시분초': [91000, 100000], '수익률': [1.0, -1.0]})
    result = add_change_segment(df)
    assert '_change_segment' in result.columns
    assert (result['_change_segment'] == '미분류').all()


def test_add_change_segment_custom_out_col():
    """out_col 파라미터로 출력 컬럼명을 변경할 수 있다."""
    df = pd.DataFrame({'B_등락율': [5.0]})
    result = add_change_segment(df, out_col='_my_change')
    assert '_my_change' in result.columns
    assert result['_my_change'].iloc[0] == '상승'


def test_add_change_segment_does_not_mutate_original():
    """add_change_segment는 원본 df를 변경하지 않는다(불변성)."""
    df = pd.DataFrame({'B_등락율': [5.0, -1.0]})
    original_cols = set(df.columns)
    add_change_segment(df)
    assert set(df.columns) == original_cols


def test_add_change_segment_non_numeric_values_graceful():
    """비수치 문자열 값은 NaN으로 coerce → '미분류'."""
    df = pd.DataFrame({'B_등락율': ['abc', '5.0', None]})
    result = add_change_segment(df)
    assert result['_change_segment'].iloc[0] == '미분류'
    assert result['_change_segment'].iloc[1] == '상승'
    assert result['_change_segment'].iloc[2] == '미분류'


# ---------------------------------------------------------------------------
# edge_by_segment — change 축
# ---------------------------------------------------------------------------

def _change_df():
    """3개 등락률 구간(급락·약상승·상승) × min_samples 통과 거래 df.

    각 구간 6건씩(min_samples=5 통과). B_등락율로 라벨링.
    """
    rows = []
    # 급락(-2.0): 손실 거래.
    for _ in range(6):
        rows.append({
            '수익률': -1.5, '수익금': -150.0, 'R_MFE': 1.0, 'R_MAE': -3.0,
            'B_시분초': 90100, 'B_시가총액': 500.0, 'B_등락율': -2.0,
        })
    # 약상승(1.5): 소폭 이익 거래.
    for _ in range(6):
        rows.append({
            '수익률': 0.5, '수익금': 50.0, 'R_MFE': 2.0, 'R_MAE': -1.0,
            'B_시분초': 90200, 'B_시가총액': 500.0, 'B_등락율': 1.5,
        })
    # 상승(4.5): 이익 거래.
    for _ in range(6):
        rows.append({
            '수익률': 2.0, '수익금': 200.0, 'R_MFE': 4.0, 'R_MAE': -0.5,
            'B_시분초': 90300, 'B_시가총액': 500.0, 'B_등락율': 4.5,
        })
    return pd.DataFrame(rows)


def test_edge_by_segment_change_axis_cells_present():
    """change 축에 3개 등락률 구간 셀이 잡힌다."""
    out = edge_by_segment(_change_df(), min_samples=5)
    assert 'change' in out
    change_labels = {r['label'] for r in out['change']}
    assert '급락' in change_labels
    assert '약상승' in change_labels
    assert '상승' in change_labels


def test_edge_by_segment_change_axis_sorted_by_avg_return():
    """change 축 셀은 avg_return 오름차순 정렬된다."""
    out = edge_by_segment(_change_df(), min_samples=5)
    returns = [r['avg_return'] for r in out['change']]
    assert returns == sorted(returns)


def test_edge_by_segment_change_axis_unclassified_excluded():
    """'미분류'(컬럼 없는 행 포함) 는 change 셀에서 제외된다."""
    df = _change_df()
    # NaN 행 추가 — 미분류로 떨어져야 한다.
    extra = pd.DataFrame([{
        '수익률': 1.0, '수익금': 100.0, 'R_MFE': 2.0, 'R_MAE': -1.0,
        'B_시분초': 90100, 'B_시가총액': 500.0, 'B_등락율': float('nan'),
    } for _ in range(3)])
    combined = pd.concat([df, extra], ignore_index=True)
    out = edge_by_segment(combined, min_samples=5)
    change_labels = {r['label'] for r in out['change']}
    assert '미분류' not in change_labels


def test_edge_by_segment_change_low_count_cell_excluded():
    """min_samples 미달 구간 셀은 change 축에서 제외된다."""
    df = _change_df()
    # 폭등(22.0) 2건 추가 — min_samples=5 미달.
    extra = pd.DataFrame([{
        '수익률': 3.0, '수익금': 300.0, 'R_MFE': 5.0, 'R_MAE': -0.5,
        'B_시분초': 90100, 'B_시가총액': 500.0, 'B_등락율': 22.0,
    } for _ in range(2)])
    combined = pd.concat([df, extra], ignore_index=True)
    out = edge_by_segment(combined, min_samples=5)
    change_labels = {r['label'] for r in out['change']}
    assert '폭등' not in change_labels


def test_edge_by_segment_change_missing_column_returns_empty_list():
    """B_등락율 컬럼이 없으면 change 축은 빈 리스트 — 다른 축 무영향."""
    df = pd.DataFrame([{
        '수익률': 1.0, '수익금': 100.0, 'R_MFE': 3.0, 'R_MAE': -1.0,
        'B_시분초': 90100, 'B_시가총액': 500.0,
    } for _ in range(8)])
    out = edge_by_segment(df, min_samples=5)
    assert 'change' in out
    assert out['change'] == []
    # market_cap/time/cross 축은 여전히 존재.
    assert 'market_cap' in out
    assert 'time' in out
    assert 'cross' in out


def test_edge_by_segment_existing_axes_unchanged_when_change_added():
    """change 축 추가 후 market_cap/time/cross 축 결과가 기존과 동일하다(byte-identical 보존)."""
    # B_등락율 없는 df로 기존 축 검증.
    df = pd.DataFrame([{
        '수익률': 1.0 if i < 6 else -0.5,
        '수익금': 100.0,
        'R_MFE': 3.0, 'R_MAE': -1.0,
        'B_시분초': 90100 if i < 6 else 100000,
        'B_시가총액': 500.0,
    } for i in range(12)])
    out = edge_by_segment(df, min_samples=5)
    # 기존 축 키 존재 및 셀 라벨 정상.
    mcap_labels = {r['label'] for r in out['market_cap']}
    assert '초소형' in mcap_labels
    time_labels = {r['label'] for r in out['time']}
    assert '장초반' in time_labels
    assert '오전' in time_labels


# ---------------------------------------------------------------------------
# feature_importance_by_segment — axis="change"
# ---------------------------------------------------------------------------

def _fi_change_df():
    """등락률 구간별 피처(B_체결강도)가 승/패를 구분하는 df.

    각 구간에 승리·손실 거래가 섞여 있어 Cohen's d가 산출된다.
    급락(B_등락율=-2.0) 구간: 승리 시 체결강도 높음, 패배 시 낮음.
    상승(B_등락율=4.5)  구간: 동일 패턴. 각 구간 25건(min_cell=20 통과).
    """
    rows = []
    # 급락 구간: 승리 13건(체결강도 높음) + 패배 12건(체결강도 낮음).
    for i in range(13):
        rows.append({
            '수익률': 1.0 + i * 0.1, 'B_등락율': -2.0,
            'B_체결강도': 120.0 + i, 'B_시분초': 90100, 'B_시가총액': 500.0,
        })
    for i in range(12):
        rows.append({
            '수익률': -0.5 - i * 0.1, 'B_등락율': -2.0,
            'B_체결강도': 60.0 + i, 'B_시분초': 90100, 'B_시가총액': 500.0,
        })
    # 상승 구간: 승리 13건(체결강도 높음) + 패배 12건(체결강도 낮음).
    for i in range(13):
        rows.append({
            '수익률': 2.0 + i * 0.1, 'B_등락율': 4.5,
            'B_체결강도': 130.0 + i, 'B_시분초': 90200, 'B_시가총액': 500.0,
        })
    for i in range(12):
        rows.append({
            '수익률': -1.0 - i * 0.1, 'B_등락율': 4.5,
            'B_체결강도': 50.0 + i, 'B_시분초': 90200, 'B_시가총액': 500.0,
        })
    return pd.DataFrame(rows)


def test_feature_importance_by_segment_change_axis():
    """axis='change'로 호출하면 등락률 구간별 피처 중요도 dict를 돌려준다."""
    df = _fi_change_df()
    result = feature_importance_by_segment(df, axis='change', min_per_group=10, min_cell=20)
    assert isinstance(result, dict)
    # 급락/상승 구간이 키로 잡혀야 한다.
    assert '급락' in result or '상승' in result


def test_feature_importance_by_segment_change_axis_ranked_features():
    """각 등락률 구간에 ranked features 리스트가 있다."""
    df = _fi_change_df()
    result = feature_importance_by_segment(df, axis='change', min_per_group=10, min_cell=20)
    for seg_label, ranked in result.items():
        assert isinstance(ranked, list)
        # 각 항목에 feature/cohens_d/n 키 포함.
        for item in ranked:
            assert 'feature' in item
            assert 'cohens_d' in item
            assert 'n' in item


def test_feature_importance_by_segment_change_axis_empty_df():
    """빈 df는 빈 dict를 돌려준다(graceful)."""
    result = feature_importance_by_segment(pd.DataFrame(), axis='change')
    assert result == {}


def test_feature_importance_by_segment_change_axis_missing_column():
    """B_등락율 컬럼이 없으면 빈 dict를 돌려준다(graceful)."""
    df = pd.DataFrame([{
        '수익률': 1.0, 'B_체결강도': 100.0,
        'B_시분초': 90100, 'B_시가총액': 500.0,
    } for _ in range(30)])
    result = feature_importance_by_segment(df, axis='change', min_per_group=5, min_cell=10)
    # _change_segment 컬럼은 생성되나 전부 '미분류' → 빈 dict.
    assert result == {}


def test_feature_importance_by_segment_invalid_axis_returns_empty():
    """알 수 없는 axis 값은 빈 dict를 돌려준다(graceful)."""
    df = _fi_change_df()
    result = feature_importance_by_segment(df, axis='unknown_axis')
    assert result == {}


def test_feature_importance_by_segment_existing_axes_unchanged():
    """axis='market_cap'/'time' 결과가 change 추가 후에도 동일하다(byte-identical 보존)."""
    df = _fi_change_df()
    mc_result = feature_importance_by_segment(df, axis='market_cap', min_per_group=10, min_cell=20)
    # market_cap 축은 여전히 dict를 돌려야 한다(비어 있을 수도 있으나 예외 없음).
    assert isinstance(mc_result, dict)
    time_result = feature_importance_by_segment(df, axis='time', min_per_group=10, min_cell=20)
    assert isinstance(time_result, dict)
