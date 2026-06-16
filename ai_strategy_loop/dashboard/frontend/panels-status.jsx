/* Reusable small panels — status / toolbar widgets (split from panels.jsx for the 800-line cap).
   연결 배지 · 루프 상태 배지 · 리서치 기준 배너 · export 결과 배너 등 "지금 상태가 뭔가"를
   한눈에 보여주는 가벼운 표시 위젯 묶음. app.jsx(헤더·상단 배너)와 panels.jsx(배럴)이 소비한다.

   stom-ui 전역(fmt* 등)은 절대 import-변환하지 않는다(window 전역으로 공유). React 훅은
   파일 고유 별칭(useState_pst / useEffect_pst)으로 destructure 한다(단일 번들 dup-globals 가드).
*/
const { useState: useState_pst, useEffect: useEffect_pst } = React;

function ConnBadge({ health, wsStatus }) {
  let cls = "badge idle", label = "확인중";
  if (wsStatus === "open" && health.connected) { cls = "badge ok"; label = `백엔드 연결됨 · v${health.contract_version ?? "?"}`; }
  else if (wsStatus === "demo") { cls = "badge warn"; label = "데모 모드 (백엔드 미접속)"; }
  else if (wsStatus === "reconnecting") { cls = "badge warn"; label = "연결 끊김 · 재연결 중"; }
  else if (wsStatus === "connecting") { cls = "badge idle"; label = "연결 시도중"; }
  return (
    <span className={cls}>
      <span className={`dot ${wsStatus === "reconnecting" ? "pulse-dot" : ""}`}></span>
      {label}
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    idle:     { cls: "badge idle", txt: "대기" },
    running:  { cls: "badge run",  txt: "실행중" },
    stopping: { cls: "badge warn", txt: "정지중" },
    complete: { cls: "badge done", txt: "완료" },
    error:    { cls: "badge err",  txt: "오류" },
  };
  const m = map[status] || map.idle;
  return (
    <span className={m.cls}>
      <span className={`dot ${status === "running" || status === "stopping" ? "pulse-dot" : ""}`}></span>
      {m.txt}
    </span>
  );
}

function ResearchCriteriaBanner({ state, baseUrl }) {
  const mode = state.active_config?.research_oos_mode || "disabled";
  const [payload, setPayload] = useState_pst(null);
  const [error, setError] = useState_pst("");

  useEffect_pst(() => {
    if (!baseUrl) return;
    let cancelled = false;
    const url = `${baseUrl}/research_criteria?mode=${encodeURIComponent(mode)}`;
    fetch(url, { signal: AbortSignal.timeout(2500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("research_criteria HTTP " + r.status)))
      .then(j => { if (!cancelled) { setPayload(j); setError(""); } })
      .catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [baseUrl, mode]);

  const label = payload?.label || (mode === "disabled" ? "OOS disabled" : `OOS ${mode}`);
  const warning = payload?.warning || "research/exploration only; not proof of human-level or production readiness.";
  const explanation = payload?.explanation_ko || "OOS를 후보 탈락에 쓰지 않는 연구 탐색 상태입니다.";

  return (
    <div className="panel" data-testid="research-criteria-banner">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>Research Criteria</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--amber)" }}>
          research_oos_mode={mode}
        </span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge warn">{label}</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
            {warning}
          </span>
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>
          {explanation}
        </div>
        {error && (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>
            research criteria route unavailable: {error}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Export 상태 배너 (P6 final_approval 결과 노출) ----
// final_approval(승인 export) 제어의 마지막 결과(lastReply)를 표시한다. 게이트는
//   ApprovalDialog(이름+"승인" 입력)가 유지하므로 여기선 결과만 보여준다(자동 export 아님).
function ExportStatusBanner({ reply }) {
  if (!reply || reply.action !== "final_approval") return null;
  const ok = reply.status === "ok";
  const buyName = reply.buy && reply.buy.name;
  const sellName = reply.sell && reply.sell.name;
  return (
    <div style={{
      padding: "10px 14px", borderRadius: 6, marginBottom: 4, fontSize: 12.5,
      border: `1px solid ${ok ? "rgba(46,204,113,0.4)" : "rgba(224,90,90,0.4)"}`,
      background: ok ? "rgba(46,204,113,0.08)" : "rgba(224,90,90,0.08)",
      color: "var(--ink-0)",
    }}>
      {ok ? (
        <span>
          ✓ 운영 strategy.db로 export 완료
          {reply.demo ? " (데모)" : ""} — 매수 <span className="mono">{buyName || "—"}</span> · 매도 <span className="mono">{sellName || "—"}</span>
          {reply.dest_db && <span className="mono" style={{ color: "var(--ink-3)" }}>{` → ${reply.dest_db}`}</span>}
        </span>
      ) : (
        <span style={{ color: "var(--red)" }}>✗ export 실패 — {reply.message || "알 수 없는 오류"}</span>
      )}
    </div>
  );
}

Object.assign(window, { ConnBadge, StatusBadge, ResearchCriteriaBanner, ExportStatusBanner });

// Track Z — dual-safe ESM export (stripped by build-app.mjs in the concat path; kept by the bundle for real module scope). KEEP on ONE physical line.
export { ConnBadge, StatusBadge, ResearchCriteriaBanner, ExportStatusBanner };
