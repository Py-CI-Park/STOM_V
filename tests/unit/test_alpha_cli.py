"""알파 랩 CLI 4종 연쇄 스모크 — dataset → mine → translate + events (통합 레인).

합성 2일 미니 DB(tmp sqlite, 실측 계약 미러: 종목 테이블 index=int
YYYYMMDDHHMMSS + moneytop 세미콜론 조인)로 CLI 전 구간을 인프로세스 실행한다.

봉인 규율 검증:
- 각 CLI는 시작 시 preregistration_v1.json 을 .sha256 사이드카 값으로
  registry.verify_seal 하며, 불일치 시 exit code 3(비정상 종료).
- 파라미터(트리/부트스트랩/채택 게이트/층화)는 tmp run dir에 봉인한 미니
  사전등록에서 온다 — CLI 기본값이 봉인 문서에서 오는 설계를 함께 검증.
- 탐색 전수(리프 수·셀 수)는 n_trials_ledger.jsonl 에 정직 합산된다.

플랜트 신호: 종목 '111111'(체결강도=200)은 전 지평 L1=1, '222222'(체결강도=50)
는 L1=0 — 채굴이 lift 2.0 리프로 회수하고 번역까지 왕복해야 한다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alpha_lab import registry
from cli import alpha_dataset, alpha_events, alpha_mine, alpha_translate

DATES = ("20240103", "20240104")
POS_CODE, NEG_CODE = "111111", "222222"
LAST_SECOND = 390  # 09:00:00 + 390초 = 09:06:30 — t0<=09:01:26 만 3지평 성립.

# 저장 54컬럼 실명(계약 순서 그대로) — 합성 DB 스키마 구성용.
COLUMNS_54 = (
    "index", "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "라운드피겨위5호가이내", "VI해제시간", "VI가격", "VI호가단위",
    "초당거래대금", "고저평균대비등락율", "저가대비고가등락율", "초당매수금액",
    "초당매도금액", "당일매수금액", "최고매수금액", "최고매수가격", "당일매도금액",
    "최고매도금액", "최고매도가격", "매도호가5", "매도호가4", "매도호가3", "매도호가2",
    "매도호가1", "매수호가1", "매수호가2", "매수호가3", "매수호가4", "매수호가5",
    "매도잔량5", "매도잔량4", "매도잔량3", "매도잔량2", "매도잔량1", "매수잔량1",
    "매수잔량2", "매수잔량3", "매수잔량4", "매수잔량5", "매도총잔량", "매수총잔량",
    "매도수5호가잔량합", "관심종목",
)

# 미니 사전등록 — CLI가 소비하는 키만 담은 소형 봉인 문서(작은 게이트 값).
MINI_PREREG = {
    "program": "alpha_lab_cli_smoke",
    "sealed_date": "2026-07-05",
    "windows": {"mvp": {"y2024": list(DATES)}},
    "label_spec": {
        "grid": {"stride_sec": 5},
        "L1": {"horizons_sec": [60, 180, 300]},
    },
    "mining_spec": {
        "label": "L1_180",
        "max_depth": 3,
        "min_samples_leaf": 5,
        "seed": 20260705,
        "bootstrap": {"n": 60},
        "fdr_q": 0.05,
        "adopt": {"lift_min": 1.5, "support_min": 10, "per_year_lift_gt": 1.0},
    },
    "events_spec": {
        "refractory_sec": 120,
        "fdr_q": 0.05,
        "min_n_cell": 2,
        "horizons": [60, 180, 300],
        "strata": {
            "시가총액_억": {"edges": [1500.0, 3000.0, 10000.0]},
            "등락율_pct": {"edges": [3.0, 8.0]},
            "시간밴드": {"band_minutes": 5},
        },
    },
    "ledger": {"path": "n_trials_ledger.jsonl"},
}


def _ts(date: str, second: int) -> int:
    base = datetime.strptime(date + "090000", "%Y%m%d%H%M%S")
    return int((base + timedelta(seconds=second)).strftime("%Y%m%d%H%M%S"))


def _row(date: str, second: int, *, pos: bool) -> dict:
    """이벤트 플랜트 포함 1행: E1(s=50 VI해제 전이), E3(당일거래대금=0 서지),
    E4(갭 +2.5%), E5(s=31 라운드피겨 1→0)."""
    row = {c: 0.0 for c in COLUMNS_54}
    row.update({
        "index": _ts(date, second),
        "현재가": 10000.0, "시가": 10000.0, "고가": 10000.0, "저가": 10000.0,
        "등락율": 2.5, "시가총액": 4321.0,
        "체결강도": 200.0 if pos else 50.0,
        "매도호가1": 10000.0,
        "매수호가1": 10600.0 if pos else 10000.0,
        "매도총잔량": 100.0, "매수총잔량": 100.0,
        "초당거래대금": 999.0, "당일거래대금": 0.0,
        "라운드피겨위5호가이내": 1.0 if second <= 30 else 0.0,
        "VI해제시간": float(f"{date}090049") if second >= 50 else 0.0,
    })
    return row


def _build_day_db(path: Path, date: str) -> None:
    conn = sqlite3.connect(str(path))
    try:
        col_defs = ", ".join(
            f'"{c}" INTEGER PRIMARY KEY' if c == "index" else f'"{c}" REAL'
            for c in COLUMNS_54
        )
        holders = ", ".join("?" for _ in COLUMNS_54)
        for code, pos in ((POS_CODE, True), (NEG_CODE, False)):
            conn.execute(f'CREATE TABLE "{code}" ({col_defs})')
            conn.executemany(
                f'INSERT INTO "{code}" VALUES ({holders})',
                [
                    tuple(_row(date, s, pos=pos)[c] for c in COLUMNS_54)
                    for s in range(0, LAST_SECOND + 1)
                ],
            )
        conn.execute(
            'CREATE TABLE moneytop ("index" INTEGER PRIMARY KEY, "거래대금순위" TEXT)'
        )
        conn.executemany(
            "INSERT INTO moneytop VALUES (?, ?)",
            [(_ts(date, s), f"{POS_CODE};{NEG_CODE}") for s in range(0, LAST_SECOND + 1)],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="module")
def cli_env(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("alpha_cli")
    db_dir, run_dir = root / "db", root / "run"
    db_dir.mkdir()
    run_dir.mkdir()
    for date in DATES:
        _build_day_db(db_dir / f"stock_tick_{date}.db", date)
    sha = registry.seal(MINI_PREREG, run_dir / "preregistration_v1.json")
    (run_dir / "preregistration_v1.sha256").write_text(sha + "\n", encoding="utf-8")
    return {"db_dir": db_dir, "run_dir": run_dir, "sha": sha}


@pytest.fixture(scope="module")
def dataset_receipt(cli_env) -> dict:
    """alpha_dataset --mvp 실행(사전등록 windows.mvp 경로 검증) 후 영수증."""
    rc = alpha_dataset.main([
        "--mvp", "--db-dir", str(cli_env["db_dir"]),
        "--run-dir", str(cli_env["run_dir"]),
    ])
    assert rc == 0
    path = cli_env["run_dir"] / "dataset_build_receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mining_report(cli_env, dataset_receipt) -> dict:
    rc = alpha_mine.main([
        "--dates", ",".join(DATES), "--run-dir", str(cli_env["run_dir"]),
    ])
    assert rc == 0
    path = cli_env["run_dir"] / "mining_report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def translation_receipt(cli_env, mining_report) -> dict:
    rc = alpha_translate.main(["--run-dir", str(cli_env["run_dir"])])
    assert rc == 0
    path = cli_env["run_dir"] / "translation_receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------ dataset --


def test_dataset_receipt_counts_and_rates(cli_env, dataset_receipt):
    r = dataset_receipt
    assert r["prereg_sha"] == cli_env["sha"]
    assert r["date_source"] == "mvp"
    assert r["days_built"] == list(DATES)
    assert r["days_skipped_missing_db"] == []
    # 종목 2 × t0 18(09:00:01~09:01:26 stride5, 3지평 성립) × 2일 = 72.
    assert r["n_samples"] == 72
    assert r["labels"]["L1_180"]["positives"] == 36
    assert r["labels"]["L1_180"]["positive_rate"] == pytest.approx(0.5)
    assert r["labels"]["L2"]["pos"] == 36 and r["labels"]["L2"]["neg"] == 0
    assert r["elapsed_sec"] >= 0.0
    for date in DATES:
        assert (cli_env["run_dir"] / "cache" / f"{date}.npz").exists()
        assert r["per_day"][date]["n_samples"] == 36


def test_dataset_missing_db_is_honest_skip(cli_env, dataset_receipt, tmp_path):
    """없는 일자는 정직 스킵 카운트로 남고 종료 코드는 4(입력 부족)가 아니어야
    한다 — 일부 성공. 전 일자 결측이면 4."""
    rc = alpha_dataset.main([
        "--dates", "20240103,20991231", "--db-dir", str(cli_env["db_dir"]),
        "--run-dir", str(cli_env["run_dir"]), "--cache-dir", str(tmp_path / "c2"),
    ])
    assert rc == 0
    receipt = json.loads(
        (cli_env["run_dir"] / "dataset_build_receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["days_skipped_missing_db"] == ["20991231"]
    assert receipt["days_built"] == ["20240103"]
    rc_all_missing = alpha_dataset.main([
        "--dates", "20991230,20991231", "--db-dir", str(cli_env["db_dir"]),
        "--run-dir", str(cli_env["run_dir"]), "--cache-dir", str(tmp_path / "c3"),
    ])
    assert rc_all_missing == 4
    # 체인 후속 픽스처가 쓰는 원본 영수증 복원(같은 run_dir 재사용).
    rc_restore = alpha_dataset.main([
        "--mvp", "--db-dir", str(cli_env["db_dir"]), "--run-dir", str(cli_env["run_dir"]),
    ])
    assert rc_restore == 0


def test_dataset_requires_dates_xor_mvp(cli_env):
    with pytest.raises(SystemExit) as exc:
        alpha_dataset.main(["--run-dir", str(cli_env["run_dir"])])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc2:
        alpha_dataset.main([
            "--dates", "20240103", "--mvp", "--run-dir", str(cli_env["run_dir"]),
        ])
    assert exc2.value.code == 2


# ------------------------------------------------------------- mining --


def test_mine_report_recovers_planted_signal(cli_env, mining_report):
    r = mining_report
    assert r["prereg_sha"] == cli_env["sha"]
    assert r["label"] == "L1_180"
    assert r["n_samples"] == 72
    assert r["base_rate"] == pytest.approx(0.5)
    rules = r["rules"]
    assert rules and r["n_discovered"] == len(rules)
    for rule in rules:
        for key in ("rule_id", "rule", "support", "positives", "lift",
                    "ci_low", "ci_high", "p", "fdr_pass", "adopted",
                    "subset_id", "leaf_id"):
            assert key in rule
    adopted = [x for x in rules if x["adopted"]]
    assert r["n_adopted"] == len(adopted) >= 1
    # 플랜트 신호 회수: 채택 리프는 분리 가능한 두 피처만 사용, lift 2.0.
    for leaf in adopted:
        names = {cond[0] for cond in leaf["rule"]}
        assert names <= {"체결강도", "스프레드율"}
        assert leaf["lift"] == pytest.approx(2.0)
        assert leaf["per_year_lift"]["2024"] == pytest.approx(2.0)
        assert leaf["fdr_pass"] is True
    assert r["n_fdr_survived"] >= len(adopted)
    # 내부 키('_' 접두)는 직렬화 제외.
    assert all(not k.startswith("_") for rule in rules for k in rule)


def test_mine_appends_full_leaf_count_to_ledger(cli_env, mining_report):
    ledger = cli_env["run_dir"] / "n_trials_ledger.jsonl"
    assert registry.total_trials(ledger, "P1") == mining_report["n_discovered"]


# ---------------------------------------------------------- translate --


def test_translate_receipt_round_trip(cli_env, mining_report, translation_receipt):
    r = translation_receipt
    assert r["prereg_sha"] == cli_env["sha"]
    adopted_ids = {x["rule_id"] for x in mining_report["rules"] if x["adopted"]}
    assert r["n_adopted_input"] == len(adopted_ids)
    assert {t["rule_id"] for t in r["translations"]} == adopted_ids
    assert r["n_translated"] >= 1
    assert r["n_translated"] + r["n_untranslatable"] == r["n_adopted_input"]
    for entry in r["translations"]:
        if entry["expr"] is None:
            assert entry["reasons"]
            continue
        assert entry["validated"] is True
        assert "시분초" in entry["expr"]  # 시간 가드 결합.
        assert entry["buy_statement"].startswith("if ")
        assert entry["reasons"] == []
    assert r["round_digits"] == 1


# ------------------------------------------------------------- events --


def test_events_report_cells_and_ledger(cli_env):
    rc = alpha_events.main([
        "--db-dir", str(cli_env["db_dir"]), "--dates", ",".join(DATES),
        "--run-dir", str(cli_env["run_dir"]),
    ])
    assert rc == 0
    r = json.loads(
        (cli_env["run_dir"] / "event_cells_report.json").read_text(encoding="utf-8")
    )
    assert r["prereg_sha"] == cli_env["sha"]
    detected = r["events_detected"]
    assert detected["E2"] == 0                      # 신고가 갱신 없음(평탄가).
    assert detected["E1"] == detected["E4"] == detected["E5"] == 4
    assert detected["E3"] == 16                     # 불응기 120초 × 4회/종목·일.
    # 결과 성립 사건족 4 × 셀 1(cap2|t0|chg0) × 지평 3 = 12행 전수.
    assert r["n_cells"] == len(r["cells"]) == 12
    families = {c["event"] for c in r["cells"]}
    assert families == {"E1", "E3", "E4", "E5"}
    for cell in r["cells"]:
        for key in ("event", "cell", "horizon", "n", "ev", "ci_low", "ci_high",
                    "p", "fdr_pass", "placebo_ev_random", "placebo_ev_shift"):
            assert key in cell
        assert cell["n"] == 4
        assert cell["cell"] == "cap2|t0|chg0"
    ledger = cli_env["run_dir"] / "n_trials_ledger.jsonl"
    assert registry.total_trials(ledger, "P2") == r["n_cells"]


# --------------------------------------------------------------- seal --


def _sealed_dir_with_bad_sidecar(tmp_path: Path) -> Path:
    run_dir = tmp_path / "bad_run"
    run_dir.mkdir()
    registry.seal({"program": "x"}, run_dir / "preregistration_v1.json")
    (run_dir / "preregistration_v1.sha256").write_text("0" * 64 + "\n", encoding="utf-8")
    return run_dir


@pytest.mark.parametrize("runner", ["dataset", "mine", "events", "translate"])
def test_seal_mismatch_aborts_every_cli(tmp_path, runner):
    run_dir = _sealed_dir_with_bad_sidecar(tmp_path)
    argv_by_runner = {
        "dataset": lambda: alpha_dataset.main([
            "--dates", "20240103", "--db-dir", str(tmp_path),
            "--run-dir", str(run_dir),
        ]),
        "mine": lambda: alpha_mine.main([
            "--dates", "20240103", "--run-dir", str(run_dir),
        ]),
        "events": lambda: alpha_events.main([
            "--dates", "20240103", "--db-dir", str(tmp_path),
            "--run-dir", str(run_dir),
        ]),
        "translate": lambda: alpha_translate.main(["--run-dir", str(run_dir)]),
    }
    assert argv_by_runner[runner]() == 3
    assert not (run_dir / "dataset_build_receipt.json").exists()
    assert not (run_dir / "mining_report.json").exists()
    assert not (run_dir / "event_cells_report.json").exists()
    assert not (run_dir / "translation_receipt.json").exists()
    assert not (run_dir / "n_trials_ledger.jsonl").exists()
