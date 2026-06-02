"""밴드 패러다임 P0 — 시드 902/905 BUY 의 밴드 인코딩 (round-trip 기준).

The seed BUY strategy ``Tick_B_902_905_Update_2`` (see ``seed_strategy_output.txt``
lines 21-131) encoded faithfully as a :class:`BandStrategy`. Compiling
:data:`SEED_902_BUY` with :func:`ai_strategy_loop.brain.band_compiler.compile_to_code`
round-trips to code that is *logically equivalent* to the seed (same conditions,
same order, same nesting) — so it backtests identically. This is the P0 proof that
the band representation + compiler work with ZERO engine change.

인코딩 규칙(design §1):
  - box 단일변수 조건(현재가/등락율/시가등락율/시가대비등락율/회전율/당일거래대금/
    시가총액/체결강도/초당순매수금액) → :class:`BandSpec` (적절한 op).
  - non-box(고저평균대비등락율>0·현재가<VI아래5호가·라운드피겨·당일거래대금각도(30)·
    초당거래대금 비율·초당매수수량 비율·매도/매수총잔량 비율·현재가>고저위치·전일비/
    전일동시간비·당일거래대금>5*100·초당거래대금>초당거래대금N(1)·누적초당*) →
    :class:`FixedFragment` (verbatim).
  - 902 분기(``시분초 < 90200``)·905 분기(``90200 <= 시분초 < 90500``)·후행
    ``else: 매수 = False`` 모두 포착.
"""

from __future__ import annotations

from ai_strategy_loop.brain.band_compiler import (
    BandSpec,
    BandStrategy,
    FixedFragment,
    McapBlock,
    TimeBranch,
)

# 공통 계산 지표 preamble + VI아래5호가 (seed lines 4-21, verbatim 핵심부).
#   주석/빈 줄은 논리에 무관하므로 실행 라인만 보존한다(round-trip 은 논리동등 기준).
_PREAMBLE = (
    "전일종가          = 현재가 / (1 + (등락율 / 100))",
    "시가등락율        = ((시가 - 전일종가) / 전일종가) * 100",
    "시가대비등락율    = ((현재가 - 시가) / 시가) * 100",
    "초당순매수금액    = (초당매수수량 - 초당매도수량) * 현재가 / 1_000_000",
    "VI아래5호가 = VI가격 - VI호가단위 * 5",
)


def _seed_902_branch() -> TimeBranch:
    """902 분기 (``시분초 < 90200``) — seed lines 30-71.

    평면 조건(현재가/등락율/고저평균/VI/라운드피겨) → ``elif 시분초 < 90200:`` →
    ``if 시가총액 < 3000:`` mcap 블록.
    """
    flat = (
        BandSpec("현재가", "lt_le", lo=1000, hi=50000),          # 1000 < 현재가 <= 50000
        BandSpec("등락율", "lt_le", lo=1.0, hi=8.0),             # 1.0 < 등락율 <= 8.0
        FixedFragment("고저평균대비등락율 > 0"),
        FixedFragment("현재가 < VI아래5호가"),
        FixedFragment("라운드피겨위5호가이내", reject_if="satisfied"),                   # elif 라운드피겨...: 매수=False
    )
    mcap = McapBlock(
        cap_lt=3000,
        clauses=(
            BandSpec("시가등락율", "between_le", lo=2.0, hi=4.0),     # 2.0 <= 시가등락율 < 4.0
            BandSpec("시가대비등락율", "between_le", lo=0.5, hi=6.0), # 0.5 <= 시가대비등락율 < 6.0
            BandSpec("초당순매수금액", "gt_lt", lo=1, hi=1000),       # 1 < 초당순매수금액 < 1000
            FixedFragment("현재가 > (고가 - (고가 - 저가) * 0.20)"),
            FixedFragment("전일비 > 0 and 전일동시간비 > 0"),
            FixedFragment("2 < 회전율"),
            FixedFragment("당일거래대금 > 5 * 100"),
            FixedFragment("당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30"),
            FixedFragment("초당거래대금 / 초당거래대금평균(30) > 3.0"),
            FixedFragment("초당매수수량 > 매도총잔량 * 0.20"),
            FixedFragment("매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0"),
            BandSpec("체결강도", "ge_le", lo=50, hi=300),            # 체결강도 >= 50 and <= 300
        ),
    )
    return TimeBranch(
        cond="시분초 < 90200",
        flat_clauses=flat,
        mcap_block=mcap,
        branch_kind="elif",
        inner_time_guard="시분초 < 90200",  # seed: elif 시분초 < 90200 (세부 조건)
        mcap_in_else=False,
    )


def _seed_905_branch() -> TimeBranch:
    """905 분기 (``90200 <= 시분초 < 90500``) — seed lines 75-119.

    평면 조건(현재가/등락율/고저평균/VI/라운드피겨/초당거래대금) → ``else:`` →
    ``if 시가총액 < 3000:`` mcap 블록.
    """
    flat = (
        BandSpec("현재가", "lt_le", lo=1000, hi=30000),          # 1000 < 현재가 <= 30000
        BandSpec("등락율", "lt_le", lo=2.0, hi=15.0),            # 2.0 < 등락율 <= 15.0
        FixedFragment("고저평균대비등락율 > 0"),
        FixedFragment("현재가 < VI아래5호가"),
        FixedFragment("라운드피겨위5호가이내", reject_if="satisfied"),
        FixedFragment("초당거래대금 > 초당거래대금N(1) * 1.0"),
    )
    mcap = McapBlock(
        cap_lt=3000,
        clauses=(
            BandSpec("시가등락율", "between_le", lo=0.0, hi=8.0),     # 0.0 <= 시가등락율 < 8.0
            BandSpec("시가대비등락율", "between_le", lo=3.0, hi=8.0), # 3.0 <= 시가대비등락율 < 8.0
            BandSpec("초당순매수금액", "gt_lt", lo=1, hi=1000),       # 1 < 초당순매수금액 < 1000
            FixedFragment("현재가 > (고가 - (고가 - 저가) * 0.20)"),
            FixedFragment("전일비 > 5 and 전일동시간비 > 0"),
            FixedFragment("회전율 > 1.5"),
            FixedFragment("당일거래대금 > 50 * 100"),
            FixedFragment("당일거래대금각도(30) > 10 and 당일거래대금각도(30) < 30"),
            FixedFragment("초당거래대금 / 초당거래대금평균(30) > 2.0"),
            FixedFragment("초당매수수량 > 매도총잔량 * 0.30"),
            FixedFragment("매도총잔량 * 0.10 < 매수총잔량 * 1.0"),
            FixedFragment("누적초당매수수량(30) * 0.5 < 누적초당매도수량(30) * 1.0"),
            FixedFragment("누적초당매도수량(30) * 1.0 < 누적초당매수수량(30) * 1.0"),
            BandSpec("체결강도", "ge_le", lo=50, hi=300),            # 체결강도 >= 50 and <= 300
        ),
    )
    return TimeBranch(
        cond="90200 <= 시분초 < 90500",
        flat_clauses=flat,
        mcap_block=mcap,
        branch_kind="elif",
        inner_time_guard=None,
        mcap_in_else=True,  # seed 905: 평면조건 else: 안에 mcap
    )


def build_seed_902_buy() -> BandStrategy:
    """시드 ``Tick_B_902_905_Update_2`` BUY 를 밴드 전략으로 인코딩해 반환한다.

    Returns:
        시드 BUY 의 :class:`BandStrategy` 인코딩 (compile 시 시드와 논리동등).
    """
    return BandStrategy(
        kind="buy",
        timeframe="tick",
        preamble=_PREAMBLE,
        state_init="매수 = True",
        preconditions=(FixedFragment("관심종목 == 1"),),  # if not (관심종목 == 1): 매수=False
        time_branches=(_seed_902_branch(), _seed_905_branch()),
        else_false=True,  # else: 매수 = False (09:05 이후)
        call="if 매수:\n    self.Buy()",
    )


# 모듈 import 시 1회 생성 (결정론·side-effect 없음).
SEED_902_BUY: BandStrategy = build_seed_902_buy()
