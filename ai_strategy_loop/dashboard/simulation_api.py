"""Chart simulation API — 일일 tick/min DB 리플레이 + 조건식 매매 오버레이 (PR3).

웹 대시보드 "차트 시뮬레이션" 탭의 백엔드. 일일 시세 DB(``stock_tick_YYYYMMDD.db`` /
``stock_min_YYYYMMDD.db``)를 시간순으로 리플레이하고, 조건식 매수/매도 신호를 차트에
오버레이한다. replay_engine.py 가 데이터 계층(로드·집계·병합·seek)을 담당한다.

라우트:
  - GET  /sim/days?src=tick|min                 → 일일 DB 날짜 인벤토리.
  - GET  /sim/stocks?date&src                    → 그날 종목(코드·이름·등락·거래대금) 등락순.
  - GET  /sim/signals?date&src&code&buy&sell      → 조건식 매매 신호(아래 정합 설계).
  - GET  /sim/signals/batch?date&src&codes&buy&sell → bounded per-code signal results.
  - WS   /sim/ws                                  → 리플레이 세션(start/pause/resume/speed/seek/stop).

조건식 매매 오버레이 — 엔진 정합(핵심 설계 결정):
  리플레이는 신호 평가기를 재구현하지 않는다. /sim/signals 는 PR2 의
  BacktestJobManager 로 **해당 날짜 1일·한종목(one_code) 백테스트**를 실행(또는 동일
  spec 의 완료 잡을 캐시 재사용)하고, per-trade CSV 에서 그 종목 거래의
  {매수시간, 매도시간, 매수가, 매도가, 수익률} 을 추출해 반환한다. **백테스트 엔진이
  실제로 낸 신호이므로 리플레이 차트와 100% 정합**한다(평가 의미 차이 0).

설계 계약(무예외):
  - 모든 REST 는 데이터 없어도 빈 구조를 반환하고 절대 500 으로 대시보드를 깨지 않는다.
  - 시세 DB 는 replay_engine 이 ``file:...?mode=ro`` 로만 연다(하드링크 보호).
  - 동시 WS 세션 4개까지 허용(초과 시 정중한 error 후 종료). 각 세션은 독립
    리플레이 태스크를 갖고 disconnect/stop 시 자기 세션만 정리한다. 세션 간
    자원 간섭 없음(각자 일일 DB 읽기전용 — 파일 핸들 독립).
  - app.py 접점은 ``include_router`` 한 줄(wt-dev 머지 충돌 최소화).
"""

from __future__ import annotations

import asyncio
import csv
import itertools
import sqlite3
import threading
import time
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Protocol, TypedDict, assert_never

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic_core import PydanticCustomError

from ai_strategy_loop.dashboard import replay_engine
from ai_strategy_loop.dashboard.backtest_jobs import (
    BacktestJobSpec,
    get_job_manager,
)
from ai_strategy_loop.dashboard.security import (
    MAX_WEBSOCKET_MESSAGE_CHARS,
    Capability,
    close_websocket_failure,
)

# 패키지 루트(.../ai_strategy_loop) 기준 경로.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_DATABASE_DIR = REPO_ROOT / "_database"
_CODE_INFO_DB = _DATABASE_DIR / "code_info.db"

# --- wall-clock 페이싱 상수 -------------------------------------------------
# bar 간 실제 시간차(t_delta)/speed 만큼 sleep 하는 정밀 페이싱. speed=1x 면 1초봉이
# 정확히 1초마다·1분봉이 1분마다 전송된다(시간이 실제로 흐르는 체감). 고배속은 sleep 을
# 잘게 줄이되 bar 시간 비례를 유지한다(프레임 누락 없이 빠르게 흐름).
_MAX_SPEED = 600
# 한 sleep 의 하한(초) — 너무 잦은 await 로 이벤트 루프가 과부하 되지 않도록 묶음 처리한다.
_MIN_FRAME_SLEEP_SEC = 0.02
# 누적 대기시간이 이 값을 넘으면 그때까지 모인 frame 들을 한 번에 flush 하고 sleep 한다.
# (고배속에서 1프레임당 sleep 이 _MIN_FRAME_SLEEP_SEC 미만이면 묶음 — 묶음 내 시간 비례 유지.)
_FRAME_FLUSH_SLEEP_SEC = 0.05
# 한 번에 보낼 frame 배치 절대 상한(폭주 입력 방어). 시간 비례 묶음이 이보다 커지면 잘라 보낸다.
_MAX_BATCH = 256
# seek 스냅샷 코드당 봉 상한(차트 가시 윈도우보다 넉넉히 — payload 폭주 방지).
_HISTORY_MAX_BARS = 2000
# 페이싱 sleep 을 잘게 쪼개는 청크(초) — 긴 대기(예: 1x min=60s)도 이 간격마다 stop/pause/seek 에 반응.
_PACED_SLEEP_CHUNK_SEC = 0.05
# bar 간 t_delta 산출 시 비정상(역행·과대) 간격을 막는 상한(초). 장 중 정상 gap 은 수 초~수십 초.
# 동시 WS 리플레이 세션 상한(프로세스 전역). 초과 연결은 정중히 거절.
_MAX_SESSIONS = 4
# /sim/signals 잡 폴링 상한(초). 1일·1종목 백테는 통상 1분 내.
_SIGNAL_JOB_TIMEOUT = 180

ReplayCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class _ReplayControl(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ReplayStartControl(_ReplayControl):
    action: Literal["start"]
    date: int = Field(ge=20_000_101, le=20_991_231)
    src: Literal["tick", "min"] = "min"
    codes: list[ReplayCode] = Field(min_length=1, max_length=replay_engine.MAX_CODES)
    agg_sec: int = Field(default=replay_engine.DEFAULT_AGG_SEC, ge=1, le=3_600)
    speed: int = Field(default=1, ge=1, le=_MAX_SPEED)


class ReplayPauseControl(_ReplayControl):
    action: Literal["pause"]


class ReplayResumeControl(_ReplayControl):
    action: Literal["resume"]


class ReplaySpeedControl(_ReplayControl):
    action: Literal["speed"]
    value: int = Field(ge=1, le=_MAX_SPEED)


class ReplaySeekControl(_ReplayControl):
    action: Literal["seek"]
    t: int = Field(ge=0, le=235_959)

    @field_validator("t")
    @classmethod
    def validate_timestamp(cls, value: int) -> int:
        try:
            replay_engine.hms_to_seconds(value)
        except replay_engine.ReplayTimelineError as exc:
            raise PydanticCustomError(
                "invalid_hhmmss",
                "timestamp must be valid HHMMSS",
            ) from exc
        return value


class ReplaySeekIndexControl(_ReplayControl):
    action: Literal["seek_index"]
    index: int = Field(ge=0, le=10_000_000)


class ReplayStopControl(_ReplayControl):
    action: Literal["stop"]


ReplayControl = Annotated[
    ReplayStartControl
    | ReplayPauseControl
    | ReplayResumeControl
    | ReplaySpeedControl
    | ReplaySeekControl
    | ReplaySeekIndexControl
    | ReplayStopControl,
    Field(discriminator="action"),
]
_REPLAY_CONTROL_ADAPTER = TypeAdapter(ReplayControl)


def _hms_to_seconds(hms: int) -> int:
    """HHMMSS(int) → 자정 기준 초. 페이싱의 bar 간 t_delta 산출에 쓴다."""
    return replay_engine.hms_to_seconds(hms)


def _bar_gap_seconds(prev_t: int, next_t: int) -> float:
    """두 유효 frame 시각 사이의 실제 경과 초를 반환한다."""
    gap = _hms_to_seconds(next_t) - _hms_to_seconds(prev_t)
    if gap <= 0:
        raise replay_engine.ReplayTimelineError(
            timestamp=next_t,
            reason="frame timestamps must be strictly increasing",
        )
    return float(gap)


def _pacing_schedule(times: List[int], speed: int) -> List[float]:
    """frame 시각열 → 각 frame '전송 직전' 대기초(speed 반영) 목록.

    schedule[i] = (times[i] - times[i-1]) 의 실제 초 / speed (i=0 은 0 — 첫 frame 즉시).
    speed 가 클수록 대기는 비례 축소된다(wall-clock 페이싱). 순수 함수라 단위테스트로
    sleep 간격을 직접 검증한다(monkeypatch 없이 스케줄만 확인 가능).
    """
    spd = _clamp_speed(speed)
    out: List[float] = []
    prev: Optional[int] = None
    for t in times:
        if prev is None:
            out.append(0.0)
        else:
            out.append(_bar_gap_seconds(prev, int(t)) / spd)
        prev = int(t)
    return out


class HealthResponse(TypedDict):
    status: str
    module: str
    api_version: int


simulation_router = APIRouter(prefix="/sim", tags=["simulation"])


@simulation_router.get("/health")
def simulation_health() -> HealthResponse:
    """차트 시뮬레이션 API 헬스 체크. 탭 셸 연결 상태 배지가 소비한다."""
    return {"status": "ok", "module": "simulation_api", "api_version": 1}


# --------------------------------------------------------------------- inventory
@simulation_router.get("/days")
def sim_days(src: str = "tick") -> Dict[str, Any]:
    """``_database`` 의 일일 DB 날짜 인벤토리(정렬). src='tick'|'min'."""
    src = "tick" if src == "tick" else "min"
    prefix = "stock_tick" if src == "tick" else "stock_min"
    days = _daily_db_dates(prefix)
    return {"days": days, "count": len(days), "src": src}


def _daily_db_dates(prefix: str) -> List[int]:
    """``_database/<prefix>_YYYYMMDD.db`` 파일에서 날짜 목록(정렬)을 추출한다."""
    dates: List[int] = []
    try:
        for entry in _DATABASE_DIR.glob(f"{prefix}_*.db"):
            tail = entry.stem.rsplit("_", 1)[-1]
            if len(tail) == 8 and tail.isdigit():
                dates.append(int(tail))
    except OSError:
        return []
    return sorted(set(dates))


# 데모/프리셋 추천 — '최대 상승일' 근사 시 스캔하는 최근 일수 상한(과한 I/O 방지).
_DEMO_SCAN_DAYS = 8


@simulation_router.get("/demo")
def sim_demo(src: str = "min", mode: str = "latest") -> Dict[str, Any]:
    """즉시 체험용 추천(날짜·종목) — 실제 인벤토리에서 자동 선택.

    탭 최초 진입 자동 데모와 원클릭 프리셋이 소비한다. 신호 백테는 돌리지 않고
    인벤토리 요약만 읽으므로 빠르고 무예외(데이터 없으면 빈 추천).

      - mode='latest'      : 최신 거래일 + 그날 등락 1위 종목.
      - mode='top_gainer'  : 최근 _DEMO_SCAN_DAYS 일을 샘플 조회해 등락 1위가 가장
                             큰 날 + 그 종목('최대 상승일' 근사).

    반환: {date, code, name, change_pct, src, mode, available}. 날짜/종목이 없으면
    available=False 로 빈 추천(클라이언트가 빈상태 처리).
    """
    src = "tick" if src == "tick" else "min"
    mode = "top_gainer" if mode == "top_gainer" else "latest"
    prefix = "stock_tick" if src == "tick" else "stock_min"
    days = _daily_db_dates(prefix)
    empty = {
        "date": 0, "code": "", "name": "", "change_pct": 0.0,
        "src": src, "mode": mode, "available": False,
    }
    if not days:
        return empty

    if mode == "latest":
        candidates = [days[-1]]
    else:
        candidates = list(reversed(days))[:_DEMO_SCAN_DAYS]

    best: Optional[Dict[str, Any]] = None
    for day in candidates:
        top = _top_mover(int(day), src)
        if top is None:
            continue
        if best is None or top["change_pct"] > best["change_pct"]:
            best = {"date": int(day), **top}
        # latest 모드는 첫 유효 후보(최신일)에서 확정.
        if mode == "latest" and best is not None:
            break

    if best is None:
        return empty
    return {
        "date": best["date"], "code": best["code"], "name": best["name"],
        "change_pct": best["change_pct"], "src": src, "mode": mode, "available": True,
    }


def _top_mover(date: int, src: str) -> Optional[Dict[str, Any]]:
    """그날 등락 1위 종목 1건(code·name·change_pct). 종목이 없으면 None(무예외)."""
    summary = replay_engine.stock_summary(int(date), src)
    if not summary:
        return None
    top = summary[0]  # stock_summary 는 등락 내림차순 정렬.
    name = _code_names({top["code"]}).get(top["code"], top["code"])
    return {"code": top["code"], "name": name, "change_pct": top["last_change_pct"]}


@simulation_router.get("/stocks")
def sim_stocks(date: int = 0, src: str = "tick") -> Dict[str, Any]:
    """그날 DB 종목 목록 + code_info 이름 + 마지막 행 등락/거래대금(등락 내림차순)."""
    if not (10000000 <= int(date) <= 99999999):
        return {"stocks": [], "count": 0, "date": date, "src": src}
    src = "tick" if src == "tick" else "min"
    summary = replay_engine.stock_summary(int(date), src)
    names = _code_names({s["code"] for s in summary})
    stocks = [
        {
            "code": s["code"],
            "name": names.get(s["code"], s["code"]),
            "last_change_pct": s["last_change_pct"],
            "trade_value": s["trade_value"],
            "rows": s["rows"],
        }
        for s in summary
    ]
    return {"stocks": stocks, "count": len(stocks), "date": int(date), "src": src}


def _code_names(codes: "set[str]") -> Dict[str, str]:
    """code_info.db stockinfo 에서 종목코드→종목명 매핑(읽기전용·무예외)."""
    if not codes or not _CODE_INFO_DB.is_file():
        return {}
    try:
        con = sqlite3.connect(f"file:{_CODE_INFO_DB.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    out: Dict[str, str] = {}
    try:
        rows = con.execute('SELECT "index", "종목명" FROM stockinfo').fetchall()
        wanted = codes
        for code, name in rows:
            c = str(code)
            if c in wanted:
                out[c] = str(name)
    except sqlite3.Error:
        return out
    finally:
        con.close()
    return out


# ----------------------------------------------------------------- signals (정합)
@simulation_router.get("/signals")
def sim_signals(
    date: int = 0,
    src: str = "tick",
    code: str = "",
    buy: str = "",
    sell: str = "",
) -> Dict[str, Any]:
    """조건식 매매 신호 — PR2 백테(1일·1종목)로 실제 거래를 받아 차트에 오버레이.

    엔진이 낸 per-trade CSV 의 매수/매도 시각·가격·수익률을 반환한다(리플레이와 100% 정합).
    거래 0건이면 {trades:[], note:"거래 0건"}. 잡 실패/타임아웃은 error 페이로드(무예외).
    """
    code = str(code or "").strip()
    buy = str(buy or "").strip()
    sell = str(sell or "").strip()
    src = "tick" if src == "tick" else "min"
    if not (10000000 <= int(date) <= 99999999) or not code or not buy or not sell:
        return {"trades": [], "note": "date/code/buy/sell 가 필요합니다.", "status": "error"}

    spec = BacktestJobSpec(
        buy=buy,
        sell=sell,
        start=int(date),
        end=int(date),
        timeframe=src,
        engines=1,
        timeout=_SIGNAL_JOB_TIMEOUT,
        divid_mode="한종목 로딩",
        one_code=code,
    )
    manager = get_job_manager()
    job_id = _find_or_submit(manager, spec)
    if job_id is None:
        return {"trades": [], "note": "잡 제출 실패", "status": "error"}

    record = _await_job(manager, job_id, _SIGNAL_JOB_TIMEOUT + 30)
    status = record.get("status")
    if status == "no_trades":
        return {"trades": [], "note": "거래 0건", "status": "ok", "job_id": job_id}
    if status != "success":
        return {
            "trades": [], "status": "error", "job_id": job_id,
            "note": f"백테 미완료({status}): {record.get('message', '')}".strip(),
        }
    trades = _read_trade_signals(record.get("csv_path"), code)
    return {"trades": trades, "count": len(trades), "status": "ok", "job_id": job_id}


@simulation_router.get("/signals/batch")
def sim_signals_batch(
    date: int = 0,
    src: str = "tick",
    codes: str = "",
    buy: str = "",
    sell: str = "",
) -> Dict[str, Any]:
    """One bounded request for selected-code overlays; each code retains its own result/error."""
    all_codes = list(dict.fromkeys(
        code.strip() for code in str(codes or "").split(",") if code.strip()
    ))
    selected = all_codes[:replay_engine.MAX_CODES]
    results: Dict[str, Dict[str, Any]] = {}
    for code in selected:
        results[code] = sim_signals(date=date, src=src, code=code, buy=buy, sell=sell)
    failed_codes = [
        code for code, result in results.items() if result.get("status") != "ok"
    ]
    return {
        "results": results,
        "codes": selected,
        "count": len(selected),
        "failed_codes": failed_codes,
        "truncated": len(all_codes) > replay_engine.MAX_CODES,
    }

def _spec_signature(spec: BacktestJobSpec) -> tuple:
    """동일 신호 spec 식별자 — 같은 날짜·종목·조건식·tf 면 잡을 재사용한다."""
    return (spec.buy, spec.sell, spec.start, spec.end, spec.timeframe, spec.one_code)


def _find_or_submit(manager: Any, spec: BacktestJobSpec) -> Optional[str]:
    """동일 spec 의 완료(success/no_trades) 잡이 있으면 재사용, 없으면 제출한다."""
    target = _spec_signature(spec)
    try:
        existing = manager.list_jobs().get("jobs", [])
    except Exception:  # noqa: BLE001 - 목록 실패는 신규 제출로 폴백.
        existing = []
    for job in existing:
        js = job.get("spec") or {}
        sig = (
            js.get("buy"), js.get("sell"), js.get("start"), js.get("end"),
            js.get("timeframe"), js.get("one_code"),
        )
        if sig == target and job.get("status") in ("success", "no_trades"):
            return job.get("job_id")
    result = manager.submit(spec)
    if result.get("status") == "ok":
        return result.get("job_id")
    return None


def _await_job(manager: Any, job_id: str, timeout_sec: int) -> Dict[str, Any]:
    """잡이 종료 상태에 이를 때까지 폴링한다(상한 timeout_sec). 무예외."""
    deadline = time.time() + timeout_sec
    terminal = ("success", "no_trades", "error", "timeout", "cancelled")
    while time.time() < deadline:
        record = manager.get(job_id, log_tail=0)
        if not record.get("available"):
            return {"status": "error", "message": "잡 레코드 없음"}
        if record.get("status") in terminal:
            return record
        time.sleep(0.5)
    return {"status": "timeout", "message": "신호 백테 폴링 시간 초과"}


def _read_trade_signals(csv_path: Optional[str], code: str) -> List[Dict[str, Any]]:
    """per-trade CSV → 신호 리스트(매수/매도 시각·가격·수익률). 무예외.

    1종목(one_code) 백테라 모든 행이 해당 종목 거래다. 컬럼: 매수시간/매도시간
    (YYYYMMDDHHMMSS|YYYYMMDDHHMM), 매수가/매도가, 수익률. tick 은 14자리, min 은
    12자리 시각이라 HHMMSS(min 은 초=00)로 정규화해 클라이언트가 차트 t 와 맞춘다.
    """
    if not csv_path:
        return []
    path = Path(csv_path)
    if not path.is_absolute():
        path = REPO_ROOT / csv_path
    if not path.is_file():
        return []
    trades: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            if "매수시간" not in fields or "매도시간" not in fields:
                return []
            for row in reader:
                trade = _normalize_signal_row(row)
                if trade is not None:
                    trades.append(trade)
    except Exception:  # noqa: BLE001 - CSV 없음/IO/파싱 실패는 빈 리스트로 흡수.
        return []
    return trades


def _normalize_signal_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    buy_raw = str(row.get("매수시간", "") or "").strip()
    sell_raw = str(row.get("매도시간", "") or "").strip()
    if len(buy_raw) < 8 or len(sell_raw) < 8:
        return None
    return {
        "buy_hms": _index_to_hms(buy_raw),
        "sell_hms": _index_to_hms(sell_raw),
        "buy_time": buy_raw,
        "sell_time": sell_raw,
        "buy_price": _safe_float(row.get("매수가")),
        "sell_price": _safe_float(row.get("매도가")),
        "profit_pct": _safe_float(row.get("수익률")),
    }


def _index_to_hms(raw: str) -> int:
    """시각 문자열(YYYYMMDDHHMMSS|YYYYMMDDHHMM) → HHMMSS(int, min 은 초=00)."""
    s = raw.strip()
    if len(s) >= 14:
        try:
            return int(s[8:14])
        except ValueError:
            return 0
    if len(s) >= 12:
        try:
            return int(s[8:12]) * 100
        except ValueError:
            return 0
    tail = s[-6:] if len(s) >= 6 else s
    try:
        return int(tail)
    except ValueError:
        return 0


def _safe_float(value: Any) -> float:
    try:
        f = float(value)
        return f if f == f else 0.0
    except (TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------- WS session
class _SessionRegistry:
    """동시 WS 리플레이 세션 레지스트리(프로세스 전역, 상한 _MAX_SESSIONS).

    세션 id 를 키로 활성 세션을 추적한다. ``acquire`` 는 상한 미만일 때만 새
    세션 id 를 등록하고 그 id 를 돌려주며, 초과 시 ``None`` 을 돌려준다(호출부가
    정중한 error 로 거절). ``release`` 는 해당 세션 id 만 제거하므로 한 세션의
    종료가 다른 세션에 영향을 주지 않는다. ``release()`` 를 인자 없이 호출하면
    전체를 비운다(테스트 격리용).
    """

    def __init__(self, limit: int = _MAX_SESSIONS) -> None:
        self._lock = threading.Lock()
        self._active: set[str] = set()
        self._limit = limit
        self._counter = itertools.count(1)

    def acquire(self) -> Optional[str]:
        """상한 미만이면 새 세션 id 를 등록·반환, 초과면 ``None``."""
        with self._lock:
            if len(self._active) >= self._limit:
                return None
            session_id = f"sim-{next(self._counter)}"
            self._active.add(session_id)
            return session_id

    def release(self, session_id: Optional[str] = None) -> None:
        """``session_id`` 세션만 제거(없으면 무시). 인자 없으면 전체 초기화."""
        with self._lock:
            if session_id is None:
                self._active.clear()
            else:
                self._active.discard(session_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)


_GATE = _SessionRegistry()


class _ReplayWebSocket(Protocol):
    async def send_json(self, data: Dict[str, Any], /) -> None: ...


class SimReplaySession:
    """WS 리플레이 1세션 상태머신 — start/pause/resume/speed/seek/stop.

    asyncio sleep 기반 배속 스케줄로 frame 배치를 push 한다. ReplayData 는
    스레드 풀에서 동기 로드(시세 DB I/O)하고, 송신 루프는 이벤트 루프에서 돈다.
    """

    def __init__(self, websocket: _ReplayWebSocket) -> None:
        self.ws = websocket
        self.data: Optional[replay_engine.ReplayData] = None
        self.cursor = 0
        self.speed = 1
        self.paused = False
        self.running = False
        # 고배속 묶음 전송 기준 인덱스(이 인덱스부터 누적 전송 개수를 센다).
        self._batch_anchor = 0
        # seek 직후 과거 봉 스냅샷 재전송 예약(스트림 루프가 다음 경계에서 소비).
        self._history_pending = False

    async def handle_start(self, msg: ReplayStartControl) -> None:
        """start — 데이터 로드 후 meta 송신, 스트림 루프 시작."""
        date = msg.date
        src = msg.src
        codes = msg.codes
        agg_sec = msg.agg_sec
        self.speed = msg.speed

        # 시세 DB I/O 는 스레드로(이벤트 루프 차단 방지).
        try:
            self.data = await asyncio.to_thread(
                replay_engine.load_replay, date, src, codes, agg_sec=agg_sec
            )
        except replay_engine.ReplayTimelineError as exc:
            await self._send({
                "type": "error",
                "code": "invalid_replay_timeline",
                "message": str(exc),
            })
            return
        self.cursor = 0
        self._batch_anchor = 0
        self.paused = False
        await self._send({
            "type": "meta",
            "codes": self.data.codes,
            "bars_total": self.data.bars_total,
            "session_range": list(self.data.session_range),
            "src": src,
            "date": date,
            "agg_sec": agg_sec,
            "total_elapsed_seconds": (
                self.data.elapsed_seconds_at(self.data.bars_total - 1)
                if self.data.bars_total else 0
            ),
            "replay_metadata": self.data.metadata,
        })
        if self.data.bars_total == 0:
            await self._send({"type": "done"})
            return
        self.running = True
        await self._stream_loop()

    async def _stream_loop(self) -> None:
        """wall-clock 페이싱으로 frame 을 push 한다. bar 간 실제 시간차/speed 만큼 대기.

        설계: 각 frame 을 보내기 전, 직전 frame 과의 실제 시각차(초)를 speed 로 나눈 만큼
        기다린다 → speed=1x 면 1초봉은 1초마다·1분봉은 1분마다 도착(시간이 흐르는 체감).
        고배속에서 프레임당 대기가 _MIN_FRAME_SLEEP_SEC 미만이면, 대기를 누적하다
        _FRAME_FLUSH_SLEEP_SEC 에 도달했을 때 그 사이 frame 들을 한 번에 flush 후 한 번
        sleep 한다(묶음 내 시간 비례 유지·이벤트 루프 과부하 방지). pause/speed/seek 는
        매 frame 경계에서 즉시 반영된다(speed 변경 시 다음 gap 부터 새 배속 적용).
        """
        assert self.data is not None
        pending_sleep = 0.0           # 아직 자지 않은 누적 대기(초).
        prev_t: Optional[int] = None  # 직전 전송 frame 시각(HHMMSS) — gap 산출용.
        while self.running and self.cursor < self.data.bars_total:
            # seek 직후엔 0..cursor 스냅샷부터 — 클라이언트가 시킹 이후 frame 만 쌓아
            #   차트에 과거 봉이 사라지는 공백(Phase6.1 신고)을 막는다. pause 중에도 전송.
            if self._history_pending:
                self._history_pending = False
                await self._send_history()
                pending_sleep = 0.0
                prev_t = None
            if self.paused:
                # 일시정지 — 누적 대기는 버리고(재개 시 현재 위치부터) idle.
                pending_sleep = 0.0
                prev_t = None
                await asyncio.sleep(0.05)
                continue

            i = self.cursor
            frame = self.data.frames[i]
            t = int(frame["t"])
            # 이 frame 전송 전 대기 = (직전 frame 과의 실제 초) / 현재 speed.
            if prev_t is not None:
                pending_sleep += _bar_gap_seconds(prev_t, t) / _clamp_speed(self.speed)

            # 누적 대기가 한 번 잘 만큼 모였으면(또는 절대 배치 상한 도달) sleep 한 뒤 전송.
            sent_since_sleep = i - self._batch_anchor
            if pending_sleep >= _FRAME_FLUSH_SLEEP_SEC or sent_since_sleep >= _MAX_BATCH:
                if pending_sleep > 0:
                    interrupted = await self._paced_sleep(pending_sleep)
                    pending_sleep = 0.0
                    # sleep 중 pause/stop/seek 가 들어왔으면 루프 상단에서 재평가.
                    if interrupted:
                        prev_t = None
                        continue
                self._batch_anchor = i

            await self._send({
                "type": "bars",
                "t": t,
                "index": i,
                "frame_count": i + 1,
                "elapsed_seconds": self.data.elapsed_seconds_at(i),
                "total_elapsed_seconds": self.data.elapsed_seconds_at(self.data.bars_total - 1),
                "items": frame["items"],
            })
            prev_t = t
            self.cursor = i + 1

        # 끝까지 seek 한 경우(루프 미진입) 스냅샷만이라도 전송 — 차트가 비지 않게.
        if self.running and self._history_pending:
            self._history_pending = False
            await self._send_history()
        # 루프 종료 시 남은 누적 대기를 마저 소진(끝부분 시간 비례 유지)하고 done.
        if self.running and self.data and self.cursor >= self.data.bars_total:
            if pending_sleep > 0 and not self.paused:
                await asyncio.sleep(min(pending_sleep, _FRAME_FLUSH_SLEEP_SEC))
            await self._send({"type": "done"})
            self.running = False

    async def _paced_sleep(self, seconds: float) -> bool:
        """page 대기를 작은 청크로 나눠 자며, 도중 상태 변화(stop/pause/seek)면 조기 반환한다.

        반환 True = 도중 중단(상위 루프가 상태를 재평가해야 함). False = 정상 완료.
        한 청크 상한(_PACED_SLEEP_CHUNK_SEC)으로 60초 대기도 ~수십 ms 안에 stop/pause 에
        반응한다(고정 0.5s 배치가 아니라 정밀 페이싱이라도 제어 반응성 유지).
        """
        remaining = float(seconds)
        start_cursor = self.cursor
        while remaining > 0:
            if not self.running or self.paused or self.cursor != start_cursor:
                return True
            chunk = remaining if remaining < _PACED_SLEEP_CHUNK_SEC else _PACED_SLEEP_CHUNK_SEC
            await asyncio.sleep(chunk)
            remaining -= chunk
        # 깬 직후에도 상태 변화 점검(seek/stop 이 sleep 막바지에 들어온 경우).
        if not self.running or self.paused or self.cursor != start_cursor:
            return True
        return False

    def handle_pause(self) -> None:
        self.paused = True

    def handle_resume(self) -> None:
        self.paused = False

    def handle_speed(self, value: Any) -> None:
        self.speed = _clamp_speed(value)

    def handle_seek(self, t: int) -> None:
        """seek — HHMMSS 시각으로 커서를 점프한다(이진 탐색). 과거 봉 스냅샷 재전송 예약."""
        if self.data is None:
            return
        self.cursor = self.data.seek_index(t)
        self._batch_anchor = self.cursor  # seek 후 묶음 기준 재설정.
        self._history_pending = True

    def handle_seek_index(self, index: int) -> bool:
        if self.data is None or type(index) is not int or index < 0 or index >= self.data.bars_total:
            return False
        self.cursor = index + 1
        self._batch_anchor = self.cursor
        self._history_pending = True
        return True

    async def _send_history(self) -> None:
        """0..cursor 구간 봉을 코드별 스냅샷으로 전송한다(코드당 최근 _HISTORY_MAX_BARS 개).

        전진 seek 는 건너뛴 구간이 스트림되지 않아 차트에 공백이 생기고, 후진 seek 는
        이미 받은 봉이 중복 append 된다 — 둘 다 스냅샷 전체 교체로 해결한다(클라이언트는
        "history" 수신 시 코드별 시계열을 통째로 대체). bar dict 는 frame item 과 동일
        스키마에 t 만 더한다(증분 "bars" 와 같은 필드 매핑을 재사용하게).
        """
        if self.data is None:
            return
        upto = min(self.cursor, self.data.bars_total)
        by_code: Dict[str, List[Dict[str, Any]]] = {}
        for i in range(upto):
            frame = self.data.frames[i]
            t = int(frame["t"])
            for it in frame["items"]:
                by_code.setdefault(str(it.get("code", "")), []).append({**it, "t": t})
        for code, arr in by_code.items():
            if len(arr) > _HISTORY_MAX_BARS:
                by_code[code] = arr[-_HISTORY_MAX_BARS:]
        actual_index = upto - 1 if upto > 0 else None
        last_t = int(self.data.frames[actual_index]["t"]) if actual_index is not None else None
        await self._send({
            "type": "history",
            "index": actual_index,
            "frame_count": upto,
            "t": last_t,
            "elapsed_seconds": (
                self.data.elapsed_seconds_at(actual_index) if actual_index is not None else 0
            ),
            "items_by_code": by_code,
        })

    def handle_stop(self) -> None:
        self.running = False

    async def _send(self, payload: Dict[str, Any]) -> None:
        try:
            await self.ws.send_json(payload)
        except Exception:  # noqa: BLE001 - 송신 실패(연결 끊김)는 루프 종료로 흡수.
            self.running = False


def _clamp_speed(value: Any) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(_MAX_SPEED, v))


@simulation_router.websocket("/ws")
async def simulation_ws(websocket: WebSocket) -> None:
    """리플레이 WS 세션. 동시 _MAX_SESSIONS 개까지 — 초과 시 정중히 거절 후 종료.

    각 연결은 독립 세션 id·SimReplaySession·스트림 태스크를 가지며, 연결 종료·stop
    시 자기 세션만 정리한다(다른 세션 무영향). 프로토콜(클라→서버):
    start/pause/resume/speed/seek/stop. 서버→클라: meta → bars(배치) → done | error.
    제어 메시지는 스트림 루프와 동시 처리되도록 별도 수신 태스크로 받는다.
    """
    security = websocket.app.state.dashboard_security
    failure = security.authorize_websocket(websocket, Capability.REPLAY_CONTROL)
    if failure is not None:
        await close_websocket_failure(websocket, failure)
        return
    await websocket.accept()
    session_id = _GATE.acquire()
    if session_id is None:
        await websocket.send_json({
            "type": "error",
            "message": f"동시 리플레이 세션 상한({_MAX_SESSIONS}개)에 도달했습니다.",
        })
        await websocket.close()
        return

    session = SimReplaySession(websocket)
    stream_task: asyncio.Task[None] | None = None
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw) > MAX_WEBSOCKET_MESSAGE_CHARS:
                await websocket.send_json({
                    "type": "error",
                    "code": "payload_too_large",
                    "message": "replay control message exceeds the server limit",
                })
                continue
            try:
                msg = _REPLAY_CONTROL_ADAPTER.validate_json(raw)
            except ValidationError:
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_message",
                    "message": "invalid replay control message",
                })
                continue
            match msg:
                case ReplayStartControl():
                    session.handle_stop()
                    if stream_task is not None and not stream_task.done():
                        await asyncio.sleep(0)
                    stream_task = asyncio.create_task(session.handle_start(msg))
                case ReplayPauseControl():
                    session.handle_pause()
                case ReplayResumeControl():
                    session.handle_resume()
                case ReplaySpeedControl(value=value):
                    session.handle_speed(value)
                case ReplaySeekControl(t=t):
                    session.handle_seek(t)
                case ReplaySeekIndexControl(index=index):
                    if not session.handle_seek_index(index):
                        await websocket.send_json({
                            "type": "error",
                            "code": "seek_index_out_of_bounds",
                            "message": "seek_index requires loaded replay data and a valid frame index",
                        })
                    elif stream_task is None or stream_task.done():
                        session.running = True
                        stream_task = asyncio.create_task(session._stream_loop())
                case ReplayStopControl():
                    session.handle_stop()
                    await websocket.send_json({"type": "done"})
                case unreachable:
                    assert_never(unreachable)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - 어떤 예외도 세션 정리 후 흡수(대시보드 보호).
        pass
    finally:
        session.handle_stop()
        if stream_task is not None and not stream_task.done():
            stream_task.cancel()
        _GATE.release(session_id)
