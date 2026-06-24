/* 명예의 전당 — 인간 벤치마크 + AI 생성 통합 패널 + 스크린샷 갤러리 (split from chart.jsx, P5.4).
   HallOfFamePanel · ReferenceGallery. app.jsx 가 chart.jsx 배럴 경유로 HallOfFamePanel 을 import.
   - 작은 표현 컴포넌트(LegendDot)는 chart-primitives 에서 import.
   - 포맷 헬퍼(fmtMoney)는 stom-ui 빌드 번들이 제공하는 전역(connection.jsx 의 const X = window.X
     별칭이 babel 스코프보다 먼저 로드)을 bare 호출로 그대로 쓴다.
   - HallOfFamePanel 본문은 field-diff DEFER 결정에 따라 byte-identical 로 이동만 한다(병합/수정 금지).
*/
import { LegendDot } from "./chart-primitives.jsx";
import { HofInventoryGate } from "./hof-inventory.jsx";

// HallOfFamePanel · ReferenceGallery 가 쓰는 React hook 별칭(이동 시 각 모듈이 자체 선언).
const { useState: useState_eq, useEffect: useEffect_eq, useCallback: useCallback_eq } = React;
const { useState: useState_rg, useEffect: useEffect_rg } = React;

/* ─────────────────────────────────────────────────────────────────────────
   명예의 전당 — 인간 벤치마크(19전략) + AI 생성 통합 패널.

   GET /hall_of_fame 에서 {human:[...], ai:[...]} 를 받아 한 테이블에 합쳐 보여준다.
   - 금액은 원 단위(fmtMoney), 수익률은 '운영금 대비'(%), 연평균은 단리 환산.
   - AI 단기창(annual_unreliable)은 연평균을 회색 + '단기' 표기(과대 환산 경고).
   - 인간(👤)은 초록/중립, AI(🤖)는 보라(violet) 뱃지로 시각 구분 → 인간 벤치마크가
     'AI가 도달해야 할 목표선'으로 한눈에 보이게 한다.
   - 정렬 토글(총수익률/연평균/MDD/payoff) + 필터(전체/인간/시드/AI). 기본=총수익률 ↓.
   - demo면 미fetch(EquityOverlayChart 패턴). 빈 응답이면 빈 상태.
   ───────────────────────────────────────────────────────────────────────── */
function HallOfFamePanel({ baseUrl, wsStatus }) {
  const [data, setData] = useState_eq(null);   // {human:[...], ai:[...]}
  const [loading, setLoading] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [sortKey, setSortKey] = useState_eq("total_return_pct"); // total_return_pct|total_return_krw|annual_return_pct|mdd_pct|payoff
  const [filter, setFilter] = useState_eq("all");                // all|human|ai
  const [galleryOpen, setGalleryOpen] = useState_eq(false);      // 📷 인간 결과 스크린샷 모달.
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_eq(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    fetch(baseUrl + "/hall_of_fame", { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  // 최초 + 30초 자동 새로고침.
  useEffect_eq(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const human = (data && data.human) || [];
  const ai = (data && data.ai) || [];

  // 통합 행: 인간(max_holdings)·AI(max_hold_count)를 공통 max_hold로 정규화.
  const rows = [
    ...human.map(h => ({ ...h, _maxHold: h.max_holdings })),
    ...ai.map(a => ({ ...a, _maxHold: a.max_hold_count })),
  ].filter(r => (filter === "all" ? true : r.kind === filter));

  // 정렬: 선택 키 내림차순(없는 값은 맨 뒤). MDD는 낮을수록 좋지만 일관성 위해
  //   '값 큰 순'을 그대로 쓰되, 사용자가 의도적으로 토글한다(라벨로 의미 전달).
  const sorted = rows.slice().sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const an = (typeof av === "number") ? av : -Infinity;
    const bn = (typeof bv === "number") ? bv : -Infinity;
    return bn - an;
  });

  const fmtPctSigned = (v) => (typeof v === "number"
    ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : "—");
  const fmtPlain = (v, d = 1) => (typeof v === "number" ? v.toFixed(d) : "—");
  const fmtInt2 = (v) => (typeof v === "number" ? Math.round(v).toLocaleString("ko-KR") : "—");

  const SORTS = [
    { key: "total_return_pct", label: "총수익률" },
    { key: "total_return_krw", label: "총수익금" },
    { key: "annual_return_pct", label: "연평균" },
    { key: "mdd_pct", label: "MDD" },
    { key: "payoff", label: "payoff" },
  ];
  const FILTERS = [
    { key: "all", label: "전체" },
    { key: "human", label: "👤 인간" },
    { key: "seed", label: "🌱 시드" },
    { key: "ai", label: "🤖 AI" },
  ];
  // 구분 뱃지 메타 — 인간 벤치마크(초록) / 시드 Tick_902 인간 튜닝(앰버) / AI 생성 AILOOP(보라).
  const HOF_KIND_META = {
    human: { color: "var(--green)",  label: "👤 인간", bg: "rgba(110,231,168,0.06)" },
    seed:  { color: "var(--amber)",  label: "🌱 시드", bg: "rgba(240,179,90,0.08)" },
    ai:    { color: "var(--violet)", label: "🤖 AI",   bg: "rgba(165,148,255,0.08)" },
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          🏆 성과 명예의 전당 — 인간 벤치마크 &amp; AI 생성
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <LegendDot color="var(--green)" label="👤 인간 벤치마크" />
          <LegendDot color="var(--amber)" label="🌱 시드(Tick_902 인간튜닝)" />
          <LegendDot color="var(--violet)" label="🤖 AI 생성(AILOOP)" />
          <span style={{ fontSize: 10, color: "var(--ink-3)", fontFamily: "var(--mono)" }}
                data-tip="백테 기간이 3개월 미만이면 연평균이 과대추정됨 — 신뢰 낮음">
            단기=연환산 신뢰낮음(짧은 백테)
          </span>
          <button className="btn ghost sm" onClick={() => setGalleryOpen(true)}
                  data-tip="인간 reference 결과 스크린샷 갤러리 열기">
            📷 인간 결과 스크린샷
          </button>
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}
                  data-tip="명예의 전당 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        <HofInventoryGate compact />
        {/* 정렬/필터 컨트롤 */}
        <div style={{ display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>정렬</span>
            {SORTS.map(s => (
              <button key={s.key} className="btn ghost sm"
                      onClick={() => setSortKey(s.key)}
                      style={sortKey === s.key
                        ? { color: "var(--amber)", borderColor: "var(--amber)" } : undefined}>
                {s.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>구분</span>
            {FILTERS.map(f => (
              <button key={f.key} className="btn ghost sm"
                      onClick={() => setFilter(f.key)}
                      style={filter === f.key
                        ? { color: "var(--ink-0)", borderColor: "var(--line-2)" } : undefined}>
                {f.label}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
            인간 {human.length} · 시드 {ai.filter(r => r.kind === "seed").length} · AI {ai.filter(r => r.kind === "ai").length}
          </div>
        </div>

        {isDemo ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            데모 모드 — 백엔드 연결 시 명예의 전당이 표시됩니다.
          </div>
        ) : err ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--red)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            조회 실패: {err}
          </div>
        ) : sorted.length === 0 ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            표시할 전략이 없습니다 (인간 벤치마크 JSON / AI 흑자 세대 누적 시 표시).
          </div>
        ) : (
          <div className="hof-scroll" style={{ overflowX: "auto", width: "100%" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse",
                                                   fontFamily: "var(--mono)", fontSize: 12,
                                                   minWidth: 1180 }}>
              <thead>
                <tr style={{ color: "var(--ink-2)", fontSize: 10, letterSpacing: ".08em",
                             textTransform: "uppercase", borderBottom: "1px solid var(--line-2)" }}>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>구분</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>이름</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>총수익금(원)</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>총수익률%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>연평균%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>MDD%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>payoff</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>일평균거래</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>동시보유</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>운영금(원)</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>백테 기간</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => {
                  const _km = HOF_KIND_META[r.kind] || HOF_KIND_META.ai;
                  const accent = _km.color;
                  return (
                    <tr key={(r.kind || "") + (r.label || "") + i}
                        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "5px 8px" }}>
                        <span style={{
                          display: "inline-block", padding: "1px 6px", borderRadius: 4,
                          fontSize: 10, fontWeight: 600, color: accent,
                          border: `1px solid ${accent}`,
                          background: _km.bg,
                        }}>
                          {_km.label}
                        </span>
                      </td>
                      <td style={{ padding: "5px 8px", color: "var(--ink-0)" }}>{r.label || "—"}</td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: (typeof r.total_return_krw === "number" && r.total_return_krw > 0)
                                     ? "var(--teal)" : "var(--ink-0)" }}>
                        {typeof r.total_return_krw === "number" ? fmtMoney(r.total_return_krw) : "—"}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: (typeof r.total_return_pct === "number" && r.total_return_pct > 0)
                                     ? "var(--teal)" : "var(--ink-0)" }}>
                        {fmtPctSigned(r.total_return_pct)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: r.annual_unreliable ? "var(--ink-3)" : "var(--ink-0)" }}>
                        {fmtPctSigned(r.annual_return_pct)}
                        {r.annual_unreliable && (
                          <span
                            data-tip="백테 기간이 3개월 미만이라 연평균이 과대추정됨(1개월 7%→연84% 식). 단기 창은 신뢰 낮음."
                            title="백테 기간이 3개월 미만이라 연평균이 과대추정됨(1개월 7%→연84% 식). 단기 창은 신뢰 낮음."
                            style={{ fontSize: 9, color: "var(--ink-3)", marginLeft: 4,
                                     borderBottom: "1px dotted var(--ink-3)", cursor: "help" }}>
                            단기
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--red)" }}>
                        {fmtPlain(r.mdd_pct, 2)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {fmtPlain(r.payoff, 2)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {fmtPlain(r.daily_avg_trades, 1)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {typeof r._maxHold === "number" ? fmtPlain(r._maxHold, r.kind === "ai" ? 1 : 0) : "—"}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-2)" }}>
                        {fmtInt2(r.operating_capital_krw)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "left", color: "var(--ink-2)",
                                   whiteSpace: "nowrap", fontSize: 11 }}>
                        {r.period || "—"}
                        {typeof r.days === "number" && (
                          <span style={{ color: "var(--ink-3)", marginLeft: 5 }}>
                            ({r.days}일)
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {galleryOpen && (
        <ReferenceGallery baseUrl={baseUrl} onClose={() => setGalleryOpen(false)} />
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
function ReferenceGallery({ baseUrl, onClose }) {
  const [files, setFiles] = useState_rg(null);   // string[] | null
  const [err, setErr] = useState_rg(null);
  const [zoom, setZoom] = useState_rg(null);     // 확대 중인 파일명 | null

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
