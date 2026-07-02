"""T2.2 Analysis Card v2 생산자 단위 테스트 (네트워크 없음, 합성 거래행만).

검증:
  - build_analysis_card: 필수 섹션 존재, schema/authority, result_meta 지표 추출
    (영/한 별칭), 세그먼트 히트맵(시간대×시가총액 교차 셀), avoid/prefer zone,
    피처 중요도(Cohen's d), MFE/MAE 요약, edge_ratio 수기 검증.
  - 정직 라벨: 거래행/컬럼/메타가 없으면 'insufficient_data' + 사유(빈 값 조작 금지).
  - root_cause/mutation_axis: 실제 ablation 파이프라인(파싱→ablate) 결합,
    세그먼트 손실 집중 결합, 후보 1~3개 상한, ablation dict(Mapping) 수용.
  - 권한 밀반입 가드: can_promote 등 truthy → ValueError.
  - JSON 직렬화/역직렬화 라운드트립 + 결정론(byte-동일), 스키마 불일치 거부.
  - render_card_md: 사람이 읽는 markdown, insufficient 라벨 노출.
  - 원본 trades_df 불변성.
"""

import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.ablation import (  # noqa: E402
    ablate,
    parse_top_level_clauses,
)
from ai_strategy_loop.autopsy.analysis_card import (  # noqa: E402
    ANALYSIS_CARD_SCHEMA,
    CARD_AUTHORITY,
    SECTION_INSUFFICIENT,
    SECTION_OK,
    build_analysis_card,
    card_from_json,
    card_to_json,
    render_card_md,
)

# 카드 최상위 필수 키(임무 계약).
REQUIRED_KEYS = (
    "schema", "authority", "trade_count", "metrics", "segment_heatmap",
    "mfe_mae", "edge_ratio", "feature_importance", "avoid_zones", "prefer_zones",
    "correlation_redundancy", "root_cause", "mutation_axis", "risk_note",
)

# 분석 섹션(모두 status 를 가진 dict).
SECTION_KEYS = (
    "metrics", "segment_heatmap", "mfe_mae", "edge_ratio", "feature_importance",
    "avoid_zones", "prefer_zones", "correlation_redundancy", "root_cause", "mutation_axis",
)

META = {"profit": 120000.0, "mdd": 3.5, "trades": 24, "win_rate": 0.5, "payoff": 1.4}


def make_trades(n_win: int = 12, n_loss: int = 12, with_r: bool = True) -> pd.DataFrame:
    """합성 거래행 — 승자는 장초반×소형(체결강도 높음), 패자는 오전×대형(낮음)."""
    rows = []
    for i in range(n_win):
        row = {
            "종목명": "승리주%02d" % i,
            "종목코드": "10%04d" % i,
            "매수시간": 202305150905 + i,
            "매도시간": 202305150935 + i,
            "보유시간": 30,
            "매수가": 10000, "매도가": 10200,
            "수익률": 2.0 + 0.05 * (i % 4),
            "수익금": 20000,
            "매도조건": "익절",
            "B_시분초": 90500 + 10 * i,       # 장초반(90000~93000)
            "B_시가총액": 2000 + 10 * (i % 3),  # 소형(1000~3000억)
            "B_등락율": 5.0 + 0.1 * i,
            "B_체결강도": 150 + (i % 5),
            "B_당일거래대금": 500 + i,
            "B_매수총잔량": 1000 + i,
            "B_매도총잔량": 900 + i,
        }
        if with_r:
            row.update({
                "R_매수후최고수익률": 3.0 + 0.1 * (i % 3),
                "R_매수후최저수익률": -0.5,
                "R_MFE": 3.0, "R_MAE": -0.5,
            })
        rows.append(row)
    for i in range(n_loss):
        row = {
            "종목명": "손실주%02d" % i,
            "종목코드": "20%04d" % i,
            "매수시간": 202305151005 + i,
            "매도시간": 202305151035 + i,
            "보유시간": 30,
            "매수가": 10000, "매도가": 9850,
            "수익률": -1.5 - 0.05 * (i % 4),
            "수익금": -15000,
            "매도조건": "손절",
            "B_시분초": 100500 + 10 * i,       # 오전(93000~113000)
            "B_시가총액": 20000 + 10 * (i % 3),  # 대형(10000~50000억)
            "B_등락율": 1.0 + 0.1 * i,
            "B_체결강도": 80 + (i % 5),
            "B_당일거래대금": 300 + i,
            "B_매수총잔량": 500 + i,
            "B_매도총잔량": 800 + i,
        }
        if with_r:
            row.update({
                "R_매수후최고수익률": 0.3,
                "R_매수후최저수익률": -2.5 - 0.1 * (i % 3),
                "R_MFE": 0.3, "R_MAE": -2.5,
            })
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 카드 구조 / 지표
# ---------------------------------------------------------------------------

def test_card_required_sections_exist():
    card = build_analysis_card(META, make_trades())
    for key in REQUIRED_KEYS:
        assert key in card, key
    assert card["schema"] == ANALYSIS_CARD_SCHEMA == "analysis_card_v2"
    assert card["authority"] == CARD_AUTHORITY
    assert card["trade_count"] == 24
    for key in SECTION_KEYS:
        assert card[key]["status"] in (SECTION_OK, SECTION_INSUFFICIENT), key
    assert isinstance(card["risk_note"], str) and card["risk_note"]


def test_metrics_section_ok():
    card = build_analysis_card(META, make_trades())
    metrics = card["metrics"]
    assert metrics["status"] == SECTION_OK
    assert metrics["values"]["profit"] == pytest.approx(120000.0)
    assert metrics["values"]["mdd"] == pytest.approx(3.5)
    assert metrics["values"]["trades"] == 24
    assert metrics["values"]["win_rate"] == pytest.approx(0.5)
    assert metrics["values"]["payoff"] == pytest.approx(1.4)
    assert metrics["missing"] == []


def test_metrics_korean_aliases_and_partial_missing():
    card = build_analysis_card({"수익금합계": 5000.0, "승률": 0.6}, make_trades())
    metrics = card["metrics"]
    assert metrics["status"] == SECTION_OK
    assert metrics["values"]["profit"] == pytest.approx(5000.0)
    assert metrics["values"]["win_rate"] == pytest.approx(0.6)
    assert set(metrics["missing"]) == {"mdd", "trades", "payoff"}


def test_metrics_insufficient_without_meta():
    card = build_analysis_card(None, make_trades())
    assert card["metrics"]["status"] == SECTION_INSUFFICIENT
    assert "result_meta" in card["metrics"]["note"]


# ---------------------------------------------------------------------------
# 세그먼트 히트맵 / avoid·prefer zone
# ---------------------------------------------------------------------------

def test_segment_heatmap_cross_cells():
    card = build_analysis_card(META, make_trades())
    heatmap = card["segment_heatmap"]
    assert heatmap["status"] == SECTION_OK
    labels = {cell["label"]: cell for cell in heatmap["cells"]}
    assert "장초반×소형" in labels and "오전×대형" in labels
    assert labels["장초반×소형"]["count"] == 12
    assert labels["오전×대형"]["count"] == 12
    assert labels["장초반×소형"]["avg_return"] > 0
    assert labels["오전×대형"]["avg_return"] < 0


def test_avoid_prefer_zones():
    card = build_analysis_card(META, make_trades())
    avoid, prefer = card["avoid_zones"], card["prefer_zones"]
    assert avoid["status"] == SECTION_OK and prefer["status"] == SECTION_OK
    avoid_labels = [z["label"] for z in avoid["zones"]]
    prefer_labels = [z["label"] for z in prefer["zones"]]
    assert "오전×대형" in avoid_labels
    assert "장초반×소형" in prefer_labels
    assert all(z["return_diff"] < 0 for z in avoid["zones"])
    assert all(z["return_diff"] > 0 for z in prefer["zones"])


# ---------------------------------------------------------------------------
# 피처 중요도 / MFE·MAE / edge ratio
# ---------------------------------------------------------------------------

def test_feature_importance_cohens_d():
    card = build_analysis_card(META, make_trades())
    section = card["feature_importance"]
    assert section["status"] == SECTION_OK
    assert section["win_count"] == 12 and section["loss_count"] == 12
    by_feature = {f["feature"]: f for f in section["features"]}
    assert "B_체결강도" in by_feature
    strength = by_feature["B_체결강도"]
    assert strength["cohens_d"] > 0  # 승자에서 체결강도가 더 컸다.
    assert strength["stom_var"] == "체결강도"
    assert strength["win_mean"] > strength["loss_mean"]


def test_mfe_mae_values():
    df = make_trades()
    card = build_analysis_card(META, df)
    section = card["mfe_mae"]
    assert section["status"] == SECTION_OK
    assert section["mfe_column"] == "R_매수후최고수익률"
    assert section["mae_column"] == "R_매수후최저수익률"
    wins = df[df["수익률"] > 0]
    losses = df[df["수익률"] <= 0]
    assert section["avg_mfe_winners"] == pytest.approx(wins["R_매수후최고수익률"].mean(), abs=1e-6)
    assert section["avg_realized_winners"] == pytest.approx(wins["수익률"].mean(), abs=1e-6)
    assert section["giveback_gap_winners"] == pytest.approx(
        wins["R_매수후최고수익률"].mean() - wins["수익률"].mean(), abs=1e-6)
    assert section["avg_mae_losers"] == pytest.approx(losses["R_매수후최저수익률"].mean(), abs=1e-6)
    assert section["worst_mae_losers"] == pytest.approx(losses["R_매수후최저수익률"].min(), abs=1e-6)


def test_edge_ratio_manual():
    df = make_trades()
    card = build_analysis_card(META, df)
    section = card["edge_ratio"]
    assert section["status"] == SECTION_OK
    expected = df["R_매수후최고수익률"].mean() / df["R_매수후최저수익률"].abs().mean()
    assert section["edge_ratio"] == pytest.approx(expected, abs=1e-6)
    assert section["rows"] == 24


def test_mfe_mae_and_edge_insufficient_without_r_columns():
    card = build_analysis_card(META, make_trades(with_r=False))
    assert card["mfe_mae"]["status"] == SECTION_INSUFFICIENT
    assert "MFE/MAE" in card["mfe_mae"]["note"]
    assert card["edge_ratio"]["status"] == SECTION_INSUFFICIENT
    assert card["edge_ratio"]["edge_ratio"] is None


# ---------------------------------------------------------------------------
# 정직 라벨 (insufficient_data)
# ---------------------------------------------------------------------------

def test_all_data_sections_insufficient_without_trades():
    card = build_analysis_card(None, None)
    assert card["trade_count"] == 0
    for key in SECTION_KEYS:
        assert card[key]["status"] == SECTION_INSUFFICIENT, key
    assert "데이터 부족 섹션" in card["risk_note"]


def test_insufficient_below_min_trades():
    small = make_trades(n_win=3, n_loss=3)  # 6건 < 기본 min_trades=10
    card = build_analysis_card(META, small)
    assert card["trade_count"] == 6
    assert card["segment_heatmap"]["status"] == SECTION_INSUFFICIENT
    assert card["feature_importance"]["status"] == SECTION_INSUFFICIENT
    # 메타 지표는 거래행과 무관하게 살아있다.
    assert card["metrics"]["status"] == SECTION_OK


def test_empty_dataframe_treated_as_no_trades():
    card = build_analysis_card(META, pd.DataFrame())
    assert card["trade_count"] == 0
    assert card["segment_heatmap"]["status"] == SECTION_INSUFFICIENT
    assert card["mfe_mae"]["status"] == SECTION_INSUFFICIENT


# ---------------------------------------------------------------------------
# root_cause / mutation_axis (ablation + 세그먼트 결합)
# ---------------------------------------------------------------------------

CONDITION_CODE = (
    "매수 = False\n"
    "if 체결강도 > 200 and 등락율 > 0:\n"
    "    매수 = True\n"
    "if 매수:\n"
    "    self.Buy()\n"
)


def _real_ablation(df):
    clauses = parse_top_level_clauses(CONDITION_CODE)
    return ablate(clauses, df)


def test_root_cause_with_real_ablation_pipeline():
    df = make_trades()
    ablation = _real_ablation(df)
    assert ablation.status == "ok"
    card = build_analysis_card(META, df, ablation)
    root = card["root_cause"]
    assert root["status"] == SECTION_OK
    assert 1 <= len(root["candidates"]) <= 3
    first = root["candidates"][0]
    # 체결강도 > 200 은 전 행을 단독 차단(평균 수익률 > 0) → harmful 최우선.
    assert first["source"] == "ablation"
    assert first["verdict"] == "harmful"
    assert "체결강도 > 200" in first["cause"]
    assert first["rank"] == 1 and first["evidence"]
    # 세그먼트 손실 집중 후보도 결합된다.
    assert any(c["source"] == "segment" for c in root["candidates"])
    # 리스크 노트에 행 기반 근사 경고가 실린다.
    assert "행 기반 근사" in card["risk_note"]


def test_root_cause_accepts_ablation_mapping():
    df = make_trades()
    card = build_analysis_card(META, df, _real_ablation(df).to_dict())
    root = card["root_cause"]
    assert root["status"] == SECTION_OK
    assert root["candidates"][0]["source"] == "ablation"


def test_root_cause_from_segment_only_without_ablation():
    card = build_analysis_card(META, make_trades(), None)
    root = card["root_cause"]
    assert root["status"] == SECTION_OK
    assert root["candidates"][0]["source"] == "segment"
    assert "오전×대형" in root["candidates"][0]["cause"]


def test_mutation_axis_from_root_cause():
    df = make_trades()
    card = build_analysis_card(META, df, _real_ablation(df))
    section = card["mutation_axis"]
    assert section["status"] == SECTION_OK
    assert len(section["axes"]) >= 1
    for axis in section["axes"]:
        assert axis["mutation_axis"]
        assert axis["expected_effect"]
        assert axis["risk_note"]
        assert axis["source"] in ("ablation", "segment")
    # 중복 없는 변이축.
    texts = [a["mutation_axis"] for a in section["axes"]]
    assert len(texts) == len(set(texts))


# 균일 수익률 합성 데이터는 읽기 전용 cli/analyzer 의 scipy t검정에서
#   catastrophic-cancellation RuntimeWarning 을 낸다(이 모듈 밖 경고 — 무해).
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_root_cause_insufficient_when_no_signal():
    # 전 거래가 같은 셀·같은 수익률 → return_diff 0 → 손실 집중 없음, ablation 없음.
    df = make_trades(n_win=12, n_loss=0)
    df = df.assign(수익률=2.0)
    card = build_analysis_card(META, df, None)
    assert card["root_cause"]["status"] == SECTION_INSUFFICIENT
    assert card["mutation_axis"]["status"] == SECTION_INSUFFICIENT


# ---------------------------------------------------------------------------
# 중복/상관
# ---------------------------------------------------------------------------

def test_correlation_redundancy_variable_pair():
    # 승자(소형·고체결강도) vs 패자(대형·저체결강도) → 시총↔체결강도 강한 음상관.
    card = build_analysis_card(META, make_trades())
    section = card["correlation_redundancy"]
    assert section["status"] == SECTION_OK
    pairs = {(p["feature_a"], p["feature_b"]): p["correlation"] for p in section["variable_pairs"]}
    hit = [(a, b) for (a, b) in pairs if {a, b} == {"B_시가총액", "B_체결강도"}]
    assert hit, pairs
    assert pairs[hit[0]] < -0.9


# ---------------------------------------------------------------------------
# 권한 가드 / 불변성
# ---------------------------------------------------------------------------

def test_authority_guard_raises():
    for key in ("can_promote", "can_export", "can_live", "promotion_eligible"):
        with pytest.raises(ValueError) as exc:
            build_analysis_card({"profit": 1.0, key: True}, make_trades())
        assert key in str(exc.value)
    # falsy 권한 키는 통과(밀반입이 아님).
    card = build_analysis_card({"profit": 1.0, "can_promote": False}, make_trades())
    assert card["schema"] == ANALYSIS_CARD_SCHEMA


def test_input_frame_not_mutated():
    df = make_trades()
    snapshot = df.copy(deep=True)
    build_analysis_card(META, df, _real_ablation(df))
    pd.testing.assert_frame_equal(df, snapshot)


# ---------------------------------------------------------------------------
# JSON 직렬화/역직렬화 / 결정론
# ---------------------------------------------------------------------------

def test_json_roundtrip_and_determinism():
    df = make_trades()
    card_a = build_analysis_card(META, df, _real_ablation(df))
    card_b = build_analysis_card(META, df, _real_ablation(df))
    json_a = card_to_json(card_a)
    json_b = card_to_json(card_b)
    assert json_a == json_b  # 동일 입력 → byte-동일(결정론).
    restored = card_from_json(json_a)
    assert restored == card_a
    # NaN 금지(allow_nan=False)로 표준 json 파서와 호환.
    assert json.loads(json_a)["schema"] == ANALYSIS_CARD_SCHEMA


def test_card_from_json_rejects_bad_input():
    with pytest.raises(ValueError):
        card_from_json(json.dumps({"schema": "something_else"}))
    with pytest.raises(ValueError):
        card_from_json(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError):
        card_from_json("not-json{{")


# ---------------------------------------------------------------------------
# markdown 렌더
# ---------------------------------------------------------------------------

def test_render_md_full_card():
    df = make_trades()
    card = build_analysis_card(META, df, _real_ablation(df))
    md = render_card_md(card)
    assert isinstance(md, str)
    assert md.startswith("# Analysis Card v2")
    for header in ("## 공식 지표", "## 세그먼트 히트맵", "## MFE/MAE 요약", "## Edge Ratio",
                   "## 피처 중요도", "## 회피 구간", "## 선호 구간", "## Root Cause 후보",
                   "## 변이축(mutation axis) 제안", "## 리스크 노트"):
        assert header in md, header
    assert "오전×대형" in md
    assert "체결강도 > 200" in md
    assert CARD_AUTHORITY in md


def test_render_md_insufficient_labels():
    card = build_analysis_card(None, None)
    md = render_card_md(card)
    assert "insufficient_data" in md
    assert "거래행 없음" in md
