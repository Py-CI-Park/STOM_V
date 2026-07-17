"""창-지위 상수와 측정 창 가드 (백로그 A1 — W1b 가드 라이브러리).

정본: `docs/research/condition_research/plans/2026-07-10_window_status_ledger.md`
본 모듈의 상수·인용문이 원장 문서와 불일치하면 **원장이 정본**이며,
본 모듈을 원장에 맞춰 고치는 새 커밋으로만 해소한다(원장 §5).

쉬운 설명: 우리 데이터는 새 문제가 안 나오는 기출문제집이다. 이 모듈은
"채점 전용으로 봉인된 페이지(known 창)"를 측정에 쓰려는 시도를 코드
수준에서 거부하는 자물쇠다 — V-1(W3 경계 오염)이 정확히 '수동 준수'
공백에서 발생했으므로, 규율을 양심에서 코드로 옮긴다.

계열 규칙(원장 §1·§2): 2024는 조건부(CONDITIONAL) 창이지만
청산 레버(P5·D5)·챔피언 선정·앙상블(v4) 계열에는 known이다.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re

# ---------------------------------------------------------------------------
# 창-지위 상수 (원장 §1 — 2026-07-10 기준)
# ---------------------------------------------------------------------------

DISCOVERY_START = dt.date(2022, 3, 23)
DISCOVERY_END = dt.date(2023, 12, 31)
CONDITIONAL_2024_START = dt.date(2024, 1, 1)
CONDITIONAL_2024_END = dt.date(2024, 12, 31)
KNOWN_START = dt.date(2025, 1, 1)
KNOWN_END = dt.date(2026, 2, 27)

LEDGER_DOC_PATH = (
    "docs/research/condition_research/plans/2026-07-10_window_status_ledger.md"
)

# 원장 §1 사용 규칙 인용(마크다운 강조 기호만 제거, 문구는 원문 그대로)
LEDGER_QUOTE_DISCOVERY = (
    "새 가설의 발견·프로파일링·지도 구축에 사용 가능. 사용 시 이력표에 기록"
)
LEDGER_QUOTE_CONDITIONAL = (
    "청산 레버·챔피언 선정 계열 가설에는 known. 그 외 신규 가설은 개봉 이력 "
    "대조 후 검증창으로 1회 사용 가능(사전등록 필수, 사용 즉시 해당 가설 "
    "계열에 known 강등)"
)
LEDGER_QUOTE_KNOWN = (
    "선택·튜닝 금지. veto 전용(최종 후보의 역방향 확인·감사 기록). "
    "blind 주장 절대 금지. S-트랙 적재 시 별도 파티션 + 경고 플래그"
)
LEDGER_QUOTE_NONE = (
    "데이터 없음, 수집하지 않음(사용자 결정 v2) — 해당 없음. "
    "미래 검증 = 감독형 소액 실전 운용(W1c)"
)

# 2024가 known인 계열 판별 토큰(원장 §1 조건부 행·§2 이력표).
# series_kind에는 원장 §2의 '가설 계열' 명칭을 쓰는 것이 원칙이다
# (방향 코드 D1 등이 아니라 예: "챔피언 선정·앙상블(v4 계열)").
SERIES_2024_KNOWN_TOKENS: tuple[str, ...] = (
    "청산",
    "출구",
    "매도",
    "p5",
    "d5",
    "챔피언",
    "선정",
    "앙상블",
    "v4",
    "rr8",
)

# 날짜 토큰 패턴: ISO 전체(2025-04-07) / 압축 8자리(20250407) / 연-월(2025-04)
_RE_FULL = re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})(?!\d)")
_RE_COMPACT = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
_RE_YEARMONTH = re.compile(r"(?<!\d)(20\d{2})-(\d{2})(?!-?\d)")


class WindowViolation(Exception):
    """창-지위 원장 위반 — 원장 문구를 인용한 측정 창 가드 예외."""


def parse_date(value) -> dt.date:
    """date/datetime/문자열(YYYY-MM-DD 또는 YYYYMMDD)을 date로 정규화한다."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", text):
            return dt.date.fromisoformat(text)
        if re.fullmatch(r"20\d{6}", text):
            return dt.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    raise ValueError(f"날짜 해석 불가(YYYY-MM-DD/YYYYMMDD/date만 허용): {value!r}")


def _safe_date(year: int, month: int, day: int) -> dt.date | None:
    """유효하지 않은 연·월·일이면 None(날짜 아님 — 토큰 제외)."""
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def extract_date_tokens(text: str) -> list[dict]:
    """문자열에서 날짜 토큰을 추출한다.

    반환: [{"token", "start", "end", "kind"}] — 연-월 토큰은 해당 월의
    1일~말일 범위로 확장한다. 유효하지 않은 날짜(예: 2025-13-99)는 제외.
    """
    tokens: list[dict] = []
    for match in _RE_FULL.finditer(text):
        day = _safe_date(int(match[1]), int(match[2]), int(match[3]))
        if day is not None:
            tokens.append(
                {"token": match[0], "start": day, "end": day, "kind": "full"}
            )
    for match in _RE_COMPACT.finditer(text):
        day = _safe_date(int(match[1]), int(match[2]), int(match[3]))
        if day is not None:
            tokens.append(
                {"token": match[0], "start": day, "end": day, "kind": "compact"}
            )
    for match in _RE_YEARMONTH.finditer(text):
        year, month = int(match[1]), int(match[2])
        if 1 <= month <= 12:
            last = calendar.monthrange(year, month)[1]
            tokens.append(
                {
                    "token": match[0],
                    "start": dt.date(year, month, 1),
                    "end": dt.date(year, month, last),
                    "kind": "yearmonth",
                }
            )
    return tokens


def window_zones(start: dt.date, end: dt.date) -> set[str]:
    """[start, end] 구간이 겹치는 창-지위 집합을 반환한다(원장 §1)."""
    if start > end:
        raise ValueError(f"start({start}) > end({end}) — 구간이 뒤집혔습니다")
    zones: set[str] = set()
    if start < DISCOVERY_START:
        zones.add("PRE_DATA")
    if start <= DISCOVERY_END and end >= DISCOVERY_START:
        zones.add("DISCOVERY")
    if start <= CONDITIONAL_2024_END and end >= CONDITIONAL_2024_START:
        zones.add("CONDITIONAL_2024")
    if start <= KNOWN_END and end >= KNOWN_START:
        zones.add("KNOWN")
    if end > KNOWN_END:
        zones.add("NONE")
    return zones


def series_2024_is_known(series_kind: str) -> bool:
    """이 계열에 2024 창이 known인가(청산 레버·챔피언 선정 계열 등).

    series_kind가 비어 있으면 판별 불가이므로 ValueError(fail-closed).
    """
    if not isinstance(series_kind, str) or not series_kind.strip():
        raise ValueError("series_kind는 비어 있지 않은 문자열이어야 합니다(fail-closed)")
    lowered = series_kind.lower()
    return any(token in lowered for token in SERIES_2024_KNOWN_TOKENS)


def _violation(zone_label: str, span: str, quote: str) -> WindowViolation:
    """원장 문구를 인용한 위반 예외를 조립한다."""
    return WindowViolation(
        f"창-지위 위반: 요청 측정창 {span} 이(가) {zone_label} 에 접촉합니다. "
        f'원장 §1 사용 규칙: "{quote}" (정본: {LEDGER_DOC_PATH}, '
        f"위반 처리: 원장 §4 — 미기록 측정 산출물은 무효)"
    )


def assert_measurement_window(start, end, series_kind, *, conditional_2024_prereg=None):
    """측정 창 [start, end]가 계열 series_kind에 허용되는지 검사한다.

    통과 시 창 지위 문자열("DISCOVERY" 또는 "CONDITIONAL_2024")을 반환하고,
    위반 시 원장 문구를 인용한 WindowViolation을 던진다.

    conditional_2024_prereg: 2024 조건부 창을 1회 검증으로 쓰는 경우에만,
    근거 사전등록(봉인 문서 경로·커밋 등) 문자열을 명시한다. 미지정이면
    2024 접촉은 거부된다(사전등록 필수 — fail-closed).
    """
    s, e = parse_date(start), parse_date(end)
    span = f"{s.isoformat()}~{e.isoformat()}"
    zones = window_zones(s, e)
    if "KNOWN" in zones:
        raise _violation(
            f"known/audit 창({KNOWN_START}~{KNOWN_END})", span, LEDGER_QUOTE_KNOWN
        )
    if "NONE" in zones:
        raise _violation(f"부재 창({KNOWN_END} 이후)", span, LEDGER_QUOTE_NONE)
    if "PRE_DATA" in zones:
        raise _violation(
            f"데이터 시작({DISCOVERY_START}) 이전", span, LEDGER_QUOTE_DISCOVERY
        )
    if "CONDITIONAL_2024" in zones:
        if series_2024_is_known(series_kind):
            raise _violation(
                f"조건부 창(2024) — 계열 '{series_kind}'에는 known",
                span,
                LEDGER_QUOTE_CONDITIONAL,
            )
        if not conditional_2024_prereg:
            raise _violation(
                "조건부 창(2024) — 사전등록 근거 미제시",
                span,
                LEDGER_QUOTE_CONDITIONAL,
            )
        return "CONDITIONAL_2024"
    series_2024_is_known(series_kind)  # 계열 문자열 유효성만 검사(fail-closed)
    return "DISCOVERY"
