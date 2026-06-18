"""R4 (2026-06-13) — 미니멀 전진 선택: R1 알파 운반자만 남긴 최소 골격.

방법: R1 부검의 역방향 — 알파 운반자 그룹만 '남기고' 나머지 신호 조건을
전부 elif False 비활성. M0=상위 5(회전율a·누적흐름하한·고가근접·당일거래
대금·시가대비등락율), M1=상위 9(+매수공격·잔량밴드·거래대금폭발·각도).
비계(가격대·등락율·시총·VI·라운드피겨)는 유지. 기본 θ(시드 원형)로 측정.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

EVID = Path(__file__).resolve().parent
KEEP5 = ["회전율", "누적초당매수수량(30) * 0.5", "고가 - 저가", "당일거래대금 >", "시가대비등락율"]
KEEP9 = KEEP5 + ["초당매수수량 > 매도총잔량", "매도총잔량 > 매수총잔량", "초당거래대금 / 초당거래대금평균", "당일거래대금각도"]
SCAFFOLD = ["현재가 <=", "< 등락율 <=", "고저평균대비등락율", "VI아래5호가", "라운드피겨", "시가등락율", "체결강도", "초당순매수금액", "전일비", "누적초당매도수량(30) * 1.0 <", "매도총잔량 * 0.10 <", "초당거래대금 > 초당거래대금N"]

def keep_only(lines, keeps):
    out = list(lines)
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not (s.startswith("elif not (") or (s.startswith("elif ") and "라운드피겨" in s)):
            continue
        # 비계 중 구조 유지 대상(가격대·등락율·시총·VI·라운드피겨·시가등락율)은 보존
        if any(k in s for k in ["현재가 <=", "< 등락율 <=", "VI아래5호가", "라운드피겨", "시가등락율"]):
            continue
        if any(k in s for k in keeps):
            continue
        indent = ln[: len(ln) - len(ln.lstrip())]
        out[i] = f"{indent}elif False:  # R4 미니멀 제외: {s[:48]}"
    return "\n".join(out)

def main() -> int:
    t = load_template("seed_902905")
    buy, sell = render(t)
    lines = buy.splitlines()
    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
    db = str(bootstrap.LOOP_DB_STRATEGY)
    pairs = [{"label": "BASE_SEED", "buy": "Tick_B_902_905_Update_2", "sell": "Tick_S_902_905_Update_2"}]
    for name, keeps, label in (("R4M0", KEEP5, "R4 M0 top5"), ("R4M1", KEEP9, "R4 M1 top9")):
        code = keep_only(lines, keeps)
        errs = validate_rendered(code, sell, "tick")
        assert errs == [], (name, errs)
        r = save_strategy_to_db(db, f"{name}_B", code, "buy")
        assert r.get("status") == "ok" or "exist" in str(r).lower()
        rs = save_strategy_to_db(db, f"{name}_S", sell, "sell")
        assert rs.get("status") == "ok" or "exist" in str(rs).lower()
        pairs.append({"label": label, "buy": f"{name}_B", "sell": f"{name}_S"})
    (EVID / "pairs-r4-minimal.json").write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} pairs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
