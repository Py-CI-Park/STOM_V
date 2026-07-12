from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession


ORIGIN = "http://127.0.0.1:8770"


class AuthorizedDashboardClient(TestClient):
    def websocket_connect(
        self,
        url: str,
        subprotocols: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> WebSocketTestSession:
        target = f"ws://127.0.0.1:8770{url}" if url.startswith("/") else url
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Origin", ORIGIN)
        return super().websocket_connect(
            target,
            subprotocols=subprotocols,
            headers=headers,
            **kwargs,
        )


def authorized_dashboard_client(app: FastAPI) -> AuthorizedDashboardClient:
    client = AuthorizedDashboardClient(app, base_url=ORIGIN)
    client.headers.update({"Origin": ORIGIN})
    response = client.get("/ui/v4/")
    if response.status_code != 200:
        raise AssertionError(f"dashboard bootstrap failed: {response.status_code}")
    return client
