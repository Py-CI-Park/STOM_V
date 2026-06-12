"""R1 (2026-06-12 밤) — 시드 조건 부검(ablation) 배치 생성기: 사상 첫 조건 기여도 실측.

프로세스 v2 계획 §3 R1. 시드 매수의 각 조건(두 시간 분기에서 같은 형태의
조건은 쌍으로)을 하나씩 `elif False:`로 비활성화한 N-1 변형 전수를
같은 자(train 3년 배치)로 측정한다. 해석: 제거로 수익이 '오르면' 데드웨이트
/과적합 조건, '무너지면' 알파 운반 조건. 그룹핑은 숫자 제거 시그니처
(같은 형태·다른 임계 = 한 의미 단위)로 자동.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/gen_r1_ablation_batch.py
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.template import load_template, render, validate_rendered  # noqa: E402

EVID = Path(__file__).resolve().parent
SEED_SELL = "Tick_S_902_905_Update_2"

def main() -> int:
    t = load_template("seed_902905")
    buy, _sell = render(t)
    lines = buy.splitlines()
    groups = {}  # sig -> [line_idx]
    for i, ln in enumerate(lines):
        s = ln.strip()
        cond = None
        if s.startswith("elif not (") and s.rstrip().endswith(":"):
            cond = s
        elif s.startswith("elif ") and "라운드피겨" in s:
            cond = s
        if cond is None:
            continue
        sig = re.sub(r"[\d.]+", "N", re.sub(r"\s+|#.*", "", cond))
        groups.setdefault(sig, []).append(i)

    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
    db = str(bootstrap.LOOP_DB_STRATEGY)
    pairs = [{"label": "BASE_SEED", "buy": "Tick_B_902_905_Update_2", "sell": SEED_SELL}]
    manifest = []
    for gi, (sig, idxs) in enumerate(sorted(groups.items())):
        var_lines = list(lines)
        first_cond = lines[idxs[0]].strip()
        for i in idxs:
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            var_lines[i] = f"{indent}elif False:  # R1 부검 비활성: {lines[i].strip()[:60]}"
        vbuy = "\n".join(var_lines)
        errs = validate_rendered(vbuy, _sell, "tick")
        assert errs == [], (sig, errs)
        bn = f"R1ABL_{gi:02d}_B"
        r = save_strategy_to_db(db, bn, vbuy, "buy")
        assert r.get("status") == "ok" or "exist" in str(r).lower(), (bn, r)
        label = f"R1 -{first_cond[:46]}"
        pairs.append({"label": label, "buy": bn, "sell": SEED_SELL})
        manifest.append({"gen_label": label, "lines": idxs, "cond": first_cond})
    (EVID / "pairs-r1-ablation.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "r1_ablation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK 변형 {len(manifest)}개 + 베이스라인 -> pairs-r1-ablation.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
