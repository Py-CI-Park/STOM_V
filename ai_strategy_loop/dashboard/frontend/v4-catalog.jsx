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

const _CAT_VIEWS = [
  { key: "chronicle", label: "연혁실", desc: "판정 원장·시리즈 연혁(SELECT-only)" },
  { key: "trapmap", label: "함정지도", desc: "실패/기각 판정 패턴 지도" },
  { key: "clauselab", label: "절실험실", desc: "조건 절(clause) 실험 카탈로그" },
  { key: "exitbank", label: "출구은행", desc: "표본·셀·출구 프로파일 은행" },
  { key: "scorecard", label: "B1 scorecard", desc: "표본 외 성적표(운용 개시 선행)" },
];

function _CatSkeleton({ title, reason }) {
  return (
    <div className="v4-cat-skeleton research-empty" role="note">
      <b>{title}</b>
      <p className="mono">{reason}</p>
    </div>
  );
}

function _catRows(rows) {
  return rows.slice(0, 200).map((c, i) => (
    <tr key={i}>{Object.values(c).slice(0, 6).map((val, k) => <td key={k}>{String(val)}</td>)}</tr>
  ));
}

function V4Catalog({ baseUrl }) {
  const [summary, setSummary] = useState_cat(null);
  const [judgments, setJudgments] = useState_cat(null);
  const [assets, setAssets] = useState_cat(null);
  const [clauses, setClauses] = useState_cat(null);
  const [cells, setCells] = useState_cat(null);
  const [err, setErr] = useState_cat("");
  const [view, setView] = useState_cat("chronicle");

  useEffect_cat(() => {
    if (!baseUrl) return undefined;
    let cancelled = false;
    const get = (p) => fetch(baseUrl + p, { signal: AbortSignal.timeout(6000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
    Promise.all([
      get("/research/summary"), get("/research/judgments"), get("/research/assets?limit=200"),
      get("/research/clauses?limit=200"), get("/research/cells?limit=200"),
    ]).then(([s, j, a, c, ce]) => { if (!cancelled) { setSummary(s); setJudgments(j); setAssets(a); setClauses(c); setCells(ce); } })
      .catch(e => { if (!cancelled) setErr(String(e && e.message ? e.message : e)); });
    return () => { cancelled = true; };
  }, [baseUrl]);

  const unavailable = summary && summary.available === false;
  const NO_DATA = "데이터 없음 · 운용 개시·U-4·data-vessel 선행 증거가 없어 골격만 표시(performance_proved=false).";
  const traps = (judgments && judgments.available ? judgments.judgments : []).filter(j => /fail|reject|경고|기각/i.test(String(j.verdict)));

  return (
    <section className="v4-catalog v4-cjk-safe" aria-labelledby="v4-catalog-heading">
      <h2 id="v4-catalog-heading" className="panel-hd-title">연구 카탈로그 (P4 · 비정본 prototype) · 읽기 전용</h2>
      <p className="v4-catalog-safe mono" role="note">research_assets.db SELECT-only · 재계산·쓰기 없음(mode=ro) · 정본 승격 전 preview</p>
      {err && <div className="research-empty danger">{err}</div>}
      {unavailable && (<div className="research-empty">카탈로그 DB 없음 · <span className="mono">{summary.hint || "build_research_catalog.py"}</span></div>)}

      <div className="v4-cat-viewbar" role="tablist" aria-label="P4 조회 뷰">
        {_CAT_VIEWS.map(v => (
          <button key={v.key} type="button" role="tab" aria-selected={view === v.key}
                  className={"v4-cat-viewtab" + (view === v.key ? " active" : "")}
                  onClick={() => setView(v.key)} title={v.desc}>{v.label}</button>
        ))}
      </div>

      {view === "chronicle" && (
        <section aria-label="연혁실">
          {summary && summary.available && (
            <div className="v4-catalog-counts">
              {Object.entries(summary.counts).map(([k, v]) => (
                <div key={k} className="v4-catalog-count"><b>{v == null ? "—" : v}</b><span>{k}</span></div>
              ))}
            </div>
          )}
          {judgments && judgments.available ? (
            <div className="v4-catalog-judgments">
              {judgments.judgments.map(j => (
                <div key={j.series} className="v4-catalog-jcard">
                  <div className="v4-catalog-jhead"><b>{j.series}</b><span className={"v4-chip " + _catVerdictCls(j.verdict)}>{j.verdict}</span></div>
                  <div className="mono v4-catalog-jmeta">원장 {j.n_ledger_rows}행{j.report_path ? " · " + j.report_path : ""}</div>
                </div>
              ))}
            </div>
          ) : <_CatSkeleton title="연혁실" reason={NO_DATA} />}
          {assets && assets.available && (
            <div className="v4-catalog-assets-scroll" data-region="scroll" tabIndex={0} aria-label="연구 자산 표">
              <h3 className="stom-section-label">자산 · {assets.count}건</h3>
              <table className="mono v4-catalog-table">
                <thead><tr><th>asset</th><th>kind</th><th>status</th><th>window</th><th>summary</th></tr></thead>
                <tbody>
                  {assets.assets.map(a => (<tr key={a.asset_id}><td>{a.asset_id}</td><td>{a.kind}</td><td>{a.status_tag}</td><td>{a.window}</td><td className="v4-catalog-sum">{a.summary}</td></tr>))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {view === "trapmap" && (
        <section aria-label="함정지도">
          {traps.length > 0 ? (
            <ul className="v4-cat-traplist mono">
              {traps.map(j => (<li key={j.series}><b>{j.series}</b> — {j.verdict}{j.note ? " · " + j.note : ""}</li>))}
            </ul>
          ) : <_CatSkeleton title="함정지도" reason={NO_DATA} />}
        </section>
      )}

      {view === "clauselab" && (
        <section aria-label="절실험실">
          {clauses && clauses.available && clauses.count > 0 ? (
            <div className="v4-catalog-assets-scroll" data-region="scroll" tabIndex={0}>
              <p className="mono">절(clause) {clauses.count}건 (읽기 전용)</p>
              <table className="mono v4-catalog-table"><tbody>{_catRows(clauses.clauses)}</tbody></table>
            </div>
          ) : <_CatSkeleton title="절실험실" reason={NO_DATA} />}
        </section>
      )}

      {view === "exitbank" && (
        <section aria-label="출구은행">
          {cells && cells.available && cells.count > 0 ? (
            <div className="v4-catalog-assets-scroll" data-region="scroll" tabIndex={0}>
              <p className="mono">표본·셀 {cells.count}건 (읽기 전용)</p>
              <table className="mono v4-catalog-table"><tbody>{_catRows(cells.cells)}</tbody></table>
            </div>
          ) : <_CatSkeleton title="출구은행" reason={NO_DATA} />}
        </section>
      )}

      {view === "scorecard" && (
        <section aria-label="B1 scorecard">
          <_CatSkeleton title="B1 scorecard (표본 외 성적표)" reason={NO_DATA} />
        </section>
      )}
    </section>
  );
}

Object.assign(window, { V4Catalog });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Catalog };
