"""HOF2 거래 부검의 순수 함수 검증 — 엔진·DB 없이 규율만 본다.

특히 지키는 것:
- 발굴은 학습 구간만 본다(검증·확인 오염 금지)
- 가설 예산 상한(헌법 15항)
- 같은 거래를 남기는 규칙은 같은 가설이다
"""

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling import run_trade_autopsy as autopsy
from ai_strategy_loop.labeling.run_trade_autopsy import (
    DEFAULT_BUDGET, bh_fdr, calendar_days, cohort_of, day_block_bootstrap,
    scan_thresholds, select_candidates, split_days, to_dsl, usable_features)


class TestCalendar:
    """분할 기준은 팔의 체결 기록이 아니라 거래일 달력이어야 한다."""

    @pytest.fixture
    def fake_root(self, tmp_path, monkeypatch):
        root = tmp_path / "design_test"
        root.mkdir()
        for day in (20240103, 20240102, 20240104):
            (root / f"day={day}.parquet").write_bytes(b"")
        (root / "_report.json").write_text("{}")      # 달력이 아니다
        (root / "day=bad.parquet").write_bytes(b"")   # 날짜가 아니다
        monkeypatch.setattr(autopsy, "_LABEL_ROOT", str(tmp_path))
        return root

    def test_정렬된_거래일만_돌려준다(self, fake_root):
        assert calendar_days("design_test") == [20240102, 20240103, 20240104]

    def test_달력이_없으면_거부(self, tmp_path, monkeypatch):
        (tmp_path / "empty").mkdir()
        monkeypatch.setattr(autopsy, "_LABEL_ROOT", str(tmp_path))
        with pytest.raises(SystemExit, match="거래일 달력"):
            calendar_days("empty")


class TestCohort:
    @pytest.mark.parametrize("hhmmss,expected", [
        (90000, "A"), (90159, "A"), (90200, "B"), (90459, "B"),
        (90500, "C"), (91959, "C"),
    ])
    def test_경계(self, hhmmss, expected):
        assert cohort_of(hhmmss) == expected

    @pytest.mark.parametrize("hhmmss", [85959, 92000, 100000])
    def test_창_밖은_빈_문자열(self, hhmmss):
        assert cohort_of(hhmmss) == ""


class TestSplit:
    def test_시간_순서로_나뉜다(self):
        days = list(range(20240101, 20240101 + 100))
        out = split_days(days, purge=5)
        assert max(out["train"]) < min(out["valid"])
        assert max(out["valid"]) < min(out["test"])

    def test_purge_가_구간을_떼어_놓는다(self):
        out = split_days(list(range(20240101, 20240101 + 100)), purge=5)
        assert len(out["purged"]) == 10
        # 버린 날은 어느 구간에도 없다.
        for day in out["purged"]:
            assert day not in out["train"] and day not in out["valid"]
            assert day not in out["test"]

    def test_중복_거래일은_한_번만(self):
        out = split_days([20240101] * 50 + list(range(20240102, 20240200)), purge=1)
        joined = out["train"] + out["valid"] + out["test"] + out["purged"]
        assert len(joined) == len(set(joined))

    def test_표본이_얇으면_거부(self):
        with pytest.raises(ValueError, match="분할이 불가능"):
            split_days(list(range(20240101, 20240111)), purge=5)

    @pytest.mark.parametrize("train,valid", [(0, 0.25), (0.8, 0.3), (-0.1, 0.5)])
    def test_잘못된_비율은_거부(self, train, valid):
        with pytest.raises(ValueError):
            split_days(list(range(20240101, 20240201)), train=train, valid=valid)


def _frame(n=200, seed=0):
    rng = np.random.default_rng(seed)
    good = rng.normal(2.0, 1.0, n // 2)
    bad = rng.normal(-2.0, 1.0, n - n // 2)
    return pd.DataFrame({
        "일자": [20240101 + i % 20 for i in range(n)],
        "수익률": np.concatenate([good, bad]),
        "수익금": np.concatenate([good, bad]) * 10_000,
        # 분리력이 있으면서 상수는 아닌 피처(문턱 5 를 사이에 두고 갈린다).
        "B_신호": np.concatenate([rng.uniform(8, 12, n // 2),
                                rng.uniform(0, 4, n - n // 2)]),
        "B_잡음": rng.normal(0, 1, n),
        "B_상수": np.ones(n),
        "B_시분초": np.full(n, 90600),
    })


class TestFeatures:
    def test_상수열과_시분초는_제외(self):
        found = usable_features(_frame())
        assert "B_신호" in found and "B_잡음" in found
        assert "B_상수" not in found and "B_시분초" not in found

    def test_비피처_열은_들어오지_않는다(self):
        found = usable_features(_frame())
        assert all(f.startswith("B_") for f in found)
        assert "수익금" not in found


class TestScan:
    def test_최소_잔존_미만은_버린다(self):
        rows = scan_thresholds(_frame(), ["B_신호"], min_keep=150)
        assert all(r["kept"] >= 150 for r in rows)

    def test_잔존과_탈락의_합은_전체다(self):
        frame = _frame()
        for row in scan_thresholds(frame, ["B_잡음"], min_keep=10):
            assert row["kept"] + row["dropped"] == len(frame)

    def test_두_방향_모두_주사한다(self):
        ops = {r["op"] for r in scan_thresholds(_frame(), ["B_잡음"], min_keep=10)}
        assert ops == {">=", "<"}


class TestSelect:
    def test_예산을_넘지_않는다(self):
        frame = _frame()
        rows = scan_thresholds(frame, usable_features(frame), min_keep=10)
        assert len(select_candidates(frame, rows, budget=3)) <= 3

    def test_기본_예산은_10(self):
        assert DEFAULT_BUDGET == 10

    def test_같은_거래를_남기는_규칙은_하나로_본다(self):
        frame = _frame()
        frame["B_쌍둥이"] = frame["B_신호"]      # 완전히 같은 마스크를 만든다
        rows = scan_thresholds(frame, ["B_신호", "B_쌍둥이"], min_keep=10)
        picked = select_candidates(frame, rows, budget=10)

        def mask(row):
            values = frame[row["feature"]].astype(float)
            return (values >= row["threshold"] if row["op"] == ">="
                    else values < row["threshold"]).to_numpy()

        # 고른 규칙끼리는 어느 쌍도 Jaccard 0.9 이상으로 겹치지 않는다.
        for i, first in enumerate(picked):
            for second in picked[i + 1:]:
                a, b = mask(first), mask(second)
                union = int((a | b).sum())
                assert union and (a & b).sum() / union < 0.9

    def test_효과_큰_순서로_고른다(self):
        frame = _frame()
        rows = scan_thresholds(frame, usable_features(frame), min_keep=10)
        picked = select_candidates(frame, rows, budget=5)
        profits = [r["kept_profit_krw"] for r in picked]
        assert profits == sorted(profits, reverse=True)


class TestBootstrap:
    def test_결정적이다(self):
        frame = _frame()
        keep = frame["B_신호"] > 5
        first = day_block_bootstrap(frame, keep, draws=200, seed=7)
        second = day_block_bootstrap(frame, keep, draws=200, seed=7)
        assert first == second

    def test_관측값이_구간_안에_있다(self):
        frame = _frame()
        keep = frame["B_신호"] > 5
        out = day_block_bootstrap(frame, keep, draws=500, seed=1)
        assert out["ci_low"] <= out["observed_krw"] <= out["ci_high"]

    def test_확실한_이익은_p가_작다(self):
        frame = _frame()
        out = day_block_bootstrap(frame, frame["B_신호"] > 5, draws=1000, seed=2)
        assert out["p_value"] < 0.05

    def test_확실한_손실은_p가_크다(self):
        frame = _frame()
        out = day_block_bootstrap(frame, frame["B_신호"] < 5, draws=1000, seed=3)
        assert out["p_value"] > 0.95

    def test_빈_선택은_안전하게_처리(self):
        frame = _frame()
        out = day_block_bootstrap(frame.iloc[0:0], frame["수익금"].iloc[0:0] > 0)
        assert out["p_value"] == 1.0


class TestBH:
    def test_빈_입력(self):
        assert bh_fdr([]) == []

    def test_전부_유의하면_전부_생존(self):
        assert bh_fdr([0.001, 0.002, 0.003], alpha=0.1) == [True] * 3

    def test_전부_무의미하면_전부_탈락(self):
        assert bh_fdr([0.9, 0.8, 0.7], alpha=0.1) == [False] * 3

    def test_단순_문턱보다_엄격하다(self):
        # 0.09 는 alpha=0.1 을 밑돌지만 10개 중 최악이면 BH 로는 탈락한다.
        pvalues = [0.09] + [0.5] * 9
        assert bh_fdr(pvalues, alpha=0.1)[0] is False

    def test_계단_규칙_중간까지_생존(self):
        # 정렬 후 p_(k) <= alpha*k/n 를 만족하는 최대 k 까지 전부 생존한다.
        out = bh_fdr([0.01, 0.04, 0.9, 0.95], alpha=0.1)
        assert out[:2] == [True, True]
        assert out[2:] == [False, False]


class TestDsl:
    def test_접두를_떼고_어휘로_돌려준다(self):
        assert to_dsl({"feature": "B_매도총잔량", "op": "<",
                       "threshold": 19563.75}) == "매도총잔량 < 19563.8"

    def test_부호가_보존된다(self):
        assert to_dsl({"feature": "B_체결강도", "op": ">=",
                       "threshold": 120.0}) == "체결강도 >= 120"
