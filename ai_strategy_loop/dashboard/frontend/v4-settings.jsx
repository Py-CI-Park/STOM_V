/* v4-settings.jsx — browser-only dashboard preferences; no server/runtime writes. */
const { useState: useState_v4s, useEffect: useEffect_v4s } = React;

const V4S_PREFERENCES = {
  appearance: ["stom_theme"],
  navigation: ["stom_active_tab", "stom_active_evolution_tab", "bt_subtab"],
};
function _v4sGet(key, dflt) { try { const v = window.localStorage.getItem(key); return v === null ? dflt : v; } catch (e) { return dflt; } }
function _V4sRow({ label, hint, children }) { return <div className="v4s-row"><div className="v4s-row-lbl"><b>{label}</b>{hint && <small>{hint}</small>}</div><div className="v4s-row-ctl">{children}</div></div>; }

function V4SettingsTab({ baseUrl, dashVersion }) {
  const [manifest, setManifest] = useState_v4s(null); const [health, setHealth] = useState_v4s(null);
  const [pendingReset, setPendingReset] = useState_v4s(""); const [storageMessage, setStorageMessage] = useState_v4s("");
  useEffect_v4s(() => { let alive = true; fetch("/ui/bundle/manifest.json?ts=" + Date.now(), { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null).then(j => alive && setManifest(j)).catch(() => {}); fetch((baseUrl || "") + "/health", { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null).then(j => alive && setHealth(j)).catch(() => {}); return () => { alive = false; }; }, [baseUrl]);
  const resetKeys = pendingReset ? V4S_PREFERENCES[pendingReset] : [];
  const resetCategory = () => { try { resetKeys.forEach(key => window.localStorage.removeItem(key)); setStorageMessage(`${resetKeys.length}개 허용된 ${pendingReset} 환경설정을 초기화했습니다. 새로고침 후 적용됩니다.`); } catch (e) { setStorageMessage("브라우저 저장소를 초기화하지 못했습니다: " + (e.message || "알 수 없는 오류")); } setPendingReset(""); };
  return <section className="v4-settings" aria-labelledby="v4-settings-heading"><h2 id="v4-settings-heading" className="panel-hd-title">설정 · 대시보드 관리</h2>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />Appearance / Layout</div></div><div className="panel-bd">
      <_V4sRow label="공통 레이아웃" hint="Live·백테스트·히스토리는 같은 12열·동일 높이 카드 계약을 사용합니다."><span className="mono">responsive · equal-height · 320px charts</span></_V4sRow>
      <_V4sRow label="테마" hint="상단 테마 버튼에서 변경하며 브라우저에만 저장됩니다."><span className="mono">{_v4sGet("stom_theme", "dark")}</span></_V4sRow>
    </div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />Browser State</div></div><div className="panel-bd"><p className="v4s-note">초기화는 아래 허용 목록의 UI 환경설정에만 적용됩니다. 임의의 stom_* 키, 연구 데이터 및 런타임 상태는 삭제하지 않습니다.</p>{Object.entries(V4S_PREFERENCES).map(([category, keys]) => <_V4sRow key={category} label={`${category} (${keys.length})`} hint={keys.join(' · ')}><button className="btn ghost sm" onClick={() => setPendingReset(category)}>미리보기·초기화</button></_V4sRow>)}{pendingReset && <div className="v4s-note" role="alert">{pendingReset}에서 삭제될 키: {resetKeys.join(" · ")}<button className="btn primary sm" onClick={resetCategory}>확인하고 초기화</button><button className="btn ghost sm" onClick={() => setPendingReset("")}>취소</button></div>}</div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />Runtime Diagnostics</div></div><div className="panel-bd"><_V4sRow label="서버 상태"><span className="mono">{health ? (health.status || "ok") : "사용 불가 또는 확인 중"}</span></_V4sRow><_V4sRow label="저장소 상태"><span className="mono" role="status">{storageMessage || "변경 없음"}</span></_V4sRow><p className="v4s-note">진단은 읽기 전용이며 실행 상태를 변경하지 않습니다.</p></div></div>
    <div className="panel"><div className="panel-hd"><div className="panel-hd-title"><span className="dot" />About / Governance</div></div><div className="panel-bd"><_V4sRow label="대시보드 버전"><span className="mono">{dashVersion || "—"}</span></_V4sRow><_V4sRow label="번들 빌드"><span className="mono">{manifest && manifest.bundles && manifest.bundles["app.js"] ? String(manifest.bundles["app.js"].v || "—") : "—"}</span></_V4sRow><p className="v4s-note">연구 시작, 게이트, export 및 human 승인 계약은 Live 탭 소유이며 여기서 변경할 수 없습니다.</p></div></div>
  </section>;
}
Object.assign(window, { V4SettingsTab });
export { V4SettingsTab };
