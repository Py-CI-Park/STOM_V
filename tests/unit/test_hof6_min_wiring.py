"""HOF6 — min 레인 시각 단위 배선 검증.

2026-08-12 결함: `_run_arm` 이 min 세션을 HHMM(900/1528)으로 보내
`GetBackloadCodeQuery` 의 /100 변환과 겹쳐 빈 구간을 질의했고,
모든 min 백테가 no_trades 로 위장됐다(레인 가용성 실사에서 발견).
CLI 계약 = tick/min 모두 **HHMMSS**.
"""

from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_engine_measure import _run_arm, _session_hhmmss


class TestSessionUnits:
    def test_min_은_HHMMSS_로_변환된다(self):
        assert _session_hhmmss(LANES["min"]) == (90000, 152800)

    def test_tick_은_기존_계약_그대로(self):
        assert _session_hhmmss(LANES["tick"]) == (90000, 92800)


class _FakeClient:
    def __init__(self):
        self.posts = []

    def call(self, method, path, payload=None):
        if method == "POST":
            self.posts.append(payload)
            return {}  # job_id 없음 → _run_arm 이 즉시 반환
        return {}


class TestRunArmPayload:
    def test_min_페이로드가_계약_단위다(self):
        fake = _FakeClient()
        out = _run_arm(fake, buy="B", sell="S", lane=LANES["min"],
                       engines=4, timeout=60, period=(20251103, 20251128))
        assert out["status"] == "no_job"
        payload = fake.posts[0]
        # 회귀의 핵심: 900/1528 이 다시 들어오면 min 레인 전체가 침묵 실패한다.
        assert payload["start_time"] == 90000
        assert payload["end_time"] == 152800
        assert payload["timeframe"] == "min"

    def test_tick_페이로드는_불변(self):
        fake = _FakeClient()
        _run_arm(fake, buy="B", sell="S", lane=LANES["tick"],
                 engines=4, timeout=60, period=(20220323, 20250822))
        payload = fake.posts[0]
        assert payload["start_time"] == 90000
        assert payload["end_time"] == 92800


class TestQueryContract:
    """STOM 쿼리 함수와의 계약을 문서화한다 — 이것이 어긋나면 침묵 실패다."""

    def test_min_쿼리는_HHMMSS_입력을_12자리_index_로_만든다(self):
        from backtest.back_static import GetBackloadCodeQuery
        q = GetBackloadCodeQuery(False, "025950", [20251117], 90000, 152800)
        assert "202511170900" in q and "202511171528" in q

    def test_HHMM_을_넣으면_빈_구간이_된다_회귀_문서화(self):
        from backtest.back_static import GetBackloadCodeQuery
        q = GetBackloadCodeQuery(False, "025950", [20251117], 900, 1528)
        # 결함 재현: 0009~0015 — 존재하지 않는 시각대.
        assert "202511170009" in q and "202511170015" in q
