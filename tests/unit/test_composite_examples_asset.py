"""G1 — 복합 조건식 예제집(composite_examples.md) 계약 테스트.

모든 샘플은 `# [BUY|SELL][tick|min] <ID>` 헤더를 가진 python 코드펜스이며,
1) 선언된 timeframe/kind에서 변수 스코프 위반이 없어야 하고,
2) 문법상 유효(ast.parse)해야 하며,
3) 매수 12개 이상 / 매도 8개 이상이어야 하고,
4) Context Pack 자산으로 등재되어 있어야 한다.
"""
import ast
import re
from pathlib import Path

from ai_strategy_loop.brain.prompt import _FULL_STOM_SOURCE_ASSETS
from ai_strategy_loop.brain.variable_scope import check_variable_scope

_DOC = Path(__file__).resolve().parents[2] / "utility" / "ai_agent" / "system_prompt" / "v1" / "composite_examples.md"
_FENCE_RE = re.compile(r"```python\n(# \[(BUY|SELL)\]\[(tick|min)\][^\n]*\n)(.*?)```", re.DOTALL)


def _samples():
    text = _DOC.read_text(encoding="utf-8")
    out = []
    for m in _FENCE_RE.finditer(text):
        header, kind, timeframe, body = m.group(1), m.group(2), m.group(3), m.group(4)
        out.append((header.strip(), kind.lower(), timeframe, header + body))
    return out


def test_sample_counts_meet_contract():
    samples = _samples()
    buys = [s for s in samples if s[1] == "buy"]
    sells = [s for s in samples if s[1] == "sell"]
    assert len(buys) >= 12, f"매수 샘플 {len(buys)}개 (<12)"
    assert len(sells) >= 8, f"매도 샘플 {len(sells)}개 (<8)"


def test_every_sample_parses_and_passes_variable_scope():
    failures = []
    for header, kind, timeframe, code in _samples():
        try:
            ast.parse(code)
        except SyntaxError as exc:
            failures.append(f"{header}: SyntaxError {exc}")
            continue
        ok, offending = check_variable_scope(code, timeframe, kind)
        if not ok:
            failures.append(f"{header}: scope 위반 {offending}")
    assert not failures, "\n".join(failures)


def test_buy_samples_end_with_action_and_avoid_sell_vars():
    for header, kind, timeframe, code in _samples():
        if kind == "buy":
            assert "self.Buy()" in code, header
            for banned in ("수익률", "보유시간", "매수가", "최고수익률"):
                assert banned not in code, f"{header}: 매수식에 매도전용 변수 {banned}"
        else:
            assert "self.Sell()" in code, header


def test_registered_in_full_stom_source_assets():
    by_name = dict(_FULL_STOM_SOURCE_ASSETS)
    assert "composite_examples" in by_name
    assert by_name["composite_examples"].exists()


def test_hypothesis_and_disclaimer_present():
    text = _DOC.read_text(encoding="utf-8")
    assert "무근거 가설" in text
    assert text.count("가설:") >= 20  # 샘플마다 엣지 가설 주석
