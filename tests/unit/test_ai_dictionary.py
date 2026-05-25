"""US-001 Phase 0 — AI 전략 사전 자산 정합성 테스트.

자산: utility/ai_agent/system_prompt/v1/{variables_reference,examples,forbidden,system_prompt}.md

검증 목표:
1. 4개 자산 파일이 모두 존재하고 비어있지 않다.
2. variables_reference.md의 "SetGlobalsFunc 화이트리스트" 섹션에 적힌 함수형 이름이
   trade/base_strategy.py의 SetGlobalsFunc(dict_add_func 리터럴 키)에서 실제로 정의된
   이름의 부분집합이다 (= 환각된 함수 이름이 없다).
3. 추출된 함수형 이름 집합이 비어있지 않다 (자산이 trivially 비어있지 않음).

canonical 이름 집합 derivation:
    trade/base_strategy.py를 AST로 파싱 -> SetGlobalsFunc FunctionDef 안에서
    `dict_add_func = { ... }` 딕셔너리 리터럴을 찾아 문자열 상수 키 전체를 수집.
    (Step 2와 동일한 방법을 테스트가 재수행한다.)
"""
import ast
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_STRATEGY = os.path.join(PROJECT_ROOT, "trade", "base_strategy.py")
ASSET_DIR = os.path.join(PROJECT_ROOT, "utility", "ai_agent", "system_prompt", "v1")
ASSET_FILES = (
    "variables_reference.md",
    "examples.md",
    "forbidden.md",
    "system_prompt.md",
)

# variables_reference.md 안에서 SetGlobalsFunc 화이트리스트 섹션의 경계 헤더.
WHITELIST_HEADER = "## SetGlobalsFunc 화이트리스트"
# 화이트리스트 섹션 다음에 오는 헤더(매도 전용 잔고종목 변수) — 파싱 종료 경계.
WHITELIST_END_HEADER = "## 매도(sell) 전용 잔고종목 변수"

# 인라인 코드 토큰: `이름` (한글/영문/숫자/밑줄로 구성된 변수·함수 이름).
INLINE_CODE_TOKEN = re.compile(r"`([0-9A-Za-z_가-힣]+)`")


def _derive_setglobals_names():
    """Step 2와 동일한 AST 추출: SetGlobalsFunc.dict_add_func 리터럴의 문자열 키."""
    with open(BASE_STRATEGY, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    func = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "SetGlobalsFunc"
    )

    names = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "dict_add_func" for t in node.targets):
            continue
        if isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)
    return names


def _read_asset(name):
    with open(os.path.join(ASSET_DIR, name), encoding="utf-8") as fh:
        return fh.read()


def _whitelist_section(text):
    """variables_reference.md에서 화이트리스트 섹션 본문만 잘라낸다.

    blockquote(`>`)와 heading(`#`) 줄은 설명/구조 라벨이므로 제외한다 (산문 속 `N`,
    `이름` 같은 인라인 코드가 enumerate된 변수 이름으로 오인되지 않도록).
    실제 이름은 본문 줄의 인라인 코드 토큰에서만 수집한다.
    """
    start = text.index(WHITELIST_HEADER)
    rest = text[start:]
    end = rest.find(WHITELIST_END_HEADER)
    section = rest if end == -1 else rest[:end]
    lines = [
        ln for ln in section.splitlines()
        if not ln.lstrip().startswith((">", "#"))
    ]
    return "\n".join(lines)


def test_asset_files_exist_and_nonempty():
    for name in ASSET_FILES:
        path = os.path.join(ASSET_DIR, name)
        assert os.path.isfile(path), f"누락된 자산 파일: {path}"
        assert os.path.getsize(path) > 0, f"비어있는 자산 파일: {path}"


def test_setglobals_derivation_is_nonempty():
    canonical = _derive_setglobals_names()
    # 회귀 가드: SetGlobalsFunc 추출이 무너지면(0개) 즉시 실패.
    assert len(canonical) >= 100, f"SetGlobalsFunc 추출 이름 수가 비정상적으로 적음: {len(canonical)}"


def test_variables_reference_has_no_hallucinated_functions():
    canonical = _derive_setglobals_names()
    section = _whitelist_section(_read_asset("variables_reference.md"))
    referenced = set(INLINE_CODE_TOKEN.findall(section))

    # 자산이 trivially 비어있지 않음을 보장.
    assert referenced, "variables_reference.md 화이트리스트 섹션에 인라인 코드 이름이 없음"

    # 핵심: 문서에 적힌 함수형 이름이 모두 실제 SetGlobalsFunc 정의에 존재해야 한다.
    hallucinated = referenced - canonical
    assert not hallucinated, (
        f"variables_reference.md에 SetGlobalsFunc에 없는(환각된) 이름이 있음: "
        f"{sorted(hallucinated)}"
    )


def test_variables_reference_covers_full_whitelist():
    """문서 화이트리스트 섹션이 SetGlobalsFunc 181개 이름을 모두 enumerate 하는지(drift 방지)."""
    canonical = _derive_setglobals_names()
    section = _whitelist_section(_read_asset("variables_reference.md"))
    referenced = set(INLINE_CODE_TOKEN.findall(section))

    missing = canonical - referenced
    assert not missing, (
        f"variables_reference.md가 SetGlobalsFunc의 일부 이름을 누락함(자산 drift): "
        f"{sorted(missing)}"
    )
    # exact equality (hallucination + missing 동시 차단).
    assert referenced == canonical
