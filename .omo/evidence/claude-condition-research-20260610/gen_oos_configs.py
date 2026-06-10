"""동결 아티팩트에서 고정 OOS 실행물을 생성한다(B8 — 동일 창·시드 동시 재측정).

p5-selected-candidate.json(seed_relative_v1 동결)을 읽어:
  - pairs-oos.json: [동결 후보, BASE_SEED] — 두 전략을 **같은 배치/같은 창**에서 평가
    (6/4 p6의 창 불일치(시드 92800 vs AI 93000) 재발 방지).
  - oos-2022-config.json / oos-2026-config.json: 템플릿의 __FROZEN_*__ 자리는 batch
    도구가 pairs로 평가하므로 사용하지 않고, 윈도우/엔진/배팅만 유지한다.

실행(동결 이후에만):
  PYTHONUTF8=1 python .omo/evidence/claude-condition-research-20260610/gen_oos_configs.py
이후:
  python -m ai_strategy_loop.scripts.claude_candidate_batch_eval \
      --pairs-json <evid>/pairs-oos.json --config-json <evid>/oos-2022-config.json \
      --run-id cldgen_oos_2022_20260610
  (2026도 동일; OOS 결과를 본 뒤의 재선택은 금지된다.)
"""
import json
import sys
from pathlib import Path

EVID = Path(__file__).resolve().parent

SEED_BUY = "Tick_B_902_905_Update_2"
SEED_SELL = "Tick_S_902_905_Update_2"


def main() -> int:
    frozen_path = EVID / "p5-selected-candidate.json"
    if not frozen_path.is_file():
        print("동결 아티팩트가 없다 — select_and_freeze.py를 먼저 실행하라. OOS 생성 중단.")
        return 2
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if not frozen.get("selected"):
        print("selected=false — OOS는 정직하게 차단된다(p6-oos-blocked 작성 대상).")
        return 3
    if not frozen.get("oos_excluded", False):
        print("oos_excluded=false — 동결 아티팩트가 오염됐다. 중단.")
        return 4

    cand = frozen["selected_candidate"]
    buy, sell = cand["buy_name"], cand["sell_name"]

    pairs = [
        {"label": "FROZEN", "buy": buy, "sell": sell},
        {"label": "BASE_SEED", "buy": SEED_BUY, "sell": SEED_SELL},
    ]
    (EVID / "pairs-oos.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for year, (start, end) in {"2022": (20220101, 20221231), "2026": (20260101, 20260228)}.items():
        template = json.loads(
            (EVID / f"oos-{year}-config.template.json").read_text(encoding="utf-8")
        )
        template.pop("seed_buy", None)
        template.pop("seed_sell", None)
        template["bt_full_start"] = start
        template["bt_full_end"] = end
        template["_comment"] = (
            f"cldgen fixed OOS {year}: 동결 후보({buy})와 시드를 동일 창(93000)에서 동시 재측정. "
            "OOS 후 재선택 금지."
        )
        (EVID / f"oos-{year}-config.json").write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"OK frozen={buy}/{sell} -> pairs-oos.json, oos-2022-config.json, oos-2026-config.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
