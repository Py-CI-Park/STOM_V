"""B-트랙 가지 분해 측정 CLI — 봉인본 §5·§6·§11·§14.

phase 분리:
  gate  = 무결성 지문 대조(은행 0b6268e0·d1 비트 4df57b77 — pair_gate 재사용) → gate_report.json.
  judge = 가지/anchor 발화 mean L3·일자블록 CI·등급·FDR·3분법·엔진 갭 → summary.json + report.md.
  all   = gate → judge.

산출물은 research_runs/alpha_restart_20260710/b_track/(parquet·parts·progress·run_ctl·log git 제외).
**본 측정(실 parquet) 실행은 메인 세션**(measure_gate 통과 후, 오프라인 수 초~분 규모라 포그라운드).
원본 read-only. 엔진 백테 0회. git 커밋은 메인 몫. 신규 비트 0(d1 비트 AND만).

사용: STOM_ALLOW_MINIMAL_SETTING=1 python scripts/b_track_measure.py --phase gate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from alpha_lab.btrack import judge_b  # noqa: E402
from alpha_lab.btrack.branches import BRANCH_902_NUMS, BRANCH_905_NUMS  # noqa: E402
from alpha_lab.clause_lab.pair_gate import check_integrity  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "b_track"
_DEFAULT_BANK = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_D1_BITS = _RUN_DIR / "stats_map" / "d1_onset_clause_bits.parquet"
_DEFAULT_LIVE = _RUN_DIR / "d5r_b1_live"
_KEYS = ["code", "day", "off", "t0"]
_ALL_BITS = [f"bit_{n}" for n in range(1, 40)]

_TAGS = [
    "① 출구 조건부: L3 는 RR8_12 매도식(sell_sha 8ef01e0e…)에 조건부 — 다른 출구면 다른 지도.",
    "② known-오염 입력: 가지 절·임계는 2024 선정창을 본 챔피언 계보(buy_sha 348c5181…)의 역사적 산물. "
    "측정창(2022-2023) clean 이나 계보·출구 조건부 진단.",
    "③ AND 프록시 하한: 가지 AND 발화는 실발화의 과소집합(엔진 상태변수·1일1회·순위·서지밖 진입 미포함) "
    "— 발화 n·mean 은 하한 성격. 엔진 실측(+0.82%/+0.57%)과의 갭이 프레임 갭.",
    "④ 성능 주장 아님·최종 심판: 가지 양/음 EV 는 진입 모집단 진단이지 성능·실전 수익 주장 아님. "
    "양(+) 가지 승격은 B-3·엔진 확인·U-4 감독형 소액 실전을 각각 별도 봉인·승인.",
]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="B-트랙 가지 분해 측정")
    ap.add_argument("--phase", choices=("gate", "judge", "all"), default="all")
    ap.add_argument("--bank", default=str(_DEFAULT_BANK))
    ap.add_argument("--d1-bits", default=str(_DEFAULT_D1_BITS))
    ap.add_argument("--live-dir", default=str(_DEFAULT_LIVE))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--smoke", action="store_true", help="스모크 딱지 + n_trials 미기입")
    return ap.parse_args(argv)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, obj) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")


def _ensure_gitignore(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\nrun_ctl/\n*.log\n", encoding="utf-8")


def _fmt(v, nd=4) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


def _sgn(s) -> str:
    return {1: "+", -1: "−", 0: "·"}.get(s, "·")


def run_gate(args) -> dict:
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    integrity = check_integrity(args.bank, args.d1_bits)
    report = {"kind": "b_track_gate", "integrity": integrity,
              "gate_pass": bool(integrity["all_match"]),
              "branch_902_clauses": list(BRANCH_902_NUMS),
              "branch_905_clauses": list(BRANCH_905_NUMS)}
    _dump(out_dir / "b_gate_report.json", report)
    print(f"[GATE] integrity all_match={integrity['all_match']} → gate_pass={report['gate_pass']}")
    return report


def _load_labeled(bank_path, d1_bits_path):
    bank = pd.read_parquet(bank_path, columns=_KEYS + ["year", "l3_net", "l3_labeled"])
    d1 = pd.read_parquet(d1_bits_path, columns=_KEYS + _ALL_BITS)
    base = bank.merge(d1, on=_KEYS, how="inner")
    if base.shape[0] != bank.shape[0]:
        raise SystemExit(f"은행/비트 키 병합 손실({bank.shape[0]}→{base.shape[0]}, kill)")
    lab = base["l3_labeled"].to_numpy().astype(bool)
    net_pp = base["l3_net"].to_numpy(dtype=np.float64)[lab] * 100.0
    days = base["day"].to_numpy(dtype=np.int64)[lab]
    years = base["year"].to_numpy(dtype=np.int64)[lab]
    bit_arrays = {c: base[c].to_numpy().astype(bool)[lab] for c in _ALL_BITS}
    return net_pp, days, years, bit_arrays


def run_judge(args, gate_report: dict) -> dict:
    if not gate_report["gate_pass"]:
        raise SystemExit("무결성 불일치 — judge 진입 금지(kill)")
    out_dir = Path(args.out_dir)
    net_pp, days, years, bit_arrays = _load_labeled(args.bank, args.d1_bits)
    engine_ref = judge_b.load_engine_reference(args.live_dir)
    judgment = judge_b.judge_branches(bit_arrays, net_pp, days, years, engine_ref=engine_ref)
    result = {
        "kind": "b_track_branch_judgment",
        "preregistration": "2026-07-13_b_track_branch_decomposition_preregistration.md (db08c1de)",
        "n_labeled": int(net_pp.size),
        "pool_mean_pp_measured": round(float(net_pp.mean()), 6) if net_pp.size else None,
        "engine_reference": engine_ref, "judgment": judgment,
        "tags": _TAGS, "smoke": bool(args.smoke),
    }
    _dump(out_dir / "b_branch_summary.json", result)
    _write(out_dir / "b_branch_report.md", render_report(result))
    j = judgment
    print(f"[JUDGE] anchor n={j['units']['anchor']['n_fire']} verdict={j['anchor_frame_verdict']} "
          f"· 902 n={j['units']['902']['n_fire']}({j['units']['902']['tier']}) "
          f"905 n={j['units']['905']['n_fire']}({j['units']['905']['tier']}) "
          f"· 정식 양(+) {j['n_positive_formal']} · sanity={j['sanity_anchor_tripped']}")
    return result


def render_report(result: dict) -> str:
    j = result["judgment"]
    u = j["units"]
    L: list = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if result["smoke"] else ""
    A(f"# B-트랙 가지 분해 판정 리포트{tag}")
    A("")
    A(f"> 사전등록: `{result['preregistration']}` · 엔진 백테 0회 · 원본 read-only · "
      "L3=RR8_12 출구 조건부 · 챔피언 가지만(신규 비트 0)")
    A("")
    A("## 0. 결론 먼저")
    A("")
    if result["smoke"]:
        A("> 스모크 — 파이프라인 검증용, 판정 아님.")
        A("")
    verdict = j["anchor_frame_verdict"]
    vtext = {
        "reproduce": "**(a) 재현 확정** — 오프라인 가지 AND 합집합이 챔피언 깊은 양(+)을 재현. 가지 사냥 확장 근거(깊은 양(+) 좌표 존재).",
        "frame_gap": "**(b) 프레임 갭 확정** — anchor CI 상한<0(명확한 음). 오프라인 비트-AND 프록시로는 엔진 진입 프레임(1일1회·순위·warmup·타이밍) 재현 불가 → 엔진 프레임 피벗 권고.",
        "undetermined": "**(c) 미결** — anchor CI 가 0을 걸침(검정력 부족). 프레임 판정 유보 — 표본/엔진 확인 필요.",
    }[verdict]
    A(f"{vtext} 정식 양(+) 가지 {j['n_positive_formal']}건"
      + (f": {j['positive_formal_branches']}" if j["n_positive_formal"] else "")
      + f" · 관찰 양(+) {len(j['positive_observational_branches'])}건"
      + (f": {j['positive_observational_branches']}" if j["positive_observational_branches"] else "")
      + f". FDR 분모 = {j['fdr_denominator']}(정식 가지 + anchor).")
    A("")
    A(f"- 서지 풀 평균(측정): {_fmt(result['pool_mean_pp_measured'])}%p (봉인 기준 −1.008) · "
      f"sanity anchor: {j['sanity_anchor_tripped']}"
      + ("→ **무차별 수렴, 수동 스팟 필수**" if j["sanity_anchor_tripped"] else "(미발동)"))
    A("")
    A("## 1. 가지·anchor 판정표")
    A("")
    A("| 단위 | 절수 | n(발화) | 등급 | mean(%p) | 일자블록 CI | 연도(22/23) | FDR | MDE(%p) | 분류/판정 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    meta = {"902": ("24", "가지"), "905": ("26", "가지"), "anchor": ("902∨905", "anchor")}
    for name in ("902", "905", "anchor"):
        r = u[name]
        ym = r["year_mean"]
        yr = f"{_sgn(ym[2022]['sign'])}{_sgn(ym[2023]['sign'])}"
        cls = r.get("frame_verdict") if name == "anchor" else r.get("classification")
        A(f"| {name} | {meta[name][0]} | {r['n_fire']:,} | {r['tier']} | {_fmt(r['mean_net_pp'])} | "
          f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | {yr} | "
          f"{'생존' if r.get('fdr_survive') else '—'} | {_fmt(r['mde_pp'])} | {cls} |")
    A("")
    A(f"- anchor 서로소 합 검증(902+905 = anchor): {u['anchor'].get('disjoint_sum_check')}")
    A("")
    A("## 2. 엔진 갭 (오프라인 anchor mean L3 vs B1 엔진 실측)")
    A("")
    A("| 연도 | 엔진 거래 | 엔진 avg(%) | 오프라인 anchor mean(%p) | 갭(엔진−오프라인) |")
    A("|---|---|---|---|---|")
    for yr in (2022, 2023):
        g = j["engine_gap"].get(yr, {}) if j["engine_gap"] else {}
        A(f"| {yr} | {g.get('engine_trades', '—')} | {_fmt(g.get('engine_avg_pct'), 2)} | "
          f"{_fmt(g.get('offline_anchor_mean_pp'))} | {_fmt(g.get('gap_pp'))} |")
    A("")
    A("> 갭이 양(+)이고 큰데 오프라인이 음이면(b), 그 크기가 '프레임 갭'의 크기다 — 엔진은 이기는데 "
      "오프라인 프록시는 그 진입 프레임을 못 담는다.")
    A("")
    A("## 3. 딱지 (강제 인쇄 — §9)")
    A("")
    for t in result["tags"]:
        A(f"- {t}")
    A("")
    A("*엔진 백테 0회 · 원본 read-only · git 커밋 없음 · 2024/2025 미접촉 · 신규 비트 0 · "
      "최종 심판=U-4 감독형 소액 실전.*")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = parse_args(argv)
    gate_report = None
    if args.phase in ("gate", "all"):
        gate_report = run_gate(args)
    if args.phase in ("judge", "all"):
        if gate_report is None:
            gp = Path(args.out_dir) / "b_gate_report.json"
            if not gp.exists():
                raise SystemExit("gate_report 없음 — 먼저 --phase gate 실행")
            gate_report = json.loads(gp.read_text(encoding="utf-8"))
        run_judge(args, gate_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
