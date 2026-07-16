"""매도식 D1 측정 — 일 루프(체크포인트) + 원본재현 게이트 + 절-제거 ablation.

봉인(bd5bb3c4 §14) 이행:
- F2: 영향 모집단 = {l3_clause==k} 제한 재채점 — 전 절이 서로소 분할이라
  총 작업 ≈ 은행 1회 규모(재현 1패스 + 자기-절 ablation 1패스, 동일 ctx 공유).
- F9(kill-2): 원본재현 — drop=None 결과가 은행 l3_net·l3_clause·l3_exit 와
  **전수 비트동일**이어야 하며, 불일치 1건이라도 있으면 즉시 예외로 중단한다.
- full-mask 스팟: 전 절 무력화 시 강제캡(0)만 남는지 표본 대조(bad-quote 누출 가드).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.bank import day_list
from alpha_lab.dataset import reader
from alpha_lab.sell_clause_lab import harness

# 봉인 지문(§4 재사용 자산 — 2절 봉인본과 동일 값).
EXPECTED_BANK_SHA = (
    "0b6268e0eff8e73831539aba8ff83b8a02608405269732a33c78565c3bfa22fd")
EXPECTED_BANK_ROWS = 863_446
EXPECTED_LABELED = 862_932

_BANK_COLS = ["code", "day", "off", "t0", "year",
              "l3_net", "l3_labeled", "l3_clause", "l3_exit"]
PART_PREFIX = "sd1_"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_bank_fingerprint(bank_path) -> Dict[str, object]:
    """은행 지문 대조 — sha·행수·labeled 수 전부 봉인값과 일치해야 통과."""
    p = Path(bank_path)
    sha = _sha256_file(p)
    df = pd.read_parquet(p, columns=["l3_labeled"])
    rows = int(len(df))
    labeled = int(df["l3_labeled"].sum())
    ok = (sha == EXPECTED_BANK_SHA and rows == EXPECTED_BANK_ROWS
          and labeled == EXPECTED_LABELED)
    return {"path": str(p), "sha256": sha, "sha_match": sha == EXPECTED_BANK_SHA,
            "rows": rows, "labeled": labeled, "gate_pass": bool(ok)}


def load_bank(bank_path) -> pd.DataFrame:
    """은행 필요 컬럼 로드(read-only 파일) — labeled 행만 측정 대상."""
    df = pd.read_parquet(Path(bank_path), columns=_BANK_COLS)
    return df[df["l3_labeled"]].reset_index(drop=True)


class ReproduceMismatch(RuntimeError):
    """원본재현 게이트 불일치(§14-F9 kill-2) — 측정 진입 금지."""


def _process_code(
    conn, code: str, day: int, sub: pd.DataFrame, engine: str,
) -> Dict[str, np.ndarray]:
    """한 (일, 종목): 재현 게이트(전 온셋) + 자기-절 ablation(발화 온셋만)."""
    rows = reader.load_stock_rows(conn, code)
    t0s = sub["t0"].to_numpy(dtype=np.int64)
    year = int(day) // 10000

    rep, _ = harness.label_drop(rows, list(t0s), year=year, drop=None,
                                engine=engine)
    old_net = sub["l3_net"].to_numpy(dtype=np.float64)
    old_clause = sub["l3_clause"].to_numpy(dtype=np.int64)
    old_exit = sub["l3_exit"].to_numpy(dtype=np.int64)
    bad = (~rep["labeled"]) | (rep["clause"] != old_clause) \
        | (rep["exit_t"] != old_exit) | ~np.isclose(
            rep["net"], old_net, rtol=0.0, atol=0.0, equal_nan=False)
    if bad.any():
        j = int(np.flatnonzero(bad)[0])
        raise ReproduceMismatch(
            f"원본재현 불일치 {int(bad.sum())}건 — 첫 예: code={code} day={day} "
            f"t0={int(t0s[j])} old(clause={int(old_clause[j])}, "
            f"net={old_net[j]!r}, exit={int(old_exit[j])}) "
            f"rep(clause={int(rep['clause'][j])}, net={rep['net'][j]!r}, "
            f"exit={int(rep['exit_t'][j])}, labeled={bool(rep['labeled'][j])})")

    n = len(sub)
    abl_net = np.full(n, np.nan, dtype=np.float64)
    abl_clause = np.full(n, -1, dtype=np.int64)
    abl_exit = np.zeros(n, dtype=np.int64)
    abl_labeled = np.zeros(n, dtype=bool)
    for k in harness.FIRE_CLAUSES:
        m = old_clause == k
        if not m.any():
            continue
        res, _ = harness.label_drop(
            rows, list(t0s[m]), year=year, drop=int(k), engine=engine)
        abl_net[m] = res["net"]
        abl_clause[m] = res["clause"]
        abl_exit[m] = res["exit_t"]
        abl_labeled[m] = res["labeled"]
    return {
        "code": sub["code"].to_numpy(dtype="U6"),
        "day": np.full(n, day, dtype=np.int32),
        "off": sub["off"].to_numpy(dtype=np.int16),
        "t0": t0s,
        "year": np.full(n, year, dtype=np.int16),
        "old_clause": old_clause.astype(np.int16),
        "old_net": old_net,
        "old_exit": old_exit,
        "abl_net": abl_net,
        "abl_clause": abl_clause.astype(np.int16),
        "abl_exit": abl_exit,
        "abl_labeled": abl_labeled,
    }


def run_days(
    bank: pd.DataFrame, db_dir, out_dir, *, days: Optional[Sequence[str]] = None,
    engine: str = "vector", progress_name: str = "sell_d1_progress.txt",
) -> Dict[str, object]:
    """일 루프(체크포인트 parts) — 재현 게이트 통과 후 자기-절 ablation 기록."""
    out = Path(out_dir)
    parts = out / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    progress = out / progress_name
    all_days = day_list(db_dir)
    bank_days = set(int(d) for d in bank["day"].unique())
    targets = [(d, p) for d, p in all_days if int(d) in bank_days]
    if days:
        want = {str(d) for d in days}
        targets = [(d, p) for d, p in targets if d in want]

    def log(msg: str) -> None:
        with open(progress, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()}   {msg}\n")

    log(f"SELL-D1 start: {len(targets)} days engine={engine}")
    done = 0
    for date, db_path in targets:
        day = int(date)
        part = parts / f"{PART_PREFIX}{date}.parquet"
        if part.exists():
            done += 1
            continue
        sub_day = bank[bank["day"] == day]
        conn = reader.connect_ro(Path(db_path))
        try:
            chunks: List[Dict[str, np.ndarray]] = []
            for code, sub in sub_day.groupby("code", sort=True):
                chunks.append(_process_code(conn, str(code), day,
                                            sub.reset_index(drop=True), engine))
        finally:
            conn.close()
        if chunks:
            rec = {k: np.concatenate([c[k] for c in chunks])
                   for k in chunks[0]}
            pd.DataFrame(rec).to_parquet(part, index=False)
        else:
            pd.DataFrame({k: [] for k in (
                "code", "day", "off", "t0", "year", "old_clause", "old_net",
                "old_exit", "abl_net", "abl_clause", "abl_exit", "abl_labeled",
            )}).to_parquet(part, index=False)
        done += 1
        n_onsets = int(len(sub_day))
        n_fired = int((sub_day["l3_clause"] > 0).sum())
        log(f"{date}: onsets={n_onsets} fired={n_fired} repro=OK "
            f"[{done}/{len(targets)}]")
    log(f"SELL-D1 done: {done}/{len(targets)} days")
    return {"days_total": len(targets), "days_done": done}


def consolidate(out_dir) -> Dict[str, object]:
    """parts → 단일 델타 parquet + 카운트 요약(측정 아님 — 이어붙이기만)."""
    out = Path(out_dir)
    files = sorted((out / "parts").glob(f"{PART_PREFIX}*.parquet"))
    if not files:
        raise FileNotFoundError("parts 없음 — run 단계 선행 필요")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    dst = out / "sell_d1_deltas.parquet"
    df.to_parquet(dst, index=False)
    summary = {
        "kind": "sell_d1_run", "generated": _utc_now(),
        "days": int(df["day"].nunique()), "rows": int(len(df)),
        "fired_rows": int((df["old_clause"] > 0).sum()),
        "cap_rows": int((df["old_clause"] == 0).sum()),
        "abl_labeled": int(df["abl_labeled"].sum()),
        "path": str(dst),
    }
    (out / "sell_d1_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def fullmask_spot(
    bank: pd.DataFrame, db_dir, *, n_sample: int = 200, seed: int = 20260717,
    engine: str = "vector",
) -> Dict[str, object]:
    """full-mask 스팟(§14-F2) — 전 절 무력화 시 강제캡(0)만 남아야 한다."""
    fired = bank[bank["l3_clause"] > 0]
    rng = np.random.default_rng(seed)
    pick = fired.iloc[np.sort(rng.choice(len(fired), size=min(n_sample, len(fired)),
                                         replace=False))]
    day_paths = {int(d): p for d, p in day_list(db_dir)}
    n_cap = n_unlab = n_bad = 0
    examples: List[Dict[str, object]] = []
    for day, sub_day in pick.groupby("day", sort=True):
        conn = reader.connect_ro(Path(day_paths[int(day)]))
        try:
            for code, sub in sub_day.groupby("code", sort=True):
                rows = reader.load_stock_rows(conn, str(code))
                res, _ = harness.label_drop(
                    rows, list(sub["t0"].to_numpy(np.int64)),
                    year=int(day) // 10000, drop=harness.DROP_ALL, engine=engine)
                for j in range(len(sub)):
                    if not res["labeled"][j]:
                        n_unlab += 1
                    elif int(res["clause"][j]) == 0:
                        n_cap += 1
                    else:
                        n_bad += 1
                        examples.append({"code": str(code), "day": int(day),
                                         "t0": int(sub["t0"].iloc[j]),
                                         "clause": int(res["clause"][j])})
        finally:
            conn.close()
    return {"n_sample": int(len(pick)), "forced_cap": n_cap,
            "unlabeled": n_unlab, "leaked_fire": n_bad,
            "gate_pass": n_bad == 0, "examples": examples[:5]}
