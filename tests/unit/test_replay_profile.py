"""공식 replay 프로파일(ReplayProfile) 단위 테스트.

2026-07-02 포렌식에서 확정된 프로파일 분기 필드(betting, avg_time)가
sha/compare로 검출되는지, canonical 동결값이 회귀하지 않는지,
cli.research_loop opt-in 배선이 additive 필드만 추가하는지 검증한다.
"""

from dataclasses import replace
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.replay_profile import (  # noqa: E402
    CANONICAL_REPLAY_PROFILE_ID_V1,
    CANONICAL_REPLAY_PROFILE_V1,
    REPLAY_PROFILE_EXECUTION_IGNORED_FIELDS,
    REPLAY_PROFILE_IDENTITY_FIELDS,
    REPLAY_PROFILE_SCHEMA_VERSION,
    ReplayProfile,
    canonical_execution_diff,
    condition_code_sha256,
)
from cli import research_loop  # noqa: E402
from cli.research_loop import ResearchLoopConfig, run_research_once  # noqa: E402

# 2026-07-02 동결 스냅샷: canonical 프로파일의 정렬 JSON sha256.
# 필드/스키마가 바뀌면 이 값이 깨진다(의도된 회귀 감지).
_CANONICAL_SHA_SNAPSHOT = '4c5acdc5ee8beeb376ba0491b99aed89f6b0ef0c743ed1ab39a8dc208386b421'


def _canonical_kwargs() -> dict:
    receipt = CANONICAL_REPLAY_PROFILE_V1.to_receipt()
    receipt.pop('schema_version')
    return receipt


# ── (a) 동일 설정 → 동일 sha ──

def test_same_settings_produce_same_sha():
    first = ReplayProfile(**_canonical_kwargs())
    second = ReplayProfile(**_canonical_kwargs())
    assert first == second
    assert first.profile_sha256() == second.profile_sha256()
    assert first.to_receipt() == second.to_receipt()
    sha = first.profile_sha256()
    assert len(sha) == 64
    assert all(ch in '0123456789abcdef' for ch in sha)


# ── (b) 필드 차이 → compare/sha 검출 (포렌식 차이 필드 포함 전 필드) ──

@pytest.mark.parametrize('field_name,changed_value', [
    ('betting', '1'),               # 포렌식 차이 필드 1
    ('avg_time', 60),               # 포렌식 차이 필드 2
    ('engine_count', 32),
    ('fallback_engine_count', 0),
    ('start_date', 20240101),
    ('end_date', 20241231),
    ('start_time', 90500),
    ('end_time', 152800),
    ('is_tick', False),
    ('universe', 'coin'),
    ('divid_mode', '일자별 분류'),
    ('db_path', '_database/stock_min_back.db'),
    ('fill_model', 'other_fill'),
    ('slippage_model', 'other_slippage'),
])
def test_single_field_difference_changes_sha_and_compare(field_name, changed_value):
    base = CANONICAL_REPLAY_PROFILE_V1
    changed = replace(base, **{field_name: changed_value})
    assert changed.profile_sha256() != base.profile_sha256()
    assert base.compare(changed) == [field_name]
    assert changed.compare(base) == [field_name]


def test_compare_ignore_and_identity_fields():
    base = CANONICAL_REPLAY_PROFILE_V1
    changed = replace(base, betting='1', avg_time=60, profile_id='other_label')
    assert base.compare(changed) == ['avg_time', 'betting', 'profile_id']
    assert base.compare(changed, ignore=('profile_id',)) == ['avg_time', 'betting']
    assert base.compare(base) == []
    # 식별자 필드(라벨/조건식 sha)는 실행 환경 diff에서 제외된다.
    identity_only = replace(
        base,
        profile_id='run_specific',
        buy_strategy_name='BaseBuy',
        sell_strategy_name='SellCond',
        buy_condition_sha256=condition_code_sha256('buy = True'),
        sell_condition_sha256=condition_code_sha256('sell = True'),
    )
    assert canonical_execution_diff(identity_only) == []
    assert canonical_execution_diff(replace(identity_only, betting='1')) == ['betting']
    # fallback 엔진 수는 재시도 용량 메타 — 실행 환경 diff에서는 제외되지만
    # 원시 compare()에서는 여전히 검출된다(receipt/sha에도 그대로 남는다).
    assert 'fallback_engine_count' in REPLAY_PROFILE_EXECUTION_IGNORED_FIELDS
    fallback_only = replace(identity_only, fallback_engine_count=0)
    assert canonical_execution_diff(fallback_only) == []
    assert base.compare(fallback_only, ignore=REPLAY_PROFILE_IDENTITY_FIELDS) == [
        'fallback_engine_count'
    ]


def test_compare_rejects_non_profile():
    with pytest.raises(TypeError):
        CANONICAL_REPLAY_PROFILE_V1.compare({'betting': '5'})


# ── (c) canonical 프로파일 동결값 회귀(스냅샷) ──

def test_canonical_profile_frozen_values():
    profile = CANONICAL_REPLAY_PROFILE_V1
    assert profile.profile_id == CANONICAL_REPLAY_PROFILE_ID_V1 == 'official_replay_v1_20260702'
    assert profile.is_tick is True
    assert profile.betting == '5'
    assert profile.avg_time == 30
    assert profile.engine_count == 64
    assert profile.fallback_engine_count == 32
    assert profile.start_date == 20250101
    assert profile.end_date == 20251231
    assert profile.start_time == 90000
    assert profile.end_time == 92800
    assert profile.divid_mode == '종목코드별 분류'
    assert profile.db_path == '_database/stock_tick_back.db'
    assert profile.fill_model == 'engine_builtin_hoga_sweep'
    assert profile.slippage_model == 'engine_builtin'
    assert REPLAY_PROFILE_SCHEMA_VERSION == 1
    assert profile.profile_sha256() == _CANONICAL_SHA_SNAPSHOT


# ── (d) receipt 왕복/불변성/코드 sha 정규화 ──

def test_receipt_roundtrip_and_unknown_keys_ignored():
    receipt = CANONICAL_REPLAY_PROFILE_V1.to_receipt()
    assert receipt['schema_version'] == REPLAY_PROFILE_SCHEMA_VERSION
    restored = ReplayProfile.from_dict(receipt)
    assert restored == CANONICAL_REPLAY_PROFILE_V1
    assert restored.profile_sha256() == CANONICAL_REPLAY_PROFILE_V1.profile_sha256()
    tolerant = ReplayProfile.from_dict({**receipt, 'unknown_future_field': 'x'})
    assert tolerant == CANONICAL_REPLAY_PROFILE_V1


def test_profile_is_frozen():
    with pytest.raises(Exception):
        CANONICAL_REPLAY_PROFILE_V1.betting = '1'  # type: ignore[misc]


def test_condition_code_sha256_normalizes_line_endings():
    lf = condition_code_sha256('buy = True\nif buy:\n    self.Buy()')
    crlf = condition_code_sha256('buy = True\r\nif buy:\r\n    self.Buy()')
    assert lf == crlf
    assert condition_code_sha256('buy = False') != lf
    assert len(condition_code_sha256('')) == 64


# ── (e) research_loop opt-in 배선 (additive 필드, mock) ──

def _patch_research_pipeline(monkeypatch):
    monkeypatch.setattr(
        research_loop, 'analyze_result_csv',
        lambda *args, **kwargs: {'status': 'ok', 'recommended_candidates': []},
    )
    monkeypatch.setattr(
        research_loop, 'generate_condition_expressions_from_analysis',
        lambda *args, **kwargs: {
            'status': 'ok',
            'expressions': ['체결강도 < 90'],
            'candidate_count': 1,
            'selected_candidates': [],
        },
    )

    def fake_load(db_path, name, strategy_type):
        codes = {('BaseBuy', 'buy'): 'buy = True', ('SellCond', 'sell'): 'sell = True'}
        code = codes.get((name, strategy_type))
        if code is None:
            return {'status': 'error', 'message': 'strategy not found', 'name': name}
        return {'status': 'ok', 'code': code, 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)


def _receipt_config(**overrides) -> ResearchLoopConfig:
    base = dict(
        name='ReplayReceipt',
        baseline_csv='baseline.csv',
        base_buy_strategy='BaseBuy',
        sell_strategy='SellCond',
        run_candidate=False,
        betting='5',
        avg_time=30,
        engine_count=64,
        start_date=20250101,
        end_date=20251231,
        start_time=90000,
        end_time=92800,
    )
    base.update(overrides)
    return ResearchLoopConfig(**base)


def test_research_loop_default_has_no_replay_profile_fields(monkeypatch):
    _patch_research_pipeline(monkeypatch)
    result = run_research_once(_receipt_config(), controller=None)
    assert result['status'] == 'ok'
    assert 'replay_profile' not in result
    assert 'replay_profile_sha256' not in result
    assert 'replay_profile_canonical_diff' not in result
    assert 'replay_profile_error' not in result


def test_research_loop_opt_in_records_replay_profile_receipt(monkeypatch):
    _patch_research_pipeline(monkeypatch)
    result = run_research_once(
        _receipt_config(record_replay_profile=True),
        controller=None,
    )
    assert result['status'] == 'ok'
    receipt = result['replay_profile']
    assert receipt['schema_version'] == REPLAY_PROFILE_SCHEMA_VERSION
    assert receipt['betting'] == '5'
    assert receipt['avg_time'] == 30
    assert receipt['engine_count'] == 64
    assert receipt['buy_strategy_name'] == 'BaseBuy'
    assert receipt['sell_strategy_name'] == 'SellCond'
    assert receipt['buy_condition_sha256'] == condition_code_sha256('buy = True')
    assert receipt['sell_condition_sha256'] == condition_code_sha256('sell = True')
    assert receipt['db_path'].endswith('stock_tick_back.db')
    # sha는 receipt만으로 재계산 가능해야 한다.
    restored = ReplayProfile.from_dict(receipt)
    assert result['replay_profile_sha256'] == restored.profile_sha256()
    assert result['replay_profile_canonical_id'] == CANONICAL_REPLAY_PROFILE_ID_V1
    # canonical 동등 설정(공식 betting/avg_time/엔진 수/기간/시간창/tick DB)이면
    # research loop에 없는 fallback 엔진 메타와 무관하게 diff가 비어야 하고,
    # matches_canonical이 실제로 True가 될 수 있어야 한다(구조적 dead flag 방지).
    assert result['replay_profile_canonical_diff'] == []
    assert result['replay_profile_matches_canonical'] is True
    # 기존 스키마 키는 그대로 유지된다(additive-only).
    assert result['baseline_csv'] == 'baseline.csv'
    assert 'report' in result


def test_research_loop_receipt_detects_non_canonical_profile(monkeypatch):
    _patch_research_pipeline(monkeypatch)
    result = run_research_once(
        _receipt_config(record_replay_profile=True, betting='1', avg_time=60),
        controller=None,
    )
    assert result['status'] == 'ok'
    diff = result['replay_profile_canonical_diff']
    assert 'betting' in diff
    assert 'avg_time' in diff
    assert result['replay_profile_matches_canonical'] is False


def test_research_loop_receipt_failure_does_not_break_result(monkeypatch):
    _patch_research_pipeline(monkeypatch)

    def broken_profile(config):
        raise RuntimeError('receipt boom')

    monkeypatch.setattr(research_loop, '_build_replay_profile', broken_profile)
    result = run_research_once(
        _receipt_config(record_replay_profile=True),
        controller=None,
    )
    assert result['status'] == 'ok'
    assert result['replay_profile_error'] == 'receipt boom'
    assert 'replay_profile_sha256' not in result


def test_replay_profile_avg_time_coercion_and_db_selection(monkeypatch):
    # 전략 이름이 비어 있으면 DB 조회 없이 sha가 빈 문자열로 남는다.
    config = _receipt_config(
        base_buy_strategy='',
        sell_strategy='',
        avg_time='30',
        is_tick=False,
    )
    profile = research_loop._build_replay_profile(config)
    assert profile.avg_time == 30
    assert profile.db_path.endswith('stock_min_back.db')
    assert profile.buy_condition_sha256 == ''
    assert profile.sell_condition_sha256 == ''
