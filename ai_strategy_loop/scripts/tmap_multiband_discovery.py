"""TMAP 다밴드 자율 발굴 루프 (밤샘 연구 드라이버) — 2026-06-14.

자율 개선 조건식 탐색·생성 시스템의 "에이전트 하네스":
  생성(다밴드) → [스모크 2분기 선별] → [전체기간 train] → [OOS] 단계 격상
  → 기록 → 반복(마감/최대횟수까지).

왜 단계 격상인가:
  전체기간(3년 tick / 11개월 min) 백테는 느려서 모든 후보에 돌리면 처리량이 죽는다.
  그래서 (1)싼 2분기 스모크로 대부분을 거르고 (2)통과분만 전체기간 train (3)그것도
  통과하면 OOS로 — THETA가 받은 실제 검증 바. 짧은 스모크만으론 불충분(gen19: 2분기
  통과했으나 3년 train −2.5M 확정 기각 = 거짓양성). 그래서 PROMISING은 전체기간+OOS까지.

규율:
  - 기존 CLI(생성·tmap_sweep) subprocess 재사용 → 엔진·하드게이트 무수정·무재구현.
  - 한 반복 실패가 루프를 못 막는다(try/except·흡수).
  - 스모크 게이트 = ★같은 좌표 양분기 흑자(min(q1,q2)>0, 선택편향 차단).
  - 검색 폭: 핵심축 5개·40점(넓게). 전체기간 검증은 robust 코너 슬롯만(빠르게).
  - tick·min config 자동 선택. 각 백테는 fresh prepare(엔진 새 구동).

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_multiband_discovery \
      --max-iters 40 --deadline-hhmm 0700 \
      --out .omo/evidence/tmap-walkforward/multiband_overnight.md
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
EVID = REPO / ".omo/evidence/tmap-walkforward"
TEMPLATES = REPO / "ai_strategy_loop/tmap/templates"

# 2분기 스모크(빠른 선별).
CONFIGS = {
    "tick": [EVID / "smoke-2025q1-e32-config.json", EVID / "smoke-2023q2-e32-config.json"],
    "min": [EVID / "min-smoke-2025m05-e32-config.json", EVID / "min-smoke-2025m09-e32-config.json"],
}
# 전체기간 train(통과분만).
FULL_CONFIGS = {
    "tick": EVID / "train-3y-e32-config.json",        # 2023~2025 3년
    "min": EVID / "min-fullsession-e32-config.json",  # 2025-04~2026-02 전체
}
# OOS(전체기간 통과분만). min은 fullsession이 2026을 이미 포함 → min-oos는 recency 점검(진성 OOS 아님).
OOS_CONFIGS = {
    "tick": [EVID / "oos-2022-e32-config.json", EVID / "oos-2026-e32-config.json"],
    "min": [EVID / "min-oos-config.json"],
}

_KEY_KW = ("cap", "burst", "strength", "prev", "turnover", "angle", "money", "rate", "ratio", "len")

TRACKS = [
    ("tick_new", (
        "시초 소형주 첫 돌파(밴드1: 09:00~09:05, 시총 소형, 거래대금 폭발+체결강도)와 "
        "그 이후 다른 시간대·다른 시총대의 독립 재발화(밴드2: 09:05 이후, 중대형, 직전고가 "
        "돌파+거래대금 재가속)를 한 조건식의 if/elif 이산 분기로 결합한다. 각 밴드는 자기 "
        "강한 AND 게이트를 갖고 점수합산이 아니다. 시간창은 겹치지 않는다.")),
    ("tick_anchor", (
        "밴드1은 검증된 THETA 구조를 고정 차용한다: 09:00~09:05, 시가총액 소형(2500억 이하), "
        "거래대금 폭발(초당거래대금/초당거래대금평균(30) 배수)+높은 체결강도+전일동시간비. "
        "밴드2는 09:05 이후 다른 시총대에서 직전고가 돌파 재발화를 독립 강한 게이트로 탐색한다. "
        "if/elif 이산 분기, 점수합산 금지, 시간창 비중첩.")),
    ("min_new", (
        "분봉(min) 타임프레임. 분당 변수(분당거래대금·분당매수수량·누적분당매수수량(N))만 사용. "
        "오전 수급 지속(밴드1: 09:00~10:00 시총 중형, 분당거래대금 재가속+누적 매수우위)과 "
        "오후 재가속(밴드2: 13:00~15:00 다른 시총, 직전 분봉고가 돌파)을 한 조건식의 if/elif "
        "이산 분기로. 각 밴드 독립 강한 게이트, 점수합산 금지, 시간창 비중첩.")),
]


def run_cmd(args: List[str], timeout: int) -> Tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT after {timeout}s: {exc}"
    except Exception as exc:  # noqa: BLE001
        return 1, f"run_cmd raised: {exc}"


def build_feedback(records: List[Dict], max_avoid: int = 12) -> str:
    """[P2] 누적 ledger에서 다음 생성용 회피/선호 컨텍스트를 조립(데이터 주도).

    무작위 추첨을 "학습하는 발굴"로 바꾸는 핵심(누수6). no-go 구조는 회피,
    스모크 양분기 신호 코너는 선호로 제시. 빈 records면 빈 문자열(무상태 degrade).
    """
    if not records:
        return ""
    # ★과적합-인지(2026-06-15 pilot 교훈): smoke-pass는 2분기 흑자였으나 *전체기간 과적합*
    #   (−10~−21M)이라 *선호 아니라 회피*다. 전에 prefer에 넣어 과적합을 증폭한 결함 수정.
    #   전체기간 생존(train-*/PROMISING)만 선호.
    avoid_flood, avoid_overfit, prefer = [], [], []
    nogo = overfit = survivor = 0
    for r in records:
        ev = r.get("eval") or {}
        v = ev.get("verdict")
        name = r.get("template")
        rob = ev.get("robust") or {}
        if v == "no-go" and name:
            nogo += 1
            avoid_flood.append(name)
        elif v == "smoke-pass":  # 2분기 통과·전체기간 과적합 → ★회피(선호 아님)
            overfit += 1
            avoid_overfit.append(f"{name}:{rob['label']}" if (name and rob.get("label")) else (name or "?"))
        elif v in ("train-only", "train-pass", "★PROMISING"):  # 전체기간 생존 → 선호
            survivor += 1
            if name and rob.get("label"):
                prefer.append(f"{name}:{rob['label']}(q1={rob.get('q1')},q2={rob.get('q2')})")
    lines = [f"누적 {len(records)}후보 — no-go(홍수) {nogo}, 2분기과적합 {overfit}, 전체기간생존 {survivor}."]
    if avoid_flood:
        lines.append("[회피-홍수] 재백테 음전(느슨 홍수형) 구조 재제출 금지: "
                     + ", ".join(avoid_flood[-max_avoid:]))
    if avoid_overfit:
        lines.append("[회피-과적합] 2분기 흑자였으나 전체기간 과적합(−)한 좌표. 같은 탐색밴드 재추구 "
                     "금지: " + ", ".join(avoid_overfit[-8:]))
    if prefer:
        lines.append("[선호] 전체기간 생존 좌표(일반화 확인됨): " + "; ".join(prefer[-6:]))
    else:
        lines.append("[선호] 아직 전체기간 생존 코너 없음 — 검증앵커(THETA: 09:00~09:05 소형주 "
                     "cap≤2500·거래대금폭발·높은 체결강도)를 밴드1로 고정. ★탐색밴드는 2분기만 맞추는 "
                     "과적합을 피하고 *전체기간 일반화*되게 더 보수적·좁은 게이트로.")
    lines.append("핵심: 홍수형 반복 금지 + **2분기 과적합 코너 추구 금지**. 앵커 고정 + 전체기간 "
                 "일반화되는 보수적 탐색밴드를 노려라.")
    return "\n".join(lines)


def generate(principle: str, timeout: int = 300, feedback_text: str = "") -> Tuple[Optional[str], str]:
    args_list = [
        sys.executable, "-m", "ai_strategy_loop.scripts.gen_template_hypothesis",
        "--provider", "gpt_auth", "--write", "--max-retries", "2", "--principles", principle,
    ]
    if feedback_text:  # [P2] 유상태: 회피/선호를 파일로 전달.
        fb_path = EVID / "_discovery_feedback.txt"
        fb_path.write_text(feedback_text, encoding="utf-8")
        args_list += ["--feedback-file", str(fb_path)]
    rc, out = run_cmd(args_list, timeout=timeout)
    m = re.search(r"\[저장\]\s+(.+\.json)", out)
    return (Path(m.group(1).strip()).stem if (rc == 0 and m) else None), out[-600:]


def _load_template(name: str) -> Dict:
    return json.loads((TEMPLATES / f"{name}.json").read_text(encoding="utf-8"))


def auto_key_slots(name: str, max_slots: int = 5) -> List[str]:
    """조이는 축으로 쓸 buy-side 슬롯 최대 5개(키워드+후보값 많은 순) — 검색 폭 확대."""
    try:
        params = _load_template(name).get("params", [])
    except Exception:  # noqa: BLE001
        return []
    buy = [p for p in params if p.get("side", "buy") == "buy" and len(p.get("values", [])) >= 3]
    buy.sort(key=lambda p: (any(k in p["name"].lower() for k in _KEY_KW), len(p.get("values", []))),
             reverse=True)
    return [p["name"] for p in buy[:max_slots]]


def sweep(name: str, config: Path, run_id: str, params_csv: str,
          max_points: int = 40, timeout: int = 1500) -> Optional[Dict]:
    """tmap_sweep → {status, ok_points, best, baseline, pmap{label:profit}}|status err."""
    manifest = EVID / f"{run_id}_manifest.json"
    args = [sys.executable, "-m", "ai_strategy_loop.scripts.tmap_sweep",
            "--template", name, "--config-json", str(config), "--run-id", run_id,
            "--max-points", str(max_points), "--manifest-out", str(manifest)]
    if params_csv:
        args += ["--params", params_csv]
    rc, out = run_cmd(args, timeout=timeout)
    if not manifest.is_file():
        return {"status": "error", "log": out[-400:]}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "log": f"manifest parse: {exc}"}
    pts = [p for p in data.get("points", [])
           if p.get("status") == "ok" and isinstance(p.get("profit"), (int, float))]
    if not pts:
        return {"status": "no_ok_points", "ok_points": 0, "log": out[-300:]}
    best = max(pts, key=lambda p: p["profit"])
    base = next((p for p in data.get("points", []) if p.get("param") == "__default__"), None)
    return {"status": "ok", "ok_points": len(pts), "best": best, "baseline": base,
            "pmap": {p["label"]: p["profit"] for p in pts}}


def _slot_of(label: str) -> Optional[str]:
    if label and label.startswith("TMAP ") and "=" in label:
        return label[len("TMAP "):].split("=")[0].strip()
    return None  # "TMAP __default__" 등.


def validate_on(name: str, config: Path, run_id: str, robust_label: str,
                timeout: int = 2400) -> Dict:
    """전체기간/OOS config에서 robust 코너(같은 라벨)의 손익만 빠르게 확인."""
    slot = _slot_of(robust_label)
    res = sweep(name, config, run_id, slot or "", max_points=(12 if slot else 1), timeout=timeout)
    if not res or res.get("status") != "ok":
        return {"status": (res or {}).get("status", "error"), "profit": None}
    pmap = res.get("pmap") or {}
    prof = pmap.get(robust_label)
    if prof is None:  # 라벨 미재현 시 baseline 또는 best로 폴백.
        prof = (res.get("baseline") or {}).get("profit")
    return {"status": "ok", "profit": prof, "config": config.name}


def evaluate(name: str, timeframe: str, iter_no: int) -> Dict:
    """단계 격상: 스모크(같은좌표 양분기) → 전체기간 train → OOS. 각 단계 게이트."""
    tag = f"mbdisc_{iter_no:03d}"
    cfgs = CONFIGS.get(timeframe, CONFIGS["tick"])
    slots = auto_key_slots(name)
    params_csv = ",".join(slots)
    out: Dict = {"slots": slots, "verdict": "no-go", "both_positive": False,
                 "robust": None, "smoke": [None, None], "full": None, "oos": []}

    # 1) 스모크 q1
    q1 = sweep(name, cfgs[0], f"{tag}_q1", params_csv)
    q1map = (q1 or {}).get("pmap") or {}
    out["smoke"][0] = max(q1map.values()) if q1map else None
    if not any(v > 0 for v in q1map.values()):
        return out
    # 2) 스모크 q2 + 같은좌표 게이트
    q2 = sweep(name, cfgs[1], f"{tag}_q2", params_csv)
    q2map = (q2 or {}).get("pmap") or {}
    out["smoke"][1] = max(q2map.values()) if q2map else None
    best_label, best_min = None, None
    for L in set(q1map) & set(q2map):
        m = min(q1map[L], q2map[L])
        if best_min is None or m > best_min:
            best_min, best_label = m, L
    if not (best_min is not None and best_min > 0):
        return out  # 스모크 실패.
    out["robust"] = {"label": best_label, "q1": q1map[best_label], "q2": q2map[best_label], "min": best_min}
    out["verdict"] = "smoke-pass"

    # 3) 전체기간 train (격상) — gen19형 거짓양성 차단.
    full_cfg = FULL_CONFIGS.get(timeframe)
    if full_cfg and full_cfg.is_file():
        full = validate_on(name, full_cfg, f"{tag}_full", best_label)
        out["full"] = full
        if not (full.get("status") == "ok" and isinstance(full.get("profit"), (int, float))
                and full["profit"] > 0):
            return out  # 스모크는 통과했으나 전체기간 음전 = 과적합(smoke-pass에서 종료).
        out["verdict"] = "train-pass"
    else:
        return out

    # 4) OOS (격상).
    oos_cfgs = OOS_CONFIGS.get(timeframe, [])
    all_oos_pos = bool(oos_cfgs)
    for j, ocfg in enumerate(oos_cfgs):
        if not ocfg.is_file():
            all_oos_pos = False
            continue
        o = validate_on(name, ocfg, f"{tag}_oos{j}", best_label)
        out["oos"].append({"config": ocfg.name, "profit": o.get("profit"), "status": o.get("status")})
        if not (o.get("status") == "ok" and isinstance(o.get("profit"), (int, float)) and o["profit"] > 0):
            all_oos_pos = False
    if all_oos_pos:
        out["verdict"] = "★PROMISING"
        out["both_positive"] = True  # = 스모크+전체기간+OOS 전부 흑자(같은 좌표).
    else:
        out["verdict"] = "train-only"  # 전체기간 통과·OOS 미달.
    return out


def _fmt(v) -> str:
    return f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)


def log_line(out_path: Path, jsonl_path: Path, rec: Dict) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ev = rec.get("eval") or {}
    verdict = ev.get("verdict", "gen-fail" if not rec.get("template") else "no-go")
    robust = ev.get("robust")
    rob_s = (f"{robust['label'].replace('TMAP ','')} min={_fmt(robust['min'])}" if robust else "—")
    smoke_s = " / ".join(_fmt(x) for x in (ev.get("smoke") or [])) or "—"
    full_s = _fmt((ev.get("full") or {}).get("profit")) if ev.get("full") else "—"
    oos_s = " / ".join(_fmt(o.get("profit")) for o in (ev.get("oos") or [])) or "—"
    if not out_path.is_file():
        out_path.write_text(
            "# 다밴드 자율 발굴 밤샘 루프 (2026-06-14~)\n\n"
            "> tmap_multiband_discovery.py — 생성→스모크(같은좌표 양분기)→전체기간 train→OOS "
            "단계격상. ★PROMISING=전체기간+OOS까지 흑자(THETA급 바). 엔진 무수정.\n\n"
            "| # | 트랙 | 템플릿 | robust 코너(스모크 min) | smoke q1/q2 | 전체train | OOS | 판정 |\n"
            "|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with out_path.open("a", encoding="utf-8") as f:
        f.write(f"| {rec['iter']} | {rec['track']} | {rec.get('template','—')} | "
                f"{rob_s} | {smoke_s} | {full_s} | {oos_s} | {verdict} |\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iters", type=int, default=40)
    ap.add_argument("--deadline-hhmm", default="0700")
    ap.add_argument("--out", default=str(EVID / "multiband_overnight.md"))
    ap.add_argument("--gen-timeout", type=int, default=300)
    ap.add_argument("--stateful", action="store_true",
                    help="[P2] 직전 결과(ledger)를 다음 생성에 환류(회피/선호). "
                         "미지정=무작위(무상태, A/B 대조군).")
    args = ap.parse_args()

    out_path = Path(args.out)
    jsonl_path = out_path.with_suffix(".jsonl")
    now0 = _dt.datetime.now()
    deadline = now0.replace(hour=int(args.deadline_hhmm[:2]), minute=int(args.deadline_hhmm[2:]),
                            second=0, microsecond=0)
    if deadline <= now0:
        deadline += _dt.timedelta(days=1)

    promising: List[str] = []
    records: List[Dict] = []  # [P2] 유상태 ledger(누적) — build_feedback 입력.
    mode = "유상태(폐루프)" if args.stateful else "무상태(무작위)"
    print(f"[DISC] start max_iters={args.max_iters} deadline={deadline:%Y-%m-%d %H:%M} "
          f"mode={mode} out={out_path}", flush=True)
    for i in range(args.max_iters):
        if _dt.datetime.now() >= deadline:
            print(f"[DISC] deadline reached at iter {i}", flush=True)
            break
        track, principle = TRACKS[i % len(TRACKS)]
        t0 = time.time()
        # [P2] 유상태면 누적 ledger에서 회피/선호 조립해 환류, 무상태면 빈 피드백.
        feedback = build_feedback(records) if args.stateful else ""
        print(f"[DISC] iter {i} track={track} fb={'Y' if feedback else 'N'} — generating...", flush=True)
        rec: Dict = {"iter": i, "track": track}
        try:
            name, gen_tail = generate(principle, timeout=args.gen_timeout, feedback_text=feedback)
            rec["template"] = name
            if not name:
                rec["gen_tail"] = gen_tail
                log_line(out_path, jsonl_path, rec)
                records.append(rec)
                print(f"[DISC] iter {i} GEN-FAIL ({time.time()-t0:.0f}s)", flush=True)
                continue
            tf = _load_template(name).get("timeframe", "tick")
            print(f"[DISC] iter {i} {name} (tf={tf}) — smoke→full→oos...", flush=True)
            ev = evaluate(name, tf, i)
            rec["timeframe"] = tf
            rec["eval"] = ev
            log_line(out_path, jsonl_path, rec)
            records.append(rec)  # [P2] ledger 누적.
            v = ev.get("verdict")
            if v == "★PROMISING":
                promising.append(name)
                print(f"[DISC] iter {i} ★PROMISING {name} robust={ev.get('robust')} "
                      f"full={ev.get('full')} oos={ev.get('oos')} ({time.time()-t0:.0f}s)", flush=True)
            else:
                print(f"[DISC] iter {i} {v} {name} smoke={ev.get('smoke')} "
                      f"full={(ev.get('full') or {}).get('profit')} ({time.time()-t0:.0f}s)", flush=True)
        except Exception as exc:  # noqa: BLE001
            rec["error"] = str(exc)
            try:
                log_line(out_path, jsonl_path, rec)
            except Exception:  # noqa: BLE001
                pass
            records.append(rec)  # [P2] ledger 누적(실패도 회피 신호).
            print(f"[DISC] iter {i} EXC {exc} ({time.time()-t0:.0f}s)", flush=True)

    print(f"[DISC] done. promising({len(promising)})={promising}", flush=True)
    (out_path.with_name(out_path.stem + "_summary.json")).write_text(
        json.dumps({"promising": promising, "out": str(out_path),
                    "finished": f"{_dt.datetime.now():%Y-%m-%d %H:%M}"},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
