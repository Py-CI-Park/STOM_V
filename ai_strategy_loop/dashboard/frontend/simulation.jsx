/* Chart simulation tab — PR1 placeholder (health check only) */
const { useState: useState_sim, useEffect: useEffect_sim, useCallback: useCallback_sim } = React;

// PR1: 차트 시뮬레이션 탭 셸. /sim/health 를 폴링해 백엔드 라우터 연결 상태만
//   표시한다. PR3 에서 일일 DB 리플레이(날짜/종목 선택, 캔들차트, 재생 컨트롤)로 확장된다.
function SimulationTab({ baseUrl, wsStatus }) {
  const [health, setHealth] = useState_sim(null);   // {status, module, api_version}
  const [err, setErr] = useState_sim("");
  const [loading, setLoading] = useState_sim(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const checkHealth = useCallback_sim(() => {
    if (isDemo || !baseUrl) { setHealth(null); return; }
    setLoading(true);
    setErr("");
    fetch(baseUrl + "/sim/health", { signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setHealth(j || null))
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_sim(() => { checkHealth(); }, [checkHealth]);

  const connected = !!(health && health.status === "ok");
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: err ? "error" : "checking", color: err ? "var(--rose, #ff8a8a)" : "var(--amber)" };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          차트 시뮬레이션
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="mono" style={{ fontSize: 10.5, color: badge.color, letterSpacing: ".06em" }}>
            ● {badge.label}
          </span>
          <button className="btn ghost sm" onClick={checkHealth} disabled={isDemo || loading}>
            {loading ? "loading" : "refresh"}
          </button>
        </div>
      </div>
      <div className="panel-bd" style={{ padding: "28px 24px" }}>
        <h2 style={{ fontSize: 18, marginBottom: 10, letterSpacing: "-0.01em" }}>
          차트 시뮬레이션 (PR3에서 구현)
        </h2>
        <p style={{ color: "var(--ink-2)", lineHeight: 1.6, fontSize: 13, marginBottom: 16 }}>
          일일 tick/min DB 를 시간순으로 리플레이합니다. 날짜·종목 선택, 캔들차트
          (lightweight-charts), 매수/매도 신호 마커, 재생/일시정지/배속/시킹 컨트롤,
          다종목 동시 재생 그리드가 여기에 들어옵니다.
        </p>
        <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
          backend: {connected ? (health.module + " · ok") : (isDemo ? "demo (백엔드 연결 필요)" : (err || "연결 확인 중…"))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SimulationTab });
