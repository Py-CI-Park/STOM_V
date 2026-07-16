"""와이드 시드 V1 -- lane당 통합 중첩 buy 시드 코드/메타데이터 (G004).

`.gjc/_session-019f660b-1c18-7000-98db-61af7bc0d0aa/plans/ralplan/019f660b-1c18-7000-98db-61af7bc0d0aa/stage-09-final.md`
의 'Tick 통합 buy', 'Tick shared sell', 'Min 통합 buy', 'Min shared sell' 섹션에서
합의된, 시분초 3개 시간창 x 시가총액 4개 밴드 = 12 leaf 전체 반복 구조의 매수
전략 코드와 lane 공용 매도 전략 코드를 동결 상수로 노출한다.

이 모듈은 순수 코드/메타데이터 생성기다. `register_seeds`/`export_seed_texts`를
직접 호출하지 않는 한 어떤 파일도 쓰지 않으며, `_database` 경로에는 항상
`ValueError`로 저장을 거부한다 (운영 DB 오염 방지).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 동결 축 값 -- stage-09-final 계획 산출물과 byte-consistent. 임의 변경 금지.
# ---------------------------------------------------------------------------

#: 틱 시간창 경계 (HHMMSS). 서로소·무간극·무중복.
TICK_WINDOWS: tuple[tuple[int, int], ...] = (
    (90000, 90500),
    (90500, 91000),
    (91000, 92000),
)

#: 분봉 시간창 경계 (HHMMSS). 서로소·무간극·무중복.
MIN_WINDOWS: tuple[tuple[int, int], ...] = (
    (90000, 93000),
    (93000, 100000),
    (100000, 140000),
)

#: 시가총액 밴드 (억원 단위). 마지막 상한은 무제한(None).
CAP_BANDS: tuple[tuple[int, Optional[int]], ...] = (
    (0, 3000),
    (3000, 6000),
    (6000, 10000),
    (10000, None),
)

#: cap 밴드에 대응하는 leaf 조건 문자열 (if/elif 순서 고정).
_CAP_CONDITIONS: tuple[str, ...] = (
    "0 < 시가총액 < 3000",
    "3000 <= 시가총액 < 6000",
    "6000 <= 시가총액 < 10000",
    "시가총액 >= 10000",
)

#: SEED_NAMES -- DB 저장 시 사용할 전략명(index 컬럼 값).
SEED_NAMES: dict[str, str] = {
    "tick_buy": "WSEED_V1_Tick_B",
    "tick_sell": "WSEED_V1_Tick_S",
    "min_buy": "WSEED_V1_Min_B",
    "min_sell": "WSEED_V1_Min_S",
}


# ---------------------------------------------------------------------------
# 코드 생성 헬퍼 -- 12개 leaf 각각에 공통 조건 세트 전체를 반복한다
# (leaf별 독립 튜닝 가능성 보존; stage-09-final 합의 사항).
# ---------------------------------------------------------------------------


def _leaf_condition_block(trade_amount_var: str, avg_amount_var: str) -> str:
    """공통 leaf 조건 블록(들여쓰기 8/16/12칸)을 반환한다."""

    return (
        "        if (-15 <= 등락율 < 29 and -15 <= 시가갭등락율 <= 15\n"
        f"                and 당일거래대금 >= 100 and {trade_amount_var} > 0\n"
        "                and 체결강도 >= 체결강도평균(20)\n"
        f"                and {trade_amount_var} >= {avg_amount_var}(20)):\n"
        "            매수 = True\n"
    )


def _cap_branch(idx: int, cap_condition: str, leaf_block: str) -> str:
    """cap 밴드 하나에 대한 `if`/`elif` 분기 텍스트를 반환한다."""

    keyword = "if" if idx == 0 else "elif"
    return f"    {keyword} {cap_condition}:\n{leaf_block}"


def _window_branch(window_condition: str, trade_amount_var: str, avg_amount_var: str) -> str:
    """시간창 하나에 대한 `elif` 분기(내부에 cap 4분기 전체 포함)를 반환한다."""

    leaf_block = _leaf_condition_block(trade_amount_var, avg_amount_var)
    caps = "".join(
        _cap_branch(i, cond, leaf_block) for i, cond in enumerate(_CAP_CONDITIONS)
    )
    return f"elif {window_condition}:\n{caps}"


def _build_wide_buy_code(window_conditions: tuple[str, ...], trade_amount_var: str, avg_amount_var: str) -> str:
    """lane 통합 중첩 buy 코드 전체(3창 x 4cap = 12 leaf)를 조립한다."""

    body = "".join(
        _window_branch(cond, trade_amount_var, avg_amount_var) for cond in window_conditions
    )
    return (
        "매수 = False\n"
        "\n"
        "전일종가 = 현재가 / (1 + 등락율 / 100) if (1 + 등락율 / 100) != 0 else 0\n"
        "시가갭등락율 = ((시가 - 전일종가) / 전일종가) * 100 if 전일종가 > 0 else 999\n"
        "\n"
        "if 데이터길이 < 20:\n"
        "    매수 = False\n"
        f"{body}"
        "\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )


_TICK_WINDOW_CONDITIONS: tuple[str, ...] = tuple(
    f"{lo} <= 시분초 < {hi}" for lo, hi in TICK_WINDOWS
)
_MIN_WINDOW_CONDITIONS: tuple[str, ...] = tuple(
    f"{lo} <= 시분초 < {hi}" for lo, hi in MIN_WINDOWS
)


# ---------------------------------------------------------------------------
# 동결 전략 코드 상수
# ---------------------------------------------------------------------------

#: Tick lane 통합 중첩 매수 (3창 x 4cap = 12 leaf, 전체 조건 반복).
WIDE_TICK_BUY_CODE: str = _build_wide_buy_code(_TICK_WINDOW_CONDITIONS, "초당거래대금", "초당거래대금평균")

#: Min lane 통합 중첩 매수 (3창 x 4cap = 12 leaf, 전체 조건 반복).
WIDE_MIN_BUY_CODE: str = _build_wide_buy_code(_MIN_WINDOW_CONDITIONS, "분당거래대금", "분당거래대금평균")

#: Tick lane 공용 매도 -- unvalidated comparison-control proposal (-3.0/+5.0/300초/09:30).
WIDE_TICK_SELL_CODE: str = (
    "매도 = False\n"
    "\n"
    "if 시분초 >= 93000:\n"
    "    매도 = True\n"
    "elif 수익률 <= -3.0:\n"
    "    매도 = True\n"
    "elif 수익률 >= 5.0:\n"
    "    매도 = True\n"
    "elif 보유시간 >= 300:\n"
    "    매도 = True\n"
    "\n"
    "if 매도:\n"
    "    self.Sell()\n"
)

#: Min lane 공용 매도 -- unvalidated comparison-control proposal (-4.0/+6.0/60분/14:59).
WIDE_MIN_SELL_CODE: str = (
    "매도 = False\n"
    "\n"
    "if 시분초 >= 145900:\n"
    "    매도 = True\n"
    "elif 수익률 <= -4.0:\n"
    "    매도 = True\n"
    "elif 수익률 >= 6.0:\n"
    "    매도 = True\n"
    "elif 보유시간 >= 60:\n"
    "    매도 = True\n"
    "\n"
    "if 매도:\n"
    "    self.Sell()\n"
)


# ---------------------------------------------------------------------------
# LEAF_CELLS -- 24개 leaf 셀 메타데이터 (tick 12 + min 12)
# ---------------------------------------------------------------------------


def _build_leaf_cells(lane: str, windows: tuple[tuple[int, int], ...]) -> list[dict]:
    """lane 하나에 대한 12개 leaf 셀 메타데이터(dict)를 조립한다."""

    cells: list[dict] = []
    ordinal = 0
    for window_lo, window_hi in windows:
        for cap_lo, cap_hi in CAP_BANDS:
            cells.append(
                {
                    "lane": lane,
                    "window_label": f"{window_lo:06d}-{window_hi:06d}",
                    "window_lo": window_lo,
                    "window_hi": window_hi,
                    "cap_lo": cap_lo,
                    "cap_hi": cap_hi,
                    "ordinal": ordinal,
                }
            )
            ordinal += 1
    return cells


#: 24개 leaf 셀(dict) 메타데이터 -- lane, window_label/lo/hi, cap_lo/hi, ordinal.
LEAF_CELLS: list[dict] = _build_leaf_cells("tick", TICK_WINDOWS) + _build_leaf_cells("min", MIN_WINDOWS)


# ---------------------------------------------------------------------------
# 검증 -- compile + (가능하면) token_check
# ---------------------------------------------------------------------------


def syntax_check(code: str) -> list[str]:
    """시드 코드의 구문/토큰 안전성을 검사하고 오류 문자열 리스트를 반환한다.

    빈 리스트는 통과를 의미한다. `ai_strategy_loop.brain.token_check`가
    import 불가한 경우에도 예외를 던지지 않고 결과 리스트에 안내 문구만
    남긴다(compile 검사 자체는 항상 수행됨).
    """

    errors: list[str] = []

    try:
        compile(code, "<seed>", "exec")
    except SyntaxError as exc:
        errors.append(f"SyntaxError: {exc}")
        return errors

    try:
        from ai_strategy_loop.brain.token_check import check_tokens
    except ImportError as exc:
        errors.append(f"token_check 모듈 import 불가(ImportError, 참고용): {exc}")
        return errors

    ok, reason = check_tokens(code)
    if not ok:
        errors.append(f"token_check 거부: {reason}")

    return errors


# ---------------------------------------------------------------------------
# register_seeds -- 격리 루프 DB 전용 저장. 운영 `_database/` 경로는 항상 거부.
# ---------------------------------------------------------------------------


def register_seeds(db_path: str) -> dict:
    """4개 와이드 시드(tick 매수/매도, min 매수/매도)를 `db_path`에 저장한다.

    Args:
        db_path: 저장 대상 sqlite 경로. 격리된 loop 전용 DB만 허용하며,
            경로 문자열에 `_database`가 포함되면 운영 DB로 간주해
            `ValueError`를 던진다(저장 시도조차 하지 않음).

    Returns:
        {"tick_buy": {...}, "tick_sell": {...}, "min_buy": {...}, "min_sell": {...}}
        각 값은 `cli.strategy_generator.save_strategy_to_db`의 반환 dict.
    """

    if "_database" in str(db_path):
        raise ValueError(
            f"운영 DB 경로로 판단되어 시드 저장을 거부합니다 ('_database' 포함): {db_path}"
        )

    from cli.strategy_generator import save_strategy_to_db

    payloads = {
        "tick_buy": (SEED_NAMES["tick_buy"], WIDE_TICK_BUY_CODE, "buy"),
        "tick_sell": (SEED_NAMES["tick_sell"], WIDE_TICK_SELL_CODE, "sell"),
        "min_buy": (SEED_NAMES["min_buy"], WIDE_MIN_BUY_CODE, "buy"),
        "min_sell": (SEED_NAMES["min_sell"], WIDE_MIN_SELL_CODE, "sell"),
    }

    results: dict = {}
    for key, (name, code, strategy_type) in payloads.items():
        results[key] = save_strategy_to_db(db_path, name, code, strategy_type)
    return results


# ---------------------------------------------------------------------------
# export_seed_texts -- 검토용 한글 명명 텍스트 파일 4개 생성 (utility/ai_agent 관례)
# ---------------------------------------------------------------------------


def export_seed_texts(out_dir: Path) -> list[Path]:
    """검토용 와이드 시드 텍스트 파일 4개를 `out_dir`에 작성하고 경로 목록을 반환한다.

    파일명은 `와이드시드V1_<lane>_<매수|매도>_YYYYMMDD.txt` 형식이다.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    specs = (
        ("tick", "매수", SEED_NAMES["tick_buy"], WIDE_TICK_BUY_CODE),
        ("tick", "매도", SEED_NAMES["tick_sell"], WIDE_TICK_SELL_CODE),
        ("min", "매수", SEED_NAMES["min_buy"], WIDE_MIN_BUY_CODE),
        ("min", "매도", SEED_NAMES["min_sell"], WIDE_MIN_SELL_CODE),
    )

    written: list[Path] = []
    for lane, kind, name, code in specs:
        filename = f"와이드시드V1_{lane}_{kind}_{today}.txt"
        file_path = out_dir / filename
        header = f"# {name} - 자동 생성 와이드 시드 V1 ({kind})\n# 생성일: {today}\n"
        file_path.write_text(header + code, encoding="utf-8")
        written.append(file_path)

    return written
