"""US-003 Phase 1b — generator 가드레일 단위 테스트 (네트워크/실LLM 없음).

provider를 mock하여 canned 응답을 돌려준다:
  1) 첫 응답: import os 가 든 나쁜 스니펫 → token_check 거부 → 재시도.
  2) 두 번째 응답: 정상 스니펫 → compile/token/dedup 통과 → tmp DB에 저장.

검증:
  - 거부 + 재시도 + 최종 저장.
  - 저장 대상은 TEMP db (프로덕션 DB 아님).
"""

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# generator는 cli.* 를 지연 import 한다. bootstrap을 먼저 import해 env-before-import 계약 충족.
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.token_check import DedupTracker  # noqa: E402
from ai_strategy_loop.controller.condition_discovery_feedback import build_pattern_card  # noqa: E402

BAD_BUY = "```python\nimport os\n매수 = True\nif 매수:\n    self.Buy()\n```"
GOOD_BUY = (
    "```python\n"
    "매수 = True\n"
    "if not (3 <= 등락율 <= 25):\n"
    "    매수 = False\n"
    "elif not (체결강도 >= 100):\n"
    "    매수 = False\n"
    "\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)


class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


class _FakeResult:
    def __init__(self, text):
        self.text = text
        self.usage = _FakeUsage()


class _ScriptedProvider:
    """미리 정해진 응답을 순서대로 돌려주는 mock provider."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, model=None, **kw):
        self.calls.append(messages)
        text = self._responses.pop(0)
        return _FakeResult(text)


def test_generator_rejects_retries_then_saves():
    provider = _ScriptedProvider([BAD_BUY, GOOD_BUY])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_strategies.db")

        result = generate_strategy(
            provider,
            kind="buy",
            name="TEST_buy",
            db_path=db_path,
            retry_max=3,
            dedup=DedupTracker(k=5),
        )

        # 최종 성공.
        assert result["status"] == "ok", result
        assert result["name"] == "TEST_buy"
        assert "self.Buy()" in result["code"]
        assert "import os" not in result["code"]
        # 첫 시도(나쁜 코드) 거부 후 두 번째에서 저장 → attempts == 2.
        assert result["attempts"] == 2
        assert provider.calls and len(provider.calls) == 2
        # usage 전달.
        assert result["usage"]["total_tokens"] == 30

        # 두 번째 프롬프트에는 prior_error(금지 토큰)가 들어가야 한다.
        second_user = provider.calls[1][-1]["content"]
        assert "금지 토큰" in second_user or "import" in second_user

        # TEMP db에 실제 저장됐는지 확인 (stockbuy 테이블).
        con = sqlite3.connect(db_path)
        try:
            cur = con.cursor()
            cur.execute('SELECT "전략코드" FROM stockbuy WHERE "index" = ?', ("TEST_buy",))
            row = cur.fetchone()
        finally:
            con.close()
        assert row is not None
        assert "self.Buy()" in row[0]


def test_generator_system_message_always_present():
    provider = _ScriptedProvider([GOOD_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(provider, "buy", "X", db_path, retry_max=1)
        assert result["status"] == "ok"
        # CRITICAL: system 메시지 필수 (HTTP 400 방지).
        first_messages = provider.calls[0]
        assert first_messages[0]["role"] == "system"
        assert first_messages[0]["content"].strip()


def test_generator_exhausts_retries_on_persistent_bad_code():
    provider = _ScriptedProvider([BAD_BUY, BAD_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(provider, "buy", "X", db_path, retry_max=2)
        assert result["status"] == "error"
        assert result["attempts"] == 2
        assert "재시도 소진" in result["reason"]


def test_generator_dedup_rejects_then_succeeds():
    # GOOD_BUY를 먼저 dedup에 기록 → 첫 응답(GOOD_BUY)은 중복 거부, 둘째는 다른 구조 저장.
    other_good = (
        "```python\n"
        "매수 = True\n"
        "if 현재가 < 500:\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
        "```"
    )
    provider = _ScriptedProvider([GOOD_BUY, other_good])
    dedup = DedupTracker(k=5)
    # GOOD_BUY 구조를 미리 기록 (직전에 같은 전략이 나왔다고 가정).
    dedup.record("매수 = True\nif not (3 <= 등락율 <= 25):\n    매수 = False\nelif not (체결강도 >= 100):\n    매수 = False\n\nif 매수:\n    self.Buy()\n")

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(provider, "buy", "X", db_path, retry_max=3, dedup=dedup)
        assert result["status"] == "ok", result
        assert result["attempts"] == 2
        assert "현재가 < 500" in result["code"]
def test_generator_pattern_card_guard_retries_before_save():
    copied = GOOD_BUY
    other_good = (
        "```python\n"
        "매수 = True\n"
        "if 현재가 < 500:\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
        "```"
    )
    card = build_pattern_card(
        card_id="seed-copy",
        source_label="seed_db:test",
        side="buy",
        expression="매수 = True\nif not (3 <= 등락율 <= 25):\n    매수 = False\nelif not (체결강도 >= 100):\n    매수 = False\n\nif 매수:\n    self.Buy()\n",
        pattern_summary="copy candidate",
        variable_families=["return", "orderflow"],
    )
    provider = _ScriptedProvider([copied, other_good])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider,
            "buy",
            "X",
            db_path,
            retry_max=2,
            pattern_cards=[card],
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 2
        assert "현재가 < 500" in result["code"]

        con = sqlite3.connect(db_path)
        try:
            rows = con.execute('SELECT "전략코드" FROM stockbuy WHERE "index" = ?', ("X",)).fetchall()
        finally:
            con.close()
        assert len(rows) == 1
        assert "현재가 < 500" in rows[0][0]
