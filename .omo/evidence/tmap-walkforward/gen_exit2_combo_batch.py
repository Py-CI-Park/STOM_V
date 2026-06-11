"""exit2 결합 재평가 배치 생성 (2026-06-11 — 승인 순서 ①).

두 알파의 가산 검증: ① 시총 축소(cap 2500 — 격자 mesa 확증) ② exit2 청산
구조(+23% — 니치 지도 1위). 사전선언 결합점 4개 + 동일 배치 비교군 3종
(시드·동결 후보·exit2 기본)을 한 run에서 같은 자로 잰다.

산출: EXIT2C_* 전략 DB 주입 + pairs-exit2-combo.json.
실행(배치는 별도): claude_candidate_batch_eval --pairs-json <이 산출물> ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.template import (  # noqa: E402
    load_template,
    render,
    validate_rendered,
)

EVID = Path(__file__).resolve().parent
SEED_BUY, SEED_SELL = "Tick_B_902_905_Update_2", "Tick_S_902_905_Update_2"
FROZEN_BUY, FROZEN_SELL = "THETA_seed_902905_06_B", "THETA_seed_902905_06_S"
EXIT2_DEF_BUY, EXIT2_DEF_SELL = "TMAP_seed_902905_exit2_000_B", "TMAP_seed_902905_exit2_000_S"


def main() -> int:
    seed = load_template("seed_902905")
    exit2 = load_template("seed_902905_exit2")
    buy_cap3000, _ = render(seed)                      # 시드 기본(=exit2 매수와 동일).
    buy_cap2500, _ = render(seed, {"cap_max": 2500})
    _, sell_def = render(exit2)
    _, sell_t7 = render(exit2, {"take_hard": 7})
    _, sell_t9 = render(exit2, {"take_hard": 9})

    combos = [  # 사전선언 4점 — cap×exit2(기본/익절7/익절9) + 익절7 단독축.
        ("EXIT2C cap2500+e2def", buy_cap2500, sell_def),
        ("EXIT2C cap2500+e2take7", buy_cap2500, sell_t7),
        ("EXIT2C cap2500+e2take9", buy_cap2500, sell_t9),
        ("EXIT2C cap3000+e2take7", buy_cap3000, sell_t7),
    ]

    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    pairs = [  # 동일 배치 비교군 — 같은 자(창·엔진)로 공정 비교.
        {"label": "BASE_SEED", "buy": SEED_BUY, "sell": SEED_SELL},
        {"label": "FROZEN_THETA", "buy": FROZEN_BUY, "sell": FROZEN_SELL},
        {"label": "EXIT2_DEFAULT", "buy": EXIT2_DEF_BUY, "sell": EXIT2_DEF_SELL},
    ]
    for i, (label, buy, sell) in enumerate(combos):
        errors = validate_rendered(buy, sell, "tick")
        assert errors == [], f"{label} 가드 실패: {errors}"
        bn, sn = f"EXIT2C_{i:02d}_B", f"EXIT2C_{i:02d}_S"
        r1 = save_strategy_to_db(db, bn, buy, "buy")
        r2 = save_strategy_to_db(db, sn, sell, "sell")
        assert r1.get("status") == "ok" and r2.get("status") == "ok", (label, r1, r2)
        pairs.append({"label": label, "buy": bn, "sell": sn})

    out = EVID / "pairs-exit2-combo.json"
    out.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} pairs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
