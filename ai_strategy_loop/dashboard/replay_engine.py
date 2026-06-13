"""Daily tick/min DB replay engine — 시간순 병합 스트림 + tick OHLC 집계 (PR3).

차트 시뮬레이션 탭이 일일 시세 DB(``_database/stock_tick_YYYYMMDD.db`` /
``stock_min_YYYYMMDD.db``)를 시간순으로 리플레이하기 위한 데이터 계층이다. WS 세션
(simulation_api.SimReplaySession)이 이 엔진을 구동해 배속 스케줄로 bar 배치를 push 한다.

설계 계약(무예외):
  - 시세 DB 는 반드시 ``file:...?mode=ro`` 로만 연다(하드링크 원본 오염 방지).
  - 코드별 시계열을 한 번에 메모리로 로드한다(일일 수십 MB → OK). tick 은 ``agg_sec``
    단위 OHLC 로 집계해 과밀 구간 렌더 부하를 줄인다. min 은 행 자체가 1분봉이라 집계 없음.
  - 다종목을 단일 시간축(HHMMSS)으로 병합해 같은 슬롯의 bar 들을 하나의 프레임으로 묶는다.
  - 빈/이상 입력(없는 날짜·종목·빈 DB)에도 raise 하지 않고 빈 시계열을 돌려준다.

용어:
  - bar    : 한 종목의 한 시점(o,h,l,c,vol,등락율,체결강도) — tick 은 집계봉, min 은 분봉.
  - frame  : 같은 시간 슬롯(t)에 속한 여러 종목 bar 의 묶음(WS 가 한 번에 보내는 단위).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 패키지 루트(.../ai_strategy_loop) 기준 경로. CWD 무관.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_DATABASE_DIR = REPO_ROOT / "_database"

# tick 집계 기본 단위(초). 1063행/일 수준이라 10초면 분당 6봉 정도로 압축된다.
DEFAULT_AGG_SEC = 10
# 한 종목 시계열 로드 안전 상한(과대 입력 방지). 일일 tick 도 수천 행 수준.
_MAX_ROWS_PER_CODE = 200_000
# 동시 리플레이 종목 상한(S2 동시보기 1~10). load_replay·WS start 가 공유하는 단일 출처.
MAX_CODES = 10

# 일일 DB candle 컬럼 인덱스(tick 54열 / min 57열 공통 선두 10열은 동일 레이아웃).
#   PRAGMA 확인: 0=index, 1=현재가, 2=시가, 3=고가, 4=저가, 5=등락율,
#               6=당일거래대금, 7=체결강도, 8=(초|분)당매수수량, 9=(초|분)당매도수량.
_COL_INDEX = "index"
_COL_CURRENT = "현재가"
_COL_OPEN = "시가"
_COL_HIGH = "고가"
_COL_LOW = "저가"
_COL_CHANGE = "등락율"
_COL_STRENGTH = "체결강도"
_COL_BUY_QTY_TICK = "초당매수수량"
_COL_SELL_QTY_TICK = "초당매도수량"
_COL_BUY_QTY_MIN = "분당매수수량"
_COL_SELL_QTY_MIN = "분당매도수량"
# min 행의 시가/고가/저가 컬럼은 "당일" 시/고/저 누적값이다(고가는 행마다 단조 증가,
#   시가는 하루 종일 동일 — 20250604 실DB 검증). 분봉 OHLC 는 별도 컬럼에 있다:
#   o=분봉시가, h=분봉고가, l=분봉저가, c=현재가. 이 컬럼이 없는 구버전 DB 는
#   _min_bars 가 직전 종가 기반 근사로 대체한다(당일 컬럼을 봉으로 쓰면 모든 캔들이
#   당일 전체 범위 풀하이트로 그려지는 왜곡 — Phase6.1 사용자 신고 버그).
_COL_MBAR_OPEN = "분봉시가"
_COL_MBAR_HIGH = "분봉고가"
_COL_MBAR_LOW = "분봉저가"
# 호가불균형용 총잔량(컬럼 존재는 PRAGMA 로 동적 확인 — tick/min 레이아웃에서 위치가 다르고
# 일부 구버전 DB 엔 없을 수 있다. 없으면 imbalance=None 으로 흘려보낸다).
_COL_BUY_TOTAL = "매수총잔량"
_COL_SELL_TOTAL = "매도총잔량"
# 라이브 호가 압력 바용 최우선호가(best bid/ask). PRAGMA 로 존재 확인 후 가용할 때만 읽는다.
_COL_BID1 = "매수호가1"
_COL_ASK1 = "매도호가1"
# VWAP 분자용 bar 당 실거래대금(Σ가격×수량). tick=초당·min=분당 (매수금액+매도금액).
# 당일거래대금(누적·백만원 단위 반올림)보다 정확해 이 컬럼을 우선 쓴다(부재 시 None → VWAP None).
_COL_BUY_AMT_TICK = "초당매수금액"
_COL_SELL_AMT_TICK = "초당매도금액"
_COL_BUY_AMT_MIN = "분당매수금액"
_COL_SELL_AMT_MIN = "분당매도금액"

# 변수 라이브 뷰 이동평균 윈도우(종가 롤링). MA60 까지 증분 계산.
_MA_WINDOWS = (5, 20, 60)
# 볼린저 밴드(종가 SMA ± k·표준편차) 윈도우·계수.
_BOLL_WINDOW = 20
_BOLL_K = 2.0
# VWAP 밴드(VWAP ± k·거래대금가중가 표준편차) 윈도우·계수. 볼린저(종가 2σ)와 구분되는 1σ.
_VWAP_BAND_WINDOW = 20
_VWAP_BAND_K = 1.0


def daily_db_path(date: int, src: str) -> Path:
    """일일 DB 파일 경로. src='tick'|'min'."""
    prefix = "stock_tick" if src == "tick" else "stock_min"
    return _DATABASE_DIR / f"{prefix}_{int(date)}.db"


def _connect_ro(db_path: Path) -> Optional[sqlite3.Connection]:
    """일일 시세 DB를 읽기전용(mode=ro)으로만 연다. 없거나 실패하면 None."""
    if not db_path.is_file():
        return None
    try:
        return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


def _table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [str(r[1]) for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]
    except sqlite3.Error:
        return []


def list_tables(date: int, src: str) -> List[str]:
    """그날 DB의 종목 테이블 목록(moneytop 제외, 정렬)."""
    con = _connect_ro(daily_db_path(date, src))
    if con is None:
        return []
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return sorted(str(r[0]) for r in rows if str(r[0]) != "moneytop")


def stock_summary(date: int, src: str) -> List[Dict[str, Any]]:
    """그날 종목별 마지막 행 요약(등락율·거래대금). 등락 내림차순 정렬.

    각 항목: {code, last_change_pct, trade_value, rows}. code_info 이름 결합은
    호출측(simulation_api)에서 한다(이 엔진은 시세 DB 만 본다).
    """
    con = _connect_ro(daily_db_path(date, src))
    if con is None:
        return []
    out: List[Dict[str, Any]] = []
    try:
        tables = sorted(
            str(r[0]) for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if str(r[0]) != "moneytop"
        )
        for code in tables:
            cols = _table_columns(con, code)
            if _COL_INDEX not in cols:
                continue
            change_expr = f'"{_COL_CHANGE}"' if _COL_CHANGE in cols else "0"
            value_expr = f'"{_COL_CURRENT}"' if _COL_CURRENT in cols else "0"
            tv_expr = '"당일거래대금"' if "당일거래대금" in cols else "0"
            try:
                row = con.execute(
                    f'SELECT {change_expr}, {tv_expr}, {value_expr}, COUNT(*) '
                    f'FROM (SELECT * FROM "{code}" ORDER BY "{_COL_INDEX}")'
                ).fetchone()
                last = con.execute(
                    f'SELECT {change_expr}, {tv_expr} FROM "{code}" '
                    f'ORDER BY "{_COL_INDEX}" DESC LIMIT 1'
                ).fetchone()
                cnt = con.execute(f'SELECT COUNT(*) FROM "{code}"').fetchone()
            except sqlite3.Error:
                continue
            if last is None:
                continue
            out.append({
                "code": code,
                "last_change_pct": _safe_float(last[0]),
                "trade_value": _safe_float(last[1]),
                "rows": int(cnt[0]) if cnt else 0,
            })
    except sqlite3.Error:
        return out
    finally:
        con.close()
    out.sort(key=lambda r: r["last_change_pct"], reverse=True)
    return out


def _safe_float(value: Any) -> float:
    try:
        f = float(value)
        return f if f == f else 0.0  # NaN guard
    except (TypeError, ValueError):
        return 0.0


def _load_code_rows(
    con: sqlite3.Connection, code: str, src: str
) -> List[Dict[str, Any]]:
    """한 종목의 candle 행을 시간순 dict 리스트로 로드한다(읽기전용·무예외).

    각 행: {ts(int index), o,h,l,c, vol(거래량 추정=매수+매도수량),
            net_qty(순매수수량=매수−매도), trade_amt(bar 거래대금=매수+매도금액 — VWAP 분자),
            change, strength,
            imbalance(호가불균형=매수총잔량/매도총잔량 — 컬럼 부재 시 None),
            buy_rest(매수총잔량 raw), sell_rest(매도총잔량 raw),
            bid1(매수호가1)/ask1(매도호가1) — 컬럼 부재 시 None}.
    호가/잔량/금액 컬럼은 PRAGMA 로 존재를 확인 후 가용할 때만 읽는다(구버전 DB 하위호환).
    imbalance 와 raw 잔량은 같은 컬럼을 공유한다(중복 조회 없음).
    """
    cols = _table_columns(con, code)
    if _COL_INDEX not in cols:
        return []
    buy_q = _COL_BUY_QTY_TICK if src == "tick" else _COL_BUY_QTY_MIN
    sell_q = _COL_SELL_QTY_TICK if src == "tick" else _COL_SELL_QTY_MIN
    buy_amt = _COL_BUY_AMT_TICK if src == "tick" else _COL_BUY_AMT_MIN
    sell_amt = _COL_SELL_AMT_TICK if src == "tick" else _COL_SELL_AMT_MIN
    has_imbalance = _COL_BUY_TOTAL in cols and _COL_SELL_TOTAL in cols
    has_quote = _COL_BID1 in cols and _COL_ASK1 in cols
    has_amount = buy_amt in cols and sell_amt in cols
    # 분봉 OHLC 정본 컬럼(min 전용 — 시가/고가/저가는 당일 누적값이라 봉에 못 쓴다).
    has_mbar = (
        src == "min"
        and _COL_MBAR_OPEN in cols
        and _COL_MBAR_HIGH in cols
        and _COL_MBAR_LOW in cols
    )

    def col(name: str) -> str:
        return f'"{name}"' if name in cols else "NULL"

    select = (
        f'SELECT "{_COL_INDEX}", {col(_COL_CURRENT)}, {col(_COL_OPEN)}, '
        f'{col(_COL_HIGH)}, {col(_COL_LOW)}, {col(_COL_CHANGE)}, '
        f'{col(_COL_STRENGTH)}, {col(buy_q)}, {col(sell_q)}, '
        f'{col(_COL_BUY_TOTAL)}, {col(_COL_SELL_TOTAL)}, '
        f'{col(_COL_BID1)}, {col(_COL_ASK1)}, {col(buy_amt)}, {col(sell_amt)}, '
        f'{col(_COL_MBAR_OPEN)}, {col(_COL_MBAR_HIGH)}, {col(_COL_MBAR_LOW)} '
        f'FROM "{code}" ORDER BY "{_COL_INDEX}" LIMIT {_MAX_ROWS_PER_CODE}'
    )
    rows: List[Dict[str, Any]] = []
    try:
        cursor = con.execute(select)
    except sqlite3.Error:
        return []
    for r in cursor:
        try:
            ts = int(r[0])
        except (TypeError, ValueError):
            continue
        buy_qty = _safe_float(r[7])
        sell_qty = _safe_float(r[8])
        # bar 당 실거래대금(Σ가격×수량) = 매수금액 + 매도금액. VWAP 분자(누적합).
        trade_amt = (_safe_float(r[13]) + _safe_float(r[14])) if has_amount else None
        rows.append({
            "ts": ts,
            "c": _safe_float(r[1]),
            "o": _safe_float(r[2]),
            "h": _safe_float(r[3]),
            "l": _safe_float(r[4]),
            "change": _safe_float(r[5]),
            "strength": _safe_float(r[6]),
            "vol": buy_qty + sell_qty,
            "net_qty": buy_qty - sell_qty,
            "trade_amt": trade_amt,
            "imbalance": _imbalance(r[9], r[10]) if has_imbalance else None,
            "buy_rest": _safe_float(r[9]) if has_imbalance else None,
            "sell_rest": _safe_float(r[10]) if has_imbalance else None,
            "bid1": _safe_float(r[11]) if has_quote else None,
            "ask1": _safe_float(r[12]) if has_quote else None,
            "mo": _safe_float(r[15]) if has_mbar else None,
            "mh": _safe_float(r[16]) if has_mbar else None,
            "ml": _safe_float(r[17]) if has_mbar else None,
        })
    return rows


def _imbalance(buy_total: Any, sell_total: Any) -> Optional[float]:
    """호가불균형 = 매수총잔량 / 매도총잔량. 매도총잔량 0/음수면 None(분모 보호)."""
    buy = _safe_float(buy_total)
    sell = _safe_float(sell_total)
    if sell <= 0:
        return None
    return buy / sell


def _hms_from_index(ts: int, src: str) -> int:
    """index(YYYYMMDDHHMMSS tick / YYYYMMDDHHMM min) → HHMMSS(int, min 은 *100)."""
    s = str(ts)
    if src == "tick" and len(s) >= 14:
        return int(s[8:14])
    if src == "min" and len(s) >= 12:
        return int(s[8:12]) * 100  # HHMM → HHMMSS(초=00)
    # 폴백: 뒤 6자리.
    tail = s[-6:] if len(s) >= 6 else s
    try:
        return int(tail)
    except ValueError:
        return 0


def _agg_bucket(hms: int, agg_sec: int) -> int:
    """HHMMSS 를 agg_sec 초 버킷의 시작 HHMMSS 로 내림 정렬한다."""
    if agg_sec <= 1:
        return hms
    h, m, s = hms // 10000, (hms // 100) % 100, hms % 100
    total = h * 3600 + m * 60 + s
    floored = (total // agg_sec) * agg_sec
    return (floored // 3600) * 10000 + ((floored % 3600) // 60) * 100 + (floored % 60)


def _aggregate_tick(rows: List[Dict[str, Any]], agg_sec: int) -> List[Dict[str, Any]]:
    """tick 행들을 agg_sec 단위 OHLC 봉으로 집계한다(시간순 유지).

    o=버킷 첫 현재가, h/l=버킷 내 고저(현재가 기준), c=버킷 마지막 현재가,
    vol=합산, change/strength=버킷 마지막 값.
    """
    if agg_sec <= 1:
        # 집계 없이 현재가를 OHLC 로 쓰되, h/l 은 행의 고저 컬럼을 존중.
        return [
            {
                "hms": _hms_from_index(r["ts"], "tick"),
                "o": r["c"], "h": max(r["c"], r["h"]), "l": min(r["c"], r["l"] or r["c"]),
                "c": r["c"], "vol": r["vol"], "net_qty": r.get("net_qty"),
                "trade_amt": r.get("trade_amt"),
                "change": r["change"], "strength": r["strength"],
                "imbalance": r.get("imbalance"),
                "buy_rest": r.get("buy_rest"), "sell_rest": r.get("sell_rest"),
                "bid1": r.get("bid1"), "ask1": r.get("ask1"),
            }
            for r in rows
        ]
    buckets: "Dict[int, Dict[str, Any]]" = {}
    order: List[int] = []
    for r in rows:
        hms = _hms_from_index(r["ts"], "tick")
        b = _agg_bucket(hms, agg_sec)
        price = r["c"]
        cur = buckets.get(b)
        if cur is None:
            buckets[b] = {
                "hms": b, "o": price, "h": price, "l": price, "c": price,
                "vol": r["vol"], "net_qty": (r.get("net_qty") or 0.0),
                "trade_amt": r.get("trade_amt"),
                "change": r["change"], "strength": r["strength"],
                "imbalance": r.get("imbalance"),
                "buy_rest": r.get("buy_rest"), "sell_rest": r.get("sell_rest"),
                "bid1": r.get("bid1"), "ask1": r.get("ask1"),
            }
            order.append(b)
        else:
            cur["h"] = max(cur["h"], price)
            cur["l"] = min(cur["l"], price)
            cur["c"] = price
            cur["vol"] += r["vol"]
            cur["net_qty"] += (r.get("net_qty") or 0.0)   # 순매수수량은 버킷 내 합산.
            # bar 당 거래대금도 버킷 내 합산(VWAP 분자 — 마지막값 아님). None 이면 합산 스킵.
            amt = r.get("trade_amt")
            if amt is not None:
                cur["trade_amt"] = (cur.get("trade_amt") or 0.0) + amt
            cur["change"] = r["change"]
            cur["strength"] = r["strength"]
            cur["imbalance"] = r.get("imbalance")
            # 스냅샷 값(잔량·호가)은 버킷 마지막 행으로 대표(imbalance·strength 와 동일).
            cur["buy_rest"] = r.get("buy_rest")
            cur["sell_rest"] = r.get("sell_rest")
            cur["bid1"] = r.get("bid1")
            cur["ask1"] = r.get("ask1")
    return [buckets[b] for b in order]


def _min_bars(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """min 행 → 1분봉. 분봉시가/분봉고가/분봉저가 컬럼이 정본(c=현재가).

    행의 시가/고가/저가는 "당일" 누적 시/고/저라 봉으로 쓰면 모든 캔들이 당일 전체
    범위로 그려진다(Phase6.1 신고 버그). 분봉 컬럼이 없는 구버전 DB 는 직전 종가를
    시가로 한 근사봉(h=max(o,c), l=min(o,c))으로 대체한다 — 첫 봉만 당일 시가 사용.
    """
    out: List[Dict[str, Any]] = []
    prev_close: float = 0.0
    for r in rows:
        c = r["c"]
        if r.get("mo") and r.get("mh") and r.get("ml"):
            o = r["mo"]
            h = max(r["mh"], o, c)
            l = min(r["ml"], o, c)
        else:
            o = prev_close or r["o"] or c
            h = max(o, c)
            l = min(o, c)
        prev_close = c
        out.append({
            "hms": _hms_from_index(r["ts"], "min"),
            "o": o,
            "h": h,
            "l": l,
            "c": c,
            "vol": r["vol"],
            "net_qty": r.get("net_qty"),
            "trade_amt": r.get("trade_amt"),
            "change": r["change"],
            "strength": r["strength"],
            "imbalance": r.get("imbalance"),
            "buy_rest": r.get("buy_rest"),
            "sell_rest": r.get("sell_rest"),
            "bid1": r.get("bid1"),
            "ask1": r.get("ask1"),
        })
    return out


def _attach_moving_averages(bars: List[Dict[str, Any]]) -> None:
    """종가 롤링 이동평균(MA5/20/60)을 각 bar 에 증분 계산해 붙인다(제자리 수정).

    전체 재계산 금지 — 각 윈도우당 running sum 을 유지해 O(n) 으로 채운다. 윈도우가
    아직 안 찼으면(예: 4번째 bar 의 MA5) None 으로 둔다(부분 평균은 오해 소지).
    """
    if not bars:
        return
    sums = {w: 0.0 for w in _MA_WINDOWS}
    closes: List[float] = []
    for i, bar in enumerate(bars):
        c = _safe_float(bar.get("c"))
        closes.append(c)
        for w in _MA_WINDOWS:
            sums[w] += c
            if i >= w:
                sums[w] -= closes[i - w]
            key = f"ma{w}"
            bar[key] = (sums[w] / w) if (i + 1) >= w else None


def _attach_vwap(bars: List[Dict[str, Any]]) -> None:
    """VWAP(거래량 가중 평균가) + VWAP 밴드를 각 bar 에 증분 계산해 붙인다(제자리 수정).

    VWAP = Σ(bar 거래대금) / Σ(bar 거래량). bar 거래대금(trade_amt)은
    (초|분)당매수금액+매도금액(=Σ가격×수량) 이라 정확하다. 금액 컬럼 부재(trade_amt=None)
    또는 누적거래량 0 이면 vwap=None(분모/데이터 보호).

    VWAP 밴드(vwap_up/vwap_low) = vwap ± _VWAP_BAND_K·σ. σ 는 bar 거래대금가중가
    (typ = trade_amt/vol, 즉 그 봉의 평균체결가)의 _VWAP_BAND_WINDOW 롤링 표준편차다.
    윈도우 미충족·금액 컬럼 부재·vwap None 이면 vwap_up/vwap_low = None(MA/볼린저 정책과 동일).
    running sum/제곱합으로 O(n)(볼린저와 동형). 음수 분산은 부동소수 오차로 보고 0 클램프.
    """
    if not bars:
        return
    cum_amt = 0.0
    cum_vol = 0.0
    w = _VWAP_BAND_WINDOW
    typs: List[Optional[float]] = []   # bar 평균체결가(trade_amt/vol) — None 은 윈도우 미포함.
    s = 0.0       # 롤링 윈도우 내 typ 합.
    s2 = 0.0      # 롤링 윈도우 내 typ 제곱합.
    n = 0         # 롤링 윈도우 내 유효 typ 개수(σ 분모).
    for i, bar in enumerate(bars):
        amt = bar.get("trade_amt")
        # 금액·거래량은 짝으로만 누적해 분자/분모 동기를 보장(금액 부재 bar 는 둘 다 스킵).
        vwap: Optional[float] = None
        if amt is not None:
            cum_amt += _safe_float(amt)
            cum_vol += _safe_float(bar.get("vol"))
            if cum_vol > 0:
                vwap = cum_amt / cum_vol
        bar["vwap"] = vwap

        # 그 봉의 평균체결가(typ) — trade_amt/vol. 둘 중 하나라도 부재/0 이면 None(σ 제외).
        bar_vol = _safe_float(bar.get("vol"))
        typ: Optional[float] = (_safe_float(amt) / bar_vol) if (amt is not None and bar_vol > 0) else None
        typs.append(typ)
        if typ is not None:
            s += typ
            s2 += typ * typ
            n += 1
        if i >= w:
            old = typs[i - w]
            if old is not None:
                s -= old
                s2 -= old * old
                n -= 1
        # 밴드는 vwap 가 있고 윈도우가 유효 typ 로 가득 찼을 때만(부분 통계 금지).
        if vwap is not None and n >= w:
            mean = s / n
            var = (s2 / n) - (mean * mean)
            if var < 0:
                var = 0.0
            sd = var ** 0.5
            bar["vwap_up"] = vwap + _VWAP_BAND_K * sd
            bar["vwap_low"] = vwap - _VWAP_BAND_K * sd
        else:
            bar["vwap_up"] = None
            bar["vwap_low"] = None


def _attach_bollinger(bars: List[Dict[str, Any]]) -> None:
    """볼린저 밴드(종가 SMA20 ± 2σ)를 각 bar 에 증분 계산해 붙인다(제자리 수정).

    윈도우(_BOLL_WINDOW) 미충족 구간은 None(부분 통계는 오해 소지 — MA 정책과 동일).
    running sum/제곱합으로 O(n) 표준편차(모표준편차). 음수 분산은 부동소수 오차로 보고 0 클램프.
    """
    if not bars:
        return
    w = _BOLL_WINDOW
    closes: List[float] = []
    s = 0.0
    s2 = 0.0
    for i, bar in enumerate(bars):
        c = _safe_float(bar.get("c"))
        closes.append(c)
        s += c
        s2 += c * c
        if i >= w:
            old = closes[i - w]
            s -= old
            s2 -= old * old
        if (i + 1) >= w:
            mean = s / w
            var = (s2 / w) - (mean * mean)
            if var < 0:
                var = 0.0
            sd = var ** 0.5
            bar["bb_mid"] = mean
            bar["bb_up"] = mean + _BOLL_K * sd
            bar["bb_low"] = mean - _BOLL_K * sd
        else:
            bar["bb_mid"] = None
            bar["bb_up"] = None
            bar["bb_low"] = None


class ReplayData:
    """리플레이 1세션의 메모리 자료구조 — 코드별 시계열 + 병합된 시간축.

    frames: List[{t:int HHMMSS, items:[{code,o,h,l,c,vol,change,strength,
                  ma5,ma20,ma60,vwap,vwap_up,vwap_low,bb_mid,bb_up,bb_low,net_qty,
                  imbalance,buy_rest,sell_rest,bid1,ask1}...]}].
    동일 t 슬롯의 종목 bar 들은 같은 frame 에 묶인다. seek 은 t→frame 인덱스 점프.
    buy_rest/sell_rest/bid1/ask1/net_qty/vwap/vwap_up/vwap_low/bb_* 는 컬럼·데이터 부재 시 None(하위호환).
    """

    def __init__(
        self,
        date: int,
        src: str,
        codes: List[str],
        frames: List[Dict[str, Any]],
        session_range: Tuple[int, int],
    ) -> None:
        self.date = date
        self.src = src
        self.codes = codes
        self.frames = frames
        self.session_range = session_range

    @property
    def bars_total(self) -> int:
        return len(self.frames)

    def seek_index(self, hms: int) -> int:
        """t(HHMMSS) 이상인 첫 frame 인덱스를 이진 탐색한다(없으면 끝)."""
        lo, hi = 0, len(self.frames)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.frames[mid]["t"] < hms:
                lo = mid + 1
            else:
                hi = mid
        return lo


def load_replay(
    date: int,
    src: str,
    codes: List[str],
    *,
    agg_sec: int = DEFAULT_AGG_SEC,
) -> ReplayData:
    """일일 DB 에서 codes 의 시계열을 로드·집계·병합해 ReplayData 를 만든다(무예외).

    codes 없음/없는 날짜/빈 DB → frames=[] 로 정상 반환(WS 가 즉시 done 처리).
    """
    src = "tick" if src == "tick" else "min"
    agg_sec = int(agg_sec) if agg_sec else DEFAULT_AGG_SEC
    if agg_sec < 1:
        agg_sec = 1
    codes = [str(c) for c in (codes or [])][:MAX_CODES]  # 최대 MAX_CODES 종목(S2).

    con = _connect_ro(daily_db_path(date, src))
    if con is None or not codes:
        if con is not None:
            con.close()
        return ReplayData(date, src, codes, [], (0, 0))

    # 코드별 봉 시계열(hms→bar) 적재.
    per_code: Dict[str, Dict[int, Dict[str, Any]]] = {}
    valid_codes: List[str] = []
    try:
        existing = {
            str(r[0]) for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for code in codes:
            if code not in existing:
                continue
            rows = _load_code_rows(con, code, src)
            if not rows:
                continue
            bars = _aggregate_tick(rows, agg_sec) if src == "tick" else _min_bars(rows)
            if not bars:
                continue
            _attach_moving_averages(bars)
            _attach_vwap(bars)
            _attach_bollinger(bars)
            valid_codes.append(code)
            per_code[code] = {b["hms"]: b for b in bars}
    finally:
        con.close()

    if not per_code:
        return ReplayData(date, src, valid_codes, [], (0, 0))

    # 전체 시간축(모든 코드 hms 합집합) 정렬 → frame 병합.
    all_hms = sorted({hms for series in per_code.values() for hms in series})
    frames: List[Dict[str, Any]] = []
    for t in all_hms:
        items: List[Dict[str, Any]] = []
        for code in valid_codes:
            bar = per_code[code].get(t)
            if bar is None:
                continue
            items.append({
                "code": code,
                "o": bar["o"], "h": bar["h"], "l": bar["l"], "c": bar["c"],
                "vol": bar["vol"], "change": bar["change"], "strength": bar["strength"],
                "ma5": bar.get("ma5"), "ma20": bar.get("ma20"), "ma60": bar.get("ma60"),
                "vwap": bar.get("vwap"),
                "vwap_up": bar.get("vwap_up"), "vwap_low": bar.get("vwap_low"),
                "bb_mid": bar.get("bb_mid"), "bb_up": bar.get("bb_up"), "bb_low": bar.get("bb_low"),
                "net_qty": bar.get("net_qty"),
                "imbalance": bar.get("imbalance"),
                "buy_rest": bar.get("buy_rest"), "sell_rest": bar.get("sell_rest"),
                "bid1": bar.get("bid1"), "ask1": bar.get("ask1"),
            })
        if items:
            frames.append({"t": t, "items": items})

    session_range = (all_hms[0], all_hms[-1]) if all_hms else (0, 0)
    return ReplayData(date, src, valid_codes, frames, session_range)
