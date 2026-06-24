"""TMAP 재백테 게이트 (refine_gate) — 사후슬라이스 착시 차단의 진실 게이트.

근거(하드교훈 a): **사후 슬라이스 ≠ 추출 가능 엣지.** 백테 결과를 사후에 필터로
쪼개 흑자 포켓을 찾아도(예: min 중형주 포켓 in-sample +1.07M), 그 조건을 *진입규칙*
으로 넣어 재백테하면 거래셋이 바뀌어(선택편향) 부호가 반전한다(재백테 −1.15M).
→ 채택 전 반드시 *재백테*가 진실을 말한다. 이 모듈이 그 게이트다.

계층:
  - P0a: `decide(in_sample_lift, rebacktest_profit)` — 순수 판정 로직(백테 미호출).
         게이트 *로직 자체*가 옳은지 오프라인 픽스처로 결정론 검증.
  - P0b: `gate_candidate(...)` — 실존 드라이버(claude_candidate_batch_eval) 배선해
         *새* 후보를 실제 재백테로 흑/적 판정(별도 추가, 해금 게이트).

분석/연구 전용 — 엔진·하드게이트·backtest/graph 무수정.
"""
from __future__ import annotations

from typing import Optional, Tuple

# 재백테 흑자로 인정할 최소 손익(원). "소멸"(near-zero) 후보도 기각하려면 >0.
# 0이면 순수 부호 게이트. 노이즈 마진은 P0b(라이브 재백테)에서 별도로 다룬다.
DEFAULT_MIN_REBACKTEST_PROFIT = 0.0


def decide(
    in_sample_lift: Optional[float],
    rebacktest_profit: Optional[float],
    *,
    min_rebacktest_profit: float = DEFAULT_MIN_REBACKTEST_PROFIT,
) -> Tuple[bool, str]:
    """재백테 결과로 후보 채택/기각을 판정한다 (순수 함수 — 백테 미호출).

    핵심 규율(하드교훈 a): in-sample(사후 슬라이스)에서 좋아 보여도, *재백테*가
    흑자를 재현하지 못하면(부호 반전/소멸) 기각한다. 진실은 재백테에 있다.

    Args:
        in_sample_lift: 사후 슬라이스/in-sample 손익(진단·사유용). None이면 결측.
        rebacktest_profit: *재백테* 손익(판정의 진실원). None이면 결측.
        min_rebacktest_profit: 재백테 흑자 최소 임계(기본 0 = 순수 부호 게이트).

    Returns:
        (passed, reason). passed=True는 "재백테가 엣지를 재현 → 채택".
    """
    if rebacktest_profit is None:
        return (False, "결측: rebacktest_profit 없음 — 재백테 없이는 채택 불가(게이트 규율)")

    # 재백테가 흑자를 재현 → 채택. (in-sample은 진실원이 아님 — 재백테가 진실.)
    if rebacktest_profit > min_rebacktest_profit:
        deg = ""
        if in_sample_lift is not None and in_sample_lift > 0:
            ratio = rebacktest_profit / in_sample_lift
            deg = f" (재백테/insample={ratio:.2f})"
        return (True, f"채택 — 재백테 흑자 {rebacktest_profit:,.0f} 재현{deg}")

    # 재백테가 흑자 미재현 → 기각. 사후슬라이스 착시 패턴을 사유에 명시.
    if in_sample_lift is not None and in_sample_lift > 0:
        return (
            False,
            f"기각 — 사후슬라이스 착시: in-sample +{in_sample_lift:,.0f} → "
            f"재백테 {rebacktest_profit:,.0f} (부호반전/소멸). 추출 가능 엣지 아님(하드교훈 a)",
        )
    return (False, f"기각 — 재백테 비흑자 {rebacktest_profit:,.0f}")


# =====================================================================
# P0b — ★진짜 재백테 게이트 (실존 드라이버 claude_candidate_batch_eval 배선)
#   해금 게이트: 테스트셋에 없던 *새* 후보를 실제 재백테로 흑/적 판정.
#   엔진·하드게이트·backtest/graph 무수정 — 헤드리스 드라이버 재사용.
# =====================================================================

import json as _json  # noqa: E402
import os as _os  # noqa: E402
import re as _re  # noqa: E402
import subprocess as _subprocess  # noqa: E402
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

# [BATCH] gen0 <label> ok profit=1,234,567 mdd=... (claude_candidate_batch_eval stdout)
_BATCH_PROFIT_RE = _re.compile(r"\[BATCH\]\s+gen\d+\s+\S+\s+ok\s+profit=([\-\d,]+)")


def _repo_root() -> _Path:
    return _Path(__file__).resolve().parents[2]


def _evid_gate_dir() -> _Path:
    d = _repo_root() / ".omo/evidence/tmap-walkforward/gate"
    d.mkdir(parents=True, exist_ok=True)
    return d


def materialize_candidate(label: str, buy_code: str, sell_code: str,
                          timeframe: str = "tick") -> Tuple[str, str]:
    """[A3] 재료화 브리지: 후보 코드를 loop_strategies.db 전략명 인덱스로 등록.

    tmap_sweep.py:83-94 기성 경로 재사용(render는 이미 렌더된 코드를 받으므로 생략,
    validate_rendered 가드 + save_strategy_to_db). 반환 (buy_name, sell_name).
    """
    import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415
    from ai_strategy_loop.tmap.template import validate_rendered  # noqa: PLC0415
    from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415

    errs = validate_rendered(buy_code, sell_code, timeframe)
    if errs:
        raise ValueError(f"재료화 가드 실패: {errs}")
    db = str(bootstrap.LOOP_DB_STRATEGY)
    safe = _re.sub(r"[^A-Za-z0-9_]", "_", label)[:40]
    buy_name, sell_name = f"GATE_{safe}_B", f"GATE_{safe}_S"
    r1 = save_strategy_to_db(db, buy_name, buy_code, "buy")
    r2 = save_strategy_to_db(db, sell_name, sell_code, "sell")
    if r1.get("status") != "ok" or r2.get("status") != "ok":
        raise RuntimeError(f"전략 저장 실패: {r1} {r2}")
    return buy_name, sell_name


def _rebacktest_once(label: str, buy_name: str, sell_name: str,
                     config_path: str, run_id: str, timeout: int = 1200) -> Optional[float]:
    """claude_candidate_batch_eval 1회 호출 → stdout에서 profit 파싱(원). 실패시 None."""
    pairs_path = _evid_gate_dir() / f"pairs_{run_id}.json"
    pairs_path.write_text(
        _json.dumps([{"label": label, "buy": buy_name, "sell": sell_name}], ensure_ascii=False),
        encoding="utf-8")
    env = dict(_os.environ, PYTHONUTF8="1")
    try:
        p = _subprocess.run(
            [_sys.executable, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
             "--pairs-json", str(pairs_path), "--config-json", config_path, "--run-id", run_id],
            cwd=str(_repo_root()), capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env)
    except Exception as exc:  # noqa: BLE001
        return None
    out = (p.stdout or "") + (p.stderr or "")
    m = _BATCH_PROFIT_RE.search(out)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def gate_candidate(buy_code: str, sell_code: str, config_path: str, *,
                   label: str, timeframe: str = "tick",
                   in_sample_lift: Optional[float] = None,
                   repeats: int = 1, noise_margin: float = 0.0,
                   run_id_prefix: str = "gate") -> dict:
    """★해금 게이트: 새 후보를 실제 재백테로 흑/적 판정.

    서브스텝0(거짓기각 가드)을 repeats로 표현 — repeats=1은 결정론 가정(a),
    repeats>=2는 비결정론 대비 반복 안정성 검사(b). 보수적으로 min(profit)으로 게이트.

    Args:
        buy_code/sell_code: 렌더된 후보 코드.
        config_path: 재백테 config-json(스모크/전체기간). bt_timeframe 자동 반영.
        label: 후보 라벨(전략명 재료화에 사용).
        in_sample_lift: 사후 슬라이스 손익(decide 진단용).
        repeats: 재백테 반복 횟수(>=2면 부호안정+안정마진 검사).
        noise_margin: (b)분기 안정마진(|profit|이 이보다 커야 신뢰).

    Returns:
        {passed, profit, profits, deterministic, reason}.
    """
    # config의 timeframe 우선.
    try:
        cfg = _json.loads(_Path(config_path).read_text(encoding="utf-8"))
        timeframe = cfg.get("bt_timeframe", timeframe)
    except Exception:  # noqa: BLE001
        pass

    buy_name, sell_name = materialize_candidate(label, buy_code, sell_code, timeframe)
    profits = []
    for k in range(max(1, repeats)):
        prof = _rebacktest_once(label, buy_name, sell_name, config_path,
                                f"{run_id_prefix}_{_re.sub(r'[^A-Za-z0-9_]', '_', label)[:30]}_{k}")
        profits.append(prof)
    valid = [p for p in profits if p is not None]
    if not valid:
        return {"passed": False, "profit": None, "profits": profits,
                "deterministic": None, "reason": "기각 — 재백테 실패(드라이버 결과 없음)"}

    deterministic = (len({round(p) for p in valid}) == 1) if len(valid) >= 2 else None
    # 보수적: 노이즈하 거짓통과 방지 위해 최악(min) profit으로 게이트.
    gate_profit = min(valid)

    # (b)분기 안정마진: 반복시 부호 불안정하면 거짓기각/통과 위험 → 신뢰불가.
    if len(valid) >= 2 and noise_margin > 0:
        signs = {1 if p > 0 else (-1 if p < 0 else 0) for p in valid}
        if len(signs) > 1 or min(abs(p) for p in valid) < noise_margin:
            return {"passed": False, "profit": gate_profit, "profits": profits,
                    "deterministic": deterministic,
                    "reason": f"기각 — 재백테 부호 불안정/마진부족(profits={valid}, margin={noise_margin:,.0f})"}

    passed, reason = decide(in_sample_lift, gate_profit)
    det_tag = "" if deterministic is None else f" [결정론={deterministic}]"
    return {"passed": passed, "profit": gate_profit, "profits": profits,
            "deterministic": deterministic, "reason": reason + det_tag}