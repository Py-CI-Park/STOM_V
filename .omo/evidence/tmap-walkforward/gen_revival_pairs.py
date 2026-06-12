"""S4 (2026-06-12) — 패자부활 재검증 배치 생성기.

`rejected_registry.json`의 **전원**(선별 없음)에 비교군(시드·챔피언)을 더해
pairs-revival.json을 만든다. 신규(미접촉) 데이터 창이 생겼을 때만 실행한다 —
같은 데이터 재선택 금지와 양립하는 유일한 형태(새 데이터·전수 자동).

사용 (신규 데이터 병합 후):
  1) PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/gen_revival_pairs.py
  2) oos-2026-config.template.json 사본에 신규 창(bt_full_start/end)만 지정
  3) python -m ai_strategy_loop.scripts.claude_candidate_batch_eval \
       --pairs-json <evid>/pairs-revival.json --config-json <신규 창 config> \
       --run-id revival_oos_<창>_<날짜>
판정: p0 §5 + 시드 상대 비교(같은 배치 동시 재측정). 결과는 결정 카드 추록.
"""
from __future__ import annotations

import json
from pathlib import Path

EVID = Path(__file__).resolve().parent
SEED_BUY, SEED_SELL = "Tick_B_902_905_Update_2", "Tick_S_902_905_Update_2"
CHAMPION_BUY, CHAMPION_SELL = "THETA_seed_902905_06_B", "THETA_seed_902905_06_S"


def build_pairs(registry: dict) -> list:
    """비교군 + 레지스트리 전원. 순수 함수 — 선별 로직이 없음을 코드로 보증."""
    pairs = [
        {"label": "BASE_SEED", "buy": SEED_BUY, "sell": SEED_SELL},
        {"label": "FROZEN_THETA", "buy": CHAMPION_BUY, "sell": CHAMPION_SELL},
    ]
    for r in registry["rejected"]:
        pairs.append({"label": r["label"], "buy": r["buy"], "sell": r["sell"]})
    return pairs


def main() -> int:
    registry = json.loads(
        (EVID / "rejected_registry.json").read_text(encoding="utf-8")
    )
    pairs = build_pairs(registry)
    out = EVID / "pairs-revival.json"
    out.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(pairs)} pairs (비교군 2 + 기각자 {len(pairs) - 2}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
