"""P3 — 환류 토글 ON 연구프리셋 + FDR(Benjamini-Hochberg) + feature_importance 배선.

설계 불변식(계획서 P3 통과조건):
  - ★★토글 OFF면 부검/생성 출력이 기존과 byte-동일(하위호환). 깨지면 무조건 롤백.
  - 연구 프리셋은 환류 토글을 켜되 전역 LoopConfig 기본값은 OFF 유지.
  - FDR: 다중검정 보정(BH)으로 잡음 피처의 임계 후보 주입을 차단(R1 선택편향 완화).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.analyze import (  # noqa: E402
    _benjamini_hochberg,
    _two_sample_p,
    analyze_trades,
)
from ai_strategy_loop.autopsy.summarize import summarize  # noqa: E402
from ai_strategy_loop.brain.feature_importance_feedback import (  # noqa: E402
    build_feature_importance_lines,
)
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.scripts.research_presets import PresetName, preset_payload  # noqa: E402

# 환류 4종 + feature_importance(신규). 연구 프리셋이 켜야 하는 토글.
_FEEDBACK_TOGGLES = (
    "segment_feedback_enabled",
    "quantile_feedback_enabled",
    "counterfactual_feedback_enabled",
    "hypothesis_tracking_enabled",
    "feature_importance_feedback_enabled",
)


# ---------------------------------------------------------------------------
# 픽스처: 강한 분리 피처(시가총액·체결강도) + 잡음 피처(회전율, win/lose 동일분포).
# ---------------------------------------------------------------------------
def _make_csv(path: Path, rows: list) -> str:
    """rows: [(수익률, 수익금, 시가총액, 체결강도, 회전율)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "수익률", "수익금",
            "B_시가총액", "B_체결강도", "B_회전율",
        ])
        w.writeheader()
        for i, (pct, krw, cap, strength, turnover) in enumerate(rows):
            w.writerow({
                "종목명": "T", "매수시간": f"202301{(i % 28) + 1:02d}090100",
                "매도시간": f"202301{(i % 28) + 1:02d}090300",
                "수익률": pct, "수익금": krw,
                "B_시가총액": cap, "B_체결강도": strength, "B_회전율": turnover,
            })
    return str(path)


def _fixture_csv(tmp_path: Path) -> str:
    rows = []
    for i in range(15):
        # 승자: 시총 낮음·체결강도 높음 / 패자: 반대. 회전율은 양쪽 동일분포(잡음).
        rows.append((1.0, 100000, 1000 + i * 20, 150 + i * 2, 50 + (i % 5)))
        rows.append((-0.5, -50000, 3000 + i * 20, 100 + i * 2, 50 + (i % 5)))
    return _make_csv(tmp_path / "bt.csv", rows)


# ---------------------------------------------------------------------------
# 증분 1 — 연구 프리셋이 환류 토글을 켜되 전역 기본값은 OFF 유지.
# ---------------------------------------------------------------------------
def test_global_defaults_stay_off() -> None:
    cfg = LoopConfig()
    for name in _FEEDBACK_TOGGLES:
        assert getattr(cfg, name) is False, f"{name} 전역 기본값은 OFF여야 한다"


def test_research_presets_enable_feedback_toggles() -> None:
    for preset in (PresetName.TICK_LATE_0920_0925, PresetName.MIN_FULL_0900_1500):
        config = preset_payload(preset)["config"]
        for name in _FEEDBACK_TOGGLES:
            assert config.get(name) is True, f"{preset} 프리셋이 {name}을 켜야 한다"


def test_preset_config_round_trips_into_loopconfig() -> None:
    config = preset_payload(PresetName.TICK_LATE_0920_0925)["config"]
    cfg = LoopConfig.from_dict(config)
    for name in _FEEDBACK_TOGGLES:
        assert getattr(cfg, name) is True


# ---------------------------------------------------------------------------
# 증분 2 — FDR(Benjamini-Hochberg) 순수함수 + analyze_trades 배선.
# ---------------------------------------------------------------------------
def test_two_sample_p_monotone_in_effect() -> None:
    # 효과(smd)가 클수록·표본이 클수록 p값은 작아진다. 효과 0이면 p=1.
    assert _two_sample_p(0.0, 30, 30) == 1.0
    p_small = _two_sample_p(0.3, 30, 30)
    p_large = _two_sample_p(2.0, 30, 30)
    assert 0.0 <= p_large < p_small <= 1.0


def test_benjamini_hochberg_basic() -> None:
    # 작은 p들은 통과, 큰 p는 탈락. 단조성 보정으로 q는 비감소.
    q, passed = _benjamini_hochberg([0.001, 0.01, 0.9, 0.95], alpha=0.10)
    assert passed[0] is True and passed[1] is True
    assert passed[2] is False and passed[3] is False
    assert all(0.0 <= v <= 1.0 for v in q)


def test_benjamini_hochberg_empty() -> None:
    q, passed = _benjamini_hochberg([], alpha=0.10)
    assert q == [] and passed == []


def test_analyze_trades_populates_fdr_fields(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    assert result.status == "ok"
    by_col = {d.column: d for d in result.discriminators}
    # 강한 분리 피처는 FDR 통과, 잡음(회전율)은 탈락.
    assert by_col["B_시가총액"].fdr_pass is True
    assert by_col["B_체결강도"].fdr_pass is True
    assert by_col["B_회전율"].fdr_pass is False
    for d in result.discriminators:
        assert d.p_value is not None and 0.0 <= d.p_value <= 1.0
        assert d.q_value is not None and 0.0 <= d.q_value <= 1.0


# ---------------------------------------------------------------------------
# byte-identical 불변식 (필수).
# ---------------------------------------------------------------------------
def test_summarize_off_is_byte_identical(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    assert summarize(result, None) == summarize(result, LoopConfig())
    assert "후보" not in summarize(result, None)


def test_quantile_on_injects_only_fdr_survivors(tmp_path) -> None:
    result = analyze_trades(_fixture_csv(tmp_path), min_trades=10)
    cfg = LoopConfig.from_dict({"quantile_feedback_enabled": True})
    text = summarize(result, cfg)
    # 강한 분리 피처엔 임계 후보가 붙고(FDR 통과)…
    assert "상한 후보: ≤" in text or "하한 후보: ≥" in text
    # …잡음 회전율 줄에는 임계 후보가 붙지 않는다(FDR 탈락 → 주입 차단).
    for line in text.splitlines():
        if "회전율" in line:
            assert "후보" not in line, "FDR 탈락 피처에 임계 후보가 주입되면 안 된다"


# ---------------------------------------------------------------------------
# 증분 3 — feature_importance prefer 힌트 + build_messages 배선.
# ---------------------------------------------------------------------------
def _segmented_csv(tmp_path: Path) -> str:
    # 소형(시총 1500억) 셀 40거래 — 체결강도가 승패를 강하게 가른다.
    rows = []
    for i in range(20):
        rows.append((1.0, 100000, 1500, 170 + i, 50 + (i % 5)))   # 승자: 체결강도 높음
        rows.append((-0.5, -50000, 1500, 90 + i, 50 + (i % 5)))   # 패자: 체결강도 낮음
    return _make_csv(tmp_path / "seg.csv", rows)


def test_build_feature_importance_lines_emits_segment_hint(tmp_path) -> None:
    lines = build_feature_importance_lines(_segmented_csv(tmp_path), min_cell=20)
    assert lines, "소형 셀에서 결정 피처 힌트가 나와야 한다"
    joined = "\n".join(lines)
    assert "소형" in joined and "체결강도" in joined
    assert "상단" in joined  # 승자가 체결강도 높음 → 상단 우선.


def test_build_feature_importance_lines_graceful_on_bad_input(tmp_path) -> None:
    assert build_feature_importance_lines("") == []
    assert build_feature_importance_lines(str(tmp_path / "missing.csv")) == []


def test_build_messages_feature_hint_off_is_byte_identical() -> None:
    base = build_messages("buy", timeframe="tick")
    none_passed = build_messages("buy", timeframe="tick", feature_hint_lines=None)
    assert base == none_passed
    assert "prefer 힌트" not in none_passed[-1]["content"]


def test_build_messages_feature_hint_on_injects_block() -> None:
    hint = ["- 시총 '소형' 구간에서는 체결강도 상단(높은 값)이 승패를 가른다 — …"]
    msgs = build_messages("buy", timeframe="tick", feature_hint_lines=hint)
    user = msgs[-1]["content"]
    assert "prefer 힌트" in user
    assert "체결강도 상단" in user
