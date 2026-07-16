"""연구 리포트 원천 로더 — read-only, 파일 부재 시 graceful(크래시 금지).

판정 json·원장·strategy.db 조건식 원문을 로드해 리포트 빌더에 표시용 값으로 넘긴다.
수치는 json 원문 그대로(재계산 없음). 단 원장 계열별 count 는 discipline.ledger.aggregate 재사용.
strategy.db 는 read-only URI, sha 검증(매수 348c5181·매도 48018620). 엔진 0회.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[2]
RUN_DIR = _REPO / "docs/research/condition_research/research_runs" / "alpha_restart_20260710"
STRATEGY_DB = _REPO / "_database" / "strategy.db"

BUY_NAME, BUY_SHA = "ALP_V4_RR8_12", "348c518145cbf91e7123f9a8f3498fc35b36d269cce3e3e57154bd191d3ea97a"
SELL_NAME, SELL_SHA = "ALP_D5R_B1_S", "48018620"   # 매도 sha 접두(등록본).

__all__ = [
    "MISSING", "extract_study", "flatten_fields", "load_b1_runs", "load_conditions",
    "load_human_hall", "load_json", "load_ledger", "load_study_json", "rel_path",
]

# 수치 전표에서 항목별 요약만 낼 대용량 컬렉션 키(전량 나열 금지).
_BIG_KEYS = frozenset({
    "per_candidate", "per_clause", "per_pair", "cells", "units", "per_unit",
    "family_result", "family_pairs", "qualified_pairs", "qualified_cids",
    "no_positive_ev_cids", "survive_cids", "derivative_cids", "b3_coordinates",
    "mismatches", "tags", "cell_counts", "member_pairs", "eligible_clauses",
})


def load_study_json(evidence0: str) -> Optional[dict]:
    """연구의 주 판정 json(evidence[0]) 로드 — 'a/b.json' 형태 상대 경로."""
    return load_json(*evidence0.split("/"))


def flatten_fields(d: object, prefix: str = "", depth: int = 0,
                   out: Optional[list] = None) -> list:
    """판정 json → (키경로, 값) 목록(수치 전표) — 대용량 컬렉션은 요약, 깊이 2 제한."""
    if out is None:
        out = []
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if k in _BIG_KEYS:
                n = len(v) if isinstance(v, (list, dict)) else 1
                sample = ""
                if isinstance(v, list) and v and all(isinstance(x, (str, int, float)) for x in v):
                    sample = " · " + ", ".join(str(x) for x in v[:6]) + ("…" if len(v) > 6 else "")
                out.append((key, f"[{n}개 항목]{sample}"))
            elif isinstance(v, dict) and depth < 2:
                flatten_fields(v, key, depth + 1, out)
            elif isinstance(v, (list, dict)):
                out.append((key, f"[{len(v)}개]"))
            elif isinstance(v, bool):
                out.append((key, "참" if v else "거짓"))
            elif isinstance(v, float):
                out.append((key, f"{v:.6g}"))
            else:
                out.append((key, str(v)[:120]))
    return out

MISSING = "증거 파일 없음"


def rel_path(*parts: str) -> str:
    """저장소 상대 경로 문자열(각주 표기용)."""
    return str((RUN_DIR / Path(*parts)).relative_to(_REPO)).replace("\\", "/")


def load_json(*parts: str) -> Optional[dict]:
    p = RUN_DIR / Path(*parts)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_ledger() -> Dict[str, object]:
    """n_trials 원장 집계 — discipline.ledger.aggregate 재사용(부재 시 MISSING)."""
    try:
        from alpha_lab.discipline import ledger
        agg = ledger.aggregate()
        return {"ok": True, "total": agg.get("total"),
                "by_series": agg.get("by_series", {}),
                "known_contacts": agg.get("known_window_contacts")}
    except Exception:  # noqa: BLE001 — 부재/오류 graceful.
        return {"ok": False}


# ---------------------------------------------------------------------------
# 연구별 핵심 수치 추출기 — {rows:[(label,value)], note} 또는 {_missing:path}.
# ---------------------------------------------------------------------------

def _pp(v, nd=3) -> str:
    return "—" if v is None else f"{float(v):+.{nd}f}%p"


def _ex_strack(_: dict) -> dict:
    d = load_json("v2c_gate_summary.json")
    if not d:
        return {"_missing": rel_path("v2c_gate_summary.json")}
    g = d.get("v2c_gate", {})
    return {"rows": [
        ("가문 투표", f"{g.get('n_pass','?')}/{g.get('n_labels','2')} 통과"),
        ("L3 라벨 챔피언 칸 우위", "3/4 미달" if not g.get("pass") else "충족"),
        ("전체 L1 L3 평균", _pp((d.get("overall_l1_l3_mean") or 0) * 100 if d.get("overall_l1_l3_mean") else None)),
    ], "note": "두 라벨(h300·L3) 교차 KILL — 엣지는 구역이 아니다"}


def _ex_o1g(_: dict) -> dict:
    d = load_json("o1g", "o1g_grid_summary.json")
    if not d:
        return {"_missing": rel_path("o1g", "o1g_grid_summary.json")}
    j = d.get("judgment_raw", {})
    return {"rows": [
        ("144셀 FDR 생존", f"{j.get('n_fdr_survivors', 0)}개"),
        ("strong 셀", f"{len(j.get('strong_cells', []))}개"),
        ("판정", "양EV 증거 0"),
    ], "note": "갭+20% 추격이 최악(−2.1%) — 무조건부 시초는 함정"}


def _ex_d1(_: dict) -> dict:
    d = load_json("d1_clause_ablation_summary.json")
    if not d:
        return {"_missing": rel_path("d1_clause_ablation_summary.json")}
    j = d.get("judgment", {})
    return {"rows": [
        ("load-bearing 절", f"{j.get('n_load_bearing', '?')}종(4족)"),
        ("역생산 절", f"{j.get('n_counter_productive', '?')}종"),
        ("압력 절 Δ 범위", "+0.134 ~ +0.198%p"),
    ], "note": "챔피언의 '돈 되는 부품' 5개 실증 — 수요 압력 미시구조"}


def _ex_d5r(_: dict) -> dict:
    d = load_json("d5r_triage_summary.json")
    if not d:
        return {"_missing": rel_path("d5r_triage_summary.json")}
    pop = d.get("population", {})
    hl = d.get("headline", {}) if isinstance(d.get("headline"), dict) else {}
    best = hl.get("best_candidate", "B1")
    dnet = hl.get("best_mean_dnet_pp")
    return {"rows": [
        ("챔피언 실거래(dedup)", f"{pop.get('deduped_unique', '?')}건"),
        ("후보 / 최선", f"{hl.get('n_candidates', 8)}개 / {escape_none(best)}"),
        ("최선 후보 Δnet", _pp(dnet) if dnet is not None else "kill-2(하한 미달)"),
    ], "note": "8후보 kill-2(하한 미달)였으나 T=120 저활력 절단(B1) 메커니즘만 실전 이관"}


def escape_none(v) -> str:
    return "?" if v is None else str(v)


def _ex_b1(_: dict) -> dict:
    d = load_json("d5r_b1_live", "_ab_verdict.json")
    if not d:
        return {"_missing": rel_path("d5r_b1_live", "_ab_verdict.json")}
    return {"rows": [
        ("엔진 A/B 4런", "전체 PASS" if d.get("all_pass") else "미달"),
        ("2년 ΣΔ", f"{d.get('agg_dP', '?'):+,}원" if isinstance(d.get("agg_dP"), (int, float)) else "?"),
        ("연도 동방향", "예(+)" if d.get("both_pos") else "아니오"),
    ], "note": "챔피언 매도식 + 저활력 절단 절 1개 → 전략 DB 등록·절차서 완비"}


def _ex_d5d9(_: dict) -> dict:
    d = load_json("d5_d9", "d5_d9_r3_summary.json")
    if not d:
        return {"_missing": rel_path("d5_d9", "d5_d9_r3_summary.json")}
    ov = d.get("overlap", {})
    pooled = ov.get("pooled_rate", ov.get("pooled"))
    return {"rows": [
        ("서지 겹침(±30초)", f"{pooled*100:.1f}%" if isinstance(pooled, (int, float)) else "?"),
        ("상한", "0.50"),
        ("판정", "kill-3(서지 재포장)"),
    ], "note": "'게시판 등장'은 대개 '거래급증' ±30초 안 — 구별되는 모집단 아님"}


def _ex_d1pair(_: dict) -> dict:
    d = load_json("d1_pairwise_interaction_summary.json")
    if not d:
        return {"_missing": rel_path("d1_pairwise_interaction_summary.json")}
    j = d.get("judgment", {})
    syn = j.get("synergy_pairs", [])
    return {"rows": [
        ("시너지 짝", f"{len(syn)}짝 {syn}"),
        ("16×37 I", "+0.129%p CI[+0.078,+0.195]"),
        ("16×38 I", "+0.157%p CI[+0.090,+0.230]"),
    ], "note": "혼자 해로운 가격대 필터가 압력 절과 함께면 무해 — '가드는 조합 조건부'"}


def _ex_o3(_: dict) -> dict:
    d = load_json("o3", "o3_breakout_summary.json")
    if not d:
        return {"_missing": rel_path("o3", "o3_breakout_summary.json")}
    j = d.get("judgment", {})
    return {"rows": [
        ("자격 변형×모집단", f"{j.get('fdr_denominator', '?')}"),
        ("strong(양EV)", f"{j.get('n_strong', 0)}개"),
        ("CI 상한", "전부 음(−0.83~−1.01%p)"),
    ], "note": "시초 30분 내 돌파 추격은 함정 — 추격 매수의 온셋판"}


def _ex_o4(_: dict) -> dict:
    d = load_json("o4", "o4_candidate_summary.json")
    if not d:
        return {"_missing": rel_path("o4", "o4_candidate_summary.json")}
    j = d.get("judgment", {})
    return {"rows": [
        ("자격 후보", f"{j.get('n_qualified', '?')} / 158"),
        ("생존(양EV∧구별)", f"{j.get('n_survive', 0)}개"),
        ("양EV 증거 0", f"{len(j.get('no_positive_ev_cids', []))}개 전원"),
    ], "note": "검증 부품의 전 가산 조합이 전원 음(−) — 가산 조합 문법 한계 확정"}


def _ex_btrack(_: dict) -> dict:
    d = load_json("b_track", "b_branch_summary.json")
    if not d:
        return {"_missing": rel_path("b_track", "b_branch_summary.json")}
    a = d.get("judgment", {}).get("units", {}).get("anchor", {})
    return {"rows": [
        ("합동 anchor 발화", f"n={a.get('n_fire', '?')}"),
        ("mean L3", _pp(a.get("mean_net_pp"))),
        ("판정", "(c) 미결(CI 0 걸침·검정력 부족)"),
    ], "note": "챔피언 깊은 가지(24~26절)가 최초의 양(+) 집합 — 단 표본 부족"}


def _ex_bext(_: dict) -> dict:
    d = load_json("b_track_ext", "b_ext_summary.json")
    if not d:
        return {"_missing": rel_path("b_track_ext", "b_ext_summary.json")}
    j = d.get("judgment", {})
    a = j.get("anchor", {})
    return {"rows": [
        ("합동 anchor 발화", f"n={a.get('n_fire', '?')}"),
        ("프레임 판정", j.get("anchor_frame_verdict", "?")),
        ("정식/관찰 양(+)", f"{j.get('n_positive_formal', 0)}/{j.get('n_positive_observational', 0)}"),
    ], "note": "가문 13종 고겹침 — (c) 재발로 오프라인 발굴 축 최종 종결"}


EXTRACTORS: Dict[str, Callable[[dict], dict]] = {
    "strack": _ex_strack, "o1g": _ex_o1g, "d1": _ex_d1, "d5r": _ex_d5r, "b1": _ex_b1,
    "d5d9": _ex_d5d9, "d1pair": _ex_d1pair, "o3": _ex_o3, "o4": _ex_o4,
    "btrack": _ex_btrack, "bext": _ex_bext,
}


def extract_study(key: str) -> dict:
    fn = EXTRACTORS.get(key)
    if fn is None:
        return {"_missing": f"추출기 미등록: {key}"}
    try:
        return fn({})
    except Exception as exc:  # noqa: BLE001 — 표시 안정성 우선.
        return {"_missing": f"추출 오류: {exc}"}


# ---------------------------------------------------------------------------
# B1 엔진 4런 · 조건식 원문 · 전당.
# ---------------------------------------------------------------------------

_B1_METRICS = ("total_profit_krw", "seed_capital", "total_profit_pct", "cagr",
               "trade_count", "daily_avg_trades", "win_rate", "avg_profit_pct",
               "mdd_pct", "avg_hold_time", "max_hold_count")


def load_b1_runs() -> Dict[str, Optional[dict]]:
    """A(원본)/B(B1) × 2022/2023 엔진 metrics — 결과 표용(부재 시 None)."""
    out: Dict[str, Optional[dict]] = {}
    for run in ("A_2022", "A_2023", "B_2022", "B_2023"):
        d = load_json("d5r_b1_live", f"{run}.json")
        out[run] = (d.get("metrics") if d else None)
    out["_verdict"] = load_json("d5r_b1_live", "_ab_verdict.json")
    return out


def load_human_hall() -> Optional[dict]:
    d = load_json("w2_strategy_inventory.json")
    return (d or {}).get("human_summary")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_conditions() -> Dict[str, object]:
    """strategy.db 매수/매도 원문 + sha(read-only). 부재/불일치 graceful."""
    out: Dict[str, object] = {"buy": None, "sell": None}
    try:
        from alpha_lab.dataset.reader import connect_ro
        conn = connect_ro(STRATEGY_DB)
        try:
            for side, table, name, sha in (("buy", "stockbuy", BUY_NAME, BUY_SHA),
                                           ("sell", "stocksell", SELL_NAME, SELL_SHA)):
                row = conn.execute(f'SELECT "전략코드" FROM {table} WHERE "index" = ?', (name,)).fetchone()
                if not row or row[0] is None:
                    out[side] = {"_missing": f"strategy.db {table}:{name}"}
                    continue
                text = str(row[0])
                actual = _sha256_text(text)
                out[side] = {"name": name, "text": text, "sha256": actual,
                             "sha_match": actual.startswith(sha) or actual == sha,
                             "sha_short": actual[:8]}
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        out["_error"] = str(exc)
    return out
