"""alpha_lab v3 P2 — EV 채굴 + 전이 판정 (봉인 preregistration_v3 50d3d38a).

사전등록 3점 세트를 registry.verify_seal로 확인한 뒤 실행한다:
  - preregistration_v3.json (50d3d38a...) - adoption_ev/hillclimb/ledger 봉인.
  - v3_feature_annex.json   (568dc061...) - 파생 18항 패리티 통과 목록.
  - preregistration_v2.json (dcac7492...) - L3 라벨 정의·sample_grid(60일 MVP) 승계.

흐름:
  1) v3_dataset_receipt_{2023,2024}_c*.json 9개 청크 병합 + npz 독립 재검수
     -> v3_dataset_receipt.json.
  2) 43피처(25 stored + 18 derived) 전체 60일 로드 -> mine_rules(L3_pos,
     max_depth=4, min_samples_leaf=1000, seed=20260707, 서브셋: 전체 1회 +
     무작위 22피처 6회) - 리프 전수를 n_trials 원장(V3M)에 정직 합산.
  3) adopt_by_ev(봉인 adoption_ev 그대로: CI_low(mean L3_net)>0, 연도별
     EV>0, support>=1000, FDR 0.05)로 EV 채택.
  4) 채택 리프만 measure_transition_ev로 전이(FALSE->TRUE onset) 재측정 -
     일평균 전이율 봉인 예산 [5,60] 필터.
  5) 최종 후보(=채택 그리고 전이예산내) >=3 -> go, 아니면 partial(+PIVOT
     근거 수치) -> v3_mining_report.json + v3_candidates.json.

엔진 백테 0회 / tick DB 접근 0회(캐시 npz만 read) / print 금지(logging) /
git 커밋 없음. 실행: python scripts/alpha_v3_p2_ev_mining.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from alpha_lab import registry  # noqa: E402
from alpha_lab.dataset.cache import feature_names_of, load_shards  # noqa: E402
from alpha_lab.mining import adopt_by_ev, mine_rules  # noqa: E402
from alpha_lab.mining.transition import (  # noqa: E402
    TRANSITION_RATE_BUDGET,
    measure_transition_ev,
    series_ids_from,
)
from cli.alpha_common import (  # noqa: E402
    DEFAULT_RUN_DIR_V3,
    LEDGER_NAME,
    load_verified_prereg,
    write_receipt,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s : %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("alpha_v3_p2_ev_mining")

# ------------------------------------------------------------- 봉인 상수
RUN_DIR = DEFAULT_RUN_DIR_V3
PREREG_V3_NAME = "preregistration_v3.json"
ANNEX_V3_NAME = "v3_feature_annex.json"
PREREG_V2_NAME = "preregistration_v2.json"

PREREG_V3_SHA = "50d3d38ae9ee999d80c06a35f9745149ad10af5bd44e903ef754289a6babfa88"
ANNEX_V3_SHA = "568dc06156d433afa8e72f3f8d27794cb574d063670b6009fe68ce6604d84003"
PREREG_V2_SHA = "dcac74927466f6383d3119d1b5905f4d0733f300de0987b95612d5e9b794444b"

DATASET_CHUNK_GLOB = "v3_dataset_receipt_????_c*.json"
MERGED_RECEIPT_NAME = "v3_dataset_receipt.json"
REPORT_NAME = "v3_mining_report.json"
CANDIDATES_NAME = "v3_candidates.json"

# 채굴 파라미터 (오케스트레이터 지시 — 봉인 support_min=1000 정합).
MAX_DEPTH = 4
MIN_SAMPLES_LEAF = 1000
MINING_SEED = 20260707
N_RANDOM_SUBSETS = 6
RANDOM_SUBSET_SIZE = 22

# EV 채택 게이트(adopt_by_ev 기본값과 동일 — 명시적으로 재기재해 단일 원천을
# 여기서도 눈으로 확인 가능하게 한다. 실제 값은 alpha_lab.mining.ev_adopt의
# SEALED_* 상수가 유일 원천이다).
EV_N_BOOT = 1000
EV_SEED = 20260707
EV_SUPPORT_MIN = 1000
EV_FDR_Q = 0.05

# 전이 재측정(측정만 — 채택 게이트 아님) — 후보별 시드는 seed+i 관례.
TRANSITION_SEED = 20260707
TRANSITION_N_BOOT = 1000

FINAL_CANDIDATES_GO_MIN = 3

EXIT_OK = 0
EXIT_PIVOT = 2  # 정상 완료 + 최종 후보 <3 (오케스트레이터 PIVOT 판단 필요).
EXIT_SEAL = 3
EXIT_INPUT = 4


def _verify_three_seals() -> Optional[Dict[str, Any]]:
    """3점 세트 registry.verify_seal + 하드코딩 sha 이중 대조."""
    try:
        prereg_v3, sha_v3 = load_verified_prereg(RUN_DIR, PREREG_V3_NAME)
        annex, sha_annex = load_verified_prereg(RUN_DIR, ANNEX_V3_NAME)
        prereg_v2, sha_v2 = load_verified_prereg(RUN_DIR, PREREG_V2_NAME)
    except registry.SealViolation as exc:
        logger.error("봉인 불일치 - 비정상 종료: %s", exc)
        return None
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("봉인 문서 적재 실패 - 비정상 종료: %s", exc)
        return None
    checks = {
        "preregistration_v3.json": (sha_v3, PREREG_V3_SHA),
        "v3_feature_annex.json": (sha_annex, ANNEX_V3_SHA),
        "preregistration_v2.json": (sha_v2, PREREG_V2_SHA),
    }
    for name, (actual, expected) in checks.items():
        if actual != expected:
            logger.error(
                "%s sha 불일치(이중 대조): 실제 %s != 지시 %s", name, actual, expected
            )
            return None
    logger.info(
        "봉인 3점 세트 확인 완료: v3=%s annex=%s v2=%s",
        sha_v3[:8], sha_annex[:8], sha_v2[:8],
    )
    return {"prereg_v3": prereg_v3, "annex": annex, "prereg_v2": prereg_v2,
            "sha_v3": sha_v3, "sha_annex": sha_annex, "sha_v2": sha_v2}


def _merge_dataset_receipts(sha_v2: str, sha_annex: str, sealed_days: Dict[str, List[str]]) -> Dict[str, Any]:
    """9개 청크 영수증 병합 - v2_merge_receipt.py(선행 세션) 관례 그대로."""
    chunk_paths = sorted(RUN_DIR.glob(DATASET_CHUNK_GLOB))
    if not chunk_paths:
        raise FileNotFoundError(f"v3 데이터셋 청크 영수증이 없다: {RUN_DIR}")
    sealed_all = [str(d) for key in sorted(sealed_days) for d in sealed_days[key]]

    per_day: Dict[str, Any] = {}
    chunk_meta: List[Dict[str, Any]] = []
    engines: set = set()
    sell_shas: set = set()
    annex_shas: set = set()
    n_feature_cols: set = set()
    derived_feature_lists: set = set()
    label_modes: set = set()
    for path in chunk_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("prereg_sha") != sha_v2:
            raise ValueError(f"청크 {path.name} prereg_sha 불일치")
        if not payload.get("sell_sha_ok", False):
            raise ValueError(f"청크 {path.name} sell_sha_ok 아님")
        if payload.get("annex_sha256") != sha_annex:
            raise ValueError(f"청크 {path.name} annex_sha256 불일치")
        overlap = set(payload["per_day"]) & set(per_day)
        if overlap:
            raise ValueError(f"청크 {path.name} 일자 중복: {sorted(overlap)}")
        engines.add(payload.get("l3_engine"))
        sell_shas.add(payload.get("sell_sha256"))
        annex_shas.add(payload.get("annex_sha256"))
        n_feature_cols.add(payload.get("n_feature_columns"))
        derived_feature_lists.add(tuple(payload.get("derived_features", [])))
        label_modes.add(payload.get("label_mode"))
        per_day.update(payload["per_day"])
        chunk_meta.append({
            "receipt": path.name,
            "n_days": payload["n_days"],
            "n_samples": payload["n_samples"],
            "days_skipped_missing_db": payload.get("days_skipped_missing_db", []),
        })

    coverage_ok = sorted(per_day) == sorted(sealed_all)
    if not coverage_ok:
        missing = sorted(set(sealed_all) - set(per_day))
        extra = sorted(set(per_day) - set(sealed_all))
        raise ValueError(f"일자 커버리지 불일치 missing={missing} extra={extra}")

    per_year: Dict[str, Dict[str, Any]] = {}
    for day in sealed_all:
        year = day[:4]
        bucket = per_year.setdefault(year, {"days_done": 0, "n_samples": 0, "_positives": 0})
        info = per_day[day]
        bucket["days_done"] += 1
        bucket["n_samples"] += int(info["n_samples"])
        bucket["_positives"] += int(info["labels"]["L3_pos"]["positives"])
    for year, bucket in per_year.items():
        positives = bucket.pop("_positives")
        n = bucket["n_samples"]
        bucket["L3_pos"] = {
            "positives": positives,
            "positive_rate": (positives / n) if n else None,
        }

    n_samples = sum(per_day[d]["n_samples"] for d in sealed_all)
    positives_total = sum(per_day[d]["labels"]["L3_pos"]["positives"] for d in sealed_all)
    days_skipped = sorted(d for c in chunk_meta for d in c["days_skipped_missing_db"])

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "prereg_sha": sha_v2,
        "label_mode": next(iter(label_modes)) if len(label_modes) == 1 else sorted(label_modes),
        "sell_sha256": next(iter(sell_shas)) if len(sell_shas) == 1 else sorted(sell_shas),
        "l3_engines_used": sorted(engines),
        "annex_sha256": sha_annex,
        "derived": True,
        "derived_features": list(next(iter(derived_feature_lists))) if len(derived_feature_lists) == 1 else None,
        "derived_window_hhmmss": [90000, 93000],
        "derived_avg": 30,
        "n_feature_columns": next(iter(n_feature_cols)) if len(n_feature_cols) == 1 else sorted(n_feature_cols),
        "source_chunk_receipts": chunk_meta,
        "n_days": len(sealed_all),
        "days": sealed_all,
        "days_skipped_missing_db": days_skipped,
        "n_samples": n_samples,
        "labels": {
            "L3_pos": {
                "n": n_samples,
                "positives": positives_total,
                "positive_rate": (positives_total / n_samples) if n_samples else None,
            }
        },
        "per_year": per_year,
        "verification": {
            "npz_recount_match": None,  # load_shards 이후 채움.
            "coverage_equals_sealed_sample_grid": coverage_ok,
            "chunk_prereg_sha_uniform": True,  # 불일치는 위에서 이미 ValueError.
            "chunk_annex_sha_uniform": True,
            "sell_sha_ok_all_chunks": True,
            "n_feature_columns_uniform_43": n_feature_cols == {43},
            "derived_features_uniform": len(derived_feature_lists) == 1,
            "days_skipped_missing_db_empty": days_skipped == [],
        },
        "per_day": per_day,
    }


def _npz_recount_matches(merged: Dict[str, Any], arrays: Dict[str, np.ndarray]) -> bool:
    """load_shards로 얻은 배열에서 일자별 표본수·L3_pos 양성수를 독립 재계산해 대조."""
    date_arr = np.asarray(arrays["date"])
    pos_arr = np.asarray(arrays["L3_pos"])
    mismatches: List[Dict[str, Any]] = []
    for day in merged["days"]:
        day_mask = date_arr == int(day)
        n = int(day_mask.sum())
        pos = int((pos_arr[day_mask] == 1).sum())
        rec = merged["per_day"][day]
        rec_n = rec["n_samples"]
        rec_pos = rec["labels"]["L3_pos"]["positives"]
        if rec_n != n or rec_pos != pos:
            mismatches.append({"day": day, "receipt": [rec_n, rec_pos], "npz": [n, pos]})
    if mismatches:
        logger.error("npz 재검수 불일치 %d건: %s", len(mismatches), mismatches[:3])
        return False
    logger.info("npz 재검수 %d일 전건 일치", len(merged["days"]))
    return True


def _build_feature_subsets(seed: int, n_features: int) -> List[List[int]]:
    """전체 피처 1회 + 무작위 22피처 서브셋 6회(seed+k, k=1..6) - alpha_mine.py
    feature_subsets()와 동일한 rng 관례(파라미터만 이 P2 지시값으로 변경)."""
    subsets: List[List[int]] = [list(range(n_features))]
    size = min(RANDOM_SUBSET_SIZE, n_features)
    for k in range(1, N_RANDOM_SUBSETS + 1):
        rng = np.random.default_rng(seed + k)
        cols = sorted(int(c) for c in rng.choice(n_features, size=size, replace=False))
        subsets.append(cols)
    return subsets


def _serialize_leaf(leaf: Dict[str, Any], transition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    row = {
        "rule_id": f"V3M-s{leaf['subset_id']:02d}-l{leaf['leaf_id']:03d}",
        **{k: v for k, v in leaf.items() if not str(k).startswith("_")},
    }
    if transition is not None:
        row["transition"] = transition
    return row


def main() -> int:
    started = datetime.now()
    verified = _verify_three_seals()
    if verified is None:
        return EXIT_SEAL
    prereg_v2 = verified["prereg_v2"]
    sha_v2, sha_annex = verified["sha_v2"], verified["sha_annex"]
    sealed_days = prereg_v2.get("sample_grid", {}).get("days")
    if not isinstance(sealed_days, dict) or not sealed_days:
        logger.error("preregistration_v2.json에 sample_grid.days가 없다")
        return EXIT_SEAL

    try:
        merged = _merge_dataset_receipts(sha_v2, sha_annex, sealed_days)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("데이터셋 청크 병합 실패: %s", exc)
        return EXIT_INPUT

    cache_dir = RUN_DIR / "cache"
    try:
        arrays = load_shards(cache_dir, merged["days"])
    except FileNotFoundError as exc:
        logger.error("npz 샤드 결측: %s", exc)
        return EXIT_INPUT
    if not arrays or int(arrays["features"].shape[0]) == 0:
        logger.error("표본 0건 - 입력 부족")
        return EXIT_INPUT

    recount_ok = _npz_recount_matches(merged, arrays)
    merged["verification"]["npz_recount_match"] = recount_ok
    write_receipt(RUN_DIR / MERGED_RECEIPT_NAME, merged)
    if not recount_ok:
        logger.error("npz 재검수 실패 - 병합 영수증만 기록하고 채굴 중단")
        return EXIT_INPUT
    logger.info(
        "병합 영수증 기록 완료: 일수=%d 표본=%d - %s",
        merged["n_days"], merged["n_samples"], RUN_DIR / MERGED_RECEIPT_NAME,
    )

    X = arrays["features"]
    y_pos = arrays["L3_pos"]
    y_net = arrays["L3_net"]
    day_ids = arrays["date"]
    codes = arrays["code"]
    feature_names = feature_names_of(arrays)
    if len(feature_names) != X.shape[1]:
        logger.error("feature_names 수(%d) != features 열수(%d)", len(feature_names), X.shape[1])
        return EXIT_INPUT
    n_samples = int(X.shape[0])

    year_arr = (np.asarray(day_ids) // 10000).astype(int)
    per_year_masks = {int(y): (year_arr == y) for y in sorted(set(year_arr.tolist()))}
    logger.info(
        "데이터셋 로드 완료: n=%d features=%d years=%s",
        n_samples, X.shape[1], sorted(per_year_masks),
    )

    # ------------------------------------------------------------ 2) 채굴
    subsets = _build_feature_subsets(MINING_SEED, X.shape[1])
    leaves = mine_rules(
        X, y_pos, feature_names,
        max_depth=MAX_DEPTH, min_samples_leaf=MIN_SAMPLES_LEAF,
        seed=MINING_SEED, feature_subsets=subsets,
    )
    n_leaves = len(leaves)
    logger.info(
        "mine_rules 완료: 서브셋=%d(전체1+무작위%d) 리프전수=%d",
        len(subsets), N_RANDOM_SUBSETS, n_leaves,
    )

    now = datetime.now()
    batch = f"V3M-evmine-{now.strftime('%Y%m%dT%H%M%S')}"
    ledger_path = RUN_DIR / LEDGER_NAME
    registry.append_trials(
        ledger_path, program="V3M", batch=batch, n=n_leaves, now=now,
        meta={
            "label": "L3_pos", "n_days": merged["n_days"], "n_samples": n_samples,
            "max_depth": MAX_DEPTH, "min_samples_leaf": MIN_SAMPLES_LEAF,
            "seed": MINING_SEED, "n_subsets": len(subsets),
        },
    )
    logger.info("n_trials 원장 V3M 정직 합산: n=%d batch=%s -> %s", n_leaves, batch, ledger_path)

    # --------------------------------------------------------- 3) EV 채택
    ev_results = adopt_by_ev(
        leaves, X, y_net, day_ids,
        n_boot=EV_N_BOOT, seed=EV_SEED, support_min=EV_SUPPORT_MIN, fdr_q=EV_FDR_Q,
        per_year_masks=per_year_masks,
    )
    ev_ci_pos = sum(1 for r in ev_results if r["ci_low"] > 0.0)
    per_year_pass = sum(
        1 for r in ev_results if all(v > 0.0 for v in r["per_year_ev"].values())
    )
    adopted = [r for r in ev_results if r["adopted"]]
    n_adopted = len(adopted)
    logger.info(
        "adopt_by_ev 완료: 리프=%d ci_low>0=%d per_year_pass=%d 채택=%d",
        len(ev_results), ev_ci_pos, per_year_pass, n_adopted,
    )

    # ---------------------------------------------------- 4) 전이 재측정
    series_ids = series_ids_from(day_ids, codes)
    transition_results: List[Optional[Dict[str, Any]]] = []
    for i, leaf in enumerate(adopted):
        try:
            tr = measure_transition_ev(
                X, leaf, y_net, day_ids, series_ids=series_ids,
                n_boot=TRANSITION_N_BOOT, seed=TRANSITION_SEED + i,
                rate_budget=TRANSITION_RATE_BUDGET,
            )
        except ValueError as exc:
            logger.error("측정 실패(리프 %d) - 전이 예산 미판정: %s", i, exc)
            tr = None
        transition_results.append(tr)
    transition_pass = sum(1 for tr in transition_results if tr is not None and tr["rate_in_budget"])
    final_candidate_pairs = [
        (leaf, tr) for leaf, tr in zip(adopted, transition_results)
        if tr is not None and tr["rate_in_budget"]
    ]
    final_candidates = len(final_candidate_pairs)
    logger.info(
        "전이 재측정 완료: 채택리프=%d 예산내(rate_in_budget)=%d 최종후보=%d",
        len(adopted), transition_pass, final_candidates,
    )

    go = final_candidates >= FINAL_CANDIDATES_GO_MIN
    status = "go" if go else "partial"

    # -------------------------------------------------------- 5) 산출물
    ev_adopted_by_key = {(leaf["subset_id"], leaf["leaf_id"]) for leaf in adopted}
    transition_by_key = {
        (leaf["subset_id"], leaf["leaf_id"]): tr
        for leaf, tr in zip(adopted, transition_results)
    }
    all_leaves_serialized = [
        _serialize_leaf(
            leaf,
            transition_by_key.get((leaf["subset_id"], leaf["leaf_id"])),
        )
        for leaf in ev_results
    ]
    candidates_serialized = [
        {**_serialize_leaf(leaf, tr), "rank": rank}
        for rank, (leaf, tr) in enumerate(
            sorted(final_candidate_pairs, key=lambda pair: pair[0]["ev"], reverse=True),
            start=1,
        )
    ]

    pivot_note = (
        f"최종 후보 {final_candidates}건 (>= {FINAL_CANDIDATES_GO_MIN} 필요) - "
        + (
            "GO: P3 힐클라임 시드로 채택 후보를 편입한다."
            if go else
            "PIVOT 검토: 최종 후보가 3 미만이다. 힐클라임(V3H)은 "
            "hillclimb.seeds 봉인값에 따라 ALP_V2SEED_01~10만으로 진행하거나 "
            f"(P2 채택 후보 {n_adopted}건 중 전이예산통과 {final_candidates}건을 "
            "보조 시드로 병기), 0건이면 preregistration_v3.pivot_p5_alt(밴드-생성기+"
            "국소탐색)로 전환할지 오케스트레이터가 판단해야 한다."
        )
    )
    logger.info("판정: %s", pivot_note)

    report = {
        "generated_at": started.isoformat(),
        "program": "alpha_lab_v3_p2",
        "prereg_sha_v3": verified["sha_v3"],
        "annex_sha256": verified["sha_annex"],
        "prereg_sha_v2": verified["sha_v2"],
        "label": "L3_pos (채굴 타겟) / L3_net (EV 타겟)",
        "n_days": merged["n_days"],
        "n_samples": n_samples,
        "n_feature_columns": int(X.shape[1]),
        "feature_names": list(feature_names),
        "years": sorted(per_year_masks),
        "params": {
            "mining": {
                "max_depth": MAX_DEPTH, "min_samples_leaf": MIN_SAMPLES_LEAF,
                "seed": MINING_SEED, "n_subsets": len(subsets),
                "subset_sizes": [len(s) for s in subsets],
            },
            "adoption_ev": {
                "n_boot": EV_N_BOOT, "seed": EV_SEED,
                "support_min": EV_SUPPORT_MIN, "fdr_q": EV_FDR_Q,
            },
            "transition": {
                "n_boot": TRANSITION_N_BOOT, "seed_base": TRANSITION_SEED,
                "rate_budget": list(TRANSITION_RATE_BUDGET),
            },
        },
        "n_leaves": n_leaves,
        "ev_ci_pos": ev_ci_pos,
        "per_year_pass": per_year_pass,
        "n_adopted": n_adopted,
        "transition_pass": transition_pass,
        "final_candidates": final_candidates,
        "go": go,
        "status": status,
        "notes": pivot_note,
        "ledger": {"program": "V3M", "batch": batch, "n": n_leaves, "path": str(ledger_path)},
        "leaves": all_leaves_serialized,
        "elapsed_sec": round((datetime.now() - started).total_seconds(), 3),
    }
    write_receipt(RUN_DIR / REPORT_NAME, report)

    candidates_doc = {
        "generated_at": started.isoformat(),
        "prereg_sha_v3": verified["sha_v3"],
        "final_candidates": final_candidates,
        "go": go,
        "status": status,
        "notes": pivot_note,
        "candidates": candidates_serialized,
    }
    write_receipt(RUN_DIR / CANDIDATES_NAME, candidates_doc)

    logger.info(
        "완료: %s / %s", RUN_DIR / REPORT_NAME, RUN_DIR / CANDIDATES_NAME,
    )
    key_values = {
        "n_leaves": n_leaves,
        "ev_ci_pos": ev_ci_pos,
        "per_year_pass": per_year_pass,
        "n_adopted": n_adopted,
        "transition_pass": transition_pass,
        "final_candidates": final_candidates,
        "go": go,
    }
    logger.info("key_values: %s", json.dumps(key_values, ensure_ascii=False))
    return EXIT_OK if go else EXIT_PIVOT


if __name__ == "__main__":
    sys.exit(main())
