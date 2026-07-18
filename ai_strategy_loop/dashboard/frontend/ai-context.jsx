/* Copyable AI state context pack panel */
const { useState: useState_ac, useEffect: useEffect_ac, useRef: useRef_ac } = React;

function packText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function copyableContextPack(pack) {
  if (!pack || typeof pack !== "object" || !pack.context_pack) return "";
  return JSON.stringify(pack.context_pack, null, 2);
}

function sameContextIdentity(left, right) {
  return !!left && !!right && left.baseUrl === right.baseUrl
    && String(left.runId) === String(right.runId) && String(left.genNo) === String(right.genNo);
}

function contextPackResponseMatchesIdentity(response, identity) {
  const has = Object.prototype.hasOwnProperty;
  return !!response && typeof response === "object" && !Array.isArray(response)
    && (!has.call(response, "base_url") || response.base_url === identity.baseUrl)
    && (!has.call(response, "base") || response.base === identity.baseUrl)
    && (!has.call(response, "run_id") || String(response.run_id) === String(identity.runId))
    && (identity.genNo == null || !has.call(response, "gen_no") || String(response.gen_no) === String(identity.genNo))
    && ((typeof response.error === "string" && response.error)
      || (!!response.context_pack && typeof response.context_pack === "object" && !Array.isArray(response.context_pack)));
}

function AIContextPanel({ baseUrl, wsStatus, runId, genNo }) {
  const [view, setView] = useState_ac({ identity: null, pack: null, loading: false, err: "", copied: false, copyError: "" });
  const requestRef = useRef_ac({ controller: null, generation: 0, identity: null });
  const currentIdentity = { baseUrl, runId, genNo };
  const identityRef = useRef_ac(currentIdentity);
  identityRef.current = currentIdentity;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const viewIsOwned = sameContextIdentity(view.identity, currentIdentity);
  const pack = viewIsOwned ? view.pack : null;
  const loading = viewIsOwned && view.loading;
  const err = viewIsOwned ? view.err : "";
  const copied = viewIsOwned && view.copied;
  const copyError = viewIsOwned ? view.copyError : "";

  const loadPack = React.useCallback(() => {
    const identity = { baseUrl, runId, genNo };
    const request = requestRef.current;
    if (request.controller) request.controller.abort();
    const generation = request.generation + 1;
    request.generation = generation;
    request.controller = null;
    request.identity = identity;
    setView({ identity, pack: null, loading: false, err: "", copied: false, copyError: "" });
    if (isDemo || !baseUrl || !runId) return;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    request.controller = controller;
    const isCurrent = () => {
      const active = requestRef.current;
      return active.controller === controller && active.generation === generation
        && sameContextIdentity(active.identity, identity) && !controller.signal.aborted;
    };
    setView({ identity, pack: null, loading: true, err: "", copied: false, copyError: "" });
    const suffix = genNo != null ? "&gen_no=" + encodeURIComponent(genNo) : "";
    fetch(baseUrl + "/ai_context_pack?run_id=" + encodeURIComponent(runId) + suffix,
          { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(response => {
        if (!isCurrent()) return;
        if (!contextPackResponseMatchesIdentity(response, identity)) {
          setView({ identity, pack: null, loading: false, err: "context pack response identity mismatch", copied: false, copyError: "" });
          return;
        }
        setView({ identity, pack: response, loading: false, err: "", copied: false, copyError: "" });
      })
      .catch(reason => {
        if (!isCurrent()) return;
        setView({ identity, pack: null, loading: false, err: String(reason), copied: false, copyError: "" });
      })
      .finally(() => {
        clearTimeout(timeout);
        if (!isCurrent()) return;
        requestRef.current.controller = null;
        setView(previous => sameContextIdentity(previous.identity, identity)
          ? { ...previous, loading: false } : previous);
      });
  }, [baseUrl, isDemo, runId, genNo]);

  useEffect_ac(() => {
    loadPack();
    return () => {
      const request = requestRef.current;
      if (sameContextIdentity(request.identity, currentIdentity)) {
        if (request.controller) request.controller.abort();
        request.controller = null;
        request.generation += 1;
      }
    };
  }, [loadPack]);

  const copyPack = async () => {
    const identity = identityRef.current;
    const text = copyableContextPack(pack);
    if (!text || !sameContextIdentity(identity, currentIdentity)) return;
    try {
      await navigator.clipboard.writeText(text);
      setView(previous => sameContextIdentity(previous.identity, identity)
        ? { ...previous, copied: true, copyError: "" } : previous);
    } catch (reason) {
      setView(previous => sameContextIdentity(previous.identity, identity)
        ? { ...previous, copied: false, copyError: String(reason) } : previous);
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
