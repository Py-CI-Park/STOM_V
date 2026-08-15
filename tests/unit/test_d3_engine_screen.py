from __future__ import annotations

import hashlib

from ai_strategy_loop.labeling.run_d3_engine_screen import SELL_SOURCE, run_screen


class FakeClient:
    def __init__(self):
        self.jobs = {}
        self.submissions = []

    def call(self, method, path, body=None):
        if method == "POST" and path == "/bt/run":
            self.submissions.append(body)
            job_id = f"J{len(self.submissions)}"
            self.jobs[job_id] = body
            return {"status": "ok", "job_id": job_id}
        if method == "GET" and path == "/bt/jobs":
            return {"jobs": [{
                "job_id": job_id, "status": "success",
                "spec": spec,
                "strategy_db_snapshot_hashes": {
                    "buy": hashlib.sha256(spec["buy_code"].encode()).hexdigest(),
                    "sell": hashlib.sha256(spec["sell_code"].encode()).hexdigest(),
                },
                "condition_identity": {
                    "kind": "code_hash",
                    "buy_hash": hashlib.sha256(spec["buy_code"].encode()).hexdigest(),
                    "sell_hash": hashlib.sha256(spec["sell_code"].encode()).hexdigest(),
                },
            } for job_id, spec in self.jobs.items()]}
        if method == "GET" and path.startswith("/bt/result"):
            return {"status": "success", "metrics": {
                "trade_count": 30, "avg_profit_pct": 0.2,
                "total_profit_pct": 1.0, "mdd_pct": 2.0,
            }, "process_diagnostics": {"last_checkpoint": "engine_backtest_completed"}}
        raise AssertionError((method, path, body))


def _manifest():
    candidates = [{
        "candidate_id": f"C{i}", "family_id": f"F{i % 5}", "band_id": f"B{i % 4}",
        "parameters": {"x": i}, "source": f"매수 = True\n# {i}\nif 매수:\n    self.Buy()\n",
        "window_contract_sha256": "a" * 64, "selected_for_engine": True,
    } for i in range(40)]
    for candidate in candidates:
        candidate["source_sha256"] = hashlib.sha256(candidate["source"].encode()).hexdigest()
    return {
        "schema": "stom.d3_mcap_qmc_manifest.v1",
        "authority": "existing_db_development_proposal_only_no_adoption",
        "window_contract": {"contract_sha256": "a" * 64},
        "candidates": candidates,
    }


def test_screen_submits_direct_sources_and_preserves_exact_hashes():
    client = FakeClient()
    report = run_screen(
        client, _manifest(), start=20231114, end=20231121,
        engines=1, job_timeout=30, poll_timeout=30, poll_interval=0,
    )
    assert report["verdict"] == "D3_SCREEN_COMPLETED"
    assert report["terminal_count"] == 40
    assert report["source_match_count"] == 40
    assert report["metrics_count"] == 40
    assert len(report["advanced"]) == 40
    assert all(item["buy_code"] and item["sell_code"] == SELL_SOURCE for item in client.submissions)
    assert all(item["start_time"] == 90000 and item["end_time"] == 93000 for item in client.submissions)


def test_screen_rejects_manifest_not_exactly_40_selected():
    manifest = _manifest()
    manifest["candidates"][0]["selected_for_engine"] = False
    try:
        run_screen(FakeClient(), manifest, start=1, end=2, engines=1, job_timeout=1, poll_timeout=1)
    except ValueError as exc:
        assert "40 unique selected" in str(exc)
    else:
        raise AssertionError("invalid screen manifest accepted")


def test_screen_rejects_tampered_manifest_source():
    manifest = _manifest()
    manifest["candidates"][0]["source"] += "# tampered\n"
    try:
        run_screen(FakeClient(), manifest, start=1, end=2, engines=1, job_timeout=1, poll_timeout=1)
    except ValueError as exc:
        assert "source hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered manifest accepted")


def test_screen_checkpoint_resumes_only_verified_success_rows(tmp_path):
    checkpoint = tmp_path / "screen.json"
    first_client = FakeClient()
    first = run_screen(
        first_client, _manifest(), checkpoint_path=checkpoint,
        start=20231114, end=20231114, engines=1, job_timeout=30, poll_timeout=30, poll_interval=0,
    )
    assert first["verdict"] == "D3_SCREEN_COMPLETED"
    assert len(first_client.submissions) == 40
    second_client = FakeClient()
    second = run_screen(
        second_client, _manifest(), checkpoint_path=checkpoint,
        start=20231114, end=20231114, engines=1, job_timeout=30, poll_timeout=30, poll_interval=0,
    )
    assert second["verdict"] == "D3_SCREEN_COMPLETED"
    assert second_client.submissions == []
