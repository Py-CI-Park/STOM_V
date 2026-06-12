"""Chart simulation API — 일일 tick/min DB 리플레이 + 조건식 매매 오버레이 (PR3).

웹 대시보드 "차트 시뮬레이션" 탭의 백엔드. 일일 시세 DB(``stock_tick_YYYYMMDD.db`` /
``stock_min_YYYYMMDD.db``)를 시간순으로 리플레이하고, 조건식 매수/매도 신호를 차트에
오버레이한다. replay_engine.py 가 데이터 계층(로드·집계·병합·seek)을 담당한다.

라우트:
  - GET  /sim/days?src=tick|min                 → 일일 DB 날짜 인벤토리.
  - GET  /sim/stocks?date&src                    → 그날 종목(코드·이름·등락·거래대금) 등락순.
  - GET  /sim/signals?date&src&code&buy&sell      → 조건식 매매 신호(아래 정합 설계).
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
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ai_strategy_loop.dashboard import replay_engine
from ai_strategy_loop.dashboard.backtest_jobs import (
    BacktestJobSpec,
    get_job_manager,
)

# 패키지 루트(.../ai_strategy_loop) 기준 경로.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_DATABASE_DIR = REPO_ROOT / "_database"
_CODE_INFO_DB = _DATABASE_DIR / "code_info.db"

# 배속 상한(스케줄 sleep 하한 보호). 한 frame 당 기본 base_interval 초.
_BASE_INTERVAL_SEC = 0.5
_MIN_SLEEP_SEC = 0.005
_MAX_SPEED = 240
# WS 한 번에 보낼 frame 배치 상한(배속 높을 때 묶음 전송).
_MAX_BATCH = 64
# 동시 WS 리플레이 세션 상한(프로세스 전역). 초과 연결은 정중히 거절.
_MAX_SESSIONS = 4
# /sim/signals 잡 폴링 상한(초). 1일·1종목 백테는 통상 1분 내.
_SIGNAL_JOB_TIMEOUT = 180


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


class SimReplaySession:
    """WS 리플레이 1세션 상태머신 — start/pause/resume/speed/seek/stop.

    asyncio sleep 기반 배속 스케줄로 frame 배치를 push 한다. ReplayData 는
    스레드 풀에서 동기 로드(시세 DB I/O)하고, 송신 루프는 이벤트 루프에서 돈다.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self.ws = websocket
        self.data: Optional[replay_engine.ReplayData] = None
        self.cursor = 0
        self.speed = 1
        self.paused = False
        self.running = False

    async def handle_start(self, msg: Dict[str, Any]) -> None:
        """start — 데이터 로드 후 meta 송신, 스트림 루프 시작."""
        try:
            date = int(msg.get("date", 0) or 0)
        except (TypeError, ValueError):
            date = 0
        src = "tick" if msg.get("src") == "tick" else "min"
        codes = [str(c) for c in (msg.get("codes") or [])][:4]
        try:
            agg_sec = int(msg.get("agg_sec", replay_engine.DEFAULT_AGG_SEC) or replay_engine.DEFAULT_AGG_SEC)
        except (TypeError, ValueError):
            agg_sec = replay_engine.DEFAULT_AGG_SEC
        self.speed = _clamp_speed(msg.get("speed", 1))

        if not (10000000 <= date <= 99999999) or not codes:
            await self._send({"type": "error", "message": "date/codes 가 필요합니다."})
            return

        # 시세 DB I/O 는 스레드로(이벤트 루프 차단 방지).
        self.data = await asyncio.to_thread(
            replay_engine.load_replay, date, src, codes, agg_sec=agg_sec
        )
        self.cursor = 0
        self.paused = False
        await self._send({
            "type": "meta",
            "codes": self.data.codes,
            "bars_total": self.data.bars_total,
            "session_range": list(self.data.session_range),
            "src": src,
            "date": date,
            "agg_sec": agg_sec,
        })
        if self.data.bars_total == 0:
            await self._send({"type": "done"})
            return
        self.running = True
        await self._stream_loop()

    async def _stream_loop(self) -> None:
        """배속 스케줄로 frame 배치를 push 한다. paused 면 idle, 끝나면 done."""
        assert self.data is not None
        while self.running and self.cursor < self.data.bars_total:
            if self.paused:
                await asyncio.sleep(0.05)
                continue
            batch = min(_MAX_BATCH, max(1, self.speed))
            end = min(self.cursor + batch, self.data.bars_total)
            for i in range(self.cursor, end):
                frame = self.data.frames[i]
                await self._send({
                    "type": "bars",
                    "t": frame["t"],
                    "index": i,
                    "items": frame["items"],
                })
            self.cursor = end
            sleep_s = max(_MIN_SLEEP_SEC, _BASE_INTERVAL_SEC * batch / max(1, self.speed))
            await asyncio.sleep(sleep_s)
        if self.running and self.data and self.cursor >= self.data.bars_total:
            await self._send({"type": "done"})
            self.running = False

    def handle_pause(self) -> None:
        self.paused = True

    def handle_resume(self) -> None:
        self.paused = False

    def handle_speed(self, value: Any) -> None:
        self.speed = _clamp_speed(value)

    def handle_seek(self, t: Any) -> None:
        """seek — HHMMSS 시각으로 커서를 점프한다(이진 탐색)."""
        if self.data is None:
            return
        try:
            hms = int(t)
        except (TypeError, ValueError):
            return
        self.cursor = self.data.seek_index(hms)

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
    stream_task: Optional[asyncio.Task] = None
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = _parse_json(raw)
            except ValueError:
                await websocket.send_json({"type": "error", "message": "invalid JSON"})
                continue
            action = (msg or {}).get("action")
            if action == "start":
                # 진행 중 스트림이 있으면 멈추고 새로 시작.
                session.handle_stop()
                if stream_task is not None and not stream_task.done():
                    await asyncio.sleep(0)
                stream_task = asyncio.create_task(session.handle_start(msg))
            elif action == "pause":
                session.handle_pause()
            elif action == "resume":
                session.handle_resume()
            elif action == "speed":
                session.handle_speed(msg.get("value"))
            elif action == "seek":
                session.handle_seek(msg.get("t"))
            elif action == "stop":
                session.handle_stop()
                await websocket.send_json({"type": "done"})
            else:
                await websocket.send_json({
                    "type": "error", "message": f"unknown action: {action!r}",
                })
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - 어떤 예외도 세션 정리 후 흡수(대시보드 보호).
        pass
    finally:
        session.handle_stop()
        if stream_task is not None and not stream_task.done():
            stream_task.cancel()
        _GATE.release(session_id)


def _parse_json(raw: str) -> Dict[str, Any]:
    import json

    text = (raw or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError(str(exc))
    return obj if isinstance(obj, dict) else {}
