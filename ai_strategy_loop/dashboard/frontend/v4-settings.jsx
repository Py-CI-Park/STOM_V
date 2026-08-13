/* v4-settings.jsx — browser-only dashboard preferences and read-only diagnostics. */
import { AiProviderStatusPanel } from "./ai-provider-status.jsx";
const { useState: useState_v4s, useEffect: useEffect_v4s } = React;

const V4S_PREFERENCES = {
  appearance: ["stom_theme", "stom_chart_height"],
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
/* v5.13.2 — GPT 로그인 상태·만료·로그인 시작(사용자 지시: 수시 확인 + 설정에서 로그인). */
function _v4sFmtRemain(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  return h > 0 ? `${h}시간 ${m}분` : m > 0 ? `${m}분 ${r}초` : `${r}초`;
}
function _V4sGptAuthCard({ baseUrl }) {
  const [auth, setAuth] = useState_v4s(null);          // /gpt_auth/status 응답
  const [fetchedAt, setFetchedAt] = useState_v4s(0);   // 클라이언트 카운트다운 기준
  const [tick, setTick] = useState_v4s(0);
  const [loginBusy, setLoginBusy] = useState_v4s(false);
  const [loginMsg, setLoginMsg] = useState_v4s("");
  const [probeMsg, setProbeMsg] = useState_v4s("");
  // v5.13.2 — 서버가 만든 인증 URL. 서버가 창 없이 기동되면 webbrowser.open 이 조용히
  //   실패할 수 있어, URL 을 화면에 띄우지 않으면 사용자가 진행할 방법이 없다.
  const [authUrl, setAuthUrl] = useState_v4s("");
  const refresh = () => {
    fetch((baseUrl || "") + "/gpt_auth/status", { credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => { if (j) { setAuth(j); setFetchedAt(Date.now()); } })
      .catch(() => {});
  };
  useEffect_v4s(() => { refresh(); const id = setInterval(refresh, 30000); return () => clearInterval(id); }, [baseUrl]);
  useEffect_v4s(() => { const id = setInterval(() => setTick(t => t + 1), 1000); return () => clearInterval(id); }, []);
  const token = (auth && auth.token) || {};
  const drift = fetchedAt ? Math.floor((Date.now() - fetchedAt) / 1000) : 0;
  const remain = token.loaded ? Math.max(0, (Number(token.expires_in_seconds) || 0) - drift) : 0;
  const state = !auth ? "unknown"
    : !token.loaded ? "none"
      : (token.expired || remain <= 0) ? (token.has_refresh_token ? "refreshable" : "expired")
        : remain < 600 ? "expiring" : "ok";
  const badge = {
    unknown: ["확인 중…", "var(--ink-3)"],
    none: ["로그인 없음", "var(--red)"],
    expired: ["만료됨 — 재로그인 필요", "var(--red)"],
    refreshable: ["만료됨 — 자동 갱신 가능(갱신 토큰 보유)", "var(--amber)"],
    expiring: ["만료 임박", "var(--amber)"],
    ok: ["정상", "var(--teal)"],
  }[state];
  const startLogin = () => {
    setLoginBusy(true); setLoginMsg("로그인 창을 여는 중…"); setAuthUrl("");
    fetch((baseUrl || "") + "/gpt_auth/login_start", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: "{}", signal: AbortSignal.timeout(8000) })
      // v5.13.2 — 403(권한/분류) 같은 실패를 조용히 삼키면 "눌러도 아무 일 없음"이 된다.
      //   실제로 login_start 가 보안 분류표에 없어 늘 403 이었다. 이제 본문을 읽어 표시한다.
      .then(async r => {
        const body = await r.json().catch(() => null);
        if (!r.ok) throw new Error((body && (body.message || body.code)) || ("HTTP " + r.status));
        return body || {};
      })
      .then(j => {
        setLoginMsg(j.message || (j.already_running ? "이미 로그인 진행 중입니다." : "로그인 시작"));
        if (j.auth_url) setAuthUrl(j.auth_url);
        // 완료까지 폴링(최대 5분 + 여유) — 끝나면 상태 재조회.
        const t0 = Date.now();
        const poll = () => {
          fetch((baseUrl || "") + "/gpt_auth/login_state", { credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(8000) })
            .then(r => r.json())
            .then(s => {
              if (s && s.auth_url) setAuthUrl(s.auth_url);
              if (s.running && Date.now() - t0 < 330000) { setTimeout(poll, 2000); return; }
              setLoginBusy(false);
              setLoginMsg(s.result === true ? "✅ 로그인 성공 — 토큰이 저장되었습니다."
                : s.error ? "로그인 실패: " + s.error
                  : s.result === false ? "로그인이 완료되지 않았습니다(취소/타임아웃)." : "상태 확인 종료");
              if (s.result === true) setAuthUrl("");
              refresh();
            })
            .catch(() => { setLoginBusy(false); setLoginMsg("로그인 상태 확인 실패"); });
        };
        setTimeout(poll, 1200);
      })
      .catch(e => { setLoginBusy(false); setLoginMsg("로그인 시작 실패: " + (e && e.message ? e.message : e)); });
  };
  const probe = () => {
    setProbeMsg("연결 테스트 중…");
    fetch((baseUrl || "") + "/gpt_auth/test", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: "{}", signal: AbortSignal.timeout(10000) })
      .then(r => r.json())
      .then(j => setProbeMsg((j.status === "ok" ? "✅ " : "⚠ ") + (j.message || j.status)))
      .catch(e => setProbeMsg("테스트 실패: " + e));
  };
  return <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: badge[1] }} />AI 공급자 · GPT 로그인 <small className="v4s-en">ChatGPT OAuth</small></div>
      <span className="mono" style={{ fontSize: 11.5, color: badge[1] }}>● {badge[0]}</span></div>
    <div className="panel-bd">
      <p className="v4s-note">조건식 생성(LLM)에 쓰는 ChatGPT 계정 인증 상태입니다. 만료되면 AI 루프의 생성 단계가 멈춥니다. 로그인 버튼을 누르면 이 PC 브라우저에 ChatGPT 로그인 창이 열리고, 완료하면 자동으로 반영됩니다.</p>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>토큰 상태</b><span className="mono" style={{ color: badge[1] }}>{badge[0]}</span></div>
        <div className="v4s-probe-card"><b>만료까지</b><span className="mono">{token.loaded && remain > 0 ? _v4sFmtRemain(remain) : "—"}</span></div>
        <div className="v4s-probe-card"><b>자동 갱신 토큰</b><span className="mono">{auth ? (token.has_refresh_token ? "있음" : "없음") : "—"}</span></div>
        <div className="v4s-probe-card"><b>로컬 프록시</b><span className="mono">{auth ? (auth.proxy_running ? "실행 중" : "정지") : "—"}</span></div>
      </div>
      <div className="v4s-log-controls" style={{ marginTop: 10 }}>
        <button className="btn primary sm" type="button" onClick={startLogin} disabled={loginBusy}>{loginBusy ? "로그인 진행 중…" : "ChatGPT 로그인 시작"}</button>
        <button className="btn ghost sm" type="button" onClick={refresh}>상태 새로고침</button>
        <button className="btn ghost sm" type="button" onClick={probe}>연결 테스트</button>
      </div>
      {(loginMsg || probeMsg) && <p className="v4s-note mono" role="status" aria-live="polite">{loginMsg}{loginMsg && probeMsg ? " · " : ""}{probeMsg}</p>}
      {/* v5.13.2 — 인증 링크 상시 노출. 브라우저가 자동으로 열리지 않아도 여기서 진행할 수 있다. */}
      {authUrl && <div className="v4s-authlink" role="group" aria-label="ChatGPT 인증 링크">
        <b>인증 링크</b>
        <p className="v4s-note">브라우저 창이 자동으로 열리지 않았다면 아래 링크로 직접 로그인하세요(5분 내).</p>
        <div className="v4s-authlink-row">
          <a className="btn primary sm" href={authUrl} target="_blank" rel="noopener noreferrer">🔗 브라우저에서 열기</a>
          <button className="btn ghost sm" type="button" onClick={() => {
            try { navigator.clipboard.writeText(authUrl); setLoginMsg("인증 링크를 클립보드에 복사했습니다."); } catch (e) {}
          }}>링크 복사</button>
        </div>
        <code className="mono v4s-authlink-url">{authUrl}</code>
      </div>}
    </div></div>;
}

/* v5.13.2 — 설정 탭 테마 선택. 셸의 상단 토글과 같은 localStorage 키(stom_theme)와
   같은 data-theme 속성을 쓰므로 어느 쪽에서 바꿔도 즉시 일치한다. */
const _V4S_THEMES = [
  { id: "dark", label: "Dark", desc: "기본 다크 — 터미널 톤" },
  { id: "midnight", label: "Midnight", desc: "딥 네이비 — 장시간 야간 관찰(순흑보다 눈부심 적음)" },
  { id: "light", label: "Light", desc: "밝은 화면" },
  { id: "sepia", label: "Sepia", desc: "종이톤 — 밝은 환경에서 오래 읽기" },
  { id: "contrast", label: "High Contrast", desc: "고대비 — 저시력·발표용" },
];
function _V4sThemeRow() {
  const [theme, setTheme] = useState_v4s(() => _v4sGet("stom_theme", "dark"));
  const apply = (id) => {
    try {
      window.localStorage.setItem("stom_theme", id);
      document.documentElement.setAttribute("data-theme", id);
    } catch (e) {}
    setTheme(id);
  };
  return <_V4sRow label="테마" hint="브라우저에만 저장됩니다. 상단 테마 버튼과 동일한 설정입니다.">
    <div className="v4s-theme-picker" role="radiogroup" aria-label="화면 테마">
      {_V4S_THEMES.map(t => (
        <button key={t.id} type="button" role="radio" aria-checked={theme === t.id} title={t.desc}
                className={"btn ghost sm" + (theme === t.id ? " active" : "")}
                onClick={() => apply(t.id)}>{t.label}</button>
      ))}
    </div>
  </_V4sRow>;
}

/* v5.13.2 — 차트 높이 취향(설정 기능 강화). CSS 변수만 덮어써서 전 차트에 즉시 반영된다. */
const _V4S_CHART_HEIGHTS = [
  { id: "compact", label: "낮게", px: "clamp(320px, 28vw, 420px)" },
  { id: "default", label: "기본", px: "" },
  { id: "tall", label: "높게", px: "clamp(500px, 46vw, 680px)" },
];
function _V4sChartHeightRow() {
  const [size, setSize] = useState_v4s(() => _v4sGet("stom_chart_height", "default"));
  const apply = (id) => {
    const found = _V4S_CHART_HEIGHTS.find(h => h.id === id) || _V4S_CHART_HEIGHTS[1];
    try {
      window.localStorage.setItem("stom_chart_height", id);
      if (found.px) document.documentElement.style.setProperty("--v4-height-chart-primary", found.px);
      else document.documentElement.style.removeProperty("--v4-height-chart-primary");
    } catch (e) {}
    setSize(id);
  };
  return <_V4sRow label="차트 높이" hint="분석 차트의 기본 높이를 바꿉니다. 브라우저에만 저장됩니다.">
    <div className="v4s-theme-picker" role="radiogroup" aria-label="차트 높이">
      {_V4S_CHART_HEIGHTS.map(h => (
        <button key={h.id} type="button" role="radio" aria-checked={size === h.id}
                className={"btn ghost sm" + (size === h.id ? " active" : "")}
                onClick={() => apply(h.id)}>{h.label}</button>
      ))}
    </div>
  </_V4sRow>;
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
    {/* v5.13.2 — AI 공급자 인증을 설정 최상단에(수시 확인 요구). */}
    <_V4sGptAuthCard baseUrl={baseUrl} />
    {/* 페이지 27 — 실행 경로 전체(failover 순서·모델 카탈로그). 인증 카드 바로 아래에 둔다. */}
    <AiProviderStatusPanel baseUrl={baseUrl} />
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />화면 모양 · 배치 <small className="v4s-en">Appearance / Layout</small></div></div><div className="panel-bd">
      <_V4sRow label="공통 레이아웃" hint="뷰는 반응형 패널과 의미 있는 차트 프레임(상태·출처·원본값)을 사용합니다. 높이와 열 수는 콘텐츠·화면 폭별 계약입니다."><span className="mono">responsive panels · semantic chart frames</span></_V4sRow>
      {/* v5.13.2 — 테마를 설정에서도 직접 고른다(상단 버튼과 같은 저장소를 씁니다). */}
      <_V4sThemeRow />
      <_V4sChartHeightRow />
      <_V4sRow label="결과 분석 레이아웃" hint="History, Backtest와 Live가 공유합니다. 기본 3열이며 2열·3열·4열을 직접 선택할 수 있습니다."><span className="mono">{_v4sGet("stom_v511_result_layout", "3")}열</span></_V4sRow>
    </div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />버전 · 기능 확인 <small className="v4s-en">Release / Capability</small></div></div><div className="panel-bd"><p className="v4s-note">번들 manifest와 읽기 전용 /health 응답에서 받은 값만 표시합니다. 응답에 없는 기능은 지원으로 추정하지 않습니다.</p><div className="v4s-probe-grid"><div className="v4s-probe-card"><b>대시보드 릴리스</b><span className="mono">{dashVersion || "—"}</span></div><div className="v4s-probe-card"><b>번들 빌드</b><span className="mono">{bundleVersion}</span></div><div className="v4s-probe-card"><b>/health 상태</b><span className="mono">{healthStatus}</span></div>{capabilityRows.map(row => <div className="v4s-probe-card" key={row.label}><b>{row.label}</b><span className="mono">{row.value}</span></div>)}</div>{!capabilityRows.length && <p className="v4s-note" role="status">기능 확인 불가 — /health 또는 번들 manifest 에 capability 필드가 없습니다.</p>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />브라우저에 저장된 설정 <small className="v4s-en">Browser State</small></div></div><div className="panel-bd"><p className="v4s-note">초기화는 아래 허용 목록의 UI 환경설정에만 적용됩니다. 임의의 stom_* 키, 연구 데이터 및 런타임 상태는 삭제하지 않습니다.</p>{Object.entries(V4S_PREFERENCES).map(([category, keys]) => <_V4sRow key={category} label={`${category} (${keys.length})`} hint={keys.join(" · ")}><button className="btn ghost sm" type="button" onClick={() => setPendingReset(category)}>미리보기·초기화</button></_V4sRow>)}{pendingReset && <div className="v4s-note" role="alert">{pendingReset}에서 삭제될 키: {resetKeys.join(" · ")}<button className="btn primary sm" type="button" onClick={resetCategory}>확인하고 초기화</button><button className="btn ghost sm" type="button" onClick={() => setPendingReset("")}>취소</button></div>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />로그 보기 (읽기 전용) <small className="v4s-en">Log Diagnostics</small></div></div><div className="panel-bd"><p className="v4s-note">브라우저 메모리 링과 인증된 GET /debug/logs?lines=200만 수동으로 읽습니다. 표시·복사·내보내기 전 API 키·토큰·Bearer·쿠키·절대 경로를 다시 가립니다. 저장소, 제어 WebSocket, POST는 사용하지 않습니다.</p><div className="v4s-log-controls"><label htmlFor="v4s-log-level">수준</label><select id="v4s-log-level" value={levelFilter} onChange={e => setLevelFilter(e.target.value)} aria-label="로그 수준 필터"><option value="all">전체 수준</option><option value="ERROR">ERROR</option><option value="REJECT">REJECT</option><option value="CONSOLE">CONSOLE</option><option value="WARNING">WARNING</option><option value="INFO">INFO</option></select><label htmlFor="v4s-log-source">출처</label><select id="v4s-log-source" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)} aria-label="로그 출처 필터"><option value="all">전체 출처</option><option value="browser">브라우저 링</option><option value="server">서버 링</option></select><label htmlFor="v4s-log-query">검색</label><input id="v4s-log-query" type="search" value={logQuery} onChange={e => setLogQuery(e.target.value)} placeholder="가려진 로그 검색" aria-label="가려진 로그 검색" /><button className="btn ghost sm" type="button" onClick={refreshLogs} disabled={logState === "loading"} aria-label="서버 로그 수동 새로고침">{logState === "loading" ? "읽는 중" : "수동 새로고침"}</button><button className="btn ghost sm" type="button" onClick={copyLogs} disabled={!visibleLogRows.length} aria-label="가려진 로그 복사">가려진 로그 복사</button><button className="btn ghost sm" type="button" onClick={exportLogs} disabled={!visibleLogRows.length} aria-label="가려진 로그 텍스트 내보내기">가려진 로그 내보내기</button></div><p className="v4s-note mono" role="status" aria-live="polite">{logMessage}</p>{logState === "error" ? <p className="v4s-note" role="alert">로그 요청 오류입니다. 세션과 API Base URL을 확인한 뒤 수동 새로고침하세요.</p> : !visibleLogRows.length ? <p className="v4s-note" role="status">표시할 로그가 없습니다. 필터를 변경하거나 수동 새로고침하세요.</p> : <div className="v4s-log-table" tabIndex="0" aria-label="가려진 진단 로그 표"><table className="mono"><thead><tr><th scope="col">시각</th><th scope="col">수준</th><th scope="col">출처</th><th scope="col">메시지</th></tr></thead><tbody>{visibleLogRows.map(row => <tr key={row.id}><td>{_v4sTime(row.ts)}</td><td>{row.level}</td><td>{row.source}</td><td>{row.msg}</td></tr>)}</tbody></table></div>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />실행 상태 점검 <small className="v4s-en">Runtime Diagnostics</small></div></div><div className="panel-bd"><_V4sRow label="서버 상태"><span className="mono">{healthStatus}</span></_V4sRow><_V4sRow label="저장소 상태"><span className="mono" role="status">{storageMessage || "변경 없음"}</span></_V4sRow><p className="v4s-note">진단은 읽기 전용이며 실행 상태를 변경하지 않습니다.</p></div></div>
    {/* v5.13.4(QSP1 P2) — AI 개입 규약 카드(사용자 승인 2026-07-29). 정본 문서:
        docs/research/quant_scoring_pipeline/agent_intervention_guidelines.md */}
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--violet)" }} />AI 개입 규약 <small className="v4s-en">Agent Intervention</small></div></div><div className="panel-bd">
      <p className="v4s-note">LLM(gpt_auth)이 불가한 동안 AI 에이전트가 조건식 생성·수정을 대행합니다(사용자 승인). 주체가 누구든 <b>같은 게이트</b>를 통과해야 합니다.</p>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>생성 주체 정책</b><span className="mono">LLM 정상 → LLM · 불가 → 에이전트 대행</span></div>
        <div className="v4s-probe-card"><b>수정 절차(고정)</b><span className="mono">수정 명세 → 생성 → 의도-일치 게이트 → 재백테</span></div>
        <div className="v4s-probe-card"><b>게이트 판정</b><span className="mono">코드 판정(V1골격·V2명세·V3상한·V4preflight) — 주체가 못 뒤집음</span></div>
        <div className="v4s-probe-card"><b>금지</b><span className="mono">GUI DB 수정 · 엔진 로직 수정 · 실거래 반영</span></div>
      </div>
      <p className="v4s-note mono">정본: docs/research/quant_scoring_pipeline/agent_intervention_guidelines.md</p>
    </div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />권한 경계 <small className="v4s-en">Governance</small></div></div><div className="panel-bd"><p className="v4s-note">연구 시작, 게이트, export 및 human 승인 계약은 Live 탭 소유이며 여기서 변경할 수 없습니다.</p></div></div>
  </section>;
}
Object.assign(window, { V4SettingsTab });
export { V4SettingsTab };
