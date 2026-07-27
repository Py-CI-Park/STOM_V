/* Read-only strategy diff, prompt, and AI context inspector */
const { useState: useState_si, useEffect: useEffect_si, useMemo: useMemo_si } = React;

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function diffClass(line) {
  if (line.startsWith("+") && !line.startsWith("+++")) return "add";
  if (line.startsWith("-") && !line.startsWith("---")) return "del";
  if (line.startsWith("@@")) return "meta";
  return "";
}

function PromptRow({ prompt }) {
  const features = prompt && prompt.injected_features ? prompt.injected_features : {};
  return (
    <div className="strategy-prompt-row">
      <div className="strategy-prompt-meta">
        <span className="pill">{safeText(prompt.kind)}</span>
        <span>attempt={safeText(prompt.attempt)}</span>
        <span>model={safeText(prompt.model)}</span>
        <span>total_tokens={safeText(prompt.total_tokens, "0")}</span>
      </div>
      <div className="strategy-prompt-head">
        user_text_head: {safeText(prompt.user_text_head, "not stored")}
      </div>
      <pre className="strategy-json">injected_features {JSON.stringify(features, null, 2)}</pre>
    </div>
  );
}

function DiffBlock({ title, lines }) {
  const rows = asList(lines);
  if (!rows.length) {
    return <div className="strategy-empty">{title}: no diff lines</div>;
  }
  return (
    <div className="strategy-diff-block">
      <div className="strategy-section-title">{title}</div>
      <pre className="strategy-diff-lines">
        {rows.map((line, i) => (
          <div key={i} className={diffClass(line)}>{line}</div>
        ))}
      </pre>
    </div>
  );
}

function CodeBlock({ title, code }) {
  const text = code || "";
  if (!text.trim()) {
    return <div className="strategy-empty">{title}: no strategy code loaded</div>;
  }
  return (
    <div className="strategy-diff-block">
      <div className="strategy-section-title">{title}</div>
      <pre className="strategy-diff-lines">{text}</pre>
    </div>
  );
}

function buildAiContext({ generation, runId, diffPayload, promptsPayload, buyCode, sellCode }) {
  const prompts = asList(promptsPayload && promptsPayload.prompts);
  const parts = [
    "STOM strategy research context",
    `run_id: ${safeText(runId)}`,
    `gen_no: ${safeText(generation && generation.gen_no)}`,
    `status: ${safeText(generation && generation.status)}`,
    `graded_score: ${safeText(generation && generation.graded_score)}`,
    `gate_passed: ${safeText(generation && generation.gate_passed)}`,
    `buy_name: ${safeText(generation && generation.buy_name)}`,
    `sell_name: ${safeText(generation && generation.sell_name)}`,
    `buy_code_lines: ${(buyCode || "").split("\n").filter(Boolean).length}`,
    `sell_code_lines: ${(sellCode || "").split("\n").filter(Boolean).length}`,
    `diff_base_gen: ${safeText(diffPayload && diffPayload.base_gen)}`,
    `diff_reason: ${safeText(diffPayload && diffPayload.reason, "available")}`,
    `prompt_count: ${prompts.length}`,
    `prompt_reason: ${safeText(promptsPayload && promptsPayload.reason, "available")}`,
    "buy_code:",
    buyCode || "(empty)",
    "sell_code:",
    sellCode || "(empty)",
    "Forbidden actions: do not approve or deploy from this copied context.",
  ];
  return parts.join("\n");
}

function StrategyInspectorTabs({ generation, runId, baseUrl, buyCode, sellCode }) {
  const [tab, setTab] = useState_si("diff");
  const [diffPayload, setDiffPayload] = useState_si(null);
  const [promptsPayload, setPromptsPayload] = useState_si(null);
  const [loading, setLoading] = useState_si(false);
  const [diffError, setDiffError] = useState_si("");
  const [promptsError, setPromptsError] = useState_si("");
  const [copied, setCopied] = useState_si(false);

  const genNo = generation && generation.gen_no;

  useEffect_si(() => {
    setDiffPayload(null);
    setPromptsPayload(null);
    setDiffError("");
    setPromptsError("");
    if (!generation || !baseUrl || !runId || genNo === undefined || genNo === null) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    let pending = 2;
    const finishOne = () => {
      pending -= 1;
      if (!cancelled && pending <= 0) setLoading(false);
    };
    setLoading(true);
    const params = `run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}&base_gen=previous`;
    fetch(`${baseUrl}/strategy_diff?${params}`, { signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(diff => { if (!cancelled) setDiffPayload(diff || {}); })
      .catch(e => {
        if (!cancelled) setDiffError("strategy_diff route unavailable: " + String(e));
      })
      .finally(finishOne);
    fetch(`${baseUrl}/prompts?run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}`,
          { signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(prompts => { if (!cancelled) setPromptsPayload(prompts || {}); })
      .catch(e => {
        if (!cancelled) setPromptsError("prompts route unavailable: " + String(e));
      })
      .finally(finishOne);
    return () => { cancelled = true; };
  }, [generation, baseUrl, runId, genNo]);

  const prompts = asList(promptsPayload && promptsPayload.prompts);
  const aiContext = useMemo_si(() => buildAiContext({
    generation, runId, diffPayload, promptsPayload, buyCode, sellCode,
  }), [generation, runId, diffPayload, promptsPayload, buyCode, sellCode]);

  const copyAiContext = async () => {
    try {
      await navigator.clipboard.writeText(aiContext);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

  // v5.13.0 — 각 탭이 무엇을 보여주는지 한국어 설명(A4). 라벨은 한국어 우선 + 원어 병기.
  const tabExplain = {
    diff: "직전 세대의 조건식과 비교해 이번 세대에서 무엇이 더해지고(＋) 빠졌는지(−) 보여줍니다. AI가 세대를 어떻게 고쳐 왔는지 추적하는 용도입니다.",
    prompts: "이 세대를 만들 때 AI에게 보낸 지시문(프롬프트) 기록입니다. 어떤 요구로 이 조건식이 나왔는지 확인합니다.",
    context: "이 세대의 요약(이름·점수·거래수·diff 근거)을 복사하기 좋은 텍스트로 정리한 것입니다. 외부 AI에게 이 전략을 설명하거나 질문할 때 붙여넣는 용도입니다.",
    code: "이 세대의 매수·매도 조건식 전체 코드입니다.",
  };
  return (
    <div className="strategy-inspector">
      <div className="strategy-inspector-tabs">
        <button className={tab === "diff" ? "active" : ""} onClick={() => setTab("diff")}>이전 세대와 비교 <small>Previous Diff</small></button>
        <button className={tab === "prompts" ? "active" : ""} onClick={() => setTab("prompts")}>프롬프트 기록 <small>Prompt Timeline</small></button>
        <button className={tab === "context" ? "active" : ""} onClick={() => setTab("context")}>AI 컨텍스트 <small>AI Context</small></button>
        <button className={tab === "code" ? "active" : ""} onClick={() => setTab("code")}>현재 코드 <small>Current Code</small></button>
      </div>
      <p className="strategy-tab-explain mono">{tabExplain[tab]}</p>
      {loading && <div className="strategy-empty">loading strategy inspector...</div>}
      {diffError && <div className="strategy-empty danger">{diffError}</div>}
      {promptsError && <div className="strategy-empty danger">{promptsError}</div>}
      {!loading && tab === "diff" && (
        <div className="strategy-inspector-body">
          <div className="strategy-kpis">
            <span>base_gen={safeText(diffPayload && diffPayload.base_gen)}</span>
            <span>reason={safeText(diffPayload && diffPayload.reason, "available")}</span>
            <span>no_previous_generation={String((diffPayload && diffPayload.reason) === "no_previous_generation")}</span>
          </div>
          <DiffBlock title="buy_diff" lines={diffPayload && diffPayload.buy_diff} />
          <DiffBlock title="sell_diff" lines={diffPayload && diffPayload.sell_diff} />
        </div>
      )}
      {!loading && tab === "prompts" && (
        <div className="strategy-inspector-body">
          <div className="strategy-kpis">
            <span>prompt_count={prompts.length}</span>
            <span>no-record reason={safeText(promptsPayload && promptsPayload.reason, "available")}</span>
          </div>
          {prompts.length ? prompts.map((prompt, i) => (
            <PromptRow key={`${prompt.kind || "prompt"}-${prompt.attempt || i}`} prompt={prompt} />
          )) : (
            <div className="strategy-empty">
              no prompt records for this generation. no-record reason: {safeText(promptsPayload && promptsPayload.reason, "prompt_logging_not_enabled_or_no_records")}
            </div>
          )}
        </div>
      )}
      {!loading && tab === "context" && (
        <div className="strategy-inspector-body">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
            <div className="strategy-section-title">Safe current-run summary</div>
            <button className="btn ghost sm" onClick={copyAiContext}>
              {copied ? "copied" : "copy AI context"}
            </button>
          </div>
          <pre className="strategy-context">{aiContext}</pre>
        </div>
      )}
      {tab === "code" && (
        <div className="strategy-inspector-body">
          <div className="strategy-section-title">Current Strategy Code</div>
          <CodeBlock title="buy_code" code={buyCode} />
          <CodeBlock title="sell_code" code={sellCode} />
        </div>
      )}
    </div>
  );
}

Object.assign(window, { StrategyInspectorTabs });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { StrategyInspectorTabs };
