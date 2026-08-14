"""HOF3 밴드 3 렌더러·게이트 검증 — 엔진 없이 규율만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-10_HOF3_사전등록.md
"""

import ast

import pytest

from ai_strategy_loop.labeling import band3
from ai_strategy_loop.labeling.run_band3_grid import (
    MIN_TRADES, ab_unchanged, gate)

CHAMPION = """if not (관심종목 == 1):
    매수 = False


elif 시분초 < 90200:
    if not (1000 < 현재가 <= 50000):
        매수 = False
    else:
        매수 = False


elif 90200 <= 시분초 < 90500:
    if not (1000 < 현재가 <= 30000):
        매수 = False
    else:
        매수 = False


# ---------- 09:05:00 이후 ----------
else:
    매수 = False


if 매수:
    self.Buy()
"""


class TestParams:
    def test_k0_는_밴드2_문턱과_같다(self):
        p = band3.band3_params(0)
        assert p["거래대금하한"] == 5000
        assert p["전일비하한"] == 5.0
        assert p["시가대비등락율하한"] == 3.0
        assert p["초당거래대금배수"] == 2.0
        assert p["체결강도하한"] == 50.0

    def test_누적계는_오르고_순간계는_내린다(self):
        low, high = band3.band3_params(0.5), band3.band3_params(2.0)
        assert high["거래대금하한"] > low["거래대금하한"]      # 누적 ↑
        assert high["전일비하한"] > low["전일비하한"]          # 누적 ↑
        assert high["초당거래대금배수"] <= low["초당거래대금배수"]  # 순간 ↓
        assert high["체결강도하한"] <= low["체결강도하한"]      # 순간 ↓

    def test_하한이_바닥_아래로_내려가지_않는다(self):
        p = band3.band3_params(10)
        assert p["초당거래대금배수"] == 1.0
        assert p["체결강도하한"] == 20.0
        assert p["회전율하한"] == 0.5

    def test_음수_k_는_거부(self):
        with pytest.raises(ValueError, match="0 이상"):
            band3.band3_params(-0.5)


class TestRender:
    @pytest.mark.parametrize("cell", ["0", "0.5", "1", "2", "swap"])
    def test_붙인_코드가_구문상_유효하다(self, cell):
        out = band3.attach_band3(CHAMPION, cell)
        # DSL 은 순수 파이썬 구문이어야 한다(호출은 하지 않는다).
        ast.parse(out)

    @pytest.mark.parametrize("cell", ["1", "swap"])
    def test_밴드_1과_2는_한_글자도_바뀌지_않는다(self, cell):
        out = band3.attach_band3(CHAMPION, cell)
        head = CHAMPION.split("# ---------- 09:05:00 이후 ----------")[0]
        assert out.startswith(head)

    def test_밴드3_창은_09_05에서_09_20이다(self):
        out = band3.attach_band3(CHAMPION, "1")
        assert "elif 90500 <= 시분초 < 92000:" in out

    def test_표식이_남는다(self):
        assert band3.MARKER in band3.attach_band3(CHAMPION, "1")

    def test_원본은_불변이다(self):
        code = str(CHAMPION)
        band3.attach_band3(code, "1")
        assert code == CHAMPION

    def test_두_번_붙이지_못한다(self):
        once = band3.attach_band3(CHAMPION, "1")
        with pytest.raises(ValueError, match="이미"):
            band3.attach_band3(once, "1")

    def test_차단_절이_없으면_거부(self):
        with pytest.raises(ValueError, match="0회"):
            band3.attach_band3("if 매수:\n    self.Buy()\n", "1")

    def test_최종_차단_절이_보존된다(self):
        out = band3.attach_band3(CHAMPION, "1")
        assert out.rstrip().endswith("self.Buy()")
        assert band3.TAIL_ANCHOR in out

    @pytest.mark.parametrize("end", [92001, 93000])
    def test_사용자_확정_상한_초과는_거부(self, end):
        with pytest.raises(ValueError, match="허용 범위"):
            band3.render_band3_block(1.0, end=end)

    def test_swap은_밴드1_문턱을_쓴다(self):
        out = band3.render_swap_block()
        assert "1000 < 현재가 <= 50000" in out    # 밴드 1 의 상한
        assert "체결강도 >= 100" in out            # 밴드 1 의 하한

    def test_k가_커지면_거래대금_문턱이_실제로_커진다(self):
        assert "당일거래대금 > 5000)" in band3.render_band3_block(0)
        assert "당일거래대금 > 50000)" in band3.render_band3_block(1)


class TestCellName:
    @pytest.mark.parametrize("cell,expected", [
        ("swap", "SWAP"), ("0.5", "K0p5"), ("1", "K1"), ("2.0", "K2"),
    ])
    def test_이름(self, cell, expected):
        assert band3.cell_name(cell) == expected

    def test_음수는_거부(self):
        with pytest.raises(ValueError):
            band3.cell_name("-1")


def _cohort(c_profit, c_trades=100, a=(50, 500_000), b=(80, 400_000)):
    return {
        "A": {"trades": a[0], "profit_krw": float(a[1])},
        "B": {"trades": b[0], "profit_krw": float(b[1])},
        "C": {"trades": c_trades, "profit_krw": float(c_profit), "avg_pct": 0.1},
    }


class TestGate:
    def test_전부_통과(self):
        out = gate(_cohort(300_000), {"seed_capital": 2_000_000},
                   reference_krw=44_216, capital_limit_krw=20_000_000)
        assert out["pass"] is True

    def test_흑자여도_기준_미달이면_실패(self):
        out = gate(_cohort(10_000), {"seed_capital": 2_000_000},
                   reference_krw=44_216, capital_limit_krw=20_000_000)
        assert out["positive_pass"] is True
        assert out["beats_reference"] is False
        assert out["pass"] is False

    def test_적자는_실패(self):
        out = gate(_cohort(-100_000), {"seed_capital": 2_000_000},
                   reference_krw=-500_000, capital_limit_krw=20_000_000)
        assert out["beats_reference"] is True      # 기준보다는 낫지만
        assert out["positive_pass"] is False       # 흑자가 아니다
        assert out["pass"] is False

    def test_표본_하한_미달은_실패(self):
        out = gate(_cohort(300_000, c_trades=MIN_TRADES - 1),
                   {"seed_capital": 2_000_000},
                   reference_krw=44_216, capital_limit_krw=20_000_000)
        assert out["sample_pass"] is False
        assert out["pass"] is False

    def test_자금_초과는_실패(self):
        out = gate(_cohort(300_000), {"seed_capital": 25_000_000},
                   reference_krw=44_216, capital_limit_krw=20_000_000)
        assert out["capital_pass"] is False
        assert out["pass"] is False


class TestAbUnchanged:
    def test_같으면_통과(self):
        base = _cohort(0)
        assert ab_unchanged(_cohort(999), base)["unchanged"] is True

    def test_거래_수가_다르면_실패(self):
        out = ab_unchanged(_cohort(0, a=(49, 500_000)), _cohort(0))
        assert out["unchanged"] is False
        assert out["detail"]["A"]["trades_same"] is False

    def test_수익금이_다르면_실패(self):
        out = ab_unchanged(_cohort(0, b=(80, 399_000)), _cohort(0))
        assert out["unchanged"] is False

    def test_반올림_오차는_허용(self):
        out = ab_unchanged(_cohort(0, b=(80, 400_000.5)), _cohort(0))
        assert out["unchanged"] is True
