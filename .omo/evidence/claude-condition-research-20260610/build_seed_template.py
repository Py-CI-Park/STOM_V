# -*- coding: utf-8 -*-
"""시드 902/905 코드 → TMAP 템플릿 JSON 기계 생성 (G1 빌더, 연구 도구).

치환마다 기대 횟수를 검증하고, 마지막에 기본값 렌더 == 원본(identity)을 확인한다.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

BUY = (REPO / ".omo/tmp_seed_buy.txt").read_text(encoding="utf-8")
SELL = (REPO / ".omo/tmp_seed_sell.txt").read_text(encoding="utf-8")

# (원문, 슬롯 치환문, 기대 횟수, 대상)
REPL = [
    ("시가총액 < 3000", "시가총액 < {cap_max}", 2, "buy"),
    ("전일동시간비 > 0", "전일동시간비 > {prev_ratio_min}", 2, "buy"),
    ("체결강도 >= 50 and 체결강도 <= 300", "체결강도 >= {strength_min} and 체결강도 <= {strength_max}", 2, "buy"),
    ("90200 <= 시분초 < 90500", "90200 <= 시분초 < {window_end}", 1, "buy"),
    ("당일거래대금각도(30) > 5 and", "당일거래대금각도(30) > {angle_min_902} and", 1, "buy"),
    ("초당거래대금 / 초당거래대금평균(30) > 3.0", "초당거래대금 / 초당거래대금평균(30) > {burst_min_902}", 1, "buy"),
    ("2 < 회전율", "{turnover_min_902} < 회전율", 1, "buy"),
    ("수익률 <= -2.0", "수익률 <= {stop_deep}", 1, "sell"),
    ("수익률 >= 5 or 수익률 <= -5.0", "수익률 >= {take_hard} or 수익률 <= {stop_hard}", 1, "sell"),
    ("최고수익률 > 6 and 최고수익률 * 0.6 >= 수익률",
     "최고수익률 > {trail_start} and 최고수익률 * {trail_keep} >= 수익률", 1, "sell"),
]

PARAMS = [
    {"name": "cap_max", "default": 3000, "values": [1500, 2000, 2500, 3000, 4000, 6000, 10000],
     "side": "buy", "note": "시총 상한(양 분기) — counterfactual: <=1705~2100이 손익 104~106%"},
    {"name": "prev_ratio_min", "default": 0, "values": [0, 100, 300, 500, 1000, 2000, 5000],
     "side": "buy", "note": "전일동시간비 하한 — 시드 부검 최강 판별자(승 14,705 vs 패 4,956)"},
    {"name": "strength_min", "default": 50, "values": [50, 70, 90, 110, 130, 150],
     "side": "buy", "note": "체결강도 하한(양 분기) — C7 부검: 승 155.9 vs 패 135"},
    {"name": "strength_max", "default": 300, "values": [200, 250, 300, 350], "side": "buy", "note": ""},
    {"name": "window_end", "default": 90500, "values": [90300, 90500, 90700, 91000, 91500, 92000],
     "side": "buy", "note": "905 분기 종료 시각 — '시간 확대' 축(09:05→09:20)"},
    {"name": "angle_min_902", "default": 5, "values": [3, 5, 8, 10, 15], "side": "buy", "note": "902 거래대금각도 하한"},
    {"name": "burst_min_902", "default": 3.0, "values": [2.0, 2.5, 3.0, 3.5, 4.0], "side": "buy", "note": "902 거래대금 폭발 배수"},
    {"name": "turnover_min_902", "default": 2, "values": [1, 1.5, 2, 3, 4], "side": "buy", "note": "902 회전율 하한"},
    {"name": "stop_deep", "default": -2.0, "values": [-1.0, -1.5, -2.0, -2.5, -3.0],
     "side": "sell", "note": "깊은손절 임계 — 부검: 이 규칙 11건 전패(평균 -4.2%)"},
    {"name": "take_hard", "default": 5, "values": [3, 4, 5, 7, 9], "side": "sell", "note": "하드 익절"},
    {"name": "stop_hard", "default": -5.0, "values": [-3.0, -4.0, -5.0, -7.0], "side": "sell", "note": "하드 손절"},
    {"name": "trail_start", "default": 6, "values": [2, 3, 4, 6, 8],
     "side": "sell", "note": "트레일링 시작 — 부검: MFE 2.7% 중 0.56%만 실현"},
    {"name": "trail_keep", "default": 0.6, "values": [0.5, 0.6, 0.7, 0.8], "side": "sell", "note": "트레일링 유지 비율"},
]


def main() -> int:
    buy, sell = BUY, SELL
    for src, dst, expect, side in REPL:
        target = buy if side == "buy" else sell
        count = target.count(src)
        assert count == expect, f"치환 횟수 불일치: {src!r} {count} != {expect}"
        if side == "buy":
            buy = buy.replace(src, dst)
        else:
            sell = sell.replace(src, dst)

    defaults = {p["name"]: p["default"] for p in PARAMS}
    assert buy.format(**defaults) == BUY, "identity 실패(buy)"
    assert sell.format(**defaults) == SELL, "identity 실패(sell)"

    out = {
        "name": "seed_902905",
        "timeframe": "tick",
        "source": "Tick_B_902_905_Update_2 / Tick_S_902_905_Update_2",
        "description": "시드 902/905 모수화 템플릿(13θ) — 구조 보존, 임계값만 슬롯. "
                       "window_end가 시간 확대 축. 기본값 렌더=원본 identity 보증.",
        "buy_code": buy,
        "sell_code": sell,
        "params": PARAMS,
    }
    path = REPO / "ai_strategy_loop/tmap/templates/seed_902905.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {path} (slots={len(PARAMS)}, identity verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
