"""US-007 — `python -m ai_strategy_loop` 엔트리포인트 (대시보드 기동).

uvicorn으로 FastAPI 대시보드 백엔드를 띄운다 (host 127.0.0.1, 기본 port 8770).
프론트엔드(HTML/JS)는 Claude Design으로 별도 생성되어 별도 origin에서 서빙되며,
이 백엔드는 CORS를 모두 허용한다.

루프 CLI(`python -m ai_strategy_loop.controller.loop`)는 그대로 동작한다 —
이 엔트리포인트는 대시보드 전용이다.
"""

from __future__ import annotations

# bootstrap을 가장 먼저 — cli.*/utility.* import 전 env 격리.
import ai_strategy_loop.bootstrap  # noqa: E402,F401

import argparse  # noqa: E402


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai_strategy_loop",
        description="STOM AI strategy loop 대시보드 (FastAPI + WebSocket 백엔드)",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="바인드 호스트 (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8770,
                        help="바인드 포트 (default: 8770)")
    args = parser.parse_args(argv)

    import uvicorn  # noqa: PLC0415

    print(f"[DASHBOARD] starting on http://{args.host}:{args.port}", flush=True)
    print(f"[DASHBOARD] health: http://{args.host}:{args.port}/health", flush=True)
    uvicorn.run(
        "ai_strategy_loop.dashboard.app:app",
        host=args.host, port=args.port, log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
