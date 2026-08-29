/* v4-current-history-authority.jsx — UX-05 current canonical vs historical boundary. */
const { useCallback: useCallback_ch5, useEffect: useEffect_ch5, useState: useState_ch5 } = React;

function _ch5VerifiedDate(value) {
  const parsed = new Date(String(value || ""));
  return Number.isNaN(parsed.valueOf()) ? "미기록" : parsed.toISOString().slice(0, 10);
}

function CurrentHistoryAuthority({ baseUrl, onNavigate, surface }) {
  const [view, setView] = useState_ch5({ status: "loading", data: null, error: "" });
  const load = useCallback_ch5(() => {
    const controller = new AbortController();
    setView(current => ({ ...current, status: "loading", error: "" }));
    fetch(String(baseUrl || "").replace(/\/$/, "") + "/research-result/current", { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(data => setView({ status: "ready", data, error: "" }))
      .catch(error => { if (error && error.name !== "AbortError") setView({ status: "error", data: null, error: String(error.message || error) }); });
    return () => controller.abort();
  }, [baseUrl]);
  useEffect_ch5(() => load(), [load]);
  if (view.status === "loading" && !view.data) return <section className="ch5-boundary pending" aria-live="polite"><h2>현재 판정 권위를 확인하는 중입니다</h2><p>봉인된 최신 결과를 검증한 뒤 과거 기록을 표시합니다.</p></section>;
  if (view.status === "error") return <section className="ch5-boundary danger" role="alert"><h2>현재 판정 확인 불가</h2><p>과거 결과를 현재 판정으로 사용하지 마세요 · {view.error}</p><button type="button" className="btn ghost sm" onClick={load}>다시 확인</button></section>;
  const data = view.data || {};
  const decision = data.decision || {};
  const analysis = data.analysis || {};
  const pageLabel = surface === "workbench" ? "성과·명예의 전당" : "기록·아카이브";
  return (
    <section className="ch5-boundary" aria-label="현재 판정과 과거 기록 권위 경계">
      <header className="ch5-heading"><div><span>UX-05 · AUTHORITY BOUNDARY</span><h2>{pageLabel} 권위 확인</h2></div><strong>CURRENT FIRST</strong></header>
      <div className="ch5-grid">
        <article className="ch5-current">
          <span>CURRENT CANONICAL</span>
          <h3>Development Rule {decision.development_pass_count || 0}/{decision.candidate_count || 0} · STOP</h3>
          <p>실행은 완료됐지만 현재 승격 가능한 경제 후보는 없습니다.</p>
          <dl><div><dt>authority</dt><dd>{data.authority || "UNKNOWN"}</dd></div><div><dt>verified-at</dt><dd>{_ch5VerifiedDate(analysis.generated_at)}</dd></div><div><dt>holdout</dt><dd>{decision.holdout_status || "UNKNOWN"}</dd></div></dl>
          <button type="button" className="btn primary sm" onClick={() => onNavigate("research")}>최신 Mission Control 열기</button>
        </article>
        <article className="ch5-historical">
          <div className="ch5-watermark">HISTORICAL ONLY</div>
          <span>ARCHIVE AUTHORITY</span>
          <h3>{surface === "workbench" ? "아래 명예의 전당은 과거 비교 기록" : "아래 run·세대는 과거 실행 기록"}</h3>
          <p>과거 기록은 현재 승격 근거가 아닙니다. 과거 수익·점수·winner는 당시 기간과 권위 안에서만 해석합니다.</p>
          <ul><li>현재 STOP을 덮지 않음</li><li>OOS·실전 증거로 자동 변환하지 않음</li><li>자동채택·Export 권한 없음</li></ul>
        </article>
      </div>
      <footer>현재 판정 → 과거 탐색 순서 · read only · persistence none</footer>
    </section>
  );
}

Object.assign(window, { CurrentHistoryAuthority });
export { CurrentHistoryAuthority };
