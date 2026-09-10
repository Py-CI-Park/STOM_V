/* bt-feature-map.jsx — QSP3 P4: 다차원 수익률 맵 탐색기.
 *
 *   목적(사용자 방법론): "여러 조건 구분을 가지고 수익률의 분포를 최대한 많은
 *   요소로 시각화 — 변수도 선택하고 전체 맵도 보여주는" 화면. X·Y 변수를 자유
 *   선택해 분위 구간 손익 히트맵(값+거래수 병기)을 보고, [손실 영역 랭킹] 모드로
 *   "어떤 매수 특징이 크게 잃는가"의 자동 후보 목록을 본다 — 제거/필터의 입력.
 *
 *   데이터: GET /bt/analysis/feature_map (job_id 또는 run_id+gen_no).
 *   색: 손익 다이버징(손실 red ↔ 이익 teal, 0 중점) — 셀에 수치 병기(색 단독 금지).
 */
import { useState_btc, useEffect_btc } from "./bt-chart-utils.jsx";
import { useFeatureEvidence, FeatureQualityNotice } from "./bt-feature-evidence.jsx";

const _FM_METRICS = [
  ["pnl", "손익 합"], ["mean_ret", "평균수익률"], ["win_rate", "승률"], ["n", "거래수"],
];

function _fmCellColor(metric, v, vmax) {
  if (v == null || !Number.isFinite(v)) return "var(--bg-2)";
  let t;
  if (metric === "pnl") t = vmax ? Math.max(-1, Math.min(1, v / vmax)) : 0;
  else if (metric === "mean_ret") t = Math.max(-1, Math.min(1, v / 0.8));
  else if (metric === "win_rate") t = Math.max(-1, Math.min(1, (v - 0.5) / 0.3));
  else return "var(--bg-2)";                        // 거래수는 색 없이 수치만.
  return t >= 0 ? `rgba(76,214,179,${0.10 + 0.55 * t})` : `rgba(255,107,107,${0.10 + 0.55 * -t})`;
}

function _fmFmt(metric, v) {
  if (v == null || !Number.isFinite(v)) return "—";
  if (metric === "pnl") return `${(v / 1e6).toFixed(1)}M`;
  if (metric === "mean_ret") return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
  if (metric === "win_rate") return `${(v * 100).toFixed(0)}%`;
  return String(v);
}

function BtFeatureMap({ baseUrl, jobId, evoSource, isDemo, sourceHash }) {
  const [catalog, setCatalog] = useState_btc({key:"",variables:[]});
  const [x, setX] = useState_btc("");
  const [y, setY] = useState_btc("");
  const [metric, setMetric] = useState_btc("pnl");
  const [bins, setBins] = useState_btc(5);
  const [view, setView] = useState_btc("map");        // map | regions
  const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);
  const srcQs = jobId
    ? `job_id=${encodeURIComponent(jobId)}`
    : (isEvo ? `run_id=${encodeURIComponent(evoSource.run_id)}&gen_no=${evoSource.gen_no}` : "");

  const sourceKey=JSON.stringify([baseUrl,srcQs,!!isDemo,sourceHash]);
  const path=view==="regions" ? `/bt/analysis/feature_map?${srcQs}&mode=regions&bins=${bins}&top=20`
    : `/bt/analysis/feature_map?${srcQs}&x=${encodeURIComponent(x)}`+(y?`&y=${encodeURIComponent(y)}`:"")+`&bins=${bins}`;
  const query=useFeatureEvidence({baseUrl,paths:[path],enabled:!isDemo&&!!srcQs&&!!baseUrl,expectedHash:sourceHash});
  const payload=query.payloads?.[0]||null;
  const vars_=catalog.key===sourceKey?catalog.variables:[];
  useEffect_btc(()=>{setX("");setY("");setCatalog({key:sourceKey,variables:[]});},[sourceKey]);
  useEffect_btc(()=>{
    if(!payload || !Array.isArray(payload.variables)) return;
    const vs=payload.variables;
    setCatalog({key:sourceKey,variables:vs});
    if(vs.length && (!x || !vs.includes(x))) setX(vs.includes("B_등락율")?"B_등락율":vs[0]);
    if(y && !vs.includes(y)) setY("");
  },[payload,sourceKey,x,y]);
  const blocked=query.error || query.mismatch || payload?.analysis_ready===false;
  const data=!blocked && view==="map"?payload:null;
  const regions=!blocked && view==="regions"?payload:null;

  const grid = data && data.grid;
  const cells = (grid && grid.cells) || [];
  const xBins = [...new Set(cells.map((c) => c.x_bin))];
  const yBins = y ? [...new Set(cells.map((c) => c.y_bin))] : [null];
  const byKey = {};
  cells.forEach((c) => { byKey[`${c.x_bin}|${c.y_bin}`] = c; });
  const vmax = Math.max(1, ...cells.map((c) => Math.abs(c.pnl || 0)));
  const sel = (val, set, opts, label) => (
    <label className="bt-fm-sel">{label}
      <select value={val} onChange={(e) => set(e.target.value)}>{opts}</select>
    </label>
  );
  const varOpts = (allowEmpty) => [
    ...(allowEmpty ? [<option key="" value="">(없음)</option>] : []),
    ...vars_.map((v) => <option key={v} value={v}>{v}</option>),
  ];

  return (
    <div className="panel bt-equal-card" role="figure" aria-label="다차원 수익률 맵">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>다차원 수익률 맵 (QSP3)</div>
        <div className="panel-hd-meta">
          <button className={`bt-fm-toggle ${view === "map" ? "on" : ""}`} onClick={() => setView("map")}>맵</button>
          <button className={`bt-fm-toggle ${view === "regions" ? "on" : ""}`} onClick={() => setView("regions")}>손실 영역 랭킹</button>
        </div>
      </div>
      <div className="panel-bd">
        <p className="bt-fm-help">전체 결과 CSV 기준 · 선택 구간 필터 미적용</p>
        {blocked && <FeatureQualityNotice payload={payload} title="피처 맵 보류" reason={query.error||(query.mismatch?"선택한 결과와 분석 원본의 일치를 확인할 수 없습니다. 결과를 다시 조회하세요.":"")}/>}
        {query.loading && <p role="status">피처 자료를 확인하고 있습니다…</p>}
        {!blocked && view === "map" && (
          <div>
            <div className="bt-fm-controls">
              {sel(x, setX, varOpts(false), "X축")}
              {sel(y, setY, varOpts(true), "Y축")}
              {sel(metric, setMetric, _FM_METRICS.map(([k, l]) => <option key={k} value={k}>{l}</option>), "표시")}
              {sel(String(bins), (v) => setBins(parseInt(v, 10)), [3, 4, 5, 8, 10].map((b) => <option key={b} value={b}>{b}구간</option>), "구간")}
            </div>
            {!cells.length ? (
              <div className="research-empty">{isDemo ? "데모에선 미지원" : query.loading ? "피처 자료를 확인하고 있습니다…" : data?.analysis_ready===true ? (vars_.length?"선택한 변수의 집계 가능한 구간이 없습니다.":"표본·분산 요건을 충족하는 진입 변수가 없습니다."):"분석 자료를 선택하고 변수를 확인하세요."}</div>
            ) : (
              <div className="bt-fm-scroll">
                <table className="bt-fm-grid">
                  <thead>
                    <tr><th>{y ? `${y} ↓ / ${x} →` : x}</th>
                      {xBins.map((b) => <th key={b} title={b}>{b}</th>)}</tr>
                  </thead>
                  <tbody>
                    {yBins.map((yb) => (
                      <tr key={String(yb)}>
                        <th title={String(yb || "")}>{yb == null ? "전체" : yb}</th>
                        {xBins.map((xb) => {
                          const c = byKey[`${xb}|${yb}`];
                          const v = c ? c[metric] : null;
                          return (
                            <td key={xb} style={{ background: _fmCellColor(metric, v, vmax) }}
                                title={c ? `${x}=${xb}${y ? ` · ${y}=${yb}` : ""} · ${c.n}건 · 손익 ${Math.round(c.pnl).toLocaleString()}원 · 평균 ${c.mean_ret.toFixed(2)}% · 승률 ${(c.win_rate * 100).toFixed(0)}%` : ""}>
                              <b>{_fmFmt(metric, v)}</b>
                              <span>{c ? `${c.n}건` : ""}</span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        {!blocked && view === "regions" && (
          <div>
            {!(regions && regions.regions && regions.regions.length) ? (
              <div className="research-empty">{query.loading?"손실 구간을 확인하고 있습니다…":regions?.analysis_ready===true?"현재 자료와 조건에서 산출된 손실 구간이 없습니다.":"분석 자료를 확인하세요."}</div>
            ) : (
              <table className="bt-fm-rank">
                <thead><tr><th>#</th><th>변수</th><th>구간</th><th>거래</th><th>손익 합</th></tr></thead>
                <tbody>
                  {regions.regions.map((r, i) => (
                    <tr key={`${r.feature}|${r.bin}`}>
                      <td>{i + 1}</td><td>{r.feature}</td><td className="num">{r.bin}</td>
                      <td className="num">{r.n.toLocaleString()}</td>
                      <td className="num neg">{Math.round(r.pnl).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="bt-fm-help">"이 매수 특징 = 손실" 자동 후보 — QSP3 제거/필터 제안의 입력과 같은 계산이다.
              채택은 항상 재백테 실측(재유입 효과 21~38% 실증) + 홀드아웃 동방향.</div>
          </div>
        )}
      </div>
    </div>
  );
}

// dual-safe ESM export. KEEP on ONE physical line.
export { BtFeatureMap };
