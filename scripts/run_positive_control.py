"""양성대조 판정 리포트 생성기 — 기존 백테스트 산출물 소비 전용 (T5.1).

기존 러너/배치평가가 이미 만들어 둔 결과 JSON(챔피언 metrics)과 결과 CSV
(equity 곡선, 선택)를 읽어 발굴 게이트 재판정 receipt JSON을 출력한다.

**백테스트 실행 자체는 이 스크립트의 범위 밖이다** — 여기서는 어떤
백테스트도 돌리지 않고, 기존 러너 산출물을 소비해 판정만 한다(2026-06-16
진단의 판정 단계 자동화). 판정 로직은
ai_strategy_loop/fitness/positive_control.py(advisory_only)를 재사용한다.

쓰기 정책: --report 로 지정한 receipt JSON 출력 외에는 어떤 파일도 쓰지
않는다(stdout으로는 항상 receipt를 내보낸다).

입력 형태:
  - JSON 경로(복수 가능). 각 파일은 다음 중 하나:
      * 챔피언 엔트리 dict: {"name", "metrics": {...},
        "equity_series"(선택), "result_csv"(선택 — per-trade CSV 경로,
        equity 곡선을 읽어 score 표시에만 사용)}
      * 위 엔트리의 목록(list)
      * {"champions": [...]} 또는 {"results": [...]} 래퍼 dict
      * metric 키가 평평하게 있는 러너 산출물 dict
  - --use-reference-baselines: dashboard/reference_strategies.json의
    인간 검증 우수전략(수익 지표 보유분)을 기준선으로 추가.
  - --gate-config: 발굴 run config JSON(예:
    ai_strategy_loop/state/run_p5_validation_tick_late.json)에서
    mdd_cap/min_trades/min_daily_trades/tpi_gate 필드를 추출해 사용.
    개별 --mdd-cap/--min-trades/--min-daily-trades가 이를 덮어쓴다.

예시:
  python scripts/run_positive_control.py results/champ_a.json results/champ_b.json \
      --gate-config ai_strategy_loop/state/run_p5_validation_tick_late.json \
      --report .omo/evidence/positive_control_receipt.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# repo 루트를 import 경로에 추가 (scripts/ 하위 실행 대비).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai_strategy_loop.fitness.positive_control import (  # noqa: E402
    AUTHORITY,
    evaluate_positive_control,
    load_champion_baselines,
)
from ai_strategy_loop.fitness.score import load_equity_series_from_csv  # noqa: E402

RECEIPT_SCHEMA = "positive_control_receipt_v1"

# --gate-config JSON에서 추출하는 게이트 필드(그 외 필드는 무시).
_GATE_FIELDS = (
    "mdd_cap",
    "min_trades",
    "min_daily_trades",
    "tpi_gate",
    "tpi_gate_enabled",
)


def _load_json(path: Path) -> object:
    """JSON 파일을 읽는다 (BOM 허용). 부재/파싱 실패는 정직 에러."""
    if not path.exists():
        raise FileNotFoundError(f"결과 JSON이 없습니다: {path}")
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _normalize_entries(payload: object, source: Path) -> list:
    """결과 JSON payload를 챔피언 엔트리 목록으로 정규화한다."""
    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict):
        wrapped = payload.get("champions") or payload.get("results")
        entries = wrapped if isinstance(wrapped, list) else [payload]
    else:
        raise ValueError(
            f"지원하지 않는 결과 JSON 형태({type(payload).__name__}): {source}"
        )
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"챔피언 엔트리가 dict가 아닙니다: {source}")
        normalized.append({**entry, "_source": str(source)})
    return normalized


def _attach_equity_from_csv(entry: dict) -> dict:
    """엔트리에 result_csv가 있으면 equity 곡선을 읽어 붙인다(새 dict 반환).

    equity는 score(우상향 R² 표시)에만 영향을 주고 게이트 판정과는 무관하다.
    CSV 부재는 정직 에러(경로를 명시했는데 없으면 침묵하지 않는다).
    """
    csv_path = entry.get("result_csv")
    if not csv_path:
        return entry
    resolved = Path(csv_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"result_csv가 없습니다: {resolved} (champion={entry.get('name', '?')})"
        )
    equity = load_equity_series_from_csv(str(resolved))
    return {**entry, "equity_series": equity}


def _build_gate_config(args: argparse.Namespace) -> dict | None:
    """--gate-config JSON + 개별 CLI 오버라이드로 게이트 dict를 만든다.

    아무것도 지정하지 않으면 None을 돌려 기본 발굴 게이트
    (mdd_cap=20 · min_trades=20 · min_daily_trades=0.05)를 쓴다.
    """
    gate: dict = {}
    if args.gate_config:
        payload = _load_json(Path(args.gate_config))
        if not isinstance(payload, dict):
            raise ValueError(f"--gate-config JSON이 dict가 아닙니다: {args.gate_config}")
        gate = {k: payload[k] for k in _GATE_FIELDS if k in payload}
    overrides = {
        "mdd_cap": args.mdd_cap,
        "min_trades": args.min_trades,
        "min_daily_trades": args.min_daily_trades,
    }
    merged = {**gate, **{k: v for k, v in overrides.items() if v is not None}}
    return merged or None


def build_receipt(args: argparse.Namespace) -> dict:
    """입력 산출물을 모아 양성대조 판정 receipt dict를 만든다."""
    champions: list = []
    inputs: list = []

    for raw in args.results:
        path = Path(raw)
        if path.suffix.lower() == ".csv":
            raise ValueError(
                f"CSV 단독 입력은 판정 불가: {path} — 게이트 지표(cagr/mdd 등)는 "
                "엔진 산출 metrics JSON에서 읽는다(여기서 재계산하지 않음). "
                "metrics JSON의 'result_csv' 필드로 CSV를 연결하세요."
            )
        payload = _load_json(path)
        champions.extend(_normalize_entries(payload, path))
        inputs.append(str(path))

    if args.use_reference_baselines:
        champions.extend(load_champion_baselines(args.baseline_path))
        inputs.append(args.baseline_path or "dashboard/reference_strategies.json")

    champions = [_attach_equity_from_csv(entry) for entry in champions]

    judgement = evaluate_positive_control(
        champions, gate_config=_build_gate_config(args)
    )

    return {
        "schema": RECEIPT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": AUTHORITY,
        "inputs": inputs,
        **judgement,
    }


def _parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "양성대조 판정 리포트 — 기존 백테스트 결과 JSON을 발굴 게이트로 "
            "재판정한다(백테스트 실행 없음, advisory_only)."
        )
    )
    parser.add_argument(
        "results",
        nargs="*",
        help="기존 러너 산출물 JSON 경로들(챔피언 metrics).",
    )
    parser.add_argument(
        "--use-reference-baselines",
        action="store_true",
        help="dashboard/reference_strategies.json의 인간 검증 전략을 기준선으로 추가.",
    )
    parser.add_argument(
        "--baseline-path",
        default=None,
        help="reference_strategies.json 대체 경로(기본: dashboard/ 내 파일).",
    )
    parser.add_argument(
        "--gate-config",
        default=None,
        help="발굴 run config JSON 경로 — mdd_cap/min_trades/min_daily_trades 추출.",
    )
    parser.add_argument("--mdd-cap", type=float, default=None, help="mdd_cap 오버라이드.")
    parser.add_argument("--min-trades", type=int, default=None, help="min_trades 오버라이드.")
    parser.add_argument(
        "--min-daily-trades", type=float, default=None, help="min_daily_trades 오버라이드."
    )
    parser.add_argument(
        "--report",
        default=None,
        help="receipt JSON을 쓸 경로(유일한 파일 쓰기). 미지정 시 stdout만.",
    )
    return parser.parse_args(argv)


def main(argv: list) -> int:
    """진입점. receipt를 stdout(+선택 --report 파일)으로 내보낸다.

    종료코드: 0=gate_healthy, 1=gate_regression_suspected, 2=입력/사용 오류.
    """
    args = _parse_args(argv)
    if not args.results and not args.use_reference_baselines:
        sys.stderr.write(
            "입력이 없습니다 — 결과 JSON 경로 또는 --use-reference-baselines를 "
            "지정하세요.\n"
        )
        return 2
    try:
        receipt = build_receipt(args)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        sys.stderr.write(f"양성대조 실패(정직 에러): {exc}\n")
        return 2

    rendered = json.dumps(receipt, ensure_ascii=False, indent=2)
    sys.stdout.write(rendered + "\n")
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered + "\n", encoding="utf-8")

    return 0 if receipt["verdict"] == "gate_healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
