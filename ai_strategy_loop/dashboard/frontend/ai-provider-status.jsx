/* 페이지 27 — AI Provider 상태 (Newsletter_AI v0.68 운영 UX 적응).

   왜 필요한가: 뇌(LLM)가 죽으면 루프는 zero-LLM 으로 퇴화해 "논리 없는 조건식"을
   만든다 — 2026-08-01 실행이 실제로 그렇게 실패했다(provider=batch · MDD 139%).
   뇌의 상태는 상시 보여야 한다.

   v0.68 색상 규율: 녹색은 **실연결 성공**에만. 설정만 된 상태는 주황(ready),
   미설정은 회색. 키가 필요 없다는 이유로 미연결을 녹색으로 칠하지 않는다.
   전역 충돌 방지로 AiProv* 접두를 쓴다. */

const { useState: useState_ap, useEffect: useEffect_ap, useCallback: useCallback_ap } = React;

function aiProvGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

const AIPROV_STATE = {
  ok: ["사용 가능 (실연결)", "var(--teal)"],
  ready: ["준비됨 · 실연결 미확인", "var(--amber)"],
  unavailable: ["사용 불가", "var(--ink-3)"],
};

function aiProvRemain(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const total = Math.max(0, Number(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  return h > 0 ? `${h}시간 ${m}분` : `${m}분`;
}

function AiProvRow({ row }) {
  const [label, color] = AIPROV_STATE[row.state] || AIPROV_STATE.unavailable;
  return (
    <tr>
      <td className="num mono">{row.order}</td>
      <td><b>{row.label}</b><br/><small className="v4s-en">{row.id}</small></td>
      <td><span className="mono" style={{ color }}>● {label}</span></td>
      <td className="mono">{row.auth}</td>
      <td className="mono">{row.cost}</td>
      <td>{row.detail || "—"}<br/><small className="v4s-note">{row.note}</small></td>
    </tr>
  );
}

function AiProvModels({ baseUrl }) {
  const [rows, setRows] = useState_ap([]);
  const [open, setOpen] = useState_ap(false);
  useEffect_ap(() => { setRows([]); }, [baseUrl]);
  useEffect_ap(() => {
    if (!open || rows.length) return;
    aiProvGet(baseUrl, "/ai/providers/models").then((d) => setRows(d.models || [])).catch(() => {});
  }, [baseUrl, open, rows.length]);
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">모델 카탈로그</div>
        <button className="btn ghost sm" type="button" onClick={() => setOpen(!open)}>
          {open ? "접기" : "펼치기"}</button></div>
      {open && <div className="panel-bd">
        <p className="v4s-note">업스트림이 거부하는 모델은 자동으로 대체됩니다 —
          <b> fallback</b> 표시가 그 경우입니다(요청한 모델과 실제 호출 모델이 다름).</p>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>요청 모델</th><th>실제 업스트림</th><th>대체 여부</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.requested}>
                  <td className="mono">{row.requested}</td>
                  <td className="mono">{row.upstream}</td>
                  <td>{row.fallback ? <span className="badge warn">fallback</span> : <span className="mono">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>}
    </section>
  );
}

export function AiProviderStatusPanel({ baseUrl }) {
  const [payload, setPayload] = useState_ap(null);
  const [error, setError] = useState_ap("");

  const load = useCallback_ap(() => {
    aiProvGet(baseUrl, "/ai/providers")
      .then((d) => { if (d && d.available) { setPayload(d); setError(""); } else setError("공급자 상태를 불러오지 못했습니다."); })
      .catch(() => setError("공급자 상태 요청 실패"));
  }, [baseUrl]);

  useEffect_ap(() => { load(); const id = setInterval(load, 60000); return () => clearInterval(id); }, [load]);

  const rows = (payload && payload.providers) || [];
  const auth = (payload && payload.auth) || {};
  const effective = payload && payload.effective_provider;
  return (
    <div className="ai-provider-status" aria-label="AI Provider 상태 (페이지 27)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">AI Provider 상태 <small className="v4s-en">페이지 27 · 관측 전용</small></div>
          <span className="badge warn" title="이 화면은 외부 API 를 호출하지 않습니다(쿼터 소모 0). 실연결 확인은 설정의 연결 테스트가 담당합니다.">쿼터 소모 없음</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">조건식 생성의 <b>뇌</b>가 살아 있는지 봅니다. 뇌가 죽으면 루프는
            논리 없는 조건식을 만들며 헛돕니다 — 그 상태를 모르고 돌린 실행이 실제로 있었습니다.</p>
          <div className="v4s-probe-grid">
            <div className="v4s-probe-card"><b>현재 실행 경로</b>
              <span className="mono">{effective || "없음 — 뇌 부재"}</span></div>
            <div className="v4s-probe-card"><b>기본 모델</b>
              <span className="mono">{(payload && payload.default_model) || "—"}</span></div>
            <div className="v4s-probe-card"><b>인증원</b>
              <span className="mono">{auth.effective_source || "—"}{auth.selected_source && auth.selected_source !== auth.effective_source ? ` (선택 ${auth.selected_source})` : ""}</span></div>
            <div className="v4s-probe-card"><b>토큰 만료까지</b>
              <span className="mono">{aiProvRemain(auth.expires_in_seconds)}{auth.has_refresh_token ? " · 자동 갱신" : ""}</span></div>
          </div>
          {auth.message && <p className="v4s-note">{auth.message}</p>}
          <div className="v4s-log-controls"><button className="btn ghost sm" type="button" onClick={load}>새로고침</button></div>
          {error && <p className="tp-error" role="alert">{error}</p>}
        </div>
      </div>

      <section className="panel" style={{ marginTop: 12 }}>
        <div className="panel-hd"><div className="panel-hd-title">실행 경로 (failover 순서)</div>
          <small className="v4s-en">녹색 = 실연결 성공에만</small></div>
        <div className="panel-bd">
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th className="num">순서</th><th>경로</th><th>상태</th><th>인증</th><th>비용</th><th>설명</th></tr></thead>
              <tbody>{rows.map((row) => <AiProvRow key={row.id} row={row}/>)}</tbody>
            </table>
          </div>
        </div>
      </section>

      <AiProvModels baseUrl={baseUrl}/>
    </div>
  );
}
