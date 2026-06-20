/* Copyable AI state context pack panel */
const { useState: useState_ac, useEffect: useEffect_ac } = React;

function packText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function AIContextPanel({ baseUrl, wsStatus, runId, genNo }) {
  const [pack, setPack] = useState_ac(null);
  const [loading, setLoading] = useState_ac(false);
  const [err, setErr] = useState_ac("");
  const [copied, setCopied] = useState_ac(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const loadPack = React.useCallback(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    setErr("");
    const suffix = genNo != null ? "&gen_no=" + encodeURIComponent(genNo) : "";
    fetch(baseUrl + "/ai_context_pack?run_id=" + encodeURIComponent(runId) + suffix,
          { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setPack(j || null))
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, genNo]);

  useEffect_ac(() => { loadPack(); }, [loadPack]);

  const copyPack = async () => {
    try {
      const text = pack
        ? (pack.summary_text
          ? `${pack.summary_text}\n\ncontext_pack:\n${JSON.stringify(pack.context_pack || {}, null, 2)}`
          : JSON.stringify(pack.context_pack || pack, null, 2))
        : "";
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

  const contextPack = pack && pack.context_pack ? pack.context_pack : null;
  const guideContext = packText(contextPack && contextPack.guide_context, pack && pack.summary_text);
  const diffContext = packText(
    contextPack && contextPack.diff_context,
    pack ? [
      `strategy_buy: ${(pack.strategy_names && pack.strategy_names.buy) || "-"}`,
      `strategy_sell: ${(pack.strategy_names && pack.strategy_names.sell) || "-"}`,
      `verdict: ${pack.verdict_note || "-"}`,
    ].join("\n") : "-",
  );
  const analysisContext = packText(
    contextPack && contextPack.analysis_context,
    pack && pack.analysis,
  );
  const correlationContext = packText(
    contextPack && contextPack.correlation_context,
    pack && pack.analysis && pack.analysis.variable_correlation,
  );

  return (
    <div className="panel ai-context-panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          AI State Context
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <button className="btn ghost sm" onClick={loadPack} disabled={isDemo || loading || !runId}>
            {loading ? "loading" : "refresh"}
          </button>
          <button className="btn ghost sm" onClick={copyPack} disabled={!pack}>
            {copied ? "copied" : "copy AI state"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <div className="ai-context-empty">Backend connection required.</div>
        ) : err ? (
          <div className="ai-context-empty danger">context pack failed: {err}</div>
        ) : !pack ? (
          <div className="ai-context-empty">No context pack loaded.</div>
        ) : pack.error ? (
          <div className="ai-context-empty danger">{pack.error}</div>
        ) : (
          <div className="ai-context-body">
            <div className="ai-context-kpis">
              <span>run_id={pack.run_id}</span>
              <span>gen_no={pack.gen_no}</span>
              <span>timeframe={pack.timeframe || "-"}</span>
              <span>prompt_count={pack.prompt_count || 0}</span>
            </div>
            <pre className="ai-context-summary">{pack.summary_text}</pre>
            <div className="ai-context-pack">
              <div className="ai-context-pack-head">
                <strong>context_pack</strong>
                <span>{contextPack ? Object.keys(contextPack).length + " sections" : "-"}</span>
              </div>
              <pre className="ai-context-summary">{JSON.stringify(contextPack, null, 2)}</pre>
            </div>
            <div className="ai-context-actions">
              <span>guide_context</span>
              <pre className="ai-context-summary">{guideContext}</pre>
              <span>diff_context</span>
              <pre className="ai-context-summary">{diffContext}</pre>
              <span>analysis_context</span>
              <pre className="ai-context-summary">{analysisContext}</pre>
              <span>correlation_context</span>
              <pre className="ai-context-summary">{correlationContext}</pre>
            </div>
            <div className="ai-context-actions">
              <strong>forbidden_actions</strong>
              {(pack.forbidden_actions || []).map((item, i) => <span key={i}>{item}</span>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { AIContextPanel });

// Track Z (PR-3) — dual-safe ESM export for bundled module imports.
export { AIContextPanel };
