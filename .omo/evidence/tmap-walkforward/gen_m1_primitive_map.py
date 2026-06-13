"""M1 (2026-06-13) — min 진단 프리미티브 지도: 6 프리미티브 × 6 시간밴드 = 36셀.

로드맵 M-트랙 1단계. 기존 min 실패 4종은 '완성 구조'였음 — 프리미티브 단위의
시간대별 기대값 지도는 미시도. 목적: "몇 시에 어떤 신호가 돈이 되나"의 기초
지도. train 2025-04~12만 사용(프로토콜), 진입 ~14:50, 강제청산 14:59.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.template import validate_rendered  # noqa: E402

EVID = Path(__file__).resolve().parent

PRIMS = {
    "P1신고가": "현재가 > 최고현재가(30, 1)",
    "P2이평재탈환": "현재가 >= 이동평균(20, 1) and 최저현재가(5) < 이동평균(20, 1)",
    "P3대금급증": "분당거래대금 > 분당거래대금평균(20, 1) * 3",
    "P4강도급등": "체결강도 > 체결강도평균(20, 1) * 1.2 and 분당매수수량 > 분당매도수량",
    "P5동시간활성": "전일동시간비 >= 300 and 분당매수수량 > 분당매도수량",
    "P6연속양봉": "현재가 > 현재가N(1) and 현재가N(1) > 현재가N(2) and 현재가N(2) > 현재가N(3)",
}
BANDS = [("B0900", 90100, 100000), ("B1000", 100000, 110000), ("B1100", 110000, 120000),
         ("B1200", 120000, 133000), ("B1330", 133000, 143000), ("B1430", 143000, 145000)]

SELL = """매도 = False
if 시분초 >= 145900:
    매도 = True
elif 수익률 >= 5.0 or 수익률 <= -3.0:
    매도 = True
elif 보유시간 >= 3600:
    매도 = True
elif 최고수익률 > 3 and 최고수익률 * 0.6 >= 수익률:
    매도 = True
if 매도:
    self.Sell()
"""

def buy_code(cond: str, lo: int, hi: int) -> str:
    return f"""매수 = True
if not (관심종목 == 1):
    매수 = False
elif not ({lo} <= 시분초 < {hi}):
    매수 = False
elif not (데이터길이 >= 31):
    매수 = False
elif not (1000 < 현재가 <= 100000):
    매수 = False
elif not (0 < 등락율 <= 25):
    매수 = False
elif not ({cond}):
    매수 = False

if 매수:
    self.Buy()
"""

def main() -> int:
    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
    db = str(bootstrap.LOOP_DB_STRATEGY)
    pairs = []
    sell_saved = False
    for pname, cond in PRIMS.items():
        for bname, lo, hi in BANDS:
            code = buy_code(cond, lo, hi)
            errs = validate_rendered(code, SELL, "min")
            assert errs == [], (pname, bname, errs)
            bn = f"M1_{pname}_{bname}_B"
            r = save_strategy_to_db(db, bn, code, "buy")
            assert r.get("status") == "ok" or "exist" in str(r).lower(), (bn, r)
            if not sell_saved:
                rs = save_strategy_to_db(db, "M1_COMMON_S", SELL, "sell")
                assert rs.get("status") == "ok" or "exist" in str(rs).lower()
                sell_saved = True
            pairs.append({"label": f"M1 {pname} {bname}", "buy": bn, "sell": "M1_COMMON_S"})
    (EVID / "pairs-m1-primitive.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} cells")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
