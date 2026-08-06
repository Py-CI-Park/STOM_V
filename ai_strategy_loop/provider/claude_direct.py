"""claude_direct provider — Claude 에이전트가 직접 뇌 역할을 하는 스풀 경로.

배경(마스터 웨이브 W1 · 감사 결함 #4): LLM 인증이 끊기면 루프는 zero-LLM 으로
퇴화해 "논리 없는 조건식"을 만든다 — 2026-08-01 실행이 실제로 provider=batch 로
돌아 MDD 139% 로 실패했다. 이 provider 는 **에이전트 세션 자체**를 뇌로 쓴다.

동작(스풀 왕복):
  1. `chat(messages)` 가 요청을 `<spool>/<hash>.request.json` 으로 쓴다.
  2. Claude(에이전트)가 같은 이름의 `<hash>.response.md` 를 채운다.
  3. `chat` 이 응답을 읽어 `ChatResult` 로 돌려준다.

핵심 계약:
  - **요청 해시 결정성**: 같은 messages → 같은 파일명. 프롬프트가 바뀌면 낡은
    응답을 재사용하지 않는다(잘못된 짝짓기가 곧 잘못된 인과 귀속이다).
  - **대기 여부는 호출자 선택**: `wait_seconds=0`(기본)이면 응답이 없을 때
    `ProviderError(retryable=True)` 로 즉시 알린다. 값이 크면 그만큼 폴링한다.
    조용히 빈 문자열을 돌려주지 않는다 — 빈 응답은 생성 실패로 위장되기 쉽다.
  - **네트워크 호출 0**: 외부 API 를 부르지 않는다(쿼터·인증 무관).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import ChatResult, ChatUsage, Provider, ProviderError

logger = logging.getLogger(__name__)

#: 스풀 디렉터리 (환경변수로 오버라이드 — 테스트/병렬 세션 격리용).
ENV_SPOOL_DIR = "STOM_AILOOP_CLAUDE_SPOOL"
ENV_WAIT_SECONDS = "STOM_AILOOP_CLAUDE_WAIT"

_DEFAULT_SPOOL = Path(__file__).resolve().parents[1] / "state" / "claude_spool"

#: 응답 파일이 이 길이 미만이면 "아직 안 채워짐"으로 본다(빈 파일 선점 방지).
_MIN_RESPONSE_CHARS = 8


def spool_dir() -> Path:
    raw = os.getenv(ENV_SPOOL_DIR, "").strip()
    return Path(raw) if raw else _DEFAULT_SPOOL


def request_id(messages: List[Dict[str, str]], model: str = "") -> str:
    """messages + model 의 결정적 해시 — 프롬프트가 바뀌면 id 도 바뀐다."""
    payload = json.dumps(
        {"model": model, "messages": messages}, ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ClaudeDirectProvider(Provider):
    """Claude 에이전트를 뇌로 쓰는 provider (스풀 파일 왕복, 네트워크 0)."""

    name = "claude_direct"
    default_model = "claude-agent-session"

    def __init__(self, config: Any = None) -> None:
        self.config = config
        configured = getattr(config, "claude_spool_dir", "") if config else ""
        self._spool = Path(configured) if configured else spool_dir()
        wait = getattr(config, "claude_wait_seconds", None) if config else None
        if wait is None:
            wait = float(os.getenv(ENV_WAIT_SECONDS, "0") or 0)
        self._wait_seconds = max(0.0, float(wait))

    # -- 경로 -------------------------------------------------------------
    def request_path(self, rid: str) -> Path:
        return self._spool / f"{rid}.request.json"

    def response_path(self, rid: str) -> Path:
        return self._spool / f"{rid}.response.md"

    # -- 본체 -------------------------------------------------------------
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatResult:
        used_model = model or self.default_model
        rid = request_id(messages, used_model)
        self._spool.mkdir(parents=True, exist_ok=True)

        self._write_request(rid, messages, used_model)
        text = self._await_response(rid)

        return ChatResult(
            text=text,
            usage=ChatUsage(),  # 세션 내 수행이라 토큰 과금 집계 대상이 아니다.
            model=used_model,
            raw={"request_id": rid, "spool": str(self._spool)},
        )

    def _write_request(
        self, rid: str, messages: List[Dict[str, str]], model: str,
    ) -> None:
        """요청을 원자적으로 기록한다(부분 쓰기 상태를 에이전트가 읽지 않도록)."""
        path = self.request_path(rid)
        tmp = path.with_suffix(".tmp")
        payload = {
            "request_id": rid,
            "model": model,
            "messages": messages,
            "response_file": self.response_path(rid).name,
            "instruction": (
                "이 요청의 응답을 response_file 에 그대로 쓰세요. "
                "생성기는 응답에서 코드 블록을 추출합니다."
            ),
        }
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    def _await_response(self, rid: str) -> str:
        path = self.response_path(rid)
        deadline = time.monotonic() + self._wait_seconds
        while True:
            text = self._read_response(path)
            if text is not None:
                return text
            if time.monotonic() >= deadline:
                break
            time.sleep(min(1.0, max(0.05, self._wait_seconds / 20)))

        raise ProviderError(
            f"Claude 응답 대기 — 아직 채워지지 않았습니다: {path}",
            retryable=True,
        )

    @staticmethod
    def _read_response(path: Path) -> Optional[str]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        return text if len(text.strip()) >= _MIN_RESPONSE_CHARS else None


def pending_requests(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """응답이 아직 없는 요청 목록 — 에이전트가 무엇을 채워야 하는지 보는 창구."""
    base = Path(directory) if directory else spool_dir()
    if not base.exists():
        return []
    pending: List[Dict[str, Any]] = []
    for request_file in sorted(base.glob("*.request.json")):
        try:
            payload = json.loads(request_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        response_file = base / str(payload.get("response_file") or "")
        if ClaudeDirectProvider._read_response(response_file) is not None:  # noqa: SLF001
            continue
        pending.append({
            "request_id": payload.get("request_id"),
            "model": payload.get("model"),
            "request_path": str(request_file),
            "response_path": str(response_file),
            "message_count": len(payload.get("messages") or []),
        })
    return pending
