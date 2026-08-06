"""QSP10 P5 실행기 — 지도 후보를 엔진으로 검증하고 **전이율**을 기록한다.

지도(탐색)와 엔진(심판)의 격차는 가정하지 않고 측정한다. 자본 경로 의존성(동시보유·
자본 한도)이 여기서 처음 반영되므로, 군집도가 높은 후보일수록 격차가 커질 것으로 본다.

사용(서버 8771 필요):
    python -m ai_strategy_loop.labeling.run_p5 --report design_v2
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import time
import urllib.parse
import urllib.request

from ai_strategy_loop.labeling.assembler import render_buy_expression, render_sell_expression
from ai_strategy_loop.labeling.lanes import LANES

_BASE = "http://127.0.0.1:8771"
_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


class Client:
    """세션 클라이언트 — 쿠키는 HTML 진입점(307 리다이렉트)에서만 발급된다."""

    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self._opener.open(f"{_BASE}/ui/v4", timeout=30).read(64)

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{_BASE}{path}", data=data, method=method)
        request.add_header("Origin", _BASE)      # mutation 은 same-origin 필수
        if data:
            request.add_header("Content-Type", "application/json")
        with self._opener.open(request, timeout=180) as response:
            return json.loads(response.read().decode())


def wait_for(client: Client, job_id: str, timeout: int = 3600) -> str:
    started = time.time()
    while True:
        time.sleep(20)
        jobs = client.call("GET", "/bt/jobs").get("jobs", [])
        row = next((j for j in jobs if j.get("job_id") == job_id), None)
        status = (row or {}).get("status", "?")
        if status in ("done", "success", "error", "failed", "canceled", "no_trades"):
            return status
        if time.time() - started > timeout:
            return "timeout"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="design_v2")
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--engines", type=int, default=16)
    args = parser.parse_args()

    lane = LANES[args.lane]
    path = os.path.join(_LABEL_ROOT, args.report, "_p3_report.json")
    report = json.load(open(path, encoding="utf-8"))
    # 게이트를 통과한 규칙만 엔진에 올린다 — 일평균이 음수인 조합을 실측하는 것은
    #   엔진 시간 낭비이고, 통과 표시가 없는 후보를 공식 런에 올리면 규율 위반이다.
    passed = [r for r in report["results"]
              if r["final"]["expectancy_pct"] > 0 and r["day_p_value"] < 0.05]
    if not passed:
        raise SystemExit("게이트를 통과한 규칙이 없습니다 — P5 엔진 검증 대상이 없습니다.")
    ranked = sorted(passed, key=lambda r: r["final"]["expectancy_pct"], reverse=True)
    picks = ranked[:args.top]

    client = Client()
    outcomes = []
    for index, pick in enumerate(picks, start=1):
        tp_pct = float(pick["rule"].split("/")[0].removeprefix("TP"))
        sl_pct = float(pick["rule"].split("/")[1].removeprefix("SL"))
        buy_name = f"QSP10_P5_{args.lane}_C{index}"
        sell_name = f"QSP10_P5_{args.lane}_S{index}"
        buy_code = render_buy_expression(
            name=buy_name, time_start=lane.entry_start, time_end=lane.entry_end,
            clauses=pick["clauses"])
        sell_code = render_sell_expression(
            name=sell_name, tp_pct=tp_pct, sl_pct=sl_pct, horizon=lane.barrier_horizon,
            forced_exit=lane.forced_exit)
        for kind, name, code in (("buy", buy_name, buy_code), ("sell", sell_name, sell_code)):
            saved = client.call("POST", "/bt/strategy",
                                {"kind": kind, "name": name, "code": code, "overwrite": True})
            print(f"{kind}: {name} {saved.get('status')}", flush=True)

        started = client.call("POST", "/bt/run", {
            "buy": buy_name, "sell": sell_name,
            "start": lane.design[0], "end": lane.design[1],
            "start_time": lane.entry_start if lane.name == "min" else 90000,
            "end_time": lane.forced_exit,
            "timeframe": lane.name, "engines": args.engines, "timeout": 3600,
        })
        job_id = started.get("job_id")
        print(f"run: {buy_name} → {job_id} {started.get('status')}", flush=True)
        if not job_id:
            outcomes.append({"name": buy_name, "error": started})
            continue
        status = wait_for(client, job_id)
        result = client.call("GET", f"/bt/result?job_id={urllib.parse.quote(job_id)}")
        metrics = result.get("metrics") or {}
        predicted = pick["final"]
        transfer = None
        if metrics.get("avg_profit_pct") is not None and predicted["expectancy_pct"]:
            transfer = float(metrics["avg_profit_pct"]) / predicted["expectancy_pct"]
        outcomes.append({
            "name": buy_name, "rule": pick["rule"], "job_id": job_id, "status": status,
            "predicted": predicted, "cluster": pick.get("cluster"),
            "engine": {k: metrics.get(k) for k in
                       ("trade_count", "win_rate", "avg_profit_pct", "total_profit_krw",
                        "cagr", "mdd_pct", "tpi")},
            "transfer_ratio": transfer,
        })
        print(f"done: {buy_name} status={status} trades={metrics.get('trade_count')} "
              f"건당={metrics.get('avg_profit_pct')} 전이율={transfer}", flush=True)

    out = os.path.join(_LABEL_ROOT, args.report, "_p5_report.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump({"lane": lane.name, "outcomes": outcomes}, handle,
                  ensure_ascii=False, indent=2, default=float)
    print("saved:", os.path.abspath(out))


if __name__ == "__main__":
    main()
