"""P1c — 프롬프트 DB 영속화 단위 테스트 (네트워크/실LLM 없음, tmp SQLite만).

옵트인 토글(config.prompt_logging_enabled)로 LLM 호출별 프롬프트를 loop_runs.db의
prompts 테이블에 기록하는 경로를 검증한다.

검증:
  - generate_strategy(on_prompt=수집콜백) → attempt마다 레코드 dict가 수집되고
    kind/attempt/system_text/user_text/injected_features를 포함한다.
  - LoopState.record_prompt 직접 호출 → prompts 테이블에 행 1개, sha 컬럼이 채워지고
    system 전문은 미저장(system_sha만), user 전문은 저장된다.
  - on_prompt=None(기본) → 레코드 없음(byte-identical 경로). 그리고 config의
    prompt_logging_enabled 기본값이 False임을 확인한다.
  - SCHEMA_VERSION 현행(>=7), prompts 테이블과 인덱스가 존재한다.

실DB/백테 미사용: tmp 경로 SQLite만 쓴다.
"""

import os
import sqlite3
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# generator는 cli.* 를 지연 import 한다. bootstrap을 먼저 import해 env-before-import 계약 충족.
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.controller.state import SCHEMA_VERSION, LoopState  # noqa: E402


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
    prompt_tokens = 11
    completion_tokens = 22
    total_tokens = 33


class _FakeResult:
    def __init__(self, text):
        self.text = text
        self.usage = _FakeUsage()
        self.model = "fake-model-1"


class _ScriptedProvider:
    """미리 정해진 응답을 순서대로 돌려주는 mock provider (model 포함)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, model=None, **kw):
        self.calls.append(messages)
        text = self._responses.pop(0)
        return _FakeResult(text)


# =====================================================================
# 1) generate_strategy on_prompt 콜백 — attempt마다 레코드 dict 수집.
# =====================================================================
def test_generate_strategy_invokes_on_prompt_callback():
    provider = _ScriptedProvider([GOOD_BUY])
    records = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        # encourage_time_dispersion=True로 토글이 injected_features에 반영되는지 본다.
        #   (require_filter_gates는 GOOD_BUY를 reject시키므로 여기선 켜지 않는다.)
        result = generate_strategy(
            provider, "buy", "X", db_path, retry_max=1,
            encourage_time_dispersion=True,
            on_prompt=records.append,
        )

    assert result["status"] == "ok", result
    # 단일 성공 호출이라 레코드 1개.
    assert len(records) == 1
    rec = records[0]
    assert rec["kind"] == "buy"
    assert rec["attempt"] == 1
    # system/user 전문이 콜백에 담긴다.
    assert rec["system_text"].strip()
    assert "STOM" in rec["user_text"]
    # 주입 피처 — 호출에 넘긴 토글이 반영된다.
    feats = rec["injected_features"]
    assert feats["timeframe"] == "min"
    assert feats["encourage_time_dispersion"] is True
    assert feats["require_filter_gates"] is False
    assert feats["has_base_code"] is False
    assert set(feats) >= {
        "guide_context",
        "diff_context",
        "analysis_context",
        "correlation_context",
    }
    assert feats["guide_context"] == {
        "system_prompt_assets": "v1",
        "timeframe": "min",
        "few_shot_examples": 0,
    }
    assert feats["diff_context"] == {
        "has_base_code": False,
        "has_crossover": False,
        "has_history_summary": False,
    }
    assert feats["analysis_context"] == {
        "has_autopsy_feedback": False,
        "has_meta_seed": False,
        "has_hypothesis_feedback": False,
        "has_segment_avoid": False,
    }
    assert feats["correlation_context"] == {
        "available_route": "/variable_correlation",
        "prompt_injected": False,
    }
    # usage/model/response 전달.
    assert rec["usage"]["total_tokens"] == 33
    assert rec["model"] == "fake-model-1"
    assert "self.Buy()" in rec["response_text"]


def test_on_prompt_records_each_attempt():
    # 첫 응답은 코드 블록 없음(extract_code 실패 → 재시도), 둘째는 정상.
    provider = _ScriptedProvider(["코드 블록 없는 설명만", GOOD_BUY])
    records = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X", db_path, retry_max=3,
            on_prompt=records.append,
        )

    assert result["status"] == "ok", result
    # 두 번 호출됐으니 두 attempt의 레코드가 수집된다.
    assert [r["attempt"] for r in records] == [1, 2]
    # 두 번째 attempt의 prior_error는 첫 시도(코드 추출 실패) 컨텍스트를 담는다.
    assert records[0]["prior_error"] is None
    assert records[1]["prior_error"] is not None


# =====================================================================
# 2) LoopState.record_prompt 직접 — prompts 행 + sha + system 미저장.
# =====================================================================
def test_record_prompt_persists_row_with_hashes(tmp_path):
    st = LoopState(db_path=str(tmp_path / "p.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        rid = st.start_run(LoopConfig())
        st.record_prompt(
            rid, 0, "buy", 1,
            system_text="시스템 전문(정적 자산)",
            user_text="유저 전문(동적)",
            injected_features={"timeframe": "min", "require_filter_gates": True},
            prior_error=None,
            model="fake-model-1",
            prompt_tokens=11, completion_tokens=22, total_tokens=33,
            response_text="응답 전문",
        )
        rows = st.get_prompts(rid)
    finally:
        st.close()

    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == rid
    assert row["gen_no"] == 0
    assert row["kind"] == "buy"
    assert row["attempt"] == 1
    # system 전문은 저장하지 않고 sha만 저장된다(컬럼 자체가 없음).
    assert "system_text" not in row
    assert row["system_sha"] and len(row["system_sha"]) == 64
    # user 전문은 저장된다 + sha도 채워진다.
    assert row["user_text"] == "유저 전문(동적)"
    assert row["user_sha"] and len(row["user_sha"]) == 64
    assert row["response_sha"] and len(row["response_sha"]) == 64
    # injected_features는 json으로 직렬화돼 저장된다.
    assert "require_filter_gates" in row["injected_features"]
    # 토큰/모델 보존.
    assert row["total_tokens"] == 33
    assert row["model"] == "fake-model-1"


def test_record_prompt_handles_empty_strings(tmp_path):
    # 빈 문자열도 sha 계산이 안전해야 한다(예외 없이 행 1개).
    st = LoopState(db_path=str(tmp_path / "pe.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        rid = st.start_run(LoopConfig())
        st.record_prompt(rid, 0, "sell", 1)  # 전부 기본값(빈 문자열/None/0).
        rows = st.get_prompts(rid)
    finally:
        st.close()
    assert len(rows) == 1
    # 빈 문자열의 sha256도 64자 hexdigest다.
    assert len(rows[0]["system_sha"]) == 64
    assert rows[0]["injected_features"] is None  # injected_features=None → NULL.


# =====================================================================
# 3) on_prompt=None(기본) → 레코드 없음(byte-identical) + 토글 기본 False.
# =====================================================================
def test_no_callback_means_no_records():
    provider = _ScriptedProvider([GOOD_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        # on_prompt 미지정(기본 None) — 로깅 경로가 평가조차 안 된다.
        result = generate_strategy(provider, "buy", "X", db_path, retry_max=1)
    assert result["status"] == "ok"
    # 콜백이 없으면 부작용도 없다(예외/추가 동작 없음). 호출은 정상 1회.
    assert len(provider.calls) == 1


def test_prompt_logging_default_disabled():
    # 신규 토글은 기본 OFF여야 한다(미설정 시 기존 동작 byte-identical).
    cfg = LoopConfig()
    assert cfg.prompt_logging_enabled is False
    # from_dict 누락 시에도 기본 False.
    assert LoopConfig.from_dict({}).prompt_logging_enabled is False
    # 직렬화 라운드트립에서도 필드가 보존된다.
    assert "prompt_logging_enabled" in cfg.to_dict()


# =====================================================================
# 4) prompts 테이블/인덱스 존재 + 스키마 버전이 prompts 도입(v7) 이후.
#    SCHEMA_VERSION은 이후 마이그레이션(v8 P1b 등)으로 증가하므로 ">=7"로 검증한다.
# =====================================================================
def test_schema_has_prompts_table_and_current_version(tmp_path):
    st = LoopState(db_path=str(tmp_path / "v7.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        # prompts 테이블은 v7에 도입됐다 — 그 이후 버전이어야 한다.
        assert SCHEMA_VERSION >= 7
        assert st.get_schema_version() == SCHEMA_VERSION
        # prompts 테이블 존재.
        tables = {
            row[0]
            for row in st._con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "prompts" in tables
        # 인덱스 존재.
        indexes = {
            row[0]
            for row in st._con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_prompts_run_gen" in indexes
        # 컬럼 셰이프 확인(주요 컬럼).
        cols = {row[1] for row in st._con.execute("PRAGMA table_info(prompts)")}
        assert {"system_sha", "user_text", "user_sha", "injected_features",
                "response_sha", "prompt_id"}.issubset(cols)
    finally:
        st.close()


def test_legacy_db_without_prompts_table_gets_it(tmp_path):
    # prompts 테이블이 없는 구버전 DB도 열면 CREATE TABLE IF NOT EXISTS로 안전 보강.
    db = str(tmp_path / "legacy_no_prompts.db")
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT,
            status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL
        );
        CREATE TABLE generations (
            run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT,
            status TEXT, score REAL, calmar REAL, uptrend_r2 REAL,
            gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER,
            created_at REAL, PRIMARY KEY (run_id, gen_no)
        );
        """
    )
    con.commit()
    con.close()

    st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
    try:
        assert st.get_schema_version() == SCHEMA_VERSION
        tables = {
            row[0]
            for row in st._con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "prompts" in tables
        # 새 DB에 prompts 행을 기록할 수 있다.
        rid = st.start_run(LoopConfig(), run_id="legacy_run")
        st.record_prompt(rid, 0, "buy", 1, user_text="x")
        assert len(st.get_prompts(rid)) == 1
    finally:
        st.close()
