/* v4-alpha.jsx — V4 "Alpha" 탭: 알파 연구 랩(PR #108) 진행 관찰.
 *   ⚠ 임시 관찰 화면(비-P4). 정본 데이터 계약은 P4(research_assets.db + /research/*)이며
 *   이 탭은 봉인된 P4 구현이 아니다 — /api/alpha/{status,funnel,rules} 를 read-only 로 읽어
 *   서버가 내려준 값만 표시한다(재계산·승급/검증 신호 없음).
 *   2026-07-17 검토 정정: 퍼널·판정은 실제 rho_gate·rho_retrial 영수증 기준으로 교정됨.
 */
const {
  useState: useState_va,
  useEffect: useEffect_va,
  useCallback: useCallback_va,
  useRef: useRef_va,
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
  { key: "engine_checked", label: "엔진 대상" },
  { key: "gate_passed", label: "성능게이트 통과" },
];

function V4Alpha({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const [status, setStatus] = useState_va(null);
  const [funnel, setFunnel] = useState_va(null);
  const [rules, setRules] = useState_va(null);
  const [error, setError] = useState_va("");
  // §4.5: 요청 세대 카운터 — interval/base 변경 시 이전 응답이 최신 상태를 덮지 않게 한다.
  const reqGenRef = useRef_va(0);

  const load = useCallback_va(() => {
    if (isDemo || !baseUrl) { setStatus(null); setFunnel(null); setRules(null); return; }
    const gen = ++reqGenRef.current;
    Promise.allSettled([
      _vaFetch(baseUrl + "/api/alpha/status"),
      _vaFetch(baseUrl + "/api/alpha/funnel"),
      _vaFetch(baseUrl + "/api/alpha/rules"),
    ]).then(([s, f, r]) => {
      if (gen !== reqGenRef.current) return; // 더 최신 요청이 있으면 폐기
      setStatus(s.status === "fulfilled" ? s.value : null);
      setFunnel(f.status === "fulfilled" ? f.value : null);
      setRules(r.status === "fulfilled" ? r.value : null);
      const firstErr = [s, f, r].find(x => x.status === "rejected");
      setError(firstErr ? String(firstErr.reason && firstErr.reason.message || firstErr.reason) : "");
    });
  }, [baseUrl, isDemo]);

  useEffect_va(() => {
    load();
    const id = setInterval(load, 30000);
    return () => { reqGenRef.current++; clearInterval(id); }; // 언마운트 시 진행 응답 무효화
  }, [load]);

  const prereg = (status && status.preregistration) || {};
  const ledger = (status && status.ledger) || {};
  const verdict = (funnel && funnel.verdict) || (status && status.verdict) || {};
  const funnelMax = funnel
    ? Math.max(1, ..._VA_FUNNEL_STAGES.map(s => Number(funnel[s.key]) || 0))
    : 1;
  const ruleRows = (rules && Array.isArray(rules.rules)) ? rules.rules : [];
  const statusAvailable = !!(status && status.available);
  // §4.3: sealed 는 present 아닌 sealed 플래그(정상 JSON + SHA 일치)로만 판정.
  const sealedLabel = prereg.sealed
    ? (prereg.program || "sealed")
    : prereg.present
      ? "봉인 미완(파일 존재하나 미봉인)"
      : "미존재";
  const shaLabel = prereg.sha256_match === true ? "SHA 일치 ✓"
    : prereg.sha256_match === false ? "SHA 불일치 ✗"
      : "SHA 미검증";

  return (
    <div className="v4-alpha">
      {/* §4.6: 비-P4 임시 관찰 화면임을 항상 명시 */}
      <div style={{ padding: "6px 16px", background: "#3a2e0c", color: "#f0d38a", fontSize: 12, borderRadius: 6, marginBottom: 10 }}>
        임시 관찰 화면(비-P4) · 정본 데이터 계약은 <b>P4 research_assets.db + /research/*</b> 입니다. 이 탭은 봉인된 P4 구현이 아니며 영수증을 직접 읽어 표시합니다.
      </div>

      <section className="panel" aria-labelledby="v4-alpha-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-alpha-title">알파 연구 랩 · 진행 관찰</div>
            <div className="mono">사전등록 봉인 · n_trials 원장 · 최종 판정 (읽기 전용 · PR #108 자산)</div>
          </div>
        </header>
        <div className="panel-bd">
          {isDemo && <p className="mono" aria-live="polite">예시 소스 · 운영 알파 산출물과 분리된 데이터입니다.</p>}
          {!isDemo && !statusAvailable && (
            <div className="research-empty" role="status">
              알파 연구 산출물 대기 · 사전등록/원장/판정 파일이 아직 없습니다{error ? " · " + error : ""}.
              <div className="mono">경로: {(status && status.run_dir) || "docs/research/condition_research/research_runs/…"}</div>
            </div>
          )}
          {statusAvailable && (
            <div className="v4-alpha-status" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
              <div className="cell">
                <div className="stom-section-label">최종 판정</div>
                <div className="value mono" style={{ color: verdict.available ? "var(--teal, #4cd6b3)" : "var(--ink-2)" }}>
                  {verdict.available ? (verdict.verdict || "\u2014") : "판정 대기"}
                </div>
                <div className="mono" style={{ color: "var(--ink-2)" }}>
                  {verdict.rho != null ? "rho=" + Number(verdict.rho).toFixed(4) : ""}
                  {verdict.final ? " · final" : ""}{verdict.source ? " · " + verdict.source.replace(".json", "") : ""}
                </div>
              </div>
              <div className="cell">
                <div className="stom-section-label">사전등록 봉인</div>
                <div className="value mono" style={{ color: prereg.sealed ? "var(--ink-0)" : "var(--red)" }}>{sealedLabel}</div>
                <div className="mono" style={{ color: prereg.sha256_match === false ? "var(--red)" : "var(--ink-2)" }}>
                  {shaLabel}{prereg.sealed_date ? " · " + prereg.sealed_date : ""}
                </div>
              </div>
              <div className="cell">
                <div className="stom-section-label">n_trials 원장</div>
                <div className="value mono">{_vaNum(ledger.total)}</div>
                <div className="mono" style={{ color: "var(--ink-2)" }}>
                  {_vaNum(ledger.entries)} 항목{ledger.malformed_lines ? " · 손상 " + ledger.malformed_lines : ""} · stage {(status && status.stage) || "\u2014"}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="panel" aria-labelledby="v4-alpha-funnel-title">
        <header className="panel-hd">
          <div className="stom-section-label" id="v4-alpha-funnel-title">발견 → 측정성공 퍼널</div>
        </header>
        <div className="panel-bd">
          {!funnel || !funnel.available ? (
            <div className="research-empty" role="status">퍼널 데이터 대기 · mining/translation/registration/verdict 영수증이 필요합니다.</div>
          ) : (
            <div className="v4-alpha-funnel" style={{ display: "grid", gap: 6 }}>
              {_VA_FUNNEL_STAGES.map(stage => {
                const v = Number(funnel[stage.key]) || 0;
                const pct = Math.round((v / funnelMax) * 100);
                return (
                  <div key={stage.key} style={{ display: "grid", gridTemplateColumns: "132px 1fr 60px", alignItems: "center", gap: 8 }}>
                    <span className="mono">{stage.label}</span>
                    <span style={{ background: "var(--panel-2, #12202c)", borderRadius: 6, height: 18, position: "relative", overflow: "hidden" }}>
                      <i style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: pct + "%", background: "linear-gradient(90deg, var(--teal, #4cd6b3), var(--violet, #8c63ff))", borderRadius: 6 }} />
                    </span>
                    <span className="mono num" style={{ textAlign: "right" }}>{_vaNum(v)}</span>
                  </div>
                );
              })}
              {verdict.coverage && (
                <p className="mono" style={{ color: "var(--ink-2)" }}>
                  봉인 {_vaNum(verdict.coverage.n_rules_sealed)} · 측정 완료 {_vaNum(verdict.coverage.measured_ok)} · 검열 {_vaNum(verdict.coverage.censored_timeout)}
                  {" · 성능게이트 통과 "}{_vaNum(verdict.performance_gate_passed)}
                  {" — 집합 rho 게이트(" + (verdict.verdict || "\u2014") + ")와 개별 성능게이트는 별개"}
                </p>
              )}
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
                    <th style={{ textAlign: "left" }}>번역식 (expr)</th>
                    <th style={{ textAlign: "left" }}>검증</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleRows.slice(0, 200).map((rule, i) => {
                    const isObj = rule && typeof rule === "object";
                    const rid = isObj ? (rule.rule_id || rule.id || rule.name || ("#" + (i + 1))) : String(rule);
                    const tr = isObj && rule.translation ? rule.translation : null;
                    // §4.2: translation_receipt 스키마 정본 필드 expr / buy_statement 를 우선 읽는다.
                    const trText = tr ? (tr.expr || tr.buy_statement || tr.rule || "\u2014") : "\u2014";
                    const validated = tr && tr.validated;
                    const reasons = tr && Array.isArray(tr.reasons) ? tr.reasons.join(", ") : "";
                    const validLabel = tr == null ? "\u2014" : validated === true ? "valid ✓" : validated === false ? ("invalid" + (reasons ? " · " + reasons : "")) : "?";
                    return (
                      <tr key={i} style={{ borderTop: "1px solid var(--line, #1e2b38)" }}>
                        <td className="mono" style={{ padding: "4px 6px", whiteSpace: "nowrap" }}>{rid}</td>
                        <td className="mono" style={{ padding: "4px 6px", maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis" }}>{trText}</td>
                        <td className="mono" style={{ padding: "4px 6px", color: validated === false ? "var(--red)" : "var(--ink-2)" }}>{validLabel}</td>
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
