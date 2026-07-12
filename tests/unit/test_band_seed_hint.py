"""A-5 — 백파인더 밴드 시드 힌트 배선 계약 테스트.

로더(_load_band_seed_lines): 정상/파일없음/깨진 JSON/lift 정렬·상한.
프롬프트(build_messages): OFF byte-동일, ON 매수 주입·매도 무영향.
스크립트(serialize_seeds): BandSpec → JSON-safe 왕복.
루프 배선: _generate_pair가 매수에만 band_seed_lines를 전달(소스 가드).
"""
import inspect
import json

from ai_strategy_loop.brain.band_compiler import BandSpec
from ai_strategy_loop.brain.prompt import build_messages
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.loop import _load_band_seed_lines
from ai_strategy_loop.scripts.mine_band_seeds import BAND_SEEDS_SCHEMA, serialize_seeds


def _artifact(seeds):
    return {"schema": BAND_SEEDS_SCHEMA, "seeds": seeds}


def _write(tmp_path, payload):
    p = tmp_path / "band_seeds.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_loader_sorts_by_lift_and_caps_lines(tmp_path):
    path = _write(tmp_path, _artifact([
        {"nl_guide": "low", "lift": 1.1},
        {"nl_guide": "high", "lift": 8.99},
        {"nl_guide": "mid", "lift": 2.0},
        {"nl_guide": None, "lift": 99.0},  # nl_guide 없는 시드는 제외
    ]))
    cfg = LoopConfig(band_seed_hint_enabled=True, band_seed_hint_path=path,
                     band_seed_hint_max_lines=2)
    lines = _load_band_seed_lines(cfg)
    assert lines == ["high", "mid"]


def test_loader_graceful_on_missing_or_broken(tmp_path):
    cfg = LoopConfig(band_seed_hint_path=str(tmp_path / "없는파일.json"))
    assert _load_band_seed_lines(cfg) is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not-json", encoding="utf-8")
    assert _load_band_seed_lines(LoopConfig(band_seed_hint_path=str(broken))) is None
    empty = _write(tmp_path, _artifact([]))
    assert _load_band_seed_lines(LoopConfig(band_seed_hint_path=empty)) is None


def test_prompt_off_byte_identical_and_on_buy_only():
    base_buy = build_messages("buy", timeframe="tick")[1]["content"]
    off_buy = build_messages("buy", timeframe="tick", band_seed_lines=None)[1]["content"]
    assert base_buy == off_buy
    on_buy = build_messages(
        "buy", timeframe="tick",
        band_seed_lines=["[0900_0905·소형] 승률 12.0% (lift 8.99) 진입 셋업: 등락율 -1.5~5.4"],
    )[1]["content"]
    assert "데이터 채굴 진입 밴드 힌트" in on_buy
    assert "lookahead 편향" in on_buy          # 시드 전용 고지
    assert "등락율 -1.5~5.4" in on_buy
    # 매도 경로는 이 힌트의 영향을 받지 않는다(호출부가 None을 넘기지만, 넘겨도 무주입).
    on_sell = build_messages(
        "sell", timeframe="tick",
        band_seed_lines=["세그먼트 힌트"],
    )[1]["content"]
    assert "데이터 채굴 진입 밴드 힌트" not in on_sell


def test_serialize_seeds_roundtrips_bandspec():
    seeds = [{
        "time_segment": "0900_0905", "market_cap_segment": "소형",
        "winner_rate": 0.12, "lift": 8.99,
        "band_specs": [BandSpec(var="등락율", op="between_le", lo=-1.5, hi=5.4)],
        "nl_guide": "[0900_0905·소형] 진입 셋업: 등락율 -1.5~5.4",
    }]
    out = serialize_seeds(seeds)
    assert out[0]["bands"] == [{"var": "등락율", "op": "between_le", "lo": -1.5, "hi": 5.4}]
    json.dumps(out, ensure_ascii=False)  # JSON-safe 보장


def test_generate_pair_passes_band_seed_lines_buy_only():
    from ai_strategy_loop.controller import loop as loop_mod

    src = inspect.getsource(loop_mod._generate_pair)
    assert 'band_seed_lines=(band_seed_lines if kind == "buy" else None)' in src
