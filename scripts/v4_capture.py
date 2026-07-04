"""V4 대시보드 스크린샷 캡처 — Playwright(Chrome 채널) 시각검증 루프용.

사용:
    python scripts/v4_capture.py --base http://127.0.0.1:8790 --out .omo/evidence/dashboard-v4-redesign-20260704/captures
    # wt-dev 실데이터 백엔드 연동(선택): --data-base http://127.0.0.1:8791
    # 특정 뷰/테마만: --views research,backtest --themes dark

7뷰(research/backtest/replay/lab/workbench/audit/context) × 테마(dark/light)를
{out}/{view}_{theme}.png 로 저장한다. 테마는 로드 전 localStorage(stom_theme) 주입.
read-only: 서버/데이터를 변경하지 않는다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

VIEWS = ["research", "backtest", "replay", "lab", "workbench", "audit", "context"]
THEMES = ["dark", "light"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8790", help="V4 프론트를 서빙하는 서버 origin")
    ap.add_argument("--data-base", default="", help="백엔드 데이터 origin(?base= 오버라이드, 예: wt-dev 8791)")
    ap.add_argument("--out", default=".omo/evidence/dashboard-v4-redesign-20260704/captures")
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--themes", default=",".join(THEMES))
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--settle-ms", type=int, default=2500, help="networkidle 후 추가 대기(차트 도장)")
    ap.add_argument("--full-page", action="store_true", help="전체 페이지 캡처(기본: viewport)")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 미설치: pip install playwright", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    views = [v for v in args.views.split(",") if v]
    themes = [t for t in args.themes.split(",") if t]
    saved = []

    with sync_playwright() as p:
        # 로컬 Chrome 채널 사용(브라우저 다운로드 불필요). 없으면 chromium 폴백.
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        for theme in themes:
            ctx = browser.new_context(viewport={"width": args.width, "height": args.height},
                                      device_scale_factor=1)
            ctx.add_init_script(f"try{{localStorage.setItem('stom_theme','{theme}');}}catch(e){{}}")
            page = ctx.new_page()
            for view in views:
                url = f"{args.base}/ui/v4/?tab={view}"
                if args.data_base:
                    url += f"&base={args.data_base}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:  # noqa: BLE001 — networkidle 미도달(WS 폴링)이어도 캡처 진행
                    print(f"[warn] {view}/{theme}: goto {type(e).__name__} — 계속 진행", file=sys.stderr)
                page.wait_for_timeout(args.settle_ms)
                dest = out / f"{view}_{theme}.png"
                page.screenshot(path=str(dest), full_page=args.full_page)
                saved.append(dest)
                print(f"saved {dest}")
            ctx.close()
        browser.close()

    print(f"done: {len(saved)} captures -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
