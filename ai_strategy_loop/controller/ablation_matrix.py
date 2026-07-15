"""CL-R06: 2x2 buy/sell attribution matrix (todo 12).

Pure arithmetic over PRE-COMPUTED per-arm metrics. This module does NOT run
backtests, hit the DB, or call any provider -- the caller supplies four
already-evaluated arms (A/B/C/D), all executed on an identical
manifest/profile/seed/cost so the only degree of freedom across arms is
which buy/sell condition was used.

Arm layout (fixed, not configurable -- callers must assemble arms this way):
    A = parent-buy   + parent-sell     (baseline)
    B = candidate-buy + parent-sell    (isolates the buy change)
    C = parent-buy   + candidate-sell  (isolates the sell change)
    D = candidate-buy + candidate-sell (both changes together)

Each arm metrics dict carries at least: profit, mdd, trade_count, daily_freq
(all plain numbers). Arms may instead be ``None`` or ``{'status': 'error'}``
to signal a failed/skipped evaluation -- in that case attribution is refused
entirely (no partial causal claim).

MDD sign convention: 'mdd' is stored as a non-negative drawdown magnitude
(0 == no drawdown, larger == worse). Because "lower MDD is better", every
delta for 'mdd' is computed on the sign-flipped series (t = -mdd, so a
larger t is better, matching profit/trade_count/daily_freq). Concretely:
buy_effect.mdd = A.mdd - B.mdd, sell_effect.mdd = A.mdd - C.mdd, and
interaction.mdd = B.mdd + C.mdd - A.mdd - D.mdd. With this convention a
positive number always means "improvement" for every metric in the matrix.
"""


from __future__ import annotations


REQUIRED_ARM_KEYS = ('A', 'B', 'C', 'D')
REQUIRED_METRIC_KEYS = ('profit', 'mdd', 'trade_count', 'daily_freq')

# Metrics where a smaller raw value is an improvement; their deltas are
# sign-flipped so "positive == better" holds uniformly across the matrix.
_LOWER_IS_BETTER_METRICS = frozenset({'mdd'})


def _arm_is_errored(arm: object) -> bool:
    if arm is None:
        return True
    if isinstance(arm, dict) and arm.get('status') == 'error':
        return True
    return False


def _arm_metrics(arm: dict) -> dict[str, float]:
    return {key: float(arm[key]) for key in REQUIRED_METRIC_KEYS}


def compute_attribution(arms: dict) -> dict:
    """Compute buy_effect, sell_effect, and interaction across a 2x2 arm set.

    arms must contain keys 'A', 'B', 'C', 'D'; each value is either a metrics
    dict (with at minimum REQUIRED_METRIC_KEYS) or a sentinel signalling a
    missing/errored evaluation (None or {'status': 'error'}).

    Returns {'valid': True, 'buy_effect': {...}, 'sell_effect': {...},
    'interaction': {...}} on success, or {'valid': False,
    'reason': 'attribution_invalid', 'missing_arms': [...]} when any arm is
    missing/errored -- in which case no effect numbers are returned.
    """

    arms = arms or {}
    missing_arms = [
        key for key in REQUIRED_ARM_KEYS
        if key not in arms or _arm_is_errored(arms.get(key))
    ]
    if missing_arms:
        return {
            'valid': False,
            'reason': 'attribution_invalid',
            'missing_arms': missing_arms,
        }

    for key in REQUIRED_ARM_KEYS:
        arm = arms[key]
        if not isinstance(arm, dict) or any(metric not in arm for metric in REQUIRED_METRIC_KEYS):
            missing_arms.append(key)
    if missing_arms:
        return {
            'valid': False,
            'reason': 'attribution_invalid',
            'missing_arms': sorted(set(missing_arms)),
        }

    metrics_a = _arm_metrics(arms['A'])
    metrics_b = _arm_metrics(arms['B'])
    metrics_c = _arm_metrics(arms['C'])
    metrics_d = _arm_metrics(arms['D'])

    buy_effect: dict[str, float] = {}
    sell_effect: dict[str, float] = {}
    interaction: dict[str, float] = {}
    for metric in REQUIRED_METRIC_KEYS:
        a, b, c, d = metrics_a[metric], metrics_b[metric], metrics_c[metric], metrics_d[metric]
        if metric in _LOWER_IS_BETTER_METRICS:
            buy_effect[metric] = a - b
            sell_effect[metric] = a - c
            interaction[metric] = b + c - a - d
        else:
            buy_effect[metric] = b - a
            sell_effect[metric] = c - a
            interaction[metric] = d - b - c + a

    return {
        'valid': True,
        'buy_effect': buy_effect,
        'sell_effect': sell_effect,
        'interaction': interaction,
    }
