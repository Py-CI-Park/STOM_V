"""Condition Passport 자동 생성 (T1.4) — 격자 시드용 md 문서 렌더러.

정본 필드 규약은 기존 passport
(``docs/research/condition_research/condition_passports/rr8_0_cap_max_2500.md``)
를 따른다: 표에 condition_id / human_name / role / buy_strategy_id /
sell_strategy_id / buy_code_sha256 / sell_code_sha256 / prior_profit /
prior_mdd / prior_trades / promotion_status, 그리고 ``## Core hypothesis`` 와
Buy/Sell full code 펜스 섹션.

격자 시드는 백테스트 전 산출물이므로 prior_* 는 기본 ``n/a`` 로 두고, 러너가
결과를 낸 뒤 갱신 렌더를 다시 호출한다. promotion_status 는 연구 레인 고정값
``research_only / not_promoted`` 만 낸다 (승격 권한 로직 접근 금지 규약).
"""

from __future__ import annotations

from typing import Optional, Union

from ai_strategy_loop.seeds.lattice import SeedRecord, seed_condition_id

# 연구 레인 고정 상태값 — 이 모듈은 다른 상태를 낼 수 없다.
PROMOTION_STATUS = "research_only / not_promoted"
PASSPORT_ROLE = "lattice_seed"

_PASSPORT_TEMPLATE = """# Condition Passport — {human_name}

| Field | Value |
|---|---|
| condition_id | `{condition_id}` |
| human_name | `{human_name}` |
| role | `{role}` |
| buy_strategy_id | `{buy_strategy_id}` |
| sell_strategy_id | `{sell_strategy_id}` |
| buy_code_sha256 | `{buy_sha256}` |
| sell_code_sha256 | `{sell_sha256}` |
| prior_profit | `{prior_profit}` |
| prior_mdd | `{prior_mdd}` |
| prior_trades | `{prior_trades}` |
| promotion_status | `{promotion_status}` |

## Core hypothesis

{hypothesis}

## Buy condition full code

```python
{buy_code}
```

## Sell condition full code

```python
{sell_code}
```
"""


def _default_hypothesis(seed: SeedRecord) -> str:
    """시드 메타에서 기본 가설 문장을 만든다 (커버리지 지도 측정용 맥락 포함)."""
    params = ", ".join(f"{k}={v}" for k, v in sorted(seed.params.items()))
    return (
        f"격자 시드 — 셀 `{seed.cell_id}` × 패밀리 `{seed.family}` "
        f"(params: {params}). 첫 돌파/활성 계열 커버리지 지도 측정용 시드로, "
        f"셀당 train 거래 >= 300건 목표의 완화 임계 기본값을 쓴다. "
        f"생성 사유: `{seed.created_reason}`."
    )


def passport_condition_id(seed: SeedRecord) -> str:
    """시드의 정본 condition_id 를 돌려준다.

    포맷 단일 출처인 :func:`ai_strategy_loop.seeds.lattice.seed_condition_id` 에
    위임한다. created_reason 은 별도 사유 태그라서 custom 값이어도 condition_id
    는 셀·패밀리 기반 정본 포맷을 유지한다.
    """
    return seed_condition_id(seed.cell_id, seed.family)


def passport_filename(seed: SeedRecord) -> str:
    """passport md 파일명을 돌려준다 (셀·패밀리 결정론 조합, ASCII)."""
    return f"{seed.cell_id}__{seed.family}.md"


def render_passport(
    seed: SeedRecord,
    hypothesis: Optional[str] = None,
    prior_profit: Union[str, int, float] = "n/a",
    prior_mdd: Union[str, int, float] = "n/a",
    prior_trades: Union[str, int] = "n/a",
) -> str:
    """격자 시드의 Condition Passport md 전문을 렌더한다.

    Args:
        seed: 격자 시드 레코드 (buy/sell 코드와 sha 포함).
        hypothesis: Core hypothesis 본문 (None 이면 시드 메타에서 자동 생성).
        prior_profit: 사전 손익 (백테스트 전이면 기본 ``n/a``).
        prior_mdd: 사전 MDD.
        prior_trades: 사전 거래수.

    Returns:
        passport md 문자열 (필수 필드 표 + 가설 + Buy/Sell 코드 펜스).
    """
    return _PASSPORT_TEMPLATE.format(
        condition_id=passport_condition_id(seed),
        human_name=f"Lattice_{seed.cell_id}_{seed.family}",
        role=PASSPORT_ROLE,
        buy_strategy_id=f"LATTICE_{seed.cell_id}_{seed.family}_B",
        sell_strategy_id=f"LATTICE_{seed.cell_id}_{seed.family}_S",
        buy_sha256=seed.buy_sha256,
        sell_sha256=seed.sell_sha256,
        prior_profit=prior_profit,
        prior_mdd=prior_mdd,
        prior_trades=prior_trades,
        promotion_status=PROMOTION_STATUS,
        hypothesis=hypothesis if hypothesis is not None else _default_hypothesis(seed),
        buy_code=seed.buy_code,
        sell_code=seed.sell_code,
    )
