/* Chart simulation tab — 좌측 패널 묶음 + 엔진 디스패처 (split from simulation.jsx).
   지표 라이브 테이블(SimIndicatorTable/Cell)·학습 모드(SimLearningPanel)·변수 워치(SimVariableWatch)·
   엔진 디스패처(SimChartByEngine — engineMode→차트 컴포넌트 선택).

   공용 상수/훅/헬퍼는 sim-tab-utils.jsx 에서 import. 차트 컴포넌트는 window 전역(엔진 토글 지원).
   stom-ui 전역(window._simTimeLabel 등)은 window 으로 호출(import 금지).
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_sim, useEffect_sim, useCallback_sim, useRef_sim, _simFmtNum, _SIM_WATCH_VARS, _loadWatchThresholds, _saveWatchThresholds, _evalWatch } from "./sim-tab-utils.jsx";

// ===========================================================================
// 엔진 디스패처 — engineMode(live/lwc/svg)에 맞는 차트 컴포넌트를 고른다.
//   live  → window.SimLiveChart(Canvas·기본). 미로드(부재)면 SimCandleChart 로 폴백(무중단).
//   lwc   → window.SimCandleChartLWC(부재 시 SimCandleChart 자동선택).
//   svg   → window.SimCandleChartSVG(부재 시 SimCandleChart).
//   모든 경로는 동일 props(bars/signals/curT/code/name/compact/indicators)를 받는다.
// ===========================================================================
function SimChartByEngine({ engineMode, ...props }) {
  const Live = window.SimLiveChart;
  const Lwc = window.SimCandleChartLWC;
  const Svg = window.SimCandleChartSVG;
  const Auto = window.SimCandleChart;
  if (engineMode === "live" && Live) return <Live {...props} />;
  if (engineMode === "svg" && Svg) return <Svg {...props} />;
  if (engineMode === "lwc" && Lwc) return <Lwc {...props} />;
  // 폴백 — 선택 엔진 컴포넌트가 아직 window 에 없으면 자동선택(LWC↔SVG) 래퍼.
  return Auto ? <Auto {...props} /> : null;
}

// ===========================================================================
// 변수 라이브 뷰 — 종목별 현재 지표 테이블(현재가·등락·체결강도·MA5/20/60·호가불균형).
//   갱신 시 값 변화 방향(상승=teal / 하락=red)으로 셀 색 플래시.
// ===========================================================================
function SimIndicatorCell({ value, digits, prev, className }) {
  // 이전값 대비 방향으로 1회 플래시. key 를 값+버전으로 바꿔 애니메이션 재시작.
  const dir = (prev == null || value == null || value === prev) ? "" :
    (value > prev ? "sim-flash-up" : "sim-flash-down");
  return (
    <td key={value + ":" + dir} className={(className || "") + " " + dir}>
      {_simFmtNum(value, digits)}
    </td>
  );
}

function SimIndicatorTable({ codes, barsByCode, nameByCode }) {
  const prevRef = useRef_sim({});
  const rows = (codes || []).map(code => {
    const arr = barsByCode[code] || [];
    const last = arr.length ? arr[arr.length - 1] : null;
    return { code, name: nameByCode[code] || code, bar: last };
  });
  // 이전값 스냅샷(렌더 후 갱신).
  const prev = prevRef.current;
  useEffect_sim(() => {
    const next = {};
    rows.forEach(r => { if (r.bar) next[r.code] = r.bar; });
    prevRef.current = next;
  });

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          지표 라이브
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>현재 시각 기준</span>
      </div>
      <div className="panel-bd" style={{ overflowX: "auto", padding: "6px 8px" }}>
        <table className="sim-live-table">
          <thead>
            <tr>
              <th>종목</th><th>현재가</th><th>등락%</th><th>강도</th>
              <th>VWAP</th><th>MA5</th><th>MA20</th><th>MA60</th><th>호가불균형</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ code, name, bar }) => {
              const p = prev[code] || {};
              if (!bar) {
                return (
                  <tr key={code}>
                    <td title={name}>{code}</td>
                    <td colSpan={8} style={{ color: "var(--ink-3)" }}>대기…</td>
                  </tr>
                );
              }
              return (
                <tr key={code}>
                  <td title={name} style={{ color: "var(--ink-1)" }}>{code}</td>
                  <SimIndicatorCell value={bar.c} digits={0} prev={p.c} />
                  <td className={bar.change > 0 ? "num-pos" : bar.change < 0 ? "num-neg" : ""}>
                    {bar.change > 0 ? "+" : ""}{(bar.change || 0).toFixed(2)}
                  </td>
                  <SimIndicatorCell value={bar.strength} digits={0} prev={p.strength} />
                  <SimIndicatorCell value={bar.vwap} digits={0} prev={p.vwap} />
                  <SimIndicatorCell value={bar.ma5} digits={0} prev={p.ma5} />
                  <SimIndicatorCell value={bar.ma20} digits={0} prev={p.ma20} />
                  <SimIndicatorCell value={bar.ma60} digits={0} prev={p.ma60} />
                  <SimIndicatorCell value={bar.imbalance} digits={2} prev={p.imbalance} />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ===========================================================================
// 학습 모드 패널 — 신호 자동 일시정지 토글 + 키보드 힌트 + 신호 북마크(클릭 시킹).
// ===========================================================================
function SimLearningPanel({ autoPause, onToggleAutoPause, signals, curT, highlightSig, onSeek }) {
  const rows = signals || [];
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          학습 모드
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10, padding: "10px" }}>
        {/* 자동 일시정지 토글 */}
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={autoPause} onChange={onToggleAutoPause}
                 style={{ accentColor: "var(--violet)" }} />
          <span style={{ fontSize: 11.5, color: "var(--ink-1)" }}>신호 자동 일시정지</span>
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", marginLeft: "auto" }}>
            매수 시각 도달 시 정지
          </span>
        </label>

        {/* 키보드 힌트 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 10, color: "var(--ink-3)" }}>
          <span className="sim-kbd">Space</span> 재생/정지
          <span className="sim-kbd">←</span><span className="sim-kbd">→</span> 배속
          <span className="sim-kbd">Esc</span> 정지
        </div>

        {/* 신호 북마크 목록 → 클릭 시킹 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 3, maxHeight: 200, overflowY: "auto" }}>
          {rows.length === 0 ? (
            <div className="research-empty" style={{ fontSize: 10.5 }}>매매 신호가 없습니다.</div>
          ) : rows.map((s, i) => {
            const key = s.code + "@" + s.buy_hms;
            const reached = curT != null && s.buy_hms <= curT;
            const isHi = highlightSig === key;
            return (
              <button key={i} className={"sim-bookmark " + (reached ? "reached" : "pending")}
                onClick={() => onSeek(s.buy_hms)}
                style={isHi ? { borderColor: "var(--violet)", background: "rgba(124,108,240,0.12)" } : null}>
                <span className="mono" style={{ fontSize: 10, color: "var(--teal)", flexShrink: 0 }}>
                  ▲{window._simTimeLabel(s.buy_hms)}
                </span>
                <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", flexShrink: 0 }}>
                  {s.code}
                </span>
                <span className={"mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg")}
                      style={{ fontSize: 10.5, marginLeft: "auto", flexShrink: 0 }}>
                  {s.profit_pct >= 0 ? "+" : ""}{(s.profit_pct || 0).toFixed(1)}%
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// 변수 워치 패널 — 현재 프레임 값 + 사용자 임계 비교(≥/≤). 충족 행 녹색/미충족 적색,
//   충족 순간 1회 플래시. 임계 세트는 localStorage 저장(조건식 코드 평가는 범위 외 —
//   엔진 정합 신호는 /sim/signals 가 담당). 단일 종목(첫 선택) 기준.
// ===========================================================================
function SimVariableWatch({ codes, barsByCode, nameByCode }) {
  // 임계 맵: key → {op:">="|"<=", value:string}. localStorage 동기화.
  const [thresholds, setThresholds] = useState_sim(_loadWatchThresholds);
  // 워치 대상 종목(첫 선택). 다종목이어도 워치는 1종목 집중(직관·과밀 방지).
  const [watchCode, setWatchCode] = useState_sim((codes && codes[0]) || "");
  // 직전 충족 상태(플래시 트리거용) — ref 로 들고 리렌더 유발 안 함.
  const prevMetRef = useRef_sim({});

  // codes 변경 시 워치 종목 보정(현재 선택이 사라지면 첫 종목으로).
  useEffect_sim(() => {
    if (!codes || codes.length === 0) return;
    if (!codes.includes(watchCode)) setWatchCode(codes[0]);
  }, [codes.join(",")]);

  const setTh = useCallback_sim((key, patch) => {
    setThresholds(prev => {
      const cur = prev[key] || { op: ">=", value: "" };
      const next = { ...prev, [key]: { ...cur, ...patch } };
      _saveWatchThresholds(next);
      return next;
    });
  }, []);

  const clearAll = useCallback_sim(() => {
    setThresholds({}); _saveWatchThresholds({}); prevMetRef.current = {};
  }, []);

  const arr = barsByCode[watchCode] || [];
  const bar = arr.length ? arr[arr.length - 1] : null;

  // 충족 상태 스냅샷 갱신(플래시는 prev→met 전환 시 1회).
  useEffect_sim(() => {
    const snap = {};
    _SIM_WATCH_VARS.forEach(v => {
      snap[v.key] = bar ? _evalWatch(bar[v.key], thresholds[v.key]) : null;
    });
    prevMetRef.current = snap;
  });

  const prevMet = prevMetRef.current;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          변수 워치
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {codes && codes.length > 1 && (
            <select className="select" value={watchCode} onChange={e => setWatchCode(e.target.value)}
                    aria-label="관찰 종목 선택" style={{ fontSize: 10.5, padding: "2px 6px", height: "auto" }}>
              {codes.map(c => <option key={c} value={c}>{nameByCode[c] || c}</option>)}
            </select>
          )}
          <button className="btn ghost sm" onClick={clearAll} style={{ fontSize: 10, padding: "2px 7px" }}>
            임계 초기화
          </button>
        </div>
      </div>
      <div className="panel-bd" style={{ padding: "6px 8px" }}>
        {!bar ? (
          <div className="research-empty" style={{ fontSize: 10.5 }}>재생을 시작하면 현재 값이 표시됩니다.</div>
        ) : (
          <table className="sim-live-table" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>변수</th>
                <th>현재값</th>
                <th style={{ width: 44 }}>조건</th>
                <th style={{ width: 76 }}>임계값</th>
              </tr>
            </thead>
            <tbody>
              {_SIM_WATCH_VARS.map(v => {
                const value = bar[v.key];
                const th = thresholds[v.key] || { op: ">=", value: "" };
                const met = _evalWatch(value, th);
                const was = prevMet[v.key];
                // 미설정 → 무색. 충족 → 녹/미충족 → 적. 막 충족(was≠true & met) → 플래시.
                const rowBg = met == null ? "transparent"
                  : met ? "rgba(76,214,179,0.10)" : "rgba(255,93,108,0.10)";
                const flash = (met === true && was !== true) ? "sim-flash-up" : "";
                const valTxt = value == null ? "—" : _simFmtNum(value, v.digits);
                return (
                  <tr key={v.key} className={flash} style={{ background: rowBg }}>
                    <td style={{ textAlign: "left", color: "var(--ink-1)" }}>{v.label}</td>
                    <td className="mono" style={{
                      color: met == null ? "var(--ink-1)" : met ? "var(--teal)" : "var(--red)",
                    }}>
                      {valTxt}
                    </td>
                    <td>
                      <select value={th.op} onChange={e => setTh(v.key, { op: e.target.value })}
                              className="mono" style={{
                                fontSize: 11, padding: "1px 2px", background: "var(--bg-0)",
                                color: "var(--ink-1)", border: "1px solid var(--line-1)", borderRadius: 4,
                              }}>
                        <option value=">=">≥</option>
                        <option value="<=">≤</option>
                      </select>
                    </td>
                    <td>
                      <input type="number" value={th.value}
                             onChange={e => setTh(v.key, { value: e.target.value })}
                             placeholder="—" className="mono"
                             style={{
                               width: "100%", fontSize: 11, padding: "2px 4px", textAlign: "right",
                               background: "var(--bg-0)", color: "var(--ink-1)",
                               border: "1px solid var(--line-1)", borderRadius: 4,
                             }} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <div style={{ fontSize: 9.5, color: "var(--ink-3)", marginTop: 6, lineHeight: 1.5 }}>
          임계는 현재 프레임 값과의 단순 비교다. 조건식 엔진 정합 매매 신호는
          위 <span style={{ color: "var(--teal)" }}>매수/매도 조건식</span> 선택 시 차트에 오버레이된다.
        </div>
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { SimChartByEngine, SimIndicatorCell, SimIndicatorTable, SimLearningPanel, SimVariableWatch };
