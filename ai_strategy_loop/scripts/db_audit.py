"""P-E (2026-06-12) — DB 감사·데이터 신선도 도구.

틱 DB(stock_tick_back.db)와 연구 run DB(loop_runs.db)의 결측·고아 데이터를
감시한다. 침묵 결측을 조기에 포착하는 것이 목적.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.db_audit \
      --tick-db _database/stock_tick_back.db \
      --runs-db ai_strategy_loop/state/loop_runs.db \
      [--json-out audit_out.json] \
      [--today YYYYMMDD]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# 순수 함수
# ---------------------------------------------------------------------------

def audit_day_coverage(days: List[str], *, today: str) -> Dict:
    """일자 목록의 커버리지·신선도·평일 갭을 계산한다.

    Args:
        days: YYYYMMDD 문자열 목록 (중복 허용, 정렬 불요).
        today: 기준일 YYYYMMDD 문자열 (freshness_days 계산용).

    Returns:
        {
          "n_days": int,           # 고유 일자 수
          "first": str | None,     # 가장 오래된 일자
          "last": str | None,      # 가장 최신 일자
          "freshness_days": int | None,  # today - last (달력일수)
          "weekday_gaps": {
              "total": int,
              "sample": List[str],  # 최근 10개 누락 평일
          },
          "note": str,
        }
    """
    unique = sorted(set(d for d in days if d))
    n = len(unique)

    if n == 0:
        return {
            "n_days": 0,
            "first": None,
            "last": None,
            "freshness_days": None,
            "weekday_gaps": {"total": 0, "sample": []},
            "note": "데이터 없음",
        }

    first_str = unique[0]
    last_str = unique[-1]
    today_dt = datetime.strptime(today, "%Y%m%d").date()
    last_dt = datetime.strptime(last_str, "%Y%m%d").date()
    freshness_days = (today_dt - last_dt).days

    # min~max 사이 누락된 평일 탐색
    first_dt = datetime.strptime(first_str, "%Y%m%d").date()
    existing = set(unique)
    gaps: List[str] = []
    cursor = first_dt
    while cursor <= last_dt:
        if cursor.weekday() < 5:  # 월~금
            ds = cursor.strftime("%Y%m%d")
            if ds not in existing:
                gaps.append(ds)
        cursor += timedelta(days=1)

    return {
        "n_days": n,
        "first": first_str,
        "last": last_str,
        "freshness_days": freshness_days,
        "weekday_gaps": {
            "total": len(gaps),
            "sample": gaps[-10:],  # 최근 10개
        },
        "note": "휴장일 포함 가능 — 거래일 캘린더 아님",
    }


def load_tick_days(con: sqlite3.Connection) -> List[str]:
    """moneytop 테이블에서 고유 일자(YYYYMMDD) 목록을 반환한다.

    [index] 컬럼은 YYYYMMDDHHMMSS 형식 INTEGER이므로
    1000000으로 정수 나눗셈해 일자를 추출한다.

    Args:
        con: 읽기 전용 SQLite 커넥션.

    Returns:
        정렬된 YYYYMMDD 문자열 목록.
    """
    cur = con.execute(
        "SELECT DISTINCT CAST([index] / 1000000 AS INTEGER) FROM moneytop ORDER BY 1"
    )
    return [str(row[0]) for row in cur.fetchall()]


def audit_runs_db(
    con: sqlite3.Connection,
    *,
    file_exists: Callable[[str], bool] = os.path.isfile,
) -> Dict:
    """generations 테이블을 감사해 run 수·상태 카운트·고아 행을 반환한다.

    Args:
        con: loop_runs.db SQLite 커넥션.
        file_exists: csv_path 실존 여부 확인 함수 (테스트 주입용).

    Returns:
        {
          "run_count": int,
          "gen_count": int,
          "status_counts": Dict[str, int],
          "orphan_csvs": {"total": int, "sample": List[str]},
          "oldest_run_id": str | None,
          "newest_run_id": str | None,
        }
    """
    # runs 테이블 집계
    cur = con.execute("SELECT COUNT(*) FROM runs")
    run_count: int = cur.fetchone()[0]

    cur = con.execute("SELECT run_id FROM runs ORDER BY started_at ASC LIMIT 1")
    row = cur.fetchone()
    oldest_run_id: Optional[str] = row[0] if row else None

    cur = con.execute("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1")
    row = cur.fetchone()
    newest_run_id: Optional[str] = row[0] if row else None

    # generations 집계
    cur = con.execute("SELECT COUNT(*) FROM generations")
    gen_count: int = cur.fetchone()[0]

    cur = con.execute(
        "SELECT status, COUNT(*) AS cnt FROM generations GROUP BY status ORDER BY cnt DESC"
    )
    status_counts: Dict[str, int] = {row[0]: row[1] for row in cur.fetchall()}

    # 고아 csv_path 탐색 (경로 있으나 파일 없는 행)
    cur = con.execute(
        "SELECT csv_path FROM generations WHERE csv_path IS NOT NULL AND csv_path != ''"
    )
    orphan_paths: List[str] = []
    for (path,) in cur.fetchall():
        if not file_exists(path):
            orphan_paths.append(path)

    return {
        "run_count": run_count,
        "gen_count": gen_count,
        "status_counts": status_counts,
        "orphan_csvs": {
            "total": len(orphan_paths),
            "sample": orphan_paths[:5],
        },
        "oldest_run_id": oldest_run_id,
        "newest_run_id": newest_run_id,
    }


# ---------------------------------------------------------------------------
# 출력 포맷터
# ---------------------------------------------------------------------------

def _fmt_coverage(cov: Dict) -> str:
    """audit_day_coverage 결과를 콘솔 요약표 문자열로 변환."""
    lines = [
        "=== 틱 DB 커버리지 ===",
        f"  고유 일자 수  : {cov['n_days']:,} 일",
        f"  최초 일자     : {cov['first'] or '—'}",
        f"  최신 일자     : {cov['last'] or '—'}",
    ]
    fd = cov["freshness_days"]
    if fd is not None:
        freshness_label = f"{fd}일 전" if fd > 0 else "오늘"
        lines.append(f"  신선도        : {freshness_label} (기준일 대비)")
    gaps = cov["weekday_gaps"]
    lines.append(f"  평일 갭 총수  : {gaps['total']:,} 건")
    if gaps["sample"]:
        lines.append(f"  최근 갭 샘플  : {', '.join(gaps['sample'])}")
    lines.append(f"  참고          : {cov['note']}")
    return "\n".join(lines)


def _fmt_runs(r: Dict) -> str:
    """audit_runs_db 결과를 콘솔 요약표 문자열로 변환."""
    lines = [
        "=== 연구 Run DB 감사 ===",
        f"  run 수        : {r['run_count']:,}",
        f"  generation 수 : {r['gen_count']:,}",
        "  status 분포   :",
    ]
    for st, cnt in r["status_counts"].items():
        lines.append(f"    {st}: {cnt:,}")
    lines += [
        f"  최초 run_id   : {r['oldest_run_id'] or '—'}",
        f"  최신 run_id   : {r['newest_run_id'] or '—'}",
    ]
    orphan = r["orphan_csvs"]
    lines.append(f"  고아 csv 총수 : {orphan['total']:,} 건")
    if orphan["sample"]:
        lines.append("  고아 샘플(5)  :")
        for p in orphan["sample"]:
            lines.append(f"    {p}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI 진입점."""
    ap = argparse.ArgumentParser(
        description="틱 DB·연구 run DB 감사 — 읽기 전용"
    )
    ap.add_argument("--tick-db", required=True, help="틱 DB 경로 (읽기 전용)")
    ap.add_argument("--runs-db", required=True, help="연구 run DB 경로")
    ap.add_argument("--json-out", default="", help="JSON 결과 저장 경로 (선택)")
    ap.add_argument(
        "--today",
        default="",
        help="기준일 YYYYMMDD (기본=오늘)",
    )
    args = ap.parse_args()

    today_str = args.today if args.today else datetime.now().strftime("%Y%m%d")

    # 틱 DB — 반드시 읽기 전용 URI
    tick_uri = f"file:{args.tick_db}?mode=ro"
    tick_con = sqlite3.connect(tick_uri, uri=True)
    try:
        tick_days = load_tick_days(tick_con)
    finally:
        tick_con.close()

    cov = audit_day_coverage(tick_days, today=today_str)

    # run DB
    runs_con = sqlite3.connect(args.runs_db)
    try:
        runs_result = audit_runs_db(runs_con)
    finally:
        runs_con.close()

    # 콘솔 출력
    print(_fmt_coverage(cov))
    print()
    print(_fmt_runs(runs_result))

    # JSON 저장 (선택)
    if args.json_out:
        payload = {"today": today_str, "tick_coverage": cov, "runs_audit": runs_result}
        out_path = args.json_out
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n[JSON] {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
