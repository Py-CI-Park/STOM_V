"""P2 — GA(population 기반 진화) 루프 단위 테스트 (네트워크/실LLM/실백테 없음).

provider(chat)와 warm_session.run을 mock으로 주입해 다음을 검증한다:
  - crossover 프롬프트 조립(부모 2개) — build_messages crossover_parents 경로.
  - mutation 경로(단일 base_code) 보존.
  - 선택/elitism: graded 상위 K 보존, 상위 ga_elite 무변이 복제.
  - **가드실패 → K 유지 fill**: provider가 invalid code를 반환해 자식이 가드
    재시도 소진(status error)이어도 population이 정확히 K로 유지된다.
  - population 직렬화(page_data['population']).
  - 종료 판정(should_terminate 재사용; max_generations).
  - run_ga_loop를 warm_session/provider mock으로 1~2세대 구동(통합형 단위).

실제 백테/루프 실행은 하지 않는다 — warm_session.run + _score_outcome을 mock한다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
import pytest  # noqa: E402

from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import ga as GA  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402


# =====================================================================
# 1) crossover 프롬프트 조립 (build_messages crossover_parents).
# =====================================================================
class TestCrossoverPrompt:
    def test_build_messages_crossover_includes_both_parents(self):
        parent_a = "매수 = True\nif 등락율 > 3:\n    매수 = True\nif 매수:\n    self.Buy()"
        parent_b = "매수 = True\nif 체결강도 >= 120:\n    매수 = True\nif 매수:\n    self.Buy()"
        msgs = build_messages("buy", crossover_parents=(parent_a, parent_b))
        user = msgs[-1]["content"]
        # 두 부모 코드가 모두 프롬프트에 들어가야 한다.
        assert "등락율 > 3" in user
        assert "체결강도 >= 120" in user
        # crossover 의도(결합) 지침이 있어야 한다.
        assert "결합" in user or "crossover" in user.lower()
        # 부모 A/B 라벨이 명시돼야 한다.
        assert "부모 A" in user and "부모 B" in user

    def test_crossover_overrides_base_code(self):
        # crossover_parents가 주어지면 base_code(단일 mutation)는 무시된다(상호 배타).
        msgs = build_messages(
            "buy",
            base_code="매수 = True\nif 시가총액 < 1000:\n    매수 = True\nif 매수:\n    self.Buy()",
            crossover_parents=("AAA_PARENT", "BBB_PARENT"),
        )
        user = msgs[-1]["content"]
        assert "AAA_PARENT" in user and "BBB_PARENT" in user
        # base_code 단독 지침(가장 좋은 ...전략이다. 이것을 출발점으로)은 붙지 않는다.
        assert "시가총액 < 1000" not in user

    def test_mutation_path_preserved(self):
        # 단일 base_code(mutation) 경로는 그대로 유지(crossover 미지정).
        msgs = build_messages(
            "buy",
            base_code="매수 = True\nif 시가총액 < 1000:\n    매수 = True\nif 매수:\n    self.Buy()",
        )
        user = msgs[-1]["content"]
        assert "시가총액 < 1000" in user
        assert "출발점" in user  # seed-and-refine 지침 보존.


# =====================================================================
# mock 헬퍼.
# =====================================================================
class _FakeUsage:
    prompt_tokens = 5
    completion_tokens = 5
    total_tokens = 10


class _FakeResult:
    def __init__(self, text):
        self.text = text
        self.usage = _FakeUsage()


# 구조적으로 서로 다른 매수 변형들(dedup은 리터럴이 아니라 AST 구조로 판정하므로
#   변수/조건 개수를 바꿔 매번 distinct 구조가 되게 한다).
_BUY_VARS = ["등락율", "체결강도", "현재가", "분당거래대금", "시가총액", "분당매수수량",
             "분당매도수량", "분봉시가", "분봉고가", "분봉저가", "분당매수금액", "분당매도금액"]
_SELL_VARS = ["수익률", "등락율", "체결강도", "현재가", "분당거래대금", "분봉저가",
              "분봉고가", "분당매도수량", "분당매수수량", "시가총액", "분봉시가", "분당매도금액"]


def _good_buy(idx):
    # idx로 변수/조건 수를 바꿔 구조적으로 distinct한 정규 매수 전략을 만든다.
    n_cond = (idx % 4) + 1
    lines = ["매수 = True"]
    for j in range(n_cond):
        var = _BUY_VARS[(idx + j) % len(_BUY_VARS)]
        lines.append(f"if {var} < {10 + idx + j}:")
        lines.append("    매수 = False")
    lines.append("if 매수:")
    lines.append("    self.Buy()")
    return "```python\n" + "\n".join(lines) + "\n```"


def _good_sell(idx):
    n_cond = (idx % 3) + 1
    lines = ["매도 = True"]
    for j in range(n_cond):
        var = _SELL_VARS[(idx + j) % len(_SELL_VARS)]
        lines.append(f"if {var} > {5 + idx + j}:")
        lines.append("    매도 = False")
    lines.append("if 매도:")
    lines.append("    self.Sell()")
    return "```python\n" + "\n".join(lines) + "\n```"


_BAD = "```python\nimport os\n매수 = True\nif 매수:\n    self.Buy()\n```"


class _CountingProvider:
    """매 호출마다 구조적으로 distinct한 유효 코드를 돌려주는 mock provider.

    buy/sell를 user 메시지로 구분해 각각 다른 구조의 전략을 만든다(dedup은 AST
    구조로 판정하므로 리터럴이 아니라 조건/변수 구성을 매번 바꾼다). 호출 수를 센다.
    """

    def __init__(self):
        self.calls = 0
        self._n = 0

    def chat(self, messages, model=None, **kw):
        self.calls += 1
        self._n += 1
        user = messages[-1]["content"]
        if "매도전략" in user:
            return _FakeResult(_good_sell(self._n))
        return _FakeResult(_good_buy(self._n))


class _AlwaysBadProvider:
    """항상 금지 토큰(import os) 코드를 돌려주는 provider → 모든 자식이 가드 소진."""

    def __init__(self):
        self.calls = 0

    def chat(self, messages, model=None, **kw):
        self.calls += 1
        return _FakeResult(_BAD)


def _fake_score_factory(graded_by_buy):
    """buy_name → graded 점수 매핑으로 _score_outcome을 흉내내는 가짜.

    GA._evaluate_individual은 warm_session.run 결과를 _warm_to_outcome로 정규화한 뒤
    _score_outcome(outcome, cfg)를 부른다. outcome.metrics에 buy_name을 심어두고
    여기서 그 이름으로 graded를 정한다(테스트 결정론).
    """

    def _fake_score(outcome, cfg):
        buy = (outcome.metrics or {}).get("_buy_name", "")
        sc = graded_by_buy.get(buy, 0.1)
        gate = sc >= 1.0
        fit = FitnessResult(
            score=sc if gate else 0.0, calmar=sc, uptrend_r2=1.0,
            gate_passed=gate, reason="ok" if gate else "gate",
            cagr=1.0, mdd=10.0, trade_count=50, total_profit=100000.0,
        )
        graded = GradedResult(
            graded=sc, gate_passed=gate, composite=sc if gate else 0.0,
            trades_term=1.0, mdd_term=1.0, profit_term=1.0, uptrend_term=1.0,
            gate_distance="ok" if gate else "gate failed",
            cagr=1.0, mdd=10.0, trade_count=50, total_profit=100000.0, uptrend_r2=1.0,
        )
        return (fit, graded, None)

    return _fake_score


class _FakeWarmSession:
    """warm_session.run(buy,sell)를 흉내낸다. metrics에 buy_name을 심어 점수와 연결."""

    def __init__(self):
        self.runs = []

    def run(self, buy, sell, **kw):
        self.runs.append((buy, sell))
        return {
            "status": "success",
            "csv_path": "fake.csv",
            "metrics": {"_buy_name": buy, "cagr": 1.0, "mdd_pct": 10.0,
                        "trade_count": 50, "total_profit_krw": 100000.0},
        }


def _neutralize_gen_db(monkeypatch):
    """전략 생성/엔진 호환의 DB 부작용을 무력화(코드만 생성, 실DB 저장 회피)."""
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    # gist/code read는 보조 — DB 없이 빈 값/None로 폴백.
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")
    monkeypatch.setattr(L, "_read_strategy_code", lambda name, kind: f"CODE::{name}::{kind}")
    # save_strategy_to_db: 실제 DB 대신 ok만 반환(generate_strategy 통과).
    import cli.strategy_generator as SG
    monkeypatch.setattr(SG, "save_strategy_to_db", lambda *a, **k: {"status": "ok"})


# =====================================================================
# 2) 선택/elitism (상위 K 보존, 상위 ga_elite 무변이 복제).
# =====================================================================
class TestSelectionElitism:
    def test_select_sorted_descending(self):
        a = GA.Individual("ba", "sa"); a.graded = 0.3
        b = GA.Individual("bb", "sb"); b.graded = 1.5; b.gate_passed = True
        c = GA.Individual("bc", "sc"); c.graded = 0.9
        ranked = GA._select_sorted([a, b, c])
        assert [i.buy_name for i in ranked] == ["bb", "bc", "ba"]

    def test_breed_preserves_k_and_elites(self, monkeypatch):
        _neutralize_gen_db(monkeypatch)
        provider = _CountingProvider()
        cfg = LoopConfig(provider="openrouter", ga_population=6, ga_elite=2,
                         ga_crossover_rate=0.5)
        ranked = []
        for i in range(6):
            ind = GA.Individual(f"AILOOP_r_g0_p{i}_buy", f"AILOOP_r_g0_p{i}_sell",
                                buy_code=f"BUY{i}", sell_code=f"SELL{i}")
            ind.graded = float(6 - i)  # p0 최고.
            ranked.append(ind)
        next_pop, guardfail = GA._breed_next_population(
            provider, cfg, "r", 1, ranked, k=6, elite_n=2,
            history_summary=None, dedup=None,
        )
        # 정확히 K=6 유지.
        assert len(next_pop) == 6
        # 상위 2개 elite가 무변이 복제(같은 전략 이름 + origin=elite).
        assert next_pop[0].origin == "elite"
        assert next_pop[0].buy_name == "AILOOP_r_g0_p0_buy"
        assert next_pop[1].origin == "elite"
        assert next_pop[1].buy_name == "AILOOP_r_g0_p1_buy"
        # 가드실패 없음(유효 코드 provider).
        assert guardfail == 0
        # 비-엘리트 자식은 crossover/mutation origin.
        for child in next_pop[2:]:
            assert child.origin in ("crossover", "mutation")

    def test_breed_crossover_count_respects_rate(self, monkeypatch):
        _neutralize_gen_db(monkeypatch)
        provider = _CountingProvider()
        cfg = LoopConfig(provider="openrouter", ga_population=6, ga_elite=2,
                         ga_crossover_rate=0.5)
        ranked = [GA.Individual(f"b{i}", f"s{i}", buy_code=f"B{i}", sell_code=f"S{i}")
                  for i in range(6)]
        for i, ind in enumerate(ranked):
            ind.graded = float(6 - i)
        next_pop, _ = GA._breed_next_population(
            provider, cfg, "r", 1, ranked, k=6, elite_n=2,
            history_summary=None, dedup=None,
        )
        children = next_pop[2:]  # 4 children, rate 0.5 → 2 crossover, 2 mutation.
        n_cross = sum(1 for c in children if c.origin == "crossover")
        assert n_cross == 2


# =====================================================================
# 3) 가드실패 → K 유지 fill (provider가 invalid code → 자식 가드 소진).
# =====================================================================
class TestGuardfailFillKeepsK:
    def test_all_children_guardfail_fills_with_elites(self, monkeypatch):
        _neutralize_gen_db(monkeypatch)
        provider = _AlwaysBadProvider()  # 모든 자식 생성이 가드(token) 소진.
        cfg = LoopConfig(provider="openrouter", ga_population=6, ga_elite=2,
                         ga_crossover_rate=0.5, max_retries=1)
        ranked = [GA.Individual(f"b{i}", f"s{i}", buy_code=f"B{i}", sell_code=f"S{i}")
                  for i in range(6)]
        for i, ind in enumerate(ranked):
            ind.graded = float(6 - i)
        next_pop, guardfail = GA._breed_next_population(
            provider, cfg, "r", 1, ranked, k=6, elite_n=2,
            history_summary=None, dedup=None,
        )
        # 자식 4개 전부 가드실패해도 population은 정확히 K=6 유지(elite 복제 fill).
        assert len(next_pop) == 6
        assert guardfail == 4  # 4개 비-엘리트 자식 모두 가드실패.
        # fill된 비-엘리트 슬롯은 elite 복제(최우수)로 채워진다.
        for child in next_pop[2:]:
            assert child.origin == "elite"
            # 최우수 elite(b0) 또는 가용 부모 복제.
            assert child.buy_name in {ind.buy_name for ind in ranked}


# =====================================================================
# 4) population 직렬화 (page_data['population']).
# =====================================================================
class TestPopulationPageData:
    def test_page_data_shape(self):
        pop = []
        for i in range(3):
            ind = GA.Individual(f"b{i}", f"s{i}")
            ind.graded = float(3 - i)
            ind.gate_passed = (i == 0)
            ind.trade_count = 40 + i
            ind.mdd = 12.0 + i
            ind.profit = 100000.0 - i
            ind.ok = True
            ind.origin = "mutation"
            pop.append(ind)
        pd = GA._population_page_data(pop, gen_no=2, guardfail=1)
        assert pd["status"] == "ok"
        assert pd["k"] == 3
        assert pd["gen_no"] == 2
        assert pd["guardfail_count"] == 1
        assert pd["gate_passed_count"] == 1
        assert pd["best_graded"] == 3.0
        assert len(pd["members"]) == 3
        # graded 내림차순 정렬.
        gradeds = [m["graded"] for m in pd["members"]]
        assert gradeds == sorted(gradeds, reverse=True)
        m0 = pd["members"][0]
        for key in ("buy_name", "sell_name", "graded", "gate_passed",
                    "trade_count", "mdd", "profit", "origin"):
            assert key in m0


# =====================================================================
# 5) 종료 판정 재사용 (should_terminate; max_generations).
# =====================================================================
class TestTermination:
    def test_run_ga_loop_stops_at_max_generations(self, monkeypatch, tmp_path):
        _neutralize_gen_db(monkeypatch)
        # 모든 개체 graded = buy_name 해시 무관 고정(점수 매핑 기본 0.1, gate 미통과).
        monkeypatch.setattr(L, "_score_outcome", _fake_score_factory({}))
        provider = _CountingProvider()
        warm = _FakeWarmSession()
        cfg = LoopConfig(provider="openrouter", ga_population=4, ga_elite=2,
                         ga_crossover_rate=0.5, max_generations=2,
                         cost_cap_generations=100, cost_cap_tokens=None,
                         max_retries=1)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        rid = st.resume_or_start(cfg, run_id="garun")
        summary = GA.run_ga_loop(cfg, warm, provider, st, rid)
        # max_generations=2 → 2세대 기록 후 종료.
        assert summary["generations"] == 2
        assert "max_generations" in summary["stop_reason"]
        # warm.run은 세대당 K=4회 직렬 평가 → 2세대면 8회.
        assert len(warm.runs) == 8
        st.close()


# =====================================================================
# 6) 통합형: run_ga_loop 1~2세대 구동 + best/winner 추적 + page_data 발행.
# =====================================================================
class TestRunGaLoopIntegration:
    def test_run_ga_loop_tracks_best_and_winner_and_publishes(self, monkeypatch, tmp_path):
        _neutralize_gen_db(monkeypatch)
        # gen0 개체 중 하나가 gate 통과(graded>=1.0)하도록 점수 매핑.
        #   초기 population buy 이름은 AILOOP_garun2_g0_p{slot}_buy 형식.
        #   p1 개체를 winner로(graded 1.5, gate pass).
        score_map = {
            "AILOOP_garun2_g0_p1_buy": 1.5,  # gate 통과 → winner 후보.
            "AILOOP_garun2_g0_p0_buy": 0.4,
        }
        monkeypatch.setattr(L, "_score_outcome", _fake_score_factory(score_map))

        published = []
        orig_publish = GA._publish

        def _capture_publish(st, rid, config, **kwargs):
            published.append(kwargs)
            return orig_publish(st, rid, config, **kwargs)

        monkeypatch.setattr(GA, "_publish", _capture_publish)

        provider = _CountingProvider()
        warm = _FakeWarmSession()
        cfg = LoopConfig(provider="openrouter", ga_population=4, ga_elite=2,
                         ga_crossover_rate=0.5, max_generations=1,
                         cost_cap_generations=100, cost_cap_tokens=None,
                         max_retries=1)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        rid = st.resume_or_start(cfg, run_id="garun2")
        summary = GA.run_ga_loop(cfg, warm, provider, st, rid)

        assert summary["run_id"] == "garun2"
        assert summary["generations"] == 1
        # best는 graded 최고(p1, 1.5).
        assert summary["best_score"] == 1.5
        assert summary["best_buy"] == "AILOOP_garun2_g0_p1_buy"
        # winner는 하드 게이트 통과 개체(p1).
        assert summary["winner_gen"] == 0
        assert summary["winner_buy"] == "AILOOP_garun2_g0_p1_buy"
        # page_data['population']이 발행됐다.
        pop_publishes = [k for k in published if (k.get("page_data") or {}).get("population")]
        assert pop_publishes, "population page_data가 발행되지 않음"
        pop = pop_publishes[-1]["page_data"]["population"]
        assert pop["k"] == 4
        assert pop["status"] == "ok"
        assert len(pop["members"]) == 4
        st.close()

    def test_run_ga_loop_robust_to_eval_failure(self, monkeypatch, tmp_path):
        """평가 실패(타임아웃/예외) 개체는 graded 0 처리되고 루프는 계속/종료한다."""
        _neutralize_gen_db(monkeypatch)
        monkeypatch.setattr(L, "_score_outcome", _fake_score_factory({}))

        class _FlakyWarm(_FakeWarmSession):
            def run(self, buy, sell, **kw):
                self.runs.append((buy, sell))
                if len(self.runs) % 2 == 0:
                    raise RuntimeError("simulated warm crash")
                return {"status": "timeout", "csv_path": None, "metrics": None}

        warm = _FlakyWarm()
        provider = _CountingProvider()
        cfg = LoopConfig(provider="openrouter", ga_population=3, ga_elite=1,
                         ga_crossover_rate=0.5, max_generations=2,
                         cost_cap_generations=100, cost_cap_tokens=None,
                         max_retries=1)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        rid = st.resume_or_start(cfg, run_id="garun3")
        summary = GA.run_ga_loop(cfg, warm, provider, st, rid)
        # 평가 전부 실패해도 크래시 없이 max_generations로 종료.
        assert summary["generations"] == 2
        assert "max_generations" in summary["stop_reason"]
        # winner 없음(게이트 통과 0).
        assert summary["winner_gen"] == -1
        st.close()


# =====================================================================
# 7) loop.run_loop의 evolution_mode='ga' 단일 분기.
# =====================================================================
class TestRunLoopGaBranch:
    def test_run_loop_delegates_to_ga_when_mode_ga(self, monkeypatch, tmp_path):
        # run_loop이 evolution_mode='ga'면 run_ga_loop에 위임하는지(단일 분기).
        monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
        # warm 세션 prepare를 무력화(실엔진 미기동) — warm_session 객체만 만든다.
        called = {"ga": False}

        def _fake_run_ga_loop(config, warm_session, provider, st, rid, **kw):
            called["ga"] = True
            return {"run_id": rid, "generations": 0, "best_gen": -1,
                    "best_score": None, "best_buy": None, "best_sell": None,
                    "winner_gen": -1, "winner_score": None, "winner_buy": None,
                    "winner_sell": None, "stop_reason": "ga_test"}

        import ai_strategy_loop.controller.ga as GAmod
        monkeypatch.setattr(GAmod, "run_ga_loop", _fake_run_ga_loop)

        # warm prepare가 ok를 반환하도록 WarmBacktestSession을 가짜로 교체.
        class _FakeWarm:
            def __init__(self, cfg):
                pass

            def prepare(self):
                return {"status": "ok", "back_count": 3}

            def close(self):
                pass

        monkeypatch.setattr(L, "WarmBacktestSession", _FakeWarm)

        cfg = LoopConfig(provider="openrouter", evolution_mode="ga",
                         bt_engine_mode="warm", max_generations=1)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(cfg, run_id="branchrun", state=st)
        assert called["ga"] is True
        assert summary["stop_reason"] == "ga_test"
        st.close()

    def test_run_loop_hillclimb_unaffected(self, monkeypatch, tmp_path):
        # 기본(hillclimb)은 GA 분기를 타지 않고 기존 세대 루프를 돈다(회귀 가드).
        monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
        monkeypatch.setattr(
            L, "_generate_pair",
            lambda provider, cfg, rid, gen, fb, history_summary=None,
            sell_feedback=None, base_buy_code=None, base_sell_code=None: {
                "status": "ok",
                "buy_name": f"AILOOP_{rid}_g{gen}_buy",
                "sell_name": f"AILOOP_{rid}_g{gen}_sell",
                "tokens": 10,
            },
        )
        monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
        monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
        monkeypatch.setattr(
            L, "run_backtest_for",
            lambda cfg, b, s: L.BacktestOutcome(False, "error", None, None, "no trades"),
        )

        # run_ga_loop이 절대 호출되지 않아야 한다.
        import ai_strategy_loop.controller.ga as GAmod

        def _boom(*a, **k):
            raise AssertionError("hillclimb 모드에서 run_ga_loop이 호출되면 안 됨")

        monkeypatch.setattr(GAmod, "run_ga_loop", _boom)

        cfg = LoopConfig(provider="openrouter", evolution_mode="hillclimb",
                         bt_engine_mode="cold", max_generations=2,
                         cost_cap_generations=100, cost_cap_tokens=None)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(cfg, run_id="hcrun", state=st)
        assert summary["generations"] == 2
        assert "max_generations" in summary["stop_reason"]
        st.close()
