/* Copyable AI state context pack panel */
const { useState: useState_ac, useEffect: useEffect_ac } = React;

function packText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function copyableContextPack(pack) {
  if (!pack || typeof pack !== "object" || !pack.context_pack) return "";
  return JSON.stringify(pack.context_pack, null, 2);
}

function AIContextPanel({ baseUrl, wsStatus, runId, genNo }) {
  const [pack, setPack] = useState_ac(null);
  const [loading, setLoading] = useState_ac(false);
  const [err, setErr] = useState_ac("");
  const [copied, setCopied] = useState_ac(false);
  const [copyError, setCopyError] = useState_ac("");
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const loadPack = React.useCallback(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    setErr("");
    setCopied(false);
    setCopyError("");
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
      const text = copyableContextPack(pack);
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setCopyError("");
    } catch (reason) {
      setCopied(false);
      setCopyError(String(reason));
    }
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
  const source = packText(contextPack && contextPack.guide_context && contextPack.guide_context.source, "서버 미제공");
  const version = packText(pack && pack.context_pack_version, "서버 미제공");
  const freshness = packText(
    pack && pack.latest_logs && (pack.latest_logs.finished_at || pack.latest_logs.started_at),
    "서버 시각 미제공",
  );

  return (
    <section className="panel ai-context-panel" aria-labelledby="ai-context-title">
      <div className="panel-hd">
        <h2 id="ai-context-title" className="panel-hd-title">
          <span className="dot"></span>
          AI State Context
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </h2>
        <div className="ai-context-actions">
          <button className="btn ghost sm" onClick={loadPack} disabled={isDemo || loading || !runId}
                  aria-label="컨텍스트 팩 새로고침">
            {loading ? "loading" : "refresh"}
          </button>
          <button className="btn ghost sm" onClick={copyPack} disabled={!contextPack}
                  aria-label="모델 컨텍스트 원문 복사">
            {copied ? "복사 완료" : "copy AI state · exact"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <div className="ai-context-empty" role="status">Backend connection required.</div>
        ) : err ? (
          <div className="ai-context-empty danger" role="alert">context pack failed: {err}</div>
        ) : loading ? (
          <div className="ai-context-empty" role="status">컨텍스트 팩을 불러오는 중입니다.</div>
        ) : !pack ? (
          <div className="ai-context-empty" role="status">No context pack loaded.</div>
        ) : pack.error ? (
          <div className="ai-context-empty danger" role="alert">{pack.error}</div>
        ) : (
          <div className="ai-context-body">
            <div className="ai-context-kpis" aria-label="컨텍스트 팩 식별 정보">
              <span>run_id={pack.run_id}</span>
              <span>gen_no={pack.gen_no}</span>
              <span>timeframe={pack.timeframe || "-"}</span>
              <span>prompt_count={pack.prompt_count || 0}</span>
              <span>source={source}</span>
              <span>version={version}</span>
              <span>freshness={freshness}</span>
            </div>
            <pre className="ai-context-summary" tabIndex="0" aria-label="컨텍스트 요약">{pack.summary_text}</pre>
            <div className="ai-context-pack">
              <div className="ai-context-pack-head">
                <strong>context_pack · 전체 원문 · 생략 없음</strong>
                <span>{contextPack ? Object.keys(contextPack).length + " sections" : "-"}</span>
              </div>
              <pre className="ai-context-summary" data-region="scroll" tabIndex="0"
                   aria-label="모델 컨텍스트 원문">{copyableContextPack(pack)}</pre>
            </div>
            <div className="ai-context-actions">
              <span>guide_context</span>
              <pre className="ai-context-summary" tabIndex="0" aria-label="guide context">{guideContext}</pre>
              <span>diff_context</span>
              <pre className="ai-context-summary" tabIndex="0" aria-label="diff context">{diffContext}</pre>
              <span>analysis_context</span>
              <pre className="ai-context-summary" tabIndex="0" aria-label="analysis context">{analysisContext}</pre>
              <span>correlation_context</span>
              <pre className="ai-context-summary" tabIndex="0" aria-label="correlation context">{correlationContext}</pre>
            </div>
            <div className="ai-context-actions">
              <strong>forbidden_actions</strong>
              {(pack.forbidden_actions || []).map((item, i) => <span key={i}>{item}</span>)}
            </div>
            <div aria-live="polite" className="mono">
              {copied ? "모델 컨텍스트 원문을 생략 없이 복사했습니다." : ""}
            </div>
            {copyError ? <div role="alert" className="ai-context-empty danger">복사 실패: {copyError}</div> : null}
          </div>
        )}
      </div>
    </section>
  );
}

Object.assign(window, { AIContextPanel });

// Track Z (PR-3) — dual-safe ESM export for bundled module imports.
export { AIContextPanel };
