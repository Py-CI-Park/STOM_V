"""V4 아카이브 시각화 스윕 — wt-dev 과거 연구 run 을 V4 로 직접 구동·캡처.

지정한 과거 run 을 RUN 셀렉터로 선택(아카이브 모드)한 뒤, 그 run 컨텍스트로
Research(접이식 포함 full-page)·Lab·Workbench·Context 를 순회 캡처한다.
selectedRun 은 셸 state 라 탭 전환에도 유지된다(V4 설계 검증 포인트).

사용:
  python scripts/v4_archive_check.py --live-base http://127.0.0.1 \
      --data-base http://127.0.0.1:8791 \
      --runs run_id_1,run_id_2 --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESULTS = []


def log(run_tag: str, step: str, ok: bool, note: str) -> None:
    RESULTS.append({"run": run_tag, "step": step, "ok": ok, "note": note})
    print(f"[{'ok' if ok else 'CHECK'}] {run_tag} {step}: {note}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-base", default="http://127.0.0.1")
    ap.add_argument("--data-base", default="http://127.0.0.1:8791")
    ap.add_argument("--runs", required=True, help="콤마 구분 run_id 목록")
    ap.add_argument("--out", default=".omo/evidence/dashboard-v4-redesign-20260704/archive-check")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run_ids = [r.strip() for r in args.runs.split(",") if r.strip()]

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        ctx.add_init_script("try{localStorage.setItem('stom_theme','dark');}catch(e){}")
        page = ctx.new_page()

        for idx, rid in enumerate(run_ids, 1):
            tag = f"run{idx}"
            page.goto(f"{args.live_base}/ui/v4/?tab=research&base={args.data_base}",
                      wait_until="domcontentloaded", timeout=30000)
            sel = page.locator(".v4-runsel select")
            for _ in range(25):
                if sel.locator("option").count() > 1:
                    break
                page.wait_for_timeout(1000)
            if sel.locator("option").count() <= 1:
                log(tag, "run-list", False, "RUN 목록 미도착")
                continue
            try:
                sel.select_option(rid)
            except Exception as e:  # noqa: BLE001
                log(tag, "select", False, f"{rid} 선택 실패: {type(e).__name__}")
                continue
            page.wait_for_timeout(8000)
            head = page.locator(".v4-view-title").inner_text()
            log(tag, "archive-mode", "archive" in head, f"{rid[:52]} · head='{head[:60]}'")
            page.screenshot(path=str(out / f"{tag}_research_full.png"), full_page=True)
            log(tag, "research", True, "full-page 캡처(접이식 포함)")

            for tab, label, wait_ms in (("History", "history", 8000), ("Lab", "lab", 9000),
                                        ("Bench", "workbench", 9000), ("Context", "context", 7000)):
                page.locator(f'.v4-rail-item:has-text("{tab}")').first.click()
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(out / f"{tag}_{label}.png"))
                log(tag, label, True, "캡처")
            # 다음 run 을 위해 Live 복귀
            page.locator('.v4-rail-item:has-text("Live")').first.click()
            page.wait_for_timeout(1500)

        ctx.close()
        browser.close()

    (out / "results.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
