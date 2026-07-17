"""판정 문서용 '시행 병기 블록' 생성기 (백로그 A6 — ledger 소비 전용).

원장 규약 §3.4: FDR·다중비교 보정의 분모는 "해당 검정족의 시행 수"이되,
전역 누계와 sqrt(2·ln N)을 판정 문서에 병기한다. 이 모듈은 그 병기 블록을
자동 생성해 분모·누계 누락을 구조적으로 제거한다.

**채택 조건(A6): 자체 기입 경로 금지.** 이 모듈은 ledger의 읽기 함수
(aggregate/read_all)만 소비하며 원장에 어떤 행도 쓰지 않는다 — 기입은
alpha_lab.discipline.ledger.append_trial 단일 경로뿐이다.

type-d 시행 신설 등 규약 확장은 본 모듈이 아니라 원장 §5 규약 개정으로만
(백로그 A6 조건).
"""

from __future__ import annotations

from alpha_lab.discipline import ledger as _ledger

DEFAULT_LEGACY_NOTE = "구 프로그램 누계 1,100+ (별도 카운터 — 원장 §3.2)"


def _fmt_sqrt(value: float) -> str:
    """sqrt(2·ln N) 표기 — 소수 3자리 고정."""
    return f"{value:.3f}"


def _series_breakdown_rows(by_series: dict) -> list[str]:
    """계열별 누계 표의 행 목록(계열명 정렬)."""
    rows = []
    for series, stats in by_series.items():
        rows.append(
            f"| {series} | {stats['n']} | {_fmt_sqrt(stats['sqrt_2_ln_n'])} |"
        )
    return rows


def _validate_inputs(family_label: str, family_denominator: int) -> None:
    """검정족 라벨·FDR 분모 입력 검증(사전등록 봉인값이므로 엄격)."""
    if not isinstance(family_label, str) or not family_label.strip():
        raise ValueError("family_label은 비어 있지 않은 문자열이어야 합니다")
    if isinstance(family_denominator, bool) or not isinstance(family_denominator, int):
        raise ValueError(f"family_denominator는 int여야 합니다: {family_denominator!r}")
    if family_denominator < 1:
        raise ValueError(f"family_denominator는 1 이상이어야 합니다: {family_denominator}")


def _series_row(agg: dict, series: str) -> str:
    """계열 누계 행 — 원장에 없는 계열은 ValueError(오타 오도 방지)."""
    stats = agg["by_series"].get(series)
    if stats is None:
        raise ValueError(
            f"원장에 없는 계열: {series!r} (존재: {sorted(agg['by_series'])})"
        )
    return (
        f"| 계열({series}) 누계 | {stats['n']} "
        f"(√(2·ln n) = {_fmt_sqrt(stats['sqrt_2_ln_n'])}) |"
    )


def build_trials_block(
    *,
    family_label: str,
    family_denominator: int,
    series: str | None = None,
    path=None,
    legacy_note: str = DEFAULT_LEGACY_NOTE,
    generated_ts: str | None = None,
    include_breakdown: bool = True,
) -> str:
    """판정 문서에 붙일 '시행 병기 블록' md를 생성한다.

    family_label: 검정족 이름(예: "D1 절-단위 A/B(자격 절)").
    family_denominator: 그 족의 FDR 분모(시행 수) — 사전등록 봉인값.
    series: 병기할 계열명(원장 series 필드값). 미기재 시 전역만 병기.
    path: 원장 경로(기본 = 프로그램 실물 원장). generated_ts: 호출자 주입
    (내부 datetime.now() 금지 관례).
    """
    _validate_inputs(family_label, family_denominator)
    agg = _ledger.aggregate(path)
    lines = [
        "### 시행 병기 블록 (n_trials — A6 자동 생성, ledger 소비 전용)",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 검정족 | {family_label.strip()} |",
        f"| 족 분모(FDR) | {family_denominator} |",
    ]
    if series is not None:
        lines.append(_series_row(agg, series))
    lines += [
        f"| 전역 누계(본 프로그램) | {agg['total']} "
        f"(√(2·ln N) = {_fmt_sqrt(agg['sqrt_2_ln_total'])}) |",
        f"| known 창 접촉 시행 | {agg['known_window_contacts']} |",
        f"| 구 프로그램 누계 | {legacy_note} |",
    ]
    if generated_ts:
        lines.append(f"| 생성 시각(주입) | {generated_ts} |")
    return "\n".join(lines + _tail_lines(agg, include_breakdown))


def _tail_lines(agg: dict, include_breakdown: bool) -> list[str]:
    """계열별 분해 표(선택)와 소비-전용 각주."""
    lines: list[str] = []
    if include_breakdown and agg["by_series"]:
        lines += [
            "",
            "계열별 누계(원장 전수):",
            "",
            "| 계열 | n | √(2·ln n) |",
            "|---|---|---|",
            *_series_breakdown_rows(agg["by_series"]),
        ]
    lines += [
        "",
        "- 원장(단일 기입 경로): `n_trials_ledger.jsonl` — 본 블록은 읽기 전용 집계이며 원장에 기입하지 않는다.",
        "",
    ]
    return lines
