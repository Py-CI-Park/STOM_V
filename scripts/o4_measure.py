"""O-4 생성 문법 후보 오프라인 선별 CLI — 봉인본 §5·§6·§7·§11·§14.

phase 분리:
  bits    = 재도출 신규 5비트 산출(발견창 437일 루프, 일별 체크포인트·재시작) →
            o4_candidate_bits.parquet. 기존 bit_4/10/16/17 은 d1 parquet 재사용(재산출 없음).
  gates   = 무결성 지문(은행·d1 비트) + o4 키 정합 + 신규 비트 패리티(엔진 exec 100%) + 포함 sanity.
  qualify = 후보 158 발화 계수·표본 하한 → 자격 후보(FDR 분모). **L3 미접촉**(비트+연도만).
  judge   = 자격 후보 발화 mean L3·일자블록 CI·FDR·겹침·분류 + 족 계상 + 딱지 5종.
  all     = bits → gates → qualify → judge.

산출물은 research_runs/alpha_restart_20260710/o4/ (parquet·parts·progress·run_ctl·log 는 git 제외).
**전 창 본 측정은 분리형 러너(메인 세션)가 measure_gate 통과 후 기동** — 본 스크립트는 --days 스모크만
직접 실행 권장(--smoke 딱지, n_trials 미기입). 원본 tick DB read-only. 엔진 백테 0회. git 커밋은 메인 몫.

사용(스모크):
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o4_measure.py --phase bits --days 20220517 --smoke
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

from alpha_lab.clause_lab.bank import day_list  # noqa: E402
from alpha_lab.o4lab import bits as o4bits  # noqa: E402
from alpha_lab.o4lab import gate as o4gate  # noqa: E402
from alpha_lab.o4lab import grammar, judge_o4  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "o4"
_DEFAULT_BANK = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_D1_BITS = _RUN_DIR / "stats_map" / "d1_onset_clause_bits.parquet"
_KEYS = list(o4bits.KEY_COLUMNS)
_ALL_BIT_COLS = [f"bit_{n}" for n in range(1, 40)] + list(o4bits.BIT_COLUMNS)

# 딱지 5종(강제 인쇄 — §9).
_TAGS = [
    "① 출구 조건부: L3 는 RR8_12 매도식(sell_sha 8ef01e0e…)에 조건부 — 다른 출구면 다른 지도.",
    "② known-오염 입력: 절 족 구조는 2024 선정창을 본 챔피언 계보(buy_sha 348c5181…)의 D1 진단, "
    "임계 어휘 출처(W5)에 2025~2026 시점 전략 포함. 측정창(2022-2023) clean 이나 계보·출구 조건부 진단.",
    "③ 원-임계 재도출: 후보 임계는 챔피언 원-임계 이식이 아니라 W5 실재 어휘 재도출 격자(결과 관측 전 봉인). "
    "단 가드 G(현재가<=30000/50000)는 시너지가 측정된 좌표라 재사용(§14-F5).",
    "④ 성능 주장 아님·최종 심판: 양/음 EV 는 매수 필터 진단이지 성능·실전 수익 주장 아님. "
    "오프라인 생존→엔진 확인(A-5)은 '실전 시험 자격'까지 — 최종 심판은 U-4 감독형 소액 실전.",
    "⑤ 09:00-09:30·필터 한정: tick DB 는 09:00~09:30 만, 후보는 서지 온셋 위 필터(자립 트리거 아님) — "
    "이 창·이 온셋 풀 한정, 장중 일반화 금지.",
]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="O-4 생성 문법 후보 오프라인 선별")
    ap.add_argument("--phase", choices=("bits", "gates", "qualify", "judge", "all"),
                    default="all")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--bank", default=str(_DEFAULT_BANK))
    ap.add_argument("--d1-bits", default=str(_DEFAULT_D1_BITS))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--days", nargs="*", default=None,
                    help="측정 일자(YYYYMMDD) 제한 — 스모크/부분. 미지정=발견창 전체")
    ap.add_argument("--smoke", action="store_true",
                    help="스모크 관통 — 리포트에 스모크 딱지, n_trials 미기입")
    return ap.parse_args(argv)


def _resolve_days(db_dir, days):
    full = day_list(db_dir)
    if not days:
        return full
    want = set(days)
    picked = [(d, p) for (d, p) in full if d in want]
    missing = want - {d for d, _ in picked}
    if missing:
        raise SystemExit(f"발견창에 없는 일자: {sorted(missing)}")
    return picked


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, obj) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")


def _ensure_gitignore(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\nrun_ctl/\n*.log\n", encoding="utf-8")


def _o4_bits_path(out_dir: Path) -> Path:
    return out_dir / "stats_map_o4" / "o4_candidate_bits.parquet"


def _fmt(v, nd=4) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


# ---------------------------------------------------------------------------
# phase 구현.
# ---------------------------------------------------------------------------

def run_phase_bits(args) -> dict:
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    parts_dir = out_dir / "parts"
    days = _resolve_days(args.db_dir, args.days)
    o4bits.run_bits(args.db_dir, out_dir, parts_dir, days=days)
    bits_path = _o4_bits_path(out_dir)
    # 스모크(부분 일)는 consolidate 로 부분 은행을 만들지 않는다 — 전 창 완주 시에만 정합.
    cons = None
    if not args.days:
        cons = o4bits.consolidate(parts_dir, bits_path)
        _dump(out_dir / "o4_bits_summary.json", {"consolidate": cons})
    part_sat = {}
    for d, _ in days:
        p = parts_dir / f"o4bits_{d}.parquet"
        if p.exists():
            df = pd.read_parquet(p)
            part_sat[d] = {"n_onsets": int(df.shape[0]),
                           **{b: int(df[b].sum()) for b in o4bits.BIT_COLUMNS}}
    _dump(out_dir / "o4_bits_smoke.json",
          {"days": [d for d, _ in days], "per_day": part_sat, "consolidated": cons is not None})
    print(f"[BITS] days={len(days)} consolidated={cons is not None} "
          + (f"n_onsets={cons['n_onsets']}" if cons else "(부분 — consolidate 생략)"))
    return {"per_day": part_sat, "consolidate": cons}


def run_phase_gates(args) -> dict:
    out_dir = Path(args.out_dir)
    o4_bits = _o4_bits_path(out_dir)
    if not o4_bits.exists():
        raise SystemExit(f"o4 비트 부재: {o4_bits} — 먼저 --phase bits 전 창 완주")
    days = [d for d, _ in _resolve_days(args.db_dir, args.days)]
    gates = o4gate.run_gates(args.bank, args.d1_bits, str(o4_bits), args.db_dir, days)
    _dump(out_dir / "o4_gates_summary.json", gates)
    print(f"[GATES] integrity={gates['reused_integrity'].get('all_match')} "
          f"key={gates['o4_key_integrity']['pass']} "
          f"parity={gates['new_bit_parity']['pass']}"
          f"({gates['new_bit_parity']['agreement_pct']:.2f}%) "
          f"inclusion={gates['inclusion_sanity']['pass']} → gate_pass={gates['gate_pass']}")
    return gates


def _load_all_onset_bits(d1_bits_path, o4_bits_path):
    """전 온셋(863,446) 비트 — d1(bit_1~39) + o4(신규 5) 키 병합 + day. L3 미접촉."""
    d1 = pd.read_parquet(d1_bits_path)
    o4 = pd.read_parquet(o4_bits_path)
    m = d1.merge(o4, on=_KEYS, how="inner")
    if m.shape[0] != d1.shape[0]:
        raise SystemExit(f"d1/o4 비트 키 병합 손실(d1={d1.shape[0]} merged={m.shape[0]})")
    forbidden = {"l3_net", "l3_labeled", "l3_clause", "l3_exit"}
    assert not (forbidden & set(m.columns)), "qualify 경로가 L3 컬럼을 로드했다(§6 위반)"
    day = m["day"].to_numpy(dtype=np.int64)
    bit_arrays = {c: m[c].to_numpy().astype(bool) for c in _ALL_BIT_COLS}
    return bit_arrays, day


def run_phase_qualify(args) -> dict:
    out_dir = Path(args.out_dir)
    o4_bits = _o4_bits_path(out_dir)
    bit_arrays, day = _load_all_onset_bits(args.d1_bits, str(o4_bits))
    qual = judge_o4.qualify_candidates(bit_arrays, day)
    _dump(out_dir / "o4_qualify_summary.json", qual)
    print(f"[QUALIFY] 후보 {qual['n_candidates']} → 자격 {qual['n_qualified']} "
          f"(FDR 분모={qual['fdr_denominator']})")
    return qual


def _load_labeled(bank_path, d1_bits_path, o4_bits_path):
    """라벨된 온셋(862,932) — net_pp(%p)·days·years + 전 비트(bit_1~39 + o4 5)."""
    bank = pd.read_parquet(bank_path, columns=_KEYS + ["year", "l3_net", "l3_labeled"])
    d1 = pd.read_parquet(d1_bits_path)
    o4 = pd.read_parquet(o4_bits_path)
    base = bank.merge(d1, on=_KEYS, how="inner").merge(o4, on=_KEYS, how="inner")
    if base.shape[0] != bank.shape[0]:
        raise SystemExit(f"은행/비트 키 병합 손실({bank.shape[0]}→{base.shape[0]}, kill-3)")
    lab = base["l3_labeled"].to_numpy().astype(bool)
    net_pp = base["l3_net"].to_numpy(dtype=np.float64)[lab] * 100.0
    days = base["day"].to_numpy(dtype=np.int64)[lab]
    years = base["year"].to_numpy(dtype=np.int64)[lab]
    bit_arrays = {c: base[c].to_numpy().astype(bool)[lab] for c in _ALL_BIT_COLS}
    pool_mean = float(net_pp.mean()) if net_pp.size else float("nan")
    return net_pp, days, years, bit_arrays, pool_mean


def run_phase_judge(args, qual: dict) -> dict:
    out_dir = Path(args.out_dir)
    o4_bits = _o4_bits_path(out_dir)
    net_pp, days, years, bit_arrays, pool_mean = _load_labeled(
        args.bank, args.d1_bits, str(o4_bits))
    judgment = judge_o4.judge_all_candidates(qual, bit_arrays, net_pp, days, years)
    result = {
        "kind": "o4_candidate_judgment",
        "preregistration": "2026-07-13_o4_generation_grammar_preregistration.md (fd7bae48)",
        "n_labeled": int(net_pp.size), "pool_mean_pp_measured": round(pool_mean, 6),
        "qualification": {k: qual[k] for k in
                          ("n_candidates", "n_qualified", "fdr_denominator", "qualified_cids")},
        "judgment": judgment, "tags": _TAGS, "smoke": bool(args.smoke),
    }
    _dump(out_dir / "o4_candidate_summary.json", result)
    _write(out_dir / "o4_candidate_report.md", render_report(result))
    j = judgment
    print(f"[JUDGE] 자격 {j['n_qualified']} · 생존 {j['n_survive']} · 아류 {j['n_derivative']} "
          f"· 약신호 {len(j['weak_signal_cids'])} · 생존족 {j['n_survive_families']} · "
          f"kill1={j['kill1_no_survivor']} · sanity={j['sanity_anchor_tripped']}")
    return result


def render_report(result: dict) -> str:
    j = result["judgment"]
    L: list = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if result["smoke"] else ""
    A(f"# O-4 생성 문법 후보 선별 판정 리포트{tag}")
    A("")
    A(f"> 사전등록: `{result['preregistration']}` · 엔진 백테 0회 · 원본 read-only · "
      "L3=RR8_12 출구 조건부 · 후보 158(N 봉인)")
    A("")
    A("## 0. 결론 먼저")
    A("")
    if result["smoke"]:
        A("> 스모크 관통 — 아래 수치는 파이프라인 검증용이며 판정이 아니다(부분 일·n_trials 미기입).")
        A("")
    if j["n_survive"]:
        verdict = f"**생존 후보 {j['n_survive']}건**(양EV ∧ 겹침 ≤0.50): {j['survive_cids']}"
    elif j["only_derivative"]:
        verdict = (f"**아류만 생존 {j['n_derivative']}건**(양EV이나 챔피언 겹침>0.50) — "
                   "새 발화 모집단 아님(RR8 병합·D5 kill-3 계보 부정 지도, kill 아님)")
    else:
        verdict = ("**kill-1 — 생존 0**(검증 압력 절 가산 조합으로 서지 음의 지형 못 뒤집음) — "
                   "O-1G·서지·O-3 에 이은 부정 지도, O-4 문법을 단독 절 가산 조합으로 좁힐 근거")
    A(f"{verdict}. 자격 후보 {j['fdr_denominator']}개(FDR 분모) 중 생존 {j['n_survive']}·"
      f"아류 {j['n_derivative']}·약신호 {len(j['weak_signal_cids'])}·양EV증거0 {len(j['no_positive_ev_cids'])}. "
      f"생존 문법족 {j['n_survive_families']}. 판정 = mean L3_net ≥ +0.10%p ∧ 일자블록 CI 하한>0 ∧ "
      "BH-FDR(q=0.10) ∧ 연도 동부호 ∧ 겹침 ≤0.50.")
    A("")
    A(f"- 서지 풀 평균(측정): {_fmt(result['pool_mean_pp_measured'])}%p "
      f"(봉인 기준 −1.008%p) · sanity anchor(§10-6): {j['sanity_anchor_tripped']}"
      + ("→ **무차별 수렴, 수동 스팟 필수**" if j["sanity_anchor_tripped"] else "(미발동)"))
    A(f"- 겹침 프록시 딱지(§14-F8): {j['overlap_proxy_tag']}")
    A("")
    A("## 1. 생존·아류·약신호 후보")
    A("")
    A("| 후보 | 족 | n(발화) | mean(%p) | 일자블록 CI | 연도(22/23) | FDR | 겹침 | MDE(%p) | 분류 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    show = j["survive_cids"] + j["derivative_cids"] + j["weak_signal_cids"]
    for cid in show:
        r = j["per_candidate"][cid]
        ym = r["year_mean"]
        yr = f"{_sgn(ym[2022]['sign'])}{_sgn(ym[2023]['sign'])}"
        A(f"| {cid} | {r['family']} | {r['n_fire']:,} | {_fmt(r['mean_net_pp'])} | "
          f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | {yr} | "
          f"{'생존' if r['fdr_survive'] else '—'} | {_fmt(r['overlap_rate'], 3)} | "
          f"{_fmt(r['mde_pp'])} | {r['classification']} |")
    if not show:
        A("| (없음 — 전 자격 후보 양EV 증거 0) | | | | | | | | | |")
    A("")
    A(f"## 2. 미검출 열거(양EV 증거 0 — {len(j['no_positive_ev_cids'])}건)")
    A("")
    A("> 자격 후보 중 생존·아류·약신호가 아닌 전량(가산 조합 한계의 정직 기록):")
    A("")
    A("`" + ", ".join(j["no_positive_ev_cids"]) + "`" if j["no_positive_ev_cids"] else "(없음)")
    A("")
    A("## 3. 딱지 (강제 인쇄 — §9)")
    A("")
    for t in result["tags"]:
        A(f"- {t}")
    A("")
    A("*엔진 백테 0회 · 원본 read-only · git 커밋 없음 · 2024/2025 미접촉 · 최종 심판=U-4 감독형 소액 실전.*")
    return "\n".join(L) + "\n"


def _sgn(s) -> str:
    return {1: "+", -1: "−", 0: "·"}.get(s, "·")


def main(argv=None) -> int:
    args = parse_args(argv)
    # 문법 봉인 검산(모듈 로드 시 assert 됨) — 명시 재확인.
    assert len(grammar.CANDIDATES) == grammar.N_CANDIDATES
    qual = None
    if args.phase in ("bits", "all"):
        run_phase_bits(args)
    if args.phase in ("gates", "all"):
        run_phase_gates(args)
    if args.phase in ("qualify", "all"):
        qual = run_phase_qualify(args)
    if args.phase in ("judge", "all"):
        if qual is None:
            qp = Path(args.out_dir) / "o4_qualify_summary.json"
            if not qp.exists():
                raise SystemExit("qualify_summary 없음 — 먼저 --phase qualify 실행")
            qual = json.loads(qp.read_text(encoding="utf-8"))
        run_phase_judge(args, qual)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
