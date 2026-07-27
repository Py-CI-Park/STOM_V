/* 명예의 전당 — 인간 벤치마크 + AI 생성 통합 패널 + 스크린샷 갤러리 (split from chart.jsx, P5.4).
   HallOfFamePanel · ReferenceGallery. app.jsx 가 chart.jsx 배럴 경유로 HallOfFamePanel 을 import.
   - 작은 표현 컴포넌트(LegendDot)는 chart-primitives 에서 import.
   - 포맷 헬퍼(fmtMoney)는 stom-ui 빌드 번들이 제공하는 전역(connection.jsx 의 const X = window.X
     별칭이 babel 스코프보다 먼저 로드)을 bare 호출로 그대로 쓴다.
*/
import { LegendDot } from "./chart-primitives.jsx";
import { HofInventoryGate } from "./hof-inventory.jsx";
import { HofPerformanceOverview } from "./hof-performance-overview.jsx";
// v5.13.0(G4) — 조건식 즉시 열람: 카탈로그 행에서 코드 뷰어를 바로 연다. KEEP on ONE physical line.
import { CodeViewer } from "./code-viewer.jsx";

// HallOfFamePanel · ReferenceGallery 가 쓰는 React hook 별칭(이동 시 각 모듈이 자체 선언).
const { useState: useState_eq, useEffect: useEffect_eq, useCallback: useCallback_eq, useRef: useRef_eq } = React;
const { useState: useState_rg, useEffect: useEffect_rg } = React;

/* ─────────────────────────────────────────────────────────────────────────
   Hall separates the fixed human benchmark from the server-paginated AI
   research catalog.  Missing stored values intentionally render as "—".
   ───────────────────────────────────────────────────────────────────────── */
const hofNumber = (value) => typeof value === "number" && Number.isFinite(value);
const hofTone = (value) => value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
const hofClass = (kind, tone) => `hof-${kind} hof-${kind}--${tone}`;

function HofSignedValue({ value, format, label }) {
  if (!hofNumber(value)) return <span className={hofClass("metric", "missing")}>—</span>;
  const tone = hofTone(value);
  const formatted = String(format(value));
  const signed = value > 0 ? "+" + formatted.replace(/^\+/, "") : formatted;
  const state = value > 0 ? "이익" : value < 0 ? "손실" : "보합";
  const icon = value > 0 ? "▲" : value < 0 ? "▼" : "●";
  return <span className={hofClass("metric", tone)} aria-label={`${label} ${state} ${signed}`}>
    <b aria-hidden="true">{icon}</b> {state} {signed}
  </span>;
}

function HofMddValue({ value }) {
  if (!hofNumber(value)) return <span className={hofClass("mdd", "missing")}>—</span>;
  const magnitude = Math.abs(value);
  const tier = magnitude <= 5 ? "low" : magnitude <= 15 ? "caution" : "high";
  const label = tier === "low" ? "낮음" : tier === "caution" ? "주의" : "높음";
  const icon = tier === "low" ? "○" : tier === "caution" ? "!" : "▲";
  return <span className={hofClass("mdd", tier)} aria-label={`MDD 위험 ${label} ${magnitude.toFixed(1)}%`}>
    <b aria-hidden="true">{icon}</b> 위험 {label} {magnitude.toFixed(1)}%
  </span>;
}

function HofToneBadge({ kind, tone, icon, label }) {
  return <span className={hofClass(kind, tone)} role="status"><b aria-hidden="true">{icon}</b> {label}</span>;
}

function HofGateBadge({ value }) {
  return value === true ? <HofToneBadge kind="gate" tone="pass" icon="✓" label="통과" />
    : value === false ? <HofToneBadge kind="gate" tone="fail" icon="✕" label="미통과" />
    : <HofToneBadge kind="gate" tone="unknown" icon="?" label="미확인" />;
}

function HofStatusBadge({ value }) {
  const normalized = typeof value === "string" ? value.toLowerCase() : "";
  if (["ok", "success", "complete"].includes(normalized)) return <HofToneBadge kind="status" tone="good" icon="✓" label="정상" />;
  if (["failed", "error"].includes(normalized)) return <HofToneBadge kind="status" tone="bad" icon="✕" label="실패" />;
  if (normalized === "unavailable") return <HofToneBadge kind="status" tone="unknown" icon="!" label="불가" />;
  return <HofToneBadge kind="status" tone="unknown" icon="?" label="미확인" />;
}

function HofOutcomeBadge({ value }) {
  const normalized = typeof value === "string" ? value.toLowerCase() : "";
  if (normalized === "success") return <HofToneBadge kind="outcome" tone="good" icon="▲" label="성공" />;
  if (normalized === "loss") return <HofToneBadge kind="outcome" tone="loss" icon="▼" label="손실" />;
  if (normalized === "failure") return <HofToneBadge kind="outcome" tone="bad" icon="✕" label="실패" />;
  if (normalized === "no_trade") return <HofToneBadge kind="outcome" tone="neutral" icon="●" label="거래 없음" />;
  if (normalized === "unavailable") return <HofToneBadge kind="outcome" tone="unknown" icon="!" label="불가" />;
  return <HofToneBadge kind="outcome" tone="unknown" icon="?" label="미확인" />;
}

function HallOfFamePanel({ baseUrl, wsStatus }) {
  const [human, setHuman] = useState_eq([]);
  const [catalog, setCatalog] = useState_eq({ items: [], total: 0, returned: 0, next: null });
  const [loading, setLoading] = useState_eq(false);
  const [loadingMore, setLoadingMore] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [sortKey, setSortKey] = useState_eq("score");
  const [sortDirection, setSortDirection] = useState_eq("desc");
  const [statusFilter, setStatusFilter] = useState_eq("");
  const [gateFilter, setGateFilter] = useState_eq("");
  const [outcomeFilter, setOutcomeFilter] = useState_eq("");
  const [galleryOpen, setGalleryOpen] = useState_eq(false);
  const [galleryInitial, setGalleryInitial] = useState_eq(null);
  const [lastUpdated, setLastUpdated] = useState_eq(null);
  // v5.13.0(G3/G4) — TOP10(게이트 통과 · score 순) + 조건식 즉시 열람 상태.
  const [top10, setTop10] = useState_eq([]);
  const [codeView, setCodeView] = useState_eq(null); // {run_id, gen_no, buy_name, sell_name} | null
  // v5.13.0(G1) — 인간 결과 스크린샷을 모달 뒤에 숨기지 않고 표와 나란히 상시 표시.
  const [shots, setShots] = useState_eq([]);
  const requestRef = useRef_eq(null);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const fetchCatalog = useCallback_eq((offset, append) => {
    if (isDemo || !baseUrl) return;
    if (requestRef.current) requestRef.current.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    append ? setLoadingMore(true) : setLoading(true);
    const params = new URLSearchParams({
      limit: "50", offset: String(offset), sort: sortKey, order: sortDirection,
    });
    if (statusFilter) params.set("status", statusFilter);
    if (gateFilter) params.set("gate", gateFilter);
    if (outcomeFilter) params.set("outcome", outcomeFilter);
    const catalogRequest = fetch(baseUrl + "/hall_of_fame/catalog?" + params, { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
    const humanRequest = append ? Promise.resolve(null) : fetch(baseUrl + "/hall_of_fame", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
    Promise.all([catalogRequest, humanRequest])
      .then(([nextCatalog, legacy]) => {
        if (controller.signal.aborted) return;
        if (legacy) setHuman(Array.isArray(legacy.human) ? legacy.human : []);
        setCatalog(previous => append
          ? { ...nextCatalog, items: [...previous.items, ...(nextCatalog.items || [])] }
          : nextCatalog);
        setErr(null);
        setLastUpdated(new Date());
      })
      .catch(e => { if (!controller.signal.aborted && e.name !== "AbortError") setErr(String(e)); })
      .finally(() => {
        if (requestRef.current === controller) {
          requestRef.current = null;
          setLoading(false);
          setLoadingMore(false);
        }
      });
  }, [baseUrl, isDemo, sortKey, sortDirection, statusFilter, gateFilter, outcomeFilter]);

  useEffect_eq(() => {
    fetchCatalog(0, false);
    const id = setInterval(() => fetchCatalog(0, false), 30000);
    return () => { clearInterval(id); if (requestRef.current) requestRef.current.abort(); };
  }, [fetchCatalog]);

  // v5.13.0(G3) — TOP10 은 필터·정렬과 독립: 게이트 통과 세대를 score 내림차순 10개.
  useEffect_eq(() => {
    if (isDemo || !baseUrl) { setTop10([]); return undefined; }
    const controller = new AbortController();
    fetch(baseUrl + "/hall_of_fame/catalog?limit=10&offset=0&sort=score&order=desc&gate=passed",
          { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => setTop10(Array.isArray(j && j.items) ? j.items : []))
      .catch(() => setTop10([]));
    return () => controller.abort();
  }, [baseUrl, isDemo]);

  // v5.13.0(G1) — 스크린샷 파일 목록(상시 스트립용).
  useEffect_eq(() => {
    if (!baseUrl) { setShots([]); return undefined; }
    const controller = new AbortController();
    fetch(baseUrl + "/reference_screenshots", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => setShots(Array.isArray(j && j.screenshots) ? j.screenshots : []))
      .catch(() => setShots([]));
    return () => controller.abort();
  }, [baseUrl]);

  const fmtPct = (v) => typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : "—";
  const fmtNumber = (v, digits = 2) => typeof v === "number" ? v.toFixed(digits) : "—";
  const fmtInt = (v) => typeof v === "number" ? Math.round(v).toLocaleString("ko-KR") : "—";
  const humanRows = human.slice().sort((a, b) => (
    (b.total_return_pct ?? -Infinity) - (a.total_return_pct ?? -Infinity)
    || String(a.label || "").localeCompare(String(b.label || ""))
  ));
  const catalogRows = catalog.items || [];
  const filterStyle = (selected, value) => selected === value
    ? { color: "var(--amber)", borderColor: "var(--amber)" } : undefined;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          🏆 명예의 전당 · 인간 벤치마크 &amp; AI 전체 연구 카탈로그
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <LegendDot color="var(--green)" label="👤 인간 벤치마크" />
          <LegendDot color="var(--violet)" label="🤖 전체 AI 연구" />
          <span style={{ fontSize: 10, color: "var(--ink-3)", fontFamily: "var(--mono)" }}
                data-tip="백테 기간이 3개월 미만이면 연환산이 과대추정될 수 있습니다.">
            단기 창=연환산 신뢰낮음
          </span>
          <button className="btn ghost sm" onClick={() => setGalleryOpen(true)}>📷 인간 결과 스크린샷</button>
          <button className="btn ghost sm" onClick={() => fetchCatalog(0, false)} disabled={isDemo || loading}>
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        <HofInventoryGate compact />
        {err && <div className="v4s-note" role="alert">조회 실패: {err}</div>}
        {isDemo ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)" }}>
            데모 모드 — 백엔드 연결 시 카탈로그가 표시됩니다.
          </div>
        ) : (
          <>
            <HofPerformanceOverview humanRows={humanRows} catalogRows={catalogRows} />

            {/* v5.13.0(G3) — 바로 사용해도 좋은 상위 TOP10: 게이트 통과 · score 내림차순.
                조건식 이름을 앞세우고 [조건식 보기]로 즉시 열람(G4). */}
            {top10.length > 0 && (
              <>
                <div style={{ margin: "16px 0 8px", fontWeight: 700 }}>⭐ 바로 쓸 만한 TOP {top10.length} — 게이트 통과 · score 순</div>
                <div className="hof-top10-grid">
                  {top10.map((row, i) => (
                    <div key={`${row.run_id}/${row.gen_no}`} className={"hof-top10-card" + (i < 3 ? " podium" : "")}>
                      <div className="hof-top10-rank">{i + 1}</div>
                      <div className="hof-top10-body">
                        <div className="hof-top10-name mono" title={row.buy_name || "—"}>
                          <span className="k">매수</span> {row.buy_name || "—"}
                        </div>
                        <div className="hof-top10-name mono sell" title={row.sell_name || "—"}>
                          <span className="k">매도</span> {row.sell_name || "—"}
                        </div>
                        <div className="hof-top10-metrics mono">
                          <span>score <b>{fmtNumber(row.score)}</b></span>
                          <span className={typeof row.return_pct === "number" && row.return_pct > 0 ? "num-pos" : "num-neg"}>
                            수익률 <b>{fmtPct(row.return_pct)}</b>
                          </span>
                          <span style={{ color: "var(--red)" }}>MDD <b>{typeof row.mdd_pct === "number" ? Math.abs(row.mdd_pct).toFixed(1) + "%" : "—"}</b></span>
                          <span>{row.label || `${row.run_id}/g${row.gen_no}`}</span>
                        </div>
                      </div>
                      <button className="btn ghost sm" title="이 세대의 매수·매도 조건식 전체 코드를 바로 봅니다"
                              onClick={() => setCodeView({ run_id: row.run_id, gen_no: row.gen_no, buy_name: row.buy_name, sell_name: row.sell_name })}>
                        &lt;/&gt; 조건식 보기
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div style={{ margin: "14px 0 8px", fontWeight: 700 }}>👤 인간 벤치마크 ({humanRows.length})</div>
            {/* v5.13.0(G1) — 인간 결과 스크린샷을 표와 나란히 상시 표시(클릭 시 확대). */}
            {shots.length > 0 && (
              <div className="hof-shot-strip" aria-label="인간 결과 스크린샷 스트립">
                {shots.slice(0, 10).map(name => (
                  <img key={name} src={baseUrl + "/reference_img/" + encodeURIComponent(name)} alt={name}
                       loading="lazy" title={name + " — 클릭하면 확대"}
                       onClick={() => { setGalleryInitial(name); setGalleryOpen(true); }} />
                ))}
                {shots.length > 10 && (
                  <button className="btn ghost sm" onClick={() => { setGalleryInitial(null); setGalleryOpen(true); }}>
                    +{shots.length - 10}장 전체
                  </button>
                )}
              </div>
            )}
            <div className="hof-scroll" tabIndex="0" aria-label="인간 벤치마크 표">
              <table className="data-table hof-table hof-human-table">
                <thead><tr><th scope="col" className="hof-identity">이름</th><th scope="col" className="hof-num">운영금</th><th scope="col" className="hof-num">총수익금(원)</th><th scope="col" className="hof-num">총수익률</th><th scope="col" className="hof-num">연평균</th><th scope="col" className="hof-num">MDD</th><th scope="col" className="hof-num">payoff</th><th scope="col" className="hof-num">승률</th><th scope="col" className="hof-num">일평균 거래</th><th scope="col" className="hof-num">최대 보유</th><th scope="col">백테 기간</th><th scope="col" className="hof-num">거래수</th></tr></thead>
                <tbody>{humanRows.map(row => <tr key={row.label}>
                  <th scope="row" className="hof-identity">{row.label || "—"}</th>
                  <td className="hof-num">{hofNumber(row.operating_capital_krw) ? fmtMoney(row.operating_capital_krw) : "—"}</td>
                  <td className="hof-num"><HofSignedValue value={row.total_return_krw} format={value => fmtMoney(Math.abs(value))} label="총수익금" /></td>
                  <td className="hof-num"><HofSignedValue value={row.total_return_pct} format={value => `${Math.abs(value).toFixed(1)}%`} label="총수익률" /></td>
                  <td className="hof-num"><HofSignedValue value={row.annual_return_pct} format={value => `${Math.abs(value).toFixed(1)}%`} label="연평균 수익률" /></td>
                  <td className="hof-num"><HofMddValue value={row.mdd_pct} /></td>
                  <td className="hof-num">{fmtNumber(row.payoff)}</td><td className="hof-num">{fmtPct(row.win_rate_pct)}</td><td className="hof-num">{fmtNumber(row.daily_avg_trades)}</td>
                  <td className="hof-num">{fmtInt(row.max_holdings)}</td><td>{row.period || "—"}</td><td className="hof-num">{fmtInt(row.trades)}</td>
                </tr>)}</tbody>
              </table>
            </div>

            <div style={{ margin: "20px 0 8px", fontWeight: 700 }}>🤖 AI 연구 카탈로그 — 전체 세대</div>
            <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>정렬</span>
              {[
                ["score", "score"], ["returns", "수익률"], ["mdd", "MDD"], ["trades", "거래수"], ["gen_no", "세대"],
              ].map(([key, label]) => <button key={key} className="btn ghost sm"
                onClick={() => {
                  if (sortKey === key) setSortDirection(direction => direction === "asc" ? "desc" : "asc");
                  else { setSortKey(key); setSortDirection(key === "mdd" ? "asc" : "desc"); }
                }} style={filterStyle(sortKey, key)}>{label}{sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : ""}</button>)}
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 8 }}>상태</span>
              {["", "ok", "success", "complete", "failed", "error", "unavailable"].map(value => <button key={value || "all-status"} className="btn ghost sm"
                onClick={() => setStatusFilter(value)} style={filterStyle(statusFilter, value)}>{value || "전체"}</button>)}
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 8 }}>gate</span>
              {[["", "전체"], ["passed", "통과"], ["failed", "미통과"]].map(([value, label]) => <button key={value || "all-gate"} className="btn ghost sm"
                onClick={() => setGateFilter(value)} style={filterStyle(gateFilter, value)}>{label}</button>)}
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 8 }}>결과</span>
              {[["", "전체"], ["success", "성공"], ["loss", "손실"], ["failure", "실패"], ["no_trade", "거래없음"], ["unavailable", "불가"]].map(([value, label]) => <button key={value || "all-outcome"} className="btn ghost sm"
                onClick={() => setOutcomeFilter(value)} style={filterStyle(outcomeFilter, value)}>{label}</button>)}
              <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
                정확한 총 {catalog.total} · 표시 {catalogRows.length}{lastUpdated ? " · 갱신 " + lastUpdated.toLocaleTimeString("ko-KR") : ""}
              </span>
            </div>
            <div className="hof-scroll" tabIndex="0" aria-label="AI 연구 카탈로그 표">
              <table className="data-table hof-table hof-catalog-table">
                <thead><tr><th scope="col" className="hof-identity">run / gen</th><th scope="col">종류</th><th scope="col">상태</th><th scope="col">gate</th><th scope="col">결과</th><th scope="col" className="hof-num">score</th><th scope="col" className="hof-num">운영금</th><th scope="col" className="hof-num">총수익금(원)</th><th scope="col" className="hof-num">총수익률</th><th scope="col" className="hof-num">연평균</th><th scope="col" className="hof-num">MDD</th><th scope="col" className="hof-num">Calmar</th><th scope="col" className="hof-num">payoff</th><th scope="col" className="hof-num">승률</th><th scope="col" className="hof-num">거래수</th><th scope="col" className="hof-num">일평균 거래</th><th scope="col" className="hof-num">최대 보유</th><th scope="col">백테 기간</th><th scope="col">매수 조건식</th><th scope="col">매도 조건식</th><th scope="col">사유</th><th scope="col">출처</th></tr></thead>
                <tbody>{catalogRows.map(row => <tr key={`${row.run_id}/${row.gen_no}`}>
                  <th scope="row" className="hof-identity">{row.label || "—"}</th><td>{row.kind || "—"}</td><td><HofStatusBadge value={row.status} /></td><td><HofGateBadge value={row.gate_passed} /></td>
                  <td><HofOutcomeBadge value={row.outcome} />{row.annual_unreliable ? <small className="hof-short-window" title="짧은 백테 기간의 연환산은 신뢰도가 낮습니다.">단기</small> : null}</td>
                  <td className="hof-num">{fmtNumber(row.score)}</td><td className="hof-num">{hofNumber(row.operating_capital_krw) ? fmtMoney(row.operating_capital_krw) : "—"}</td>
                  <td className="hof-num"><HofSignedValue value={row.return_krw} format={value => fmtMoney(Math.abs(value))} label="총수익금" /></td><td className="hof-num"><HofSignedValue value={row.return_pct} format={value => `${Math.abs(value).toFixed(1)}%`} label="총수익률" /></td>
                  <td className="hof-num"><HofSignedValue value={row.annual_return_pct} format={value => `${Math.abs(value).toFixed(1)}%`} label="연평균 수익률" /></td><td className="hof-num"><HofMddValue value={row.mdd_pct} /></td><td className="hof-num">{fmtNumber(row.calmar)}</td><td className="hof-num">{fmtNumber(row.payoff)}</td>
                  <td className="hof-num">{fmtPct(row.win_rate_pct)}</td><td className="hof-num">{fmtInt(row.trades)}</td><td className="hof-num">{fmtNumber(row.daily_avg_trades)}</td><td className="hof-num">{fmtInt(row.max_hold_count)}</td><td>{row.period || "—"}</td>
                  {/* v5.13.0(G4) — 조건식 이름 클릭 = 코드 즉시 열람. */}
                  <td className="hof-long">
                    <button type="button" className="hof-cond-link" title={(row.buy_name || "—") + " — 클릭하면 조건식 코드를 봅니다"}
                            onClick={() => setCodeView({ run_id: row.run_id, gen_no: row.gen_no, buy_name: row.buy_name, sell_name: row.sell_name })}>
                      {row.buy_name || "—"}
                    </button>
                  </td>
                  <td className="hof-long">
                    <button type="button" className="hof-cond-link sell" title={(row.sell_name || "—") + " — 클릭하면 조건식 코드를 봅니다"}
                            onClick={() => setCodeView({ run_id: row.run_id, gen_no: row.gen_no, buy_name: row.buy_name, sell_name: row.sell_name })}>
                      {row.sell_name || "—"}
                    </button>
                  </td>
                  <td className="hof-long" title={row.reason || "—"}>{row.reason || "—"}</td>
                  <td>{row.provenance && row.provenance.source ? row.provenance.source : "—"}</td>
                </tr>)}</tbody>
              </table>
            </div>
            {catalogRows.length === 0 && !loading && <div className="v4s-note">표시할 AI 연구 세대가 없습니다.</div>}
            {catalog.next !== null && <div style={{ textAlign: "center", marginTop: 12 }}>
              <button className="btn ghost sm" onClick={() => fetchCatalog(catalog.next, true)} disabled={loadingMore}>
                {loadingMore ? "불러오는 중…" : `더 보기 (${catalogRows.length}/${catalog.total})`}
              </button>
            </div>}
          </>
        )}
      </div>
      {galleryOpen && <ReferenceGallery baseUrl={baseUrl} initialZoom={galleryInitial}
                                        onClose={() => { setGalleryOpen(false); setGalleryInitial(null); }} />}
      {/* v5.13.0(G4) — 조건식 즉시 열람 모달(코드는 CodeViewer 가 /strategy_code 로 조회). */}
      {codeView && (
        <CodeViewer
          generation={{ gen_no: codeView.gen_no, buy_name: codeView.buy_name, sell_name: codeView.sell_name }}
          runId={codeView.run_id}
          baseUrl={baseUrl}
          onClose={() => setCodeView(null)}
        />
      )}
    </div>
  );
}

/* 📷 인간 결과 스크린샷 갤러리 모달.
   GET /reference_screenshots 로 파일명 목록(17장)을 받아 썸네일 그리드로 보여주고,
   썸네일 클릭 시 같은 모달에서 확대(라이트박스)한다. 이미지 src는
   baseUrl+'/reference_img/'+filename(StaticFiles 읽기 전용 마운트)로 직접 가져온다.
   스크린샷↔전략# 매핑은 불확실하므로 개별 행 정확 매핑을 시도하지 않고 전체 갤러리
   브라우징만 제공한다(정직). 모달 패턴은 CodeViewer(modal-bd/modal)를 따른다. */
function ReferenceGallery({ baseUrl, onClose, initialZoom }) {
  const [files, setFiles] = useState_rg(null);   // string[] | null
  const [err, setErr] = useState_rg(null);
  // v5.13.0(G1) — 스트립 썸네일 클릭 시 해당 이미지로 바로 확대 진입.
  const [zoom, setZoom] = useState_rg(initialZoom || null);     // 확대 중인 파일명 | null

  useEffect_rg(() => {
    if (!baseUrl) { setFiles([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/reference_screenshots", { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { if (!cancelled) { setFiles(j.screenshots || []); setErr(null); } })
      .catch(e => { if (!cancelled) setErr(String(e)); })
      .finally(() => {});
    return () => { cancelled = true; };
  }, [baseUrl]);

  const imgSrc = (name) => baseUrl + "/reference_img/" + encodeURIComponent(name);

  return (
    <div className="modal-bd"
         onMouseDown={(e) => { if (e.target === e.currentTarget) (zoom ? setZoom(null) : onClose()); }}>
      <div className="modal" style={{ width: "min(1100px, calc(100vw - 32px))" }}
           onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            📷 인간 결과 스크린샷
            <span className="sub">
              STOM_Good_Results — 결과 화면 {files ? files.length : "…"}장 · 스크린샷↔전략# 매핑 불확실(전체 브라우징)
            </span>
          </h2>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {zoom && (
              <button className="btn ghost sm" onClick={() => setZoom(null)}>← 그리드</button>
            )}
            <button className="btn ghost sm" onClick={onClose}>닫기</button>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
          {err ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--red)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              스크린샷 목록 조회 실패: {err}
            </div>
          ) : files == null ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              스크린샷 불러오는 중…
            </div>
          ) : files.length === 0 ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              표시할 스크린샷이 없습니다.
            </div>
          ) : zoom ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <img src={imgSrc(zoom)} alt={zoom}
                   style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain",
                            border: "1px solid var(--line-2)", borderRadius: 6 }} />
              <div style={{ fontSize: 11, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>{zoom}</div>
            </div>
          ) : (
            <div style={{ display: "grid",
                          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
              {files.map((name) => (
                <div key={name} onClick={() => setZoom(name)}
                     data-tip="클릭하면 확대"
                     style={{ cursor: "zoom-in", border: "1px solid var(--line-2)",
                              borderRadius: 6, overflow: "hidden", background: "var(--bg-0)" }}>
                  <img src={imgSrc(name)} alt={name} loading="lazy"
                       style={{ width: "100%", height: 120, objectFit: "cover", display: "block" }} />
                  <div style={{ fontSize: 9.5, color: "var(--ink-3)", fontFamily: "var(--mono)",
                                padding: "4px 6px", whiteSpace: "nowrap", overflow: "hidden",
                                textOverflow: "ellipsis" }}>
                    {name}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Track Z (PR-3) — dual-safe ESM export (kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { HallOfFamePanel, ReferenceGallery };
