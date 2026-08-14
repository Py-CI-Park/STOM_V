"""HOF4 놓친 승자 추출의 순수 함수 검증 — DB·parquet 없이 규칙만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-12_HOF4_사전등록.md
"""

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.run_missed_winners import (
    BAND1_CLAUSES, BAND2_CLAUSES, drop_taken, evaluate_clauses, find_onsets,
    summarize)


def _row(**over):
    base = {
        "일자": 20230102, "종목코드": "000001", "시분초": 90100,
        # 현재가는 고가권 20% 이내(> 5100-400*0.2=5020)여야 전절 통과다.
        "현재가": 5080, "시가": 4800, "고가": 5100, "저가": 4700,
        "등락율": 5.0, "시가총액": 1500, "체결강도": 150.0, "회전율": 3.0,
        "전일비": 10.0, "전일동시간비": 100.0, "당일거래대금": 6000.0,
        "시가등락율": 2.0, "시가대비등락율": 4.0, "고저평균대비등락율": 1.0,
        "초당순매수금액": 50.0, "초당거래대금배율_30": 4.0,
        "초당매수수량": 1000.0, "매도총잔량": 3000.0, "매수총잔량": 5000.0,
        "라운드피겨위5호가이내": 0, "VI가격": 6000.0, "VI호가단위": 10.0,
        "관심종목": 1, "flag_no_trade": 0, "flag_limit_up": 0,
        "flag_vi_near": 0, "trail_5_2": 7.0, "trailt_5_2": 300,
    }
    base.update(over)
    return base


def _frame(rows):
    return pd.DataFrame(rows)


class TestOnsets:
    def test_승자만_남는다(self):
        out = find_onsets(_frame([_row(trail_5_2=7.0), _row(시분초=90300, trail_5_2=3.0)]))
        assert len(out) == 1

    def test_창_밖은_제외(self):
        out = find_onsets(_frame([_row(시분초=90500), _row(시분초=85959)]))
        assert out.empty

    def test_플래그가_켜지면_제외(self):
        rows = [_row(flag_limit_up=1), _row(시분초=90200, flag_vi_near=1),
                _row(시분초=90300, flag_no_trade=1)]
        assert find_onsets(_frame(rows)).empty

    def test_60초_이내_연속_승자는_onset_하나(self):
        rows = [_row(시분초=90100), _row(시분초=90130), _row(시분초=90159)]
        assert len(find_onsets(_frame(rows))) == 1

    def test_60초_넘게_떨어지면_새_onset(self):
        rows = [_row(시분초=90100), _row(시분초=90230)]
        assert len(find_onsets(_frame(rows))) == 2

    def test_종목이_다르면_각각_onset(self):
        rows = [_row(종목코드="000001"), _row(종목코드="000002", 시분초=90101)]
        assert len(find_onsets(_frame(rows))) == 2


def _abs_sec(hhmmss: int) -> int:
    return (hhmmss // 10000) * 3600 + ((hhmmss // 100) % 100) * 60 + hhmmss % 100


class TestDropTaken:
    def test_챔피언이_산_지점_근처는_제외(self):
        onsets = find_onsets(_frame([_row(시분초=90130)]))
        out = drop_taken(onsets, {("000001", _abs_sec(90120)): True})  # 10초 차
        assert out.empty

    def test_다른_종목은_남는다(self):
        onsets = find_onsets(_frame([_row(시분초=90130)]))
        out = drop_taken(onsets, {("999999", _abs_sec(90130)): True})
        assert len(out) == 1

    def test_61초_밖이면_남는다(self):
        onsets = find_onsets(_frame([_row(시분초=90231)]))
        out = drop_taken(onsets, {("000001", _abs_sec(90130)): True})  # 61초 차
        assert len(out) == 1


class TestClauses:
    def test_전절_통과_행은_실패수_0(self):
        out = evaluate_clauses(_frame([_row()]))
        assert out["실패수"].iloc[0] == 0

    def test_밴드_배정(self):
        out = evaluate_clauses(_frame([_row(시분초=90100), _row(시분초=90300)]))
        assert list(out["밴드"]) == [1, 2]

    def test_밴드1_등락율_상한_8(self):
        out = evaluate_clauses(_frame([_row(시분초=90100, 등락율=9.0)]))
        assert "등락율1~8" in out["실패절"].iloc[0]

    def test_밴드2는_등락율_9가_통과(self):
        out = evaluate_clauses(_frame([_row(시분초=90300, 등락율=9.0, 시가대비등락율=4.0)]))
        assert "등락율2~15" not in out["실패절"].iloc[0]

    def test_밴드2_현재가_상한_30000(self):
        out = evaluate_clauses(_frame([_row(시분초=90300, 현재가=40000, 시가=39000,
                                            고가=41000, 저가=38000,
                                            VI가격=45000)]))
        assert "현재가1000~30000" in out["실패절"].iloc[0]

    def test_시가총액_상한(self):
        out = evaluate_clauses(_frame([_row(시가총액=5000)]))
        assert "시가총액<3000" in out["실패절"].iloc[0]

    def test_VI아래5호가(self):
        # 현재가 5000 >= VI가격 5040 - 5*10 = 4990 → 실패
        out = evaluate_clauses(_frame([_row(VI가격=5040.0, VI호가단위=10.0)]))
        assert "VI아래5호가" in out["실패절"].iloc[0]

    def test_밴드1_체결강도_하한_100_밴드2는_50(self):
        f1 = evaluate_clauses(_frame([_row(시분초=90100, 체결강도=80.0)]))
        f2 = evaluate_clauses(_frame([_row(시분초=90300, 체결강도=80.0,
                                           시가대비등락율=4.0)]))
        assert "체결강도100~300" in f1["실패절"].iloc[0]
        assert "체결강도50~300" not in f2["실패절"].iloc[0]

    def test_절_이름은_밴드_목록과_일치(self):
        names1 = {n for n, _ in BAND1_CLAUSES}
        names2 = {n for n, _ in BAND2_CLAUSES}
        assert "등락율1~8" in names1 and "등락율2~15" in names2
        assert len(names1) == len(BAND1_CLAUSES)  # 이름 중복 없음
        assert len(names2) == len(BAND2_CLAUSES)


class TestSummarize:
    def test_단일_실패_집계(self):
        frame = evaluate_clauses(_frame([
            _row(),                                   # 전절 통과
            _row(시분초=90101, 등락율=9.0),             # 등락율만 실패
            _row(시분초=90102, 등락율=9.0, 시가총액=5000),  # 2개 실패
        ]))
        s = summarize(frame)
        assert s["onsets_total"] == 3
        assert s["pass_all"] == 1
        assert s["single_fail"] == 1
        assert s["single_fail_by_clause"]["등락율1~8"]["onsets"] == 1

    def test_미평가_절이_명시된다(self):
        s = summarize(evaluate_clauses(_frame([_row()])))
        assert any("당일거래대금각도" in u for u in s["unevaluated_clauses"])
