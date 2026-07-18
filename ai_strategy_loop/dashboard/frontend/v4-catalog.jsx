/* v4-catalog.jsx — V4 "카탈로그" 탭(P4): research_assets.db SELECT-only 읽기 전용 뷰.
 *   /research/summary·judgments·assets 소비. 백엔드가 mode=ro 로만 열어 재계산·쓰기 없음.
 *   부재/오류는 error envelope(available=false)로 조용히 안내(빈 화면 오해 방지).
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_cat, useEffect: useEffect_cat } = React;

function _catVerdictCls(v) {
  const s = String(v || "");
  if (/PASS|양성|생존/.test(s)) return "ok";
  if (/KILL|무가치|기각/.test(s)) return "bad";
  return "warn";
}

function V4Catalog({ baseUrl }) {
  const [summary, setSummary] = useState_cat(null);
  const [judgments, setJudgments] = useState_cat(null);
  const [assets, setAssets] = useState_cat(null);
  const [err, setErr] = useState_cat("");

  useEffect_cat(() => {
    if (!baseUrl) return undefined;
    let cancelled = false;
    const get = (p) => fetch(baseUrl + p, { signal: AbortSignal.timeout(6000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
    Promise.all([get("/research/summary"), get("/research/judgments"), get("/research/assets?limit=200")])
      .then(([s, j, a]) => { if (!cancelled) { setSummary(s); setJudgments(j); setAssets(a); } })
      .catch(e => { if (!cancelled) setErr(String(e && e.message ? e.message : e)); });
    return () => { cancelled = true; };
  }, [baseUrl]);

  const unavailable = summary && summary.available === false;

  return (
    <section className="v4-catalog" aria-labelledby="v4-catalog-heading">
      <h2 id="v4-catalog-heading" className="panel-hd-title">연구 카탈로그 (P4) · 읽기 전용</h2>
      <p className="v4-catalog-safe mono" role="note">research_assets.db SELECT-only · 재계산·쓰기 없음(mode=ro)</p>
      {err && <div className="research-empty danger">{err}</div>}
      {unavailable && (
        <div className="research-empty">카탈로그 DB 없음 · <span className="mono">{summary.hint || "build_research_catalog.py"}</span></div>
      )}
      {summary && summary.available && (
        <div className="v4-catalog-counts">
          {Object.entries(summary.counts).map(([k, v]) => (
            <div key={k} className="v4-catalog-count"><b>{v == null ? "—" : v}</b><span>{k}</span></div>
          ))}
        </div>
      )}
      {judgments && judgments.available && (
        <section aria-label="판정카드">
          <h3 className="stom-section-label">판정카드 · {judgments.count}건</h3>
          <div className="v4-catalog-judgments">
            {judgments.judgments.map(j => (
              <div key={j.series} className="v4-catalog-jcard">
                <div className="v4-catalog-jhead">
                  <b>{j.series}</b>
                  <span className={"v4-chip " + _catVerdictCls(j.verdict)}>{j.verdict}</span>
                </div>
                <div className="mono v4-catalog-jmeta">원장 {j.n_ledger_rows}행{j.report_path ? " · " + j.report_path : ""}</div>
              </div>
            ))}
          </div>
        </section>
      )}
      {assets && assets.available && (
        <section aria-label="자산 목록">
          <h3 className="stom-section-label">자산 · {assets.count}건</h3>
          <div className="v4-catalog-assets-scroll" data-region="scroll" tabIndex={0} aria-label="연구 자산 표">
            <table className="mono v4-catalog-table">
              <thead><tr><th>asset</th><th>kind</th><th>status</th><th>window</th><th>summary</th></tr></thead>
              <tbody>
                {assets.assets.map(a => (
                  <tr key={a.asset_id}>
                    <td>{a.asset_id}</td><td>{a.kind}</td><td>{a.status_tag}</td>
                    <td>{a.window}</td><td className="v4-catalog-sum">{a.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </section>
  );
}

Object.assign(window, { V4Catalog });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Catalog };
