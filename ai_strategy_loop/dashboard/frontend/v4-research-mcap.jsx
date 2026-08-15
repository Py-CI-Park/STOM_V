/* v4-research-mcap.jsx — v5.16 market-cap/native lab, job health and prereg preview. */
const { useEffect: useEffect_rm16, useState: useState_rm16 } = React;

function _rm16BandLabel(band) {
  if (band.lower == null) return `< ${band.upper}억`;
  if (band.upper == null) return `≥ ${band.lower}억`;
  return `${band.lower}~${band.upper}억`;
}

function V516MarketCapNativeLab({ baseUrl }) {
  const root = String(baseUrl || "").replace(/\/$/, "");
  const [data, setData] = useState_rm16({ status: "loading", census: null, health: null, error: "" });
  const [form, setForm] = useState_rm16({ family_id: "ABSORPTION_REVERSAL", compute_hours: 36, entry_variables: 8, exit_variables: 6 });
  const [preview, setPreview] = useState_rm16({ status: "idle", data: null, error: "" });
  useEffect_rm16(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(root + "/research-program/market-cap-census", { signal: controller.signal }).then(r => r.ok ? r.json() : Promise.reject(new Error(`census HTTP ${r.status}`))),
      fetch(root + "/research-program/jobs/health", { signal: controller.signal }).then(r => r.ok ? r.json() : Promise.reject(new Error(`health HTTP ${r.status}`))),
    ]).then(([census, health]) => setData({ status: "ready", census, health, error: "" }))
      .catch(error => { if (error.name !== "AbortError") setData({ status: "error", census: null, health: null, error: String(error.message || error) }); });
    return () => controller.abort();
  }, [root]);
  const submit = event => {
    event.preventDefault();
    if (!data.census) return;
    setPreview({ status: "loading", data: null, error: "" });
    fetch(root + "/research-program/preregistration/preview", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, bands: data.census.bands }),
    }).then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(payload => setPreview({ status: "ready", data: payload, error: "" }))
      .catch(error => setPreview({ status: "error", data: null, error: String(error.message || error) }));
  };
  if (data.status === "loading") return <section className="rm16-panel pending" aria-live="polite"><h2>Market-cap Lab</h2><p>Census와 Job Evidence를 불러오는 중입니다.</p></section>;
  if (data.status === "error") return <section className="rm16-panel danger" role="alert"><h2>Market-cap Lab 요청 실패</h2><p>{data.error}</p></section>;
  const census = data.census || {};
  const health = data.health || {};
  const bandRows = census.data && census.data.bands || [];
  const byId = Object.fromEntries(bandRows.map(row => [row.band_id, row]));
  return (
    <section className="rm16-panel" aria-labelledby="rm16-title">
      <div className="rm16-heading"><div><span>READ-ONLY RESEARCH DESIGN</span><h2 id="rm16-title">Market-cap · Native Tools · Job Health</h2></div><strong>{census.available ? "CENSUS AVAILABLE" : String(census.reason || "SOURCE_UNAVAILABLE").toUpperCase()}</strong></div>
      <div className="rm16-band-grid" role="list" aria-label="시가총액 4개 고정 구간">
        {(census.bands || []).map(band => { const row = byId[band.band_id] || {}; return <article role="listitem" key={band.band_id}><span>{band.band_id}</span><h3>{_rm16BandLabel(band)}</h3><dl><div><dt>거래일</dt><dd>{row.days ?? "—"}</dd></div><div><dt>종목</dt><dd>{row.symbols ?? "—"}</dd></div><div><dt>Event</dt><dd>{row.events ?? "—"}</dd></div><div><dt>판정</dt><dd>{row.verdict || (census.available ? "PENDING_GATE" : "SOURCE_MISSING")}</dd></div></dl></article>; })}
      </div>
      <div className="rm16-two-col">
        <section className="rm16-native"><h3>Native Tools Gate</h3><table><tbody>{[["BackFinder","Census/Event"],["OptimizeConditions","Inner clause"],["Genetic","조건부 구조"],["QMC/TPE","숫자 변수"],["RWFT","Rolling development"]].map(([tool, role]) => <tr key={tool}><th>{tool}</th><td>{role}</td><td>{health.runtime_queue === "not_started" ? "NOT_STARTED" : "EVIDENCE_ONLY"}</td></tr>)}</tbody></table><p>운영 DB hash·sidecar·immutable connector N0 통과 전 실행 금지</p></section>
        <section className="rm16-health"><h3>Compute / Job Health</h3><dl><div><dt>모드</dt><dd>{health.mode || "—"}</dd></div><div><dt>Runtime queue</dt><dd>{health.runtime_queue || "—"}</dd></div><div><dt>Engine terminal</dt><dd>{JSON.stringify(health.engine_terminal_counts || {})}</dd></div><div><dt>Recovered</dt><dd>{health.recovered_terminal_rows ?? 0}</dd></div></dl></section>
      </div>
      <form className="rm16-designer" onSubmit={submit}><h3>Next Research Designer · Preview only</h3><div><label>Family<select value={form.family_id} onChange={e => setForm({ ...form, family_id: e.target.value })}>{["ABSORPTION_REVERSAL","FAILED_BREAKOUT_RETURN","COMPRESSION_CONFIRMED_BREAKOUT","FLOW_PRICE_DIVERGENCE","OPENING_OVERREACTION_MEAN_REVERT"].map(id => <option key={id}>{id}</option>)}</select></label><label>Compute hours<input type="number" min="24" max="48" value={form.compute_hours} onChange={e => setForm({ ...form, compute_hours: Number(e.target.value) })} /></label><label>Entry variables<input type="number" min="1" max="8" value={form.entry_variables} onChange={e => setForm({ ...form, entry_variables: Number(e.target.value) })} /></label><label>Exit variables<input type="number" min="1" max="6" value={form.exit_variables} onChange={e => setForm({ ...form, exit_variables: Number(e.target.value) })} /></label></div><button type="submit" className="btn primary">사전등록 Preview 검증</button><p>Preview는 저장·실행·승인·Export를 수행하지 않습니다.</p>{preview.status === "loading" && <span aria-live="polite">검증 중</span>}{preview.status === "error" && <span role="alert">Preview 실패 · {preview.error}</span>}{preview.status === "ready" && <output>VALID · {preview.data.preview_sha256}</output>}</form>
    </section>
  );
}

Object.assign(window, { V516MarketCapNativeLab });
export { V516MarketCapNativeLab };
