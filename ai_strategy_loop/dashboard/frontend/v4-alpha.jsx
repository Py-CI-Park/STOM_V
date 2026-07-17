/* v4-alpha.jsx — V4 "Alpha" 탭: 알파 연구 랩(PR #108) 진행 상태 관찰.
 *   /api/alpha/status · /funnel · /rules 만 읽고(read-only), 서버가 내려준 값만 표시한다.
 *   조건식/성과를 클라이언트에서 재구성하지 않으며 승급/검증 신호를 발신하지 않는다(탐색 표시만).
 *   산출물이 없으면(available:false) 빈 상태로 흡수하고 절대 추측하지 않는다.
 */
const {
  useState: useState_va,
  useEffect: useEffect_va,
  useCallback: useCallback_va,
} = React;

function _vaNum(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  return Number(value).toLocaleString();
}

function _vaFetch(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 8000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

// 퍼널 6단계 정본(alpha_api.alpha_funnel 반환 키 순서와 일치).
const _VA_FUNNEL_STAGES = [
  { key: "discovered", label: "발견" },
  { key: "fdr_survived", label: "FDR 생존" },
  { key: "translated", label: "번역" },
  { key: "registered", label: "등재" },
  { key: "engine_checked", label: "엔진 확인" },
  { key: "gate_passed", label: "게이트 통과" },
];

function V4Alpha({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const [status, setStatus] = useState_va(null);
  const [funnel, setFunnel] = useState_va(null);
  const [rules, setRules] = useState_va(null);
  const [error, setError] = useState_va("");

  const load = useCallback_va(() => {
    if (isDemo || !baseUrl) { setStatus(null); setFunnel(null); setRules(null); return; }
    let done = false;
    Promise.allSettled([
      _vaFetch(baseUrl + "/api/alpha/status"),
      _vaFetch(baseUrl + "/api/alpha/funnel"),
      _vaFetch(baseUrl + "/api/alpha/rules"),
    ]).then(([s, f, r]) => {
      if (done) return;
      setStatus(s.status === "fulfilled" ? s.value : null);
      setFunnel(f.status === "fulfilled" ? f.value : null);
      setRules(r.status === "fulfilled" ? r.value : null);
      const firstErr = [s, f, r].find(x => x.status === "rejected");
      setError(firstErr ? String(firstErr.reason && firstErr.reason.message || firstErr.reason) : "");
    });
    return () => { done = true; };
  }, [baseUrl, isDemo]);

  useEffect_va(() => {
    const cleanup = load();
    const id = setInterval(load, 30000);
    return () => { if (typeof cleanup === "function") cleanup(); clearInterval(id); };
  }, [load]);

  const prereg = (status && status.preregistration) || {};
  const ledger = (status && status.ledger) || {};
  const funnelMax = funnel
    ? Math.max(1, ..._VA_FUNNEL_STAGES.map(s => Number(funnel[s.key]) || 0))
    : 1;
  const ruleRows = (rules && Array.isArray(rules.rules)) ? rules.rules : [];
  const statusAvailable = !!(status && status.available);

  return (
    <div className="v4-alpha">
      <section className="panel" aria-labelledby="v4-alpha-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-alpha-title">알파 연구 랩 · 진행 관찰</div>
            <div className="mono">사전등록 봉인 · n_trials 원장 · 발견→게이트 퍼널 (읽기 전용 · PR #108 자산)</div>
          </div>
        </header>
        <div className="panel-bd">
          {isDemo && <p className="mono" aria-live="polite">예시 소스 · 운영 알파 산출물과 분리된 데이터입니다.</p>}
          {!isDemo && !statusAvailable && (
            <div className="research-empty" role="status">
              알파 연구 산출물 대기 · 사전등록/원장/퍼널 파일이 아직 없습니다{error ? " · " + error : ""}.
              <div className="mono">경로: {(status && status.run_dir) || "docs/research/condition_research/research_runs/…"}</div>
            </div>
          )}
          {statusAvailable && (
            <div className="v4-alpha-status" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
              <div className="cell">
                <div className="stom-section-label">stage</div>
                <div className="value mono">{status.stage || "\u2014"}</div>
              </div>
              <div className="cell">
                <div className="stom-section-label">사전등록 봉인</div>
                <div className="value mono">{prereg.available ? (prereg.program || "sealed") : "미봉인"}</div>
                <div className="mono" style={{ color: prereg.sha256_match === false ? "var(--red)" : "var(--ink-2)" }}>
                  {prereg.sha256_match === true ? "SHA 일치 ✓" : prereg.sha256_match === false ? "SHA 불일치 ✗" : "SHA 미검증"}
                  {prereg.sealed_date ? " · " + prereg.sealed_date : ""}
                </div>
              </div>
              <div className="cell">
                <div className="stom-section-label">n_trials 원장</div>
                <div className="value mono">{_vaNum(ledger.total)}</div>
                <div className="mono" style={{ color: "var(--ink-2)" }}>
                  {_vaNum(ledger.entries)} 항목{ledger.malformed_lines ? " · 손상 " + ledger.malformed_lines : ""}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="panel" aria-labelledby="v4-alpha-funnel-title">
        <header className="panel-hd">
          <div className="stom-section-label" id="v4-alpha-funnel-title">발견 → 게이트 통과 퍼널</div>
        </header>
        <div className="panel-bd">
          {!funnel || !funnel.available ? (
            <div className="research-empty" role="status">퍼널 데이터 대기 · mining/translation/registration/engine/gate 영수증이 필요합니다.</div>
          ) : (
            <div className="v4-alpha-funnel" style={{ display: "grid", gap: 6 }}>
              {_VA_FUNNEL_STAGES.map(stage => {
                const v = Number(funnel[stage.key]) || 0;
                const pct = Math.round((v / funnelMax) * 100);
                return (
                  <div key={stage.key} style={{ display: "grid", gridTemplateColumns: "120px 1fr 60px", alignItems: "center", gap: 8 }}>
                    <span className="mono">{stage.label}</span>
                    <span style={{ background: "var(--panel-2, #12202c)", borderRadius: 6, height: 18, position: "relative", overflow: "hidden" }}>
                      <i style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: pct + "%", background: "linear-gradient(90deg, var(--teal, #4cd6b3), var(--violet, #8c63ff))", borderRadius: 6 }} />
                    </span>
                    <span className="mono num" style={{ textAlign: "right" }}>{_vaNum(v)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section className="panel" aria-labelledby="v4-alpha-rules-title">
        <header className="panel-hd">
          <div className="stom-section-label" id="v4-alpha-rules-title">규칙 리더보드 (mining × translation 병합)</div>
        </header>
        <div className="panel-bd">
          {!rules || !rules.available ? (
            <div className="research-empty" role="status">규칙 리더보드 대기 · mining_report.json 이 필요합니다.</div>
          ) : ruleRows.length === 0 ? (
            <div className="research-empty" role="status">병합된 규칙이 없습니다(발견 0 또는 FDR 전멸).</div>
          ) : (
            <div data-region="scroll" tabIndex={0} style={{ maxHeight: 360, overflow: "auto" }}>
              <table className="v4-alpha-rules" style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left" }}>규칙</th>
                    <th style={{ textAlign: "left" }}>번역</th>
                    <th style={{ textAlign: "left" }}>메타</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleRows.slice(0, 200).map((rule, i) => {
                    const isObj = rule && typeof rule === "object";
                    const rid = isObj ? (rule.rule_id || rule.id || rule.name || ("#" + (i + 1))) : String(rule);
                    const tr = isObj && rule.translation ? rule.translation : null;
                    const trText = tr ? (tr.expression || tr.text || tr.rule || JSON.stringify(tr)) : "\u2014";
                    const meta = isObj
                      ? Object.entries(rule)
                          .filter(([k]) => !["rule_id", "id", "name", "translation"].includes(k))
                          .slice(0, 4)
                          .map(([k, v]) => k + "=" + (typeof v === "object" ? "…" : v)).join(" · ")
                      : "";
                    return (
                      <tr key={i} style={{ borderTop: "1px solid var(--line, #1e2b38)" }}>
                        <td className="mono" style={{ padding: "4px 6px", whiteSpace: "nowrap" }}>{rid}</td>
                        <td className="mono" style={{ padding: "4px 6px", maxWidth: 380, overflow: "hidden", textOverflow: "ellipsis" }}>{trText}</td>
                        <td className="mono" style={{ padding: "4px 6px", color: "var(--ink-2)" }}>{meta}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="mono" style={{ color: "var(--ink-2)" }}>
                {ruleRows.length > 200 ? "상위 200행 표시 · 전체 " + ruleRows.length + "행" : ruleRows.length + "행"}
                {rules.translation_available ? " · 번역 병합됨" : " · 번역 미가용"}
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

Object.assign(window, { V4Alpha });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Alpha };
