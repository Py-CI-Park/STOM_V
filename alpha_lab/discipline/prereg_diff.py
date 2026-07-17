# -*- coding: utf-8 -*-
"""봉인 사전등록 md ↔ 결과 json 자동 대조기 (백로그 A5 / WBS v3 P1-2, 보고 전용).

역할: 봉인 문서가 선언한 수치(원문 sha·발견창 날짜·온셋 수·n_boot·FDR q·분모
상한 등)를 정규식 규칙으로 추출해, 판정 결과 json 의 대응 키와 기계 대조한다.
감사 §6.1(봉인 문구 ≠ 실제 표본) 유형의 재발을 커밋 전에 드러내는 것이 목적.

규율(봉인 조건 준수):
- 보고 전용 — 어떤 파일도 수정하지 않고 측정을 차단하지 않는다. 기동 차단은
  measure_gate(A7), 문서 정적 린트는 ledger-lint(A4) 소관 — 3계층 방어선 분담.
- 오탐 최소화 우선 — 자동 매핑이 확실한 항목만 MATCH/MISMATCH 를 선언하고,
  매핑이 불확실한 선언(효과크기 하한·표본 하한·연도 세율·param_sha 등 결과
  json 에 직접 대응 키가 없는 항목)은 전부 '수동 확인 필요(MANUAL)'로 격리한다.
- 판정 주체는 사람 유지(백로그 A5 조건) — 본 도구는 대조 근거만 공급한다.

첫 실전 적용 대상(D1):
  봉인: docs/research/condition_research/plans/
        2026-07-12_d1_clause_ablation_preregistration.md
  결과: docs/research/condition_research/research_runs/alpha_restart_20260710/
        d1_clause_ablation_summary.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── 선언 추출 규칙(정규식) ────────────────────────────────────────────────────
# 오탐 최소화를 위해 전부 "키워드 문맥이 붙은" 패턴만 쓴다. 벌거벗은 숫자는 안 잡는다.
_RE_DATE_PAIR = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")
_RE_BUY_SHA = re.compile(r"buy(?:_code)?_sha(?:256)?\s*[`: ]*([0-9a-fA-F]{8,64})")
_RE_SELL_SHA = re.compile(r"sell_sha(?:256)?\s*[`: ]*([0-9a-fA-F]{8,64})")
_RE_PARAM_SHA = re.compile(r"param_sha\s*[`: ]*([0-9a-fA-F]{8,64})")
_RE_NBOOT = re.compile(r"n_boot\s*=?\s*(\d+)")
_RE_FDR_Q = re.compile(r"\bq\s*=\s*(\d*\.\d+)")
_RE_CAP_SEAL = re.compile(
    r"상한[은는]?\s*\*{0,2}(\d{1,4})\*{0,2}\s*[로으]?로?\s*봉인"
    r"|상한\s*봉인\s*\(≤\s*(\d{1,4})\)"
)
_RE_COUNT_GEON = re.compile(r"(\d[\d,]{3,})\s*건")
_RE_EFFECT_FLOOR = re.compile(r"≥\s*\+(\d+\.\d+)\s*%p")
_RE_N_FLOOR = re.compile(r"n\s*≥\s*([\d,]+)")
_RE_YEAR_FLOOR = re.compile(r"연도별\s*각?\s*≥\s*([\d,]+)")
_RE_TAX_RATE = re.compile(r"(20\d{2})\s*=\s*(\d+(?:\.\d+)?)\s*%")

# 온셋 건수로 인정할 최소값 — "미결 4건" 같은 소수 카운트 오탐 차단.
_MIN_ONSET_COUNT = 10_000

_SHA_KEYS = frozenset({"buy_sha256", "sell_sha256", "param_sha"})

# 자동 대조 규칙: 선언 키 → (결과 json 경로 후보들, 비교 방식).
# 여기 없는 선언 키는 전부 MANUAL 로 격리된다(오탐 최소화의 축).
_AUTO_RULES: dict[str, tuple[tuple[str, ...], str]] = {
    "buy_sha256": (("buy_sha256",), "sha"),
    "sell_sha256": (("sell_sha256",), "sha"),
    "window_discovery": (("window",), "window"),
    "n_onsets": (("bank_meta.n_onsets_total", "consolidate.n_onsets"), "int_all"),
    "n_boot": (("judgment.per_clause.*.n_boot",), "int_uniform"),
    "fdr_q": (("judgment.fdr_q",), "float"),
    "sealed_cap": (("gate.qualified.sealed_cap",), "int_all"),
}
# sealed_cap 이 정상 추출되면 파생 검사: 실제 FDR 분모가 봉인 상한 이하인가.
_BOUND_KEY = "fdr_denominator≤sealed_cap"
_BOUND_PATHS = ("judgment.fdr_denominator", "gate.qualified.fdr_denominator")

_STATUS_ORDER = {"MISMATCH": 0, "MATCH": 1, "MANUAL": 2}


@dataclass(frozen=True)
class Declaration:
    """봉인 md 에서 추출한 선언 1건 (불변)."""

    key: str
    value: str
    raw: str
    line_no: int
    conflict: bool  # 같은 키로 서로 다른 값이 추출됨 → 자동 판정 금지


@dataclass(frozen=True)
class DiffEntry:
    """대조 결과 1행 (불변). status ∈ {MATCH, MISMATCH, MANUAL}."""

    key: str
    status: str
    declared: str
    observed: str
    json_path: str
    note: str
    md_line: int
    md_raw: str


# ── 1단계: 선언 추출 ─────────────────────────────────────────────────────────
def _extract_line(line: str, no: int) -> list[tuple[str, str, str, int]]:
    """한 라인에서 (key, value, raw, line_no) 선언 후보를 전부 수집한다."""
    raw = line.rstrip()
    found: list[tuple[str, str]] = []
    for m in _RE_BUY_SHA.finditer(line):
        found.append(("buy_sha256", m.group(1).lower()))
    for m in _RE_SELL_SHA.finditer(line):
        found.append(("sell_sha256", m.group(1).lower()))
    for m in _RE_PARAM_SHA.finditer(line):
        found.append(("param_sha", m.group(1).lower()))
    for m in _RE_DATE_PAIR.finditer(line):
        pair = f"{m.group(1)}~{m.group(2)}"
        if "발견" in line:
            found.append(("window_discovery", pair))
        else:
            found.append((f"window_other[{pair}]", pair))
    for m in _RE_NBOOT.finditer(line):
        found.append(("n_boot", m.group(1)))
    for m in _RE_FDR_Q.finditer(line):
        found.append(("fdr_q", m.group(1)))
    for m in _RE_CAP_SEAL.finditer(line):
        found.append(("sealed_cap", m.group(1) or m.group(2)))
    if "온셋" in line:
        for m in _RE_COUNT_GEON.finditer(line):
            if int(m.group(1).replace(",", "")) >= _MIN_ONSET_COUNT:
                found.append(("n_onsets", m.group(1).replace(",", "")))
    for m in _RE_EFFECT_FLOOR.finditer(line):
        found.append(("effect_floor_pp", m.group(1)))
    for m in _RE_N_FLOOR.finditer(line):
        found.append(("sample_floor_each", m.group(1).replace(",", "")))
    for m in _RE_YEAR_FLOOR.finditer(line):
        found.append(("sample_floor_year", m.group(1).replace(",", "")))
    for m in _RE_TAX_RATE.finditer(line):
        found.append((f"tax_rate_{m.group(1)}", m.group(2)))
    return [(k, v, raw, no) for k, v in found]


def _merge_sha_prefixes(values: list[str]) -> list[str]:
    """서로 접두 관계인 sha 축약들을 최장값 하나로 병합한다(아니면 그대로)."""
    longest = max(values, key=len)
    if all(longest.startswith(v) for v in values):
        return [longest]
    return values


def extract_declarations(md_text: str) -> tuple[Declaration, ...]:
    """봉인 md 전체에서 선언을 추출하고 키별 dedupe/충돌 표시를 한다."""
    items: list[tuple[str, str, str, int]] = []
    for no, line in enumerate(md_text.splitlines(), start=1):
        items.extend(_extract_line(line, no))
    by_key: dict[str, list[tuple[str, str, int]]] = {}
    for key, value, raw, no in items:
        by_key.setdefault(key, []).append((value, raw, no))
    out: list[Declaration] = []
    for key, vals in by_key.items():
        uniq = list(dict.fromkeys(v for v, _, _ in vals))
        if key in _SHA_KEYS and len(uniq) > 1:
            uniq = _merge_sha_prefixes(uniq)
        _, raw0, no0 = vals[0]
        if len(uniq) == 1:
            out.append(Declaration(key, uniq[0], raw0, no0, False))
        else:
            out.append(Declaration(key, " | ".join(uniq), raw0, no0, True))
    return tuple(sorted(out, key=lambda d: (d.line_no, d.key)))


# ── 2단계: 결과 json 경로 해석 ───────────────────────────────────────────────
def resolve_paths(data: Any, pattern: str) -> tuple[tuple[str, Any], ...]:
    """'a.b.*.c' 형 점 경로(글롭 * 지원)를 (경로, 값) 쌍들로 해석한다."""
    nodes: list[tuple[str, Any]] = [("", data)]
    for part in pattern.split("."):
        nxt: list[tuple[str, Any]] = []
        for path, node in nodes:
            if not isinstance(node, dict):
                continue
            if part == "*":
                for k, v in node.items():
                    nxt.append((f"{path}.{k}".lstrip("."), v))
            elif part in node:
                nxt.append((f"{path}.{part}".lstrip("."), node[part]))
        nodes = nxt
    return tuple(nodes)


# ── 3단계: 비교기 ────────────────────────────────────────────────────────────
def _to_int(value: Any) -> int:
    return int(str(value).replace(",", ""))


def _cmp_values(kind: str, declared: str,
                pairs: tuple[tuple[str, Any], ...]) -> tuple[bool, str]:
    """비교 방식별 판정. (일치 여부, 부가 설명) 을 돌려준다."""
    if kind == "sha":
        ok = all(isinstance(v, str) and v.lower().startswith(declared.lower())
                 for _, v in pairs)
        return ok, "축약 sha 는 접두 일치로 대조"
    if kind == "int_all":
        d = _to_int(declared)
        return all(_to_int(v) == d for _, v in pairs), ""
    if kind == "int_uniform":
        d = _to_int(declared)
        vals = {_to_int(v) for _, v in pairs}
        return vals == {d}, f"{len(pairs)}개 경로 균일성 포함 검사"
    if kind == "float":
        d = float(declared)
        return all(abs(float(v) - d) < 1e-9 for _, v in pairs), ""
    if kind == "int_upper_bound":
        d = _to_int(declared)
        return all(_to_int(v) <= d for _, v in pairs), "상한(≤) 검사 — 등호 아님"
    if kind == "window":
        for _, v in pairs:
            m = _RE_DATE_PAIR.search(str(v))
            if m is None or f"{m.group(1)}~{m.group(2)}" != declared:
                return False, "결과 창 문자열에서 날짜쌍 추출 대조"
        return True, "결과 창 문자열에서 날짜쌍 추출 대조"
    raise ValueError(f"알 수 없는 비교 방식: {kind}")


def _observed_repr(pairs: tuple[tuple[str, Any], ...]) -> tuple[str, str]:
    """관측값 표시 문자열과 대표 경로 문자열을 만든다(긴 글롭은 요약)."""
    vals = list(dict.fromkeys(str(v) for _, v in pairs))
    if len(pairs) > 3:
        return "/".join(vals), f"{pairs[0][0]} 외 {len(pairs) - 1}개"
    return ", ".join(str(v) for _, v in pairs), "; ".join(p for p, _ in pairs)


def _auto_entry(decl: Declaration, patterns: tuple[str, ...], kind: str,
                data: Any) -> DiffEntry:
    """자동 매핑 규칙 1건을 결과 json 과 대조해 DiffEntry 로 만든다."""
    pairs: tuple[tuple[str, Any], ...] = ()
    for pat in patterns:
        pairs += resolve_paths(data, pat)
    if not pairs:
        return DiffEntry(decl.key, "MANUAL", decl.value, "", "",
                         "결과 json 에 대응 키 없음 — 수동 확인 필요",
                         decl.line_no, decl.raw)
    try:
        ok, note = _cmp_values(kind, decl.value, pairs)
    except (TypeError, ValueError):
        return DiffEntry(decl.key, "MANUAL", decl.value, "", "; ".join(patterns),
                         "관측값 형 변환 실패 — 수동 확인 필요",
                         decl.line_no, decl.raw)
    observed, path_repr = _observed_repr(pairs)
    return DiffEntry(decl.key, "MATCH" if ok else "MISMATCH", decl.value,
                     observed, path_repr, note, decl.line_no, decl.raw)


def compare(declarations: tuple[Declaration, ...], data: Any) -> tuple[DiffEntry, ...]:
    """선언 전체를 대조한다. 자동 규칙 밖 선언은 전부 MANUAL 격리."""
    entries: list[DiffEntry] = []
    sealed_cap: Declaration | None = None
    for decl in declarations:
        if decl.conflict:
            entries.append(DiffEntry(
                decl.key, "MANUAL", decl.value, "", "",
                "선언 값 충돌(문서 내 상이값) — 수동 확인 필요",
                decl.line_no, decl.raw))
            continue
        if decl.key in _AUTO_RULES:
            patterns, kind = _AUTO_RULES[decl.key]
            entries.append(_auto_entry(decl, patterns, kind, data))
            if decl.key == "sealed_cap":
                sealed_cap = decl
        else:
            entries.append(DiffEntry(
                decl.key, "MANUAL", decl.value, "", "",
                "자동 매핑 규칙 없음 — 수동 확인 필요",
                decl.line_no, decl.raw))
    if sealed_cap is not None:
        bound = Declaration(_BOUND_KEY, sealed_cap.value, sealed_cap.raw,
                            sealed_cap.line_no, False)
        entries.append(_auto_entry(bound, _BOUND_PATHS, "int_upper_bound", data))
    return tuple(sorted(entries,
                        key=lambda e: (_STATUS_ORDER[e.status], e.md_line, e.key)))


# ── 4단계: 리포트 ────────────────────────────────────────────────────────────
def render_table(entries: tuple[DiffEntry, ...], prereg: str, result: str) -> str:
    """한국어 대조표(불일치 우선 정렬)를 문자열로 만든다."""
    lines = [
        "[prereg-diff] 봉인↔결과 자동 대조 (보고 전용 — 판정 주체는 사람)",
        f"  봉인: {prereg}",
        f"  결과: {result}",
        "",
        f"{'상태':<9}| {'항목':<28}| {'선언값':<22}| 관측값 (json 경로)",
        "-" * 100,
    ]
    for e in entries:
        obs = f"{e.observed} ({e.json_path})" if e.json_path else f"— {e.note}"
        lines.append(f"{e.status:<9}| {e.key:<28}| {e.declared:<22}| {obs}")
    counts = summarize(entries)
    lines += [
        "-" * 100,
        (f"요약: MATCH {counts['MATCH']} / MISMATCH {counts['MISMATCH']}"
         f" / MANUAL(수동 확인 필요) {counts['MANUAL']}"),
    ]
    if counts["MISMATCH"]:
        lines.append("경고: 불일치가 있다 — 봉인 위반 여부를 사람이 판정할 것"
                     "(본 도구는 보고 전용).")
    return "\n".join(lines)


def summarize(entries: tuple[DiffEntry, ...]) -> dict[str, int]:
    """상태별 건수 집계."""
    return {s: sum(1 for e in entries if e.status == s)
            for s in ("MATCH", "MISMATCH", "MANUAL")}


def run_diff(prereg_path: Path | str, result_path: Path | str) -> dict[str, Any]:
    """봉인 md 와 결과 json 을 읽어 대조 리포트 dict 를 만든다(파일 쓰기 없음)."""
    prereg_path = Path(prereg_path)
    result_path = Path(result_path)
    md_text = prereg_path.read_text(encoding="utf-8")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    entries = compare(extract_declarations(md_text), data)
    return {
        "kind": "prereg_diff_report",
        "generated": datetime.now(timezone.utc).isoformat(),
        "prereg": str(prereg_path),
        "result": str(result_path),
        "counts": summarize(entries),
        "entries": [asdict(e) for e in entries],
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    """보고 전용 CLI. 불일치가 있어도 종료 코드 0(차단은 measure_gate 소관)."""
    parser = argparse.ArgumentParser(
        prog="prereg_diff",
        description="봉인 사전등록 md ↔ 결과 json 자동 대조(보고 전용)")
    parser.add_argument("--prereg", required=True, help="봉인 사전등록 md 경로")
    parser.add_argument("--result", required=True, help="판정 결과 json 경로")
    parser.add_argument("--json-out", default=None,
                        help="리포트 json 저장 경로(선택)")
    args = parser.parse_args(argv)
    try:
        report = run_diff(args.prereg, args.result)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[prereg-diff] 입력 읽기 실패: {exc}", file=sys.stderr)
        return 2
    entries = tuple(DiffEntry(**e) for e in report["entries"])
    print(render_table(entries, report["prereg"], report["result"]))
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"[prereg-diff] 리포트 저장: {out}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 파이프/구형 스트림이면 무시
        pass
    sys.exit(main())
