"""MEDIUM-4 — extract_code 펜스 추출 단위 테스트 (네트워크 없음).

검증:
  - ```python 펜스가 있으면 그 안의 코드만 추출(양끝 공백 제거).
  - 여러 펜스면 가장 긴 블록 채택.
  - 펜스가 전혀 없으면 산문을 통째로 넘기지 않고 빈 문자열을 반환한다
    (생성기 재시도 루프가 "코드 블록 없음" 사유로 재프롬프트하도록).
  - 빈 입력은 빈 문자열.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.brain.prompt import extract_code  # noqa: E402


def test_extracts_python_fence():
    text = "여기 전략입니다:\n```python\n매수 = True\nif 매수:\n    self.Buy()\n```\n끝."
    code = extract_code(text)
    assert code == "매수 = True\nif 매수:\n    self.Buy()"


def test_extracts_bare_fence():
    text = "```\n매도 = False\n```"
    assert extract_code(text) == "매도 = False"


def test_picks_longest_fence():
    text = "```python\nx=1\n```\n```python\n매수 = True\nif 매수:\n    self.Buy()\n```"
    code = extract_code(text)
    assert "self.Buy()" in code
    assert code != "x=1"


def test_no_fence_returns_empty_string():
    # MEDIUM-4: 펜스가 없으면 산문 폴백을 쓰지 않는다 → "" 반환.
    prose = "죄송하지만 전략 코드를 작성할 수 없습니다. 추가 정보가 필요합니다."
    assert extract_code(prose) == ""


def test_empty_input_returns_empty_string():
    assert extract_code("") == ""
    assert extract_code(None) == ""  # type: ignore[arg-type]
