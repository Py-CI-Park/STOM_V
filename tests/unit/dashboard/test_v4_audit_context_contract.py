from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _run_helper(source: str, name: str, expression: str) -> object:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    start = source.index(f"function {name}")
    end = source.index("\n}\n", start) + 2
    helper = source[start:end]
    script = f"const fn = new Function(process.argv[2] + '; return {name};')();\nconsole.log(JSON.stringify({expression}));"
    result = subprocess.run(
        [node, "-", helper], capture_output=True, text=True, encoding="utf-8",
        input=script, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def _run_helper_block(
    source: str,
    first_name: str,
    last_name: str,
    return_name: str,
    expression: str,
) -> object:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    start = source.index(f"function {first_name}")
    last = source.index(f"function {last_name}", start)
    end = source.index("\n}\n", last) + 2
    helper = source[start:end]
    script = (
        f"const fn = new Function(process.argv[2] + '; return {return_name};')();\n"
        f"console.log(JSON.stringify({expression}));"
    )
    result = subprocess.run(
        [node, "-", helper], capture_output=True, text=True, encoding="utf-8",
        input=script, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_audit_exposes_filterable_decision_trace_with_honest_states() -> None:
    # Given: the V4 Audit tab source.
    source = _read("v4-audit.jsx")

    # When/Then: decision trace is searchable and exposes provenance without inventing evidence.
    assert "function auditDecisionMatches" in source
    assert '<fieldset className="v4-audit-filters">' in source
    assert '<legend>' in source
    assert 'aria-labelledby="v4-audit-trace-title"' in source
    assert '<caption>' in source
    assert 'scope="col"' in source
    assert 'role="status"' in source
    assert 'role="alert"' in source
    for marker in ("provenance", "status", "blocker", "append-only"):
        assert marker in source


def test_audit_filter_matches_verdict_and_trace_fields() -> None:
    # Given: one traced decision and two filters.
    source = _read("v4-audit.jsx")
    expression = "[fn({verdict:'hold',note:'OOS blocker',candidate:{buy_name:'Alpha'}},'alpha','all'),fn({verdict:'hold',note:'OOS blocker'},'','promote')]"

    # When/Then: text searches trace content while verdict filtering remains exact.
    assert _run_helper(source, "auditDecisionMatches", expression) == [True, False]


def test_context_copy_serializes_only_the_exact_model_context_pack() -> None:
    # Given: a response containing display metadata around the model context pack.
    source = _read("ai-context.jsx")
    expression = r"fn({summary_text:'display-only',run_id:'r1',context_pack:{guide_context:{text:'\uAE34 \uD55C\uAD6D\uC5B4'},diff_context:{code:'A > B'}}})"

    # When/Then: clipboard text is exactly the context_pack JSON, with no display prefix/truncation.
    copied = _run_helper(source, "copyableContextPack", expression)
    assert json.loads(copied) == {
        "guide_context": {"text": "긴 한국어"},
        "diff_context": {"code": "A > B"},
    }
    assert "display-only" not in copied
    assert "run_id" not in copied


def test_context_exposes_identity_freshness_and_copy_outcomes() -> None:
    # Given: the V4 Context panel source.
    source = _read("ai-context.jsx")

    # When/Then: loading/error/copy outcomes and long-content ownership are accessible and explicit.
    assert 'aria-labelledby="ai-context-title"' in source
    assert 'aria-label="모델 컨텍스트 원문"' in source
    assert 'aria-live="polite"' in source
    assert 'role="alert"' in source
    assert "copyError" in source
    assert "복사 실패" in source
    assert "setView(previous" in source
    assert "source=" in source
    assert "version=" in source
    assert "freshness=" in source
    assert 'tabIndex="0"' in source
    assert "전체 원문 · 생략 없음" in source
    assert ".slice(" not in source
    assert "catch {}" not in source


def test_context_response_identity_rejects_stale_base_run_gen_and_malformed_payloads() -> None:
    # Given: a requested BASE/run/generation identity and responses that may arrive late.
    source = _read("ai-context.jsx")
    expression = """[
      fn({base_url:'http://one',run_id:'run-a',gen_no:7,context_pack:{}},{baseUrl:'http://one',runId:'run-a',genNo:7}),
      fn({base_url:'http://old',run_id:'run-a',gen_no:7,context_pack:{}},{baseUrl:'http://one',runId:'run-a',genNo:7}),
      fn({run_id:'run-old',gen_no:7,context_pack:{}},{baseUrl:'http://one',runId:'run-a',genNo:7}),
      fn({run_id:'run-a',gen_no:6,context_pack:{}},{baseUrl:'http://one',runId:'run-a',genNo:7}),
      fn({run_id:'run-a',gen_no:7},{baseUrl:'http://one',runId:'run-a',genNo:7}),
      fn({context_pack:{}},{baseUrl:'http://one',runId:'run-a',genNo:7})
    ]"""

    # When/Then: supplied identity fields must match exactly; legacy omission is allowed,
    # but a payload without either a context pack or a server error is rejected.
    assert _run_helper(source, "contextPackResponseMatchesIdentity", expression) == [
        True, False, False, False, False, True,
    ]


def test_context_request_lifecycle_aborts_and_hides_unowned_content_before_copy() -> None:
    # Given: the context panel request lifecycle.
    source = _read("ai-context.jsx")

    # When/Then: selection changes abort prior work, generation gates callbacks, and
    # render/copy consume only a view tagged with the current BASE/run/generation.
    for marker in (
        "new AbortController()",
        "request.generation + 1",
        "request.generation += 1",
        "controller.abort()",
        "viewIsOwned = sameContextIdentity(view.identity, currentIdentity)",
        "contextPackResponseMatchesIdentity(response, identity)",
        "disabled={!contextPack}",
        "const text = copyableContextPack(pack)",
    ):
        assert marker in source
def test_verdict_payload_base_identity_rejects_malformed_and_foreign_responses() -> None:
    # Given: a VerdictPanel response may carry an explicit source BASE.
    source = _read("dashboard-pages.jsx")
    expression = """[
      fn({base_url:'http://one'}, 'http://one'),
      fn({base:'http://one'}, 'http://one'),
      fn({base_url:'http://old'}, 'http://one'),
      fn({base:'http://old'}, 'http://one'),
      fn([], 'http://one'),
      fn(null, 'http://one')
    ]"""

    # When/Then: explicit ownership must match exactly and malformed responses fail closed.
    assert _run_helper(source, "verdictPayloadMatchesBase", expression) == [
        True, True, False, False, False, False,
    ]


def test_verdict_endpoint_payloads_require_backend_owned_shapes() -> None:
    source = _read("dashboard-pages.jsx")
    expression = """[
      fn('freeze_verdict',{lines:[],alerts:[],promote_checklist:[],oos_diff_ci:{}},'http://one'),
      fn('freeze_verdict',{status:'ok'},'http://one'),
      fn('regime_report',{status:'unavailable'},'http://one'),
      fn('regime_report',{breakdowns:{}},'http://one'),
      fn('regime_report',{},'http://one'),
      fn('revival_registry',{rejected:[{label:'x'}]},'http://one'),
      fn('revival_registry',{rejected:'wrong'},'http://one'),
      fn('portfolio_verdict',{adopted:false,status:'unavailable'},'http://one'),
      fn('portfolio_verdict',{adopted:true,members:[{name:'A',weight:0.5}],m4:{alerts:[]}},'http://one'),
      fn('portfolio_verdict',{adopted:true,members:[{name:'A',weight:'0.5'}],m4:null},'http://one'),
      fn('record_decision',{status:'ok',recorded:{verdict:'hold'}},'http://one'),
      fn('record_decision',{status:'ok'},'http://one'),
      fn('record_decision',{status:'anything'},'http://one'),
      fn('unknown',{},'http://one')
    ]"""
    assert _run_helper_block(
        source,
        "verdictPayloadMatchesBase",
        "verdictPayloadMatchesEndpoint",
        "verdictPayloadMatchesEndpoint",
        expression,
    ) == [
        True, False, True, True, False, True, False,
        True, True, False, True, False, False, False,
    ]


def test_research_index_links_only_explicit_governed_history_ids() -> None:
    source = _read("research-index.jsx")
    expression = """[
      fn({research_id:'loop_run:r1'}),
      fn({id:'campaign:c1',kind:'campaign'}),
      fn({exact_link:'research-index://loop_run:r2'}),
      fn({exact_link:'research-index://campaign:c2'}),
      fn({id:'doc:campaign:c3',kind:'doc'}),
      fn({exact_link:'research-index://doc:loop_run:r3'}),
      fn({id:'campaignish:c4'}),
      fn(null)
    ]"""
    assert _run_helper(source, "_rixExactResearchId", expression) == [
        "loop_run:r1", "campaign:c1", "loop_run:r2", "campaign:c2",
        "", "", "", "",
    ]


def test_verdict_panel_aborts_and_generation_guards_all_governance_sources() -> None:
    # Given: the History governance panel can be rebound to another BASE mid-request.
    source = _read("dashboard-pages.jsx")
    start = source.index("function VerdictPanel(")
    panel = source[start:source.index("Object.assign(window", start)]

    # When/Then: old BASE callbacks cannot publish data, errors, POST feedback, or a ledger reload.
    for marker in (
        "const sourceOwned = verdictState.base === base",
        "currentBaseRef.current === identity",
        "active.generation === generation",
        "Object.values(previous.controllers).forEach(controller => controller.abort())",
        "Object.values(active.controllers).forEach(controller => controller.abort())",
        'loadVerdictEndpoint(base, generation, "freeze_verdict", "v", 12000)',
        'loadVerdictEndpoint(base, generation, "regime_report", "regime", 10000)',
        'loadVerdictEndpoint(base, generation, "revival_registry", "revival", 10000)',
        'loadVerdictEndpoint(base, generation, "portfolio_verdict", "portfolio", 10000)',
        'loadVerdictEndpoint(base, generation, "decisions", "history", 8000)',
        'ownsVerdictRequest(identity, generation, "record_decision", controller)',
        'loadVerdictEndpoint(identity, generation, "decisions", "history", 8000)',
        'throw new Error("Malformed /" + endpoint + " response")',
        'throw new Error("Malformed /record_decision response")',
    ):
        assert marker in panel