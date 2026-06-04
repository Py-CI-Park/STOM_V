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
    "Forbidden actions: do not approve or deploy from this copied context.",
  ];
  return parts.join("\n");
}

function StrategyInspectorTabs({ generation, runId, baseUrl, buyCode, sellCode }) {
  const [tab, setTab] = useState_si("diff");
  const [diffPayload, setDiffPayload] = useState_si(null);
  const [promptsPayload, setPromptsPayload] = useState_si(null);
  const [loading, setLoading] = useState_si(false);
  const [error, setError] = useState_si("");
  const [copied, setCopied] = useState_si(false);

  const genNo = generation && generation.gen_no;

  useEffect_si(() => {
    setDiffPayload(null);
    setPromptsPayload(null);
    setError("");
    if (!generation || !baseUrl || !runId || genNo === undefined || genNo === null) return;
    let cancelled = false;
    setLoading(true);
    const params = `run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}&base_gen=previous`;
    Promise.all([
      fetch(`${baseUrl}/strategy_diff?${params}`, { signal: AbortSignal.timeout(3000) })
        .then(r => r.ok ? r.json() : Promise.reject(new Error("strategy_diff HTTP " + r.status))),
      fetch(`${baseUrl}/prompts?run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}`,
            { signal: AbortSignal.timeout(3000) })
        .then(r => r.ok ? r.json() : Promise.reject(new Error("prompts HTTP " + r.status))),
    ])
      .then(([diff, prompts]) => {
        if (!cancelled) {
          setDiffPayload(diff || {});
          setPromptsPayload(prompts || {});
        }
      })
      .catch(e => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
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

  return (
    <div className="strategy-inspector">
      <div className="strategy-inspector-tabs">
        <button className={tab === "diff" ? "active" : ""} onClick={() => setTab("diff")}>Previous Diff</button>
        <button className={tab === "prompts" ? "active" : ""} onClick={() => setTab("prompts")}>Prompt Timeline</button>
        <button className={tab === "context" ? "active" : ""} onClick={() => setTab("context")}>AI Context</button>
      </div>
      {loading && <div className="strategy-empty">loading strategy inspector...</div>}
      {error && <div className="strategy-empty danger">strategy inspector error: {error}</div>}
      {!loading && !error && tab === "diff" && (
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
      {!loading && !error && tab === "prompts" && (
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
      {!loading && !error && tab === "context" && (
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
    </div>
  );
}

Object.assign(window, { StrategyInspectorTabs });
