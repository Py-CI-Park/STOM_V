"""alpha_lab v3 P1 — 파생 18항 패리티 게이트 실행 + v3_feature_annex 봉인.

사전등록(preregistration_v3.json, sha 50d3d38a…)의 P1 게이트를 집행한다:
- 표본: 실DB 2일(20230601, 20240103) x 일별 상위 4종목(결정적 선정).
- 방법 (a): utility.static.add_rolling_data read-only 재적용 스팟 대조.
- 산출: v3_feature_annex.json(alpha_lab.registry.seal) + .sha256 사이드카.
- 엔진 백테 0회 / tick DB mode=ro / print 금지(logging).

실행: python scripts/alpha_v3_p1_parity_gate.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from alpha_lab.dataset.parity import build_annex_payload, run_parity  # noqa: E402
from alpha_lab.registry import seal, verify_seal  # noqa: E402

logger = logging.getLogger("alpha_v3_p1_parity_gate")

# 사전등록 봉인 sha(오케스트레이터 지시값 — verify_seal 통과 후에만 진행).
PREREG_SHA = "50d3d38ae9ee999d80c06a35f9745149ad10af5bd44e903ef754289a6babfa88"
OUT_DIR = (
    REPO_ROOT / "docs" / "research" / "condition_research" / "research_runs"
    / "alpha_lab_v3_20260706"
)
PREREG_PATH = OUT_DIR / "preregistration_v3.json"
ANNEX_PATH = OUT_DIR / "v3_feature_annex.json"
DB_DIR = REPO_ROOT / "_database"

# 표본 규약: 20240103(지시 고정) + 2023년 1일(20230601 — 2023 상반기 중
# 6월 첫 거래일, 1월 표본과 레짐 분리를 위해 결정적으로 선정).
SAMPLE_DAYS = (20230601, 20240103)
CODES_PER_DAY = 4
P1_KILL_MIN_PASSED = 5  # preregistration_v3 feature_space_v3.p1_kill


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s : %(message)s",
        stream=sys.stderr,
    )
    verify_seal(PREREG_PATH, PREREG_SHA)
    logger.info("사전등록 봉인 확인: %s", PREREG_SHA[:8])

    result = run_parity(DB_DIR, SAMPLE_DAYS, codes_per_day=CODES_PER_DAY)
    payload = build_annex_payload(
        result,
        method_extra={
            "sample_days": [str(d) for d in SAMPLE_DAYS],
            "day_selection": (
                "20240103 지시 고정 + 20230601(2023년 6월 첫 거래일 — "
                "1월 표본과 레짐 분리, 결정적)"
            ),
            "preregistration_sha256": PREREG_SHA,
            "engine_backtests": 0,
        },
    )

    annex_sha = seal(payload, ANNEX_PATH)
    sidecar = ANNEX_PATH.with_suffix(".sha256")
    sidecar.write_bytes((annex_sha + "\n").encode("ascii"))

    passed = payload["passed_features"]
    failed = payload["failed_features"]
    min_agreement = min(
        (f["agreement_pct"] for f in passed + failed), default=0.0
    )
    logger.info(
        "annex 봉인 완료: %s sha=%s", ANNEX_PATH.name, annex_sha
    )
    logger.info(
        "passed=%d failed=%d min_agreement=%s rows_total=%d",
        len(passed), len(failed), min_agreement, result["rows_total"],
    )
    summary = {
        "passed_count": len(passed),
        "failed_count": len(failed),
        "min_agreement": min_agreement,
        "annex_sha": annex_sha,
    }
    logger.info("key_values: %s", json.dumps(summary, ensure_ascii=False))
    if len(passed) < P1_KILL_MIN_PASSED:
        logger.warning(
            "p1_kill 조항 발동: 통과 %d < %d — P5-대안(밴드-생성기) 피벗 판단 필요",
            len(passed), P1_KILL_MIN_PASSED,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
