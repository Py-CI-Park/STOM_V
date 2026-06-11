/* Backtest workbench tab — PR1 placeholder (health check only) */
const { useState: useState_bt, useEffect: useEffect_bt, useCallback: useCallback_bt } = React;

// PR1: 백테스트 탭 셸. /bt/health 를 폴링해 백엔드 라우터 연결 상태만 표시한다.
//   PR2 에서 조건식 브라우저+에디터, 실행 설정, 결과/분석 패널로 확장된다.
function BacktestTab({ baseUrl, wsStatus }) {
  const [health, setHealth] = useState_bt(null);   // {status, module, api_version}
  const [err, setErr] = useState_bt("");
  const [loading, setLoading] = useState_bt(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const checkHealth = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setHealth(null); return; }
    setLoading(true);
    setErr("");
    fetch(baseUrl + "/bt/health", { signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setHealth(j || null))
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_bt(() => { checkHealth(); }, [checkHealth]);

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
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          백테스트 워크벤치
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
          백테스트 워크벤치 (PR2에서 구현)
        </h2>
        <p style={{ color: "var(--ink-2)", lineHeight: 1.6, fontSize: 13, marginBottom: 16 }}>
          GUI 백테스트 전체 기능을 웹으로 이관합니다. 조건식 브라우저·코드 에디터,
          기간/시간단위/수수료 실행 설정, 자본곡선·일별손익·히스토그램·히트맵·언더워터
          차트와 규칙 기반 인사이트 패널이 여기에 들어옵니다.
        </p>
        <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
          backend: {connected ? (health.module + " · ok") : (isDemo ? "demo (백엔드 연결 필요)" : (err || "연결 확인 중…"))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { BacktestTab });
