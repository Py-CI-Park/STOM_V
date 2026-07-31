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

from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from ai_strategy_loop.autopsy.analyze import _benjamini_hochberg, _two_sample_p
from ai_strategy_loop.autopsy.label_dataset import enrich
from ai_strategy_loop.revision.hier_ast import parse_leaves
from ai_strategy_loop.revision.proposer import _PRICE_AXIS, _cohen_d, _round_sig, _leaf_key_from_labels

FDR_ALPHA = 0.10
LEAF_MIN_N = 30
HOLDOUT_MIN_N = 30          # 홀드아웃 리프 최소 표본(감사1호 A-8 — 1건 충족 방지).
MAX_REMOVED_FRAC = 0.60
QUANTS = (0.10, 0.25, 0.50, 0.75, 0.90)
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


def propose_filters(design_csv: str, holdout_csv: str, buy_code: str, *,
                    top_k: int = 3, exclude: Optional[Set[Tuple[str, str]]] = None,
                    alpha: float = FDR_ALPHA, timeframe: str = "tick") -> List[Dict[str, Any]]:
    """손실 리프 × FDR 통과 변수 × 분위 임계 스윕 → 양쪽 이득 필터 top_k."""
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
        # ① 리프 내 변수 family 에 FDR — 잡음 필터 컷(감사 B1 처방).
        stats = []
        import re as _re
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
                    if not kill_d.any() or kill_d.mean() > MAX_REMOVED_FRAC:
                        continue
                    est_d = -float(sub.loc[kill_d, "수익금"].sum())
                    est_h = -float(sub_h.loc[kill_h.fillna(False), "수익금"].sum())
                    if est_d <= 0 or est_h <= 0:
                        continue
                    if best is None or est_d > best["est_delta_design"]:
                        best = {"op": op, "threshold": t,
                                "est_delta_design": est_d, "est_delta_holdout": est_h,
                                "removed_frac": float(kill_d.mean()),
                                "removed_n": int(kill_d.sum())}
            if best is None:
                continue
            cands.append({
                "action": "add_filter", "leaf": list(leaf_key), "leaf_label": leaf_label,
                "feature": f, "runtime_var": var,
                "op": best["op"], "threshold": best["threshold"],
                "est_delta_design": best["est_delta_design"],
                "est_delta_holdout": best["est_delta_holdout"],
                "evidence": {"cohen_d": float(d), "n": int(len(sub)),
                             "removed_n": best["removed_n"],
                             "removed_frac": best["removed_frac"]},
                "change": f"FILTER {leaf_label} · {var} {best['op']} {best['threshold']}"
                          f" (설계 +{best['est_delta_design']:,.0f}/홀드"
                          f" +{best['est_delta_holdout']:,.0f}, d={d:+.2f})",
            })
    cands.sort(key=lambda s: s["est_delta_design"], reverse=True)
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
