"""ledger-lint — known 창 날짜의 측정 문맥 접촉을 문서에서 검출 (백로그 A4).

**보고 전용 고정.** 차단(fail) 모드는 구현하지 않는다 — A4 채택 조건이
"보고 전용 고정(차단 모드 금지)"이며, 3계층 방어선에서 이 도구는 '커밋 전
정적 보고' 층만 담당한다(기동 전 게이트 A7·런타임 가드 B1은 별도 트랙).

검출 규칙:
- known 창 날짜 = 실제 known/audit 구간(2025-01-01~2026-02-27)에 속하는
  날짜 토큰(ISO/압축 8자리/연-월). 2026-03 이후는 데이터 부재 구간이므로
  문서 작성일(예: 2026-07-12)은 구조적으로 오탐되지 않는다.
- 2024 날짜는 청산 레버·챔피언 계열 문맥 토큰이 근접할 때만 후보(원장 §1
  조건부 행 — 해당 계열에는 known).
- 측정 문맥 키워드(측정/적재/부트스트랩/백테/스캔/표본 등)가 같은 행 또는
  전후 PROXIMITY_LINES 행 안에 있어야 플래그한다.
- 같은 행이 금지/veto/원장 등 정책 서술 표지를 포함하면 category를
  "policy_context"로 분류한다(오탐 소견용 — 억제하지 않고 보고).

합격 기준(백로그 A4): 창-지위 원장 §6의 위반 V-1(W3 프로파일링이 known
2025 표본일을 경계 산정에 사용)을 실제 코퍼스에서 재검출할 것.
"""

from __future__ import annotations

from pathlib import Path

from alpha_lab.discipline import windows

# 측정 문맥 키워드(백로그 A4 "측정/적재/부트스트랩/백테/스캔/표본 등")
MEASUREMENT_KEYWORDS: tuple[str, ...] = (
    "측정",
    "적재",
    "부트스트랩",
    "백테",
    "스캔",
    "표본",
    "산정",
    "경계",
    "검정",
    "학습",
    "튜닝",
    "프로파일링",
    "라벨",
    "채굴",
    "상관",
    "분위",
)

# 정책 서술 표지(같은 행에 있으면 policy_context로 분류 — 보고는 유지)
POLICY_MARKERS: tuple[str, ...] = (
    "금지",
    "veto",
    "원장",
    "지위",
    "딱지",
    "규율",
    "위반",
    "known",
    "audit",
    "개봉",
    "봉인",
)

PROXIMITY_LINES = 3
SNIPPET_MAX = 160


def _candidate_tokens(line: str) -> list[tuple[str, str]]:
    """행에서 (토큰, 창 라벨) 후보를 추출한다 — KNOWN/CONDITIONAL_2024만."""
    candidates: list[tuple[str, str]] = []
    for token in windows.extract_date_tokens(line):
        zones = windows.window_zones(token["start"], token["end"])
        if "KNOWN" in zones:
            candidates.append((token["token"], "KNOWN"))
        elif "CONDITIONAL_2024" in zones:
            candidates.append((token["token"], "CONDITIONAL_2024"))
    return candidates


def _context_block(lines: list[str], index: int) -> str:
    """index 행 기준 전후 PROXIMITY_LINES 행을 합친 문맥 문자열."""
    lo = max(0, index - PROXIMITY_LINES)
    hi = min(len(lines), index + PROXIMITY_LINES + 1)
    return "\n".join(lines[lo:hi])


def _exit_series_context(context: str) -> bool:
    """문맥에 청산 레버·챔피언 계열 토큰이 있는가(2024 후보 자격)."""
    lowered = context.lower()
    return any(token in lowered for token in windows.SERIES_2024_KNOWN_TOKENS)


def _classify_line(line: str) -> str:
    """행 분류 — 정책 서술 표지 포함 시 policy_context(오탐 가능 소견)."""
    lowered = line.lower()
    if any(marker in lowered for marker in POLICY_MARKERS):
        return "policy_context"
    return "measurement_context"


def scan_text(text: str, source: str = "<memory>") -> list[dict]:
    """문서 본문을 스캔해 플래그 행 목록을 반환한다(행 단위 1건)."""
    lines = text.splitlines()
    findings: list[dict] = []
    for index, line in enumerate(lines):
        candidates = _candidate_tokens(line)
        if not candidates:
            continue
        context = _context_block(lines, index)
        keywords = [kw for kw in MEASUREMENT_KEYWORDS if kw in context]
        if not keywords:
            continue
        known_tokens = [tok for tok, zone in candidates if zone == "KNOWN"]
        cond_tokens = [tok for tok, zone in candidates if zone == "CONDITIONAL_2024"]
        flagged: list[str] = list(known_tokens)
        zone_label = "KNOWN"
        if cond_tokens and _exit_series_context(context):
            flagged += cond_tokens
            if not known_tokens:
                zone_label = "CONDITIONAL_2024(청산·챔피언 문맥)"
            else:
                zone_label = "KNOWN+CONDITIONAL_2024"
        if not flagged:
            continue
        findings.append(
            {
                "file": source,
                "line": index + 1,
                "zone": zone_label,
                "date_tokens": flagged,
                "keywords": keywords,
                "category": _classify_line(line),
                "snippet": line.strip()[:SNIPPET_MAX],
            }
        )
    return findings


def scan_file(path) -> list[dict]:
    """md 파일 1개를 스캔한다(utf-8, 인코딩 오류는 대체 문자로 관용)."""
    target = Path(path)
    text = target.read_text(encoding="utf-8", errors="replace")
    return scan_text(text, source=str(target))


def scan_paths(paths, pattern: str = "*.md") -> dict:
    """디렉토리/파일 목록을 재귀 스캔해 종합 결과를 반환한다.

    반환: {"files_scanned", "findings", "summary"} — summary에는 분류별
    계수와 파일별 계수가 들어간다. 보고 전용 — 어떤 예외적 '차단' 판정도
    내리지 않는다.
    """
    files: list[Path] = []
    for raw in paths:
        entry = Path(raw)
        if entry.is_dir():
            files.extend(sorted(entry.rglob(pattern)))
        elif entry.is_file():
            files.append(entry)
    findings: list[dict] = []
    for file_path in files:
        findings.extend(scan_file(file_path))
    measurement = [f for f in findings if f["category"] == "measurement_context"]
    policy = [f for f in findings if f["category"] == "policy_context"]
    by_file: dict[str, int] = {}
    for finding in findings:
        by_file[finding["file"]] = by_file.get(finding["file"], 0) + 1
    return {
        "files_scanned": len(files),
        "findings": findings,
        "summary": {
            "flagged_lines": len(findings),
            "measurement_context": len(measurement),
            "policy_context": len(policy),
            "by_file": dict(sorted(by_file.items())),
        },
    }


def render_report(result: dict) -> str:
    """스캔 결과를 한국어 보고 텍스트로 렌더링한다(보고 전용 명시)."""
    summary = result["summary"]
    lines = [
        "# ledger-lint 보고 (A4 — 보고 전용, 차단 모드 없음)",
        "",
        f"- 스캔 파일: {result['files_scanned']}개",
        f"- 플래그 행: {summary['flagged_lines']}건 "
        f"(측정 문맥 {summary['measurement_context']} / "
        f"정책 서술 문맥·오탐 가능 {summary['policy_context']})",
        "",
    ]
    if not result["findings"]:
        lines.append("플래그 없음 — known 창 날짜의 측정 문맥 접촉이 검출되지 않았다.")
        return "\n".join(lines)
    lines += [
        "| 파일 | 행 | 창 | 날짜 토큰 | 근접 키워드 | 분류 |",
        "|---|---|---|---|---|---|",
    ]
    for finding in result["findings"]:
        name = Path(finding["file"]).name
        lines.append(
            f"| {name} | {finding['line']} | {finding['zone']} | "
            f"{', '.join(finding['date_tokens'][:6])} | "
            f"{', '.join(finding['keywords'][:6])} | {finding['category']} |"
        )
    lines += [
        "",
        "분류 안내: measurement_context = 측정 서술 근접(우선 검토 대상), "
        "policy_context = 같은 행에 금지/veto/원장 등 정책 표지 동반(오탐 "
        "가능성 높음 — 그래도 보고는 유지한다).",
        "",
    ]
    return "\n".join(lines)
