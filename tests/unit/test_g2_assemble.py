"""G2 새 골격 조립기 검증 — 엔진 없이 렌더·게이트·원장 규칙만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-13_G2_G4_사전등록.md
"""

import ast

import pytest

from ai_strategy_loop.labeling.run_g2_assemble import (
    BAND_FEATURES, BANDS, GATE_MIN_TRADES, MICRO_CAP_MAX, VARIANTS, gate,
    render_strategy, sync_ledger)

SEEDS = [
    {"time_segment": "0900-0905", "market_cap_segment": "초소형", "lift": 5.19,
     "features": {"등락율": {"q25": 2.05, "q75": 9.26},
                  "체결강도": {"q25": 73.0, "q75": 176.73},
                  "당일거래대금": {"q25": 346.0, "q75": 2263.0},
                  "회전율": {"q25": 0.52, "q75": 3.38},
                  "초당거래대금": {"q25": 1.0, "q75": 16.0},
                  "고저평균대비등락율": {"q25": -0.46, "q75": 1.53}}},
    {"time_segment": "0905-0910", "market_cap_segment": "초소형", "lift": 3.05,
     "features": {"등락율": {"q25": 3.42, "q75": 12.99}}},
    {"time_segment": "0910-0915", "market_cap_segment": "초소형", "lift": 1.76,
     "features": {"등락율": {"q25": 4.15, "q75": 13.9}}},
]


class TestRender:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_구문상_유효하다(self, variant):
        ast.parse(render_strategy(SEEDS, variant))

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_안전절과_세그먼트가_항상_들어간다(self, variant):
        code = render_strategy(SEEDS, variant)
        assert "관심종목 == 1" in code
        assert "현재가 < VI아래5호가" in code
        assert "라운드피겨위5호가이내" in code
        assert f"시가총액 < {MICRO_CAP_MAX}" in code

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_세_시간밴드가_모두_있다(self, variant):
        code = render_strategy(SEEDS, variant)
        for lo, hi, _ in BANDS:
            assert f"{lo} <= 시분초 < {hi}:" in code

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_챔피언_절을_쓰지_않는다(self, variant):
        code = render_strategy(SEEDS, variant)
        # 챔피언 고유 절(닫힌 방향의 국소 변형이 되지 않도록)
        for champion_only in ("시가등락율", "시가대비등락율", "초당순매수금액",
                              "매도총잔량", "전일동시간비"):
            assert champion_only not in code

    def test_SEG_ONLY_는_피처_절이_없다(self):
        code = render_strategy(SEEDS, "SEG_ONLY")
        for name in BAND_FEATURES:
            assert name not in code

    def test_LOWER_는_하한만(self):
        code = render_strategy(SEEDS, "LOWER")
        assert "등락율 >= 2.05" in code
        assert "<= 등락율 <" not in code

    def test_IQR_은_양쪽_경계(self):
        code = render_strategy(SEEDS, "IQR")
        assert "2.05 <= 등락율 < 9.26" in code

    def test_밴드별로_다른_문턱이_들어간다(self):
        code = render_strategy(SEEDS, "LOWER")
        assert "등락율 >= 3.42" in code and "등락율 >= 4.15" in code

    def test_격자_밖_변형은_거부(self):
        with pytest.raises(ValueError, match="격자 밖"):
            render_strategy(SEEDS, "FREESTYLE")

    def test_시드가_없는_밴드는_통과절로_남는다(self):
        code = render_strategy([SEEDS[0]], "LOWER")
        ast.parse(code)
        assert "pass" in code   # 0905·0910 밴드는 조건 없이 통과


BASE = {"trade_count": 900, "avg_profit_pct": 0.4,
        "total_profit_krw": 1_500_000, "seed_capital": 3_000_000}


class TestGate:
    def test_전부_통과(self):
        assert gate(BASE, champion_krw=1_316_746,
                    capital_limit_krw=20_000_000)["pass"] is True

    def test_적자는_실패(self):
        out = gate(dict(BASE, total_profit_krw=-1), champion_krw=-100,
                   capital_limit_krw=20_000_000)
        assert out["champion_pass"] is True and out["positive_pass"] is False
        assert out["pass"] is False

    def test_챔피언_미달은_실패(self):
        out = gate(dict(BASE, total_profit_krw=1_000_000),
                   champion_krw=1_316_746, capital_limit_krw=20_000_000)
        assert out["pass"] is False

    def test_표본_미달은_실패(self):
        out = gate(dict(BASE, trade_count=GATE_MIN_TRADES - 1),
                   champion_krw=1_316_746, capital_limit_krw=20_000_000)
        assert out["pass"] is False

    def test_자금_초과는_실패(self):
        out = gate(dict(BASE, seed_capital=21_000_000),
                   champion_krw=1_316_746, capital_limit_krw=20_000_000)
        assert out["pass"] is False

    def test_결측은_실패(self):
        assert gate({"trade_count": 900}, champion_krw=0,
                    capital_limit_krw=20_000_000)["pass"] is False


def _report(passed: bool) -> dict:
    return {"span": [20220323, 20231121],
            "outcomes": [{"variant": "SEG_ONLY", "buy": "G2_B_SEG_ONLY",
                          "engine": dict(BASE),
                          "gate": {"pass": passed, "champion_krw": 1_316_746.0}}]}


class TestLedger:
    @pytest.fixture(autouse=True)
    def records(self, monkeypatch):
        """autouse — 이 클래스의 어떤 테스트도 운영 원장에 닿지 못한다(L-2026-08-12)."""
        captured = []
        monkeypatch.setattr(
            "ai_strategy_loop.controller.strategy_ledger.append",
            lambda record: captured.append(record))
        return captured

    def test_1차_통과는_MIXED(self, records):
        sync_ledger(_report(True), stage="train")
        assert records[0].verdict == "MIXED"

    def test_2차_통과가_PROMISING_상한(self, records):
        sync_ledger(_report(True), stage="valid")
        assert records[0].verdict == "PROMISING"

    def test_실패는_REJECT(self, records):
        sync_ledger(_report(False), stage="valid")
        assert records[0].verdict == "REJECT"

    def test_독립_골격임이_notes_에_남는다(self, records):
        sync_ledger(_report(True), stage="train")
        assert "독립 골격" in records[0].notes
