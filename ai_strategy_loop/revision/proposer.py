"""리프→절 제안기 (QSP1 P2) — 잔차표에서 수정 명세(revision spec)를 만든다.

방법론(prompt_v2_drafts/analysis_to_revision.md 계약의 코드 구현):
  1) 신뢰 리프(n≥min_n) 중 손실 하위 리프를 고른다(중앙값 우선 — R0 복권형 왜곡 대응).
  2) 그 리프 안에서 승·패를 가장 잘 가르는 조절 변수를 고른다(Cohen's d).
     - 가격 수준 계열(현재가/시가/고가/저가/전일종가)은 다중공선(F-R1-1)이라
       한 축으로 묶고, 조절 절에 없는 변수는 제안 대상에서 제외한다.
  3) 경계 후보 = 리프 내 승 그룹 분위수(데이터구동 — "예쁜 숫자" 발명 금지).
  4) 명세는 리프 1곳·절 1개만 겨냥한다(라운드당 조건식 수정 ≤3 은 상위 러너가 관리).

산출 spec(dict):
  {target, leaf: (band,cap), clause_ident, action, feature, evidence{...},
   old_consts, new_consts, change(사람용 한 줄)}

apply(spec, code): 골격 불변 원칙으로 **해당 리프·해당 절의 상수만** 치환한 새 코드를
만든다(AST 좌표 기반 — 텍스트 전역 치환 금지). 실패는 (None, 사유).
"""

from __future__ import annotations

import ast
import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .hier_ast import parse_leaves, skeleton_fp

# 조절 변수(설명변수) → HIER 절 식별자 후보 매핑.
#   절 식별자는 hier_ast._expr_ident 산출 형식(공백 제거·상수 ? 마스킹)과 맞춘다.
FEATURE_TO_CLAUSE: Dict[str, List[str]] = {
    "B_등락율": ["?<=등락율<=?"],
    "D_시가등락율": ["-?<=시가등락율<?"],
    "D_시가대비등락율": ["-?<=시가대비등락율<?"],
    "B_체결강도": ["체결강도>=?"],
    "D_체결강도비율": ["체결강도>=?"],          # 절은 체결강도 하한 — 비율 신호도 같은 손잡이.
    "D_거래대금폭발배수": ["거래대금비율>?"],
    "B_초당거래대금": ["거래대금비율>?"],
    "B_분당거래대금": ["거래대금비율>?"],
    "D_누적수급비": ["초당순매수금액>?"],
    "D_수급비": ["분당순매수금액>?"],
    "B_전일동시간비": ["전일동시간비>?"],
    "D_고가근접율": ["고가근접율>?"],
}
# 다중공선 가격축(F-R1-1) — 개별 제안 금지(공통 그물 가격대는 리프 절이 아니다).
_PRICE_AXIS = {"B_현재가", "B_시가", "B_고가", "B_저가", "D_전일종가", "B_시분초",
               "B_분봉시가", "B_분봉고가", "B_분봉저가", "B_시가총액"}

_LEAF_MIN_N = 30
_GROUP_MIN_N = 10


def _expr_numbers(expr: str) -> frozenset:
    import re
    return frozenset(float(n) for n in re.findall(r"\d+(?:\.\d+)?", expr))


def _band_windows(timeframe: str) -> Dict[str, frozenset]:
    """라벨 → 유한 경계 숫자 집합. label_dataset 밴드 상수가 단일 출처다.

    hier 밴드 식(예: '90200<=시분초<90500')의 숫자 집합과 **정확 일치**로 사상한다 —
    부분 포함 매칭은 인접 밴드(공유 경계)와 혼동한다(2026-07-30 실측: min 라벨에
    숫자가 없어 기존 자릿수 매칭이 전면 실패했던 결함의 교정).
    """
    from ai_strategy_loop.autopsy.label_dataset import MIN_TIME_BANDS, TICK_TIME_BANDS

    bands = TICK_TIME_BANDS if timeframe == "tick" else MIN_TIME_BANDS
    out: Dict[str, frozenset] = {}
    prev = 0
    for edge, label in bands:
        edges = {float(edge)} | ({float(prev)} if prev else set())
        out[label] = frozenset(edges)
        prev = edge
    return out


_CAP_WINDOWS: Dict[str, frozenset] = {
    "S_3000미만": frozenset({3000.0}),
    "M1_3000_5000": frozenset({3000.0, 5000.0}),
    "M2_5000_10000": frozenset({5000.0, 10000.0}),
    "L_10000이상": frozenset({10000.0}),
}


def _leaf_key_from_labels(band_label: str, cap_label: str,
                          leaves: Dict[Tuple[str, str], Any],
                          timeframe: str) -> Optional[Tuple[str, str]]:
    """label_dataset 리프 라벨 → hier_ast 좌표. 경계 숫자 집합의 정확 일치로 판정."""
    band_want = _band_windows(timeframe).get(band_label)
    cap_want = _CAP_WINDOWS.get(cap_label)
    if band_want is None or cap_want is None:
        return None
    for (b, c) in leaves:
        if _expr_numbers(b) == band_want and _expr_numbers(c) == cap_want:
            return (b, c)
    return None


def _cohen_d(win: pd.Series, loss: pd.Series) -> float:
    if len(win) < _GROUP_MIN_N or len(loss) < _GROUP_MIN_N:
        return 0.0
    pooled = math.sqrt(((len(win) - 1) * float(win.std()) ** 2
                        + (len(loss) - 1) * float(loss.std()) ** 2)
                       / max(1, len(win) + len(loss) - 2))
    if pooled <= 0:
        return 0.0
    return (float(win.mean()) - float(loss.mean())) / pooled


def propose(ds, buy_code: str, target: str, *,
            top_k: int = 3, min_n: int = _LEAF_MIN_N) -> List[Dict[str, Any]]:
    """LabelDataset + 현재 매수식 → 수정 명세 목록(손실 리프 상위 top_k).

    ds: autopsy.label_dataset.LabelDataset (enrich 결과)
    buy_code: 대상 HIER 매수식 원문(절 좌표 확인용)
    target: 전략 이름(명세 표기용)
    """
    hier = parse_leaves(buy_code)
    if not hier.ok:
        return []
    df = ds.df
    pct = pd.to_numeric(df.get("수익률"), errors="coerce")
    overall_median = float(pct.median())
    specs: List[Dict[str, Any]] = []

    # 손실 리프 후보 — 중앙값 오름차순(가장 나쁜 것부터).
    leaf_stats: List[Tuple[float, str, str, pd.Index]] = []
    for (lt, lc), idx in df.groupby(["leaf_time", "leaf_cap"]).groups.items():
        p = pct.loc[idx].dropna()
        if len(p) < min_n:
            continue
        leaf_stats.append((float(p.median()), str(lt), str(lc), idx))
    leaf_stats.sort(key=lambda x: x[0])

    for median_pct, lt, lc, idx in leaf_stats:
        if len(specs) >= top_k:
            break
        if median_pct >= overall_median:
            break  # 전체보다 나쁜 리프가 더 없음.
        leaf_key = _leaf_key_from_labels(lt, lc, hier.leaves, ds.timeframe)
        if leaf_key is None:
            continue
        clause_idents = {c.ident: c for c in hier.leaves[leaf_key]}
        sub = df.loc[idx]
        sub_pct = pct.loc[idx]
        is_win = sub_pct > 0
        # 리프 내 변별 변수 중 '조절 절이 존재하는' 것만 후보.
        best = None
        for feat in ds.features:
            if feat in _PRICE_AXIS:
                continue
            targets = [ci for ci in FEATURE_TO_CLAUSE.get(feat, []) if ci in clause_idents]
            if not targets:
                continue
            vals = pd.to_numeric(sub[feat], errors="coerce")
            d = _cohen_d(vals[is_win].dropna(), vals[~is_win].dropna())
            if best is None or abs(d) > abs(best[1]):
                best = (feat, d, targets[0], vals)
        if best is None or abs(best[1]) < 0.1:
            continue  # 실효 변별 없음 — 이 리프는 이번 라운드 보류.
        feat, d, clause_ident, vals = best
        clause = clause_idents[clause_ident]
        win_vals = vals[is_win].dropna()
        if len(win_vals) < _GROUP_MIN_N:
            continue
        # 데이터구동 경계: 승 그룹 분위수. d>0(승이 큼)→하한을 승 25분위로 올림.
        #   d<0(승이 작음)→상한을 승 75분위로 내림.
        consts = list(clause.consts)
        if d > 0:
            bound = float(win_vals.quantile(0.25))
            new_consts, which = _tighten_lower(clause_ident, consts, bound)
        else:
            bound = float(win_vals.quantile(0.75))
            new_consts, which = _tighten_upper(clause_ident, consts, bound)
        if new_consts is None or tuple(new_consts) == tuple(consts):
            continue
        specs.append({
            "target": target,
            "leaf": list(leaf_key),
            "leaf_label": f"{lt}×{lc}",
            "clause_ident": clause_ident,
            "action": "tighten",
            "feature": feat,
            "evidence": {
                "n": int(len(sub_pct.dropna())),
                "median_pct": median_pct,
                "vs_overall_median": median_pct - overall_median,
                "cohen_d": float(d),
                "win_quantile_bound": bound,
            },
            "old_consts": [float(x) for x in consts],
            "new_consts": [float(x) for x in new_consts],
            "change": f"{lt}×{lc} · {clause_ident} {which} {consts} → {new_consts}"
                      f" (d={d:+.2f}, {feat})",
        })
    return specs


def _round_sig(x: float) -> float:
    """분위수 경계를 조건식 친화 자릿수로(유효 3자리) — 값 자체는 데이터구동."""
    if x == 0:
        return 0.0
    from math import floor, log10
    digits = max(0, 2 - int(floor(log10(abs(x)))))
    return round(x, digits)


def _tighten_lower(ident: str, consts: List[float], bound: float):
    """하한 상향. ident 형태별 상수 위치가 다르다(음수 마스킹 '-?' 유의)."""
    b = _round_sig(bound)
    if ident.startswith("-?<="):
        # '-3.0 <= X < 10.0' → consts=(3.0, 10.0), 하한 실값 = -consts[0].
        if b <= -consts[0]:
            return None, ""
        if b < 0:
            return [abs(b), consts[1]], "하한(-)"
        # 하한이 양수로 넘어가면 골격상 '-?' 유지 불가 → 0 직전까지만 조인다.
        return [0.0, consts[1]], "하한(0캡)"
    if ident.startswith("?<="):
        if b <= consts[0]:
            return None, ""
        return [b] + consts[1:], "하한"
    if ">=?" in ident or ">?" in ident:
        if b <= consts[-1]:
            return None, ""
        return consts[:-1] + [b], "하한"
    return None, ""


def _tighten_upper(ident: str, consts: List[float], bound: float):
    b = _round_sig(bound)
    if ident.startswith("-?<=") or ident.startswith("?<="):
        if b >= consts[-1]:
            return None, ""
        # 하한 실값보다 커야 유효.
        lower_real = -consts[0] if ident.startswith("-?<=") else consts[0]
        if b <= lower_real:
            return None, ""
        return consts[:-1] + [b], "상한"
    # 하한 전용 절(>=)은 상한 조임 불가.
    return None, ""


def apply(spec: Dict[str, Any], code: str) -> Tuple[Optional[str], str]:
    """수정 명세를 코드에 적용 — 해당 리프·해당 절의 상수만 교체(AST 좌표 기반).

    반환 (새 코드, 사유). 골격 지문이 반드시 보존된다(자체 검증 포함).
    """
    hier = parse_leaves(code)
    if not hier.ok:
        return None, f"hier parse 실패: {hier.reason}"
    leaf_key = tuple(spec.get("leaf") or ())
    clauses = hier.leaves.get(leaf_key)  # type: ignore[arg-type]
    if not clauses:
        return None, f"리프 없음: {leaf_key}"
    match = [c for c in clauses if c.ident == spec.get("clause_ident")]
    if not match:
        return None, f"절 없음: {spec.get('clause_ident')}"
    clause = match[0]
    old_consts = [float(x) for x in spec.get("old_consts") or []]
    new_consts = [float(x) for x in spec.get("new_consts") or []]
    if list(clause.consts) != old_consts:
        return None, (f"old_consts 불일치(명세 {old_consts} vs 코드 {list(clause.consts)})"
                      " — 명세가 stale")
    lines = code.splitlines()
    line_i = clause.lineno - 1
    line = lines[line_i]
    new_line = _replace_consts_in_line(line, old_consts, new_consts)
    if new_line is None:
        return None, "라인 상수 치환 실패"
    lines[line_i] = new_line
    new_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    # 자체 검증: 골격 보존 + 의도한 상수만 변경.
    if skeleton_fp(new_code) != skeleton_fp(code):
        return None, "적용 후 골격 지문 불일치(내부 오류)"
    return new_code, "ok"


def _replace_consts_in_line(line: str, old: List[float], new: List[float]) -> Optional[str]:
    """한 줄 안의 숫자 리터럴을 등장 순서대로 old→new 교체(개수·값 일치 필수)."""
    import re
    nums = re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", line)
    vals = [float(n) for n in nums]
    if vals != [abs(x) for x in old] and vals != old:
        # 음수 표기('-3.0')는 부호가 별 토큰 — 절댓값 비교 폴백까지 불일치면 실패.
        return None
    out, idx = "", 0
    pos = 0
    for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", line):
        out += line[pos:m.start()]
        repl = float(new[idx])
        # 원문 표기 보존: 원 토큰에 소수점이 있으면 결과도 소수점 유지(15.0→"15" 방지),
        #   정수 토큰(체결강도 40 등)은 정수 유지.
        if "." in m.group(0):
            text = f"{repl:.10g}"
            if "." not in text:
                text += ".0"
        else:
            text = str(int(repl)) if repl.is_integer() else f"{repl:.10g}"
        out += text
        idx += 1
        pos = m.end()
    out += line[pos:]
    return out
