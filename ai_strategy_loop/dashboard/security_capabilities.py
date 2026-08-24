from __future__ import annotations

from enum import StrEnum
from typing import Final


class Capability(StrEnum):
    LOOP_CONTROL = "loop-control"
    SAFE_BACKTEST = "safe-backtest"
    REPLAY_CONTROL = "replay-control"
    STRATEGY_WRITE = "strategy-write"
    DECISION_WRITE = "decision-write"
    PROVIDER_TEST = "provider-test"
    # Manual offline diagnostics/proposals only. Routes under this capability must not
    # start engines, read runtime DB/data, adopt, export, or write protected state.
    RESEARCH_DIAGNOSTIC = "research-diagnostic"
    # v5.13.2 — ChatGPT OAuth 브라우저 로그인 시작. PROVIDER_TEST 와 분리한 이유:
    #   test 는 외부 API 를 실제로 호출(토큰 소비)하지만, login 은 로컬 브라우저를 열고
    #   사용자가 직접 인증한 결과 토큰 파일을 저장할 뿐이다(자격증명이 서버를 거치지 않음).
    #   권한 축을 나눠야 "로그인은 허용, 외부 호출은 차단" 같은 조합이 가능하다.
    PROVIDER_LOGIN = "provider-login"
    FINAL_APPROVAL = "final-approval"


DEFAULT_ON_CAPABILITIES: Final = frozenset(
    {
        Capability.LOOP_CONTROL,
        Capability.SAFE_BACKTEST,
        Capability.REPLAY_CONTROL,
        Capability.RESEARCH_DIAGNOSTIC,
        # 기본 ON. 위협모델: 서버는 루프백에만 바인드하고, 이 경로는 Origin 일치 + 유효
        #   세션 쿠키를 이미 요구한다. 동작은 "사용자 브라우저에서 사용자가 직접 로그인"이
        #   전부이며 서버는 비밀번호를 보지도 저장하지도 않는다. 기본 OFF 로 두면 설정 탭
        #   로그인 버튼이 항상 403 이라 기능 자체가 죽는다(2026-07-28 실측 결함).
        Capability.PROVIDER_LOGIN,
    }
)
CAPABILITY_ENV: Final = {
    Capability.STRATEGY_WRITE: "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
    Capability.DECISION_WRITE: "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
    Capability.PROVIDER_TEST: "STOM_DASHBOARD_ALLOW_PROVIDER_TEST",
    Capability.FINAL_APPROVAL: "STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",
}
HTTP_CAPABILITIES: Final = {
    ("POST", "/bt/run"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/job/cancel"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/job/meta"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/portfolio"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/strategy/validate"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/jobs"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/jobs/{analysis_id}/cancel"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/counterfactual"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/proposals"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/official-pair"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/promotion-gate"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/matrix"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/candidate-runs"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/buy-filters"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/removal-simulate"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/trade-path/region-candidates"): Capability.SAFE_BACKTEST,
    ("GET", "/sim/signals"): Capability.SAFE_BACKTEST,
    # QSP10 도달 지도 — 읽기 전용 탐색이지만 POST 라 분류가 필요하다(미분류는 403).
    ("POST", "/bt/map/slider"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/map/candidate"): Capability.SAFE_BACKTEST,
    ("POST", "/bt/strategy"): Capability.STRATEGY_WRITE,
    ("POST", "/bt/strategy/delete"): Capability.STRATEGY_WRITE,
    ("POST", "/bt/extract_vars"): Capability.STRATEGY_WRITE,
    ("POST", "/record_decision"): Capability.DECISION_WRITE,
    ("POST", "/gpt_auth/test"): Capability.PROVIDER_TEST,
    # 미분류였던 탓에 mutation_unclassified 로 항상 403 이었다(로그인 버튼 무반응 원인).
    #   실재하는 라우트만 싣는다 — 없는 경로를 적어 두면 분류표가 라우트 목록과
    #   어긋나고, 그 어긋남을 test_security_mutations 가 정확히 잡아낸다.
    ("POST", "/gpt_auth/login_start"): Capability.PROVIDER_LOGIN,
    ("POST", "/loop/research-tools/bayesian"): Capability.RESEARCH_DIAGNOSTIC,
    ("POST", "/loop/research-tools/ast"): Capability.RESEARCH_DIAGNOSTIC,
    ("POST", "/loop/research-tools/qmc"): Capability.RESEARCH_DIAGNOSTIC,
    ("POST", "/loop/research-tools/denoise"): Capability.RESEARCH_DIAGNOSTIC,
    ("POST", "/research-program/preregistration/preview"): Capability.RESEARCH_DIAGNOSTIC,
}
