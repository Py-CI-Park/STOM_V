from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

try:  # Pillow is optional at import time; screenshots are required at runtime.
    from PIL import Image, ImageDraw, ImageStat
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]

REPO = Path(__file__).resolve().parents[1]

BACKTEST_REQUIRED_TEXT = (
    "LIVE READ-ONLY MODE",
    "Backtest API Contract Matrix",
    "실행 파라미터",
    "최적화 JSON",
    "WFO 설정",
    "스윕 / self.vars 빌더",
    "진행 중인 작업",
    "조건식 편집",
    "검증",
    "저장",
    "삭제",
    "결과 분석",
    "A/B 비교",
    "멀티 잡 에쿼티 오버레이",
    "포트폴리오 조합",
    "독립 HTML 보고서",
    "/bt/* mutating endpoints are not auto-invoked",
    "No Live Order",
    "Human Approval Gate",
)

REPLAY_REQUIRED_TEXT = (
    "LIVE READ-ONLY REPLAY MODE",
    "Replay API/WS Contract Matrix",
    "데이터 소스",
    "사용 가능 일자",
    "종목 리스트",
    "선택 종목",
    "전략",
    "즉시 리플레이",
    "재생 컨트롤",
    "실시간 리플레이 차트",
    "/sim/ws 수동 게이트",
    "start",
    "pause",
    "resume",
    "speed",
    "seek",
    "stop",
    "meta",
    "bars",
    "history",
    "done",
    "error",
    "전략 신호 로그",
    "No Account Trading",
    "Append-Only Audit",
)

BACKTEST_REQUIRED_ENDPOINTS = {
    "/bt/health",
    "/bt/strategies?kind=buy",
    "/bt/strategies?kind=sell",
    "/bt/strategy?kind=&name=",
    "/bt/strategy/validate",
    "/bt/strategy",
    "/bt/strategy/delete",
    "/bt/extract_vars",
    "/bt/legacy/self_vars?kind=&name=",
    "/bt/backfinder/preflight?kind=&name=",
    "/bt/data_range",
    "/bt/run",
    "/bt/jobs",
    "/bt/job?job_id=",
    "/bt/job/cancel",
    "/bt/job/meta",
    "/bt/ws_job?job_id=",
    "/bt/result?job_id=__demo__",
    "/bt/evo_gens?run_id=",
    "/bt/analysis/montecarlo?job_id=__demo__&n=2000",
    "/bt/compare?job_a=&job_b=",
    "/bt/overlay?job_ids=",
    "/bt/portfolio",
    "/bt/report?job_id=",
}

REPLAY_REQUIRED_ENDPOINTS = {
    "/sim/health",
    "/sim/days?src=min|tick",
    "/sim/demo?src=min&mode=latest",
    "/sim/stocks?date=&src=",
    "/bt/strategies?kind=buy",
    "/bt/strategies?kind=sell",
    "/sim/signals?date=&src=&code=&buy=&sell=",
    "/sim/ws",
    "start",
    "pause",
    "resume",
    "speed",
    "seek",
    "stop",
    "meta",
    "bars",
    "history",
    "done",
    "error",
}

SAFE_BACKTEST_GETS = (
    "/bt/health",
    "/bt/strategies?kind=buy",
    "/bt/strategies?kind=sell",
    "/bt/jobs",
    "/bt/data_range",
    "/bt/result?job_id=__demo__",
    "/bt/analysis/montecarlo?job_id=__demo__&n=2000",
)

SAFE_REPLAY_GETS = (
    "/sim/health",
    "/sim/days?src=min",
    "/sim/demo?src=min&mode=latest",
    "/bt/strategies?kind=buy",
    "/bt/strategies?kind=sell",
)

FORBIDDEN_AUTO_PATHS = (
    "/bt/run",
    "/bt/strategy/validate",
    "/bt/strategy/delete",
    "/bt/extract_vars",
    "/bt/job/cancel",
    "/bt/job/meta",
    "/bt/portfolio",
    "/bt/ws_job",
    "/sim/ws",
    "/order",
    "/orders",
    "/broker/login",
    "/account/trade",
    "/live_order",
)
ALLOWED_WS_PATHS = {"/ws"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify V3 backtest and chart replay runtime depth without unsafe auto-mutations.")
    parser.add_argument("--base-url", required=True, help="Running dashboard base URL, e.g. http://127.0.0.1:8776")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def simplified_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


def text_score(required: tuple[str, ...], text: str) -> dict[str, Any]:
    missing = [needle for needle in required if needle not in text]
    return {"score": round((1.0 - len(missing) / max(1, len(required))) * 100.0, 2), "missing": missing}


def screenshot_metrics(path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"available": False, "status": "FAIL", "reason": "Pillow unavailable"}
    with Image.open(path) as raw:
        img = raw.convert("RGB")
        stat = ImageStat.Stat(img.resize((160, 90)).convert("L"))
        non_uniform = img.size[0] >= 1000 and img.size[1] >= 700 and float(stat.stddev[0]) >= 2.0
        return {"available": True, "status": "PASS" if non_uniform else "FAIL", "size": list(img.size), "lumaStddev": round(float(stat.stddev[0]), 2), "nonUniform": non_uniform}


def api_get(base_url: str, path: str, timeout: float = 8.0) -> dict[str, Any]:
    url = norm_url(base_url, path)
    started = utc_now()
    try:
        req = Request(url, method="GET", headers={"Accept": "application/json,text/html;q=0.8,*/*;q=0.1"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(240000)
            body = raw.decode("utf-8", errors="replace")
            content_type = resp.headers.get("content-type", "")
            parsed: Any = None
            if "json" in content_type:
                try:
                    parsed = json.loads(body)
                except Exception:
                    parsed = None
            return {"path": path, "url": url, "method": "GET", "statusCode": resp.status, "contentType": content_type, "bodyBytes": len(raw), "startedAt": started, "endedAt": utc_now(), "jsonKeys": sorted(parsed.keys()) if isinstance(parsed, dict) else [], "jsonStatus": parsed.get("status") if isinstance(parsed, dict) else None, "summary": summarize_payload(parsed if parsed is not None else body)}
    except HTTPError as exc:
        return {"path": path, "url": url, "method": "GET", "statusCode": exc.code, "error": str(exc), "startedAt": started, "endedAt": utc_now()}
    except URLError as exc:
        return {"path": path, "url": url, "method": "GET", "statusCode": None, "error": str(exc), "startedAt": started, "endedAt": utc_now()}
    except Exception as exc:  # noqa: BLE001
        return {"path": path, "url": url, "method": "GET", "statusCode": None, "error": str(exc), "startedAt": started, "endedAt": utc_now()}


def summarize_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        parts = []
        for key, value in payload.items():
            if isinstance(value, list):
                parts.append(f"{key}[{len(value)}]")
            elif isinstance(value, dict):
                parts.append(f"{key}{{{len(value)}}}")
            else:
                parts.append(f"{key}={str(value)[:32]}")
            if len(parts) >= 8:
                break
        return "; ".join(parts)
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    text = str(payload or "")
    return text[:120]


def forbidden_request_reason(entry: dict[str, Any]) -> str | None:
    url = str(entry.get("url") or "")
    parsed = urlparse(url)
    path = parsed.path
    method = str(entry.get("method") or "GET").upper()
    kind = str(entry.get("kind") or "request")
    if kind == "websocket" and path not in ALLOWED_WS_PATHS:
        return f"forbidden_websocket:{path}"
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return f"non_readonly_method:{method}:{path}"
    for needle in FORBIDDEN_AUTO_PATHS:
        if needle in path:
            return f"forbidden_auto_path:{needle}"
    return None


def coverage_for_contracts(contracts: list[dict[str, Any]], required: set[str], manual_ids: set[str], user_gated_ids: set[str]) -> dict[str, Any]:
    endpoints = {str(c.get("endpoint") or "") for c in contracts}
    ids = {str(c.get("id") or "") for c in contracts}
    missing = sorted(required - endpoints)
    manual_missing = sorted(item for item in manual_ids if item not in ids)
    user_gated_missing = sorted(item for item in user_gated_ids if item not in ids)
    unsafe_auto = [c for c in contracts if c.get("method") in {"POST", "WS", "ACTION"} and c.get("safeAuto") is True]
    status = "PASS" if not missing and not manual_missing and not user_gated_missing and not unsafe_auto else "FAIL"
    return {
        "status": status,
        "contractCount": len(contracts),
        "missingEndpointsOrActions": missing,
        "missingManualGateIds": manual_missing,
        "missingUserGatedIds": user_gated_missing,
        "unsafeAutoContracts": unsafe_auto,
    }


def make_contact_sheet(out_dir: Path, backtest_path: Path, replay_path: Path) -> dict[str, Any]:
    path = out_dir / "runtime-depth-contact-sheet.png"
    if Image is None or ImageDraw is None:
        return {"status": "FAIL", "path": str(path), "reason": "Pillow unavailable"}
    width, height = 768, 500
    sheet = Image.new("RGB", (width, height), "#07131d")
    draw = ImageDraw.Draw(sheet)
    for idx, (label, shot) in enumerate((("Backtest V3 live read-only", backtest_path), ("Chart Replay V3 live read-only", replay_path))):
        y = idx * 250
        draw.rectangle((0, y, width, y + 34), fill="#0b2030")
        draw.text((10, y + 9), label, fill="#d8eefc")
        with Image.open(shot) as raw:
            img = raw.convert("RGB").resize((768, 216))
        sheet.paste(img, (0, y + 34))
    sheet.save(path)
    return {"status": "PASS", "path": str(path), "layout": "Backtest screenshot on top, chart replay screenshot below."}


def capture_pages(base_url: str, out_dir: Path, timeout_ms: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Playwright is required for runtime-depth capture: {exc}") from exc

    forbidden_findings: list[dict[str, Any]] = []
    transcript_actions: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)

    def timestamp(i: int) -> str:
        return (started.replace(microsecond=0)).isoformat().replace("+00:00", "Z")[:-1] + f".{i:03d}Z"

    def record_request(route_id: str, version: str, entry: dict[str, Any]) -> None:
        reason = forbidden_request_reason(entry)
        if reason:
            forbidden_findings.append({"routeId": route_id, "version": version, "url": entry.get("url"), "method": entry.get("method"), "reason": reason})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)

        def page_capture(route_id: str, path: str, required_text: tuple[str, ...], contracts_expr: str, screenshot_name: str) -> dict[str, Any]:
            requests: list[dict[str, Any]] = []
            websockets: list[str] = []
            console_errors: list[dict[str, str]] = []
            page_errors: list[str] = []
            page = context.new_page()
            page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "assert"} else None)
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.on("request", lambda req: requests.append({"kind": "request", "method": req.method, "url": req.url, "resourceType": req.resource_type}))
            page.on("websocket", lambda ws: websockets.append(ws.url))
            url = norm_url(base_url, path)
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(1200)
            text = page.locator("body").inner_text(timeout=timeout_ms)
            if "Live probe pending" in text or "awaiting" in text:
                page.wait_for_timeout(3500)
                text = page.locator("body").inner_text(timeout=timeout_ms)
            contracts = page.evaluate(contracts_expr)
            shot = out_dir / screenshot_name
            page.screenshot(path=str(shot), full_page=False)
            for req in requests:
                record_request(route_id, "v3", req)
            for ws_url in websockets:
                record_request(route_id, "v3", {"kind": "websocket", "method": "GET", "url": ws_url})
            score = text_score(required_text, text)
            transcript_actions.append({"type": "navigate", "timestamp": timestamp(len(transcript_actions)), "selector": "browser-url", "target": url, "status": "passed", "assertion": f"{route_id} loaded with status {None if response is None else response.status}"})
            transcript_actions.append({"type": "assert", "timestamp": timestamp(len(transcript_actions)), "selector": "body", "status": "passed" if not score["missing"] else "failed", "assertion": f"{route_id} text score {score['score']} missing={score['missing']}"})
            payload = {
                "routeId": route_id,
                "url": url,
                "statusCode": None if response is None else response.status,
                "headers": {} if response is None else {k.lower(): v for k, v in response.headers.items() if k.lower() in {"x-stom-dashboard-version", "cache-control"}},
                "title": page.title(),
                "textScore": score,
                "contracts": contracts,
                "requests": [{"method": r.get("method"), "path": simplified_url(r.get("url", "")), "resourceType": r.get("resourceType")} for r in requests],
                "websockets": websockets,
                "consoleErrors": console_errors,
                "pageErrors": page_errors,
                "screenshot": str(shot),
                "imageMetrics": screenshot_metrics(shot),
                "bodyTextExcerpt": text[:3000],
            }
            page.close()
            return payload

        backtest = page_capture("backtest", "/ui/remodel/backtest", BACKTEST_REQUIRED_TEXT, "window.BacktestContracts || []", "backtest-live-depth.png")
        replay = page_capture("chart_replay", "/ui/remodel/chart-replay", REPLAY_REQUIRED_TEXT, "window.ReplayContracts || []", "chart-replay-live-depth.png")
        browser.close()

    transcript = {
        "schemaVersion": 1,
        "kind": "browser-automation",
        "tool": "playwright+verify_dashboard_runtime_depth",
        "surface": "web",
        "verdict": "passed" if not forbidden_findings and not backtest["textScore"]["missing"] and not replay["textScore"]["missing"] else "failed",
        "startedAt": started.isoformat(),
        "endedAt": utc_now(),
        "actions": transcript_actions,
    }
    return {"backtest": backtest, "chartReplay": replay, "transcript": transcript}, forbidden_findings, transcript_actions


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    captures, forbidden_findings, _actions = capture_pages(args.base_url, out_dir, args.timeout_ms)
    backtest = captures["backtest"]
    replay = captures["chartReplay"]
    back_cov = coverage_for_contracts(
        backtest["contracts"],
        BACKTEST_REQUIRED_ENDPOINTS,
        {"bt-strategy-validate", "bt-strategy-save", "bt-strategy-delete", "bt-extract-vars", "bt-run", "bt-job-cancel", "bt-job-meta", "bt-portfolio"},
        {"bt-ws-job"},
    )
    replay_cov = coverage_for_contracts(
        replay["contracts"],
        REPLAY_REQUIRED_ENDPOINTS,
        set(),
        {"sim-ws", "ws-action-start", "ws-action-pause", "ws-action-resume", "ws-action-speed", "ws-action-seek", "ws-action-stop"},
    )

    api_rows = [api_get(args.base_url, path) for path in SAFE_BACKTEST_GETS + SAFE_REPLAY_GETS]
    # Conditional replay reads are safe GETs only after demo discovery.
    demo = next((row for row in api_rows if row.get("path") == "/sim/demo?src=min&mode=latest"), {})
    # Keep direct conditional probes conservative; the page itself also probes discovered stocks/signals when keys exist.
    api_failures = [
        row for row in api_rows
        if (
            not isinstance(row.get("statusCode"), int)
            or row.get("statusCode", 500) >= 500
            or (row.get("path") in {"/bt/strategies?kind=buy", "/bt/strategies?kind=sell"} and row.get("jsonStatus") == "error")
        )
    ]

    forbidden_scan = {
        "generatedAt": utc_now(),
        "status": "PASS" if not forbidden_findings else "FAIL",
        "findings": forbidden_findings,
        "forbiddenAutoPaths": list(FORBIDDEN_AUTO_PATHS),
        "allowedWebSocketPaths": sorted(ALLOWED_WS_PATHS),
        "readOnly": True,
    }
    contact = make_contact_sheet(out_dir, Path(backtest["screenshot"]), Path(replay["screenshot"]))

    back_score = 100.0 if not backtest["textScore"]["missing"] and back_cov["status"] == "PASS" and not backtest["consoleErrors"] and not backtest["pageErrors"] and backtest["imageMetrics"]["nonUniform"] else 0.0
    replay_score = 100.0 if not replay["textScore"]["missing"] and replay_cov["status"] == "PASS" and not replay["consoleErrors"] and not replay["pageErrors"] and replay["imageMetrics"]["nonUniform"] else 0.0
    api_score = 100.0 if not api_failures else max(0.0, 100.0 - 10.0 * len(api_failures))
    safety_score = 100.0 if forbidden_scan["status"] == "PASS" else 0.0
    average = round(back_score * 0.34 + replay_score * 0.34 + api_score * 0.17 + safety_score * 0.15, 2)

    failures: list[dict[str, Any]] = []
    if back_score < 95.0:
        failures.append({"id": "backtest", "reason": "backtest_depth_failed", "textMissing": backtest["textScore"]["missing"], "coverage": back_cov})
    if replay_score < 95.0:
        failures.append({"id": "chart_replay", "reason": "replay_depth_failed", "textMissing": replay["textScore"]["missing"], "coverage": replay_cov})
    if api_failures:
        failures.append({"reason": "api_smoke_failures", "failures": api_failures})
    if forbidden_scan["status"] != "PASS":
        failures.append({"reason": "forbidden_runtime_findings", "findings": forbidden_findings})
    if contact["status"] != "PASS":
        failures.append({"reason": "contact_sheet_failed", "detail": contact})

    scorecard = {
        "schemaVersion": 1,
        "kind": "dashboard-runtime-depth-scorecard",
        "generatedAt": utc_now(),
        "baseUrl": args.base_url,
        "status": "PASS" if not failures else "FAIL",
        "averageRuntimeDepthScore": average,
        "scores": {"backtest": back_score, "chartReplay": replay_score, "apiSmoke": api_score, "safety": safety_score},
        "failures": failures,
        "coverage": {"backtest": back_cov, "chartReplay": replay_cov},
    }

    write_json(out_dir / "backtest-runtime-evidence.json", backtest)
    write_json(out_dir / "chart-replay-runtime-evidence.json", replay)
    write_json(out_dir / "api-smoke.json", {"generatedAt": utc_now(), "status": "PASS" if not api_failures else "FAIL", "rows": api_rows, "failures": api_failures, "readOnly": True, "demoSummary": demo})
    write_json(out_dir / "forbidden-runtime-scan.json", forbidden_scan)
    write_json(out_dir / "runtime-depth-scorecard.json", scorecard)
    write_json(out_dir / "browser-transcript.json", captures["transcript"])
    write_json(out_dir / "manifest.json", {
        "schemaVersion": 1,
        "kind": "dashboard-runtime-depth-manifest",
        "generatedAt": utc_now(),
        "status": scorecard["status"],
        "artifacts": {
            "scorecard": str((out_dir / "runtime-depth-scorecard.json").resolve()),
            "backtestEvidence": str((out_dir / "backtest-runtime-evidence.json").resolve()),
            "chartReplayEvidence": str((out_dir / "chart-replay-runtime-evidence.json").resolve()),
            "apiSmoke": str((out_dir / "api-smoke.json").resolve()),
            "forbiddenRuntimeScan": str((out_dir / "forbidden-runtime-scan.json").resolve()),
            "browserTranscript": str((out_dir / "browser-transcript.json").resolve()),
            "contactSheet": str((out_dir / "runtime-depth-contact-sheet.png").resolve()),
        },
    })

    print(json.dumps({"status": scorecard["status"], "averageRuntimeDepthScore": average, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if scorecard["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
