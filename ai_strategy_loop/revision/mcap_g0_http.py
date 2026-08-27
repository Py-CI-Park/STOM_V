"""Small strict JSON client for isolated local G0 dashboard managers."""

from __future__ import annotations

import http.cookiejar
import json
import urllib.error
import urllib.request
from http.client import HTTPResponse
from typing import cast, final

from pydantic import ConfigDict, TypeAdapter

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue], config=ConfigDict(strict=True))


@final
class DashboardClient:
    base_url: str
    _opener: urllib.request.OpenerDirector

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._opener = urllib.request.OpenerDirector()
        self._open_session()

    def _open_session(self) -> None:
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
        response = cast(
            HTTPResponse,
            self._opener.open(f"{self.base_url}/ui/v4", timeout=30),
        )
        try:
            _ = response.read(64)
        finally:
            response.close()

    def _request(
        self, method: str, path: str, body: dict[str, JsonValue] | None
    ) -> dict[str, JsonValue]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method
        )
        request.add_header("Origin", self.base_url)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        response = cast(HTTPResponse, self._opener.open(request, timeout=180))
        try:
            raw = response.read()
        finally:
            response.close()
        return _JSON_OBJECT.validate_json(raw)

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        try:
            return self._request(method, path, body)
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                raise
        self._open_session()
        return self._request(method, path, body)
