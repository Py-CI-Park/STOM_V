/* v4-settings.jsx — v5.5 F8: 설정 탭(대시보드 관리).
 *   ① 화면 배치(스테이지 열 수·연구실 매트릭스 기본) — localStorage 기반, 적용은 새로고침.
 *   ② UI 저장상태 초기화(stom_* 키) — 배치·폴드·선택 상태를 공장값으로.
 *   ③ 정보 — 대시보드 버전·번들 빌드·CSS 핀·서버 상태(읽기 전용).
 *   안전: 서버 설정/연구 설정은 다루지 않는다(연구 시작 설정은 Live 의 SettingsModal 소유,
 *   export/승인 계약 불변). 이 탭은 순수 클라이언트 표시 설정만 관리한다.
 */
const { useState: useState_v4s, useEffect: useEffect_v4s } = React;

function _v4sGet(key, dflt) {
  try { const v = window.localStorage.getItem(key); return v === null ? dflt : v; } catch (e) { return dflt; }
}
function _v4sSet(key, val) {
  try { window.localStorage.setItem(key, val); } catch (e) {}
}

function _V4sRow({ label, hint, children }) {
  return (
    <div className="v4s-row">
      <div className="v4s-row-lbl">
        <b>{label}</b>
        {hint && <small>{hint}</small>}
      </div>
      <div className="v4s-row-ctl">{children}</div>
    </div>
  );
}

function V4SettingsTab({ baseUrl, dashVersion }) {
  const [stageCols, setStageCols] = useState_v4s(() => _v4sGet("stom_v6_stage_cols", "4"));
  const [labAll, setLabAll] = useState_v4s(() => _v4sGet("stom_v55_lab_view", "matrix") !== "single");
  const [manifest, setManifest] = useState_v4s(null);
  const [health, setHealth] = useState_v4s(null);
  const [cleared, setCleared] = useState_v4s(0);
  const [dirty, setDirty] = useState_v4s(false);

  useEffect_v4s(() => {
    let alive = true;
    fetch("/ui/bundle/manifest.json?ts=" + Date.now(), { signal: AbortSignal.timeout(8000) })
      .then(r => r.ok ? r.json() : null).then(j => { if (alive) setManifest(j); }).catch(() => {});
    fetch((baseUrl || "") + "/health", { signal: AbortSignal.timeout(8000) })
      .then(r => r.ok ? r.json() : null).then(j => { if (alive) setHealth(j); }).catch(() => {});
    return () => { alive = false; };
  }, [baseUrl]);

  const stomKeys = (() => {
    try { return Object.keys(window.localStorage).filter(k => k.startsWith("stom_")); } catch (e) { return []; }
  })();
  const cssPin = (() => {
    const link = [...document.querySelectorAll('link[rel="stylesheet"]')].map(l => l.getAttribute("href") || "").find(h => h.includes("v4.css"));
    const m = link && link.match(/v=([\w-]+)/);
    return m ? m[1] : "—";
  })();

  return (
    <section className="v4-settings" aria-labelledby="v4-settings-heading">
      <h2 id="v4-settings-heading" className="panel-hd-title">설정 · 대시보드 관리</h2>

      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>화면 배치</div></div>
        <div className="panel-bd">
          <_V4sRow label="Live 스테이지 열 수" hint="스테이지(생성·백테·채점·반복) 내용 그리드 열 수">
            {["2", "4"].map(c => (
              <button key={c} type="button" className={"btn ghost sm" + (stageCols === c ? " on" : "")}
                      aria-pressed={stageCols === c}
                      onClick={() => { setStageCols(c); _v4sSet("stom_v6_stage_cols", c); setDirty(true); }}>{c}열</button>
            ))}
          </_V4sRow>
          <_V4sRow label="연구실 매트릭스 보기" hint="채점·부검의 5개 분석(히트맵·중요도·상관·조합·검증) 동시 표시">
            <button type="button" className={"btn ghost sm" + (labAll ? " on" : "")}
                    aria-pressed={labAll}
                    onClick={() => { const v = !labAll; setLabAll(v); _v4sSet("stom_v55_lab_view", v ? "matrix" : "single"); setDirty(true); }}>
              {labAll ? "매트릭스(기본)" : "개별 보기"}
            </button>
          </_V4sRow>
          {dirty && (
            <div className="v4s-note" role="status">
              변경은 저장되었습니다 — Live 탭에 적용하려면 <button className="btn primary sm" onClick={() => window.location.reload()}>새로고침</button>
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>UI 저장상태</div></div>
        <div className="panel-bd">
          <_V4sRow label={`저장된 UI 상태 ${stomKeys.length}개`} hint="배치·폴드·선택 탭 등 브라우저 저장값(연구 데이터 아님)">
            <button type="button" className="btn ghost sm"
                    onClick={() => {
                      try { stomKeys.forEach(k => window.localStorage.removeItem(k)); } catch (e) {}
                      setCleared(stomKeys.length); setDirty(true);
                    }}>공장값으로 초기화</button>
            {cleared > 0 && <span className="mono v4s-ok">{cleared}개 초기화됨 — 새로고침 시 적용</span>}
          </_V4sRow>
          <div className="v4s-keys mono">{stomKeys.join(" · ") || "(없음)"}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>정보 (읽기 전용)</div></div>
        <div className="panel-bd">
          <_V4sRow label="대시보드 버전" hint="STOM 본체 버전과 분리 관리 — 태그 V2UC-Dashboard-v*">
            <span className="mono">{dashVersion || "—"}</span>
          </_V4sRow>
          <_V4sRow label="번들 빌드"><span className="mono">{manifest && manifest.appJs ? String(manifest.appJs).slice(0, 12) : (manifest && manifest.v ? manifest.v : "—")}</span></_V4sRow>
          <_V4sRow label="CSS 핀"><span className="mono">{cssPin}</span></_V4sRow>
          <_V4sRow label="서버 상태"><span className="mono">{health ? (health.status || "ok") + (health.version ? " · " + health.version : "") : "—"}</span></_V4sRow>
          <div className="v4s-note">연구 시작·게이트·export 설정은 여기서 다루지 않습니다 — Live 탭 "▸ 설정·시작"(연구 설정)과 human 승인 계약은 불변.</div>
        </div>
      </div>
    </section>
  );
}

Object.assign(window, { V4SettingsTab });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4SettingsTab };
