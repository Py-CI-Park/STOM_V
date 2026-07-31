"""필터 발굴(QSP3 P2) — add_filter 제안·적용·검증.

사용자 방법론: "여러 변수들을 필터하여 수익률을 개선 — 조건식에 여러 필터를 넣어
만드는 원리". 손실 리프에서 승/패를 가르는 변수(FDR q≤α 통과만)를 골라
`elif not (X > t): 매수=False` 절을 리프 끝에 추가한다.

허용 변수 = B_* 캡처 컬럼(접두어 제거 = 런타임 변수명 — 이름 기반 캡처 설계상
동일성이 보장된다). D_* 파생은 v1 제외(런타임 식 합성·0나눗셈 문제, 원장 참조).
채택 기준: 설계·홀드아웃 **양쪽에서 추정 이득 > 0**(제거 규칙과 동일 규율) +
리프 거래 제거율 ≤ 60%(과조임 방지). 추정은 순위용 — 채택은 재백테 실측.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from ai_strategy_loop.autopsy.analyze import _benjamini_hochberg, _two_sample_p
from ai_strategy_loop.autopsy.label_dataset import enrich
from ai_strategy_loop.revision.hier_ast import parse_leaves
from ai_strategy_loop.revision.proposer import _PRICE_AXIS, _cohen_d, _round_sig, _leaf_key_from_labels

FDR_ALPHA = 0.10
LEAF_MIN_N = 30
HOLDOUT_MIN_N = 30          # 홀드아웃 리프 최소 표본(감사1호 A-8 — 1건 충족 방지).
# 손실 리프를 '깎아내는(trim)' 필터의 제거율 상한. 과조임 방지용이지만, 남는
#   부분집합이 양쪽 창에서 흑자면(rescue) 이 상한을 적용하지 않는다 — 사용자
#   지적 실증: B1×소형(−12.7M)의 회전율>3.2 부분집합은 설계 건당 +8,411·홀드
#   +4,749원인데 제거율 80% 라 이 캡에 막혀 후보조차 못 됐다(통째 제거로 유실).
MAX_REMOVED_FRAC = 0.60
MIN_KEEP_N = 60             # rescue 판정에 필요한 최소 잔존 표본(양쪽 창 각각).
QUANTS = (0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90)
# 구조 축(리프 좌표 자체)과 시각류 — 필터 대상 아님.
_STRUCT = {"B_시가총액", "B_시분초"}
# 구간함수형 이름(감사1호 BUG-Q1): 캡처 컬럼명과 겹치지만 런타임에서는 `이름(30)`
#   형태의 함수라 `이름 > t` 절이 엔진 exec 에서 TypeError→정지를 만든다.
#   출처: backtest/back_code_test.py CheckFactor 의 gugan_factors(스냅샷 캡처 대상만 발췌).
_GUGAN_FUNCS = {
    "체결강도평균", "초당거래대금평균", "분당거래대금평균",
    "등락율각도", "당일거래대금각도", "전일비각도",
    "누적초당매수수량", "누적초당매도수량", "누적분당매수수량", "누적분당매도수량",
    "최고체결강도", "최저체결강도", "최고현재가", "최저현재가",
    "최고초당매수수량", "최고초당매도수량", "최고분당매수수량", "최고분당매도수량",
    "RSI",
}


def _runtime_var(feature: str) -> Optional[str]:
    if not feature.startswith("B_") or feature in _PRICE_AXIS or feature in _STRUCT:
        return None
    var = feature[2:]
    if var in _GUGAN_FUNCS:
        return None
    return var


def _leaf_frames(csv_path: str):
    ds = enrich(pd.read_csv(csv_path, encoding="utf-8-sig"))
    df = ds.df
    return df, {(lt, lc): df.loc[idx]
                for (lt, lc), idx in df.groupby(["leaf_time", "leaf_cap"]).groups.items()}


def _quarter_key(df: pd.DataFrame) -> pd.Series:
    """매수시간(YYYYMMDDHHMMSS) → 'YYYYQn' 분기 라벨(구간 일관성 검정용)."""
    s = df["매수시간"].astype(str).str.slice(0, 6)
    year = s.str.slice(0, 4)
    month = pd.to_numeric(s.str.slice(4, 6), errors="coerce").fillna(1)
    return year + "Q" + ((month - 1) // 3 + 1).astype(int).astype(str)


def _one_sample_p(x: pd.Series) -> float:
    """평균>0 단측 p값(정규근사). 잔존 부분집합의 엣지가 잡음인지 판정용."""
    v = pd.to_numeric(x, errors="coerce").dropna()
    n = len(v)
    if n < 10:
        return 1.0
    sd = float(v.std())
    if sd <= 0:
        return 1.0
    t = float(v.mean()) / (sd / math.sqrt(n))
    if t <= 0:
        return 1.0
    return float(min(1.0, 0.5 * math.erfc(t / math.sqrt(2.0))))


def _rescue_candidates(sub, sub_h, feats, leaf_key, leaf_label, clause_idents,
                       excluded, alpha: float) -> List[Dict[str, Any]]:
    """구제 탐색 — '남는 부분집합이 양쪽 창에서 흑자'인 (변수, 임계) 를 직접 찾는다.

    왜 별도 경로인가(사용자 지적의 핵심): 기존 선별은 '승자 평균 vs 패자 평균'
    차이(효과크기+FDR)로 변수를 먼저 거른다. 그런데 실제 엣지는 분포의 **꼬리**에
    있을 수 있다 — B1×소형 리프의 회전율은 d=+0.06·q=0.87(무의미)인데 상위 20%만
    남기면 설계 +1.27M·홀드 +0.92M 이다. 평균 비교로는 보이지 않는 이 주머니를
    놓치면 '손실 구역'을 통째로 버리게 된다. 그래서 여기서는 사전 선별 없이
    (변수 × 임계) 전수를 목적함수(잔존 손익)로 직접 평가하고, 다중비교는 **잔존
    부분집합의 단측 검정 p값**에 BH 를 걸어 통제한다. 홀드아웃 흑자 요건이
    표본외 확인을 겸한다.
    """
    rows: List[Dict[str, Any]] = []
    for f in feats:
        var = _runtime_var(f)
        if var is None or (f, leaf_label) in excluded:
            continue
        pat = re.compile(rf"(?<![0-9A-Za-z_가-힣]){re.escape(var)}(?![0-9A-Za-z_가-힣])")
        if any(pat.search(ci) for ci in clause_idents):
            continue
        vd = pd.to_numeric(sub[f], errors="coerce")
        vh = pd.to_numeric(sub_h[f], errors="coerce") if f in sub_h.columns else None
        if vh is None:
            continue
        for q in QUANTS:
            t = _round_sig(float(vd.quantile(q)))
            for op in (">", "<="):
                keep_d = (vd > t) if op == ">" else (vd <= t)
                keep_h = ((vh > t) if op == ">" else (vh <= t)).fillna(False)
                kn_d, kn_h = int(keep_d.sum()), int(keep_h.sum())
                if kn_d < MIN_KEEP_N or kn_h < MIN_KEEP_N:
                    continue
                kp_d = float(sub.loc[keep_d, "수익금"].sum())
                kp_h = float(sub_h.loc[keep_h, "수익금"].sum())
                if kp_d <= 0 or kp_h <= 0:
                    continue          # 양쪽 창 흑자만 구제로 인정.
                p = _one_sample_p(sub.loc[keep_d, "수익률"])
                # 분기 일관성 — 설계구간을 YYYYQ 로 쪼개 흑자 분기 비율.
                kept = sub.loc[keep_d]
                per_q = kept.groupby(_quarter_key(kept))["수익금"].sum()
                q_pos = int((per_q > 0).sum())
                q_all = int(len(per_q))
                q_req = max(2, (q_all + 1) // 2)   # 과반(최소 2분기).
                rows.append({"feature": f, "runtime_var": var, "op": op, "threshold": t,
                             "p": p, "quarters_pos": q_pos, "quarters_all": q_all,
                             "quarters_req": q_req,
                             "kept_n_design": kn_d, "kept_n_holdout": kn_h,
                             "kept_pnl_design": kp_d, "kept_pnl_holdout": kp_h,
                             "kept_per_trade_design": kp_d / kn_d,
                             "kept_per_trade_holdout": kp_h / kn_h,
                             "removed_n": int((~keep_d).sum()),
                             "removed_frac": float((~keep_d).mean()),
                             "est_delta_design": -float(sub.loc[~keep_d, "수익금"].sum()),
                             "est_delta_holdout": -float(sub_h.loc[~keep_h, "수익금"].sum())})
    if not rows:
        return []
    # 검정 규격(중요): 이 분포는 복권형(승률 46%·표준편차 4%대)이라 평균 단측 t검정은
    #   힘이 없다 — 실측 p 0.18~0.49. 그래서 하드 게이트는 **시간 구간 일관성**으로
    #   둔다: 설계구간을 분기로 쪼개 과반 분기에서 흑자 + 홀드아웃 흑자.
    #   (p/q 는 증거로 함께 기록하되 단독 채택 기준으로 쓰지 않는다.)
    _q, _flags = _benjamini_hochberg([r["p"] for r in rows], alpha)
    for r, q in zip(rows, _q):
        r["q"] = float(q)
    passed = [r for r in rows if r["quarters_pos"] >= r["quarters_req"]]
    if not passed:
        return []
    # 변수당 최선 1개(같은 변수의 인접 임계 중복 방지) → 양쪽 최소 건당 엣지 순.
    best_by_var: Dict[str, Dict[str, Any]] = {}
    for r in passed:
        edge = min(r["kept_per_trade_design"], r["kept_per_trade_holdout"])
        cur = best_by_var.get(r["runtime_var"])
        if cur is None or edge > min(cur["kept_per_trade_design"], cur["kept_per_trade_holdout"]):
            best_by_var[r["runtime_var"]] = r
    out = []
    for r in best_by_var.values():
        out.append({
            "action": "add_filter", "leaf": list(leaf_key), "leaf_label": leaf_label,
            "feature": r["feature"], "runtime_var": r["runtime_var"],
            "op": r["op"], "threshold": r["threshold"], "rescue": True,
            "est_delta_design": r["est_delta_design"],
            "est_delta_holdout": r["est_delta_holdout"],
            "evidence": {k: r[k] for k in ("p", "q", "quarters_pos", "quarters_all",
                                           "kept_n_design", "kept_n_holdout",
                                           "kept_pnl_design", "kept_pnl_holdout",
                                           "kept_per_trade_design", "kept_per_trade_holdout",
                                           "removed_n", "removed_frac")},
            "change": (f"RESCUE {leaf_label} · {r['runtime_var']} {r['op']} {r['threshold']}"
                       f" — 잔존 설계 {r['kept_per_trade_design']:+,.0f}원/건({r['kept_n_design']}건)"
                       f" · 홀드 {r['kept_per_trade_holdout']:+,.0f}원/건({r['kept_n_holdout']}건)"
                       f" · 흑자분기 {r['quarters_pos']}/{r['quarters_all']} · p={r['p']:.3f}"),
        })
    return out


def propose_filters(design_csv: str, holdout_csv: str, buy_code: str, *,
                    top_k: int = 3, exclude: Optional[Set[Tuple[str, str]]] = None,
                    alpha: float = FDR_ALPHA, timeframe: str = "tick") -> List[Dict[str, Any]]:
    """손실 리프에서 필터 후보 — ① 구제(잔존 흑자) 우선 ② 없으면 손실 깎기(trim)."""
    hier = parse_leaves(buy_code)
    if not hier.ok:
        return []
    df_d, leaves_d = _leaf_frames(design_csv)
    _, leaves_h = _leaf_frames(holdout_csv)
    excluded = exclude or set()
    feats = [c for c in df_d.columns if _runtime_var(c)]
    cands: List[Dict[str, Any]] = []
    for (lt, lc), sub in sorted(leaves_d.items(), key=lambda kv: kv[1]["수익금"].sum()):
        if float(sub["수익금"].sum()) >= 0 or len(sub) < LEAF_MIN_N:
            continue
        leaf_label = f"{lt}×{lc}"
        leaf_key = _leaf_key_from_labels(str(lt), str(lc), hier.leaves, timeframe)
        if leaf_key is None:
            continue
        clauses = hier.leaves[leaf_key]
        if clauses and clauses[0].ident == "?":
            continue  # 드롭된 리프 — 필터 무의미.
        existing_idents = [c.ident for c in clauses]
        sub_h = leaves_h.get((lt, lc))
        if sub_h is None or len(sub_h) < HOLDOUT_MIN_N:
            continue  # 홀드아웃 표본 부족 — '양쪽 이득' 판단 불가(A-8).
        is_win = pd.to_numeric(sub["수익률"], errors="coerce") > 0
        # ⓪ 구제 탐색 우선 — 잔존 부분집합이 양쪽 창 흑자인 (변수, 임계).
        rescued = _rescue_candidates(sub, sub_h, feats, leaf_key, leaf_label,
                                     existing_idents, excluded, alpha)
        if rescued:
            cands.extend(rescued)
            continue    # 이 리프는 구제안으로 간다(깎기 후보와 섞지 않는다).
        # ① 리프 내 변수 family 에 FDR — 잡음 필터 컷(감사 B1 처방).
        stats = []
        _re = re
        for f in feats:
            var = _runtime_var(f)
            if var is None or (f, leaf_label) in excluded:
                continue
            # 토큰 경계 일치(감사2 A11): '등락율' 이 '시가등락율' 절 때문에 과다
            #   배제되지 않도록 부분문자열이 아닌 변수 토큰으로 대조.
            pat = _re.compile(rf"(?<![0-9A-Za-z_가-힣]){_re.escape(var)}(?![0-9A-Za-z_가-힣])")
            if any(pat.search(ident) for ident in existing_idents):
                continue
            vals = pd.to_numeric(sub[f], errors="coerce")
            d = _cohen_d(vals[is_win].dropna(), vals[~is_win].dropna())
            if abs(d) < 1e-12:
                continue
            p = _two_sample_p(d, int(is_win.sum()), int((~is_win).sum()))
            stats.append((f, var, d, p))
        if not stats:
            continue
        _qvals, flags = _benjamini_hochberg([s[3] for s in stats], alpha)
        passed = [(f, var, d) for (f, var, d, _p), ok in zip(stats, flags) if ok]
        # ② 통과 변수만 임계 스윕 — 설계·홀드아웃 양쪽 추정 이득 요구.
        for f, var, d in passed:
            vd = pd.to_numeric(sub[f], errors="coerce")
            vh = pd.to_numeric(sub_h.get(f), errors="coerce") if f in sub_h.columns else None
            if vh is None:
                continue
            best = None
            for q in QUANTS:
                t = _round_sig(float(vd.quantile(q)))
                for op in (">", "<="):
                    kill_d = (vd <= t) if op == ">" else (vd > t)
                    kill_h = (vh <= t) if op == ">" else (vh > t)
                    kill_h = kill_h.fillna(False)
                    if not kill_d.any():
                        continue
                    est_d = -float(sub.loc[kill_d, "수익금"].sum())
                    est_h = -float(sub_h.loc[kill_h, "수익금"].sum())
                    if est_d <= 0 or est_h <= 0:
                        continue
                    # 잔존 부분집합(= 실제로 계속 매수할 거래)의 성적.
                    keep_d, keep_h = ~kill_d, ~kill_h
                    kn_d, kn_h = int(keep_d.sum()), int(keep_h.sum())
                    kp_d = float(sub.loc[keep_d, "수익금"].sum())
                    kp_h = float(sub_h.loc[keep_h, "수익금"].sum())
                    rescue = (kn_d >= MIN_KEEP_N and kn_h >= MIN_KEEP_N
                              and kp_d > 0 and kp_h > 0)
                    if not rescue and float(kill_d.mean()) > MAX_REMOVED_FRAC:
                        continue  # 구제가 아니면 과조임 캡 적용.
                    cand = {"op": op, "threshold": t,
                            "est_delta_design": est_d, "est_delta_holdout": est_h,
                            "removed_frac": float(kill_d.mean()),
                            "removed_n": int(kill_d.sum()),
                            "rescue": rescue, "kept_n_design": kn_d, "kept_n_holdout": kn_h,
                            "kept_pnl_design": kp_d, "kept_pnl_holdout": kp_h,
                            "kept_per_trade_design": kp_d / kn_d if kn_d else 0.0,
                            "kept_per_trade_holdout": kp_h / kn_h if kn_h else 0.0}
                    # 우선순위: ① 구제(잔존 흑자) 후보 ② 그 안에선 잔존 건당 엣지
                    #   (설계·홀드 최솟값 — 양쪽에서 살아남는 엣지) ③ 아니면 est_d.
                    def _key(c):
                        return (1 if c["rescue"] else 0,
                                min(c["kept_per_trade_design"], c["kept_per_trade_holdout"])
                                if c["rescue"] else 0.0,
                                c["est_delta_design"])
                    if best is None or _key(cand) > _key(best):
                        best = cand
            if best is None:
                continue
            tag = "RESCUE" if best["rescue"] else "FILTER"
            extra = ""
            if best["rescue"]:
                extra = (f" · 잔존 흑자 설계 {best['kept_per_trade_design']:+,.0f}원/건"
                         f"({best['kept_n_design']}건) 홀드 {best['kept_per_trade_holdout']:+,.0f}원/건"
                         f"({best['kept_n_holdout']}건)")
            cands.append({
                "action": "add_filter", "leaf": list(leaf_key), "leaf_label": leaf_label,
                "feature": f, "runtime_var": var,
                "op": best["op"], "threshold": best["threshold"],
                "rescue": best["rescue"],
                "est_delta_design": best["est_delta_design"],
                "est_delta_holdout": best["est_delta_holdout"],
                "evidence": {"cohen_d": float(d), "n": int(len(sub)),
                             "removed_n": best["removed_n"],
                             "removed_frac": best["removed_frac"],
                             "kept_n_design": best["kept_n_design"],
                             "kept_n_holdout": best["kept_n_holdout"],
                             "kept_pnl_design": best["kept_pnl_design"],
                             "kept_pnl_holdout": best["kept_pnl_holdout"],
                             "kept_per_trade_design": best["kept_per_trade_design"],
                             "kept_per_trade_holdout": best["kept_per_trade_holdout"]},
                "change": f"{tag} {leaf_label} · {var} {best['op']} {best['threshold']}"
                          f" (설계 +{best['est_delta_design']:,.0f}/홀드"
                          f" +{best['est_delta_holdout']:,.0f}, d={d:+.2f}){extra}",
            })
    # 구제 후보 우선 — 그 안에선 '양쪽 창에서 살아남는 건당 엣지' 큰 순.
    cands.sort(key=lambda s: (1 if s.get("rescue") else 0,
                              min(s["evidence"].get("kept_per_trade_design", 0),
                                  s["evidence"].get("kept_per_trade_holdout", 0))
                              if s.get("rescue") else 0.0,
                              s["est_delta_design"]), reverse=True)
    # 리프당 1개(같은 리프에 필터 중복 금지 — 후보 다양성).
    seen, out = set(), []
    for s in cands:
        if s["leaf_label"] in seen:
            continue
        seen.add(s["leaf_label"])
        out.append(s)
        if len(out) >= top_k:
            break
    return out


def apply_filter(spec: Dict[str, Any], code: str) -> Tuple[Optional[str], str]:
    """리프 절 체인 끝에 `elif not (X op t): 매수 = False` 를 삽입."""
    hier = parse_leaves(code)
    if not hier.ok:
        return None, f"hier parse 실패: {hier.reason}"
    leaf_key = tuple(spec.get("leaf") or ())
    clauses = hier.leaves.get(leaf_key)  # type: ignore[arg-type]
    if not clauses:
        return None, f"리프 없음: {leaf_key}"
    if clauses[0].ident == "?":
        return None, "드롭된 리프에는 필터 추가 불가"
    last = clauses[-1]
    lines = code.split("\n")
    head_line = lines[last.lineno - 1]
    indent = head_line[:len(head_line) - len(head_line.lstrip())]
    # 마지막 절의 본문(매수=False) 줄 뒤에 삽입 — 본 골격에서 본문은 항상 한 줄.
    insert_at = last.lineno + 1
    if insert_at > len(lines) or "매수" not in lines[insert_at - 1]:
        return None, f"마지막 절 본문 형태 예상 밖(줄 {insert_at})"
    var, op, t = spec["runtime_var"], spec["op"], spec["threshold"]
    new_lines = [f"{indent}elif not ({var} {op} {t}):  # ADD_FILTER — QSP3",
                 f"{indent}    매수 = False"]
    lines[insert_at:insert_at] = new_lines
    new_code = "\n".join(lines)
    try:
        compile(new_code, "<filter>", "exec")
    except SyntaxError as e:
        return None, f"필터 결과 구문 오류: {e}"
    return new_code, ""


def verify_filter(spec: Dict[str, Any], old_code: str, new_code: str) -> Tuple[bool, str]:
    """의도-일치 검증(필터 전용) — diff 가 '대상 리프 끝 절 1개 추가' 뿐인지."""
    old_h, new_h = parse_leaves(old_code), parse_leaves(new_code)
    if not old_h.ok or not new_h.ok:
        return False, "parse 실패"
    if set(old_h.leaves) != set(new_h.leaves):
        return False, "V_FILTER: 리프 키 집합 변경"
    # 전체 파일 라인 diff 가드(감사1호 A-2/BUG-Q4): 생성기는 정확히 2줄 삽입만 한다 —
    #   그 외의 어떤 라인 변경(리프 본문·공통 그물·파생부)도 여기서 걸린다.
    old_lines, new_lines = old_code.split("\n"), new_code.split("\n")
    if len(new_lines) != len(old_lines) + 2:
        return False, "V_FILTER: 삽입 줄 수 ≠ 2"
    ins_at = next((i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b),
                  len(old_lines))
    inserted = new_lines[ins_at:ins_at + 2]
    if old_lines[ins_at:] != new_lines[ins_at + 2:]:
        return False, "V_FILTER: 삽입 외 라인 변경 존재"
    if "ADD_FILTER" not in inserted[0] or inserted[1].strip() != "매수 = False":
        return False, "V_FILTER: 삽입 줄 형태 불일치"
    target = tuple(spec.get("leaf") or ())
    # 음수 임계는 파서가 부호를 마스킹('-?')하므로 기대 ident 도 부호를 반영(BUG-Q2).
    neg = float(spec.get("threshold") or 0) < 0
    want_ident = f"{spec['runtime_var']}{spec['op']}{'-?' if neg else '?'}"
    for key in old_h.leaves:
        o = [(c.ident, tuple(c.consts)) for c in old_h.leaves[key]]
        n = [(c.ident, tuple(c.consts)) for c in new_h.leaves[key]]
        if key == target:
            if len(n) != len(o) + 1 or n[:-1] != o:
                return False, "V_FILTER: 기존 절 변형 또는 삽입 위치 이상"
            ident, consts = n[-1]
            if ident != want_ident:
                return False, f"V_FILTER: 새 절 형태 불일치 {ident} ≠ {want_ident}"
            if not consts or abs(float(consts[-1]) - abs(float(spec["threshold"]))) > 1e-9:
                return False, f"V_FILTER: 임계 불일치 {consts}"
        elif n != o:
            return False, f"V_FILTER: 명세 밖 리프 변경 {key}"
    return True, ""
