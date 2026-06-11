"""exit2 비공격(Non-Aggressive) 변형 재검증 배치 생성 (2026-06-12 — 큐 #2).

사전선언(이 docstring이 동결 전 고정 기록):
- 가설: EXIT2C 기각(take9 — train 신기록이 OOS 2026 음전)의 원인은 청산
  공격성이며, exit2 구조 자체의 가치(OOS 2022 시드 +21%)는 비공격 영역
  (take 5~7)에서 일반화될 것이다 — 6/12 핸드오프 §5-2 사전선언 그대로.
- 풀: cap2500 매수 × exit2 매도, take_hard ∈ {5, 6, 7} **3점 한정**.
  take9는 OOS 기각된 후보이므로 재동결 금지(사후 재선택 차단) — 풀에서 제외.
- 선택: 기존 seed_relative_v1 선택기 무수정(같은 자) + n_trials는
  exit2 패밀리 전체(니치 스윕 + 결합 배치) 및 시드 스윕 패밀리 합산.
- OOS: 고정 2022/2026 — exit2 패밀리의 **2번째 사용**임을 공시(증거 가중치
  한계). 통과 시에도 V4 walk-forward 추가 검증을 결정 카드에 병기할 것.
- take5(EXIT2C_00)·take7(EXIT2C_01)은 6/11 결합 배치에서 주입·측정됨 —
  전략 재사용, 같은 배치에서 재측정(같은 자 원칙). take6만 신규 주입.

산출: EXIT2NA_06_B/S 전략 DB 주입 + pairs-exit2na.json.
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


def main() -> int:
    seed = load_template("seed_902905")
    exit2 = load_template("seed_902905_exit2")
    buy_cap2500, _ = render(seed, {"cap_max": 2500})
    _, sell_t6 = render(exit2, {"take_hard": 6})

    errors = validate_rendered(buy_cap2500, sell_t6, "tick")
    assert errors == [], f"take6 가드 실패: {errors}"

    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    bn, sn = "EXIT2NA_06_B", "EXIT2NA_06_S"
    for name, code, kind in ((bn, buy_cap2500, "buy"), (sn, sell_t6, "sell")):
        r = save_strategy_to_db(db, name, code, kind)
        ok = r.get("status") == "ok" or "exist" in str(r).lower()  # 재실행 허용.
        assert ok, (name, r)

    pairs = [  # BASE_SEED는 seed_relative 프로파일용 — 선택 풀에서 출처 제외됨.
        {"label": "BASE_SEED", "buy": SEED_BUY, "sell": SEED_SELL},
        {"label": "EXIT2NA cap2500+e2take5", "buy": "EXIT2C_00_B", "sell": "EXIT2C_00_S"},
        {"label": "EXIT2NA cap2500+e2take6", "buy": bn, "sell": sn},
        {"label": "EXIT2NA cap2500+e2take7", "buy": "EXIT2C_01_B", "sell": "EXIT2C_01_S"},
    ]
    out = EVID / "pairs-exit2na.json"
    out.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} pairs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
