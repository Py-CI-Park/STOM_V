/* Copyable AI state context pack panel */
const { useState: useState_ac, useEffect: useEffect_ac } = React;

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
      const text = pack ? (pack.summary_text || JSON.stringify(pack, null, 2)) : "";
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

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
