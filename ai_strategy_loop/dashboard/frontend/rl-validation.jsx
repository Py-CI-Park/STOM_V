/* rl-validation.jsx — ResearchLab 검증 탭(_ValidationPanel) (research-lab.jsx 에서 분리).

   D1/D2/D4(2026-06-10) — 검증 패널: 연도 분해 · 선택기 미리보기 · 부검 요약.
   읽기 전용 GET 다수(/run_yearly /selector_preview /autopsy /freeze_verdict /ops_status …)만 소비.
   공유 Vdt* 표시 블록은 rl-vdt-shell.jsx, 차트/격자/체크포인트 프리미티브는 rl-analysis.jsx 에서 import.
   (P5.6 분해: 정의 파일만 옮겼고 _ValidationPanel 본문은 그대로다.)
   stom-ui 전역은 import 하지 않는다. 외부 차트 라이브러리 금지.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines } from "./rl-vdt-shell.jsx";
import { _ResearchEmptyState, _rlNum, _rlPeriodFromDays, _GridHeatmap, _EquityChart, _CurveSpark, _McFanChart, _PipelineCheckpointPanel } from "./rl-analysis.jsx";
const {
  useState: useState_rl,
  useEffect: useEffect_rl,
  useCallback: useCallback_rl,
} = React;

/* D1/D2/D4(2026-06-10) — 검증 패널: 연도 분해 · 선택기 미리보기 · 부검 요약.
   읽기 전용 GET 3종(/run_yearly /selector_preview /autopsy)만 소비한다.
   근거: 원인5(연도별 쇠퇴는 합계로 안 보임)·원인1(기준-목표 비정합을 눈으로 확인). */
function _ValidationPanel({ baseUrl, runId, isDemo }) {
  const [selector, setSelector] = useState_rl("seed_relative_v1");
  const [yearly, setYearly] = useState_rl(null);
  const [preview, setPreview] = useState_rl(null);
  const [autopsyGen, setAutopsyGen] = useState_rl(0);
  const [autopsy, setAutopsy] = useState_rl(null);
  const [cf, setCf] = useState_rl(null);
  const [mc, setMc] = useState_rl(null);
  const [tmap, setTmap] = useState_rl(null);
  const [compareRun, setCompareRun] = useState_rl("");  /* M12 — 지도 비교 run. */
  const [ops, setOps] = useState_rl(null);  /* 운영 현황 — 10초 자동 갱신. */
  const [grid, setGrid] = useState_rl(null);     /* C6 — 2-D 격자 히트맵. */
  const [gridRun, setGridRun] = useState_rl("");
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const fetchGrid = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    const rid = gridRun.trim() || runId;
    if (!rid) return;
    fetch(baseUrl + "/tmap_grid?run_id=" + encodeURIComponent(rid),
          { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setGrid(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, gridRun, isDemo, runId]);

  const [gridMetric, setGridMetric] = useState_rl("profit");  /* E5 — 히트맵 색 기준. */
  const [runOptions, setRunOptions] = useState_rl([]);  /* F2 — run 자동완성. */
  useEffect_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(d => setRunOptions(((d && d.runs) || []).slice(0, 40).map(r => r.run_id)))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  const [niche, setNiche] = useState_rl(null);  /* D3 — 니치 지도 비교. */
  const fetchNiche = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/niche_compare", { signal: AbortSignal.timeout(15000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setNiche(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, isDemo]);

  /* 과업2(2026-06-12) — 포트폴리오 결합 시뮬 v0 균등가중. */
  const [psimRun1, setPsimRun1] = useState_rl("");
  const [psimRun2, setPsimRun2] = useState_rl("");
  const [psim, setPsim] = useState_rl(null);
  const fetchPsim = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    const r1 = psimRun1.trim(), r2 = psimRun2.trim();
    if (!r1 || !r2) return;
    fetch(baseUrl + "/portfolio_sim?runs=" + encodeURIComponent(r1 + "," + r2),
          { signal: AbortSignal.timeout(15000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setPsim(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, isDemo, psimRun1, psimRun2]);

  const [verdict, setVerdict] = useState_rl(null);  /* 검증 결산 — V1~V5 종합. */

  useEffect_rl(() => {
    if (isDemo || !baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setOps(j))
      .catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    fetch(baseUrl + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setVerdict(j))
      .catch(() => {});
    return () => clearInterval(timer);
  }, [baseUrl, isDemo]);

  const fetchTmap = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const cmp = compareRun.trim()
      ? "&compare_run_id=" + encodeURIComponent(compareRun.trim()) : "";
    fetch(baseUrl + "/tmap_map?run_id=" + encodeURIComponent(runId) + cmp,
          { signal: AbortSignal.timeout(10000) })
      .then(r => r.ok ? r.json() : null)
      .then(j => setTmap(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, compareRun, isDemo, runId]);

  const refresh = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const yUrl = baseUrl + "/run_yearly?run_id=" + encodeURIComponent(runId);
    const pUrl = baseUrl + "/selector_preview?run_id=" + encodeURIComponent(runId)
      + "&selector=" + encodeURIComponent(selector);
    Promise.all([
      fetch(yUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
      fetch(pUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
    ])
      .then(([y, p]) => { setYearly(y); setPreview(p); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, selector]);

  useEffect_rl(() => { refresh(); }, [refresh]);

  const [equity, setEquity] = useState_rl(null);  /* E2/D4 — 누적 수익곡선. */
  const fetchAutopsy = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const q = "?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(autopsyGen);
    Promise.all([
      fetch(baseUrl + "/autopsy" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/counterfactual" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/freeze_mc" + q, { signal: AbortSignal.timeout(15000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/equity_curve" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
    ])
      .then(([a, c, m, eq]) => { setAutopsy(a); setCf(c); setMc(m); setEquity(eq); })
      .catch(e => setErr(String(e)));
  }, [autopsyGen, baseUrl, isDemo, runId]);

  if (isDemo || !runId) {
    return <div className="research-lab-panel"><_ResearchEmptyState message="검증 화면을 표시할 run 컨텍스트가 부족합니다." /></div>;
  }

  const gens = (yearly && Array.isArray(yearly.generations)) ? yearly.generations : [];
  return (
    <div className="research-lab-panel">
      <div className="research-controls">
        <label>
          <span>selector</span>
          <select value={selector} onChange={(e) => setSelector(e.target.value)} disabled={loading}>
            <option value="seed_relative_v1">seed_relative_v1</option>
            <option value="sparse_positive_v1">sparse_positive_v1</option>
          </select>
        </label>
        <span className="research-empty">diagnostic_only · 동결 아티팩트 아님</span>
        {/* E4 — 품질/적합도 용어 hover 설명(이 파이프라인 기준). */}
        <span className="research-help"
              title="적합도(Fitness): 손익·MDD·거래수·일관성을 가중합한 한 개의 점수. 세대(전략)가 목표 기준에 얼마나 부합하는지를 나타냅니다 — 높을수록 좋고, 게이트의 1차 통과 기준입니다. 차트는 세대 진행(x)에 따라 적합도가 우상향하는지를 봅니다.">
          적합도 ?
        </span>
        <span className="research-help"
              title="품질(Quality): 결과의 견고함 지표 모음(흑자율·고원/mesa 안정성·OOS 유지 등). 단발 고점이 아니라 이웃 파라미터·다른 기간에서도 성과가 유지되는지를 봅니다 — 과최적화를 거르는 척도입니다.">
          품질 ?
        </span>
      </div>
      {err && <_ResearchEmptyState message={"응답을 받지 못했습니다: " + err} />}

      {ops && (
        <div style={{ marginTop: 6 }}>
          <div className="research-empty">
            {"운영 현황 (10초 자동 갱신)"
              + (ops.walkforward
                ? ` · WF ${ops.walkforward.path}: 정책 ${Math.round(ops.walkforward.policy_total || 0).toLocaleString()} vs 시드 ${Math.round(ops.walkforward.baseline_total || 0).toLocaleString()} (${ops.walkforward.windows_done}창 완료)`
                : "")}
          </div>
          {(ops.active || []).length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>실행 중 run 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>실행 중 run</th><th>세대</th><th>마지막 포인트</th><th>무진행(초)</th><th>상태</th></tr></thead>
                <tbody>
                  {ops.active.map(a => (
                    <tr key={a.run_id}>
                      <td>{a.run_id}</td>
                      <td>{a.gens}</td>
                      <td>{a.last_label || "—"}</td>
                      <td>{a.seconds_since_last_gen}</td>
                      <td>{a.health === "active" ? "✅ 진행 중" : "⚠️ 정체 의심"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          {(ops.recent || []).length > 0 && (
            <div className="mono" style={{ fontSize: 11 }}>
              {"최근 완료: " + ops.recent.slice(0, 5).map(r =>
                `${r.run_id}(${r.gens}세대${r.best_profit != null ? "·최고 " + Math.round(r.best_profit).toLocaleString() : ""})`
              ).join("  ·  ")}
            </div>
          )}
          {(ops.evidence || []).length > 0 && (
            <div className="research-empty">
              {"최신 증거: " + ops.evidence.map(e => `${e.name}(${e.age_min}분 전)`).join(" · ")}
            </div>
          )}
        </div>
      )}

      {verdict && (verdict.lines || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">검증 결산 (V1~V5 + 리스크 — 결정 카드 라이브)</div>
          {/* P7 — 공유 PROMOTE 체크리스트(정본: rl-vdt-shell 정의). 빈 상태 메시지 포함. */}
          {(verdict.promote_checklist || []).length > 0 && (
            <VdtPromoteChecklist v={verdict} />
          )}
          {verdict.walkforward && Array.isArray(verdict.walkforward.windows)
            && verdict.walkforward.windows.length > 0 && (
            <table className="mono" style={{ fontSize: 11, marginBottom: 4 }}>
              <thead><tr><th>WF 창(fit)</th><th>eval</th><th>θ 선택</th><th>정책</th><th>시드</th></tr></thead>
              <tbody>
                {verdict.walkforward.windows.map((w, i) => (
                  <tr key={"w" + i}>
                    <td>{w.fit_start}~{w.fit_end}</td>
                    <td>{w.eval_start}~{w.eval_end}</td>
                    <td>{w.theta
                      ? Object.entries(w.theta).map(([k, v]) => `${k}=${v}`).join(",")
                      : "기권(시드 유지)"}</td>
                    <td>{w.policy ? Math.round(w.policy.profit).toLocaleString() : "—"}</td>
                    <td>{w.baseline ? Math.round(w.baseline.profit).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {/* P7 — 공유 경보·요약줄(정본: rl-vdt-shell 정의). */}
          <VdtAlerts v={verdict} />
          <VdtSummaryLines v={verdict} />
        </div>
      )}

      {niche && (niche.runs || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">니치 지도 비교 (최근 tmap run 자동 — 신규 니치 4종 아침 분석용)</div>
          <table className="mono" style={{ fontSize: 11, width: "100%" }}>
            <thead><tr><th>run</th><th>상태</th><th>ok세대</th><th>베이스라인</th><th>최강 슬롯 고원 / 격자</th><th>최고 단일점</th><th>시간대</th><th>R²·정체</th><th>동결상관</th></tr></thead>
            <tbody>
              {niche.runs.map(r => (
                <tr key={r.run_id}>
                  <td>{r.run_id}</td>
                  <td>{r.status === "running" ? "🔄" : "✅"}</td>
                  <td>{r.gens_ok}</td>
                  <td>{r.baseline ? `${Math.round(r.baseline.profit).toLocaleString()} (MDD ${_rlNum(r.baseline.mdd, 1)})` : "—"}</td>
                  <td>
                    {r.top_slot
                      ? `${r.top_slot.param}: 중심 ${r.top_slot.center} · 평균 ${Math.round(r.top_slot.mean_profit || 0).toLocaleString()} (score ${_rlNum(r.top_slot.plateau_score, 2)})`
                      : r.grid
                        ? `격자 ${r.grid.cells}셀 · 흑자 ${Math.round((r.grid.positive_ratio || 0) * 100)}% · mesa ${r.grid.mesa}`
                        : "—"}
                  </td>
                  <td>{r.best_profit != null ? Math.round(r.best_profit).toLocaleString() : "—"}</td>
                  <td>{(r.time_buckets || []).join(",") || "—"}</td>
                  <td>{r.shape_r2 != null ? `${_rlNum(r.shape_r2, 2)}·${r.stagnation_days}일` : "—"}</td>
                  <td>{r.corr_vs_frozen != null ? _rlNum(r.corr_vs_frozen, 2) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="research-empty" style={{ marginTop: 6 }}>연도 분해 (per-trade CSV 집계)</div>
      <table className="mono" style={{ fontSize: 11, width: "100%" }}>
        <thead><tr><th>gen</th><th>label</th><th>연도별 손익(거래수·승률)</th></tr></thead>
        <tbody>
          {gens.map(g => (
            <tr key={g.gen_no}>
              <td>{g.gen_no}</td>
              <td>{g.label || g.buy_name || "—"}</td>
              <td>
                {(g.years || []).length
                  ? g.years.map(y => `${y.year}: ${Math.round(y.profit).toLocaleString()} (${y.trades}건·${Math.round((y.win_rate || 0) * 100)}%)`).join("  ·  ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="research-empty" style={{ marginTop: 8 }}>
        선택기 미리보기 — selected: {preview && preview.selected ? "TRUE" : "false"}
        {preview && preview.mdd_limit != null ? ` · mdd_limit ${_rlNum(preview.mdd_limit, 2)}` : ""}
        {preview && preview.selected_candidate
          ? ` · gen${preview.selected_candidate.gen_no} ${preview.selected_candidate.label || preview.selected_candidate.buy_name}`
          : ""}
      </div>
      {preview && Array.isArray(preview.rejected) && preview.rejected.length > 0 && (
        <ul className="mono" style={{ fontSize: 11 }}>
          {preview.rejected.map(rj => (
            <li key={rj.gen_no}>gen{rj.gen_no} {rj.label || ""}: {(rj.reasons || []).join("; ")}</li>
          ))}
        </ul>
      )}

      <div className="research-controls" style={{ marginTop: 8 }}>
        <label>
          <span>gen</span>
          <input type="number" value={autopsyGen} min={0}
                 onChange={(e) => setAutopsyGen(Number(e.target.value) || 0)}
                 style={{ width: 64 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchAutopsy}>부검·반사실·MC 보기</button>
        <datalist id="rl-run-options">
          {runOptions.map(id => <option key={id} value={id} />)}
        </datalist>
        <label>
          <span>비교 run</span>
          <input type="text" value={compareRun} placeholder="다른 스윕 run_id (선택)"
                 list="rl-run-options"
                 onChange={(e) => setCompareRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchTmap}>TMAP 지도</button>
        <label>
          <span>격자 run</span>
          <input type="text" value={gridRun} placeholder="--grid 스윕 run_id"
                 list="rl-run-options"
                 onChange={(e) => setGridRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchGrid}>2-D 히트맵</button>
        <button type="button" className="research-tab" onClick={fetchNiche}>니치 비교</button>
      </div>
      {autopsy && (
        <div className="mono" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
          {autopsy.status !== "ok"
            ? `autopsy: ${autopsy.status}`
            : `${autopsy.entry_summary || "(진입 부검 없음)"}\n\n${autopsy.exit_summary || "(청산 부검 없음)"}`}
        </div>
      )}

      {cf && cf.status === "ok" && Array.isArray(cf.suggestions) && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">반사실 필터 제안 (백테 0회·인샘플 advisory — 채택 시 정식 파이프라인 검증 필수)</div>
          {cf.suggestions.length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>총손익이 깎이지 않는 강화 필터 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>필터</th><th>거래</th><th>총손익</th><th>승률</th><th>잘린 거래 순손익</th><th>최근연도</th></tr></thead>
                <tbody>
                  {cf.suggestions.map((s, i) => (
                    <tr key={i}>
                      <td>{s.filter}</td>
                      <td>{s.base_trades}→{s.kept_trades}</td>
                      <td>{Math.round((s.profit_ratio || 0) * 100)}%</td>
                      <td>{Math.round((s.base_win_rate || 0) * 100)}%→{Math.round((s.kept_win_rate || 0) * 100)}%</td>
                      <td>{Math.round(s.cut_net_profit || 0).toLocaleString()}</td>
                      <td>{s.recent_year
                        ? `${s.recent_year.year}: ${Math.round(s.recent_year.base_profit).toLocaleString()}→${Math.round(s.recent_year.kept_profit).toLocaleString()}`
                        : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {mc && mc.status === "ok" && mc.mc && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            블록 부트스트랩 MC (일별 손익·레짐 군집 보존 — iid 거래 추출 MC의 OOS 전이 실패 교훈 반영)
          </div>
          <div className="mono" style={{ fontSize: 11 }}>
            {`P(총손익>0)=${Math.round((mc.mc.p_positive || 0) * 100)}% · 총손익 p05/p50/p95 = `
              + `${Math.round(mc.mc.profit_p05).toLocaleString()} / ${Math.round(mc.mc.profit_p50).toLocaleString()} / ${Math.round(mc.mc.profit_p95).toLocaleString()}`
              + ` · MDD(낙폭금액) p50/p95 = ${Math.round(mc.mc.mdd_p50).toLocaleString()} / ${Math.round(mc.mc.mdd_p95).toLocaleString()}`
              + ` (${mc.mc.n_days}일·${mc.mc.n_boot}회·블록 ${mc.mc.block_len}일)`}
          </div>
          <_McFanChart fan={mc.mc.fan} />
        </div>
      )}

      {equity && equity.status === "ok" && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty"
               title="x축은 거래일 진행(왼→오른쪽=과거→현재), y축은 누적 손익(원). 0선 점선 위는 흑자 구간입니다.">
            {`누적 수익곡선 — gen ${equity.gen_no}${equity.label ? " · " + equity.label : ""}`
              + ` · 총 ${Math.round(equity.total).toLocaleString()}`}
          </div>
          {/* E3 — 축 의미(거래일 진행)·기간(연도 포함) 명시. */}
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-2)", marginBottom: 2 }}>
            {`x축: 거래일 진행(${equity.n_days}거래일) · 기간 ${_rlPeriodFromDays(equity.days)} · y축: 누적 손익(원)`}
          </div>
          <_EquityChart cum={equity.cum} />
        </div>
      )}

      {tmap && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            TMAP 경향성 지도 (고원 &gt; 피크 — 이웃 θ도 흑자인 영역이 진짜)
          </div>
          {(!tmap.count || !Object.keys(tmap.params || {}).length)
            ? <div className="mono" style={{ fontSize: 11 }}>이 run은 TMAP 스윕이 아닙니다 (tmap_sweep run_id를 선택하세요)</div>
            : (
              <div>
                <div className="mono" style={{ fontSize: 11 }}>
                  {tmap.baseline
                    ? `베이스라인(θ=기본값): 손익 ${Math.round(tmap.baseline.profit).toLocaleString()} · MDD ${_rlNum(tmap.baseline.mdd, 2)} · ${tmap.baseline.trades}건`
                    : "베이스라인 없음"}
                </div>
                <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                  <thead><tr><th>슬롯(θ)</th><th>응답 곡선</th><th>plateau score</th><th>고원 중심</th><th>폭</th><th>고원 평균손익</th><th>흑자율</th><th>절벽(최대 점프)</th><th>중심 형태(R²·정체일)</th>{tmap.compare && <th>비교 run(중심·score)</th>}</tr></thead>
                  <tbody>
                    {Object.entries(tmap.params)
                      .sort((a, b) => (b[1].plateau_score || 0) - (a[1].plateau_score || 0))
                      .map(([name, m]) => {
                        const cm = (tmap.compare && tmap.compare.params) ? tmap.compare.params[name] : null;
                        return (
                          <tr key={name}>
                            <td>{name}</td>
                            <td><_CurveSpark curve={m.curve} /></td>
                            <td>{_rlNum(m.plateau_score, 3)}</td>
                            <td>{m.plateau ? m.plateau.center_value : "—"}</td>
                            <td>{m.plateau ? m.plateau.width : "—"}</td>
                            <td>{m.plateau ? Math.round(m.plateau.mean_profit).toLocaleString() : "—"}</td>
                            <td>{Math.round((m.positive_ratio || 0) * 100)}%</td>
                            <td>{m.cliff ? `${Math.round(m.cliff.jump).toLocaleString()} @${m.cliff.between.join("→")}` : "—"}</td>
                            <td>{m.center_shape ? `${_rlNum(m.center_shape.uptrend_r2, 2)}·${m.center_shape.max_stagnation_days}일` : "—"}</td>
                            {tmap.compare && <td>{cm && cm.plateau ? `${cm.plateau.center_value} · ${_rlNum(cm.plateau_score, 2)}` : "—"}</td>}
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
                {tmap.compare && (
                  <div className="research-empty">
                    비교 run: {tmap.compare.run_id || "—"} — 구간별 경향 발산 확인용(M12). 다년 지도의 고원만 동결 자격.
                  </div>
                )}
              </div>
            )}
        </div>
      )}

      {grid && grid.count > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>
              {`2-D 격자 히트맵 (${grid.param_a} × ${grid.param_b}) — ★=mesa(4-이웃 전부 흑자) · 흑자율 ${Math.round((grid.positive_ratio || 0) * 100)}%`
                + (grid.baseline ? ` · 베이스라인 ${Math.round(grid.baseline.profit).toLocaleString()}` : "")}
            </span>
            <button type="button" className="research-tab"
                    onClick={() => setGridMetric(gridMetric === "profit" ? "mdd" : "profit")}>
              색: {gridMetric === "profit" ? "수익" : "MDD"}
            </button>
          </div>
          <_GridHeatmap grid={grid} metric={gridMetric} />
        </div>
      )}
      {grid && grid.count === 0 && (
        <div className="mono" style={{ fontSize: 11 }}>격자 run 아님(--grid 스윕 run_id를 입력하세요)</div>
      )}

      {/* 과업3(2026-06-12) — 파이프라인 체크포인트 패널 */}
      <_PipelineCheckpointPanel baseUrl={baseUrl} isDemo={isDemo} />

      {/* 과업2(2026-06-12) — 결합 시뮬(v0 균등가중) advisory 패널 */}
      <div style={{ marginTop: 10 }}>
        <div className="research-empty">결합 시뮬 (v0 균등가중) — advisory. 판정 미사용.</div>
        <div className="research-controls" style={{ marginTop: 4 }}>
          <label>
            <span>run 1</span>
            <input type="text" value={psimRun1} placeholder="run_id"
                   list="rl-run-options"
                   onChange={e => setPsimRun1(e.target.value)} style={{ width: 180 }} />
          </label>
          <label>
            <span>run 2</span>
            <input type="text" value={psimRun2} placeholder="run_id"
                   list="rl-run-options"
                   onChange={e => setPsimRun2(e.target.value)} style={{ width: 180 }} />
          </label>
          <button type="button" className="research-tab" onClick={fetchPsim}>결합 시뮬 실행</button>
        </div>
        {psim && !psim.error && (
          <div style={{ marginTop: 6 }}>
            <div className="mono" style={{ fontSize: 11 }}>
              결합 총손익: <b>{Math.round(psim.combined_total || 0).toLocaleString()}</b>
              {" · "}결합 MDD: <b>{Math.round(psim.combined_mdd || 0).toLocaleString()}</b>
              {psim.diversification_gain != null
                ? ` · 분산이득: ${(psim.diversification_gain * 100).toFixed(1)}%`
                : ""}
            </div>
            {psim.correlation && Array.isArray(psim.correlation.labels) && (
              <table className="mono" style={{ fontSize: 11, marginTop: 4 }}>
                <thead>
                  <tr>
                    <th>상관</th>
                    {psim.correlation.labels.map(l => <th key={l}>{l.split(":")[0]}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {psim.correlation.labels.map((row, i) => (
                    <tr key={row}>
                      <th>{row.split(":")[0]}</th>
                      {(psim.correlation.matrix[i] || []).map((v, j) => (
                        <td key={j}>{v.toFixed(2)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        {psim && psim.error && (
          <div className="mono" style={{ fontSize: 11, color: "var(--amber)" }}>{psim.error}</div>
        )}
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { _ValidationPanel };
