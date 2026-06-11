"""V5 슬리피지 스트레스 advisory CLI.

per-trade 백테스트 결과 CSV(들)만 읽어 틱 슬리피지 + 추가 수수료(bps) 시나리오별
손익 민감도 리포트를 stdout 요약 + JSON 파일로 출력한다. **DB 접근 금지**(--run-id
없음), 엔진/하드게이트/런타임 플래그 무수정 — 순수 분석 스크립트.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.slippage_stress_report \
      --csv <결과1.csv> [--csv <결과2.csv>] [--csv a.csv,b.csv] \
      --out <report.json> [--ticks 0,1,2,3] [--fee-bps 0,5,10] [--betting 5]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_strategy_loop.fitness.slippage_stress import stress_report_from_csvs


def _parse_csv_args(values) -> list:
    """--csv 반복 + 항목별 쉼표 구분을 모두 허용해 경로 목록으로 푼다."""
    paths = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                paths.append(part)
    return paths


def _parse_number_list(text: str, cast) -> list:
    """'0,1,2' 형태 문자열을 cast 적용한 숫자 목록으로 푼다."""
    return [cast(p.strip()) for p in str(text).split(",") if p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="슬리피지 스트레스 advisory 리포트 (CSV 읽기 전용, DB 접근 없음)"
    )
    ap.add_argument(
        "--csv",
        action="append",
        required=True,
        help="per-trade 결과 CSV 경로 (반복 지정 또는 쉼표 구분)",
    )
    ap.add_argument("--out", required=True, help="리포트 JSON 저장 경로")
    ap.add_argument("--ticks", default="0,1,2", help="틱 수 목록 (쉼표, 기본 0,1,2)")
    ap.add_argument("--fee-bps", default="0,5", help="추가 수수료 bps 목록 (쉼표, 기본 0,5)")
    ap.add_argument("--betting", default=None, help="종목당 배팅(백만원 단위, 참고 메타)")
    args = ap.parse_args()

    csv_paths = _parse_csv_args(args.csv)
    report = stress_report_from_csvs(
        csv_paths,
        tick_levels=_parse_number_list(args.ticks, int),
        extra_fee_bps=_parse_number_list(args.fee_bps, float),
        betting=args.betting,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"[slippage_stress] trades={report['trade_count']} "
        f"skipped={report['skipped_trades']} "
        f"base_profit={report['base_total_profit']:,.0f}"
    )
    for sc in report["scenarios"]:
        retention = sc["profit_retention_ratio"]
        retention_txt = f"{retention * 100:.1f}%" if retention is not None else "n/a"
        breakeven = sc["breakeven_tick"]
        breakeven_txt = f"{breakeven:.2f}" if breakeven is not None else "n/a"
        print(
            f"  tick={sc['tick']} fee={sc['fee_bps']:g}bps "
            f"profit={sc['total_profit']:,.0f} retention={retention_txt} "
            f"mdd={sc['mdd_amount']:,.0f} breakeven_tick={breakeven_txt}"
        )
    print(f"[slippage_stress] saved → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
