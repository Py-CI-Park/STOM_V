from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:  # Pillow is optional at import time so static tests can load this file cheaply.
    from PIL import Image, ImageChops, ImageFilter, ImageStat
except Exception:  # pragma: no cover - exercised only on hosts without Pillow.
    Image = None  # type: ignore[assignment]
    ImageChops = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[1]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
CAPTURE_REFERENCE_DIR = REMODEL / "docs" / "captures"
SOURCE_SCAN_FILES = [
    REMODEL / "index.html",
    REMODEL / "src" / "app.js",
    REMODEL / "src" / "data.js",
    REMODEL / "styles" / "theme.css",
]
LIVE_ARTIFACT_CANDIDATES = {
    "G004_BACKTEST": REPO / "artifacts" / "ultragoal-g004-backtest",
    "G005_REPLAY": REPO / "artifacts" / "ultragoal-g005-replay",
}


@dataclass(frozen=True)
class RouteCase:
    id: str
    path: str
    title: str
    required_text: tuple[str, ...]


ROUTES: tuple[RouteCase, ...] = (
    RouteCase(
        "01_condition_ai_overview",
        "/ui/remodel/condition?demo=reference",
        "조건식 AI / 조건식 AI",
        ("현재 세대 라이브 상태", "세대 테이블", "BEST / WINNER", "Human Approval", "Strategy Inspector"),
    ),
    RouteCase(
        "02_process",
        "/ui/remodel/process?demo=reference",
        "조건식 AI / 프로세스",
        ("프로세스 맵", "Generation", "Backtest", "Scoring", "Autopsy", "Repeat", "라이브 로그"),
    ),
    RouteCase(
        "03_history",
        "/ui/remodel/history?demo=reference",
        "조건식 AI / 히스토리",
        ("실행/생성 히스토리", "Research Records", "ResultDetail", "Compare", "Lineage"),
    ),
    RouteCase(
        "04_lab",
        "/ui/remodel/lab?demo=reference",
        "조건식 AI / 연구실",
        ("Edge Ratio", "변수 중요도", "상관관계", "변수 조합", "검증 요약"),
    ),
    RouteCase(
        "05_workbench",
        "/ui/remodel/workbench?demo=reference",
        "조건식 AI / 분석 워크벤치",
        ("Hall of Fame 워크벤치", "History Compare", "Backtest Result Review", "후보 상세 분석", "리뷰 큐"),
    ),
    RouteCase(
        "06_decision_audit",
        "/ui/remodel/audit?demo=reference",
        "조건식 AI / 결정 감사",
        ("결정 감사", "Append-Only", "PROMOTE", "OOS 성과 차이", "결정 히스토리"),
    ),
    RouteCase(
        "07_backtest",
        "/ui/remodel/backtest?demo=reference",
        "백테스트",
        ("REFERENCE mode", "Backtest API Contract Matrix", "실행 파라미터", "최적화", "WFO", "스윕", "조건식 편집", "결과 분석", "독립 HTML 보고서"),
    ),
    RouteCase(
        "08_chart_replay",
        "/ui/remodel/chart-replay?demo=reference",
        "차트 리플레이",
        ("데이터 소스", "재생 컨트롤", "실시간 리플레이 차트", "/sim/ws 수동 게이트", "전략 신호 로그"),
    ),
)


SAFETY_CUES = (
    "No Live Order",
    "No Broker Login",
    "No Account Trading",
    "Research Only",
    "Human Approval Gate",
    "Append-Only Audit",
    "research-only",
    "local-only",
    "실거래/주문 기능 없음",
    "브로커 로그인 없음",
    "계좌/자산 연동 없음",
    "연구 전용",
    "Human Gate Required",
    "Append-Only",
)
REQUIRED_SAFETY_TEXT = ("No Live Order", "No Broker Login", "No Account Trading", "Research Only", "Human Approval Gate", "Append-Only Audit")
FORBIDDEN_ACTION_MARKERS = (
    'data-action="live-order"',
    'data-action="broker-login"',
    'data-action="account-trade"',
    'data-action="replay-live-order"',
    "liveOrder",
    "brokerLogin",
    "accountTrade",
    "주문 실행",
    "계좌 로그인",
    "브로커 로그인 버튼",
    "hidden production export",
)
FORBIDDEN_ENDPOINT_MARKERS = ("/sim/ws", "/bt/ws_job")
ENDPOINT_ALLOW_CONTEXT = (
    "never auto-opened",
    "not auto-invoked",
    "user-gated",
    "manual",
    "inert",
    "no /sim/ws",
    "must not auto-open",
)
MODAL_CONTRACTS = {
    "settings": {
        "source_markers": ('data-action="settings"', "openSettingsModal"),
        "dom_buttons": ("설정",),
    },
    "inspector": {
        "source_markers": ('data-action="inspector"', "openInspectorModal", "Strategy Inspector"),
        "dom_buttons": ("인스펙터", "Inspector"),
    },
    "approval_export": {
        "source_markers": ('data-action="approval"', "openApprovalModal", "Winner 승인 / Export", "Human Confirm"),
        "dom_buttons": ("승인", "Export", "내보내기"),
    },
}
OUTPUT_ARTIFACTS = (
    "visual-gate-manifest.json",
    "scorecard.json",
    "side-by-side-contact-sheet.png",
    "source-safety-scan.json",
    "dom-safety-scan.json",
    "modal-coverage.json",
    "api-live-evidence.json",
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only visual/evidence gate for the STOM dashboard remodel.")
    parser.add_argument("--base-url", required=True, help="Running dashboard base URL, e.g. http://127.0.0.1:8776")
    parser.add_argument("--out", required=True, type=Path, help="Output artifact directory")
    parser.add_argument("--min-page-score", type=float, default=95.0)
    parser.add_argument("--min-average-score", type=float, default=97.0)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def artifact_ref(path: Path) -> str:
    return str(path.resolve())


def norm_url(base_url: str, route_path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", route_path.lstrip("/"))


def image_metrics(reference_path: Path, current_path: Path) -> dict[str, Any]:
    if Image is None:
        return {"available": False, "error": "Pillow is not installed; visual comparison unavailable.", "score": 0.0}
    with Image.open(reference_path) as ref_raw, Image.open(current_path) as cur_raw:
        ref = ref_raw.convert("RGB")
        cur = cur_raw.convert("RGB")
        current_size = list(cur.size)
        reference_size = list(ref.size)
        if cur.size != ref.size:
            cur = cur.resize(ref.size)
        small_ref = ref.resize((320, 180))
        small_cur = cur.resize((320, 180))
        diff = ImageChops.difference(small_ref, small_cur)
        stat = ImageStat.Stat(diff)
        mean_abs = sum(stat.mean) / 3.0
        rms = math.sqrt(sum(v * v for v in stat.rms) / 3.0)
        pixel_similarity = max(0.0, 100.0 - (mean_abs / 255.0 * 100.0))
        rmse_similarity = max(0.0, 100.0 - (rms / 255.0 * 100.0))
        hist_ref = small_ref.histogram()
        hist_cur = small_cur.histogram()
        dot = sum(a * b for a, b in zip(hist_ref, hist_cur))
        mag_ref = math.sqrt(sum(a * a for a in hist_ref))
        mag_cur = math.sqrt(sum(b * b for b in hist_cur))
        histogram_cosine = (dot / (mag_ref * mag_cur) * 100.0) if mag_ref and mag_cur else 0.0
        edge_similarity = edge_iou(small_ref, small_cur)
        dhash_similarity = dhash_score(small_ref, small_cur)
        weighted_visual_parity_score = (
            pixel_similarity * 0.35
            + rmse_similarity * 0.25
            + histogram_cosine * 0.20
            + dhash_similarity * 0.10
            + edge_similarity * 0.10
        )
        blank = is_blank_image(cur)
        unreadable = current_size[0] < 1000 or current_size[1] < 700
        if blank or unreadable:
            weighted_visual_parity_score = 0.0
        return {
            "available": True,
            "referenceSize": reference_size,
            "currentSize": current_size,
            "pixelSimilarity": round(pixel_similarity, 2),
            "rmseSimilarity": round(rmse_similarity, 2),
            "dhashSimilarity": round(dhash_similarity, 2),
            "edgeIoU": round(edge_similarity, 2),
            "histogramCosine": round(histogram_cosine, 2),
            "weightedVisualParityScore": round(weighted_visual_parity_score, 2),
            "meanAbsPixelDelta": round(mean_abs, 2),
            "rmsPixelDelta": round(rms, 2),
            "blankOrUnreadable": bool(blank or unreadable),
            "scoreFieldDocumentation": {
                "pixelSimilarity": "100 - average absolute RGB channel delta percentage after deterministic 320x180 downscale.",
                "rmseSimilarity": "100 - RMS RGB channel delta percentage after deterministic 320x180 downscale.",
                "histogramCosine": "Cosine similarity of RGB histograms after deterministic downscale.",
                "dhashSimilarity": "Similarity of 64-bit difference hashes for coarse layout drift detection.",
                "edgeIoU": "Intersection-over-union of FIND_EDGES luminance masks for structure drift detection.",
                "weightedVisualParityScore": "0.35 pixel + 0.25 RMSE + 0.20 histogram + 0.10 dHash + 0.10 edgeIoU; forced to 0 for blank/unreadable captures.",
            },
        }


def is_blank_image(img: Any) -> bool:
    stat = ImageStat.Stat(img.resize((160, 90)).convert("L"))
    return stat.stddev[0] < 2.0


def edge_iou(ref: Any, cur: Any) -> float:
    ref_edges = ref.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda p: 255 if p > 18 else 0)
    cur_edges = cur.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda p: 255 if p > 18 else 0)
    ref_pixels = list(ref_edges.getdata())
    cur_pixels = list(cur_edges.getdata())
    intersection = sum(1 for a, b in zip(ref_pixels, cur_pixels) if a and b)
    union = sum(1 for a, b in zip(ref_pixels, cur_pixels) if a or b)
    return (intersection / union * 100.0) if union else 100.0


def dhash_score(ref: Any, cur: Any) -> float:
    def bits(img: Any) -> list[int]:
        small = img.convert("L").resize((9, 8))
        px = list(small.getdata())
        out: list[int] = []
        for y in range(8):
            row = px[y * 9 : (y + 1) * 9]
            out.extend(1 if row[x] > row[x + 1] else 0 for x in range(8))
        return out

    a = bits(ref)
    b = bits(cur)
    matches = sum(1 for x, y in zip(a, b) if x == y)
    return matches / len(a) * 100.0


def score_page(case: RouteCase, text: str, metrics: dict[str, Any], console_errors: list[dict[str, str]], page_errors: list[str]) -> dict[str, Any]:
    missing_required = [needle for needle in case.required_text if needle not in text]
    missing_safety = [needle for needle in REQUIRED_SAFETY_TEXT if needle not in text]
    required_text_score = (1.0 - len(missing_required) / max(1, len(case.required_text))) * 100.0
    safety_score = (1.0 - len(missing_safety) / len(REQUIRED_SAFETY_TEXT)) * 100.0
    page_score = (
        required_text_score * 0.45
        + safety_score * 0.25
        + float(metrics.get("pixelSimilarity", 0.0)) * 0.20
        + float(metrics.get("rmseSimilarity", 0.0)) * 0.05
        + float(metrics.get("histogramCosine", 0.0)) * 0.05
    )
    hard_failures: list[str] = []
    if missing_required:
        hard_failures.append("missing_required_route_text")
    if missing_safety:
        hard_failures.append("missing_required_safety_text")
    if metrics.get("blankOrUnreadable"):
        hard_failures.append("blank_or_unreadable_screenshot")
    if console_errors:
        hard_failures.append("browser_console_errors")
    if page_errors:
        hard_failures.append("browser_page_errors")
    if hard_failures:
        page_score = min(page_score, 94.0)
    return {
        "id": case.id,
        "title": case.title,
        "route": case.path,
        "requiredTextScore": round(required_text_score, 2),
        "missingRequiredText": missing_required,
        "safetyTextScore": round(safety_score, 2),
        "missingSafetyText": missing_safety,
        "visualMetrics": metrics,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "hardFailures": hard_failures,
        "totalCorrectedScore": round(page_score, 2),
    }


def source_safety_scan() -> dict[str, Any]:
    files = []
    failures: list[dict[str, Any]] = []
    cue_hits = {cue: [] for cue in SAFETY_CUES}
    forbidden_hits: list[dict[str, Any]] = []
    endpoint_hits: list[dict[str, Any]] = []
    for path in SOURCE_SCAN_FILES:
        if not path.exists():
            failures.append({"file": str(path.relative_to(REPO)), "reason": "missing_source_file"})
            continue
        text = read_text(path)
        rel = str(path.relative_to(REPO))
        files.append(rel)
        for cue in SAFETY_CUES:
            if cue in text:
                cue_hits[cue].append(rel)
        for marker in FORBIDDEN_ACTION_MARKERS:
            if marker.lower() in text.lower():
                forbidden_hits.append({"file": rel, "marker": marker})
        for endpoint in FORBIDDEN_ENDPOINT_MARKERS:
            for match in re.finditer(re.escape(endpoint), text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                allowed = any(term in line.lower() for term in ENDPOINT_ALLOW_CONTEXT)
                endpoint_hits.append({"file": rel, "endpoint": endpoint, "line": line.strip(), "allowedDocumentedManualOnly": allowed})
                if not allowed:
                    forbidden_hits.append({"file": rel, "marker": endpoint, "reason": "endpoint lacks manual/inert/no-auto-open context"})
        for line in text.splitlines():
            lowered = line.lower()
            if "new websocket" in lowered and "/sim/ws" in lowered and not any(term in lowered for term in ENDPOINT_ALLOW_CONTEXT):
                forbidden_hits.append({"file": rel, "marker": "new WebSocket + /sim/ws", "reason": "possible auto-open replay websocket", "line": line.strip()})
    missing_cues = [cue for cue in REQUIRED_SAFETY_TEXT if not cue_hits.get(cue)]
    if missing_cues:
        failures.append({"reason": "missing_source_safety_cues", "missing": missing_cues})
    if forbidden_hits:
        failures.append({"reason": "forbidden_source_marker_present", "hits": forbidden_hits})
    return {
        "generatedAt": utc_now(),
        "files": files,
        "safetyCueHits": cue_hits,
        "endpointDocumentationHits": endpoint_hits,
        "forbiddenHits": forbidden_hits,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def modal_coverage_from_source_and_dom(source_text: str, dom_snapshots: dict[str, str]) -> dict[str, Any]:
    rows = []
    failures = []
    combined_dom = "\n".join(dom_snapshots.values())
    for name, contract in MODAL_CONTRACTS.items():
        missing_source = [m for m in contract["source_markers"] if m not in source_text]
        missing_dom = [m for m in contract["dom_buttons"] if m not in combined_dom]
        row = {
            "name": name,
            "sourceMarkers": list(contract["source_markers"]),
            "missingSourceMarkers": missing_source,
            "domButtonMarkers": list(contract["dom_buttons"]),
            "missingDomButtonMarkers": missing_dom,
            "status": "PASS" if not missing_source and not missing_dom else "FAIL",
        }
        rows.append(row)
        if row["status"] != "PASS":
            failures.append(row)
    return {"generatedAt": utc_now(), "rows": rows, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def dom_safety_scan(dom_snapshots: dict[str, str], action_snapshots: dict[str, list[str]]) -> dict[str, Any]:
    rows = []
    failures = []
    for route_id, text in dom_snapshots.items():
        cue_hits = [cue for cue in SAFETY_CUES if cue in text]
        forbidden_text = [marker for marker in FORBIDDEN_ACTION_MARKERS if marker.lower() in text.lower()]
        forbidden_actions = [action for action in action_snapshots.get(route_id, []) if action in {"broker-login", "replay-live-order", "live-order", "account-trade"}]
        missing_required = [cue for cue in REQUIRED_SAFETY_TEXT if cue not in text]
        row_failures = []
        if missing_required:
            row_failures.append("missing_required_safety_text")
        if forbidden_text or forbidden_actions:
            row_failures.append("forbidden_dom_control_or_text")
        row = {
            "id": route_id,
            "safetyCueHits": cue_hits,
            "missingRequiredSafetyText": missing_required,
            "dataActions": action_snapshots.get(route_id, []),
            "forbiddenTextHits": forbidden_text,
            "forbiddenActionHits": forbidden_actions,
            "failures": row_failures,
            "status": "PASS" if not row_failures else "FAIL",
        }
        rows.append(row)
        if row_failures:
            failures.append(row)
    return {"generatedAt": utc_now(), "rows": rows, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def api_live_evidence() -> dict[str, Any]:
    rows = []
    for label, directory in LIVE_ARTIFACT_CANDIDATES.items():
        artifacts = []
        if directory.exists():
            artifacts = [str(path.relative_to(REPO)) for path in sorted(directory.iterdir()) if path.is_file()]
        rows.append(
            {
                "label": label,
                "directory": str(directory.relative_to(REPO)),
                "status": "LINKED" if artifacts else "PLACEHOLDER_MISSING",
                "artifactRefs": artifacts,
                "note": "Linked read-only prior live evidence when present; this G006 gate does not call live order, broker, account, export, or WebSocket start paths.",
            }
        )
    return {"generatedAt": utc_now(), "rows": rows, "readOnly": True}


def make_contact_sheet(out_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    sheet_path = out_dir / "side-by-side-contact-sheet.png"
    if Image is None:
        return {"path": str(sheet_path), "status": "SKIPPED", "reason": "Pillow unavailable"}
    thumbs = []
    for row in rows:
        ref_path = CAPTURE_REFERENCE_DIR / f"{row['id']}.png"
        cur_path = out_dir / f"{row['id']}.png"
        with Image.open(ref_path) as ref, Image.open(cur_path) as cur:
            ref_thumb = ref.convert("RGB").resize((384, 216))
            cur_thumb = cur.convert("RGB").resize((384, 216))
            thumbs.append((row, ref_thumb.copy(), cur_thumb.copy()))
    width = 768
    height = 216 * len(thumbs)
    sheet = Image.new("RGB", (width, height), "white")
    for idx, (_row, ref, cur) in enumerate(thumbs):
        y = idx * 216
        sheet.paste(ref, (0, y))
        sheet.paste(cur, (384, y))
    sheet.save(sheet_path)
    return {"path": str(sheet_path), "status": "PASS", "layout": "Each row is reference left and current capture right at 384x216."}


def capture_routes(base_url: str, out_dir: Path, timeout_ms: int) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, list[str]]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent.
        raise RuntimeError(f"Playwright is required for capture: {exc}") from exc

    rows: list[dict[str, Any]] = []
    dom_snapshots: dict[str, str] = {}
    action_snapshots: dict[str, list[str]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        for case in ROUTES:
            page_console: list[dict[str, str]] = []
            page_errors: list[str] = []
            page = context.new_page()
            page.on("console", lambda msg, sink=page_console: sink.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "assert"} else None)
            page.on("pageerror", lambda err, sink=page_errors: sink.append(str(err)))
            url = norm_url(base_url, case.path)
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if response is None or response.status >= 400:
                page_errors.append(f"navigation_status={None if response is None else response.status}")
            page.wait_for_selector("#page", timeout=timeout_ms)
            page.wait_for_timeout(250)
            text = page.locator("body").inner_text(timeout=timeout_ms)
            actions = page.locator("[data-action]").evaluate_all("els => els.map(el => el.getAttribute('data-action')).filter(Boolean)")
            current_path = out_dir / f"{case.id}.png"
            page.screenshot(path=str(current_path), full_page=False)
            reference_path = CAPTURE_REFERENCE_DIR / f"{case.id}.png"
            metrics = image_metrics(reference_path, current_path)
            row = score_page(case, text, metrics, page_console, page_errors)
            row.update(
                {
                    "url": url,
                    "screenshot": str(current_path),
                    "reference": str(reference_path),
                    "responseStatus": None if response is None else response.status,
                }
            )
            rows.append(row)
            dom_snapshots[case.id] = text
            action_snapshots[case.id] = list(actions)
            page.close()
        browser.close()
    return rows, dom_snapshots, action_snapshots


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    missing_refs = [str((CAPTURE_REFERENCE_DIR / f"{case.id}.png").relative_to(REPO)) for case in ROUTES if not (CAPTURE_REFERENCE_DIR / f"{case.id}.png").is_file()]
    if missing_refs:
        write_json(out_dir / "visual-gate-manifest.json", {"status": "FAIL", "missingReferences": missing_refs, "generatedAt": utc_now()})
        return 2

    source_scan = source_safety_scan()
    rows, dom_snapshots, action_snapshots = capture_routes(args.base_url, out_dir, args.timeout_ms)
    dom_scan = dom_safety_scan(dom_snapshots, action_snapshots)
    source_text = "\n".join(read_text(path) for path in SOURCE_SCAN_FILES if path.exists())
    modal_coverage = modal_coverage_from_source_and_dom(source_text, dom_snapshots)
    api_evidence = api_live_evidence()
    contact_sheet = make_contact_sheet(out_dir, rows)

    average_score = round(sum(row["totalCorrectedScore"] for row in rows) / len(rows), 2)
    score_failures = []
    for row in rows:
        if row["totalCorrectedScore"] < args.min_page_score:
            score_failures.append({"id": row["id"], "reason": "below_min_page_score", "score": row["totalCorrectedScore"], "minimum": args.min_page_score})
        if row["hardFailures"]:
            score_failures.append({"id": row["id"], "reason": "hard_failures", "failures": row["hardFailures"]})
    if average_score < args.min_average_score:
        score_failures.append({"reason": "below_min_average_score", "score": average_score, "minimum": args.min_average_score})
    if source_scan["status"] != "PASS":
        score_failures.append({"reason": "source_safety_scan_failed"})
    if dom_scan["status"] != "PASS":
        score_failures.append({"reason": "dom_safety_scan_failed"})
    if modal_coverage["status"] != "PASS":
        score_failures.append({"reason": "modal_coverage_failed"})
    if contact_sheet["status"] != "PASS":
        score_failures.append({"reason": "contact_sheet_failed", "detail": contact_sheet})

    scorecard = {
        "generatedAt": utc_now(),
        "basis": "Reference captures under ai_strategy_loop/dashboard/frontend/remodel/docs/captures versus current Playwright Chromium captures at 1920x1080 with ?demo=reference.",
        "thresholds": {"minPageScore": args.min_page_score, "minAverageScore": args.min_average_score},
        "averageCorrectedTotalScore": average_score,
        "rows": rows,
        "failures": score_failures,
        "status": "PASS" if not score_failures else "FAIL",
        "scoreFieldDocumentation": {
            "requiredTextScore": "Percent of route-specific contract text found in DOM body text.",
            "safetyTextScore": "Percent of required safety text found in DOM body text: No Live Order, No Broker Login, No Account Trading, Research Only, Human Approval Gate, Append-Only Audit.",
            "totalCorrectedScore": "0.45 requiredTextScore + 0.25 safetyTextScore + 0.20 pixelSimilarity + 0.05 rmseSimilarity + 0.05 histogramCosine; capped below threshold by hard failures. weightedVisualParityScore, edgeIoU, and dHash remain diagnostics only.",
        },
    }
    manifest = {
        "generatedAt": utc_now(),
        "readOnly": True,
        "baseUrl": args.base_url,
        "viewport": "1920x1080",
        "routes": [{"id": case.id, "path": case.path, "reference": artifact_ref(CAPTURE_REFERENCE_DIR / f"{case.id}.png")} for case in ROUTES],
        "artifacts": {name: artifact_ref(out_dir / name) for name in OUTPUT_ARTIFACTS},
        "captureArtifacts": {case.id: artifact_ref(out_dir / f"{case.id}.png") for case in ROUTES},
        "status": scorecard["status"],
    }

    write_json(out_dir / "source-safety-scan.json", source_scan)
    write_json(out_dir / "dom-safety-scan.json", dom_scan)
    write_json(out_dir / "modal-coverage.json", modal_coverage)
    write_json(out_dir / "api-live-evidence.json", api_evidence)
    write_json(out_dir / "scorecard.json", scorecard)
    write_json(out_dir / "visual-gate-manifest.json", manifest)
    print(json.dumps({"status": scorecard["status"], "averageCorrectedTotalScore": average_score, "failures": score_failures}, ensure_ascii=False, indent=2))
    return 0 if scorecard["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
