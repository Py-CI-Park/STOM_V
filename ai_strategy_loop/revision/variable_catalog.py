"""QSP7 변수 카탈로그 원장(P2-9) — 후보 생성에 쓸 수 있는 변수의 유일한 관문.

원칙(마스터 플랜 §10):
  - 등록되지 않은 변수는 후보 생성에 쓰지 않는다.
  - 모든 변수는 STOM 조건식으로 표현 가능해야 한다(``stom_template``) —
    "연구에서 발견 = 조건식으로 즉시 표현"의 보장. 표현 불가는 analysis_only.
  - 누출 검사: 매수시점 이전 정보만. R_*/매도 후 값 파생은 등록 자체를 금지.
  - 루트: "runtime"(엔진 기본 변수) / "A"(B_* 사후 조합) / "B"(DB 창 재구성).
    루트 C(엔진 캡처 확장)는 A·B 에서 FDR 유용성이 증명된 뒤 별도 결정.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final


_FORBIDDEN_SOURCES: Final = ("R_", "S_", "매도후", "미래", "최종")
_MINUTE_ONLY_TEMPLATE_TOKENS: Final = ("분봉시가", "분봉고가", "분봉저가")


@dataclass(frozen=True, slots=True)
class CatalogVariable:
    name: str
    route: str                     # "runtime" | "A" | "B"
    lanes: tuple[str, ...]         # ("tick",) | ("min",) | ("tick", "min")
    formula: str                   # 사람이 읽는 정의(근거 열/함수)
    stom_template: str             # 조건식 상단 인라인 정의(빈 문자열 = 런타임 직접 변수)
    unit: str
    leakage_safe: bool
    analysis_only: bool = False    # True 면 인사이트 전용 — 후보 생성 금지
    note: str = ""


def _guard(expr: str, denominator: str) -> str:
    """0나눗셈 가드가 붙은 인라인 정의(기준선 인라인 5종의 기존 패턴)."""
    return f"{expr} if {denominator} != 0 else 0"


CATALOG: Final[tuple[CatalogVariable, ...]] = (
    # ---- 루트 A: 기존 B_* 31개 조합(사후 파생) — 기준선 인라인 5종 승계 ----
    CatalogVariable(
        "전일종가추정", "A", ("tick", "min"),
        "현재가 / (1 + 등락율/100)",
        _guard("전일종가추정 = 현재가 / (1 + (등락율 / 100))", "(1 + (등락율 / 100))"),
        "원", True, note="기준선 Min_B_Study_251227 인라인 승계",
    ),
    CatalogVariable(
        "시가갭수익률", "A", ("min",),
        "(분봉시가 - 전일종가추정) / 전일종가추정 * 100",
        _guard("시가갭수익률 = ((분봉시가 - 전일종가추정) / 전일종가추정) * 100", "전일종가추정"),
        "%", True, note="전일종가추정 선행 정의 필요(연쇄) · min 전용",
    ),
    CatalogVariable(
        "시가대비등락율", "A", ("min",),
        "(현재가 - 분봉시가) / 분봉시가 * 100",
        _guard("시가대비등락율 = ((현재가 - 분봉시가) / 분봉시가) * 100", "분봉시가"),
        "%", True, note="기준선 인라인 승계 · min 전용",
    ),
    CatalogVariable(
        "분당순매수금액", "A", ("min",),
        "(분당매수수량 - 분당매도수량) * 현재가 / 1_000_000",
        "분당순매수금액 = (분당매수수량 - 분당매도수량) * 현재가 / 1_000_000",
        "백만원", True, note="기준선 인라인 승계 · min 전용",
    ),
    CatalogVariable(
        "초당순매수수량", "A", ("tick",),
        "초당매수수량 - 초당매도수량",
        "초당순매수수량 = 초당매수수량 - 초당매도수량",
        "주", True, note="tick 전용",
    ),
    CatalogVariable(
        "당일거래대금비율", "A", ("tick", "min"),
        "당일거래대금 / (시가총액 * 회전율 / 100) * 100",
        _guard(
            "당일거래대금비율 = 당일거래대금 / (시가총액 * 회전율 / 100) * 100",
            "(시가총액 * 회전율 / 100)",
        ),
        "%", True, note="기준선 인라인 승계",
    ),
    CatalogVariable(
        "매수잔량비율", "A", ("tick", "min"),
        "매수총잔량 / (매수총잔량 + 매도총잔량) * 100",
        _guard(
            "매수잔량비율 = 매수총잔량 / (매수총잔량 + 매도총잔량) * 100",
            "(매수총잔량 + 매도총잔량)",
        ),
        "%", True,
    ),
    CatalogVariable(
        "고저위치비율", "A", ("tick", "min"),
        "(현재가 - 저가) / (고가 - 저가) * 100",
        _guard("고저위치비율 = (현재가 - 저가) / (고가 - 저가) * 100", "(고가 - 저가)"),
        "%", True, note="당일 고저 범위 내 현재가 위치",
    ),
    CatalogVariable(
        "체결강도괴리", "A", ("tick", "min"),
        "체결강도 - 체결강도평균(평균창)",
        "체결강도괴리 = 체결강도 - 체결강도평균(30)",
        "pt", True, note="창 30은 공식 avg 동결값(bt_avg_time=30) 승계",
    ),
    CatalogVariable(
        "시총회전강도", "A", ("tick", "min"),
        "회전율 * 등락율",
        "시총회전강도 = 회전율 * 등락율",
        "pt", True, note="회전과 방향의 곱 — 탐색용",
    ),
    # ---- 루트 B: DB 창 재구성(엔진 파생 18항 미러 계열) — 조건식 함수로 표현 가능 ----
    CatalogVariable(
        "이평60위치", "B", ("tick", "min"),
        "현재가 / 이동평균(60) * 100",
        _guard("이평60위치 = 현재가 / 이동평균(60) * 100", "이동평균(60)"),
        "%", True, note="derived-18 이동평균60 대응 · min 은 60분",
    ),
    CatalogVariable(
        "이평300위치", "B", ("tick",),
        "현재가 / 이동평균(300) * 100",
        _guard("이평300위치 = 현재가 / 이동평균(300) * 100", "이동평균(300)"),
        "%", True, note="tick 전용(min 세션 383분 — 300분 창은 워밍업 과다)",
    ),
    CatalogVariable(
        "고점대비낙폭", "B", ("tick", "min"),
        "(최고현재가(창) - 현재가) / 최고현재가(창) * 100",
        _guard(
            "고점대비낙폭 = (최고현재가(60) - 현재가) / 최고현재가(60) * 100",
            "최고현재가(60)",
        ),
        "%", True, note="derived-18 최고현재가 대응",
    ),
    CatalogVariable(
        "저점대비반등", "B", ("tick", "min"),
        "(현재가 - 최저현재가(창)) / 최저현재가(창) * 100",
        _guard(
            "저점대비반등 = (현재가 - 최저현재가(60)) / 최저현재가(60) * 100",
            "최저현재가(60)",
        ),
        "%", True, note="derived-18 최저현재가 대응",
    ),
    CatalogVariable(
        "체결강도밴드폭", "B", ("tick", "min"),
        "최고체결강도(창) - 최저체결강도(창)",
        "체결강도밴드폭 = 최고체결강도(60) - 최저체결강도(60)",
        "pt", True, note="derived-18 최고/최저체결강도 대응",
    ),
)


def catalog_for_lane(lane: str) -> tuple[CatalogVariable, ...]:
    return tuple(item for item in CATALOG if lane in item.lanes)


def candidate_pool(lane: str) -> tuple[CatalogVariable, ...]:
    """후보 생성에 허용되는 변수만(analysis_only 제외)."""
    return tuple(item for item in catalog_for_lane(lane) if not item.analysis_only)


def template_block(names: tuple[str, ...], lane: str) -> str:
    """선택 변수의 인라인 정의 블록 — 연쇄 의존(전일종가추정)까지 순서 보장."""
    by_name = {item.name: item for item in catalog_for_lane(lane)}
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        item = by_name.get(name)
        if item is None or name in seen or not item.stom_template:
            return
        for dependency in by_name:
            if dependency != name and dependency in item.stom_template:
                _add(dependency)
        seen.add(name)
        ordered.append(item.stom_template)

    for name in names:
        _add(name)
    return "\n".join(ordered)


def validate_catalog() -> tuple[str, ...]:
    """등록 시점 자가 검증 — 누출 금지·레인 값·템플릿 이름 일치."""
    problems: list[str] = []
    for item in CATALOG:
        if any(token in item.formula for token in _FORBIDDEN_SOURCES):
            problems.append(f"{item.name}: 누출 의심 원천")
        if not item.leakage_safe:
            problems.append(f"{item.name}: leakage_safe=False 는 등록 불가")
        if not set(item.lanes) <= {"tick", "min"}:
            problems.append(f"{item.name}: 잘못된 lane {item.lanes}")
        if "tick" in item.lanes:
            expression = f"{item.formula}\n{item.stom_template}"
            minute_tokens = [token for token in _MINUTE_ONLY_TEMPLATE_TOKENS if token in expression]
            if minute_tokens:
                problems.append(f"{item.name}: tick lane minute-only token {minute_tokens[0]}")
        if item.stom_template and not item.stom_template.startswith(item.name):
            problems.append(f"{item.name}: 템플릿이 자기 이름으로 시작하지 않음")
    return tuple(problems)


def catalog_payload(lane: str = "") -> dict[str, object]:
    rows = catalog_for_lane(lane) if lane in ("tick", "min") else CATALOG
    return {
        "available": True,
        "authority": "diagnostic",
        "lane": lane or "all",
        "count": len(rows),
        "variables": [asdict(item) for item in rows],
        "problems": list(validate_catalog()),
    }
