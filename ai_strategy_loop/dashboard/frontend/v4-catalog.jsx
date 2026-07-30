/* v4-catalog.jsx — V4 "카탈로그" 탭(P4): research_assets.db SELECT-only 읽기 전용 뷰.
 *   /research/summary·judgments·assets 소비. 백엔드가 mode=ro 로만 열어 재계산·쓰기 없음.
 *   부재/오류는 error envelope(available=false)로 조용히 안내(빈 화면 오해 방지).
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_cat, useEffect: useEffect_cat } = React;
import { V4Alpha } from "./v4-alpha.jsx";

function _catVerdictCls(v) {
  const s = String(v || "");
  if (/PASS|양성|생존/.test(s)) return "ok";
  if (/KILL|무가치|기각/.test(s)) return "bad";
  return "warn";
}

// v5.13.0(J1) — 각 뷰가 무엇인지 쉬운 말 설명(explain)을 함께 둔다(용어만 있던 문제).
const _CAT_VIEWS = [
  { key: "chronicle", label: "연혁실", desc: "판정 원장·시리즈 연혁(SELECT-only)",
    explain: "지금까지 연구한 시리즈(연구 묶음)마다 최종 판정(살릴 것/버릴 것)이 어떻게 났는지 모아 놓은 기록실입니다. 같은 실험을 반복하지 않으려면 여기부터 봅니다." },
  { key: "trapmap", label: "함정지도", desc: "실패/기각 판정 패턴 지도",
    explain: "이미 해봤는데 실패·기각으로 끝난 아이디어 목록입니다. 새 가설을 세우기 전에 이 함정 목록과 겹치는지 확인하는 용도입니다." },
  { key: "clauselab", label: "절실험실", desc: "조건 절(clause) 실험 카탈로그",
    explain: "조건식을 문장 단위(절)로 쪼개 '이 절이 성과에 기여하는가'를 실험한 기록입니다. 어떤 절이 밥값을 하는지(load-bearing) 여기서 봅니다." },
  { key: "exitbank", label: "출구은행", desc: "표본·셀·출구 프로파일 은행",
    explain: "언제 파는 게 좋았는지(청산 타이밍)를 시간대·조건 셀별로 쌓아 둔 저장소입니다. 매도식 개선 재료를 여기서 꺼냅니다." },
  { key: "alpha", label: "진행 관찰", desc: "알파랩 진행 관찰(사전등록·원장·퍼널, 비-P4 영수증)",
    explain: "알파 연구 프로그램이 사전등록 → 실험 → 판정 퍼널을 규칙대로 밟았는지 관찰하는 화면입니다." },
  { key: "scorecard", label: "B1 scorecard", desc: "표본 외 성적표(운용 개시 선행)",
    explain: "B1 후보가 표본 밖(실전에 가까운 구간)에서 어떤 성적을 냈는지 보는 성적표입니다. 운용 개시 결정에 선행하는 증거입니다." },
  { key: "qsp", label: "QSP 라운드", desc: "다후보 라운드 보드(round_runner 기록, 읽기 전용)",
    explain: "퀀트 채점 파이프라인(QSP)의 다후보 개선 라운드 기록입니다. 라운드마다 후보 N개의 성적·베스트·교훈·수렴/발산 판정을 봅니다 — 구조해석의 잔차 수렴 로그에 해당합니다." },
];

function _CatSkeleton({ title, reason }) {
  return (
    <div className="v4-cat-skeleton research-empty" role="note">
      <b>{title}</b>
      <p className="mono">{reason}</p>
    </div>
  );
}

// v5.13.0(J1) — 머리글 없는 값 나열 표를 컬럼명 있는 표로(어느 열이 무엇인지 안 보이던 문제).
function _CatTable({ rows }) {
  const list = (rows || []).slice(0, 200);
  if (!list.length) return null;
  const cols = Object.keys(list[0]).slice(0, 6);
  return (
    <table className="mono v4-catalog-table">
      <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>
        {list.map((row, i) => (
          <tr key={i}>{cols.map(c => <td key={c}>{String(row[c] == null ? "—" : row[c])}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

function V4Catalog({ baseUrl, wsStatus }) {
  const [summary, setSummary] = useState_cat(null);
  const [judgments, setJudgments] = useState_cat(null);
  const [assets, setAssets] = useState_cat(null);
  const [clauses, setClauses] = useState_cat(null);
  const [cells, setCells] = useState_cat(null);
  const [qspRounds, setQspRounds] = useState_cat(null);   // v5.13.4(P3) — QSP 라운드 보드.
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
    // QSP 라운드는 독립 fetch(다른 카탈로그 API 실패와 무관하게 표시).
    get("/qsp/rounds").then(j => { if (!cancelled) setQspRounds(j); }).catch(() => { if (!cancelled) setQspRounds({ rounds: [] }); });
    return () => { cancelled = true; };
  }, [baseUrl]);

  const unavailable = summary && summary.available === false;
  const NO_DATA = "데이터 없음 · 운용 개시·U-4·data-vessel 선행 증거가 없어 골격만 표시(performance_proved=false).";
  // 함정지도: 실패/기각/무가치 판정 = 재시도 금지 함정 목록(실측 verdict 어휘: KILL·무가치·기각).
  const traps = (judgments && judgments.available ? judgments.judgments : []).filter(j => /kill|무가치|기각|실패|fail|reject/i.test(String(j.verdict)));

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
      {(() => {
        const cur = _CAT_VIEWS.find(item => item.key === view) || _CAT_VIEWS[0];
        return (
          <div className="v4-cat-viewdesc" role="status">
            <b>{cur.label}</b>
            <span>{cur.explain || cur.desc}</span>
            <i>{cur.desc} · 읽기 전용 · 성능 증명 아님</i>
          </div>
        );
      })()}

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
              <_CatTable rows={clauses.clauses} />
            </div>
          ) : <_CatSkeleton title="절실험실" reason={NO_DATA} />}
        </section>
      )}

      {view === "exitbank" && (
        <section aria-label="출구은행">
          {cells && cells.available && cells.count > 0 ? (
            <div className="v4-catalog-assets-scroll" data-region="scroll" tabIndex={0}>
              <p className="mono">표본·셀 {cells.count}건 (읽기 전용)</p>
              <_CatTable rows={cells.cells} />
            </div>
          ) : <_CatSkeleton title="출구은행" reason={NO_DATA} />}
        </section>
      )}

      {view === "alpha" && (
        <section aria-label="진행 관찰 (구 Alpha Lab)">
          <V4Alpha baseUrl={baseUrl} wsStatus={wsStatus} />
        </section>
      )}

      {view === "qsp" && (
        <section aria-label="QSP 다후보 라운드 보드">
          {!qspRounds && <p className="mono" style={{ color: "var(--ink-3)" }}>라운드 기록 로딩…</p>}
          {qspRounds && (qspRounds.rounds || []).length === 0 && (
            <div className="research-empty">라운드 기록 없음 — round_runner 실행 시 여기 쌓입니다.</div>
          )}
          {(qspRounds && qspRounds.rounds || []).map((r, i) => (
            <div key={i} className="panel" style={{ marginBottom: 10 }}>
              <div className="panel-hd">
                <div className="panel-hd-title">
                  <span className="dot" style={{ background: r.judgment && r.judgment.state === "diverged" ? "var(--red)" : r.judgment && r.judgment.state === "converged" ? "var(--teal)" : "var(--blue)" }}></span>
                  {r.tag} · 라운드 {r.round}
                  <span className={"badge " + (r.judgment && r.judgment.state === "continue" ? "idle" : r.judgment && r.judgment.state === "converged" ? "done" : "warn")} style={{ marginLeft: 8 }}>
                    {r.judgment ? r.judgment.state : "?"}
                  </span>
                </div>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>run {r.run_id}</span>
              </div>
              <div className="panel-bd">
                <p className="mono" style={{ fontSize: 11, color: "var(--ink-2)", margin: "0 0 8px" }}>{r.judgment && r.judgment.reason}</p>
                <table className="mono" style={{ width: "100%", fontSize: 11 }}>
                  <thead><tr><th style={{ textAlign: "left" }}>후보</th><th>objective</th><th>손익</th><th>MDD</th><th>거래</th><th>gate</th></tr></thead>
                  <tbody>
                    {(r.results || []).map((c, k) => (
                      <tr key={k} style={{ color: r.best && c.buy_name === r.best.buy_name ? "var(--teal)" : undefined }}>
                        <td>{c.pair_label}{r.best && c.buy_name === r.best.buy_name ? " ★" : ""}</td>
                        <td style={{ textAlign: "right" }}>{c.objective != null ? Math.round(c.objective).toLocaleString("ko-KR") : "—"}</td>
                        <td style={{ textAlign: "right" }}>{c.profit != null ? Math.round(c.profit).toLocaleString("ko-KR") : "—"}</td>
                        <td style={{ textAlign: "right" }}>{c.mdd != null ? Number(c.mdd).toFixed(1) : "—"}</td>
                        <td style={{ textAlign: "right" }}>{c.trade_count ?? "—"}</td>
                        <td style={{ textAlign: "center" }}>{c.gate_passed ? "✓" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(r.lessons || []).length > 0 && (
                  <p className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", margin: "8px 0 0" }}>
                    교훈: {(r.lessons || []).map(l => `${l.axis}@${l.leaf} Δ${Math.round(l.delta_vs_base).toLocaleString("ko-KR")}`).join(" · ")}
                  </p>
                )}
              </div>
            </div>
          ))}
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
