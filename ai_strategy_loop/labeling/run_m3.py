"""M-3 실행기 — 후보 조립 → 대시보드 등록 → 엔진 16 설계 구간 실측 → 수집.

판정은 하지 않는다(관측 수집만). 설계 구간(20240304~20250822)만 돌린다 —
홀드아웃 노출은 M-5 검증 사다리에서만 한다.

사용 (서버가 8771 에 떠 있어야 한다):
    python -m ai_strategy_loop.labeling.run_m3
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

import numpy as np

from ai_strategy_loop.labeling.assembler import render_buy_expression, snap_threshold
from ai_strategy_loop.labeling.terrain import load_usable

_BASE = "http://127.0.0.1:8771"
_OUT = os.path.join(os.path.dirname(__file__), "..", "state", "labels", "design",
                    "_m3_report.json")
DESIGN_START, DESIGN_END = 20240304, 20250822

SELL_NAME = "QSP9_M3_tick_S_hold300"
#: 스크리닝 매도 — 라벨 fr_300 의 거울(고정 300초 + 전체청산). M-4 에서 진짜 매도로 교체.
SELL_CODE = """매도 = False
if 보유시간 >= 300:
    매도 = True
elif 시분초 >= 92800:
    매도 = True
if 매도:
    self.Sell()
"""


class _Client:
    """세션 클라이언트 — 함정 2개를 실측으로 배웠다:
    ① `/ui/v4` 는 307 리다이렉트라 최종 응답 헤더만 보면 쿠키를 놓친다 → cookiejar 필수.
    ② mutation 은 정확한 same-origin Origin 헤더가 필수(security.py)."""

    def __init__(self) -> None:
        import http.cookiejar
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self._opener.open(f"{_BASE}/ui/v4", timeout=30).read(64)   # 쿠키는 HTML 진입점에서만 발급

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{_BASE}{path}", data=data, method=method)
        request.add_header("Origin", _BASE)
        if data:
            request.add_header("Content-Type", "application/json")
        with self._opener.open(request, timeout=120) as response:
            return json.loads(response.read().decode())


def build_candidates() -> list[dict]:
    frame = load_usable(["당일거래대금", "거래대금증감", "등락율", "시가등락율", "초당순매수금액"])

    def snap(variable: str, raw: float) -> float:
        return snap_threshold(frame, variable, raw=raw)

    q_amt_lo = snap("당일거래대금", 736.5)
    q_amt_mid = snap("당일거래대금", 1448.5)
    q_chg = snap("거래대금증감", -6.887e9)
    q_rate = snap("등락율", -0.56)
    q_gap = snap("시가등락율", -0.97)
    q_net80 = float(np.quantile(frame["초당순매수금액"].dropna(), 0.8))

    quiet = [{"변수": "당일거래대금", "연산자": "<=", "임계": q_amt_lo},
             {"변수": "거래대금증감", "연산자": ">", "임계": q_chg}]
    rebound = [{"변수": "당일거래대금", "연산자": ">", "임계": q_amt_mid},
               {"변수": "등락율", "연산자": "<=", "임계": q_rate},
               {"변수": "시가등락율", "연산자": "<=", "임계": q_gap}]
    demand = {"변수": "초당순매수금액", "연산자": ">", "임계": 0.0}
    spread_guard = {"변수": "spread_pct", "연산자": "<=", "임계": 1.0}

    plans = [
        ("QSP9_M3_tick_C1_조용한드리프트", quiet),
        ("QSP9_M3_tick_C2_드리프트수요", [*quiet, demand, spread_guard]),
        ("QSP9_M3_tick_C3_낙폭반등", rebound),
        ("QSP9_M3_tick_C4_반등수요", [*rebound, demand]),
        ("QSP9_M3_tick_C5_수요압력", [
            {"변수": "초당순매수금액", "연산자": ">", "임계": round(q_net80, 6)},
            {"변수": "당일거래대금", "연산자": "<=", "임계": q_amt_mid}]),
    ]
    return [{"name": name,
             "clauses": clauses,
             "code": render_buy_expression(name=name, time_start=90000, time_end=92000,
                                           clauses=clauses)}
            for name, clauses in plans]


def main() -> None:
    client = _Client()
    candidates = build_candidates()

    saved = client.call("POST", "/bt/strategy",
                        {"kind": "sell", "name": SELL_NAME, "code": SELL_CODE, "overwrite": True})
    print("sell:", saved.get("status"), flush=True)
    for candidate in candidates:
        result = client.call("POST", "/bt/strategy",
                             {"kind": "buy", "name": candidate["name"],
                              "code": candidate["code"], "overwrite": True})
        print("buy:", candidate["name"], result.get("status"), flush=True)

    results = []
    for candidate in candidates:
        started = client.call("POST", "/bt/run", {
            "buy": candidate["name"], "sell": SELL_NAME,
            "start": DESIGN_START, "end": DESIGN_END,
            "start_time": 90000, "end_time": 92800,
            "timeframe": "tick", "engines": 16, "timeout": 3600,
        })
        job_id = started.get("job_id")
        print("run:", candidate["name"], "→", job_id, started.get("status"), flush=True)
        if not job_id:
            results.append({"name": candidate["name"], "error": started})
            continue
        t0 = time.time()
        while True:
            time.sleep(20)
            jobs = client.call("GET", "/bt/jobs").get("jobs", [])
            row = next((j for j in jobs if j.get("job_id") == job_id), None)
            status = (row or {}).get("status", "?")
            # no_trades 도 종결 상태다(2026-08-05 실측 — C1 0건).
            if status in ("done", "success", "error", "failed", "canceled", "no_trades"):
                break
            if time.time() - t0 > 3600:
                status = "timeout"
                break
        # job_id 에 한글이 들어가므로 URL 인코딩 필수(ascii 강제 크래시 실측).
        quoted = urllib.parse.quote(str(job_id))
        outcome = client.call("GET", f"/bt/result?job_id={quoted}")
        metrics = outcome.get("metrics") or {}
        results.append({"name": candidate["name"], "job_id": job_id, "status": status,
                        "metrics": metrics})
        print(f"done: {candidate['name']} status={status} "
              f"trades={metrics.get('trade_count')} pnl={metrics.get('total_profit')}",
              flush=True)

    report = {"sell": SELL_NAME, "design": [DESIGN_START, DESIGN_END],
              "candidates": [{k: c[k] for k in ("name", "clauses")} for c in candidates],
              "results": results}
    with open(_OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("saved:", os.path.abspath(_OUT), flush=True)


if __name__ == "__main__":
    main()
