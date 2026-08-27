"""US-007 — AI strategy loop 대시보드 FastAPI 백엔드.

엔드포인트:
  - GET  /health       → {status, contract_version}
  - GET  /status       → 현재 LoopState (current_state.json 또는 idle 기본값)
  - GET  /config/spec  → config_field_specs (GUI 폼 렌더용)
  - WS   /ws           → 연결 시 현재 LoopState 송신 후 current_state.json
                         변경을 폴링(~1s)해 push. 인바운드 제어 메시지 수신:
                           {"action":"start","config":{...}}
                           {"action":"stop"}
                           {"action":"final_approval", ...}

제어 구현:
  - start          : 루프를 서브프로세스로 기동 (STOP 플래그 선제거).
  - stop           : STOP 플래그 파일을 쓴다 (루프가 세대 시작 전 관측).
  - final_approval : export_winner(...) 호출 (사람 승인 live-deploy 게이트).

CORS는 모두 허용 — Claude Design 프론트엔드가 별도 origin에서 서빙된다.

라이브 상태 seam은 controller/contract.py(LoopState) + controller/state.py
(publish/read/stop helpers)에 정의되어 있다.
"""

from __future__ import annotations

# bootstrap을 가장 먼저 — cli.*/utility.* import 전 env 격리 (export 경로용).
import ai_strategy_loop.bootstrap  # noqa: E402,F401

import asyncio  # noqa: E402
import difflib  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import threading  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
import re  # noqa: E402
from urllib.parse import parse_qs  # noqa: E402
from collections.abc import Callable  # noqa: E402
from typing import Any, Dict, List, Optional, assert_never  # noqa: E402

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller.evidence_contract import content_sha256  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.progress_contract import (  # noqa: E402
    build_backtest_progress,
    build_engine_state,
)
from ai_strategy_loop.controller.telemetry import (  # noqa: E402
    attach_telemetry_to_status,
    dashboard_telemetry,
)
from ai_strategy_loop.dashboard.research_api import router as research_router  # noqa: E402
from ai_strategy_loop.dashboard.backtest_api import backtest_router  # noqa: E402
from ai_strategy_loop.dashboard.simulation_api import simulation_router  # noqa: E402
from ai_strategy_loop.dashboard.security import (  # noqa: E402
    MAX_WEBSOCKET_MESSAGE_CHARS,
    Capability,
    DashboardSecurity,
    close_websocket_failure,
    is_loopback_http_url,
)
from ai_strategy_loop.dashboard.security_controls import (  # noqa: E402
    CONTROL_PAYLOAD_ADAPTER,
    ControlPayload,
    DecisionRecordPayload,
    FinalApprovalControl,
    LoopStartControl,
    LoopStopControl,
    control_capability,
)
from ai_strategy_loop.dashboard.alpha_api import alpha_router  # noqa: E402
from ai_strategy_loop.dashboard.trade_path_api import trade_path_router  # noqa: E402
from ai_strategy_loop.dashboard.reach_map_api import reach_map_router  # noqa: E402
from ai_strategy_loop.dashboard.analysis_card_api import analysis_card_router  # noqa: E402
from ai_strategy_loop.dashboard.autoloop_api import autoloop_router  # noqa: E402
from ai_strategy_loop.dashboard.provider_status_api import provider_status_router  # noqa: E402
from ai_strategy_loop.dashboard.transfer_ledger_api import transfer_ledger_router  # noqa: E402
from ai_strategy_loop.dashboard.exit_axis_api import exit_axis_router  # noqa: E402
from ai_strategy_loop.dashboard.strategy_ledger_api import strategy_ledger_router  # noqa: E402
from ai_strategy_loop.dashboard.power_gauge_api import power_gauge_router  # noqa: E402
from ai_strategy_loop.dashboard.response_surface_api import response_surface_router  # noqa: E402
from ai_strategy_loop.dashboard.condition_diff_api import condition_diff_router  # noqa: E402
from ai_strategy_loop.dashboard.trade_pairs_api import trade_pairs_router  # noqa: E402
from ai_strategy_loop.dashboard.research_tools_api import research_tools_router  # noqa: E402
from ai_strategy_loop.dashboard.research_program_api import research_program_router  # noqa: E402
from ai_strategy_loop.dashboard.research_truth_api import research_truth_router  # noqa: E402
from ai_strategy_loop.dashboard.analysis_bundle_api import analysis_bundle_router  # noqa: E402
from ai_strategy_loop.dashboard.research_result_api import research_result_router  # noqa: E402
from ai_strategy_loop.fitness.research_criteria import normalize_research_oos_mode, research_mode_payload  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 프론트엔드(Claude Design 산출물) 정적 자산 디렉토리. 모듈 위치 기준 절대 경로로
#   해석해 CWD와 무관하게 동작한다. 이 디렉토리를 /ui 하위에 마운트해 같은 origin에서
#   서빙한다(REST/WS API와 동일 출처 → CORS 우회 + 단일 진입점).
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
_REMODEL_FRONTEND_DIR = os.path.join(_FRONTEND_DIR, "remodel")
_DASHBOARD_RELEASE = "v5.16.0"
_DASHBOARD_SHELL = "v4-ops"
_DASHBOARD_BUILD_RE = re.compile(r"^[0-9A-Za-z._-]{1,64}$")
_DASHBOARD_PROCESS_STARTED_AT = int(time.time())


def _dashboard_build_identity() -> str:
    """Freeze the bundled frontend build identity when this backend process starts."""
    manifest_path = os.path.join(_FRONTEND_DIR, "bundle", "manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            value = json.load(fh).get("bundles", {}).get("app.js", {}).get("v")
        if isinstance(value, str) and _DASHBOARD_BUILD_RE.fullmatch(value):
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return "unknown"


_DASHBOARD_BUILD = _dashboard_build_identity()

# UXR-P7 Reports 허브 — 리포트 HTML 을 읽기 전용·스크립트 차단으로 안전 서빙한다.
#   허용 루트는 저장소 docs/ 하위 *.html 로 한정(alpha_lab reporting 산출물·process_flow 등).
#   보안(§10-5): (1) 경로 탈출(traversal) 차단 — 루트 하위 실제 파일만; (2) CSP default-src 'none'
#   로 스크립트 전면 차단(리포트에 inline JS 가 있어도 실행 불가); (3) 프론트는 sandbox iframe.
_REPORTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docs")
_REPORTS_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; "
    "font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def _reports_root_abs() -> str:
    return os.path.realpath(_REPORTS_ROOT)


def _safe_report_path(rel: str) -> Optional[str]:
    """rel 을 리포트 루트 하위의 실제 .html 파일로 안전 해석. traversal/비-html/부재는 None."""
    if not rel or "\x00" in rel:
        return None
    root = _reports_root_abs()
    candidate = os.path.realpath(os.path.join(root, rel))
    # 루트 경계 탈출 차단(realpath 후 접두 검사; 구분자 경계 포함).
    if candidate != root and not candidate.startswith(root + os.sep):
        return None
    if not candidate.lower().endswith(".html") or not os.path.isfile(candidate):
        return None
    return candidate


_REPORT_CATALOG_TTL_SECONDS = 30.0
_REPORT_CATALOG_CACHE: Dict[str, tuple[float, list[Dict[str, Any]]]] = {}
_REPORT_CATALOG_CACHE_LOCK = threading.RLock()
_REPORT_MANIFEST_SCHEMA_VERSION = "stom-research-report-v1"
_REPORT_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _report_manifest_relative_path(prefix: str, report: Dict[str, Any]) -> Optional[str]:
    report_path = report.get("path")
    if not isinstance(report_path, str) or not report_path.lower().endswith(".html"):
        return None
    normalized = report_path.replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or os.path.isabs(report_path)
        or any(part in ("", ".", "..") for part in normalized.split("/"))
    ):
        return None
    return f"{prefix}/{normalized}".replace("//", "/")


def _failed_report_metadata(reason: str, report: Dict[str, Any]) -> Dict[str, Any]:
    source_sha256 = report.get("source_sha256")
    provenance = report.get("provenance")
    source_backed = (
        isinstance(source_sha256, str)
        and _REPORT_SHA256_RE.fullmatch(source_sha256.lower()) is not None
        and isinstance(provenance, str)
        and bool(provenance.strip())
    )
    return {
        "registered": False,
        "integrity_status": "failed",
        "integrity_error": reason,
        "catalog_classification": "source_backed_regenerable" if source_backed else "unverifiable",
        "catalog_reason": (
            f"{reason}; manifest declares source_sha256 and provenance"
            if source_backed
            else reason
        ),
        **{
            key: report.get(key)
            for key in ("source_sha256", "provenance", "generator", "report_type", "research_id", "run_id")
            if report.get(key) is not None
        },
    }
def _is_legacy_static_manifest(payload: Any) -> bool:
    if (
        not isinstance(payload, dict)
        or set(payload) != {"generated_at", "count", "reports"}
        or not isinstance(payload.get("generated_at"), str)
        or not payload["generated_at"]
        or not isinstance(payload.get("count"), int)
        or isinstance(payload.get("count"), bool)
        or not isinstance(payload.get("reports"), list)
        or payload["count"] != len(payload["reports"])
    ):
        return False
    for report in payload["reports"]:
        if (
            not isinstance(report, dict)
            or set(report) != {"research_id", "step_id", "path", "sha256", "bytes", "trust"}
            or not all(isinstance(report.get(key), str) and report[key] for key in ("research_id", "step_id", "trust"))
            or not isinstance(report.get("sha256"), str)
            or _REPORT_SHA256_RE.fullmatch(report["sha256"].lower()) is None
            or not isinstance(report.get("bytes"), int)
            or isinstance(report.get("bytes"), bool)
            or report["bytes"] < 0
        ):
            return False
    return True


def _legacy_static_report_metadata(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "registered": False,
        "integrity_status": "legacy_static",
        "catalog_classification": "legacy_static",
        "catalog_reason": "recognized_legacy_manifest_not_migrated",
        "research_id": report["research_id"],
        "trust": report["trust"],
    }




def _report_manifest_rows(root: str) -> Dict[str, Dict[str, Any]]:
    """Return only manifest metadata whose declared file bytes and digest verify."""
    rows: Dict[str, Dict[str, Any]] = {}
    for rel_manifest in (
        "generated_reports/manifest.json",
        "research/condition_research/reports/research_report_manifest.json",
        # QSP(퀀트 채점 파이프라인) 보고서 — 매니페스트를 보고서 옆에 둔다.
        #   경로 규약상 항목의 path 는 매니페스트 디렉토리 기준 상대경로여야 하고
        #   '..' 를 포함할 수 없다(_report_manifest_relative_path).
        "research/quant_scoring_pipeline/qsp_report_manifest.json",
    ):
        manifest_path = os.path.join(root, *rel_manifest.split("/"))
        prefix = os.path.dirname(rel_manifest).replace("\\", "/")
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError, TypeError):
            continue

        reports = payload.get("reports") if isinstance(payload, dict) else None
        manifest_valid = (
            isinstance(payload, dict)
            and payload.get("schema_version") == _REPORT_MANIFEST_SCHEMA_VERSION
            and isinstance(reports, list)
            and isinstance(payload.get("count"), int)
            and not isinstance(payload.get("count"), bool)
            and payload["count"] == len(reports)
        )
        legacy_static_manifest = _is_legacy_static_manifest(payload)
        if not isinstance(reports, list):
            continue

        for report in reports:
            if not isinstance(report, dict):
                continue
            rel_path = _report_manifest_relative_path(prefix, report)
            if rel_path is None:
                continue
            if legacy_static_manifest:
                rows[rel_path] = _legacy_static_report_metadata(report)
                continue
            if not manifest_valid:
                rows[rel_path] = _failed_report_metadata("manifest_schema_invalid", report)
                continue

            expected_hash = report.get("content_sha256")
            expected_bytes = report.get("bytes")
            if (
                report.get("schema_version") != _REPORT_MANIFEST_SCHEMA_VERSION
                or not isinstance(expected_hash, str)
                or _REPORT_SHA256_RE.fullmatch(expected_hash.lower()) is None
                or not isinstance(expected_bytes, int)
                or isinstance(expected_bytes, bool)
                or expected_bytes < 0
            ):
                rows[rel_path] = _failed_report_metadata("report_schema_invalid", report)
                continue

            full = _safe_report_path(rel_path)
            if full is None:
                continue
            digest = hashlib.sha256()
            actual_bytes = 0
            try:
                with open(full, "rb") as handle:
                    for chunk in iter(lambda: handle.read(64 * 1024), b""):
                        actual_bytes += len(chunk)
                        digest.update(chunk)
            except OSError:
                rows[rel_path] = _failed_report_metadata("report_unreadable", report)
                continue
            if actual_bytes != expected_bytes:
                rows[rel_path] = _failed_report_metadata("bytes_mismatch", report)
                continue
            if digest.hexdigest() != expected_hash.lower():
                rows[rel_path] = _failed_report_metadata("content_sha256_mismatch", report)
                continue

            rows[rel_path] = {
                "registered": True,
                "integrity_status": "verified",
                "catalog_classification": "canonical_registered",
                "catalog_reason": "manifest_schema_and_content_verified",
                **{
                    key: report.get(key)
                    for key in (
                        "schema_version", "report_id", "report_type", "research_id",
                        "run_id", "generation", "cycle", "status", "publication_status", "generator",
                        "content_sha256", "source_sha256", "trust", "provenance", "toc",
                        "profile", "evidence", "decision", "limitations",
                        "renderer_version", "template_id", "theme",
                    )
                    if report.get(key) is not None
                },
            }
    return rows


def _report_catalog() -> list[Dict[str, Any]]:
    """Build a bounded cached catalog and enrich verified registered reports from manifests."""
    root = _reports_root_abs()
    now = time.monotonic()
    with _REPORT_CATALOG_CACHE_LOCK:
        cached = _REPORT_CATALOG_CACHE.get(root)
        if cached is not None and now - cached[0] < _REPORT_CATALOG_TTL_SECONDS:
            return [dict(item) for item in cached[1]]

        metadata = _report_manifest_rows(root)
        items: list[Dict[str, Any]] = []
        for base, _dirs, files in os.walk(root):
            for filename in files:
                if not filename.lower().endswith(".html"):
                    continue
                rel = os.path.relpath(os.path.join(base, filename), root).replace(os.sep, "/")
                full = _safe_report_path(rel)
                if full is None:
                    continue
                try:
                    stat = os.stat(full)
                except OSError:
                    continue
                item: Dict[str, Any] = {
                    "path": rel,
                    "name": filename,
                    "bytes": stat.st_size,
                    "mtime": int(stat.st_mtime),
                    "registered": False,
                    "integrity_status": "unregistered",
                    "catalog_classification": "legacy_static",
                    "catalog_reason": "no_manifest_registration",
                }
                item.update(metadata.get(rel, {}))
                items.append(item)
        items.sort(key=lambda item: item["path"])
        _REPORT_CATALOG_CACHE[root] = (now, items)
        return [dict(item) for item in items]

_DASHBOARD_FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<circle cx='32' cy='32' r='28' fill='#081624'/>"
    "<circle cx='32' cy='32' r='16' fill='#0fb5ff'/>"
    "</svg>"
)

# `?v=<hash>` 지문이 붙은 정적 자산(.js/.css)에 far-future immutable 캐시를 부여한다.
#   webui-build 가 내용 변경마다 ?v= 해시를 갱신하므로(내용 주소화) 지문 응답은 안전하게
#   장기 캐시가 가능하다. Starlette StaticFiles 기본값은 Cache-Control 을 안 붙여, 2.3MB
#   정적 자산(app.js 2MB 포함)이 매 로드 재검증/재다운로드되던 '크롬 느림'의 주원인이었다.
#   지문 없는 요청과 .html 은 no-store 로 남겨 셸 HTML(핸들러가 직접 no-store 서빙)과 정합.
# 지문 형식: 빌드가 발행하는 v 값(8자리 hex 해시 또는 date+alnum, 예: 998fd305 / 20260624u002).
#   6자 이상 영숫자·._- 조합만 지문으로 인정한다(빈 값·짧은 값·다른 파라미터 부분매칭 배제).
_FINGERPRINT_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{5,}$")


def _is_fingerprint_query(query: bytes) -> bool:
    try:
        params = parse_qs(query.decode("latin-1"))
    except Exception:  # noqa: BLE001
        return False
    values = params.get("v") or []
    return bool(values and values[0] and _FINGERPRINT_RE.match(values[0]))


class _FingerprintedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:  # type: ignore[override]
        response = await super().get_response(path, scope)
        try:
            lower = path.lower()
            query = scope.get("query_string", b"") or b""
            # §1e(검토): b"v=" in query 는 rev=·prev= 등 부분매칭까지 immutable 로 만든다.
            #   query 를 정확히 파싱해 비어있지 않은 지문 형식의 v 파라미터만 지문으로 인정한다.
            fingerprinted = _is_fingerprint_query(query)
            if lower.endswith(".html"):
                response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            elif fingerprinted and (lower.endswith(".js") or lower.endswith(".css")):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif lower.endswith(".js") or lower.endswith(".css") or lower.endswith(".jsx"):
                # §3.4: 지문(?v=) 없는 JS/CSS/JSX 는 내용 주소화가 안 돼 장기 캐시가 위험하다 →
                #   no-store 로 명시(주석·문서 계약과 코드를 일치시킨다).
                response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
        except Exception:  # noqa: BLE001 - 캐시 헤더 부여 실패가 정적 서빙을 막지 않는다.
            pass
        return response

# 폴링 주기(초) — current_state.json 변경 감지 → WS push.
_POLL_INTERVAL = 1.0

# W1-A 이후: CORS allowlist 미들웨어는 제거됨. DashboardSecurity.authorize_http 의
#   strict same-origin(Origin == 서빙 host) 검사가 cross-origin 요청을 4403/403 으로
#   차단하므로 CORS allowlist 는 무효(vestigial)였다. same-origin 브라우저 요청은
#   CORS 헤더 없이도 동일 출처 정책으로 허용된다.
_PROMPT_HEAD_CHARS = 240


class LoopProcessManager:
    """루프 서브프로세스 핸들을 in-process로 관리하는 단순 매니저.

    한 번에 하나의 루프만 추적한다(MVP). start는 STOP 플래그를 먼저 지우고
    `python -m ai_strategy_loop.controller.loop --config-json <...>` 를 띄운다.
    """

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """루프를 서브프로세스로 기동한다. 이미 running이면 거부.

        P6 — 대시보드가 추적하는 자식(is_running)뿐 아니라, **cross-process 락**도
        확인한다. LoopProcessManager는 이 대시보드 인스턴스 한정 보호라, 다른
        진입점(CLI 또는 다른 대시보드 프로세스)이 이미 루프를 돌리는 경우를 못 본다.
        runlock.is_locked()로 그 경우까지 막아 같은 state/DB 동시 쓰기를 차단한다.
        실제 락 획득/해제는 자식 run_loop가 소유한다(여기선 사전 거부만).
        """
        if self.is_running():
            return {"status": "error", "message": "loop already running"}

        # cross-process 락: 살아있는 다른 루프(CLI/타 GUI)가 보유 중이면 거부.
        from ai_strategy_loop.controller.runlock import is_locked  # noqa: PLC0415

        if is_locked():
            return {
                "status": "error",
                "message": "다른 루프가 실행 중입니다(cross-process 락 보유). 동시 실행 차단.",
            }

        # 설정 검증 (CLI=GUI 동일 경로). 잘못된 값이면 여기서 막는다.
        try:
            cfg = config_from_dict(config_dict)
        except ValueError as exc:
            return {"status": "error", "message": f"invalid config: {exc}"}

        # 기동 전 잔여 STOP 플래그 제거 (즉시 정지 방지).
        S.clear_stop_flag()

        env = dict(os.environ)
        env.setdefault("STOM_ALLOW_MINIMAL_SETTING", "1")
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable, "-m", "ai_strategy_loop.controller.loop",
            "--config-json", json.dumps(cfg.to_dict(), ensure_ascii=False),
        ]
        self._proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env)
        return {"status": "ok", "pid": self._proc.pid}

    def stop(self, *, grace: float = 10.0) -> Dict[str, Any]:
        """STOP 플래그를 써서 깔끔한 종료를 요청하고, 안 멈추면 강제 종료한다.

        1) STOP 플래그를 쓴다(루프가 세대 시작 전 관측 → 깔끔히 종료).
        2) grace 동안 자식이 스스로 끝나길 기다린다.
        3) 여전히 살아 있으면 hard_stop()으로 terminate→kill→reap 해서
           오펀 백테스트를 남기지 않는다.
        """
        path = S.set_stop_flag()
        reaped = self.hard_stop(grace=grace)
        return {"status": "ok", "stop_flag": path, "reaped": reaped}

    def hard_stop(self, *, grace: float = 10.0) -> bool:
        """실행 중인 자식을 terminate→(grace 대기)→kill→wait 로 강제 회수한다.

        오펀 방지: 서버 종료/강제 정지 시 자식 백테스트가 남지 않도록 반드시
        wait()으로 좀비를 reap 한다. 추적 중인 자식이 없거나 이미 종료됐으면
        조용히 False를 반환한다(회수할 것 없음). 회수했으면 True.
        """
        proc = self._proc
        if proc is None:
            return False
        if proc.poll() is not None:
            self._proc = None
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except OSError:
            # 이미 죽었거나 회수 불가 — 그래도 핸들은 비워 다음 start를 허용한다.
            pass
        self._proc = None
        return True


def _current_state_payload() -> Dict[str, Any]:
    """current_state.json을 읽어 dict로 반환하고 dashboard-only telemetry를 병합한다."""
    raw = S.read_current_state()
    if raw is not None:
        try:
            payload = _with_observability_defaults(C.LoopState.model_validate(raw).model_dump())
        except ValidationError:
            payload = raw
    else:
        payload = C.idle_state().model_dump()
    return attach_telemetry_to_status(payload, dashboard_telemetry().snapshot())


def _with_observability_defaults(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fill dashboard-only observability fields for legacy current_state snapshots."""
    latest = payload.get("latest")
    if not isinstance(latest, dict):
        return payload

    active_config_raw = payload.get("active_config")
    active_config = dict(active_config_raw) if isinstance(active_config_raw, dict) else {}
    try:
        config = config_from_dict(active_config)
    except ValueError:
        config = config_from_dict({})

    status = str(payload.get("status") or "")
    raw_current_gen = payload.get("current_gen")
    try:
        current_gen = int(raw_current_gen) if raw_current_gen is not None else -1
    except (TypeError, ValueError):
        current_gen = -1
    max_generations = int(payload.get("max_generations") or 0)
    phase = str(latest.get("phase") or "")
    bt_timeframe = str(payload.get("bt_timeframe") or getattr(config, "bt_timeframe", "") or "")

    latest["backtest_progress"] = build_backtest_progress(
        config=config,
        latest=latest,
        status=status,
        current_gen=current_gen,
        max_generations=max_generations,
        phase=phase,
        phase_started_at=float(latest.get("phase_started_at") or 0.0),
        bt_timeframe=bt_timeframe,
        now=time.time(),
    )
    latest["engine_state"] = build_engine_state(
        config=config,
        latest=latest,
        active_config=active_config,
        status=status,
        current_gen=current_gen,
        phase=phase,
    )
    return payload


def _runs_payload(run_ids: Optional[list]) -> Dict[str, Any]:
    """loop_runs.db를 열어 run 비교 요약을 만든다(읽기 전용, 무예외).

    lineage.compare_runs를 호출하고 LoopState 연결을 반드시 닫는다. DB 부재/조회
    실패는 빈 목록으로 표준화한다(대시보드 콘솔이 깨지지 않게).
    """
    from ai_strategy_loop.controller.lineage import compare_runs  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        result = compare_runs(st, run_ids)
        _attach_run_labels(result)
        # 2026-06-11 — 최신 우선 + (최근 48h 내) running 최상단. 종전 오름차순은
        #   당일 작업 13개가 132개 목록 맨 뒤에 묻혀 "운영 중인 게 안 보이는"
        #   문제를 냈다. 48h 컷: 과거 세션 중단으로 running이 박제된 좀비 run이
        #   상단을 점유하지 않게 한다(실가동 myr2~5 사례).
        if isinstance(result.get("runs"), list):
            _now = time.time()
            result["runs"].sort(
                key=lambda r: (
                    0 if (r.get("status") == "running"
                          and (r.get("started_at") or 0) > _now - 48 * 3600) else 1,
                    -(r.get("started_at") or 0.0),
                )
            )
        return result
    except Exception as exc:  # noqa: BLE001 - run 비교 조회 실패는 빈 목록으로.
        return {"runs": [], "count": 0, "error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

def _runs_slim_payload() -> Dict[str, Any]:
    """Return run summaries with two readonly queries and no full comparison payload."""

    from collections import defaultdict
    from ai_strategy_loop.controller import lineage  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        runs = st.list_runs()
        generation_columns = _slim_generation_columns(st)
        grouped: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
        if generation_columns:
            sql = (
                "SELECT run_id, " + ", ".join(generation_columns)
                + " FROM generations ORDER BY run_id, gen_no"
            )
            for row in st._con.execute(sql).fetchall():
                data = dict(row)
                grouped[str(data.pop("run_id"))].append(data)

        summaries: list[Dict[str, Any]] = []
        generation_count = 0
        for run in runs:
            run_id = run["run_id"]
            generations = grouped.get(run_id, [])
            generation_count += len(generations)
            summary = lineage._summarize_run(run_id, run, generations)
            labels: list[str] = []
            for generation in generations:
                gist = generation.get("strategy_gist")
                if isinstance(gist, str) and gist and gist not in labels:
                    labels.append(gist)
            if labels:
                summary["label"] = labels[0]
                summary["labels"] = labels[:8]
            # v5.13.2 — 사람이 읽는 이름 조각(날짜·시각·타임프레임·목적). 구 run_id 도
            #   runs.started_at 으로 시각을 채워 "언제 시작했는지"가 항상 나온다.
            try:
                from ai_strategy_loop.controller.run_naming import describe_run_id  # noqa: PLC0415

                summary["naming"] = describe_run_id(
                    run_id, started_at=run.get("started_at"),
                    timeframe=summary.get("timeframe"))
            except Exception:  # noqa: BLE001 - 표기 보조값 실패가 목록을 막지 않는다.
                pass
            summaries.append(summary)
        result: Dict[str, Any] = {
            "runs": summaries,
            "count": len(summaries),
            "generation_count": generation_count,
        }
        _sort_runs_by_recency(result)
        return result
    except Exception as exc:  # noqa: BLE001 - preserve the full endpoint's unavailable envelope.
        return {"runs": [], "count": 0, "error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass


def _slim_generation_columns(state: Any) -> list[str] | None:
    connection = getattr(state, "_con", None)
    if connection is None:
        return None
    wanted = (
        "gen_no", "score", "gate_passed", "buy_name", "sell_name", "mdd", "profit",
        "trade_count", "total_profit_pct", "daily_avg_trades", "max_hold_count",
        "payoff_ratio", "created_at", "strategy_gist",
    )
    available = {
        row["name"] for row in connection.execute("PRAGMA table_info(generations)").fetchall()
    }
    return [column for column in wanted if column in available]



def _sort_runs_by_recency(result: Dict[str, Any]) -> None:
    runs = result.get("runs")
    if not isinstance(runs, list):
        return
    now = time.time()
    runs.sort(
        key=lambda row: (
            0 if (row.get("status") == "running"
                  and (row.get("started_at") or 0) > now - 48 * 3600) else 1,
            -(row.get("started_at") or 0.0),
        )
    )


def _attach_run_labels(result: Dict[str, Any]) -> None:
    """D5 — run 목록에 대표 라벨(strategy_gist)을 덧붙인다(읽기 전용·무예외).

    배치 평가 run(예: cldgen_*)은 세대 라벨(BASE_SEED/C7_SEEDPLUS …)이 정체성이다.
    run별 첫 비어있지 않은 gist를 label로, 고유 gist 목록(최대 8)을 labels로 노출한다.
    실패는 조용히 무시한다(라벨은 장식 — 기존 응답 키 불변).
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    runs = result.get("runs") if isinstance(result, dict) else None
    if not runs:
        return
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        try:
            rows = con.execute(
                "SELECT run_id, strategy_gist FROM generations"
                " WHERE strategy_gist IS NOT NULL AND strategy_gist != ''"
                " ORDER BY gen_no"
            ).fetchall()
        finally:
            con.close()
        first_gist: Dict[str, str] = {}
        gists: Dict[str, list] = {}
        for rid, gist in rows:
            first_gist.setdefault(rid, gist)
            bucket = gists.setdefault(rid, [])
            if gist not in bucket:
                bucket.append(gist)
        for row in runs:
            rid = row.get("run_id")
            if rid in first_gist:
                row["label"] = first_gist[rid]
                row["labels"] = gists[rid][:8]
    except Exception:  # noqa: BLE001 - 라벨 실패해도 목록은 그대로.
        return


def _row_for_gen(run_id: str, gen_no: int) -> Optional[Dict[str, Any]]:
    """run/gen 한 행(csv_path 포함)을 dict로 읽는다(읽기 전용, 실패 None)."""
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            row = con.execute(
                "SELECT gen_no, status, score, gate_passed, reason, profit,"
                " total_profit_pct, mdd, trade_count, daily_avg_trades, payoff_ratio,"
                " max_hold_count, buy_name, sell_name, csv_path, strategy_gist"
                " FROM generations WHERE run_id=? AND gen_no=?",
                (run_id, int(gen_no)),
            ).fetchone()
        finally:
            con.close()
        return dict(row) if row is not None else None
    except Exception:  # noqa: BLE001
        return None


def _yearly_detail_from_csv(csv_path: str) -> list:
    """per-trade CSV에서 연도별 {year, trades, profit, win_rate}를 만든다(graceful)."""
    try:
        import pandas as pd  # noqa: PLC0415

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "매수시간" not in df.columns or "수익금" not in df.columns:
            return []
        years = df["매수시간"].astype(str).str[:4]
        result = []
        for year, group in df.groupby(years):
            profits = group["수익금"].astype(float)
            wins = (group["수익률"].astype(float) > 0) if "수익률" in df.columns else (profits > 0)
            result.append({
                "year": str(year),
                "trades": int(len(group)),
                "profit": float(profits.sum()),
                "win_rate": round(float(wins.mean()), 4),
            })
        return result
    except Exception:  # noqa: BLE001
        return []


def _run_yearly_payload(run_id: str) -> Dict[str, Any]:
    """D1 — run의 세대별 연도 분해(거래수·손익·승률)를 만든다(읽기 전용·무예외).

    근거(2026-06-10 원인5): 시드 알파의 연도별 쇠퇴(+4.88M→+3.37M→+0.38M→2026 적자)는
    합계만 봐서는 보이지 않는다. generations.csv_path의 per-trade CSV(매수시간·수익금·
    수익률)를 연도로 집계한다 — 추가 백테 0회. CSV 부재/파싱 실패는 빈 분해로 표준화.
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    out: Dict[str, Any] = {"run_id": run_id, "generations": [], "count": 0}
    if not run_id:
        return out
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT gen_no, status, buy_name, strategy_gist, csv_path, profit,"
                " trade_count FROM generations WHERE run_id=? ORDER BY gen_no",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out

    for row in rows:
        d = dict(row)
        entry: Dict[str, Any] = {
            "gen_no": d["gen_no"],
            "buy_name": d.get("buy_name"),
            "label": d.get("strategy_gist") or "",
            "status": d.get("status"),
            "total_profit": d.get("profit"),
            "trade_count": d.get("trade_count"),
            "years": _yearly_detail_from_csv(d.get("csv_path") or "") if d.get("csv_path") else [],
        }
        out["generations"].append(entry)
    out["count"] = len(out["generations"])
    return out


def _autopsy_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """D2 — 세대 CSV에 공식 부검(진입/청산)을 적용해 NL 요약을 반환한다(읽기 전용·무예외).

    autopsy.analyze_trades/analyze_exits + summarize — 루프가 프롬프트 환류로만 쓰던
    분석을 사람이 대시보드에서 직접 본다("왜 졌는지"). 실패/부족은 status로 표준화.
    """
    out: Dict[str, Any] = {
        "run_id": run_id, "gen_no": gen_no,
        "entry_summary": "", "exit_summary": "", "status": "unavailable",
    }
    row = _row_for_gen(run_id, gen_no)
    if row is None:
        return out
    out["buy_name"] = row.get("buy_name")
    out["label"] = row.get("strategy_gist") or ""
    csv_path = row.get("csv_path") or ""
    if not csv_path:
        out["status"] = "no_csv"
        return out
    try:
        from ai_strategy_loop.autopsy.analyze import analyze_exits, analyze_trades  # noqa: PLC0415
        from ai_strategy_loop.autopsy.summarize import summarize, summarize_exits  # noqa: PLC0415

        entry = analyze_trades(csv_path)
        exits = analyze_exits(csv_path)
        out["entry_summary"] = summarize(entry) or ""
        out["exit_summary"] = summarize_exits(exits) or ""
        out["entry_status"] = getattr(entry, "status", "")
        out["exit_status"] = getattr(exits, "status", "")
        out["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def _trade_quant_payload(run_id: str, gen_no: int, fine_time: bool, top_n: int) -> Dict[str, Any]:
    """G3 — per-trade CSV의 정량 지표 자연어 요약을 반환한다(읽기 전용·무예외).

    gen_no<0이면 run_id의 최신 ok 세대(csv_path 보유)를 쓴다(_portfolio_sim_payload와
    동일 관례). ai_strategy_loop.autopsy.trade_quant.analyze_trade_table을 지연
    import해 호출한다 — 모듈이 아직 없거나 import/분석이 실패해도 예외를 던지지
    않고 status="error"로 흡수한다.
    """
    out: Dict[str, Any] = {
        "run_id": run_id, "gen_no": gen_no,
        "contract_version": C.CONTRACT_VERSION,
        "status": "unavailable", "trade_count": 0, "metrics": {}, "nl_lines": [],
    }
    if not run_id:
        out["error"] = "run_id required"
        return out

    csv_path = ""
    label = ""
    try:
        if gen_no is not None and int(gen_no) >= 0:
            row = _row_for_gen(run_id, int(gen_no))
            if row is not None:
                csv_path = row.get("csv_path") or ""
                label = row.get("strategy_gist") or ""
        else:
            con = sqlite3.connect(str(S.LOOP_RUNS_DB))
            con.row_factory = sqlite3.Row
            try:
                row = con.execute(
                    "SELECT gen_no, strategy_gist, csv_path"
                    " FROM generations"
                    " WHERE run_id=? AND status='ok' AND csv_path IS NOT NULL AND csv_path != ''"
                    " ORDER BY gen_no DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
            finally:
                con.close()
            if row is not None:
                out["gen_no"] = row["gen_no"]
                csv_path = str(row["csv_path"] or "")
                label = str(row["strategy_gist"] or "")
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패는 error로 흡수(무예외).
        out["status"] = "error"
        out["error"] = str(exc)
        return out

    if not csv_path:
        out["status"] = "no_csv"
        return out

    out["label"] = label
    abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        from ai_strategy_loop.autopsy.trade_quant import analyze_trade_table  # noqa: PLC0415

        result = analyze_trade_table(abs_csv, fine_time=bool(fine_time), top_n=int(top_n))
        out.update(result or {})
    except Exception as exc:  # noqa: BLE001 - 모듈 부재/분석 실패도 error로 흡수(무예외).
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def _research_maturity_payload() -> Dict[str, Any]:
    """G005 — 연구 프로그램 단계별 성숙도 스코어카드를 즉석 계산한다(읽기 전용·무예외).

    scripts.research_maturity_scorecard.build_scorecard을 지연 import해 호출한다(모듈이
    아직 없거나 계산이 실패해도 예외를 던지지 않고 status="error"로 흡수한다). state
    캐시를 두지 않고 매 호출 재계산한다 — 값이 저장소 파일/상태 DB 변화를 즉시 반영한다.
    """
    try:
        from scripts.research_maturity_scorecard import build_scorecard  # noqa: PLC0415

        return build_scorecard(REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 - 모듈 부재/계산 실패도 error로 흡수(무예외).
        return {"schema": "research_maturity_v1", "status": "error", "error": str(exc)}


def _selector_preview_payload(run_id: str, selector: str) -> Dict[str, Any]:
    """D4 — run 행에 선택기를 진단 적용해 동결 가능 후보를 미리 본다(읽기 전용·무예외).

    근거(2026-06-10 원인1): 기준-목표 비정합(시드조차 탈락)을 눈으로 확인하는 도구.
    sparse_positive_v1 | seed_relative_v1 지원. 베이스라인(BASE_*)은 후보에서 출처
    기준으로 제외하되 seed_relative의 시드 프로파일로 쓴다. **진단 전용 — 아무것도
    쓰지 않으며 동결 아티팩트가 아니다.**
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    out: Dict[str, Any] = {
        "run_id": run_id, "selector": selector or "sparse_positive_v1",
        "diagnostic_only": True, "selected": False, "eligible": [], "rejected": [],
    }
    if not run_id:
        return out
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT gen_no, status, score, gate_passed, reason, profit,"
                " total_profit_pct, mdd, trade_count, daily_avg_trades, payoff_ratio,"
                " max_hold_count, buy_name, sell_name, csv_path, strategy_gist"
                " FROM generations WHERE run_id=? ORDER BY gen_no",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out

    try:
        from ai_strategy_loop.controller.candidate_selection import (  # noqa: PLC0415
            SeedProfile,
            parse_candidate_generation,
            select_seed_relative_v1,
            select_sparse_positive_v1,
        )

        candidates, labels = [], {}
        seed_profile = None
        for r in rows:
            d = dict(r)
            gist = d.pop("strategy_gist", "") or ""
            labels[int(d.get("gen_no") or 0)] = gist
            d["gate_passed"] = bool(d.get("gate_passed"))
            for k in ("payoff_ratio", "max_hold_count", "profit", "mdd",
                      "daily_avg_trades", "score"):
                if d.get(k) is None:
                    d[k] = 0.0
            if d.get("csv_path") is None:
                d["csv_path"] = ""
            if gist == "BASE_SEED" and seed_profile is None and d.get("status") == "ok":
                seed_profile = SeedProfile(
                    mdd=float(d["mdd"]), trade_count=int(d["trade_count"]),
                    profit=float(d["profit"]), source=f"BASE_SEED of {run_id}",
                )
            if gist.startswith("BASE_"):
                continue
            candidates.append(parse_candidate_generation(d))

        if (selector or "") == "seed_relative_v1":
            res = select_seed_relative_v1(
                candidates, run_id=run_id, config_path="", config_hash="",
                seed_profile=seed_profile, diagnostic_only=True,
            )
            out["selector"] = "seed_relative_v1"
            out["mdd_limit"] = res.mdd_limit
            out["seed_profile"] = (
                {"mdd": seed_profile.mdd, "trade_count": seed_profile.trade_count}
                if seed_profile else None
            )
        else:
            out["selector"] = "sparse_positive_v1"
            res = select_sparse_positive_v1(
                candidates, run_id=run_id, config_path="", config_hash="",
                diagnostic_only=True,
            )
        out["selected"] = bool(res.selected)
        if res.selected_candidate is not None:
            c = res.selected_candidate
            out["selected_candidate"] = {
                "gen_no": c.gen_no, "label": labels.get(c.gen_no, ""),
                "buy_name": c.buy_name, "sell_name": c.sell_name,
                "profit": c.profit, "mdd": c.mdd, "trade_count": c.trade_count,
                "payoff_ratio": c.payoff_ratio,
            }
        out["eligible"] = [
            {"gen_no": e.gen_no, "label": labels.get(e.gen_no, "")}
            for e in res.eligible_candidates
        ]
        out["rejected"] = [
            {"gen_no": rj.gen_no, "label": labels.get(rj.gen_no, ""),
             "reasons": list(rj.reasons)}
            for rj in res.rejected_candidates
        ]
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    return out


def _generation_durations_payload(run_id: Optional[str] = None) -> Dict[str, Any]:
    """세대별 소요초를 인접 created_at 차분으로 산출한다(#64, 읽기 전용·무예외).

    generations.created_at은 각 세대 *종료* 시각(record_generation 시 _now())이 영속된다.
    따라서 gen[i] 소요 = created_at[i] - created_at[i-1]. 첫 세대(i=0)는 이전 세대가 없으니
    runs.started_at(run 시작 시각)으로 보정해 created_at[0] - started_at를 쓴다. 이 방식은
    추가 백테 0회이고, LIVE 발행이 없던 과거 run(예: reframe1)에도 retroactive하게 작동한다
    (DB에 이미 created_at/started_at가 있으므로).

    run_id가 주어지면 그 run만, 없으면 모든 run을 산출한다. DB 부재/조회 실패/이상치는
    빈 목록·None으로 표준화한다(무예외 — 대시보드가 깨지지 않게). 음수 차(시계 역행/UPSERT
    재기록)는 None으로 둔다(잘못된 소요 표시 방지).

    반환: {"durations": [{"run_id","gen_no","duration_sec","created_at","status"}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        all_gens = st.get_all_generations()
        runs = {r.get("run_id"): r for r in st.list_runs()}
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"durations": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # run별로 gen_no 순 그룹핑(인접 차분을 같은 run 안에서만 계산).
    by_run: Dict[str, list] = {}
    for g in all_gens:
        rid = g.get("run_id")
        if run_id and rid != run_id:
            continue
        by_run.setdefault(rid, []).append(g)

    run_context: Dict[str, Dict[str, Any]] = {}
    for rid, row in runs.items():
        cfg_json = (row or {}).get("config_json")
        cfg: Dict[str, Any] = {}
        if cfg_json:
            try:
                parsed = json.loads(str(cfg_json))
                if isinstance(parsed, dict):
                    cfg = parsed
            except (ValueError, TypeError):
                cfg = {}
        run_context[rid] = {
            "period": _period_string_from_config(cfg_json),
            "timeframe": cfg.get("bt_timeframe"),
        }

    durations: list = []
    for rid, gens in by_run.items():
        gens_sorted = sorted(gens, key=lambda g: int(g.get("gen_no", 0) or 0))
        started_at = (runs.get(rid) or {}).get("started_at")
        prev_created = float(started_at) if started_at is not None else None
        for g in gens_sorted:
            created = g.get("created_at")
            duration_sec: Optional[float] = None
            if created is not None and prev_created is not None:
                delta = float(created) - float(prev_created)
                # 음수(시계 역행/재기록)는 None으로 — 잘못된 소요 표시 방지.
                duration_sec = delta if delta >= 0.0 else None
            # gen_no는 0이 유효값이므로 `or -1`(0을 falsy로 떨구는 버그) 금지 — None만 -1.
            _gen_no = g.get("gen_no")
            durations.append({
                "run_id": rid,
                "gen_no": (-1 if _gen_no is None else int(_gen_no)),
                "duration_sec": duration_sec,
                "created_at": (None if created is None else float(created)),
                "status": str(g.get("status", "") or ""),
                **run_context.get(rid, {}),
            })
            if created is not None:
                prev_created = float(created)

    return {"durations": durations, "count": len(durations)}


def _equity_curves_payload(
    cap: int = 200, downsample: int = 200, run_id: Optional[str] = None
) -> Dict[str, Any]:
    """loop_runs.db의 세대 equity curve를 읽어 반환한다(읽기 전용, 무예외).

    run_id가 주어지면 그 run의 세대만 반환한다 — 전체 이력에는 과발화 폭망 곡선
    (±수십억)이 섞여 있어, 그것까지 한 차트에 그리면 정상 곡선이 y스케일에 압착돼
    0선에 한 줄처럼 뭉개진다. 현재 보고 있는 run만 보내면 스케일이 정상화된다.
    run_id 미지정이면 전체(하위호환).

    각 세대의 csv_path로 load_equity_series_from_csv를 호출해 수익금합계 시계열을
    얻는다. 곡선이 많으면 최근 cap 개로 제한하고, 곡선당 포인트는 downsample 개로
    줄인다. CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 응답(무예외).

    반환: {"curves": [{"run_id","gen_no","gate_passed","final_pct","equity":[...]}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.score import load_equity_series_from_csv  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        all_gens = st.get_all_generations()
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"curves": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # created_at 내림차순(최신 우선).
    sorted_gens = sorted(all_gens, key=lambda g: g.get("created_at") or 0, reverse=True)
    # run_id가 주어지면 해당 run만(현재 보고 있는 run의 곡선만 정상 스케일로 표시).
    if run_id:
        sorted_gens = [g for g in sorted_gens if g.get("run_id") == run_id]
    candidates = sorted_gens[:cap]

    curves = []
    for g in candidates:
        csv_path = g.get("csv_path")
        if not csv_path:
            continue
        try:
            equity_raw = load_equity_series_from_csv(str(csv_path))
        except Exception:  # noqa: BLE001 - CSV 없거나 파싱 실패는 skip.
            continue
        if not equity_raw:
            continue
        # 다운샘플: 포인트 수가 downsample 초과면 균등 간격으로 추려 payload 축소.
        if len(equity_raw) > downsample:
            step = len(equity_raw) / downsample
            equity_ds = [equity_raw[int(i * step)] for i in range(downsample)]
            equity_ds.append(equity_raw[-1])  # 마지막 값 보존.
        else:
            equity_ds = equity_raw
        curves.append({
            "run_id": g.get("run_id", ""),
            "gen_no": int(g.get("gen_no", -1)),
            "gate_passed": bool(g.get("gate_passed")),
            "final_pct": float(g.get("total_profit_pct") or 0.0),
            "equity": [float(v) for v in equity_ds],
        })

    return {"curves": curves, "count": len(curves)}


_REFERENCE_STRATEGIES_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reference_strategies.json"
)

# 인간 reference 결과 스크린샷 디렉토리(REPO_ROOT 기준). 읽기 전용으로 /reference_img에
#   StaticFiles 마운트하고, /reference_screenshots가 이 디렉토리의 이미지 파일명을 나열한다.
#   이 디렉토리만 노출하며(다른 디렉토리 노출 금지) 디렉토리가 없으면 마운트를 스킵한다.
_REFERENCE_SCREENSHOTS_DIR = os.path.join(REPO_ROOT, "docs", "reference", "STOM_Good_Results")

# 갤러리에 표시할 이미지 확장자. 결과 스크린샷은 .png 17장이 정본이다. 같은 #1의
#   .jpg/.jpeg 중복 포맷 변환본은 동일 화면이라 갤러리 노이즈가 되므로 .png만 노출한다
#   (StaticFiles 마운트 자체는 디렉토리 전체를 읽기 전용 서빙하므로 직접 URL 접근엔 영향 없음).
_SCREENSHOT_EXTS = (".png",)


def _reference_screenshots() -> list:
    """인간 reference 결과 스크린샷 파일명 목록을 반환한다(읽기 전용, 무예외).

    _REFERENCE_SCREENSHOTS_DIR의 최상위(서브디렉토리 미탐색) .png 결과 스크린샷만 나열한다.
    분석용 파생 크롭/줌(언더스코어 `_`로 시작하는 보조 파일: `_zoom_*`, `_crops` 등)은
    실제 결과 스크린샷이 아니므로 제외한다. #1의 .jpg/.jpeg 중복 포맷본도 .png 정본과
    같은 화면이라 제외해(확장자 화이트리스트=.png) 갤러리가 결과 화면 17장만 브라우징하게 한다.
    파일명만(경로 제외) 정렬해 돌려준다 — 프론트가 baseUrl+'/reference_img/'+filename으로
    StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록으로 표준화한다(무예외).
    """
    try:
        entries = os.listdir(_REFERENCE_SCREENSHOTS_DIR)
    except OSError:
        return []
    out = []
    for name in entries:
        if name.startswith("_"):
            continue  # 분석용 파생 크롭/줌(보조 파일) 제외 — 결과 스크린샷만.
        if not name.lower().endswith(_SCREENSHOT_EXTS):
            continue
        try:
            full = os.path.join(_REFERENCE_SCREENSHOTS_DIR, name)
            if not os.path.isfile(full):
                continue  # 서브디렉토리(_crops 등)는 제외.
        except OSError:
            continue
        out.append(name)
    return sorted(out)


def _load_reference_strategies() -> list:
    """reference_strategies.json을 읽어 인간 벤치마크 목록을 반환한다(읽기 전용, 무예외).

    파일은 이 모듈 기준 dashboard/reference_strategies.json. 파일 부재/JSON 파싱
    실패는 빈 목록으로 표준화한다(대시보드가 빈 상태를 표시). 각 항목을 명예의
    전당 공통 스키마(label·total_return_krw·total_return_pct·annual_return_pct·
    mdd_pct·payoff·trades·daily_avg_trades·max_holdings·operating_capital_krw·
    kind='human')로 매핑한다.
    """
    try:
        with open(_REFERENCE_STRATEGIES_JSON, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []

    strategies = (raw or {}).get("strategies") or []
    out: list = []
    for s in strategies:
        if not isinstance(s, dict):
            continue
        out.append({
            "kind": "human",
            "label": str(s.get("id") or ""),
            "period": s.get("period"),
            "days": s.get("days"),
            "operating_capital_krw": s.get("operating_capital_krw"),
            "total_return_krw": s.get("profit_krw"),
            "total_return_pct": s.get("total_return_pct"),
            "annual_return_pct": s.get("annual_return_pct"),
            "annual_unreliable": False,
            "mdd_pct": s.get("mdd_pct"),
            "payoff": s.get("payoff"),
            "trades": s.get("trades"),
            "daily_avg_trades": s.get("daily_avg_trades"),
            "max_holdings": s.get("max_holdings"),
            "win_rate_pct": s.get("win_rate_pct"),
        })
    return out


def _window_years_from_config(config_json: Optional[str]) -> Optional[float]:
    """runs.config_json의 bt_full_start/bt_full_end(YYYYMMDD 정수)에서 창 길이(년)를 구한다.

    (date(end) − date(start)).days / 365.25. 파싱 실패/필드 부재/비정상 값은 None
    으로 표준화한다(연평균을 산출하지 못함 → 호출부가 None 처리). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    days = (end - start).days
    if days <= 0:
        return None
    return days / 365.25


def _period_string_from_config(config_json: Optional[str]) -> Optional[str]:
    """runs.config_json의 bt_full_start/end(YYYYMMDD 정수)를 'YYYY-MM-DD ~ YYYY-MM-DD'로 포맷한다.

    명예의 전당 '백테 기간' 컬럼용. 인간 전략은 reference_strategies.json의 period 문자열을
    그대로 쓰고, AI 전략은 이 헬퍼로 run 창에서 동일 포맷의 기간 문자열을 만든다.
    파싱 실패/필드 부재/비정상 값(end<=start)은 None으로 표준화한다(컬럼이 '—' 표시). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    if (end - start).days <= 0:
        return None
    return f"{start.isoformat()} ~ {end.isoformat()}"


def _catalog_number(value: Any) -> Optional[float]:
    """Return a stored numeric value without converting missing values to zero."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _catalog_int(value: Any) -> Optional[int]:
    """Return a stored integer value without converting missing values to zero."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _generation_outcome(generation: Dict[str, Any]) -> str:
    """Classify a stored generation result without inventing a performance metric."""
    status = str(generation.get("status") or "").lower()
    trades = _catalog_int(generation.get("trade_count"))
    profit = _catalog_number(generation.get("profit"))
    if status == "unavailable":
        return "unavailable"
    if trades == 0:
        return "no_trade"
    if status in {"failed", "failure", "error"}:
        return "failure"
    if profit is not None and profit < 0:
        return "loss"
    if status in {"ok", "success", "complete", "completed"}:
        return "success"
    return "unknown"


def _hall_catalog_payload(
    *,
    limit: int = 50,
    offset: int = 0,
    sort: str = "score",
    order: str = "desc",
    statuses: Optional[set[str]] = None,
    gates: Optional[set[str]] = None,
    outcomes: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """Return a bounded, deterministic, read-only AI generation catalog."""
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    sort_fields = {
        "score": "score",
        "returns": "return_pct",
        "return_pct": "return_pct",
        "return_krw": "return_krw",
        "mdd": "mdd_pct",
        "mdd_pct": "mdd_pct",
        "trades": "trades",
        "gen_no": "gen_no",
    }
    sort_field = sort_fields.get(sort, "score")
    descending = order != "asc"
    bounded_limit = min(max(int(limit), 1), 100)
    bounded_offset = max(int(offset), 0)

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        generations = st.get_all_generations()
        # One run-list read supplies metadata for every generation; never per-row get_run().
        runs = {str(row.get("run_id")): row for row in st.list_runs() if row.get("run_id") is not None}
    except Exception:  # noqa: BLE001 - absent/unreadable DB is an empty read-only catalog.
        return {"items": [], "total": 0, "returned": 0, "next": None}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    items: list[Dict[str, Any]] = []
    for generation in generations:
        run_id_value = generation.get("run_id")
        run_id = str(run_id_value) if run_id_value is not None else None
        run = runs.get(run_id or "")
        gate_raw = generation.get("gate_passed")
        gate_passed = None if gate_raw is None else bool(gate_raw)
        status = generation.get("status")
        outcome = _generation_outcome(generation)
        if statuses and str(status or "").lower() not in statuses:
            continue
        if gates:
            gate_filter = "passed" if gate_passed is True else "failed" if gate_passed is False else "unknown"
            if gate_filter not in gates:
                continue
        if outcomes and outcome not in outcomes:
            continue

        config_json = run.get("config_json") if run else None
        period = _period_string_from_config(config_json)
        window_years = _window_years_from_config(config_json)
        return_krw = _catalog_number(generation.get("profit"))
        return_pct = _catalog_number(generation.get("total_profit_pct"))
        operating_capital = (
            return_krw / return_pct * 100.0
            if return_krw is not None and return_pct not in (None, 0)
            else None
        )
        annual_return_pct = (
            return_pct / window_years
            if return_pct is not None and window_years is not None and window_years > 0
            else None
        )
        items.append({
            "kind": "seed" if (
                generation.get("buy_name") and not str(generation.get("buy_name")).startswith("AILOOP")
            ) else "ai",
            "run_id": run_id,
            "gen_no": _catalog_int(generation.get("gen_no")),
            "label": f"{run_id}/g{generation.get('gen_no')}" if run_id is not None else None,
            "status": status,
            "gate_passed": gate_passed,
            "outcome": outcome,
            "score": _catalog_number(generation.get("score")),
            "return_krw": return_krw,
            "return_pct": return_pct,
            "operating_capital_krw": operating_capital,
            "annual_return_pct": annual_return_pct,
            "annual_unreliable": bool(window_years is not None and window_years < 0.25),
            "profit": _catalog_number(generation.get("profit")),
            "total_profit_pct": _catalog_number(generation.get("total_profit_pct")),
            "mdd": _catalog_number(generation.get("mdd")),
            "mdd_pct": _catalog_number(generation.get("mdd")),
            "trade_count": _catalog_int(generation.get("trade_count")),
            "trades": _catalog_int(generation.get("trade_count")),
            "period": period,
            "window_years": window_years,
            "calmar": _catalog_number(generation.get("calmar")),
            "payoff": _catalog_number(generation.get("payoff_ratio")),
            "daily_avg_trades": _catalog_number(generation.get("daily_avg_trades")),
            "max_hold_count": _catalog_number(generation.get("max_hold_count")),
            "win_rate_pct": _catalog_number(generation.get("win_rate_pct", generation.get("win_rate"))),
            "buy_name": generation.get("buy_name"),
            "sell_name": generation.get("sell_name"),
            "reason": generation.get("reason"),
            "provenance": {
                "source": "loop_runs.db",
                "generation_created_at": generation.get("created_at"),
                "run_status": run.get("status") if run else None,
                "run_started_at": run.get("started_at") if run else None,
                "run_finished_at": run.get("finished_at") if run else None,
            },
        })

    def sort_key(item: Dict[str, Any]) -> tuple[Any, ...]:
        value = item.get(sort_field)
        missing = value is None
        if isinstance(value, (int, float)) and descending:
            value = -value
        return (missing, value, str(item.get("run_id") or ""), item.get("gen_no") if item.get("gen_no") is not None else -1)

    items.sort(key=sort_key)
    total = len(items)
    page = items[bounded_offset:bounded_offset + bounded_limit]
    next_offset = bounded_offset + len(page)
    return {
        "items": page,
        "total": total,
        "returned": len(page),
        "next": next_offset if next_offset < total else None,
    }


def _hall_of_fame_payload(ai_limit: int = 30) -> Dict[str, Any]:
    """Legacy Hall payload: human benchmark plus the historical profitable AI subset."""
    human = _load_reference_strategies()
    catalog = _hall_catalog_payload(limit=100, sort="score", order="desc", gates={"passed"})
    ai: list[Dict[str, Any]] = []
    for item in catalog["items"]:
        profit = item["return_krw"]
        total_pct = item["return_pct"]
        if profit is None or total_pct is None or profit <= 0 or total_pct <= 0:
            continue
        run_id = item["run_id"] or ""
        annual_pct = None
        annual_unreliable = False
        # Legacy annualization remains based on the stored configured backtest window.
        years = item.get("window_years")
        if isinstance(years, (int, float)) and years > 0:
            annual_pct = total_pct / years
            annual_unreliable = years < 0.25
        ai.append({
            "kind": item["kind"],
            "run_id": run_id,
            "gen_no": item["gen_no"],
            "label": item["label"],
            "period": item["period"],
            "buy_name": item["buy_name"],
            "score": item["score"],
            "operating_capital_krw": profit / total_pct * 100.0,
            "total_return_krw": profit,
            "total_return_pct": total_pct,
            "annual_return_pct": annual_pct,
            "annual_unreliable": annual_unreliable,
            "mdd_pct": item["mdd_pct"],
            "calmar": item["calmar"],
            "payoff": item["payoff"],
            "trades": item["trades"],
            "daily_avg_trades": item["daily_avg_trades"],
            "max_hold_count": item["max_hold_count"],
        })
    return {"human": human, "ai": ai[:max(0, int(ai_limit))]}


def _strategy_code_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """루프 DB에서 한 세대의 매수/매도 전략 코드를 조회한다(읽기 전용, 무예외).

    P10 — 대시보드 코드 뷰어가 fetch 한다. 세대 행(generations)의 실제 buy_name/
    sell_name을 먼저 읽어(시드 세대는 seed 이름, 일반 세대는 AILOOP_<run>_g<gen>_*),
    그 이름으로 loop.py의 _read_strategy_code(stockbuy/stocksell의 "전략코드")를
    재사용해 코드를 가져온다. 행이 없으면 namespaced 기본 이름으로 폴백한다.

    조회 실패/미존재는 빈 문자열로 표준화한다(대시보드가 "코드가 없습니다"를 표시).
    """
    from ai_strategy_loop.controller.loop import _read_strategy_code  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    buy_name = f"AILOOP_{run_id}_g{gen_no}_buy"
    sell_name = f"AILOOP_{run_id}_g{gen_no}_sell"
    generation_found = False
    # 세대 행에서 실제 전략 이름을 읽는다(시드 세대는 seed 이름일 수 있음).
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                generation_found = True
                buy_name = row.get("buy_name") or buy_name
                sell_name = row.get("sell_name") or sell_name
                break
    except Exception:  # noqa: BLE001 - 행 조회 실패는 namespaced 기본 이름으로 폴백.
        pass
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    buy_code = _read_strategy_code(buy_name, "buy") or ""
    sell_code = _read_strategy_code(sell_name, "sell") or ""
    code_status = "ok"
    reason: Optional[str] = None
    if not buy_code and not sell_code:
        if not generation_found:
            code_status = "missing_generation"
            reason = "missing_generation"
        else:
            code_status = "empty_code"
            reason = "empty_code"
    return {
        "ok": True,
        "run_id": run_id,
        "gen": int(gen_no),
        "gen_no": int(gen_no),
        "buy_name": buy_name,
        "sell_name": sell_name,
        "buy_code": buy_code,
        "sell_code": sell_code,
        "code_status": code_status,
        "reason": reason,
    }


def _prompt_row_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 행을 해시/메타데이터 + 제한된 user head로 변환한다."""
    user_text = str(row.get("user_text") or "")
    features_raw = row.get("injected_features")
    injected_features = None
    if features_raw:
        try:
            injected_features = json.loads(str(features_raw))
        except (ValueError, TypeError):
            injected_features = None
    return {
        "prompt_id": row.get("prompt_id"),
        "run_id": row.get("run_id"),
        "gen_no": row.get("gen_no"),
        "kind": row.get("kind"),
        "attempt": row.get("attempt"),
        "system_sha": row.get("system_sha"),
        "user_sha": row.get("user_sha"),
        "user_text_head": user_text[:_PROMPT_HEAD_CHARS],
        "user_text_len": len(user_text),
        "injected_features": injected_features,
        "prior_error": row.get("prior_error"),
        "model": row.get("model"),
        "prompt_tokens": row.get("prompt_tokens"),
        "completion_tokens": row.get("completion_tokens"),
        "total_tokens": row.get("total_tokens"),
        "response_sha": row.get("response_sha"),
        "created_at": row.get("created_at"),
    }


def _prompts_payload(run_id: Optional[str], gen_no: Optional[int] = None) -> Dict[str, Any]:
    """저장된 프롬프트를 조회한다. 전문 대신 head/hash만 반환한다."""
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required", "prompts": []}
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        rows = st.get_prompts(run_id)
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc), "run_id": run_id, "gen_no": gen_no, "prompts": []}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if gen_no is not None:
        rows = [row for row in rows if int(row.get("gen_no", -1)) == int(gen_no)]
    prompts = [_prompt_row_payload(row) for row in rows]
    reason = None if prompts else "prompt_logging_not_enabled_or_no_records"
    return {"run_id": run_id, "gen_no": gen_no, "prompts": prompts, "reason": reason}


def _diff_lines(base_code: str, code: str, base_name: str, name: str) -> List[str]:
    """매수/매도 전략 코드 두 버전의 unified diff line 배열을 만든다."""
    if not base_code and not code:
        return []
    return list(difflib.unified_diff(
        (base_code or "").splitlines(),
        (code or "").splitlines(),
        fromfile=base_name or "base",
        tofile=name or "current",
        lineterm="",
    ))


def _parse_base_gen(gen_no: int, base_gen: str) -> Optional[int]:
    """base_gen 쿼리를 해석한다. gen0의 previous는 base 없음."""
    if base_gen == "previous":
        return int(gen_no) - 1 if int(gen_no) > 0 else None
    try:
        return int(base_gen)
    except (TypeError, ValueError):
        return None


def _strategy_diff_payload(
    run_id: Optional[str], gen_no: int, base_gen: str = "previous"
) -> Dict[str, Any]:
    """현재 세대와 base 세대의 매수/매도 코드와 diff를 반환한다."""
    if not run_id:
        return {"error": "run_id required", "prompts": []}

    current = _strategy_code_payload(run_id, int(gen_no))
    base_no = _parse_base_gen(int(gen_no), str(base_gen))
    prompts = _prompts_payload(run_id, int(gen_no)).get("prompts", [])
    current_status = str(current.get("code_status") or "")
    if current_status == "missing_generation":
        return {
            "ok": True,
            "run_id": run_id,
            "gen_no": int(gen_no),
            "buy_name": current.get("buy_name"),
            "sell_name": current.get("sell_name"),
            "buy_code": current.get("buy_code", ""),
            "sell_code": current.get("sell_code", ""),
            "base_gen": base_no,
            "base_buy_name": None,
            "base_sell_name": None,
            "base_buy_code": "",
            "base_sell_code": "",
            "buy_diff": [],
            "sell_diff": [],
            "prompts": prompts,
            "diff_status": "missing_generation",
            "reason": "missing_generation",
        }
    if base_no is None:
        return {
            "ok": True,
            "run_id": run_id,
            "gen_no": int(gen_no),
            "buy_name": current.get("buy_name"),
            "sell_name": current.get("sell_name"),
            "buy_code": current.get("buy_code", ""),
            "sell_code": current.get("sell_code", ""),
            "base_gen": None,
            "base_buy_name": None,
            "base_sell_name": None,
            "base_buy_code": "",
            "base_sell_code": "",
            "buy_diff": [],
            "sell_diff": [],
            "prompts": prompts,
            "diff_status": "no_previous_generation",
            "reason": "no_previous_generation",
        }

    base = _strategy_code_payload(run_id, int(base_no))
    base_status = str(base.get("code_status") or "")
    diff_status = "ok"
    reason: Optional[str] = None
    if current_status == "empty_code" or base_status == "empty_code":
        diff_status = "empty_code"
        reason = "empty_code"
    elif base_status == "missing_generation":
        diff_status = "missing_generation"
        reason = "missing_generation"
    return {
        "ok": True,
        "run_id": run_id,
        "gen_no": int(gen_no),
        "buy_name": current.get("buy_name"),
        "sell_name": current.get("sell_name"),
        "buy_code": current.get("buy_code", ""),
        "sell_code": current.get("sell_code", ""),
        "base_gen": int(base_no),
        "base_buy_name": base.get("buy_name"),
        "base_sell_name": base.get("sell_name"),
        "base_buy_code": base.get("buy_code", ""),
        "base_sell_code": base.get("sell_code", ""),
        "buy_diff": _diff_lines(
            str(base.get("buy_code") or ""),
            str(current.get("buy_code") or ""),
            str(base.get("buy_name") or ""),
            str(current.get("buy_name") or ""),
        ),
        "sell_diff": _diff_lines(
            str(base.get("sell_code") or ""),
            str(current.get("sell_code") or ""),
            str(base.get("sell_name") or ""),
            str(current.get("sell_name") or ""),
        ),
        "prompts": prompts,
        "diff_status": diff_status,
        "reason": reason,
    }


def _p5_verdict_note() -> str:
    """Return the latest honest OOS verdict note without exposing arbitrary files."""
    path = os.path.join(
        REPO_ROOT, ".omo", "evidence", "tick-oos-validation-20260603", "p5-decision-card.md"
    )
    try:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return "Previous OOS verdict unavailable; do not infer promotion."
    if "Final Verdict: REJECT_CANDIDATE" in text:
        return "Final Verdict: REJECT_CANDIDATE; prior candidate remains rejected."
    return "Previous OOS verdict file exists but no promotion verdict was found."


def _ai_context_pack_payload(run_id: Optional[str], gen_no: Optional[int] = None) -> Dict[str, Any]:
    """Build a deterministic, copyable research-state pack for an external AI agent.

    This is read-only and intentionally excludes prompt bodies, code bodies, secrets,
    environment values, production DB paths, and any network call.
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required"}

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        run_row = st.get_run(run_id)
        gens = st.get_generations(run_id)
        prompt_rows = st.get_prompts(run_id)
    except Exception as exc:  # noqa: BLE001 - context pack must be non-crashing.
        return {"error": str(exc), "run_id": run_id}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not gens:
        return {"error": "run_not_found_or_empty", "run_id": run_id}

    def _row_gen_no(row: Dict[str, Any]) -> int:
        try:
            return int(row.get("gen_no", -1))
        except (TypeError, ValueError):
            return -1

    selected_gen = int(gen_no) if gen_no is not None and int(gen_no) >= 0 else _row_gen_no(gens[-1])
    gen = next((g for g in gens if _row_gen_no(g) == selected_gen), gens[-1])
    cfg_json = (run_row or {}).get("config_json")
    cfg: Dict[str, Any] = {}
    if cfg_json:
        try:
            cfg = json.loads(str(cfg_json))
        except (ValueError, TypeError):
            cfg = {}
    period = _period_string_from_config(cfg_json)
    timeframe = cfg.get("bt_timeframe")
    gen_no_out = _row_gen_no(gen)
    gen_prompts = [p for p in prompt_rows if _row_gen_no(p) == gen_no_out]
    best = max(gens, key=lambda row: float(row.get("score", 0.0) or 0.0))
    winners = [g for g in gens if bool(g.get("gate_passed"))]
    winner = max(winners, key=lambda row: float(row.get("score", 0.0) or 0.0)) if winners else None
    strategy_names = {"buy": gen.get("buy_name"), "sell": gen.get("sell_name")}

    def _prompt_features(row: Dict[str, Any]) -> Dict[str, Any]:
        raw = row.get("injected_features")
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    prompt_feature_rows = [_prompt_features(p) for p in gen_prompts]
    first_features = next((f for f in prompt_feature_rows if f), {})
    context_pack = {
        "guide_context": {
            "source": "utility/ai_agent/system_prompt/v1",
            "prompt_count": len(gen_prompts),
            "prompt_logging_enabled": bool(cfg.get("prompt_logging_enabled")),
            "injected": first_features.get("guide_context"),
        },
        "diff_context": {
            "selected_gen_no": gen_no_out,
            "comparison_base_gen_no": gen_no_out - 1 if gen_no_out > 0 else None,
            "has_current_strategy_names": bool(strategy_names["buy"] or strategy_names["sell"]),
            "injected": first_features.get("diff_context"),
        },
        "analysis_context": {
            "best_gen_no": int(best.get("gen_no", -1) or -1),
            "winner_gen_no": (
                None if winner is None else int(winner.get("gen_no", -1) or -1)
            ),
            "score": gen.get("score"),
            "profit": gen.get("profit"),
            "injected": first_features.get("analysis_context"),
        },
        "correlation_context": {
            "source_route": "/variable_correlation",
            "per_trade_csv_available": bool(gen.get("csv_path")),
            "injected": first_features.get("correlation_context"),
        },
    }

    forbidden_actions = [
        "Do not approve, deploy, or write production strategy storage from this context.",
        "Do not place live orders or advance V3K gates.",
        "Do not claim human-level or seed-superior performance without fresh OOS evidence.",
    ]
    verdict_note = _p5_verdict_note()
    analysis = {
        "edge_ratio": "available via /edge_ratio when per-trade CSVs exist",
        "feature_importance": "available via /feature_importance when per-trade CSVs exist",
        "variable_correlation": "available via /variable_correlation when per-trade CSVs exist",
        "wiki": "available via /research_docs and /research_doc",
    }
    summary_lines = [
        "STOM AI condition research state",
        f"run_id: {run_id}",
        f"gen_no: {gen_no_out}",
        f"timeframe: {timeframe or '-'}",
        f"period: {period or '-'}",
        f"strategy_buy: {strategy_names['buy'] or '-'}",
        f"strategy_sell: {strategy_names['sell'] or '-'}",
        f"graded_score: {gen.get('score')}",
        f"profit: {gen.get('profit')}",
        f"return_pct: {gen.get('total_profit_pct')}",
        f"prompt_count: {len(gen_prompts)}",
        f"verdict: {verdict_note}",
        "forbidden: " + " | ".join(forbidden_actions),
    ]
    return {
        "run_id": run_id,
        "gen_no": gen_no_out,
        "timeframe": timeframe,
        "period": period,
        "config": {
            "provider": cfg.get("provider"),
            "bt_timeframe": cfg.get("bt_timeframe"),
            "bt_full_start": cfg.get("bt_full_start"),
            "bt_full_end": cfg.get("bt_full_end"),
            "bt_universe_start_time": cfg.get("bt_universe_start_time"),
            "bt_universe_end_time": cfg.get("bt_universe_end_time"),
        },
        "latest_logs": {
            "run_status": (run_row or {}).get("status"),
            "started_at": (run_row or {}).get("started_at"),
            "finished_at": (run_row or {}).get("finished_at"),
            "generation_count": len(gens),
        },
        "best": {
            "gen_no": int(best.get("gen_no", -1) or -1),
            "graded_score": best.get("score"),
            "profit": best.get("profit"),
        },
        "winner": (
            None if winner is None else {
                "gen_no": int(winner.get("gen_no", -1) or -1),
                "graded_score": winner.get("score"),
                "profit": winner.get("profit"),
            }
        ),
        "strategy_names": strategy_names,
        "prompt_count": len(gen_prompts),
        "context_pack": context_pack,
        "analysis": analysis,
        "verdict_note": verdict_note,
        "verdict_refs": [
            ".omo/evidence/tick-oos-validation-20260603/p5-decision-card.md",
            ".omo/evidence/tick-research-dashboard-upgrade-20260603/",
        ],
        "forbidden_actions": forbidden_actions,
        "summary_text": "\n".join(summary_lines),
    }


def _run_state_payload(run_id: str) -> Dict[str, Any]:
    """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성한다(읽기 전용·무예외).

    #65 P0 — run 셀렉터용. 대시보드 라이브 상태(current_state.json)는 한 번에 하나의
    run만 보여주고, 에이전트 테스트가 합성 run('segrun')을 그 파일에 쓰면 화면이 오염된다.
    이 엔드포인트는 loop_runs.db의 runs+generations에서 임의 run을 통째로 재구성하므로,
    사용자가 라이브 오염과 무관하게 실제 run(reframe1 등)을 골라 브라우징할 수 있다.

    재구성:
      - generations 행을 읽어 summary(best/winner)를 만든다.
          best   = graded(score) 최고 세대.
          winner = 하드게이트 통과 세대 중 score 최고(없으면 None).
        이는 lineage._summarize_run의 우승 선택 규칙과 동일하나, to_loop_state가
        소비하는 평탄 키(best_gen/best_score/best_buy/best_sell, winner_*)로 만든다.
      - runs.config_json에서 LoopConfig를 복원해 provider/bt_timeframe/active_config를 채운다.
      - runs.status와 실제 마지막 gen_no를 보존해 정적 DB 스냅샷으로 빌드한다.

    DB 부재/없는 run/조회 실패는 idle_state로 표준화한다(무예외 — 대시보드가 빈 상태 표시).
    엔진/하드게이트/CSV 무수정. 추가 백테 0회(DB 조회만).
    """
    from ai_strategy_loop.config import LoopConfig  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState, to_loop_state  # noqa: PLC0415

    if not run_id:
        return C.idle_state().model_dump()

    st: Optional[LoopState] = None
    run_row: Optional[Dict[str, Any]] = None
    gens: list = []
    try:
        st = LoopState(readonly=True)
        run_row = st.get_run(run_id)
        gens = st.get_generations(run_id)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 idle(무예외).
        return C.idle_state().model_dump()
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # 없는 run(행도 세대도 없음) → idle(무예외 계약).
    if run_row is None and not gens:
        return C.idle_state().model_dump()

    # config_json에서 LoopConfig 복원(provider/bt_timeframe/active_config 채움). 실패는 None.
    cfg: Any = None
    cfg_json = (run_row or {}).get("config_json")
    if cfg_json:
        try:
            cfg = LoopConfig.from_dict(json.loads(cfg_json))
        except (ValueError, TypeError):
            cfg = None

    # best = graded(score) 최고 세대(점수 None은 제외). 동률은 gen_no 큰 쪽(최신).
    best_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if g.get("score") is None:
            continue
        if best_row is None or float(g.get("score") or 0.0) >= float(best_row.get("score") or 0.0):
            best_row = g
    # winner = 하드게이트 통과 세대 중 score 최고(없으면 None). 동률은 gen_no 큰 쪽.
    winner_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if not bool(g.get("gate_passed")):
            continue
        if winner_row is None or float(g.get("score") or 0.0) >= float(winner_row.get("score") or 0.0):
            winner_row = g

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "best_gen": (int(best_row.get("gen_no", -1)) if best_row is not None else -1),
        "best_score": (float(best_row.get("score")) if best_row and best_row.get("score") is not None else None),
        "best_buy": (best_row.get("buy_name") if best_row is not None else None),
        "best_sell": (best_row.get("sell_name") if best_row is not None else None),
        "winner_gen": (int(winner_row.get("gen_no", -1)) if winner_row is not None else -1),
        "winner_score": (
            float(winner_row.get("score")) if winner_row and winner_row.get("score") is not None else None
        ),
        "winner_buy": (winner_row.get("buy_name") if winner_row is not None else None),
        "winner_sell": (winner_row.get("sell_name") if winner_row is not None else None),
    }

    try:
        run_status = str((run_row or {}).get("status") or "complete")
        current_gen = max((int(g.get("gen_no", -1)) for g in gens), default=-1)
        snapshot = to_loop_state(
            summary, gens, config=cfg, status=run_status, current_gen=current_gen,
        ).model_dump()
        persisted_times = [
            value
            for value in (
                (run_row or {}).get("started_at"),
                (run_row or {}).get("finished_at"),
                *(g.get("created_at") for g in gens),
            )
            if value is not None
        ]
        snapshot["updated_at"] = max((float(value) for value in persisted_times), default=0.0)
        return snapshot
    except Exception:  # noqa: BLE001 - 빌드 실패도 idle로 표준화(무예외 계약).
        return C.idle_state().model_dump()


def _backtest_detail_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(읽기 전용, 무예외).

    O1 — 대시보드 BacktestDetailChart가 fetch 한다. 일반 STOM 백테가 만드는 2-그래프
    (일별손익 막대 + 누적수익곡선)를 헤드리스 루프 결과로 재현한다. 엔진 PNG 생성은
    꺼져 있으나(cli/runner.py) per-trade 거래 CSV는 항상 생성되므로, 이미 있는 그 CSV
    하나를 O2의 parse_backtest_series로 시계열 변환한다(추가 백테 0회).

    세대 행(generations)에서 (run_id, gen_no)의 csv_path·gate_passed·daily_avg_trades를
    조회하고, 그 run의 config_json에서 bt_betting을 뽑아 누적%(cum_pct) 산출에 쓴다.
    csv_path가 상대경로면 REPO_ROOT 기준으로 해석해 서버 CWD와 무관하게 동작한다.

    csv 없음/파싱 실패/없는 세대는 빈 시계열(daily=[]·summary 0)로 표준화한다(무예외).

    반환:
      {"run_id","gen_no","gate_passed",
       "daily":[{date,daily_pnl,profit,loss,net}...],
       "cumulative":[{date,cum_profit,cum_pct}...],
       "drawdown":[{date,drawdown}...],
       "holdings":[{t_index,count}...],   # 동시보유 종목수(이벤트/시각축, STOM fig2 상단 대응)
       "summary":{trade_count,final_profit,max_drawdown,n_days,peak_holdings}}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.equity_series import parse_backtest_series  # noqa: PLC0415

    empty_series: Dict[str, Any] = {
        "daily": [],
        "cumulative": [],
        "drawdown": [],
        "holdings": [],
        "summary": {
            "trade_count": 0,
            "final_profit": 0.0,
            "max_drawdown": 0.0,
            "n_days": 0,
            "peak_holdings": 0,
        },
    }

    # 세대 행에서 csv_path·gate_passed 조회 + run config_json에서 bt_betting 추출.
    csv_path: Optional[str] = None
    gate_passed = False
    betting = None
    found = False
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                csv_path = row.get("csv_path")
                gate_passed = bool(row.get("gate_passed"))
                found = True
                break
        # bt_betting은 runs.config_json(JSON 문자열)에서 뽑는다(cum_pct 산출용).
        if found:
            run_row = st.get_run(run_id)
            if run_row is not None:
                try:
                    cfg = json.loads(run_row.get("config_json") or "{}")
                    betting = cfg.get("bt_betting")
                except (ValueError, TypeError):
                    betting = None
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": False, **empty_series}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not found or not csv_path:
        # 없는 (run,gen) 또는 csv_path 없는 세대 → 빈 시계열(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": gate_passed, **empty_series}

    # 상대경로면 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작). 파서는 실패 시 빈 구조.
    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    series = parse_backtest_series(resolved, betting=betting)
    return {
        "run_id": run_id,
        "gen_no": int(gen_no),
        "gate_passed": gate_passed,
        "daily": series.get("daily", []),
        "cumulative": series.get("cumulative", []),
        "drawdown": series.get("drawdown", []),
        "holdings": series.get("holdings", []),
        "summary": series.get("summary", empty_series["summary"]),
    }


def _adaptive_timing_payload(run_id: Optional[str], lookback: int) -> Dict[str, Any]:
    """run의 gen0(또는 첫 gate_passed) 전략 CSV에 적응형 타이밍 리포트를 적용한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성 무영향) 오버레이다. loop_runs.db의 generations에서
    그 run의 gen0(가장 낮은 gen_no) 행 csv_path를 찾아 adaptive_timing_report를 돌려준다.
    gen0에 csv_path가 없으면 첫 gate_passed=1 세대의 csv_path로 폴백한다(_backtest_detail
    payload와 동일한 LoopState DB 경로/무예외 패턴).

    run_id 미지정/없는 run/csv_path 없음/파싱 실패는 {"error": ...}로 표준화한다(무예외).
    상대경로 csv_path는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.adaptive_timing import adaptive_timing_report  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required"}

    csv_path: Optional[str] = None
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        rows = st.get_generations(run_id)  # gen_no 오름차순.
        if not rows:
            return {"error": f"no generations for run_id={run_id!r}"}
        # gen0(가장 낮은 gen_no)의 csv_path 우선. 없으면 첫 gate_passed 세대로 폴백.
        first = rows[0]
        csv_path = first.get("csv_path")
        if not csv_path:
            for row in rows:
                if bool(row.get("gate_passed")) and row.get("csv_path"):
                    csv_path = row.get("csv_path")
                    break
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not csv_path:
        return {"error": f"no csv_path for run_id={run_id!r}"}

    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        report = adaptive_timing_report(resolved, lookback)
    except Exception as exc:  # noqa: BLE001 - 리포트 산출 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"run_id": run_id, "lookback": lookback, **report}


def _edge_ratio_payload(
    run_id: Optional[str], run_ids: Optional[str], fine_time: bool,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 MFE/MAE 엣지비율 + 파노라마 세그먼트를 반환한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성/winner 무영향). loop_runs.db의 generations에서
    csv_path를 모은다:
      - run_ids(쉼표구분) 주면 그 모든 run의 **모든 세대** csv_path를 모은다(파노라마 풀).
      - 아니면 run_id 단일 run의 모든 세대 csv_path를 모은다.
    경로는 path로 dedupe하고, 상대경로는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    모은 CSV를 edge_report_from_csvs로 풀링 집계한다(추가 백테 0회).

    run 식별자 미지정/없는 run/세대 없음/조회 실패/풀 비음은 {"error": ...} 또는
    edge_report_from_csvs의 insufficient 결과로 표준화한다(무예외).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.edge_ratio import edge_report_from_csvs  # noqa: PLC0415

    # run_ids(쉼표구분) 우선, 없으면 run_id 단일. 둘 다 없으면 error.
    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    # generations에서 모든 세대 csv_path를 모은다(gate-passed 한정 아님 — 풀을 풍부하게).
    #   경로는 등장 순서를 보존하며 path로 dedupe한다.
    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for rid in target_runs:
            for row in st.get_generations(rid):  # gen_no 오름차순.
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    # 상대경로는 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작).
    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = edge_report_from_csvs(resolved, fine_time=fine_time)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "fine_time": bool(fine_time),
            "gen_no": gen_no, **report}


def _feature_importance_payload(
    run_id: Optional[str], run_ids: Optional[str], axis: str, fine_time: bool,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 세그먼트별 승리-변수 피처 중요도를 반환한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성/winner 무영향). loop_runs.db의 generations에서
    csv_path를 모은다:
      - run_ids(쉼표구분) 주면 그 모든 run의 **모든 세대** csv_path를 모은다(파노라마 풀).
      - 아니면 run_id 단일 run의 모든 세대 csv_path를 모은다.
    경로는 path로 dedupe하고, 상대경로는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    모은 CSV를 feature_importance_from_csvs로 풀링 집계한다(추가 백테 0회). 각 B_* 진입
    피처가 승/패를 가르는 정도(Cohen's d + 분위 승률)를 전역·세그먼트(시총 또는 시간대)별로 낸다.

    run 식별자 미지정/없는 run/세대 없음/조회 실패/풀 비음은 {"error": ...} 또는
    feature_importance_from_csvs의 insufficient 결과로 표준화한다(무예외).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.feature_importance import (  # noqa: PLC0415
        feature_importance_from_csvs,
    )

    # run_ids(쉼표구분) 우선, 없으면 run_id 단일. 둘 다 없으면 error.
    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    # generations에서 모든 세대 csv_path를 모은다(gate-passed 한정 아님 — 풀을 풍부하게).
    #   경로는 등장 순서를 보존하며 path로 dedupe한다.
    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for rid in target_runs:
            for row in st.get_generations(rid):  # gen_no 오름차순.
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    # 상대경로는 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작).
    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = feature_importance_from_csvs(resolved, axis=axis, fine_time=fine_time)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "gen_no": gen_no, **report}


def _variable_correlation_payload(
    run_id: Optional[str], run_ids: Optional[str], method: str,
    gen_no: Optional[int] = None,
) -> Dict[str, Any]:
    """run(들)의 세대 결과 CSV를 풀링해 B_* 변수 상관도를 반환한다(읽기 전용, 무예외)."""
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.correlation import (  # noqa: PLC0415
        variable_correlation_from_csvs,
    )

    if run_ids:
        target_runs = [s.strip() for s in run_ids.split(",") if s.strip()]
    elif run_id:
        target_runs = [run_id]
    else:
        target_runs = []
    if not target_runs:
        return {"error": "run_id or run_ids required"}

    seen: set = set()
    raw_paths: List[str] = []
    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for rid in target_runs:
            for row in st.get_generations(rid):
                # R4(2026-06-11) — gen_no 지정 시 그 세대만(G3: 이질 전략 혼합 풀링 방지).
                if gen_no is not None and int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                cp = row.get("csv_path")
                if cp and cp not in seen:
                    seen.add(cp)
                    raw_paths.append(str(cp))
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not raw_paths:
        return {"error": f"no csv_path for runs={target_runs!r}"}

    resolved = [
        p if os.path.isabs(p) else os.path.join(REPO_ROOT, p) for p in raw_paths
    ]
    try:
        report = variable_correlation_from_csvs(resolved, method=method)
    except Exception as exc:  # noqa: BLE001 - 풀링 집계 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"runs": target_runs, "gen_no": gen_no, **report}


def _ops_status_payload(window_hours: int = 24) -> Dict[str, Any]:
    """운영 현황(2026-06-11) — '지금 무엇이 돌고 있고 잘 돌고 있는가' 한 화면.

    - active: status=running run + 마지막 세대 이후 경과초 → 활성/정체 판정
      (한 점 평가 ~30~340초 실측 — 10분 무진행이면 stalled 의심 표시).
    - recent: 최근 window_hours 내 완료 run + 최고 손익/세대 수.
    - walkforward: 최신 aggregate.json의 정책-대-베이스라인 누적.
    - evidence: 증거 디렉토리 최신 파일 5종(신선도 분).
    읽기 전용·무예외 — 어떤 실패도 부분 결과로 흡수한다.
    """
    import glob as _glob  # noqa: PLC0415
    import sqlite3  # noqa: PLC0415
    import time as _time  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    now = _time.time()
    out: Dict[str, Any] = {"now": now, "active": [], "recent": [],
                           "walkforward": None, "evidence": []}
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT r.run_id, r.status, r.started_at, r.finished_at,"
                " (SELECT COUNT(*) FROM generations g WHERE g.run_id=r.run_id) AS gens,"
                " (SELECT MAX(created_at) FROM generations g WHERE g.run_id=r.run_id)"
                "   AS last_gen_at,"
                " (SELECT strategy_gist FROM generations g WHERE g.run_id=r.run_id"
                "   ORDER BY gen_no DESC LIMIT 1) AS last_label,"
                " (SELECT MAX(profit) FROM generations g WHERE g.run_id=r.run_id"
                "   AND g.status='ok') AS best_profit"
                " FROM runs r WHERE r.started_at > ? ORDER BY r.started_at DESC",
                (now - window_hours * 3600,),
            ).fetchall()
        finally:
            con.close()
        for r in rows:
            d = {
                "run_id": r["run_id"], "status": r["status"],
                "gens": int(r["gens"] or 0),
                "last_label": r["last_label"] or "",
                "best_profit": float(r["best_profit"]) if r["best_profit"] is not None else None,
                "elapsed_min": round((now - (r["started_at"] or now)) / 60, 1),
            }
            if r["status"] == "running":
                idle = now - float(r["last_gen_at"] or r["started_at"] or now)
                d["seconds_since_last_gen"] = round(idle)
                d["health"] = "active" if idle < 600 else "stalled?"
                out["active"].append(d)
            else:
                out["recent"].append(d)
    except Exception as exc:  # noqa: BLE001 - 부분 결과 허용.
        out["error_runs"] = str(exc)

    try:  # walk-forward 최신 집계(있으면).
        aggs = sorted(
            _glob.glob(os.path.join(REPO_ROOT, ".omo/evidence/tmap-walkforward",
                                    "*", "aggregate.json")),
            key=os.path.getmtime, reverse=True,
        )
        if aggs:
            with open(aggs[0], encoding="utf-8") as fh:
                agg = json.load(fh)
            out["walkforward"] = {
                "path": os.path.basename(os.path.dirname(aggs[0])),
                "windows_done": sum(1 for w in agg.get("windows", [])
                                    if w.get("status") == "ok"),
                "policy_total": agg.get("policy_total"),
                "baseline_total": agg.get("baseline_total"),
                "age_min": round((now - os.path.getmtime(aggs[0])) / 60, 1),
            }
    except Exception:  # noqa: BLE001
        pass

    try:  # F6(2026-06-11) — 배치 큐 스테이지: 최신 *queue*log* 휴리스틱 파싱.
        qlogs = sorted(
            _glob.glob(os.path.join(REPO_ROOT, ".omo/evidence/tmap-walkforward",
                                    "*queue*log*.txt")),
            key=os.path.getmtime, reverse=True,
        )
        if qlogs:
            import re as _re  # noqa: PLC0415

            with open(qlogs[0], encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            templates = _re.findall(r"template=(\S+)", text)
            out["batch_queue"] = {
                "log": os.path.basename(qlogs[0]),
                "stages_done": text.count("] done"),
                "current_template": templates[-1] if templates else None,
                "age_min": round((now - os.path.getmtime(qlogs[0])) / 60, 1),
            }
    except Exception:  # noqa: BLE001
        pass

    try:  # 증거 신선도 — 두 증거 디렉토리의 최신 파일 5종.
        files = []
        for pattern in (".omo/evidence/tmap-walkforward/*",
                        ".omo/evidence/claude-condition-research-20260610/*"):
            files += [p for p in _glob.glob(os.path.join(REPO_ROOT, pattern))
                      if os.path.isfile(p)]
        files.sort(key=os.path.getmtime, reverse=True)
        out["evidence"] = [
            {"name": os.path.basename(p),
             "age_min": round((now - os.path.getmtime(p)) / 60, 1)}
            for p in files[:5]
        ]
    except Exception:  # noqa: BLE001
        pass
    return out


def _freeze_verdict_payload() -> Dict[str, Any]:
    """검증 결산(2026-06-11) — 동결 후보의 V1~V5+리스크 증거를 한 화면으로.

    증거 JSON(동결·과적합·중복도·플라시보·슬리피지·리스크 advisory)과 OOS
    run(loop_runs.db, 최신 *_oos_<year>* run)을 모아 사람이 읽는 lines와
    경고(alerts)로 합성한다. 파일 부재/스키마 드리프트는 해당 항목만 생략
    (무예외 — 부분 결과). 읽기 전용 · 판정 미사용(advisory 표시 전용).
    """
    base_t = os.path.join(REPO_ROOT, ".omo/evidence/tmap-walkforward")
    base_r = os.path.join(REPO_ROOT, ".omo/evidence/claude-condition-research-20260610")

    def _load(*parts):
        try:
            with open(os.path.join(*parts), encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:  # noqa: BLE001
            return None

    out: Dict[str, Any] = {"lines": [], "alerts": [], "oos_diff_ci": {}}
    lines, alerts = out["lines"], out["alerts"]

    sel = _load(base_r, "p5-selected-candidate.json")
    if sel and sel.get("selected_candidate"):
        c = sel["selected_candidate"]
        out["selected"] = c
        out["selected_run_id"] = sel.get("run_id")
        lines.append(
            f"동결 후보: gen{c.get('gen_no')} {c.get('buy_name')} — train 손익"
            f" {(c.get('profit') or 0):,.0f} · MDD {c.get('mdd')}"
            f" · {c.get('trade_count')}건 · payoff {round(c.get('payoff_ratio') or 0, 2)}"
        )

    ov = _load(base_r, "p5-overfit-advisory.json")
    if ov:
        dsr = (ov.get("dsr") or {}).get("dsr")
        pbo = (ov.get("pbo") or {}).get("pbo")
        mc = ov.get("mc_block_bootstrap") or {}
        pool = ov.get("pool_independence") or {}
        out["overfit"] = {"dsr": dsr, "pbo": pbo, "n_trials": ov.get("n_trials"),
                          "p_positive": mc.get("p_positive"),
                          "pool_independence": pool}
        if dsr is not None:
            lines.append(
                f"V1 과적합: DSR {dsr:.3f} (n_trials {ov.get('n_trials')})"
                f" · PBO {round(pbo, 3) if pbo is not None else '—'}"
                f" · MC P(흑자) {mc.get('p_positive')}"
            )
        if pool.get("pbo_reliability_warning"):
            alerts.append("V1: " + str(pool["pbo_reliability_warning"]))

    # V3 — 최신 고정 OOS run 2개(연도별)에서 FROZEN vs BASE_SEED.
    try:
        import sqlite3  # noqa: PLC0415

        from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            # 2026-06-12 — OOS run을 '현재 동결 후보'에 바인딩: 도전자 기각 후
            #   최신 OOS(기각자 것)가 챔피언 결산에 섞여 표시되던 혼선 수정.
            cand_buy = (out.get("selected") or {}).get("buy_name")
            for year in ("2022", "2026"):
                rid_row = con.execute(
                    "SELECT r.run_id FROM runs r WHERE r.run_id LIKE ?"
                    " AND EXISTS (SELECT 1 FROM generations g"
                    "   WHERE g.run_id = r.run_id AND g.strategy_gist='FROZEN'"
                    "   AND (? IS NULL OR g.buy_name = ?))"
                    " ORDER BY r.started_at DESC LIMIT 1",
                    (f"%oos_{year}%", cand_buy, cand_buy),
                ).fetchone()
                if rid_row is None:
                    continue
                rows = {r["strategy_gist"]: r for r in con.execute(
                    "SELECT strategy_gist, profit, mdd, trade_count, csv_path"
                    " FROM generations WHERE run_id=? AND status='ok'",
                    (rid_row["run_id"],),
                )}
                fz, bs = rows.get("FROZEN"), rows.get("BASE_SEED")
                if fz and bs:
                    out.setdefault("oos", {})[year] = {
                        "frozen_profit": float(fz["profit"] or 0.0),
                        "frozen_mdd": float(fz["mdd"] or 0.0),
                        "frozen_trades": int(fz["trade_count"] or 0),
                        "seed_profit": float(bs["profit"] or 0.0),
                        "seed_mdd": float(bs["mdd"] or 0.0),
                    }
                    lines.append(
                        f"V3 OOS {year}: 후보 {fz['profit']:,.0f}({fz['trade_count']}건"
                        f"·MDD {fz['mdd']:.2f}) vs 시드 {bs['profit']:,.0f}"
                        f"(MDD {bs['mdd']:.2f})"
                    )
                    # C1-OOS (2026-06-12) — 후보 vs 시드 OOS 차이 CI (advisory).
                    # csv_path 부재·daily_pnl_series 실패·oos_diff_ci 실패는 None으로.
                    try:
                        from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
                            daily_pnl_series,
                            oos_diff_ci,
                        )

                        fz_csv = str(fz["csv_path"] or "")
                        bs_csv = str(bs["csv_path"] or "")
                        if fz_csv and bs_csv:
                            fz_abs = fz_csv if os.path.isabs(fz_csv) else os.path.join(REPO_ROOT, fz_csv)
                            bs_abs = bs_csv if os.path.isabs(bs_csv) else os.path.join(REPO_ROOT, bs_csv)
                            fz_series = daily_pnl_series(fz_abs) or {}
                            bs_series = daily_pnl_series(bs_abs) or {}
                            ci = oos_diff_ci(fz_series, bs_series)
                        else:
                            ci = None
                    except Exception:  # noqa: BLE001 - advisory: 어떤 예외도 기존 응답을 깨지 않는다.
                        ci = None
                    out["oos_diff_ci"][year] = ci
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        pass

    pl = _load(base_t, "placebo_position.json")
    if pl and pl.get("position"):
        pos = pl["position"]
        out["placebo"] = pos
        lines.append(
            f"V2 플라시보: 표본 {pos.get('n_placebo')}종 전부 하회"
            if pos.get("exceeds_all")
            else f"V2 플라시보: 백분위 {pos.get('percentile')}"
        )
        lines[-1] += f" — {pos.get('interpretation')}"

    sl = _load(base_t, "theta_slippage_stress.json")
    if sl:
        by_key = {(s.get("tick"), s.get("fee_bps")): s
                  for s in (sl.get("scenarios") or []) if isinstance(s, dict)}
        s1, s2 = by_key.get((1, 0.0)), by_key.get((2, 0.0))
        if s1:
            out["slippage_summary"] = {
                "t1_retention": s1.get("profit_retention_ratio"),
                "t2_retention": (s2 or {}).get("profit_retention_ratio"),
                "t2_profit": (s2 or {}).get("total_profit"),
                "breakeven_tick": s1.get("breakeven_tick"),
            }
            lines.append(
                f"V5 슬리피지(합산 {sl.get('trade_count')}건): 1틱 유지"
                f" {s1.get('profit_retention_ratio', 0) * 100:.0f}%"
                + (f" · 2틱 {s2.get('profit_retention_ratio', 0) * 100:.0f}%" if s2 else "")
                + f" · 손익분기 {round(s1.get('breakeven_tick') or 0, 2)}틱"
            )
        oos26 = _load(base_t, "theta_slippage_oos2026.json")
        if oos26:
            sc = next((s for s in (oos26.get("scenarios") or [])
                       if s.get("tick") == 1 and not s.get("fee_bps")), None)
            if sc and (sc.get("breakeven_tick") or 9) < 2:
                alerts.append(
                    f"V5: 2026 OOS 단독 손익분기 {round(sc['breakeven_tick'], 2)}틱 — 얇은 마진"
                )

    tov = _load(base_r, "p5-trade-overlap.json")
    if tov:
        out["trade_overlap"] = tov
        lines.append(f"M1 중복도: jaccard {tov.get('jaccard')} — {tov.get('interpretation')}")

    ra = _load(base_t, "theta_risk_advisories.json")
    if ra:
        ff = ra.get("fill_fragility_train") or {}
        cb = ra.get("circuit_breaker_train") or {}
        sz = ra.get("sizing_advisory") or {}
        if ff:
            lines.append(
                f"C8 체결: 추격 의존 거래 {round((ff.get('fragile_trade_ratio') or 0) * 100, 1)}%"
                f" · 의존 수익비중 {round((ff.get('fragile_profit_share') or 0) * 100, 1)}%"
            )
        if cb.get("best_rule"):
            lines.append(f"M10 서킷: {cb['best_rule']} → x{cb.get('profit_ratio')}")
        if sz.get("applied_scale"):
            lines.append(f"M11 사이징: 권고 배수 x{sz['applied_scale']}")

    try:  # V4 — 최신 walk-forward 집계(창별 행 포함).
        import glob as _glob  # noqa: PLC0415

        aggs = sorted(
            _glob.glob(os.path.join(base_t, "*", "aggregate.json")),
            key=os.path.getmtime, reverse=True,
        )
        if aggs:
            agg = _load(aggs[0]) or {}
            out["walkforward"] = agg
            done = [w for w in agg.get("windows", []) if w.get("status") == "ok"]
            if done:
                lines.append(
                    f"V4 walk-forward({len(done)}창): 정책 누적"
                    f" {agg.get('policy_total', 0):,.0f} vs 시드"
                    f" {agg.get('baseline_total', 0):,.0f}"
                )
    except Exception:  # noqa: BLE001
        pass

    # ── D2(2026-06-11): PROMOTE 조건 체크리스트 ────────────────────────────
    #   사전선언 p0 §5(V3 4기준) + advisory 기준(V1·V2·V4·V5). 게이트가 아니라
    #   표시 전용 — 'PROMOTE까지 무엇이 남았나'를 한눈에(상태: pass/warn/fail/pending).
    checklist: List[Dict[str, str]] = []

    def _check(item: str, status: str, detail: str = "") -> None:
        checklist.append({"item": item, "status": status, "detail": detail})

    oos = out.get("oos") or {}
    o22, o26 = oos.get("2022"), oos.get("2026")
    if o22 and o26:
        both = o22["frozen_profit"] > 0 and o26["frozen_profit"] > 0
        _check("V3 두 OOS 연도 모두 흑자", "pass" if both else "fail",
               f"2022 {o22['frozen_profit']:,.0f} / 2026 {o26['frozen_profit']:,.0f}")
        cand_sum = o22["frozen_profit"] + o26["frozen_profit"]
        seed_sum = o22["seed_profit"] + o26["seed_profit"]
        _check("V3 합산 후보 ≥ 합산 시드", "pass" if cand_sum >= seed_sum else "fail",
               f"{cand_sum:,.0f} vs {seed_sum:,.0f}")
        cand_mdd = max(o22["frozen_mdd"], o26["frozen_mdd"])
        seed_mdd = max(o22["seed_mdd"], o26["seed_mdd"])
        _check("V3 후보 maxMDD ≤ 시드", "pass" if cand_mdd <= seed_mdd else "fail",
               f"{cand_mdd:.2f} vs {seed_mdd:.2f}")
        trades_ok = o22["frozen_trades"] >= 20 and o26["frozen_trades"] >= 20
        _check("V3 연 20거래", "pass" if trades_ok else "warn",
               f"2022 {o22['frozen_trades']} / 2026 {o26['frozen_trades']}"
               " — 2026 창 2개월 구조 한계(V4 표본으로 보강)")
    else:
        _check("V3 고정 OOS", "pending", "OOS run 미발견")

    ovf = out.get("overfit") or {}
    if ovf.get("dsr") is not None:
        _check("V1 DSR ≥ 0.5 (advisory)", "pass" if ovf["dsr"] >= 0.5 else "warn",
               f"{ovf['dsr']:.3f} (n_trials {ovf.get('n_trials')})")
        if ovf.get("p_positive") is not None:
            _check("V1 MC P(흑자) ≥ 0.95", "pass" if ovf["p_positive"] >= 0.95 else "warn",
                   str(ovf["p_positive"]))
    else:
        _check("V1 과적합 통계", "pending", "")

    plc = out.get("placebo")
    if plc:
        _check("V2 플라시보 전 표본 상회", "pass" if plc.get("exceeds_all") else "fail",
               f"표본 {plc.get('n_placebo')}종 · 백분위 {plc.get('percentile')}")
    else:
        _check("V2 플라시보", "pending", "")

    slp = out.get("slippage_summary")
    if slp:
        t2_pos = (slp.get("t2_profit") or 0) > 0
        _check("V5 합산 2틱 불리에도 흑자", "pass" if t2_pos else "fail",
               f"2틱 유지율 {round((slp.get('t2_retention') or 0) * 100)}%")
        if any("얇은 마진" in a for a in alerts):
            _check("V5 최신 구간 마진", "warn", "2026 단독 손익분기 < 2틱")
    else:
        _check("V5 슬리피지", "pending", "")

    wf = out.get("walkforward") or {}
    if wf.get("windows"):
        ok_w = [w for w in wf["windows"] if w.get("status") == "ok"]
        noninf = (wf.get("policy_total") or 0) >= (wf.get("baseline_total") or 0)
        _check("V4 정책 누적 비열등", "pass" if noninf and ok_w else "fail",
               f"{wf.get('policy_total', 0):,.0f} vs {wf.get('baseline_total', 0):,.0f} ({len(ok_w)}창)")
    else:
        _check("V4 walk-forward", "pending", "")
    out["promote_checklist"] = checklist
    review_state = _current_state_payload()
    winner = (review_state.get("winner") or {})
    selected = out.get("selected")
    selected_matches_winner = (
        isinstance(selected, dict)
        and isinstance(winner, dict)
        and int(selected.get("gen_no", -1)) == int(winner.get("gen", -2))
        and str(out.get("selected_run_id") or "") == str(review_state.get("run_id") or "")
        and str(selected.get("buy_name") or "") == str(winner.get("buy_name") or "")
        and (
            not selected.get("sell_name")
            or str(selected.get("sell_name")) == str(winner.get("sell_name") or "")
        )
    )
    if selected_matches_winner and isinstance(winner.get("candidate_identity"), dict):
        out["candidate_identity"] = dict(winner["candidate_identity"])
    else:
        out["candidate_identity_error"] = "frozen_review_candidate_mismatch"
    return out


def _canonical_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _candidate_identity_from_payload(
    payload: Any,
    *,
    run_id: str,
    gen_no: int,
) -> tuple[Dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "candidate_identity_missing"
    try:
        projection = C.CandidateIdentityV2Projection.model_validate(payload)
        identity = projection.to_identity()
    except (TypeError, ValueError):
        return None, "candidate_identity_invalid"
    if identity.run_id != run_id or identity.gen_no != gen_no:
        return None, "candidate_identity_coordinate_mismatch"
    return identity.to_dict(), None


def _approval_binding_payload(
    review: Dict[str, Any],
    loop_db: Optional[str],
) -> Dict[str, Any]:
    state = _current_state_payload()
    run_id = str(state.get("run_id") or "")
    current_gen = int(state.get("current_gen", -1))
    winner = state.get("winner")
    if state.get("status") != "complete" or not run_id or current_gen < 0:
        return {"available": False, "reason": "current_run_not_complete"}
    if not isinstance(winner, dict):
        return {"available": False, "reason": "server_winner_missing"}
    winner_gen = int(winner.get("gen", -1))
    winner_buy = str(winner.get("buy_name") or "")
    winner_sell = str(winner.get("sell_name") or "")
    generations = state.get("generations") or []
    generation = next(
        (
            row
            for row in generations
            if isinstance(row, dict) and int(row.get("gen_no", -1)) == winner_gen
        ),
        None,
    )
    if not isinstance(generation, dict):
        return {"available": False, "reason": "winner_generation_missing"}
    if not bool(generation.get("gate_passed")) or generation.get("status") != "ok":
        return {"available": False, "reason": "hard_gates_not_passed"}
    if not winner_buy or not winner_sell:
        return {"available": False, "reason": "server_winner_names_missing"}
    winner_identity, winner_identity_error = _candidate_identity_from_payload(
        winner.get("candidate_identity"),
        run_id=run_id,
        gen_no=winner_gen,
    )
    generation_identity, generation_identity_error = _candidate_identity_from_payload(
        generation.get("candidate_identity"),
        run_id=run_id,
        gen_no=winner_gen,
    )
    if (
        winner_identity_error
        or generation_identity_error
        or winner_identity != generation_identity
    ):
        return {
            "available": False,
            "reason": winner_identity_error or generation_identity_error
            or "winner_generation_identity_mismatch",
        }
    review_identity, review_identity_error = _candidate_identity_from_payload(
        review.get("candidate_identity"),
        run_id=run_id,
        gen_no=winner_gen,
    )
    if review_identity_error or review_identity != winner_identity:
        return {
            "available": False,
            "reason": review_identity_error or "review_winner_identity_mismatch",
        }
    checklist = review.get("promote_checklist")
    if not isinstance(checklist, list) or not checklist:
        return {"available": False, "reason": "frozen_review_missing"}
    if any(
        not isinstance(item, dict) or item.get("status") != "pass"
        for item in checklist
    ):
        return {"available": False, "reason": "frozen_review_incomplete"}

    source_db = loop_db
    if source_db is None:
        import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415

        source_db = str(bootstrap.LOOP_DB_STRATEGY)
    from ai_strategy_loop.controller.export import _read_strategy_code  # noqa: PLC0415

    try:
        buy_code = _read_strategy_code(source_db, winner_buy, "buy")
        sell_code = _read_strategy_code(source_db, winner_sell, "sell")
    except (KeyError, sqlite3.Error) as exc:
        return {"available": False, "reason": "winner_code_unavailable", "message": str(exc)}
    if (
        winner_identity is None
        or winner_identity["buy_body_sha256"] != hashlib.sha256(buy_code.encode("utf-8")).hexdigest()
        or winner_identity["sell_body_sha256"] != hashlib.sha256(sell_code.encode("utf-8")).hexdigest()
    ):
        return {"available": False, "reason": "winner_source_identity_mismatch"}

    review_hash = _canonical_hash(review)
    buy_code_hash = hashlib.sha256(buy_code.encode("utf-8")).hexdigest()
    sell_code_hash = hashlib.sha256(sell_code.encode("utf-8")).hexdigest()
    evidence = {
        "run_id": run_id,
        "current_gen": current_gen,
        "winner_gen": winner_gen,
        "winner_buy": winner_buy,
        "winner_sell": winner_sell,
        "winner_score": winner.get("score"),
        "gate_passed": True,
        "review_hash": review_hash,
        "buy_code_hash": buy_code_hash,
        "sell_code_hash": sell_code_hash,
        "candidate_identity": winner_identity,
    }
    result = {
        "available": True,
        **evidence,
        "evidence_hash": _canonical_hash(evidence),
        "candidate_identity_hash": content_sha256(
            C.CandidateIdentityV2.from_dict(winner_identity)
        ),
    }
    return result


def _portfolio_sim_payload(run_ids_str: str) -> Dict[str, Any]:
    """과업2(2026-06-12) — 복수 run의 최신 ok 세대를 균등 가중 결합해 포트폴리오 리포트.

    각 run_id의 최신 ok 세대(csv_path 보유)에서 daily_pnl_series를 구성하고
    portfolio_report를 호출한다. 유효 시리즈 2개 미만이면 portfolio_report의
    {"error": ...}를 그대로 200으로 반환한다(advisory — 판정 미사용).
    읽기 전용·무예외: 모든 예외는 {"error": ...}로 흡수한다.
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    run_ids = [r.strip() for r in run_ids_str.split(",") if r.strip()]
    if not run_ids:
        return {"error": "run_ids 파라미터가 비어 있습니다."}

    try:
        from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: PLC0415
        from ai_strategy_loop.fitness.portfolio import portfolio_report  # noqa: PLC0415

        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        series: Dict[str, Dict[str, float]] = {}
        try:
            for run_id in run_ids:
                # 최신 ok 세대 중 csv_path 보유한 것 1개.
                row = con.execute(
                    "SELECT gen_no, buy_name, strategy_gist, csv_path"
                    " FROM generations"
                    " WHERE run_id=? AND status='ok' AND csv_path IS NOT NULL AND csv_path != ''"
                    " ORDER BY gen_no DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                if row is None:
                    continue
                csv_path = str(row["csv_path"])
                abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
                s = daily_pnl_series(abs_csv)
                if s:
                    label = (
                        str(row["strategy_gist"] or "")
                        or str(row["buy_name"] or "")
                        or run_id
                    )
                    # 같은 run_id를 중복 제출해도 키가 유일하도록 run_id를 접두로.
                    key = f"{run_id}:{label}"
                    series[key] = s
        finally:
            con.close()

        return portfolio_report(series)
    except Exception as exc:  # noqa: BLE001 - advisory: 어떤 예외도 200으로 흡수.
        return {"error": str(exc)}


def _equity_curve_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """E2/D4(2026-06-11) — 세대 누적 수익곡선(일별, ≤240점 다운샘플).

    per-trade CSV의 일별 손익을 누적해 '우상향 그림'을 차트로 직접 렌더할
    데이터를 만든다. 읽기 전용·무예외 — CSV 부재는 no_csv.
    """
    out: Dict[str, Any] = {"run_id": run_id, "gen_no": gen_no, "status": "unavailable"}
    try:
        row = _row_for_gen(run_id, gen_no)
        if row is None:
            return out
        csv_path = row.get("csv_path") or ""
        abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
        if not csv_path or not os.path.isfile(abs_csv):
            out["status"] = "no_csv"
            return out
        from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: PLC0415

        series = daily_pnl_series(abs_csv)
        if not series:
            out["status"] = "no_csv"
            return out
        days = sorted(series)
        cum, total = [], 0.0
        for d in days:
            total += float(series[d])
            cum.append(round(total, 2))
        step = max(1, len(days) // 240)
        idx = list(range(0, len(days), step))
        if idx and idx[-1] != len(days) - 1:
            idx.append(len(days) - 1)
        out.update({
            "status": "ok",
            "days": [days[i] for i in idx],
            "cum": [cum[i] for i in idx],
            "total": round(total, 2),
            "n_days": len(days),
            "label": row.get("strategy_gist") or "",
        })
    except Exception as exc:  # noqa: BLE001
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def _niche_compare_payload(run_ids: str = "") -> Dict[str, Any]:
    """D3(2026-06-11) — 니치 지도 비교: 여러 스윕 run을 한 표에(읽기 전용·무예외).

    run_ids 미지정이면 최근 7일 'tmap%' run 최신 8개를 자동 발굴 — 밤샘 큐의
    신규 니치 4종(exit2·F07·F10·min)을 아침에 나란히 비교하는 용도. run별:
    베이스라인 · 최강 슬롯 고원(1-D) 또는 격자 요약(grid) · 최고 단일점 · 진행.
    """
    import sqlite3  # noqa: PLC0415
    import time as _time  # noqa: PLC0415

    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415
    from ai_strategy_loop.tmap.tendency import grid_summary, summarize_tendency  # noqa: PLC0415

    ids = [s.strip() for s in run_ids.split(",") if s.strip()]
    out: Dict[str, Any] = {"runs": [], "count": 0}
    try:
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            if not ids:
                rows = con.execute(
                    "SELECT run_id FROM runs WHERE run_id LIKE 'tmap%' AND started_at > ?"
                    " ORDER BY started_at DESC LIMIT 8",
                    (_time.time() - 7 * 86400,),
                ).fetchall()
                ids = [r["run_id"] for r in rows]
            # F1(2026-06-11) — 상관 비교 기준: 최신 reeval run의 최고 손익 gen(동결 후보).
            vs_series = None
            try:
                vs_row = con.execute(
                    "SELECT g.csv_path FROM generations g JOIN runs r"
                    " ON g.run_id = r.run_id"
                    " WHERE g.run_id LIKE '%reeval%' AND g.status='ok'"
                    " ORDER BY r.started_at DESC, g.profit DESC LIMIT 1"
                ).fetchone()
                if vs_row and vs_row["csv_path"]:
                    from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
                        daily_pnl_series as _dps,
                    )

                    p = vs_row["csv_path"]
                    vs_series = _dps(p if os.path.isabs(p) else os.path.join(REPO_ROOT, p))
            except Exception:  # noqa: BLE001
                vs_series = None
            for rid in ids:
                entry: Dict[str, Any] = {"run_id": rid}
                try:
                    status = con.execute(
                        "SELECT status FROM runs WHERE run_id=?", (rid,)).fetchone()
                    entry["status"] = status["status"] if status else None
                    agg = con.execute(
                        "SELECT COUNT(*) AS c, MAX(profit) AS best FROM generations"
                        " WHERE run_id=? AND status='ok'", (rid,)).fetchone()
                    entry["gens_ok"] = int(agg["c"] or 0)
                    entry["best_profit"] = (
                        float(agg["best"]) if agg["best"] is not None else None)
                    # F1 — 최고 손익 gen의 CSV로 시간버킷·곡선 형태·동결 상관(advisory).
                    best_row = con.execute(
                        "SELECT csv_path FROM generations WHERE run_id=? AND status='ok'"
                        " ORDER BY profit DESC LIMIT 1", (rid,)).fetchone()
                    csvp = (best_row["csv_path"] or "") if best_row else ""
                    if csvp:
                        abs_csv = csvp if os.path.isabs(csvp) else os.path.join(REPO_ROOT, csvp)
                        buckets = sorted(_entry_time_buckets(abs_csv))
                        if buckets:
                            entry["time_buckets"] = buckets[:4]
                        from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
                            curve_shape_metrics,
                            daily_pnl_series,
                        )

                        series = daily_pnl_series(abs_csv)
                        shape = curve_shape_metrics(series) if series else None
                        if shape:
                            entry["shape_r2"] = shape["uptrend_r2"]
                            entry["stagnation_days"] = shape["max_stagnation_days"]
                        if series and vs_series:
                            common = sorted(set(series) & set(vs_series))
                            if len(common) >= 10:
                                import numpy as _np  # noqa: PLC0415

                                a = _np.asarray([series[d] for d in common], dtype=float)
                                b = _np.asarray([vs_series[d] for d in common], dtype=float)
                                if float(a.std()) > 0 and float(b.std()) > 0:
                                    entry["corr_vs_frozen"] = round(
                                        float(_np.corrcoef(a, b)[0, 1]), 3)
                    summary = summarize_tendency(rid)
                    entry["baseline"] = summary.get("baseline")
                    params = summary.get("params") or {}
                    if params:
                        entry["type"] = "1d"
                        name, m = max(params.items(),
                                      key=lambda kv: kv[1].get("plateau_score") or 0.0)
                        plateau = m.get("plateau") or {}
                        entry["top_slot"] = {
                            "param": name,
                            "plateau_score": m.get("plateau_score"),
                            "center": plateau.get("center_value"),
                            "width": plateau.get("width"),
                            "mean_profit": plateau.get("mean_profit"),
                        }
                    else:
                        grid = grid_summary(rid)
                        if grid.get("count"):
                            entry["type"] = "grid"
                            entry["grid"] = {
                                "cells": grid["count"],
                                "positive_ratio": grid.get("positive_ratio"),
                                "mesa": len(grid.get("mesa_cells") or []),
                                "best": grid.get("best_cell"),
                            }
                except Exception as exc:  # noqa: BLE001 - run 단위 부분 실패 허용.
                    entry["error"] = str(exc)
                out["runs"].append(entry)
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    out["count"] = len(out["runs"])
    return out


_DEFAULT_DECISIONS_FILE = os.path.join(REPO_ROOT, ".omo", "evidence", "decisions.jsonl")


def _decisions_file() -> str:
    return os.environ.get("STOM_DASHBOARD_DECISIONS_FILE") or _DEFAULT_DECISIONS_FILE


def _decisions_payload() -> Dict[str, Any]:
    """F3/P-D(2026-06-11) — V6 운용 결정 이력(append-only jsonl) 읽기. 무예외."""
    out: Dict[str, Any] = {"decisions": []}
    try:
        with open(_decisions_file(), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out["decisions"].append(json.loads(line))
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
    out["count"] = len(out["decisions"])
    return out


def _validated_decision_snapshot(
    candidate_identity: Dict[str, Any] | None,
) -> tuple[Dict[str, Any] | None, str | None]:
    state = _current_state_payload()
    winner = state.get("winner")
    if not isinstance(winner, dict):
        return None, "decision_winner_identity_unavailable"
    run_id = str(state.get("run_id") or "")
    winner_gen = int(winner.get("gen", -1))
    identity, error = _candidate_identity_from_payload(
        candidate_identity, run_id=run_id, gen_no=winner_gen
    )
    if error:
        return None, error
    winner_identity, winner_error = _candidate_identity_from_payload(
        winner.get("candidate_identity"), run_id=run_id, gen_no=winner_gen
    )
    if winner_error or identity != winner_identity:
        return None, winner_error or "decision_winner_identity_mismatch"
    generation = next(
        (
            row
            for row in state.get("generations") or []
            if isinstance(row, dict) and int(row.get("gen_no", -1)) == winner_gen
        ),
        None,
    )
    if not isinstance(generation, dict):
        return None, "decision_generation_identity_unavailable"
    generation_identity, generation_error = _candidate_identity_from_payload(
        generation.get("candidate_identity"), run_id=run_id, gen_no=winner_gen
    )
    if generation_error or identity != generation_identity:
        return None, generation_error or "decision_generation_identity_mismatch"
    return {
        "run_id": run_id,
        "gen_no": winner_gen,
        "buy_name": winner.get("buy_name"),
        "sell_name": winner.get("sell_name"),
        "candidate_identity": identity,
    }, None


def _decision_identity_error(candidate_identity: Dict[str, Any] | None) -> str | None:
    _, error = _validated_decision_snapshot(candidate_identity)
    return error


def _record_decision(
    verdict: str,
    note: str,
    candidate_identity: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """F3/P-D — V6 운용 결정을 기록한다(연구 거버넌스 — 유일한 쓰기 라우트).

    append-only: 수정·삭제 없음(결정 번복도 새 레코드로 — 이력 보존).
    현재 동결 후보 스냅샷을 함께 박제해 '무엇에 대한 결정'인지 고정한다.
    """
    if verdict not in ("promote", "complement", "hold", "reject"):
        return {"status": "invalid",
                "allowed": ["promote", "complement", "hold", "reject"]}
    validated_candidate, identity_error = _validated_decision_snapshot(candidate_identity)
    if identity_error is not None:
        return {
            "status": "error",
            "code": "decision_identity_unavailable",
            "message": identity_error,
        }
    try:
        candidate = validated_candidate
        record = {
            "ts": time.time(),
            "verdict": verdict,
            "note": (note or "")[:500],
            "candidate": candidate,
            "candidate_identity": candidate["candidate_identity"] if candidate else None,
        }
        decisions_file = _decisions_file()
        os.makedirs(os.path.dirname(decisions_file), exist_ok=True)
        with open(decisions_file, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"status": "ok", "recorded": record}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def _entry_time_buckets(csv_path: str) -> set:
    """N6(2026-06-11) — per-trade CSV의 진입 시각 30분 버킷(HHMM) 집합.

    포트폴리오 시간 분산 게이트 재료: 전 후보가 같은 버킷 1개면 결합이
    무의미하다(같은 30분 창의 쌍둥이들). 어떤 실패도 빈 집합(advisory).
    """
    try:
        import pandas as pd  # noqa: PLC0415

        if not csv_path or not os.path.isfile(csv_path):
            return set()
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if "매수시간" not in df.columns:
            return set()
        hhmm = df["매수시간"].astype(str).str[8:12]
        return {
            f"{s[:2]}{'00' if s[2:4] < '30' else '30'}"
            for s in hhmm if len(s) == 4 and s.isdigit()
        }
    except Exception:  # noqa: BLE001 - advisory.
        return set()


def _regime_report_payload() -> Dict[str, Any]:
    """과업1(2026-06-12) — 레짐 분해 리포트(최신 regime_report_*.json 반환).

    .omo/evidence/tmap-walkforward/regime_report_*.json 중 mtime 최신을 읽어
    그대로 반환한다. 파일 없으면 {"status": "unavailable"}. 읽기 전용·무예외.
    """
    import glob as _glob  # noqa: PLC0415

    pattern = os.path.join(REPO_ROOT, ".omo", "evidence", "tmap-walkforward",
                           "regime_report_*.json")
    try:
        candidates = sorted(_glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if not candidates:
            return {"status": "unavailable"}
        with open(candidates[0], encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {"status": "unavailable"}
    except Exception:  # noqa: BLE001
        return {"status": "unavailable"}


def _revival_registry_payload() -> Dict[str, Any]:
    """과업2(2026-06-12) — 패자부활 레지스트리(rejected_registry.json 반환).

    .omo/evidence/tmap-walkforward/rejected_registry.json을 읽어 그대로 반환한다.
    파일 없으면 {"status": "unavailable"}. 읽기 전용·무예외.
    """
    path = os.path.join(REPO_ROOT, ".omo", "evidence", "tmap-walkforward",
                        "rejected_registry.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {"status": "unavailable"}
    except FileNotFoundError:
        return {"status": "unavailable"}
    except Exception:  # noqa: BLE001
        return {"status": "unavailable"}


def _pipeline_status_payload() -> Dict[str, Any]:
    """과업3(2026-06-12) — 파이프라인 체크포인트 상태(state.json 순회).

    .omo/evidence/pipeline/*/state.json 을 순회해 {prefix, stages, mtime} 목록을
    mtime 최신순으로 반환한다. 디렉토리 없으면 빈 목록. 읽기 전용·무예외.
    """
    import glob as _glob  # noqa: PLC0415

    pipeline_dir = os.path.join(REPO_ROOT, ".omo", "evidence", "pipeline")
    out: Dict[str, Any] = {"items": [], "count": 0}
    try:
        state_files = _glob.glob(os.path.join(pipeline_dir, "*", "state.json"))
        items: list = []
        for sf in state_files:
            try:
                prefix = os.path.basename(os.path.dirname(sf))
                mtime = os.path.getmtime(sf)
                with open(sf, encoding="utf-8") as fh:
                    stages = json.load(fh)
                items.append({
                    "prefix": prefix,
                    "stages": stages if isinstance(stages, dict) else {},
                    "mtime": round(mtime, 1),
                })
            except Exception:  # noqa: BLE001 - 개별 파일 실패는 skip.
                continue
        items.sort(key=lambda x: x["mtime"], reverse=True)
        out["items"] = items
        out["count"] = len(items)
    except Exception:  # noqa: BLE001
        pass
    return out


M4_MONITOR_BASELINE_FILE = os.path.join(
    REPO_ROOT, ".omo", "evidence", "tmap-walkforward", "m4_monitor_baseline.json"
)

_T2C3_FINDINGS_DOC = os.path.join(
    ".omo", "evidence", "tmap-walkforward", "t2c3_verdict_findings.md"
)

# V6 포트폴리오 구성(하드코딩 — V6 결정 불변).
_V6_MEMBERS = [
    {"name": "THETA", "weight": 0.5},
    {"name": "T2C3", "weight": 0.5},
]


def _portfolio_verdict_payload() -> Dict[str, Any]:
    """V6 채택 추천 포트폴리오 패널 데이터(읽기 전용, 무예외).

    m4_monitor_baseline.json(포트폴리오 vs 시드 월별 M4 baseline) +
    decisions.jsonl(최신 complement 결정) 을 읽어 반환한다.

    반환:
      {"adopted": true/false,
       "members": [{"name":"THETA","weight":0.5},{"name":"T2C3","weight":0.5}],
       "m4": {"champion_total":..., "challenger_total":..., "alerts":[...], "n_months":...},
       "decision_note": "<complement 결정의 note>",
       "findings_doc": "<t2c3_verdict_findings.md 상대경로>"}

    파일 부재/오류 시 {"adopted": false, "status": "unavailable"}. 무예외 계약.
    """
    # decisions.jsonl 에서 최신 complement 레코드 탐색.
    decision_note: Optional[str] = None
    adopted = False
    try:
        with open(_decisions_file(), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if rec.get("verdict") == "complement":
                    decision_note = str(rec.get("note") or "")
                    adopted = True
    except FileNotFoundError:
        pass
    except Exception:  # noqa: BLE001 - 무예외 계약.
        pass

    # m4_monitor_baseline.json 읽기.
    m4: Optional[Dict[str, Any]] = None
    try:
        with open(M4_MONITOR_BASELINE_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        report = (raw or {}).get("report") or {}
        months = report.get("months") or []
        m4 = {
            "champion_total": report.get("champion_total"),
            "challenger_total": report.get("challenger_total"),
            "alerts": report.get("alerts") or [],
            "n_months": len(months),
        }
    except FileNotFoundError:
        pass
    except Exception:  # noqa: BLE001 - 무예외 계약.
        pass

    if not adopted and m4 is None:
        return {"adopted": False, "status": "unavailable"}

    return {
        "adopted": adopted,
        "members": _V6_MEMBERS,
        "m4": m4,
        "decision_note": decision_note,
        "findings_doc": _T2C3_FINDINGS_DOC,
    }


def create_app(
    *,
    security_boundary: Optional[DashboardSecurity] = None,
    final_approval_dest_db: Optional[str] = None,
    final_approval_loop_db: Optional[str] = None,
    final_review_provider: Optional[Callable[[], Dict[str, Any]]] = None,
) -> FastAPI:
    """대시보드 FastAPI 앱을 생성한다 (테스트가 TestClient로 감싼다)."""
    manager = LoopProcessManager()
    security = security_boundary or DashboardSecurity()
    review_provider = final_review_provider or _freeze_verdict_payload

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        # 서버 수명 동안 매니저를 보유하고, 종료 시 추적 중인 루프 자식을
        #   강제 회수한다(오펀 백테스트 방지).
        yield
        manager.hard_stop()

    app = FastAPI(
        title="STOM AI Strategy Loop Dashboard", version="1.0", lifespan=_lifespan,
    )

    @app.middleware("http")
    async def _no_cache_html(request, call_next):
        # 2026-06-11 — index.html 브라우저 캐시 박제 방지: HTML 응답은 매 로드마다
        #   재검증(no-cache)시킨다. ETag 304로 비용은 없고, jsx 버전 범프(v=...)가
        #   즉시 반영된다 ("새 기능이 안 보이는 옛 대시보드" 실사고 재발 방지).
        response = await call_next(request)
        if "text/html" in (response.headers.get("content-type") or "") and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.middleware("http")
    async def _authorize_dashboard(request: Request, call_next):
        failure = security.authorize_http(request)
        if failure is None:
            failure = await security.enforce_http_body_limit(request)
        if failure is not None:
            headers = {"WWW-Authenticate": "Session"} if failure.status_code == 401 else None
            return JSONResponse(
                status_code=failure.status_code,
                content={
                    "status": "error",
                    "code": failure.code,
                    "message": failure.message,
                },
                headers=headers,
            )
        response = await call_next(request)
        security.issue_bootstrap_cookie(request, response)
        return response

    app.state.loop_manager = manager
    app.state.dashboard_security = security
    app.include_router(research_router)
    app.include_router(backtest_router)
    app.include_router(simulation_router)
    app.include_router(alpha_router)
    app.include_router(trade_path_router)
    app.include_router(reach_map_router)
    app.include_router(analysis_card_router)
    app.include_router(autoloop_router)
    app.include_router(provider_status_router)
    app.include_router(transfer_ledger_router)
    app.include_router(exit_axis_router)
    app.include_router(strategy_ledger_router)
    app.include_router(power_gauge_router)
    app.include_router(response_surface_router)
    app.include_router(condition_diff_router)
    app.include_router(trade_pairs_router)
    app.include_router(research_tools_router)
    app.include_router(research_program_router)
    app.include_router(research_truth_router)
    app.include_router(analysis_bundle_router)
    app.include_router(research_result_router)

    @app.get("/", response_class=HTMLResponse)
    def root(request: Request) -> HTMLResponse:
        # 단일 진입점: 루트가 최신 대시보드를 그대로 서빙한다.
        #   버전 접미사(/ui/v4/)나 중간 리다이렉트 없이 http://host:port/ 하나만 정본 주소다.
        return _dashboard_selected_index_response(request)

    def _dashboard_index_response() -> HTMLResponse:
        index_path = os.path.join(_FRONTEND_DIR, "index.html")
        try:
            with open(index_path, encoding="utf-8") as fh:
                return HTMLResponse(fh.read())
        except Exception:  # noqa: BLE001
            return HTMLResponse("<h1>Dashboard frontend not available</h1>", status_code=503)

    def _dashboard_remodel_index_response() -> HTMLResponse:
        index_path = os.path.join(_REMODEL_FRONTEND_DIR, "index.html")
        try:
            with open(index_path, encoding="utf-8") as fh:
                response = HTMLResponse(fh.read())
            response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["X-STOM-Dashboard-Version"] = "v3-remodel"
            return response
        except Exception:  # noqa: BLE001
            return HTMLResponse("<h1>Dashboard remodel frontend not available</h1>", status_code=503)

    def _dashboard_v4_index_response() -> HTMLResponse:
        # V4 graph-first 정본(B트랙 승격 2026-07-17): frontend/v4.html(window.DashboardV4Shell 마운트).
        #   legacy 셸과 같은 bundle/app.js 공유. /ui, /ui/evolution/* 기본 서빙 대상.
        index_path = os.path.join(_FRONTEND_DIR, "v4.html")
        try:
            with open(index_path, encoding="utf-8") as fh:
                response = HTMLResponse(fh.read())
            response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["X-STOM-Dashboard-Version"] = "v4-ops"
            return response
        except Exception:  # noqa: BLE001
            return HTMLResponse("<h1>Dashboard V4 frontend not available</h1>", status_code=503)

    def _dashboard_version_from_request(request: Request) -> str:
        """Return one-response dashboard version selector; never persist in browser state.

        내부 키는 역사적 이유로 v2(legacy 셸)/v3(리모델)/v4(graph-first 정본)를 유지한다.
        B트랙 승격(2026-07-17): 기본값이 v4(graph-first, PR #105 계보)로 전환됐다.
        legacy 셸은 dashboard_version=legacy(v2/production/ops 별칭)로만 1회 열린다.
        """
        selector = (request.query_params.get("dashboard_version") or "").strip().lower()
        if selector in {"v3", "remodel", "preview"}:
            return "v3"
        if selector in {"v2", "legacy", "production", "ops"}:
            return "v2"
        if selector in {"v4", "v4-preview", "v4-ops"}:
            return "v4"

        profile = (request.query_params.get("dashboard_profile") or "").strip().lower()
        if profile in {"v3", "remodel", "preview"}:
            return "v3"
        if profile in {"v2", "legacy", "production", "ops"}:
            return "v2"
        return "v4"

    def _dashboard_selected_index_response(request: Request) -> HTMLResponse:
        version = _dashboard_version_from_request(request)
        if version == "v4":
            return _dashboard_v4_index_response()
        if version == "v3":
            return _dashboard_remodel_index_response()
        response = _dashboard_index_response()
        # legacy 셸(구 V2 계보): 명시 선택으로만 서빙. 헤더로 legacy 임을 표기한다.
        response.headers["X-STOM-Dashboard-Version"] = "legacy"
        return response

    def _redirect_with_query(request: Request, target: str) -> RedirectResponse:
        query = str(request.url.query or "")
        if query:
            target = f"{target}?{query}"
        return RedirectResponse(url=target, status_code=307)

    def _dashboard_not_found() -> HTMLResponse:
        return HTMLResponse(
            """<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <title>STOM Dashboard Route Not Found</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background:
      radial-gradient(circle at 18% 18%, rgba(17, 88, 118, .65), transparent 34%),
      radial-gradient(circle at 80% 72%, rgba(117, 74, 179, .34), transparent 30%),
      linear-gradient(135deg, #06131d 0%, #020409 55%, #090b13 100%);
      color: #d8eefc; font-family: system-ui, sans-serif; }
    main { width: min(920px, calc(100vw - 48px)); border: 1px solid #1e5d77; border-radius: 22px;
      background: linear-gradient(135deg, rgba(9, 32, 45, .96), rgba(3, 9, 16, .96));
      box-shadow: 0 24px 80px rgba(0, 0, 0, .45); padding: 30px; display: grid; gap: 20px; }
    .hero { display: grid; grid-template-columns: 120px 1fr; gap: 22px; align-items: center; }
    .code { height: 120px; border-radius: 18px; display: grid; place-items: center; font-size: 42px; font-weight: 800;
      background: conic-gradient(from 180deg, #0fb5ff, #65e6c4, #8c63ff, #0fb5ff); color: #06131d; }
    h1 { margin: 0 0 10px; font-size: 30px; letter-spacing: .02em; }
    p { margin: 0; color: #8db6c8; line-height: 1.6; }
    .badges { display: flex; gap: 10px; flex-wrap: wrap; }
    .badge { border: 1px solid #2d7290; border-radius: 999px; padding: 7px 11px; background: rgba(10, 48, 65, .72); color: #b9f6e5; font-size: 12px; }
    .matrix { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .cell { min-height: 74px; border: 1px solid #173d52; border-radius: 14px; padding: 14px; background: rgba(4, 18, 29, .72); }
    .label { color: #69d6ff; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .value { margin-top: 8px; color: #f2fbff; font-weight: 700; }
    code { color: #65e6c4; }
  </style>
</head>
<body>
  <main>
    <section class=\"hero\">
      <div class=\"code\">404</div>
      <div>
        <h1>Dashboard route not found</h1>
        <p>Unknown dashboard routes fail closed with <code>404</code> instead of masking broken links with a legacy shell.</p>
      </div>
    </section>
    <section class=\"badges\">
      <span class=\"badge\">V4 ops default preserved</span>
      <span class=\"badge\">V3/graph preview explicit only</span>
      <span class=\"badge\">No hidden SPA fallback</span>
      <span class=\"badge\">Research-only boundary</span>
    </section>
    <section class=\"matrix\">
      <div class=\"cell\"><div class=\"label\">route state</div><div class=\"value\">unknown</div></div>
      <div class=\"cell\"><div class=\"label\">response</div><div class=\"value\">fail-closed 404</div></div>
      <div class=\"cell\"><div class=\"label\">shell loaded</div><div class=\"value\">none</div></div>
    </section>
  </main>
</body>
</html>""",
            status_code=404,
        )

    @app.get("/ui", response_class=HTMLResponse)
    def ui_root_no_slash(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/")

    @app.get("/ui/", response_class=HTMLResponse)
    def ui_root(request: Request) -> RedirectResponse:
        # 구 진입점. 정본 루트로 보낸다(?dashboard_version=legacy 등 쿼리는 보존).
        return _redirect_with_query(request, "/")

    @app.get("/ui/remodel", response_class=HTMLResponse)
    def ui_remodel_root_no_slash() -> RedirectResponse:
        return RedirectResponse(url="/ui/remodel/", status_code=307)

    @app.get("/ui/remodel/", response_class=HTMLResponse)
    def ui_remodel_root() -> HTMLResponse:
        return _dashboard_remodel_index_response()

    @app.get("/ui/remodel/{remodel_page}", response_class=HTMLResponse)
    def ui_remodel_deeplink(remodel_page: str = "condition") -> Any:
        if remodel_page == "remodel-bootstrap.js":
            script_path = os.path.join(_REMODEL_FRONTEND_DIR, "remodel-bootstrap.js")
            try:
                with open(script_path, encoding="utf-8") as fh:
                    return Response(fh.read(), media_type="application/javascript")
            except Exception:  # noqa: BLE001
                return Response("", media_type="application/javascript", status_code=404)
        allowed = {
            "condition", "evolution", "process", "history", "records",
            "lab", "workbench", "audit", "verdict", "backtest",
            "chart-replay", "simulation", "settings",
        }
        if remodel_page not in allowed:
            return _dashboard_not_found()
        return _dashboard_remodel_index_response()

    @app.get("/ui/v4", response_class=HTMLResponse)
    def ui_v4_root_no_slash(request: Request) -> RedirectResponse:
        # 버전 접미사 주소는 은퇴했다. 쿼리스트링은 보존한다 — 없으면 ?base=/?tab= 가
        #   리다이렉트에서 유실돼(예: cross-origin 데이터 연동 ?base=8791) 로컬 백엔드로
        #   붙는 사고가 난다.
        return _redirect_with_query(request, "/")

    @app.get("/ui/v4/", response_class=HTMLResponse)
    def ui_v4_root(request: Request) -> RedirectResponse:
        # 구 graph-first 진입점 → 정본 루트 하나로 통합(2026-07-26).
        return _redirect_with_query(request, "/")

    @app.get("/ui/evolution", response_class=HTMLResponse)
    @app.get("/ui/evolution/{subtab}", response_class=HTMLResponse)
    def ui_evolution(request: Request, subtab: str = "overview") -> Any:
        if subtab == "history":
            return _redirect_with_query(request, "/ui/evolution/records")
        allowed = {"overview", "process", "records", "lab", "workbench", "verdict", "catalog"}
        if subtab not in allowed:
            return _dashboard_not_found()
        return _dashboard_selected_index_response(request)

    @app.get("/ui/backtest", response_class=HTMLResponse)
    def ui_backtest(request: Request) -> HTMLResponse:
        return _dashboard_selected_index_response(request)

    @app.get("/ui/chart-replay", response_class=HTMLResponse)
    def ui_chart_replay(request: Request) -> HTMLResponse:
        return _dashboard_selected_index_response(request)

    @app.get("/ui/simulation")
    def ui_simulation_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/chart-replay")

    @app.get("/ui/process")
    def ui_process_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/process")

    @app.get("/ui/records")
    def ui_records_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/records")

    @app.get("/ui/history")
    def ui_history_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/records")

    @app.get("/ui/lab")
    def ui_lab_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/lab")

    @app.get("/ui/pro")
    def ui_pro_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/workbench")

    @app.get("/ui/verdict")
    def ui_verdict_alias(request: Request) -> RedirectResponse:
        return _redirect_with_query(request, "/ui/evolution/verdict")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "contract_version": C.CONTRACT_VERSION,
            "dashboard": {
                "shell": {
                    "name": _DASHBOARD_SHELL,
                    "release": _DASHBOARD_RELEASE,
                    "build": _DASHBOARD_BUILD,
                },
                "release": _DASHBOARD_RELEASE,
                "build": _DASHBOARD_BUILD,
                "backend": {
                    "release": _DASHBOARD_RELEASE,
                    "build": _DASHBOARD_BUILD,
                    "process": {
                        "pid": os.getpid(),
                        "started_at_unix": _DASHBOARD_PROCESS_STARTED_AT,
                    },
                },
            },
        }
    # Backend diagnostic ring: process-local, bounded, redacted and session-protected.
    import collections as _collections
    import logging as _logging

    _log_secret = re.compile(
        r"(?i)(api[_-]?key|token|secret|password|cookie)"
        r"(\s*[:=]\s*)([^\s,;]+)"
    )
    _log_bearer = re.compile(r"(?i)\bauthorization\s*[:=]?\s*bearer\s+[^\s,;]+")
    _log_absolute_path = re.compile(
        r"(?i)(?:[a-z]:[\\/][^\s,;]*|\\\\[^\s,;]+|(?<![a-z0-9:])/[^\s,;]+)"
    )
    _ring_marker = "_stom_dashboard_ring_handler"

    class _RingLogHandler(_logging.Handler):
        def __init__(self, capacity: int = 400) -> None:
            super().__init__(level=_logging.INFO)
            self.buf: "_collections.deque" = _collections.deque(maxlen=capacity)
            setattr(self, _ring_marker, True)

        def emit(self, record: _logging.LogRecord) -> None:
            try:
                message = self.format(record)
                message = _log_bearer.sub("Authorization: Bearer <redacted>", message)
                message = _log_secret.sub(r"\1\2<redacted>", message)
                message = _log_absolute_path.sub("<absolute-path>", message)
                self.buf.append({
                    "ts": record.created,
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": message[:500],
                })
            except Exception:
                self.handleError(record)

    _ring = _RingLogHandler()
    _ring.setFormatter(_logging.Formatter("%(message)s"))
    _loggers = [_logging.getLogger()]
    for _name in ("uvicorn", "uvicorn.access", "uvicorn.error", "ai_strategy_loop"):
        _logger = _logging.getLogger(_name)
        if not _logger.propagate:
            _loggers.append(_logger)
    for _logger in _loggers:
        for _old in tuple(_logger.handlers):
            if getattr(_old, _ring_marker, False):
                _logger.removeHandler(_old)
        _logger.addHandler(_ring)

    @app.get("/debug/logs")
    def debug_logs(request: Request, lines: int = 200) -> Response:
        """Return a redacted diagnostic tail only to a bootstrapped dashboard session."""

        if not security.session_valid(request):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "code": "session_required",
                    "message": "valid dashboard session required",
                },
                headers={"WWW-Authenticate": "Session"},
            )
        n = max(1, min(400, lines))
        rows = list(_ring.buf)[-n:]
        return JSONResponse(
            {"count": len(rows), "logs": rows},
            headers={"Cache-Control": "no-store, private"},
        )

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(
            _DASHBOARD_FAVICON_SVG,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.get("/process_flow", response_class=HTMLResponse)
    def process_flow() -> HTMLResponse:
        """조건식 발굴 프로세스 정적 참고 자료를 읽기 전용으로 서빙한다.

        프론트 Process subtab의 실시간 그래프가 정본이고, 이 legacy HTML은 별도 보관된
        정적 설명 자료다. GET 요청에서는 파일 재생성이나 디스크 쓰기를 절대 하지 않는다.
        """
        from pathlib import Path as _P  # noqa: PLC0415
        out = _P(__file__).resolve().parents[2] / "docs/process_flow.html"
        try:
            return HTMLResponse(out.read_text(encoding="utf-8"))
        except Exception:
            return HTMLResponse(
                "<h1>프로세스 흐름 생성 전</h1><p>아직 생성되지 않았습니다. "
                "<code>python -m ai_strategy_loop.scripts.build_process_flow_html</code> 실행 후 새로고침.</p>",
                status_code=200)

    @app.get("/reports")
    def reports() -> Dict[str, Any]:
        """Return a cached HTML catalog enriched by canonical report manifests."""

        items = _report_catalog()
        return {
            "root": "docs",
            "count": len(items),
            "registered_count": sum(1 for item in items if item.get("registered")),
            "reports": items,
        }

    @app.get("/reports/view")
    def reports_view(path: str = "") -> Response:
        """리포트 HTML 을 스크립트 차단 CSP + nosniff 로 서빙(sandbox iframe 소비 전제).
           inline JS 가 있어도 CSP default-src 'none' 로 실행 불가(§10-5). traversal/비-html 은 404."""
        target = _safe_report_path(path)
        if target is None:
            return Response("report not found", status_code=404, media_type="text/plain; charset=utf-8")
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as _fh:
                html = _fh.read()
        except OSError:
            return Response("report unreadable", status_code=404, media_type="text/plain; charset=utf-8")
        return HTMLResponse(html, headers={
            "Content-Security-Policy": _REPORTS_CSP,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "no-store",
        })

    @app.get("/status")
    def status() -> Dict[str, Any]:
        return _current_state_payload()

    @app.get("/config/spec")
    def config_spec() -> Dict[str, Any]:
        return {"contract_version": C.CONTRACT_VERSION, "fields": config_field_specs()}
    # v5.13.2 — 설정 탭 GPT 로그인 고도화(사용자 지시): 브라우저 PKCE 로그인을 대시보드
    #   버튼으로 시작하고, 진행/결과를 폴링으로 확인한다. 로그인 자체는 로컬 브라우저에서
    #   사용자가 완료한다(자격증명은 서버가 다루지 않음 — oauth_login 이 토큰 파일만 저장).
    _gpt_login_state: Dict[str, Any] = {
        "running": False, "result": None, "error": None,
        "started_at": None, "finished_at": None,
        # v5.13.2 — 인증 URL 을 상태에 실어 화면이 클릭 가능한 링크로 보여준다.
        #   서버가 창 없이(Hidden) 기동되면 webbrowser.open 이 조용히 실패할 수 있어,
        #   URL 이 화면에 없으면 사용자가 진행할 방법이 아예 사라진다.
        "auth_url": None,
    }
    _gpt_login_lock = threading.Lock()

    def _gpt_login_snapshot() -> Dict[str, Any]:
        with _gpt_login_lock:
            return {"status": "ok", "mode": "gpt_auth", "safe": True,
                    "starts_evolution": False, **dict(_gpt_login_state)}

    @app.post("/gpt_auth/login_start")
    def gpt_auth_login_start() -> Dict[str, Any]:
        """ChatGPT OAuth 브라우저 로그인 시작(비동기, 5분 타임아웃은 oauth_login 소유)."""
        with _gpt_login_lock:
            if _gpt_login_state["running"]:
                return {**_gpt_login_snapshot(), "already_running": True}
            _gpt_login_state.update(running=True, result=None, error=None,
                                    started_at=time.time(), finished_at=None,
                                    auth_url=None)

        def _publish_auth_url(url: str) -> None:
            with _gpt_login_lock:
                _gpt_login_state["auth_url"] = str(url)

        def _worker() -> None:
            try:
                from ai_strategy_loop.provider.chatgpt_oauth.oauth_login import login  # noqa: PLC0415

                ok = asyncio.run(login(on_auth_url=_publish_auth_url))
                if ok:
                    # 새 토큰 파일을 현재 프로세스 토큰 매니저에 즉시 반영.
                    try:
                        from ai_strategy_loop.provider.chatgpt_oauth.token_manager import (  # noqa: PLC0415
                            get_token_manager,
                        )

                        get_token_manager()._load_from_file()  # noqa: SLF001 - 동일 패키지 재적재 관례
                    except Exception:  # noqa: BLE001
                        pass
                with _gpt_login_lock:
                    _gpt_login_state.update(running=False, result=bool(ok),
                                            finished_at=time.time())
            except Exception as exc:  # noqa: BLE001 - 로그인 실패는 상태로만 보고.
                with _gpt_login_lock:
                    _gpt_login_state.update(running=False, result=False,
                                            error=str(exc), finished_at=time.time())

        threading.Thread(target=_worker, name="gpt-auth-login", daemon=True).start()
        return {**_gpt_login_snapshot(), "started": True,
                "message": "브라우저에서 ChatGPT 로그인 창이 열립니다. 창이 뜨지 않으면 "
                           "아래 인증 링크를 직접 여세요(5분 내 완료)."}

    @app.get("/gpt_auth/login_state")
    def gpt_auth_login_state() -> Dict[str, Any]:
        """로그인 진행 상태 스냅샷(읽기 전용)."""
        return _gpt_login_snapshot()

    @app.get("/gpt_auth/status")
    async def gpt_auth_status() -> Dict[str, Any]:
        """Read-only ChatGPT OAuth status for the dashboard settings panel."""
        try:
            from ai_strategy_loop.provider.chatgpt_oauth import get_status  # noqa: PLC0415

            status_payload = await get_status()
            return {
                "status": "ok",
                "mode": "gpt_auth",
                "safe": True,
                "starts_evolution": False,
                **status_payload,
            }
        except Exception as exc:  # noqa: BLE001 - auth status must not break dashboard.
            return {
                "status": "error",
                "mode": "gpt_auth",
                "safe": True,
                "starts_evolution": False,
                "reason": str(exc),
            }

    @app.post("/gpt_auth/test")
    def gpt_auth_test() -> Dict[str, Any]:
        """Probe the existing OAuth proxy without starting evolution or exporting anything."""
        try:
            import requests  # noqa: PLC0415
            from ai_strategy_loop.provider.chatgpt_oauth.constants import (  # noqa: PLC0415
                DEFAULT_MODEL,
                PROXY_OPENAI_API_KEY_PLACEHOLDER,
                get_proxy_base_url,
            )

            proxy_base_url = get_proxy_base_url()
            if not is_loopback_http_url(proxy_base_url):
                return {
                    "status": "unavailable",
                    "mode": "gpt_auth",
                    "safe": True,
                    "starts_evolution": False,
                    "code": "provider_non_loopback_forbidden",
                    "message": "provider test target must be loopback",
                }

            response = requests.post(
                f"{proxy_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {PROXY_OPENAI_API_KEY_PLACEHOLDER}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": "OK"}],
                    "max_tokens": 4,
                    "stream": False,
                },
                timeout=5,
            )
            ok = response.status_code == 200
            return {
                "status": "ok" if ok else "unavailable",
                "mode": "gpt_auth",
                "model": DEFAULT_MODEL,
                "reasoning_effort": "high",
                "safe": True,
                "starts_evolution": False,
                "http_status": response.status_code,
                "message": "GPT auth proxy responded" if ok else "GPT auth proxy unavailable or credential expired",
            }
        except Exception as exc:  # noqa: BLE001 - report safe failure.
            return {
                "status": "unavailable",
                "mode": "gpt_auth",
                "model": DEFAULT_MODEL,
                "reasoning_effort": "high",
                "safe": True,
                "starts_evolution": False,
                "message": "GPT auth connection test failed without starting evolution",
                "reason": str(exc),
            }

    @app.get("/research_criteria")
    def research_criteria(mode: Optional[str] = None) -> Dict[str, Any]:
        active_mode = normalize_research_oos_mode(mode)
        return {"contract_version": C.CONTRACT_VERSION, **research_mode_payload(active_mode)}

    @app.get("/equity_curves")
    def equity_curves(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 누적수익 시계열(equity curve)을 반환한다(읽기 전용, 무예외).

        run_id 주면 그 run의 세대만(현재 run 정상 스케일), 없으면 전체(하위호환).
        최근 200 세대까지 조회하며, 세대당 포인트는 최대 200개로 다운샘플한다.
        CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 배열(무예외).
        """
        return _equity_curves_payload(run_id=run_id)

    @app.get("/hall_of_fame")
    def hall_of_fame() -> Dict[str, Any]:
        """명예의 전당: 인간 벤치마크 + AI 생성 통합 목록을 반환한다(읽기 전용, 무예외).

        인간은 reference_strategies.json(19전략), AI는 loop_runs.db의 gate_passed=1·
        흑자 세대를 운영금 역산·연평균 산식으로 매핑해 graded 상위 30개를 돌려준다.
        JSON/DB가 없으면 빈 목록(무예외 계약 — 대시보드가 빈 상태를 표시).
        """
        return _hall_of_fame_payload()
    @app.get("/hall_of_fame/catalog")
    def hall_of_fame_catalog(
        limit: int = 50,
        offset: int = 0,
        sort: str = "score",
        order: str = "desc",
        status: str = "",
        gate: str = "",
        outcome: str = "",
    ) -> Dict[str, Any]:
        """Bounded AI research catalog; legacy /hall_of_fame remains unchanged."""
        filters = lambda value: {part.strip().lower() for part in value.split(",") if part.strip()}
        return _hall_catalog_payload(
            limit=limit,
            offset=offset,
            sort=sort.lower(),
            order=order.lower(),
            statuses=filters(status),
            gates=filters(gate),
            outcomes=filters(outcome),
        )

    @app.get("/qsp/rounds")
    def qsp_rounds(tag: str = "") -> Dict[str, Any]:
        """QSP 다후보 라운드 기록(round_runner 산출 JSON) 목록 — 라운드 보드용.

        docs/research/quant_scoring_pipeline/rounds/*.json 을 읽는다(읽기 전용,
        무예외). tag 를 주면 해당 태그만. 라운드 오름차순.
        """
        from pathlib import Path as _Path  # noqa: PLC0415 - REPO_ROOT 는 str.

        rounds_dir = _Path(REPO_ROOT) / "docs" / "research" / "quant_scoring_pipeline" / "rounds"
        items: List[Dict[str, Any]] = []
        try:
            for p in sorted(rounds_dir.glob("*_r*.json")):
                if p.name.endswith("_pairs.json"):
                    continue
                if tag and not p.name.startswith(f"{tag}_"):
                    continue
                try:
                    items.append(json.loads(p.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        except OSError:
            pass
        items.sort(key=lambda r: (str(r.get("tag")), int(r.get("round", 0) or 0)))
        return {"rounds": items, "count": len(items)}

    @app.get("/reference_screenshots")
    def reference_screenshots() -> Dict[str, Any]:
        """인간 reference 결과 스크린샷 파일명 목록을 반환한다(갤러리 fetch용, 읽기 전용, 무예외).

        docs/reference/STOM_Good_Results의 최상위 이미지 파일명만 나열한다(분석용 파생
        크롭/줌은 제외). 프론트가 각 파일명을 baseUrl+'/reference_img/'+filename으로
        StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록(무예외 계약).
        """
        files = _reference_screenshots()
        return {"screenshots": files, "count": len(files)}

    @app.get("/runs")
    def runs(fields: str = "") -> Dict[str, Any]:
        """loop_runs.db의 모든 run 요약을 반환한다(run 비교 콘솔 목록).

        lineage.compare_runs(run_ids=None)로 전 run을 요약한다. DB가 없거나
        조회 실패면 빈 목록을 돌려 대시보드가 깨지지 않게 한다(무예외 계약).
        2026-06-11부터 최신 우선 정렬(running 최상단) — _runs_payload 참조.
        v5.6 U7 — ?fields=slim: 목록 UI가 쓰는 필드만 남겨 3MB→수십KB(히스토리/셀렉터 성능).
        """
        if fields == "slim":
            # This summary path deliberately never calls compare_runs(): that function
            # emits every generation row before callers can project it away.
            payload = _runs_slim_payload()
            keep = ("run_id", "label", "naming", "status", "started_at", "finished_at", "elapsed_sec",
                    "period", "timeframe", "gen_count", "gate_passed_count", "best_gen", "best_score",
                    "has_csv", "final_profit", "total_profit_pct", "max_hold_count", "trade_count",
                    "years", "start_year", "end_year", "bt_universe_start_time", "bt_universe_end_time")
            rs = payload.get("runs") or []
            payload["runs"] = [{k: r.get(k) for k in keep if k in r} for r in rs]
            payload["fields"] = "slim"
            payload["generation_rows_omitted"] = True
        else:
            payload = _runs_payload(None)
        return payload

    @app.get("/ops_status")
    def ops_status(window_hours: int = 24) -> Dict[str, Any]:
        """운영 현황(2026-06-11) — 실행 중 run 활성/정체·최근 완료·WF 집계·증거 신선도.

        쿼리: ?window_hours=24. '지금 무엇이 돌고 있고 잘 돌고 있는가'를 한
        호출로 — Validation 탭 Ops 패널이 10초 폴링한다. 읽기 전용·무예외.
        """
        return _ops_status_payload(window_hours)

    @app.get("/freeze_verdict")
    def freeze_verdict() -> Dict[str, Any]:
        """검증 결산(2026-06-11) — 동결 후보의 V1~V5+리스크 증거 종합(읽기 전용).

        결정 카드의 라이브 버전: 동결·DSR/PBO(+쌍둥이 경고)·OOS·플라시보·
        슬리피지·중복도·체결/서킷/사이징·walk-forward를 lines/alerts로 합성.
        """
        review = review_provider()
        return {
            **review,
            "approval_binding": _approval_binding_payload(
                review,
                final_approval_loop_db,
            ),
        }

    @app.get("/portfolio_sim")
    def portfolio_sim(runs: str = "") -> Dict[str, Any]:
        """과업2(2026-06-12) — 복수 run 균등 가중 결합 시뮬(advisory).

        쿼리: ?runs=run1,run2[,run3...]. 각 run의 최신 ok 세대 일별 손익으로
        portfolio_report를 호출한다. 유효 시리즈 2개 미만이면 {"error": ...} 200.
        읽기 전용·무예외·판정 미사용.
        """
        return _portfolio_sim_payload(runs)

    @app.get("/regime_report")
    def regime_report() -> Dict[str, Any]:
        """과업1(2026-06-12) — 레짐 분해 리포트(최신 regime_report_*.json 반환). 읽기 전용·무예외."""
        return _regime_report_payload()

    @app.get("/revival_registry")
    def revival_registry() -> Dict[str, Any]:
        """과업2(2026-06-12) — 패자부활 레지스트리(rejected_registry.json 반환). 읽기 전용·무예외."""
        return _revival_registry_payload()

    @app.get("/pipeline_status")
    def pipeline_status() -> Dict[str, Any]:
        """과업3(2026-06-12) — 파이프라인 체크포인트 상태(.omo/evidence/pipeline/*/state.json). 읽기 전용·무예외."""
        return _pipeline_status_payload()

    @app.get("/portfolio_verdict")
    def portfolio_verdict() -> Dict[str, Any]:
        """V6 채택 추천 포트폴리오(2026-06-13) — m4 baseline + 최신 complement 결정. 읽기 전용·무예외."""
        return _portfolio_verdict_payload()

    @app.get("/niche_compare")
    def niche_compare(run_ids: str = "") -> Dict[str, Any]:
        """D3(2026-06-11) — 니치 지도 비교(미지정 시 최근 tmap run 자동 발굴)."""
        return _niche_compare_payload(run_ids)

    @app.get("/equity_curve")
    def equity_curve(run_id: str = "", gen_no: int = 0) -> Dict[str, Any]:
        """E2/D4(2026-06-11) — 세대 누적 수익곡선(일별·다운샘플). 읽기 전용·무예외."""
        return _equity_curve_payload(run_id, gen_no)

    @app.get("/decisions")
    def decisions() -> Dict[str, Any]:
        """F3/P-D — V6 운용 결정 이력. 읽기 전용·무예외."""
        return _decisions_payload()

    @app.post("/record_decision")
    def record_decision(payload: DecisionRecordPayload) -> Dict[str, Any]:
        """F3/P-D — V6 운용 결정 기록(promote|complement|hold|reject, append-only)."""
        result = _record_decision(
            payload.verdict,
            payload.note,
            payload.candidate_identity.identity_dict()
            if payload.candidate_identity is not None
            else None,
        )
        if result.get("status") != "ok":
            return JSONResponse(status_code=409, content=result)
        return result

    @app.get("/tmap_grid")
    def tmap_grid(run_id: str = "") -> Dict[str, Any]:
        """C6/P1(2026-06-11) — 2-D 격자 지도(mesa·히트맵 데이터). 읽기 전용·무예외.

        쿼리: ?run_id=<--grid 스윕 run>. 셀 행렬·흑자율·최강 셀·mesa(4-이웃
        전부 흑자)를 반환 — 프런트가 히트맵으로 그린다.
        """
        try:
            from ai_strategy_loop.tmap.tendency import grid_summary  # noqa: PLC0415

            return grid_summary(run_id)
        except Exception as exc:  # noqa: BLE001
            return {"run_id": run_id, "cells": [], "count": 0, "error": str(exc)}

    @app.get("/run_state")
    def run_state(run_id: str = "") -> Dict[str, Any]:
        """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성해 반환한다(#65 run 셀렉터).

        쿼리: ?run_id=<run_id>. loop_runs.db의 runs+generations에서 그 run을 통째로
        재구성한다(세대표·best/winner·코드뷰어가 그 run을 소비). 라이브 상태가 합성 run으로
        오염돼도 사용자가 실제 run을 골라 본다. run_id 미지정/없는 run/조회 실패는 idle
        상태로 표준화한다(무예외 — 대시보드가 빈 상태 표시). 읽기 전용·추가 백테 0회.
        """
        return _run_state_payload(run_id)

    @app.get("/generation_durations")
    def generation_durations(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 소요초(인접 created_at 차분)를 반환한다(#64 과거 run retroactive).

        쿼리: ?run_id=<run_id>(선택). 없으면 전체 run. LIVE 발행이 없던 과거 run에도
        DB의 created_at/started_at로 산출되므로 사용자가 지금 바로 세대 소요를 본다.
        DB 없거나 조회 실패면 빈 목록(무예외).
        """
        return _generation_durations_payload(run_id)

    @app.get("/run_yearly")
    def run_yearly(run_id: str = "") -> Dict[str, Any]:
        """D1 — run의 세대별 연도 분해(거래·손익·승률)를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>. 근거(2026-06-10 원인5): 연도별 쇠퇴는 합계로는 안 보인다.
        per-trade CSV를 연 단위로 집계한다(추가 백테 0회). CSV 없으면 빈 분해.
        """
        return _run_yearly_payload(run_id)

    @app.get("/autopsy")
    def autopsy(run_id: str = "", gen_no: int = 0) -> Dict[str, Any]:
        """D2 — 세대 결과 CSV의 공식 부검(진입/청산) NL 요약을 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&gen_no=<n>. 루프 프롬프트 환류로만 쓰이던 부검을 사람이
        직접 본다(손실군집·MFE 반납·손실집중 매도규칙). CSV 없으면 status=no_csv.
        """
        return _autopsy_payload(run_id, gen_no)

    @app.get("/trade_quant")
    def trade_quant(run_id: str = "", gen_no: int = -1,
                    fine_time: bool = False, top_n: int = 5) -> Dict[str, Any]:
        """G3 — 세대 결과 CSV의 거래 정량 지표 자연어 요약을 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&gen_no=<n>(음수면 최신 ok 세대)&fine_time=<bool>&top_n=<k>.
        ai_strategy_loop.autopsy.trade_quant.analyze_trade_table을 지연 import해 호출한다
        (모듈이 아직 없어도 조기 부팅을 막지 않는다). 승인/export/엔진 경로 무영향 —
        advisory 전용.
        """
        # top_n 클램프(아키텍트 리뷰 LOW): 음수/초대형 입력 방어 — 이웃 라우트 관례.
        return _trade_quant_payload(run_id, gen_no, fine_time, max(1, min(int(top_n), 50)))

    @app.get("/research_maturity")
    def research_maturity() -> Dict[str, Any]:
        """G005 — 연구 프로그램 단계별 성숙도 자동 스코어카드(읽기 전용·무예외).

        scripts.research_maturity_scorecard.build_scorecard을 지연 import해 즉석 계산한다
        (모듈이 아직 없어도 조기 부팅을 막지 않는다). state 캐시 없음 — 매 호출 재계산.
        승인/export/엔진 경로 무영향, advisory 전용.
        """
        return _research_maturity_payload()

    @app.get("/selector_preview")
    def selector_preview(run_id: str = "", selector: str = "sparse_positive_v1") -> Dict[str, Any]:
        """D4 — run 행에 선택기를 진단 적용한 미리보기를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&selector=sparse_positive_v1|seed_relative_v1.
        근거(2026-06-10 원인1): 기준-목표 비정합을 눈으로 확인한다. **진단 전용** —
        동결 아티팩트를 쓰지 않으며 OOS-blind 동결 절차를 대체하지 않는다.
        """
        return _selector_preview_payload(run_id, selector)

    @app.get("/counterfactual")
    def counterfactual(run_id: str = "", gen_no: int = 0, top_k: int = 5) -> Dict[str, Any]:
        """R2(2026-06-11) — 세대 CSV의 반사실 필터 제안을 반환한다(백테 0회, 읽기 전용·무예외).

        쿼리: ?run_id=<run_id>&gen_no=<n>&top_k=<k>. 부검 변별 변수+승자 분위수로 강화 필터
        후보를 만들고 "총손익이 깎이지 않는" 것만 손익 영향·연도별 분해와 함께 반환한다.
        **인샘플 advisory** — 채택 후보는 스모크→train→동결→OOS 규율로 검증해야 한다.
        """
        out: Dict[str, Any] = {"run_id": run_id, "gen_no": gen_no,
                               "suggestions": [], "count": 0, "status": "unavailable"}
        row = _row_for_gen(run_id, gen_no)
        if row is None:
            return out
        out["label"] = row.get("strategy_gist") or ""
        csv_path = row.get("csv_path") or ""
        if not csv_path:
            out["status"] = "no_csv"
            return out
        try:
            from ai_strategy_loop.fitness.counterfactual import suggestions_payload  # noqa: PLC0415

            abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
            payload = suggestions_payload(abs_csv, top_k=top_k)
            out.update(payload)
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/freeze_mc")
    def freeze_mc(run_id: str = "", gen_no: int = 0,
                  n_boot: int = 2000, block_len: int = 5) -> Dict[str, Any]:
        """R3(2026-06-11) — 세대 일별 손익의 블록 부트스트랩 MC를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=&gen_no=&n_boot=&block_len=. GUI 백테스트 MC(거래 iid 추출)의
        헤드리스 대응물 — 단 일별 손익 **블록** 재추출로 레짐 군집을 보존하고 MDD(낙폭금액)
        분포까지 산출한다(6/2 in-sample iid MC의 OOS 전이 실패 교훈 반영). advisory 전용.
        """
        out: Dict[str, Any] = {"run_id": run_id, "gen_no": gen_no, "status": "unavailable"}
        row = _row_for_gen(run_id, gen_no)
        if row is None:
            return out
        out["label"] = row.get("strategy_gist") or ""
        csv_path = row.get("csv_path") or ""
        if not csv_path:
            out["status"] = "no_csv"
            return out
        try:
            from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
                block_bootstrap_daily,
                daily_pnl_series,
            )

            abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
            series = daily_pnl_series(abs_csv)
            if not series:
                out["status"] = "no_daily_series"
                return out
            mc = block_bootstrap_daily(
                list(series.values()), n_boot=min(int(n_boot), 10000),
                block_len=max(int(block_len), 1),
            )
            if mc is None:
                out["status"] = "insufficient_days"
                out["n_days"] = len(series)
                return out
            out["mc"] = mc
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/tmap_map")
    def tmap_map(run_id: str = "", compare_run_id: str = "") -> Dict[str, Any]:
        """TMAP G3(2026-06-11) — 스윕 run의 경향성 지도를 반환한다(읽기 전용·무예외).

        쿼리: ?run_id=<tmap_sweep run_id>[&compare_run_id=<다른 스윕 run>].
        변수별 응답 곡선·고원(중심/폭/평균손익)·절벽·plateau_score + 베이스라인.
        compare_run_id(M12)를 주면 같은 슬롯의 다른 창(마이크로/본/연도) 지도를
        compare 키로 병기 — 구간별 경향 발산(예: window_end 분기 +61% vs 3년
        +12%)을 즉시 가시화한다. TMAP 라벨 행이 없으면 count=0(graceful).
        피크가 아닌 고원을 고르는 것이 계약 — advisory 전용.
        """
        try:
            from ai_strategy_loop.tmap.tendency import summarize_tendency  # noqa: PLC0415

            out = summarize_tendency(run_id)
            if compare_run_id:
                try:
                    out["compare"] = summarize_tendency(compare_run_id)
                except Exception as exc:  # noqa: BLE001 - 비교 실패가 본 지도를 막지 않게.
                    out["compare"] = {"run_id": compare_run_id, "error": str(exc)}
            return out
        except Exception as exc:  # noqa: BLE001
            return {"run_id": run_id, "baseline": None, "params": {},
                    "count": 0, "error": str(exc)}

    @app.get("/portfolio_preview")
    def portfolio_preview(run_id: str = "", gens: str = "",
                          max_size: int = 4, corr_cap: float = 0.5) -> Dict[str, Any]:
        """TMAP G5(2026-06-11) — 세대들의 일별손익 저상관 결합 미리보기(읽기 전용·무예외).

        쿼리: ?run_id=&gens=<0,1,2>(비우면 status=ok 전 세대)&max_size=&corr_cap=.
        일별손익 합산 근사(동시보유 자본 제약 무시 — 낙관 편향, note에 명시) —
        채택 조합은 실백테 확인이 계약. advisory 전용.
        """
        import sqlite3  # noqa: PLC0415

        from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

        out: Dict[str, Any] = {"run_id": run_id, "selection": [], "steps": [],
                               "combined": None, "status": "unavailable"}
        if not run_id:
            return out
        try:
            con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
            con.row_factory = sqlite3.Row
            try:
                rows = con.execute(
                    "SELECT gen_no, status, strategy_gist, buy_name, csv_path"
                    " FROM generations WHERE run_id=? ORDER BY gen_no",
                    (run_id,),
                ).fetchall()
            finally:
                con.close()
            wanted = {int(g) for g in gens.split(",") if g.strip()} if gens.strip() else None
            from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: PLC0415
            from ai_strategy_loop.tmap.portfolio import greedy_portfolio  # noqa: PLC0415

            series, csv_by_key = {}, {}
            for r in rows:
                d = dict(r)
                if d.get("status") != "ok" or not d.get("csv_path"):
                    continue
                if wanted is not None and int(d["gen_no"]) not in wanted:
                    continue
                csv_path = d["csv_path"]
                abs_csv = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
                s = daily_pnl_series(abs_csv)
                if s:
                    label = d.get("strategy_gist") or d.get("buy_name") or f"gen{d['gen_no']}"
                    key = f"gen{d['gen_no']}:{label}"
                    series[key] = s
                    csv_by_key[key] = abs_csv
            if len(series) < 1:
                out["status"] = "no_series"
                return out
            result = greedy_portfolio(series, max_size=max_size, corr_cap=corr_cap)
            out.update(result)
            # N6(2026-06-11) — 진입 시간대 분산 게이트: 전 후보가 같은 30분 창이면
            #   상관 게이트와 무관하게 포트폴리오가 무의미하다(쌍둥이 풀 — 정직 공시).
            selection = result.get("selection") or []
            buckets = {k: sorted(_entry_time_buckets(csv_by_key.get(k, ""))) for k in selection}
            union = set().union(*buckets.values()) if buckets else set()
            out["time_dispersion"] = {
                "buckets_by_candidate": buckets,
                "union_bucket_count": len(union),
            }
            if selection and len(union) <= 1:
                out["time_dispersion"]["warning"] = (
                    "선택 후보 전원이 같은 30분 진입 창 — 시간 분산 0,"
                    " 포트폴리오 결합 무의미(독립 니치 템플릿(A4)이 필요)"
                )
            out["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            out["status"] = "error"
            out["error"] = str(exc)
        return out

    @app.get("/runs/compare")
    def runs_compare(ids: str = "") -> Dict[str, Any]:
        """지정한 run id들을 지표/우승전략으로 비교한다(loop_runs.db 직접).

        ids는 쉼표로 구분한 run_id 목록(예: `?ids=run_a,run_b`). 비면 전체 run.
        """
        id_list = [s.strip() for s in ids.split(",") if s.strip()] or None
        return _runs_payload(id_list)

    @app.get("/strategy_code")
    def strategy_code(run: str = "", gen: int = -1) -> Dict[str, Any]:
        """한 세대의 매수/매도 전략 코드를 반환한다(코드 뷰어 fetch용).

        쿼리: ?run=<run_id>&gen=<n>. 루프 DB(STOM_CLI_DB_STRATEGY)의
        stockbuy/stocksell에서 그 세대의 코드를 조회해 {buy_code, sell_code}를
        돌려준다. run 미지정/조회 실패/없는 gen은 빈 코드 문자열로 표준화한다
        (무예외 — 대시보드가 "코드가 없습니다"를 표시).
        """
        if not run or gen < 0:
            reason = "missing_run" if not run else "missing_generation"
            return {
                "ok": True,
                "run_id": run, "gen": gen,
                "gen_no": gen,
                "buy_name": "", "sell_name": "", "buy_code": "", "sell_code": "",
                "code_status": reason,
                "reason": reason,
            }
        return _strategy_code_payload(run, gen)

    @app.get("/prompts")
    def prompts(run_id: Optional[str] = None, gen_no: Optional[int] = None) -> Dict[str, Any]:
        """저장된 프롬프트 메타데이터와 bounded text head를 반환한다(읽기 전용)."""
        return _prompts_payload(run_id, gen_no)

    @app.get("/strategy_diff")
    def strategy_diff(run_id: Optional[str] = None, gen_no: int = -1,
                      base_gen: str = "previous") -> Dict[str, Any]:
        """현재 세대와 이전/base 세대의 매수·매도 전략 코드 diff를 반환한다."""
        if not run_id:
            return {
                "ok": True,
                "run_id": run_id,
                "gen_no": int(gen_no),
                "buy_name": "",
                "sell_name": "",
                "buy_code": "",
                "sell_code": "",
                "base_gen": None,
                "base_buy_name": None,
                "base_sell_name": None,
                "base_buy_code": "",
                "base_sell_code": "",
                "buy_diff": [],
                "sell_diff": [],
                "prompts": [],
                "diff_status": "missing_run",
                "reason": "missing_run",
            }
        if int(gen_no) < 0:
            return {
                "ok": True,
                "run_id": run_id,
                "gen_no": int(gen_no),
                "buy_name": "",
                "sell_name": "",
                "buy_code": "",
                "sell_code": "",
                "base_gen": None,
                "base_buy_name": None,
                "base_sell_name": None,
                "base_buy_code": "",
                "base_sell_code": "",
                "buy_diff": [],
                "sell_diff": [],
                "prompts": [],
                "diff_status": "missing_generation",
                "reason": "missing_generation",
            }
        return _strategy_diff_payload(run_id, int(gen_no), base_gen)

    @app.get("/ai_context_pack")
    def ai_context_pack(run_id: Optional[str] = None, gen_no: Optional[int] = None) -> Dict[str, Any]:
        """현재 연구 상태를 외부 AI에게 전달할 수 있는 read-only context pack으로 반환한다."""
        return _ai_context_pack_payload(run_id, gen_no)

    @app.get("/backtest_detail")
    def backtest_detail(run_id: str = "", gen_no: int = -1) -> Dict[str, Any]:
        """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(차트 fetch용).

        쿼리: ?run_id=<run_id>&gen_no=<n>. 그 세대의 per-trade 결과 CSV를
        parse_backtest_series로 일별손익+누적곡선+낙폭으로 변환해 돌려준다(추가 백테 0회).
        run_id 미지정/없는 gen/CSV 없음/파싱 실패는 빈 시계열로 표준화한다(무예외 —
        대시보드가 빈 상태 패널을 표시).
        """
        if not run_id or gen_no < 0:
            return {
                "run_id": run_id, "gen_no": gen_no, "gate_passed": False,
                "daily": [], "cumulative": [], "drawdown": [],
                "summary": {
                    "trade_count": 0, "final_profit": 0.0,
                    "max_drawdown": 0.0, "n_days": 0,
                },
            }
        return _backtest_detail_payload(run_id, gen_no)

    @app.get("/evolution_gui_parity")
    def evolution_gui_parity(run_id: str = "", gen_no: int = -1) -> Dict[str, Any]:
        """Return GUI-parity hourly/weekday analysis for one evolution generation."""
        from ai_strategy_loop.dashboard.evolution_gui_parity import evolution_gui_parity_payload  # noqa: PLC0415

        return evolution_gui_parity_payload(run_id, int(gen_no))

    @app.get("/adaptive_timing")
    def adaptive_timing(run_id: Optional[str] = None, lookback: int = 2) -> Dict[str, Any]:
        """run의 gen0(또는 첫 gate_passed) 전략 결과 CSV에 적응형 레짐-타이밍 리포트를 돌린다.

        쿼리: ?run_id=<run_id>&lookback=<n>. 분석 전용(엔진/하드게이트/스코어 무영향)
        오버레이로, always-on 대비 위험조정(수익/MDD)을 비교한다(추가 백테 0회). run_id
        미지정/없는 run/CSV 없음/파싱 실패는 {"error": ...}로 표준화한다(읽기 전용·무예외).
        """
        return _adaptive_timing_payload(run_id, lookback)

    @app.get("/edge_ratio")
    def edge_ratio(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                   fine_time: bool = False,
                   gen_no: Optional[int] = None) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 MFE/MAE 엣지비율 + 시간대×시총 파노라마 세그먼트를 반환한다.

        쿼리: ?run_ids=<a,b,c>(파노라마 다중 run 풀) 또는 ?run_id=<run_id>(단일 run 풀),
        &fine_time=<bool>(5분 시초 세분). 미사용이던 R_MFE/R_MAE 신호로 엣지비율(평균MFE/평균|MAE|)을
        산출하고, 누적된 전체 거래를 시총·시간대·등락률·교차로 쪼개 본다(분석 전용·엔진/하드게이트/스코어
        무영향·추가 백테 0회). segments 응답에 "change" 키 포함(B_등락율 없으면 빈 리스트).
        run 식별자 미지정/없는 run/CSV 없음은 {"error": ...} 또는
        insufficient로 표준화한다(읽기 전용·무예외).
        """
        return _edge_ratio_payload(run_id, run_ids, fine_time, gen_no=gen_no)

    @app.get("/feature_importance")
    def feature_importance(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                           axis: str = "market_cap", fine_time: bool = False,
                           gen_no: Optional[int] = None) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 세그먼트별 승리-변수 피처 중요도를 반환한다.

        쿼리: ?run_ids=<a,b,c>(파노라마 다중 run 풀) 또는 ?run_id=<run_id>(단일 run 풀),
        &axis=<market_cap|time|change>(세그먼트 축), &fine_time=<bool>(시간축 5분 시초 세분). 각 B_*
        진입 피처가 승리거래(수익률>0)와 패배거래를 가르는 정도를 표준화 평균차(Cohen's d)와
        상/하위 사분위 승률로 산출하고, 전역 풀과 세그먼트(시총 등급·시간대·등락률)별로 나눠
        "어느 시간대×시총×등락률에서 어느 진입변수가 승패를 가르나"에 답한다(분석 전용·엔진/하드게이트/
        스코어 무영향·추가 백테 0회). run 식별자 미지정/없는 run/CSV 없음은 {"error": ...} 또는
        insufficient로 표준화한다(읽기 전용·무예외).
        """
        return _feature_importance_payload(run_id, run_ids, axis, fine_time, gen_no=gen_no)

    @app.get("/variable_correlation")
    def variable_correlation(run_id: Optional[str] = None, run_ids: Optional[str] = None,
                             method: str = "pearson",
                             gen_no: Optional[int] = None) -> Dict[str, Any]:
        """run(들)의 세대 결과 CSV를 풀링해 변수별 outcome/feature 상관도를 반환한다.

        쿼리: ?run_ids=<a,b,c> 또는 ?run_id=<run_id>, &method=<pearson|spearman>.
        B_* 진입 변수만 분석하며, outcome은 수익률 컬럼이다. 분석 전용·읽기 전용으로
        엔진/하드게이트/스코어/생성/winner/export에는 영향이 없다.
        """
        return _variable_correlation_payload(run_id, run_ids, method, gen_no=gen_no)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        failure = security.authorize_websocket(websocket, Capability.LOOP_CONTROL)
        if failure is not None:
            await close_websocket_failure(websocket, failure)
            return
        await websocket.accept()
        # 연결 즉시 현재 상태 송신.
        last_sent = _current_state_payload()
        await websocket.send_json(last_sent)

        async def _pusher() -> None:
            """current_state.json 변경을 폴링해 변경 시에만 push."""
            nonlocal last_sent
            while True:
                await asyncio.sleep(_POLL_INTERVAL)
                payload = _current_state_payload()
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_json(payload)

        push_task = asyncio.create_task(_pusher())
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw) > MAX_WEBSOCKET_MESSAGE_CHARS:
                    await websocket.send_json({
                        "status": "error",
                        "code": "payload_too_large",
                        "message": "control message exceeds the server limit",
                    })
                    continue
                try:
                    msg = CONTROL_PAYLOAD_ADAPTER.validate_json(raw)
                except ValidationError:
                    await websocket.send_json({
                        "status": "error",
                        "code": "invalid_message",
                        "message": "invalid dashboard control message",
                    })
                    continue
                failure = security.authorize_websocket(
                    websocket,
                    control_capability(msg),
                )
                if failure is not None:
                    await websocket.close(
                        code=failure.websocket_code,
                        reason=failure.code,
                    )
                    return
                result = _handle_control(
                    msg,
                    manager,
                    security,
                    final_approval_dest_db,
                    final_approval_loop_db,
                    review_provider,
                )
                await websocket.send_json(result)
        except WebSocketDisconnect:
            pass
        finally:
            push_task.cancel()

    # 인간 reference 결과 스크린샷을 /reference_img 하위에 읽기 전용으로 마운트한다.
    #   StaticFiles는 GET/HEAD만 처리(쓰기 불가)하고, 노출 대상은 STOM_Good_Results
    #   디렉토리 단 하나뿐이다(다른 디렉토리 노출 금지). 디렉토리가 없으면 마운트를
    #   스킵해 API만으로도 기동되게 한다(무예외). 갤러리는 /reference_screenshots로 받은
    #   파일명을 baseUrl+'/reference_img/'+filename 으로 직접 가져온다.
    if os.path.isdir(_REFERENCE_SCREENSHOTS_DIR):
        app.mount(
            "/reference_img",
            StaticFiles(directory=_REFERENCE_SCREENSHOTS_DIR),
            name="reference_img",
        )

    # 정적 프론트엔드 마운트는 모든 API 라우트(/health, /status, /config/spec, /ws, /)
    #   등록 이후에 한다. /ui 하위 경로에 마운트하므로 위 API 라우트와 WS를 가리지
    #   않는다(StaticFiles는 /ui/* 만 처리). html=True 로 /ui/ 가 index.html을 서빙.
    #   .jsx 는 StaticFiles 기본 content-type으로 서빙되며 브라우저 fetch+Babel 변환에
    #   문제 없다. 프론트엔드 디렉토리가 없으면 API만으로도 기동되도록 가드한다.
    # reviewed 리모델 산출물은 딥링크 라우트(/ui/remodel/condition 등)를
    #   FastAPI 핸들러가 fail-closed로 판정해야 한다. 따라서 /ui/remodel
    #   전체를 StaticFiles로 마운트하지 않고 정적 하위 디렉터리만 분리해
    #   딥링크가 정적 파일 404로 오인되지 않게 한다.
    if os.path.isdir(_REMODEL_FRONTEND_DIR):
        remodel_static_mounts = {
            "src": "ui_remodel_src",
            "styles": "ui_remodel_styles",
            "docs": "ui_remodel_docs",
            "data": "ui_remodel_data",
        }
        for subdir, mount_name in remodel_static_mounts.items():
            static_dir = os.path.join(_REMODEL_FRONTEND_DIR, subdir)
            if os.path.isdir(static_dir):
                app.mount(
                    f"/ui/remodel/{subdir}",
                    StaticFiles(directory=static_dir),
                    name=mount_name,
                )
    if os.path.isdir(_FRONTEND_DIR):
        app.mount("/ui", _FingerprintedStaticFiles(directory=_FRONTEND_DIR, html=True), name="ui")

    return app


def _handle_control(
    msg: ControlPayload,
    manager: LoopProcessManager,
    security: DashboardSecurity,
    dest_db: Optional[str],
    loop_db: Optional[str],
    review_provider: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    match msg:
        case LoopStartControl(config=config):
            return {"action": "start", **manager.start(dict(config))}
        case LoopStopControl():
            return {"action": "stop", **manager.stop()}
        case FinalApprovalControl():
            return {
                "action": "final_approval",
                **_do_final_approval(
                    msg,
                    security,
                    dest_db,
                    loop_db,
                    review_provider,
                ),
            }
        case unreachable:
            assert_never(unreachable)


def _do_final_approval(
    msg: FinalApprovalControl,
    security: DashboardSecurity,
    dest_db: Optional[str],
    loop_db: Optional[str],
    review_provider: Callable[[], Dict[str, Any]],
) -> Dict[str, Any]:
    from ai_strategy_loop.controller.export import (  # noqa: PLC0415
        PRODUCTION_STRATEGY_DB,
        export_winner,
    )

    binding = _approval_binding_payload(review_provider(), loop_db)
    if not binding.get("available"):
        return {
            "status": "error",
            "code": "approval_binding_unavailable",
            "message": str(binding.get("reason") or "approval binding unavailable"),
        }
    if msg.candidate_identity is None:
        return {
            "status": "error",
            "code": "approval_binding_unavailable",
            "message": "candidate_identity_missing",
        }
    supplied = {
        "run_id": msg.run_id,
        "current_gen": msg.current_gen,
        "winner_gen": msg.winner_gen,
        "review_hash": msg.review_hash,
        "evidence_hash": msg.evidence_hash,
        "buy_code_hash": msg.buy_code_hash,
        "sell_code_hash": msg.sell_code_hash,
        "candidate_identity": msg.candidate_identity.identity_dict(),
    }
    if any(binding.get(key) != value for key, value in supplied.items()):
        return {
            "status": "error",
            "code": "stale_approval_binding",
            "message": "run, winner, review, or code evidence changed",
        }
    if not security.claim_final_approval(msg.evidence_hash):
        return {
            "status": "error",
            "code": "approval_already_applied",
            "message": "this reviewed winner was already exported",
        }
    result = export_winner(
        str(binding["winner_buy"]),
        str(binding["winner_sell"]),
        str(dest_db or PRODUCTION_STRATEGY_DB),
        msg.user_buy,
        msg.user_sell,
        loop_db=loop_db,
        expected_buy_code_hash=msg.buy_code_hash,
        expected_sell_code_hash=msg.sell_code_hash,
    )
    if result.get("status") != "ok":
        security.release_final_approval(msg.evidence_hash)
        return result
    return {
        **result,
        "run_id": msg.run_id,
        "current_gen": msg.current_gen,
        "winner_gen": msg.winner_gen,
        "evidence_hash": msg.evidence_hash,
    }


# 모듈 레벨 app — uvicorn `ai_strategy_loop.dashboard.app:app` 로도 띄울 수 있다.
app = create_app()
