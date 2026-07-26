/* v4-settings.jsx — browser-only dashboard preferences and read-only diagnostics. */
const { useState: useState_v4s, useEffect: useEffect_v4s } = React;

const V4S_PREFERENCES = {
  appearance: ["stom_theme"],
  navigation: ["stom_active_tab", "stom_active_evolution_tab", "bt_subtab"],
  result_layout: ["stom_v511_result_layout", "stom_v511_live_stage_density"],
};
const V4S_LOG_LIMIT = 200;
function _v4sGet(key, dflt) { try { const v = window.localStorage.getItem(key); return v === null ? dflt : v; } catch (e) { return dflt; } }
function _V4sRow({ label, hint, children }) { return <div className="v4s-row"><div className="v4s-row-lbl"><b>{label}</b>{hint && <small>{hint}</small>}</div><div className="v4s-row-ctl">{children}</div></div>; }
function _v4sRedact(value) {
  const redact = window.__stomRedactLog;
  if (typeof redact === "function") return redact(value);
  return String(value == null ? "" : value).replace(/\b(?:set-)?cookie\s*[:=]\s*[^\r\n]*/gi, "Cookie: <redacted>").replace(/\b(?:authorization\s*[:=]?\s*)?bearer\s+[^\s,;]+/gi, "Bearer <redacted>").replace(/(?:[a-z]:[\\/][^\s,;'"`]+|\\\\[^\s,;'"`]+|(?<![:\w])\/(?!\/)[^\s,;'"`]+)/gi, "<absolute-path>").slice(0, 400);
}
function _v4sTime(value) { const date = new Date(Number(value) * 1000); return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString(); }
function _v4sRows(serverRows) {
  const browser = Array.isArray(window.__stomFeLog) ? window.__stomFeLog : [];
  return browser.map((row, index) => ({ id: `browser-${index}-${row.ts}`, source: "browser", level: _v4sRedact(row.level || "ERROR"), ts: Number(row.ts) || 0, msg: _v4sRedact(row.msg) }))
    .concat((Array.isArray(serverRows) ? serverRows : []).map((row, index) => ({ id: `server-${index}-${row.ts}`, source: _v4sRedact(row.logger || "server"), level: _v4sRedact(row.level || "INFO"), ts: Number(row.ts) || 0, msg: _v4sRedact(row.msg) })))
    .sort((a, b) => b.ts - a.ts).slice(0, V4S_LOG_LIMIT);
}
function _v4sProbeValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "지원" : "미지원";
  if (typeof value === "object") return "—";
  return String(value);
}
function _v4sCapabilityRows(manifest, health) {
  const capabilities = health && health.capabilities !== undefined ? health.capabilities : manifest && manifest.capabilities;
  if (Array.isArray(capabilities)) return capabilities.map(value => ({ label: String(value), value: "발행됨" }));
  if (capabilities && typeof capabilities === "object") return Object.entries(capabilities).map(([label, value]) => ({ label, value: _v4sProbeValue(value) }));
  return [];
}
function V4SettingsTab({ baseUrl, dashVersion }) {
  const [manifest, setManifest] = useState_v4s(null); const [health, setHealth] = useState_v4s(null);
  const [pendingReset, setPendingReset] = useState_v4s(""); const [storageMessage, setStorageMessage] = useState_v4s("");
  const [serverLogs, setServerLogs] = useState_v4s([]); const [logState, setLogState] = useState_v4s("not-loaded"); const [logMessage, setLogMessage] = useState_v4s("아직 로그를 불러오지 않았습니다. 수동 새로고침으로만 읽습니다."); const [levelFilter, setLevelFilter] = useState_v4s("all"); const [sourceFilter, setSourceFilter] = useState_v4s("all"); const [logQuery, setLogQuery] = useState_v4s("");
  useEffect_v4s(() => { let alive = true; fetch("/ui/bundle/manifest.json?ts=" + Date.now(), { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null).then(j => alive && setManifest(j)).catch(() => {}); fetch((baseUrl || "") + "/health", { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null).then(j => alive && setHealth(j)).catch(() => {}); return () => { alive = false; }; }, [baseUrl]);
  const resetKeys = pendingReset ? V4S_PREFERENCES[pendingReset] : [];
  const resetCategory = () => { try { resetKeys.forEach(key => window.localStorage.removeItem(key)); setStorageMessage(`${resetKeys.length}개 허용된 ${pendingReset} 환경설정을 초기화했습니다. 새로고침 후 적용됩니다.`); } catch (e) { setStorageMessage("브라우저 저장소를 초기화하지 못했습니다: " + (e.message || "알 수 없는 오류")); } setPendingReset(""); };
  const refreshLogs = () => {
    setLogState("loading"); setLogMessage("서버 진단 로그를 읽는 중입니다. 실행 상태는 변경하지 않습니다.");
    fetch((baseUrl || "") + "/debug/logs?lines=200", { method: "GET", credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(8000) })
      .then(async response => { const body = await response.json().catch(() => null); if (!response.ok) throw new Error((body && body.message) || `HTTP ${response.status}`); return body; })
      .then(body => { const rows = Array.isArray(body && body.logs) ? body.logs : []; setServerLogs(rows.slice(-V4S_LOG_LIMIT)); setLogState("ready"); setLogMessage(`${rows.length}건의 서버 로그를 읽었습니다. 브라우저 로그와 합쳐 최근 ${V4S_LOG_LIMIT}건만 표시합니다.`); })
      .catch(error => { setLogState("error"); setLogMessage("로그를 읽지 못했습니다: " + _v4sRedact((error && error.message) || "알 수 없는 오류")); });
  };
  const allLogRows = _v4sRows(serverLogs);
  const normalizedQuery = logQuery.trim().toLowerCase();
  const visibleLogRows = allLogRows.filter(row => (levelFilter === "all" || row.level.toUpperCase() === levelFilter) && (sourceFilter === "all" || (sourceFilter === "browser" ? row.source === "browser" : row.source !== "browser")) && (!normalizedQuery || `${row.level} ${row.source} ${row.msg}`.toLowerCase().includes(normalizedQuery)));
  const logText = visibleLogRows.map(row => `[${_v4sTime(row.ts)}] ${row.level} ${row.source}: ${row.msg}`).join("\n");
  const copyLogs = () => { if (!(navigator.clipboard && navigator.clipboard.writeText)) { setLogMessage("브라우저가 클립보드 복사를 지원하지 않습니다."); return; } navigator.clipboard.writeText(logText).then(() => setLogMessage(`${visibleLogRows.length}건의 이미 가려진 로그를 클립보드에 복사했습니다.`)).catch(() => setLogMessage("로그 복사에 실패했습니다.")); };
  const exportLogs = () => { const blob = new Blob([logText + (logText ? "\n" : "")], { type: "text/plain;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "stom-dashboard-redacted-logs.txt"; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url); setLogMessage(`${visibleLogRows.length}건의 이미 가려진 로그 내보내기를 시작했습니다.`); };
  const capabilityRows = _v4sCapabilityRows(manifest, health);
  const bundleVersion = manifest && manifest.bundles && manifest.bundles["app.js"] ? String(manifest.bundles["app.js"].v || "—") : "—";
  const healthStatus = health && health.status !== undefined ? _v4sProbeValue(health.status) : "—";
  return <section className="v4-settings" aria-labelledby="v4-settings-heading"><h2 id="v4-settings-heading" className="panel-hd-title">설정 · 대시보드 관리</h2>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />화면 모양 · 배치 <small className="v4s-en">Appearance / Layout</small></div></div><div className="panel-bd">
      <_V4sRow label="공통 레이아웃" hint="뷰는 반응형 패널과 의미 있는 차트 프레임(상태·출처·원본값)을 사용합니다. 높이와 열 수는 콘텐츠·화면 폭별 계약입니다."><span className="mono">responsive panels · semantic chart frames</span></_V4sRow>
      <_V4sRow label="테마" hint="상단 테마 버튼에서 변경하며 브라우저에만 저장됩니다."><span className="mono">{_v4sGet("stom_theme", "dark")}</span></_V4sRow>
      <_V4sRow label="결과 분석 레이아웃" hint="History, Backtest와 Live가 공유합니다. 기본 3열이며 2열·3열·4열을 직접 선택할 수 있습니다."><span className="mono">{_v4sGet("stom_v511_result_layout", "3")}열</span></_V4sRow>
    </div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />버전 · 기능 확인 <small className="v4s-en">Release / Capability</small></div></div><div className="panel-bd"><p className="v4s-note">번들 manifest와 읽기 전용 /health 응답에서 받은 값만 표시합니다. 응답에 없는 기능은 지원으로 추정하지 않습니다.</p><div className="v4s-probe-grid"><div className="v4s-probe-card"><b>대시보드 릴리스</b><span className="mono">{dashVersion || "—"}</span></div><div className="v4s-probe-card"><b>번들 빌드</b><span className="mono">{bundleVersion}</span></div><div className="v4s-probe-card"><b>/health 상태</b><span className="mono">{healthStatus}</span></div>{capabilityRows.map(row => <div className="v4s-probe-card" key={row.label}><b>{row.label}</b><span className="mono">{row.value}</span></div>)}</div>{!capabilityRows.length && <p className="v4s-note" role="status">기능 확인 불가 — /health 또는 번들 manifest 에 capability 필드가 없습니다.</p>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />브라우저에 저장된 설정 <small className="v4s-en">Browser State</small></div></div><div className="panel-bd"><p className="v4s-note">초기화는 아래 허용 목록의 UI 환경설정에만 적용됩니다. 임의의 stom_* 키, 연구 데이터 및 런타임 상태는 삭제하지 않습니다.</p>{Object.entries(V4S_PREFERENCES).map(([category, keys]) => <_V4sRow key={category} label={`${category} (${keys.length})`} hint={keys.join(" · ")}><button className="btn ghost sm" type="button" onClick={() => setPendingReset(category)}>미리보기·초기화</button></_V4sRow>)}{pendingReset && <div className="v4s-note" role="alert">{pendingReset}에서 삭제될 키: {resetKeys.join(" · ")}<button className="btn primary sm" type="button" onClick={resetCategory}>확인하고 초기화</button><button className="btn ghost sm" type="button" onClick={() => setPendingReset("")}>취소</button></div>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />로그 보기 (읽기 전용) <small className="v4s-en">Log Diagnostics</small></div></div><div className="panel-bd"><p className="v4s-note">브라우저 메모리 링과 인증된 GET /debug/logs?lines=200만 수동으로 읽습니다. 표시·복사·내보내기 전 API 키·토큰·Bearer·쿠키·절대 경로를 다시 가립니다. 저장소, 제어 WebSocket, POST는 사용하지 않습니다.</p><div className="v4s-log-controls"><label htmlFor="v4s-log-level">수준</label><select id="v4s-log-level" value={levelFilter} onChange={e => setLevelFilter(e.target.value)} aria-label="로그 수준 필터"><option value="all">전체 수준</option><option value="ERROR">ERROR</option><option value="REJECT">REJECT</option><option value="CONSOLE">CONSOLE</option><option value="WARNING">WARNING</option><option value="INFO">INFO</option></select><label htmlFor="v4s-log-source">출처</label><select id="v4s-log-source" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)} aria-label="로그 출처 필터"><option value="all">전체 출처</option><option value="browser">브라우저 링</option><option value="server">서버 링</option></select><label htmlFor="v4s-log-query">검색</label><input id="v4s-log-query" type="search" value={logQuery} onChange={e => setLogQuery(e.target.value)} placeholder="가려진 로그 검색" aria-label="가려진 로그 검색" /><button className="btn ghost sm" type="button" onClick={refreshLogs} disabled={logState === "loading"} aria-label="서버 로그 수동 새로고침">{logState === "loading" ? "읽는 중" : "수동 새로고침"}</button><button className="btn ghost sm" type="button" onClick={copyLogs} disabled={!visibleLogRows.length} aria-label="가려진 로그 복사">가려진 로그 복사</button><button className="btn ghost sm" type="button" onClick={exportLogs} disabled={!visibleLogRows.length} aria-label="가려진 로그 텍스트 내보내기">가려진 로그 내보내기</button></div><p className="v4s-note mono" role="status" aria-live="polite">{logMessage}</p>{logState === "error" ? <p className="v4s-note" role="alert">로그 요청 오류입니다. 세션과 API Base URL을 확인한 뒤 수동 새로고침하세요.</p> : !visibleLogRows.length ? <p className="v4s-note" role="status">표시할 로그가 없습니다. 필터를 변경하거나 수동 새로고침하세요.</p> : <div className="v4s-log-table" tabIndex="0" aria-label="가려진 진단 로그 표"><table className="mono"><thead><tr><th scope="col">시각</th><th scope="col">수준</th><th scope="col">출처</th><th scope="col">메시지</th></tr></thead><tbody>{visibleLogRows.map(row => <tr key={row.id}><td>{_v4sTime(row.ts)}</td><td>{row.level}</td><td>{row.source}</td><td>{row.msg}</td></tr>)}</tbody></table></div>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />실행 상태 점검 <small className="v4s-en">Runtime Diagnostics</small></div></div><div className="panel-bd"><_V4sRow label="서버 상태"><span className="mono">{healthStatus}</span></_V4sRow><_V4sRow label="저장소 상태"><span className="mono" role="status">{storageMessage || "변경 없음"}</span></_V4sRow><p className="v4s-note">진단은 읽기 전용이며 실행 상태를 변경하지 않습니다.</p></div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />권한 경계 <small className="v4s-en">Governance</small></div></div><div className="panel-bd"><p className="v4s-note">연구 시작, 게이트, export 및 human 승인 계약은 Live 탭 소유이며 여기서 변경할 수 없습니다.</p></div></div>
  </section>;
}
Object.assign(window, { V4SettingsTab });
export { V4SettingsTab };
