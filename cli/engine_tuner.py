"""엔진 수 자동 최적화 — CPU/메모리 기반 권장."""

import os
import platform


def get_system_info() -> dict:
    """Return basic system resource info.

    Uses psutil if available; falls back to os.cpu_count() only.

    Returns:
        {
            'cpu_count': int,
            'memory_total_gb': float,
            'memory_available_gb': float,
            'platform': str,
        }
    """
    cpu_count = os.cpu_count() or 1
    plat = platform.system()

    try:
        import psutil
        mem = psutil.virtual_memory()
        memory_total_gb = mem.total / (1024 ** 3)
        memory_available_gb = mem.available / (1024 ** 3)
    except ImportError:
        memory_total_gb = 0.0
        memory_available_gb = 0.0

    return {
        "cpu_count": cpu_count,
        "memory_total_gb": round(memory_total_gb, 2),
        "memory_available_gb": round(memory_available_gb, 2),
        "platform": plat,
    }


def recommend_engine_count(total_codes: int = 0) -> dict:
    """Recommend engine count based on CPU count.

    Rules:
        cpu_count <= 2  -> 1
        cpu_count <= 4  -> 2
        cpu_count <= 8  -> max(2, cpu_count - 2)
        cpu_count > 8   -> min(cpu_count - 2, 8)   (cap at 8)

    If total_codes > 0 and total_codes < recommended, use total_codes
    (no point having more engines than codes).

    Returns:
        {'recommended': int, 'cpu_count': int, 'reason': str}
    """
    cpu_count = os.cpu_count() or 1

    if cpu_count <= 2:
        recommended = 1
        reason = f"CPU {cpu_count}개 — 단일 엔진 권장"
    elif cpu_count <= 4:
        recommended = 2
        reason = f"CPU {cpu_count}개 — 엔진 2개 권장"
    elif cpu_count <= 8:
        recommended = max(2, cpu_count - 2)
        reason = f"CPU {cpu_count}개 — 엔진 {recommended}개 권장 (cpu-2)"
    else:
        recommended = min(cpu_count - 2, 8)
        reason = f"CPU {cpu_count}개 — 엔진 {recommended}개 권장 (상한 8)"

    if total_codes > 0 and total_codes < recommended:
        reason += f" → 종목 수({total_codes})가 더 적어 {total_codes}개로 조정"
        recommended = total_codes

    return {
        "recommended": recommended,
        "cpu_count": cpu_count,
        "reason": reason,
    }


def estimate_memory_per_engine(is_tick: bool) -> float:
    """Estimate memory usage per engine in MB.

    Args:
        is_tick: True for tick data (heavier), False for minute data.

    Returns:
        Estimated MB per engine as float.
    """
    return 500.0 if is_tick else 200.0


def check_resources(engine_count: int, is_tick: bool) -> dict:
    """Check whether the system has enough resources for the requested engine count.

    Returns:
        {
            'status': 'ok' | 'warning',
            'message': str,
            'recommended': int,
        }
    """
    info = get_system_info()
    available_mb = info["memory_available_gb"] * 1024
    per_engine_mb = estimate_memory_per_engine(is_tick)
    required_mb = per_engine_mb * engine_count

    rec = recommend_engine_count()["recommended"]

    if available_mb <= 0:
        # psutil not available — cannot check memory, trust CPU recommendation
        return {
            "status": "ok",
            "message": "메모리 정보 없음 — CPU 기반 권장값 사용",
            "recommended": rec,
        }

    if required_mb <= available_mb:
        return {
            "status": "ok",
            "message": (
                f"엔진 {engine_count}개 × {per_engine_mb:.0f}MB"
                f" = {required_mb:.0f}MB (가용: {available_mb:.0f}MB)"
            ),
            "recommended": engine_count,
        }

    # Not enough memory — find how many engines fit
    fitting = max(1, int(available_mb // per_engine_mb))
    fitting = min(fitting, rec)
    return {
        "status": "warning",
        "message": (
            f"메모리 부족 — 필요 {required_mb:.0f}MB, 가용 {available_mb:.0f}MB."
            f" 엔진 {fitting}개로 줄이기를 권장"
        ),
        "recommended": fitting,
    }
