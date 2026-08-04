"""패턴 카드 추출기(G-0b) — 사람이 쓴 조건식에서 **골격만** 가져온다.

왜 필요한가:
  현재 생성기는 `변수 >= 상수` 한 줄만 만든다. 사용자가 실제로 쓰는 문법은 8종이고,
  골짜기·다중 밴드 손실은 단측으로는 **표현 자체가 불가능**하다. 사람이 이미 쓰고 있는
  문법을 사전으로 만들어 두면, 생성기는 그 골격의 `?` 자리만 데이터로 채우면 된다.
  결과적으로 "읽을 수 있는 조건식"이 구조적으로 보장된다.

계약:
  - **임계값은 저장하지 않는다.** 숫자 상수는 전부 `?` 로 마스킹한다. 구간연산 창 크기도
    파라미터이므로 마스킹한다. 사람 전략의 숫자를 복제하면 그 값이 왜 좋은지 설명할 수
    없고, 그건 연구가 아니라 표절이다.
  - 카드는 **문법 사전(reference 권위)** 일 뿐이다. 값은 데이터가 채운다(region_proposer).
  - 어떤 전략에서 몇 번 나왔는지는 남긴다 — 어디서 배운 문법인지 추적 가능해야 한다.
  - 파싱 실패는 예외로 터뜨리지 않고 skipped 로 보고한다(fail-closed).
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from typing import Final, Mapping


MASK: Final = "?"
# 구간 문법이 아닌 상태 플래그 — 카드로 만들지 않는다.
_FLAG_NAMES: Final = frozenset({"관심종목", "라운드피겨위5호가이내", "매수", "매도"})
_POSITION_NAMES: Final = frozenset({"고가", "저가", "시가"})
_PREV_SUFFIX: Final = "N"


@dataclass(frozen=True, slots=True)
class PatternCard:
    card_id: str
    kind: str
    skeleton: str              # 상수가 전부 `?` 로 마스킹된 골격
    variables: tuple[str, ...]
    slots: int                 # 채워야 할 `?` 개수
    occurrences: int
    sources: tuple[str, ...]


class _Mask(ast.NodeTransformer):
    """숫자 상수를 전부 `?` 로 바꾼다 — 창 크기(구간틱수)도 예외가 아니다."""

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool):
            return node
        if isinstance(node.value, (int, float)):
            return ast.Name(id=MASK, ctx=ast.Load())
        return node


def _variable_names(node: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id != MASK:
            if child.id not in names:
                names.append(child.id)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            if child.func.id not in names:
                names.append(child.func.id)
    return tuple(names)


def _base_name(node: ast.AST) -> str | None:
    """변수 이름(구간연산 호출 포함). 마스킹된 상수는 변수가 아니다."""
    if isinstance(node, ast.Name):
        return None if node.id == MASK else node.id
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _is_previous_of(node: ast.AST, other: ast.AST) -> bool:
    """`초당거래대금N(1)` 이 `초당거래대금` 의 이전값 호출인가."""
    name = _base_name(node)
    other_name = _base_name(other)
    if not name or not other_name or not isinstance(node, ast.Call):
        return False
    return name == f"{other_name}{_PREV_SUFFIX}"


def _mult_base(node: ast.AST) -> ast.AST | None:
    """`B * ?` 또는 `? * B` 에서 B 를 돌려준다."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Mult):
        return None
    for side, other in ((node.left, node.right), (node.right, node.left)):
        if isinstance(other, ast.Name) and other.id == MASK and _base_name(side):
            return side
    return None


def _classify_compare(node: ast.Compare) -> str | None:
    """마스킹된 Compare 노드 하나의 문법 종류."""
    if len(node.ops) == 2:
        middle = node.comparators[0]
        name = _base_name(middle)
        if name is None:
            return None
        return "band_ctx" if name == "시분초" else "range_keep"
    if len(node.ops) != 1:
        return None
    left, right = node.left, node.comparators[0]
    if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
        return None                                   # 상태 플래그 비교
    if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Div):
        return "ratio_cmp"
    base = _mult_base(right)
    if base is not None:
        return "prev_mult" if _is_previous_of(base, left) else "mult_cmp"
    if _contains_position_shape(right):
        return "position"
    if _base_name(left) and isinstance(right, ast.Name) and right.id == MASK:
        return "single_cmp"
    if _base_name(right) and isinstance(left, ast.Name) and left.id == MASK:
        return "single_cmp"
    return None


def _contains_position_shape(node: ast.AST) -> bool:
    """`고가 - (고가 - 저가) * ?` 형태의 일중 위치 표현인가."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Sub):
        return False
    names = set(_variable_names(node))
    return len(names & _POSITION_NAMES) >= 2


def _classify_boolop(node: ast.BoolOp) -> str | None:
    """`A > B*?1 and A < B*?2` / `A >= ?1 and A <= ?2` 같은 양측 결합."""
    if not isinstance(node.op, ast.And) or len(node.values) != 2:
        return None
    if not all(isinstance(value, ast.Compare) and len(value.ops) == 1
               for value in node.values):
        return None
    left, right = node.values                                  # type: ignore[misc]
    if _base_name(left.left) is None or _base_name(left.left) != _base_name(right.left):
        return None                                            # 같은 변수의 양측이어야 한다
    bases = [_mult_base(value.comparators[0]) for value in (left, right)]
    if all(base is not None for base in bases):
        return "mult_range"
    if all(isinstance(value.comparators[0], ast.Name)
           and value.comparators[0].id == MASK for value in (left, right)):
        return "range_and"
    return None


def _skeleton(node: ast.AST) -> str:
    return ast.unparse(node)


def extract_cards_with_report(
    *, sources: Mapping[str, str],
) -> tuple[tuple[PatternCard, ...], tuple[dict[str, str], ...]]:
    """조건식 원문들 → 패턴 카드와 제외 보고."""
    collected: dict[tuple[str, str], dict[str, object]] = {}
    skipped: list[dict[str, str]] = []
    for strategy, code in sources.items():
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            skipped.append({"strategy": strategy, "reason": f"syntax:{exc.msg}"})
            continue
        masked = ast.fix_missing_locations(_Mask().visit(tree))
        for node in ast.walk(masked):
            kind = None
            if isinstance(node, ast.BoolOp):
                kind = _classify_boolop(node)
            elif isinstance(node, ast.Compare):
                if _inside_boolop(masked, node):
                    continue
                kind = _classify_compare(node)
            if kind is None:
                continue
            variables = _variable_names(node)
            if any(name in _FLAG_NAMES for name in variables):
                continue
            skeleton = _skeleton(node)
            key = (kind, skeleton)
            entry = collected.setdefault(
                key, {"occurrences": 0, "sources": [], "variables": variables},
            )
            entry["occurrences"] = int(entry["occurrences"]) + 1              # type: ignore[arg-type]
            sources_list: list[str] = entry["sources"]                        # type: ignore[assignment]
            if strategy not in sources_list:
                sources_list.append(strategy)
    cards = tuple(
        PatternCard(
            card_id=f"{kind}_{index:02d}",
            kind=kind,
            skeleton=skeleton,
            variables=tuple(entry["variables"]),                              # type: ignore[arg-type]
            slots=skeleton.count(MASK),
            occurrences=int(entry["occurrences"]),                            # type: ignore[arg-type]
            sources=tuple(entry["sources"]),                                  # type: ignore[arg-type]
        )
        for index, ((kind, skeleton), entry) in enumerate(sorted(collected.items()))
    )
    return cards, tuple(skipped)


def _inside_boolop(tree: ast.AST, target: ast.Compare) -> bool:
    """이미 BoolOp 카드로 잡힌 Compare 는 따로 세지 않는다(중복 카드 방지)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and _classify_boolop(node) is not None:
            if any(value is target for value in node.values):
                return True
    return False


def extract_cards(*, sources: Mapping[str, str]) -> tuple[PatternCard, ...]:
    cards, _ = extract_cards_with_report(sources=sources)
    return cards


def catalog_payload(cards: tuple[PatternCard, ...]) -> dict[str, object]:
    by_kind: dict[str, int] = {}
    for card in cards:
        by_kind[card.kind] = by_kind.get(card.kind, 0) + 1
    return {
        "authority": "reference",
        "total": len(cards),
        "by_kind": by_kind,
        "cards": [asdict(card) for card in cards],
        "guard": (
            "골격만 저장합니다. 임계값과 창 크기는 카드에 남기지 않으며 "
            "데이터 분위 격자에서 채웁니다."
        ),
    }
