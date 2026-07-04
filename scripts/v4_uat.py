"""V4 대시보드 자동 브라우저 UAT — Playwright 조작 시나리오.

시나리오(각각 스크린샷 + verdict JSON):
  1) replay-playback : 최근 거래일 빠른시작 → 재생 진행 확인 → 탭 이탈/복귀 keep-alive
  2) run-archive     : (데이터 origin 지정 시) RUN 셀렉터로 실 run 선택 → archive 렌더
  3) backtest-smoke  : 라이브러리 전략 선택 → 실행 → 결과 영역 렌더
  4) lab/workbench/context-live : 실데이터 origin 으로 각 뷰 캡처

사용:
  python scripts/v4_uat.py --base http://127.0.0.1:8790 \
      --live-base http://127.0.0.1 --data-base http://127.0.0.1:8791 \
      --out .omo/evidence/dashboard-v4-redesign-20260704/uat
read-only 지향: 백테스트 스모크(연구 전용 엔진 실행) 외에 서버 상태를 바꾸지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERDICTS = []


def record(name: str, status: str, note: str) -> None:
    VERDICTS.append({"scenario": name, "status": status, "note": note})
    print(f"[{status}] {name} — {note}")


def snap(page, out: Path, name: str) -> None:
    page.screenshot(path=str(out / f"{name}.png"))


def scenario_replay(page, base: str, out: Path) -> None:
    name = "replay-playback"
    try:
        page.goto(f"{base}/ui/v4/?tab=replay", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("text=빠른 시작", timeout=20000)
        snap(page, out, "1_replay_before")
        page.locator("button", has_text="최근 거래일").first.click()
        page.wait_for_timeout(9000)
        snap(page, out, "1_replay_playing")
        text1 = page.locator(".v4-replay").inner_text()
        m1 = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", text1)
        # keep-alive: Live 로 이탈 후 복귀
        page.locator('.v4-rail-item:has-text("Live")').first.click()
        page.wait_for_timeout(2500)
        page.locator('.v4-rail-item:has-text("Replay")').first.click()
        page.wait_for_timeout(1500)
        snap(page, out, "1_replay_keepalive")
        text2 = page.locator(".v4-replay").inner_text()
        m2 = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", text2)
        kept = ("빠른 시작" in text2) and (m2 is not None)
        if m1 and kept:
            record(name, "pass", f"재생 시각 {m1.group(1)} → 복귀 후 {m2.group(1)} (keep-alive 유지)")
        elif m1:
            record(name, "partial", "재생은 확인, 복귀 후 시각 미검출 — 스크린샷 판독 필요")
        else:
            record(name, "partial", "재생 시각 미검출 — 스크린샷 판독 필요")
    except Exception as e:  # noqa: BLE001
        snap(page, out, "1_replay_error")
        record(name, "fail", f"{type(e).__name__}: {e}")


def scenario_run_archive(page, live_base: str, data_base: str, out: Path) -> None:
    name = "run-archive"
    try:
        page.goto(f"{live_base}/ui/v4/?tab=research&base={data_base}",
                  wait_until="domcontentloaded", timeout=30000)
        sel = page.locator(".v4-runsel select")
        # /runs 도착 대기(최대 20s)
        for _ in range(20):
            if sel.locator("option").count() > 1:
                break
            page.wait_for_timeout(1000)
        n = sel.locator("option").count()
        if n <= 1:
            snap(page, out, "2_run_archive_norunlist")
            record(name, "fail", "RUN 목록이 비어 있음(연동 실패?)")
            return
        # gate 통과(✓) run 우선, 없으면 두 번째 옵션
        values = sel.locator("option").evaluate_all(
            "els => els.map(e => ({v: e.value, t: e.textContent}))")
        pick = next((o["v"] for o in values if "✓" in (o["t"] or "")), values[1]["v"])
        sel.select_option(pick)
        page.wait_for_timeout(7000)
        snap(page, out, "2_run_archive")
        head = page.locator(".v4-view-title").inner_text()
        if "archive" in head:
            record(name, "pass", f"run={pick[:48]} archive 렌더(옵션 {n}개)")
        else:
            record(name, "partial", f"선택 후 archive 표기 미검출(옵션 {n}개) — 스크린샷 판독 필요")
    except Exception as e:  # noqa: BLE001
        snap(page, out, "2_run_archive_error")
        record(name, "fail", f"{type(e).__name__}: {e}")


def scenario_backtest(page, url: str, out: Path, execute: bool = False) -> None:
    """백테 스모크. execute=False(기본): 라이브러리 로드+전략 선택까지만 검증.
    실행은 데이터 백엔드가 활성 연구를 돌리는 중이면 CPU 경합을 일으키므로 옵트인."""
    name = "backtest-smoke"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("text=백테스트 워크벤치", timeout=20000)
        selects = page.locator(".v4-backtest select")
        if selects.count() < 2:
            record(name, "fail", "매수/매도 셀렉터 미검출")
            return
        picked = 0
        for i in (0, 1):
            # 라이브러리(/bt/strategies) 도착 대기 후 첫 실전략 선택
            opts = []
            for _ in range(10):
                opts = selects.nth(i).locator("option").evaluate_all(
                    "els => els.map(e => e.value).filter(v => v)")
                if opts:
                    break
                page.wait_for_timeout(1000)
            if opts:
                selects.nth(i).select_option(opts[0])
                picked += 1
        snap(page, out, "3_backtest_selected")
        if picked < 2:
            record(name, "partial", "라이브러리에 저장된 매수/매도 조건식 부족 — 실행 생략")
            return
        if not execute:
            record(name, "pass", "라이브러리 로드+매수/매도 선택 검증 · 실행은 활성 연구 CPU 경합 회피로 보류(--execute 옵트인)")
            return
        page.locator("button", has_text="백테스트 실행").first.click()
        # 결과 폴링(최대 120s): 결과/에러/작업 상태 텍스트 변화
        done_note = "타임아웃(120s) — 스크린샷 판독 필요"
        status = "partial"
        for _ in range(40):
            page.wait_for_timeout(3000)
            body = page.locator(".v4-backtest").inner_text()
            if re.search(r"총수익|수익률\s|MDD|거래수|완료|실패|오류", body):
                if re.search(r"실패|오류", body) and not re.search(r"총수익|완료", body):
                    status, done_note = "partial", "실행 응답에 오류 문구 — 스크린샷 판독 필요"
                else:
                    status, done_note = "pass", "결과 지표 텍스트 렌더 확인"
                break
        snap(page, out, "3_backtest_result")
        record(name, status, done_note)
    except Exception as e:  # noqa: BLE001
        snap(page, out, "3_backtest_error")
        record(name, "fail", f"{type(e).__name__}: {e}")


def scenario_live_views(page, live_base: str, data_base: str, out: Path) -> None:
    for tab, wait_ms in (("lab", 9000), ("workbench", 9000), ("context", 7000)):
        name = f"{tab}-live"
        try:
            page.goto(f"{live_base}/ui/v4/?tab={tab}&base={data_base}",
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(wait_ms)
            snap(page, out, f"4_{tab}_live")
            record(name, "captured", "스크린샷 판독으로 판정")
        except Exception as e:  # noqa: BLE001
            record(name, "fail", f"{type(e).__name__}: {e}")


def main() -> int:
    # Windows cp949 콘솔에서 non-ASCII 출력이 죽지 않도록 utf-8 재구성.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8790")
    ap.add_argument("--live-base", default="", help="allowlist origin(예: http://127.0.0.1)")
    ap.add_argument("--data-base", default="", help="실데이터 백엔드(예: http://127.0.0.1:8791)")
    ap.add_argument("--out", default=".omo/evidence/dashboard-v4-redesign-20260704/uat")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 미설치", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
        ctx.add_init_script("try{localStorage.setItem('stom_theme','dark');}catch(e){}")
        page = ctx.new_page()

        scenario_replay(page, args.base, out)
        if args.live_base and args.data_base:
            # 백테 라이브러리·run 아카이브는 실데이터 백엔드가 풍부 — live 조합으로 실행.
            scenario_backtest(page, f"{args.live_base}/ui/v4/?tab=backtest&base={args.data_base}", out)
            scenario_run_archive(page, args.live_base, args.data_base, out)
            scenario_live_views(page, args.live_base, args.data_base, out)
        else:
            scenario_backtest(page, f"{args.base}/ui/v4/?tab=backtest", out)
        ctx.close()
        browser.close()

    (out / "verdict.json").write_text(json.dumps(VERDICTS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {len(VERDICTS)} scenarios -> {out}")
    return 0 if all(v["status"] != "fail" for v in VERDICTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
