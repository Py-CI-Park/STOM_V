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
from ai_strategy_loop.config import (  # noqa: E402
    LoopConfig,
    research_feedback_config_overrides,
)
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402
from ai_strategy_loop.scripts.research_presets import PresetName, preset_payload  # noqa: E402

# 환류 4종 + feature_importance(신규). 연구 프리셋이 켜야 하는 토글.
_FEEDBACK_TOGGLES = (
    "segment_feedback_enabled",
    "quantile_feedback_enabled",
    "counterfactual_feedback_enabled",
    "hypothesis_tracking_enabled",
    "feature_importance_feedback_enabled",
    # 2026-07-16 실 A/B 실측 교훈: 카드 채널 원천 토글 — 연구 프리셋 필수 ON.
    "analysis_card_v3_enabled",
)


# ---------------------------------------------------------------------------
# 픽스처: 강한 분리 피처(시가총액·체결강도) + 잡음 피처(회전율, win/lose 동일분포).
# ---------------------------------------------------------------------------
def _make_csv(
    path: Path,
    rows: list[tuple[float, int, int, int, int]],
) -> str:
    """rows: [(수익률, 수익금, 시가총액, 체결강도, 회전율)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "수익률", "수익금",
            "B_시가총액", "B_체결강도", "B_회전율",
            "S_사후진단누수", "R_결과누수",
        ])
        w.writeheader()
        for i, (pct, krw, cap, strength, turnover) in enumerate(rows):
            w.writerow({
                "종목명": "T", "매수시간": f"202301{(i % 28) + 1:02d}090100",
                "매도시간": f"202301{(i % 28) + 1:02d}090300",
                "수익률": pct, "수익금": krw,
                "B_시가총액": cap, "B_체결강도": strength, "B_회전율": turnover,
                "S_사후진단누수": strength * 100,
                "R_결과누수": pct * 100,
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


def test_dr02_manifest_v2_flags_default_off() -> None:
    # DR-02 additive flags (Manifest v2 wiring) must default OFF like every other
    # feature toggle — v11 startup/default run_loop output stays byte-identical.
    cfg = LoopConfig()
    assert cfg.manifest_v2_enabled is False
    assert cfg.v2_certification_enabled is False


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


def test_generation_feature_hints_exclude_sell_and_result_columns(tmp_path) -> None:
    # Given: a trade CSV containing valid B_* inputs plus predictive S_*/R_* outcomes.
    lines = build_feature_importance_lines(_segmented_csv(tmp_path), min_cell=20)

    # When: the feedback text that can enter the next BUY prompt is assembled.
    joined = "\n".join(lines)

    # Then: only buy-time inputs can become generation hints.
    assert "체결강도" in joined
    assert "사후진단누수" not in joined
    assert "결과누수" not in joined


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


# ---------------------------------------------------------------------------
# 증분 4 — research_feedback_config_overrides: 환류 4종 opt-in 스위치 묶음.
#   전역 기본값(OFF)은 절대 바꾸지 않고, 호출부가 명시 병합할 때만 켜진다.
# ---------------------------------------------------------------------------
_OVERRIDE_TOGGLES = (
    "segment_feedback_enabled",
    "quantile_feedback_enabled",
    "hypothesis_tracking_enabled",
    "feature_importance_feedback_enabled",
)


def test_research_feedback_overrides_enable_exactly_four_toggles() -> None:
    overrides = research_feedback_config_overrides()
    assert set(overrides) == set(_OVERRIDE_TOGGLES)
    assert all(value is True for value in overrides.values())


def test_research_feedback_overrides_do_not_change_defaults() -> None:
    # 반환 dict를 변이해도(새 dict) 전역 LoopConfig 기본값은 전부 OFF 그대로.
    mutated = research_feedback_config_overrides()
    mutated["segment_feedback_enabled"] = False
    cfg = LoopConfig()
    for name in _OVERRIDE_TOGGLES:
        assert getattr(cfg, name) is False, f"{name} 전역 기본값은 OFF여야 한다"


def test_research_feedback_overrides_round_trip_into_loopconfig() -> None:
    cfg = LoopConfig.from_dict(research_feedback_config_overrides())
    for name in _OVERRIDE_TOGGLES:
        assert getattr(cfg, name) is True
    # 세트에 없는 토글은 켜지지 않는다(명시적 4종 스위치 — 부수효과 없음).
    assert cfg.counterfactual_feedback_enabled is False
    assert cfg.exit_forensics_feedback_enabled is False


def test_research_feedback_overrides_returns_fresh_dict_each_call() -> None:
    first = research_feedback_config_overrides()
    second = research_feedback_config_overrides()
    assert first == second
    assert first is not second  # 공유 상태 변이 방지(불변성).


# ---------------------------------------------------------------------------
# 증분 5 — loop 배선: _build_feature_hints 산출 + _generate_pair 전달.
# ---------------------------------------------------------------------------
def test_build_feature_hints_off_returns_none(tmp_path) -> None:
    # 토글 OFF(기본)면 CSV가 있어도 헬퍼가 즉시 None — 산출 자체가 없다(byte-동일).
    outcome = L.BacktestOutcome(True, "success", _segmented_csv(tmp_path), {}, "ok")
    assert L._build_feature_hints(LoopConfig(), outcome) is None


def test_build_feature_hints_on_returns_lines(tmp_path) -> None:
    cfg = LoopConfig.from_dict({"feature_importance_feedback_enabled": True})
    outcome = L.BacktestOutcome(True, "success", _segmented_csv(tmp_path), {}, "ok")
    lines = L._build_feature_hints(cfg, outcome)
    assert lines, "토글 ON + 분리 신호 CSV면 prefer 힌트가 나와야 한다"
    assert "체결강도" in "\n".join(lines)


def test_build_feature_hints_on_missing_csv_returns_none(tmp_path) -> None:
    cfg = LoopConfig.from_dict({"feature_importance_feedback_enabled": True})
    # 실패 세대(CSV 없음) → None.
    failed = L.BacktestOutcome(False, "error", None, None, "no csv")
    assert L._build_feature_hints(cfg, failed) is None
    # 존재하지 않는 CSV → 빈 결과가 None으로 정규화(gen_kwargs 키 미주입 보장).
    missing = L.BacktestOutcome(True, "success", str(tmp_path / "missing.csv"), {}, "ok")
    assert L._build_feature_hints(cfg, missing) is None


def _capture_hint_kwargs(monkeypatch) -> dict[str, object]:
    """brain.generate_strategy를 대체해 kind별 feature_hint_lines kwargs를 캡처한다."""
    captured: dict[str, object] = {}

    def _fake_generate_strategy(provider, kind, name, db, **kw):
        captured[kind] = kw.get("feature_hint_lines")
        return {"status": "ok", "name": name, "code": "x",
                "attempts": 1, "usage": {"total_tokens": 1}}

    # _generate_pair는 함수 내부에서 brain.generate_strategy를 지연 import 한다.
    import ai_strategy_loop.brain as brain
    monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)
    return captured


def test_generate_pair_passes_hints_to_buy_only(monkeypatch) -> None:
    captured = _capture_hint_kwargs(monkeypatch)
    hints = ["- 시총 '소형' 구간에서는 체결강도 상단(높은 값)이 승패를 가른다 — …"]
    res = L._generate_pair(object(), LoopConfig(), "rid", 1, None,
                           feature_hint_lines=hints)
    assert res["status"] == "ok", res
    assert captured["buy"] == hints
    assert captured["sell"] is None  # 매도 프롬프트 무영향(kind=='buy' 전용 채널).


def test_generate_pair_default_passes_none_hints(monkeypatch) -> None:
    # feature_hint_lines 미전달(기본 None) → buy/sell 모두 None(byte-identical 보호).
    captured = _capture_hint_kwargs(monkeypatch)
    res = L._generate_pair(object(), LoopConfig(), "rid", 1, None)
    assert res["status"] == "ok", res
    assert captured["buy"] is None
    assert captured["sell"] is None


# ---------------------------------------------------------------------------
# 증분 6 — run_loop 폐루프 배선: 직전 세대 train CSV → 다음 세대 프롬프트 kwargs.
# ---------------------------------------------------------------------------
def _fake_score(outcome, cfg):
    """gate 실패(거래 발생) 성공 세대 — 루프가 부검 phase까지 진행하게 한다."""
    fit = FitnessResult(score=0.0, calmar=0.5, uptrend_r2=0.5, gate_passed=False,
                        reason="MDD 초과", cagr=1.0, mdd=20.0,
                        trade_count=20, total_profit=1000.0)
    graded = GradedResult(
        graded=0.7, gate_passed=False, composite=0.0,
        trades_term=1.0, mdd_term=0.5, profit_term=1.0, uptrend_term=0.5,
        gate_distance="MDD 20 > cap", cagr=1.0, mdd=20.0,
        trade_count=20, total_profit=1000.0, uptrend_r2=0.5,
    )
    return (fit, graded, None)


def _run_two_gen_loop(monkeypatch, tmp_path, fake_generate, config_extra, run_id) -> None:
    """성공 백테(실 CSV) 2세대 미니 루프 하네스 (test_error_feedback 패턴 미러)."""
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L, "_generate_pair", fake_generate)
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")
    csv_path = _segmented_csv(tmp_path)
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, buy, sell: L.BacktestOutcome(
            True, "success", csv_path,
            {"cagr": 1.0, "mdd_pct": 5.0, "trade_count": 20, "total_profit_krw": 1000},
            "ok",
        ),
    )
    monkeypatch.setattr(L, "_score_outcome", _fake_score)
    config = LoopConfig.from_dict({
        "provider": "openrouter", "max_generations": 2, "bt_engine_mode": "cold",
        "cost_cap_generations": 100, "cost_cap_tokens": None,
        "autopsy_enabled": True, "mdd_cap": 10.0, "min_trades": 10,
        **config_extra,
    })
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        L.run_loop(config, run_id=run_id, state=st)
    finally:
        st.close()


def test_loop_on_feeds_feature_hints_to_next_generation(monkeypatch, tmp_path) -> None:
    """토글 ON: gen0 train CSV의 prefer 힌트가 gen1 프롬프트 빌드 kwargs로 환류된다."""
    captured = []

    def fake_generate(provider, cfg, rid, gen, fb, **kw):
        captured.append({"gen": gen, "hints": kw.get("feature_hint_lines")})
        return {"status": "ok",
                "buy_name": f"AILOOP_{rid}_g{gen}_buy",
                "sell_name": f"AILOOP_{rid}_g{gen}_sell",
                "tokens": 1}

    _run_two_gen_loop(monkeypatch, tmp_path, fake_generate,
                      {"feature_importance_feedback_enabled": True}, "fihint")
    by_gen = {c["gen"]: c for c in captured}
    assert by_gen[0]["hints"] is None, "첫 세대는 직전 CSV가 없어 힌트가 없어야 한다"
    hints = by_gen[1]["hints"]
    assert hints, "토글 ON이면 gen1 프롬프트 빌드 kwargs에 비어있지 않은 힌트가 온다"
    assert "체결강도" in "\n".join(hints)


def test_loop_off_never_passes_feature_hint_kwarg(monkeypatch, tmp_path) -> None:
    """토글 OFF(기본): gen_kwargs에 feature_hint_lines 키 자체가 없다(시그니처 보호)."""
    seen_gens = []

    def fake_generate_strict(provider, cfg, rid, gen, fb,
                             history_summary=None, sell_feedback=None):
        # opt-in 키가 하나라도 오면 TypeError로 즉사 → byte-identical 시그니처 보증.
        seen_gens.append(gen)
        return {"status": "ok",
                "buy_name": f"AILOOP_{rid}_g{gen}_buy",
                "sell_name": f"AILOOP_{rid}_g{gen}_sell",
                "tokens": 1}

    _run_two_gen_loop(monkeypatch, tmp_path, fake_generate_strict, {}, "fioff")
    assert seen_gens == [0, 1]
