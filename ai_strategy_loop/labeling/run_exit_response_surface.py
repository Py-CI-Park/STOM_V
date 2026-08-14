"""S6 — 매도축 응답면: "지금 값이 고원 위인가, 절벽 끝인가".

## 왜 Optuna 200 시행이 아닌가

로드맵 §3 단계 3 은 "매도축 Optuna 200 시행"으로 적혀 있었다. 실제로 재어 보니
그 형태로는 못 돌린다:

| | 조합 | 엔진 소요 |
|---|---:|---:|
| 매도축 `vars[25..31]` 전수 | 46,875 | 1년 |
| Optuna 200 시행 (확장 구간 엔진) | 200 | **약 50시간** |

그런데 목적은 "최고값 찾기"가 아니라 **"지금 값이 고원 위인지 확인"**이다
(로드맵 §2.4). 그 확인은 격자 두 축(무장 × 되돌림)이면 충분하고, 그 격자는
**지도에서 초 단위로** 계산된다 — 챔피언 진입 344건 위에서 트레일링을 그대로
시뮬레이션하기 때문이다(`trailing.py` 는 근사가 아니라 계산이다).

그래서 이렇게 한다:

    1. 지도에서 36셀(무장 6 × 되돌림 6) 응답면을 통째로 낸다   ← 초 단위
    2. 고원/절벽을 판정한다                                    ← 이 러너
    3. 고원 최고 셀만 엔진으로 확인한다                        ← 1~2런

Optuna 를 안 쓰는 것이 아니라, **Optuna 가 답할 수 없는 질문(이웃이 평평한가)을
격자가 답한다**. 시행 수를 200 → 36 으로 줄이면서 선택 편의도 함께 줄인다.

사용:
    python -m ai_strategy_loop.labeling.run_reproduction_gate \\
        --out-name design_v4 --grid wide --tag _wide
    python -m ai_strategy_loop.labeling.run_exit_response_surface --out-name design_v4
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys

from ai_strategy_loop.controller import response_surface as rs

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def load_cells(out_name: str, tag: str) -> tuple[list[dict], dict]:
    path = os.path.join(_LABEL_ROOT, out_name, f"_reproduction_gate{tag}.json")
    if not os.path.exists(path):
        raise SystemExit(
            f"격자 게이트가 없다: {path}\n"
            f"  먼저: python -m ai_strategy_loop.labeling.run_reproduction_gate "
            f"--out-name {out_name} --grid wide --tag {tag}")
    with open(path, "r", encoding="utf-8") as handle:
        gate = json.load(handle)
    return gate.get("cells", []), gate


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--tag", default="_wide")
    parser.add_argument("--metric", default="expectancy_pct",
                        choices=("expectancy_pct", "day_mean_pct"))
    parser.add_argument("--retain", type=float, default=rs.DEFAULT_RETAIN,
                        help="이웃이 중심의 이 배수 이상이면 평평하다고 본다")
    args = parser.parse_args()

    cells, gate = load_cells(args.out_name, args.tag)
    report = rs.analyze(cells, metric=args.metric, retain=args.retain)
    if not report.get("available"):
        raise SystemExit(f"응답면을 만들 수 없다: {report.get('reason')}")

    print(f"=== 매도축 응답면 (격자 {gate.get('grid')} · 진입 {gate.get('entry_positions')}건) ===")
    print(f"지표 {args.metric} · 고원 기준 이웃 유지율 {args.retain:.0%}\n")
    print(rs.render_ascii(report))

    counts = report["verdict_counts"]
    print(f"\n판정 분포: " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    best, flat = report["best"], report["best_plateau"]
    print(f"\n최고 셀     {best['rule']:<28} {best[args.metric]:+.4f}%  [{best['verdict']}]")
    if flat:
        print(f"고원 최고   {flat['rule']:<28} {flat[args.metric]:+.4f}%  "
              f"이웃최소 {flat['neighbour_min']:+.4f}% (유지율 {flat['retention']:.0%})")
    if report["overfit_gap"] is not None:
        print(f"\n★ 과최적 격차 {report['overfit_gap']:+.4f}%p — 최고값을 채택하면 "
              f"이만큼이 표본 밖에서 사라질 위험이다.")
    print(f"\n권고: {report['recommendation']}")

    out_path = os.path.join(_LABEL_ROOT, args.out_name,
                            f"_exit_response_surface{args.tag}.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "grid": gate.get("grid"),
            "entry_positions": gate.get("entry_positions"),
            "ascii": rs.render_ascii(report),
            **{k: v for k, v in report.items() if k != "points"},
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
