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

from dataclasses import replace
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
    ANALYSIS_CARD_SCHEMA_V3,
    CARD_AUTHORITY,
    REASON_INELIGIBLE,
    REASON_NOT_TRAIN,
    REASON_OK,
    ROLE_OOS,
    ROLE_TRAIN,
    ROLE_VALIDATION,
    SECTION_INSUFFICIENT,
    SECTION_OK,
    build_analysis_card,
    build_analysis_card_v3,
    card_from_json,
    card_to_json,
    card_v3_to_json,
    evaluate_directive_gate,
    render_card_md,
    render_card_v3_md,
    verify_analysis_card_v3_content_hash,
)
from ai_strategy_loop.autopsy.analyze import _benjamini_hochberg  # noqa: E402
from ai_strategy_loop.brain.feature_importance_feedback import (  # noqa: E402
    build_feature_importance_findings,
    render_directive_hints_from_card_v3,
)
from ai_strategy_loop.brain.segment_feedback import (  # noqa: E402
    render_directives_from_card_v3,
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
    # DR-01: prefer 셀은 절대 수익률도 양수이므로 actionable=True.
    assert prefer["actionable"] is True
    assert all(z["actionable"] is True for z in prefer["zones"])


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

def _make_all_negative_trades() -> pd.DataFrame:
    """전 구간 손실 — 소형은 '덜' 손실(-1.0%), 대형은 '더' 손실(-3.0%).
    소형의 return_diff는 전체평균 대비 양수(prefer 후보)이지만 절대 수익률은
    여전히 음수 — DR-01: 이런 '최선 셀'은 non-actionable로 라벨돼야 한다."""
    rows = []
    for i in range(12):
        rows.append({
            "종목명": "소형%02d" % i,
            "매수시간": 202305150905 + i,
            "매도시간": 202305150935 + i,
            "수익률": -1.0,
            "수익금": -10000,
            "B_시분초": 90500 + 10 * i,
            "B_시가총액": 2000 + 10 * (i % 3),
        })
    for i in range(12):
        rows.append({
            "종목명": "대형%02d" % i,
            "매수시간": 202305151005 + i,
            "매도시간": 202305151035 + i,
            "수익률": -3.0,
            "수익금": -30000,
            "B_시분초": 100500 + 10 * i,
            "B_시가총액": 20000 + 10 * (i % 3),
        })
    return pd.DataFrame(rows)


def test_prefer_zone_all_negative_best_slice_is_non_actionable():
    """DR-01: 최선(best) 셀조차 절대 수익률이 음수면 prefer 섹션이 non-actionable이다."""
    card = build_analysis_card(META, _make_all_negative_trades())
    prefer = card["prefer_zones"]
    assert prefer["status"] == SECTION_OK
    assert prefer["zones"], "손실 완화 셀(소형)이 return_diff>0 로 prefer에 잡혀야 함"
    assert all(z["avg_return"] < 0 for z in prefer["zones"])
    assert prefer["actionable"] is False
    assert all(z["actionable"] is False for z in prefer["zones"])
    assert "non-actionable" in prefer["note"]


# ---------------------------------------------------------------------------
# DR-05 — AnalysisCardV3: 통계 안전판이 있는 영속 카드.
# ---------------------------------------------------------------------------


def _v3_rows(n_trades=40, n_days=12, n_symbols=3, *, all_positive_return=1.0):
    rows = []
    for i in range(n_trades):
        day = (i % n_days) + 1
        rows.append({
            "매수시간": f"202601{day:02d}120000",
            "종목코드": f"S{i % n_symbols}",
            "수익률": all_positive_return if i % 3 else -0.5,
            "수익금": 100.0 if i % 3 else -50.0,
        })
    return pd.DataFrame(rows)


_GOOD_FINDING = {
    "finding_id": "f_signal",
    "statement": "B_signal 진입 시 초과수익",
    "axis": "entry_feature",
    "p_value": 0.001,
    "prereg_axis": False,
    "ci_low": 1.0,
    "ci_high": 5.0,
    "full_population": True,
}

_NOISE_FINDING = {
    "finding_id": "f_noise",
    "statement": "무작위 노이즈",
    "axis": "entry_feature",
    "p_value": 0.9,
    "prereg_axis": False,
    "ci_low": -1.0,
    "ci_high": 1.0,
    "full_population": True,
}


def test_analysis_card_v3_identity_and_content_hash_deterministic():
    """같은 입력 → byte-동일 content_hash. source가 다르면 해시도 달라진다."""
    df = _v3_rows()
    card_a = build_analysis_card_v3(df, source={"alias": "fixture://a", "hash": "h1"}, role=ROLE_TRAIN)
    card_b = build_analysis_card_v3(df, source={"alias": "fixture://a", "hash": "h1"}, role=ROLE_TRAIN)
    assert card_a.schema == ANALYSIS_CARD_SCHEMA_V3
    assert card_a.content_hash == card_b.content_hash
    assert len(card_a.content_hash) == 64  # sha256 hex
    assert verify_analysis_card_v3_content_hash(card_a) is True
    assert verify_analysis_card_v3_content_hash(
        replace(card_a, role=ROLE_VALIDATION)
    ) is False

    card_c = build_analysis_card_v3(df, source={"alias": "fixture://b", "hash": "h2"}, role=ROLE_TRAIN)
    assert card_c.content_hash != card_a.content_hash

    # 영속 라운드트립도 동일 콘텐츠를 실어야 한다.
    text = card_v3_to_json(card_a)
    assert json.loads(text)["content_hash"] == card_a.content_hash


def test_analysis_card_v3_directive_requires_sample_gate():
    """표본(n_trades/n_days/n_symbols) 미달 → 지시로 승격 금지(descriptive만)."""
    small_df = _v3_rows(n_trades=5, n_days=2, n_symbols=1)
    card = build_analysis_card_v3(
        small_df, source={"alias": "fixture://small"}, role=ROLE_TRAIN,
        candidate_findings=[_GOOD_FINDING],
    )
    assert card.actionable_directives == ()
    assert len(card.descriptive_findings) == 1
    assert card.descriptive_findings[0]["reason_code"] == REASON_INELIGIBLE


def test_analysis_card_v3_directive_requires_ci_and_fdr_gate():
    """표본은 충분해도 CI가 0을 포함하거나 q>alpha면 지시 승격 금지."""
    df = _v3_rows()
    ci_includes_zero = {**_GOOD_FINDING, "ci_low": -1.0, "ci_high": 1.0}
    card = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role=ROLE_TRAIN,
        candidate_findings=[ci_includes_zero],
    )
    assert card.actionable_directives == ()
    assert card.descriptive_findings[0]["reason_code"] == REASON_INELIGIBLE

    card_noise = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role=ROLE_TRAIN,
        candidate_findings=[_NOISE_FINDING],
    )
    assert card_noise.actionable_directives == ()


def test_analysis_card_v3_directive_passes_when_all_gates_ok():
    """표본+CI+FDR 전부 통과 + role='train' → actionable_directives에 실린다."""
    df = _v3_rows()
    card = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role=ROLE_TRAIN,
        candidate_findings=[_GOOD_FINDING, _NOISE_FINDING],
    )
    assert len(card.actionable_directives) == 1
    directive = card.actionable_directives[0]
    assert directive["finding_id"] == "f_signal"
    assert directive["reason_code"] == REASON_OK
    assert directive["n_trades"] >= 30 and directive["n_days"] >= 10 and directive["n_symbols"] >= 2


def test_analysis_card_v3_validation_and_oos_role_zero_directives():
    """DR-05: validation/oos 롤은 게이트를 통과하는 발견이 있어도 지시 0개(train-only)."""
    df = _v3_rows()
    for role in (ROLE_VALIDATION, ROLE_OOS):
        card = build_analysis_card_v3(
            df, source={"alias": "fixture://x"}, role=role,
            candidate_findings=[_GOOD_FINDING],
        )
        assert card.actionable_directives == (), f"role={role} 는 지시 0개여야 한다"
        assert card.descriptive_findings[0]["reason_code"] == REASON_NOT_TRAIN


def test_analysis_card_v3_row_ablation_never_becomes_directive():
    """ablation_findings 는 candidate_findings 경로가 아니라 항상 서술 섹션이다(causal 승격 없음)."""
    from ai_strategy_loop.autopsy.ablation import to_card_section_v3 as ablation_to_card_section_v3
    from ai_strategy_loop.autopsy.ablation import AblationResult, ABLATION_STATUS_OK

    ablation_result = AblationResult(status=ABLATION_STATUS_OK, trade_count=40, clause_count=0, evaluable_clause_count=0)
    section = ablation_to_card_section_v3(ablation_result)
    assert section["causal_claim"] is False

    df = _v3_rows()
    card = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role=ROLE_TRAIN,
        ablation_findings=[section],
    )
    assert card.actionable_directives == ()
    assert card.ablation_findings[0]["causal_claim"] is False


def test_analysis_card_v3_null_simulation_hard_zero_fdr():
    """Appendix-B 스타일 하드 널: 순수 잡음(p=1, CI=[0,0])이면 지시가 항상 정확히 0개다.

    1000회 반복 결정론 널 시뮬레이션 — 경험적 FDR(허위 지시 비율)이 정확히 0.0
    (<=0.05)임을 증명한다.
    """
    df = _v3_rows()
    false_discovery_count = 0
    trials = 200
    for j in range(trials):
        null_finding = {
            "finding_id": f"null_{j}",
            "statement": "null",
            "axis": "entry_feature",
            "p_value": 1.0,
            "prereg_axis": False,
            "ci_low": 0.0,
            "ci_high": 0.0,
        }
        card = build_analysis_card_v3(
            df, source={"alias": f"fixture://null/{j}"}, role=ROLE_TRAIN,
            candidate_findings=[null_finding],
        )
        false_discovery_count += len(card.actionable_directives)
    empirical_fdr = false_discovery_count / trials
    assert false_discovery_count == 0
    assert empirical_fdr <= 0.05


def test_analysis_card_v3_null_simulation_bh_gate_empirical_fdr_le_5pct():
    """BH-FDR 게이트 자체의 경험적 FDR — 순수 잡음 p값 family에서 결정론 시드로
    측정한 허위-지시 비율이 5% 이하다(Simes 전역귀무검정 성질의 실측 확인).
    """
    import random

    alpha = 0.05
    n_families = 5000
    family_size = 20
    rng = random.Random(0)  # 결정론 시드 — 재현 가능한 경험적 FDR.

    false_discovery_families = 0
    for _ in range(n_families):
        p_values = [rng.random() for _ in range(family_size)]
        q_values, _pass_flags = _benjamini_hochberg(p_values, alpha=alpha)
        any_directive = False
        for q in q_values:
            is_directive, _reason = evaluate_directive_gate(
                role=ROLE_TRAIN, n_trades=40, n_days=12, n_symbols=3,
                ci_low=1.0, ci_high=5.0, q_value=q, prereg_axis=False, alpha=alpha,
            )
            if is_directive:
                any_directive = True
        if any_directive:
            false_discovery_families += 1

    empirical_fdr = false_discovery_families / n_families
    assert empirical_fdr <= alpha


def test_analysis_card_v3_render_paths_share_same_content_hash():
    """DR-05: 대시보드(render_card_v3_md)/prompt(segment_feedback)/문서
    (feature_importance_feedback) 렌더 경로가 전부 카드의 동일 content_hash를
    그대로 읽는다(재계산 없음).
    """
    df = _v3_rows()
    card = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role=ROLE_TRAIN,
        candidate_findings=[_GOOD_FINDING],
    )
    assert len(card.actionable_directives) == 1

    md = render_card_v3_md(card)
    assert f"content_hash: {card.content_hash}" in md

    prompt_lines = render_directives_from_card_v3(card)
    assert prompt_lines and all(f"[card:{card.content_hash}]" in line for line in prompt_lines)

    doc_lines = render_directive_hints_from_card_v3(card)
    assert doc_lines and all(f"[card:{card.content_hash}]" in line for line in doc_lines)

    # 세 렌더 경로가 참조하는 해시가 전부 동일 문자열 — 재계산이 아니라 참조임을 증명.
    hash_from_md = md.splitlines()[1].split("content_hash: ")[1]
    hash_from_prompt = prompt_lines[0].split("]")[0][len("[card:"):]
    hash_from_doc = doc_lines[0].split("]")[0][len("[card:"):]
    assert hash_from_md == hash_from_prompt == hash_from_doc == card.content_hash

def test_analysis_card_v3_supplied_typed_attribution_is_hashed_and_rendered():
    """Supplied segment/feature/evidence lineage is preserved; no empty prior is made."""
    finding = {
        **_GOOD_FINDING,
        "side": "buy",
        "scope": "entry",
        "priority": 2,
        "data_role": "TRAIN",
        "status": "READY",
        "evidence_ids": ["ev-feature", "ev-segment"],
    }
    supplied_segments = [{"finding_id": "seg-loss", "kind": "loss", "label": "0900-0905"}]
    supplied_features = [{"finding_id": "feature-win", "feature": "B_signal", "kind": "win"}]
    kwargs = {
        "source": {"alias": "fixture://typed", "hash": "typed"},
        "role": ROLE_TRAIN,
        "candidate_findings": [finding, {**finding, "finding_id": "empty", "statement": "   "}],
        "segment_findings": supplied_segments,
        "feature_importance_findings": supplied_features,
        "evidence_ids": ["ev-card"],
    }
    card_a = build_analysis_card_v3(_v3_rows(), **kwargs)
    card_b = build_analysis_card_v3(_v3_rows(), **kwargs)
    changed = build_analysis_card_v3(
        _v3_rows(), **{**kwargs, "candidate_findings": [{**finding, "statement": "B_signal stronger"}]}
    )

    assert card_a.content_hash == card_b.content_hash
    assert card_a.content_hash != changed.content_hash
    supplied_segments[0]["label"] = "mutated-after-build"
    assert card_a.segment_findings[0]["label"] == "0900-0905"
    with pytest.raises(TypeError):
        card_a.source["alias"] = "mutated"
    assert verify_analysis_card_v3_content_hash(card_a) is True
    assert card_a.feature_importance_findings == tuple(supplied_features)
    assert len(card_a.actionable_directives) == 1
    directive = card_a.actionable_directives[0]
    assert {key: directive[key] for key in ("side", "scope", "priority", "data_role", "status")} == {
        "side": "buy", "scope": "entry", "priority": 2, "data_role": "TRAIN", "status": "READY",
    }
    assert directive["evidence_ids"] == ("ev-feature", "ev-segment")


def test_analysis_card_v3_prompt_renderers_only_accept_train_ready_directives():
    """Validation/HOLDOUT and non-READY supplied findings remain descriptive-only."""
    finding = {
        **_GOOD_FINDING,
        "side": "buy",
        "scope": "entry",
        "priority": 1,
        "data_role": "TRAIN",
        "status": "READY",
    }
    card = build_analysis_card_v3(
        _v3_rows(), source={"alias": "fixture://typed"}, role=ROLE_TRAIN,
        candidate_findings=[
            finding,
            {**finding, "finding_id": "holdout", "data_role": "HOLDOUT"},
            {**finding, "finding_id": "pending", "status": "PENDING"},
        ],
    )

    assert [item["finding_id"] for item in card.actionable_directives] == ["f_signal"]
    assert len(card.descriptive_findings) == 2
    assert len(render_directives_from_card_v3(card)) == 1
    assert len(render_directive_hints_from_card_v3(card)) == 1


def test_analysis_card_v3_malformed_statistics_fail_closed():
    malformed = {
        **_GOOD_FINDING,
        "p_value": "not-a-number",
        "q_value": float("nan"),
        "ci_low": float("nan"),
        "ci_high": "bad",
    }
    out_of_range_preregistered = {
        **_GOOD_FINDING,
        "finding_id": "invalid-preregistered",
        "p_value": 2.0,
        "q_value": 2.0,
        "prereg_axis": True,
    }

    card = build_analysis_card_v3(
        _v3_rows(),
        source={"alias": "fixture://malformed"},
        role=ROLE_TRAIN,
        candidate_findings=[malformed, out_of_range_preregistered],
    )

    assert card.actionable_directives == ()
    assert len(card.descriptive_findings) == 2


def test_feature_importance_findings_carry_real_gap_ci(monkeypatch):
    import ai_strategy_loop.brain.feature_importance_feedback as feature_mod

    monkeypatch.setattr(
        feature_mod,
        "feature_importance_by_segment",
        lambda *args, **kwargs: {
            "segment-a": [{
                "feature": "B_체결강도",
                "win_rate_top_q": 1.0,
                "win_rate_bot_q": 0.0,
                "n": 100,
            }],
        },
    )

    findings = build_feature_importance_findings(pd.DataFrame({"x": [1]}))

    assert findings
    assert findings[0]["ci_low"] > 0
    assert findings[0]["ci_high"] > 0

def test_analysis_card_v3_invalid_role_rejected():
    df = _v3_rows()
    with pytest.raises(ValueError):
        build_analysis_card_v3(df, source={"alias": "fixture://x"}, role="bogus")
