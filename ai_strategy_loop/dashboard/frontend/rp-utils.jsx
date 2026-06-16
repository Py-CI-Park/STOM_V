/* rp-utils.jsx — 리서치 프로 공용 유틸/공유 컴포넌트 (P5.7 분해 후).
   research-pro.jsx 패밀리가 공유하는 (1) 파일별 훅 별칭 (2) 무예외 fetch 헬퍼
   (3) 안전 포매터 (4) 워크벤치 느슨결합 디스패치 (5) edge_ratio 색상
   (6) 변수 칩(_RpVarChips) (7) 조건식 뷰어(_RpStrategyCode)를 모은다.

   제약(in-browser Babel): window 전역 컴포넌트 · 파일별 훅 별칭 · 한국어 UI.
   BtVarChips 는 window 에 없으므로(backtest.jsx 내부 전용) /bt/extract_vars 를 호출하는
   _RpVarChips 를 자체 구현한다 — window.BtVarChips 가 있으면 우선 사용한다(load-order 방어). */

const {
  useState: useState_rp,
  useEffect: useEffect_rp,
  useCallback: useCallback_rp,
  useMemo: useMemo_rp,
  useRef: useRef_rp,
} = React;

/* 공용 fetch(무예외) — 실패는 거부로 흘려 호출측 catch 가 빈 상태로 표준화한다. */
function _rpFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 8000) })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}
function _rpPostJson(url, body, timeoutMs) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
    signal: AbortSignal.timeout(timeoutMs || 8000),
  }).then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

/* 안전 포매터(전역 헬퍼 폴백 포함). */
const _rpMoney = (v) =>
  typeof window.fmtMoney === "function"
    ? window.fmtMoney(v)
    : typeof v === "number" && isFinite(v)
    ? Math.round(v).toLocaleString("ko-KR") + "원"
    : "—";
const _rpInt = (v) =>
  typeof v === "number" && isFinite(v) ? Math.round(v).toLocaleString("ko-KR") : "—";
const _rpNum = (v, d) =>
  typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 2 : d) : "—";
const _rpPct = (v, d) =>
  typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 1 : d) + "%" : "—";

/* 진화 워크벤치(백테스트 탭) 연동 — evolution-analysis.jsx 와 동일 payload·전달 경로.
   CustomEvent + localStorage + onOpenWorkbench(탭 전환). 직접 결합 없음(느슨 결합). */
function _rpOpenWorkbench(runId, genNo, onOpenWorkbench) {
  const detail = { run_id: runId, gen_no: genNo };
  try {
    window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
    localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
  } catch (e) {
    /* 전달 실패해도 탭 전환은 시도한다. */
  }
  if (typeof onOpenWorkbench === "function") onOpenWorkbench(detail);
}

/* edge_ratio 색(1.0 발산 기준) — analysis.jsx _edgeColor 와 동일 의미(자체 구현, 의존 제거). */
function _rpEdgeColor(er, alpha) {
  if (typeof er !== "number" || !isFinite(er)) return "rgba(40,50,60,0.4)";
  const a = alpha == null ? 0.85 : alpha;
  const d = Math.max(-1, Math.min(1, er - 1)); // 1.0 기준 발산
  if (d >= 0) {
    const t = Math.min(1, d / 0.6);
    return `rgba(${Math.round(60 - 25 * t)},${Math.round(170 + 20 * t)},${Math.round(120 + 10 * t)},${a})`;
  }
  const t = Math.min(1, -d / 0.6);
  return `rgba(${Math.round(200 + 40 * t)},${Math.round(110 - 40 * t)},${Math.round(90 - 30 * t)},${a})`;
}

/* ── 변수 칩(E8) — window.BtVarChips 가 있으면 사용, 없으면 /bt/extract_vars 자체 호출. ── */
function _RpVarChips({ baseUrl, isDemo, code }) {
  if (typeof window.BtVarChips === "function") {
    return React.createElement(window.BtVarChips, { baseUrl, isDemo, code });
  }
  const [known, setKnown] = useState_rp([]);
  const [unknown, setUnknown] = useState_rp([]);

  useEffect_rp(() => {
    if (isDemo || !baseUrl) {
      setKnown([]);
      setUnknown([]);
      return undefined;
    }
    const trimmed = (code || "").trim();
    if (!trimmed) {
      setKnown([]);
      setUnknown([]);
      return undefined;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      _rpPostJson(baseUrl + "/bt/extract_vars", { code: trimmed }, 5000)
        .then((j) => {
          if (cancelled) return;
          setKnown(Array.isArray(j && j.known) ? j.known : []);
          setUnknown(Array.isArray(j && j.unknown) ? j.unknown : []);
        })
        .catch(() => {
          if (!cancelled) {
            setKnown([]);
            setUnknown([]);
          }
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [baseUrl, isDemo, code]);

  if (known.length === 0 && unknown.length === 0) {
    return (
      <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
        사용 변수 칩 — 조건식의 한글 변수가 SSOT 화이트리스트와 대조되어 표시됩니다.
      </div>
    );
  }
  const chip = (v, ok) => (
    <span
      key={(ok ? "k:" : "u:") + v.name}
      className="mono rp-chip"
      title={ok ? "SSOT 화이트리스트 변수" : "SSOT 어휘 밖 — 오타이거나 미정의 변수일 수 있습니다"}
      style={{
        border: "1px solid " + (ok ? "var(--teal-dim)" : "rgba(240,179,90,0.45)"),
        color: ok ? "var(--teal)" : "var(--amber)",
        background: ok ? "rgba(76,214,179,0.06)" : "rgba(240,179,90,0.06)",
      }}
    >
      {ok ? "" : "⚠ "}
      {v.name}
      {v.count > 1 && <span style={{ color: "var(--ink-3)" }}>×{v.count}</span>}
    </span>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {known.map((v) => chip(v, true))}
        {unknown.map((v) => chip(v, false))}
      </div>
      <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
        SSOT 변수 {known.length} · 미확인 {unknown.length}
      </div>
    </div>
  );
}

/* ── 조건식 뷰어(E5/E8/E9) — run+gen 으로 /strategy_code 조회, 매수·매도 monospace + 변수칩. ── */
function _RpStrategyCode({ baseUrl, isDemo, runId, genNo }) {
  const [code, setCode] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);

  useEffect_rp(() => {
    if (isDemo || !baseUrl || !runId || genNo == null || genNo < 0) {
      setCode(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    /* /strategy_code 쿼리는 run/gen(런/세대) 키를 쓴다(코드 뷰어와 동일). */
    _rpFetchJson(
      baseUrl + "/strategy_code?run=" + encodeURIComponent(runId) + "&gen=" + encodeURIComponent(genNo),
      8000
    )
      .then((j) => {
        if (!cancelled) setCode(j || null);
      })
      .catch(() => {
        if (!cancelled) setCode(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, runId, genNo]);

  if (loading) {
    return <div className="mono rp-code-empty">조건식 불러오는 중…</div>;
  }
  if (!code) {
    return <div className="mono rp-code-empty">조건식 정보 없음</div>;
  }
  const buy = code.buy_code || "";
  const sell = code.sell_code || "";
  if (!buy && !sell) {
    return (
      <div className="mono rp-code-empty">
        이 세대의 조건식 코드가 없습니다{code.reason ? ` (${code.reason})` : ""}.
      </div>
    );
  }
  return (
    <div className="rp-code-grid">
      <div>
        <div className="rp-code-label" style={{ color: "var(--teal)" }}>
          매수 조건식 {code.buy_name ? `· ${code.buy_name}` : ""}
        </div>
        <pre className="rp-code-block">{buy || "(없음)"}</pre>
        <_RpVarChips baseUrl={baseUrl} isDemo={isDemo} code={buy} />
      </div>
      <div>
        <div className="rp-code-label" style={{ color: "var(--blue)" }}>
          매도 조건식 {code.sell_name ? `· ${code.sell_name}` : ""}
        </div>
        <pre className="rp-code-block">{sell || "(없음)"}</pre>
        <_RpVarChips baseUrl={baseUrl} isDemo={isDemo} code={sell} />
      </div>
    </div>
  );
}

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { useState_rp, useEffect_rp, useCallback_rp, useMemo_rp, useRef_rp, _rpFetchJson, _rpPostJson, _rpMoney, _rpInt, _rpNum, _rpPct, _rpOpenWorkbench, _rpEdgeColor, _RpVarChips, _RpStrategyCode };
