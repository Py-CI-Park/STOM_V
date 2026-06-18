/* Chart simulation tab — 컨트롤/프리셋/미니맵/재생/보기 도구 바 (split from simulation.jsx).
   리플레이 설정(시간단위·날짜·종목 멀티선택·조건식·집계초)·원클릭 프리셋·시장 미니맵·
   재생 컨트롤(▶/⏸/⏹·배속·seek)·보기 도구 바(엔진/지표/분할 열·행)·엔진 설명 팝오버.

   공용 상수/훅/헬퍼는 sim-tab-utils.jsx 에서 import. stom-ui 전역은 window 으로 호출(import 금지).
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_sim, useMemo_sim, useRef_sim, useEffect_sim, _simFmtDate, _simTileColor, _SIM_MAX_CODES, _SIM_SPEEDS, _SIM_ENGINE_MODES, _SIM_CHART_MODES, _SIM_MAX_SPLIT_COLS, _SIM_VIEWBAR_LABEL, _SIM_ENGINE_ROWS } from "./sim-tab-utils.jsx";

// ===========================================================================
// 1. 컨트롤 바 — src·날짜·종목 멀티선택·조건식 buy/sell·agg_sec.
// ===========================================================================
function SimControlBar({
  baseUrl, isDemo, src, onSrc, date, onDate, days,
  stocks, selected, onToggleStock, stockQuery, onStockQuery,
  buy, onBuy, sell, onSell, strategies, aggSec, onAggSec, loadingStocks,
}) {
  const filteredStocks = useMemo_sim(() => {
    const q = (stockQuery || "").trim().toLowerCase();
    if (!q) return stocks;
    return stocks.filter(s =>
      (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
  }, [stocks, stockQuery]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          리플레이 설정
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* src + 날짜 + agg */}
        <div className="field-row">
          <div className="field">
            <label>시간단위</label>
            <div style={{ display: "flex", gap: 4 }}>
              {[["tick", "틱"], ["min", "분봉"]].map(([k, lbl]) => (
                <button key={k} onClick={() => onSrc(k)} className="mono" disabled={isDemo}
                  style={{
                    flex: 1, padding: "5px 8px", fontSize: 11, borderRadius: 5,
                    border: "1px solid " + (src === k ? "var(--teal-dim)" : "var(--line-1)"),
                    background: src === k ? "rgba(76,214,179,0.08)" : "transparent",
                    color: src === k ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                  }}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>날짜 ({days.length}일)</label>
            <select className="select" value={date || ""} onChange={e => onDate(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {days.map(d => <option key={d} value={d}>{_simFmtDate(d)}</option>)}
            </select>
          </div>
          {src === "tick" && (
            <div className="field" style={{ maxWidth: 110 }}>
              <label>집계(초)</label>
              <input className="input" type="number" min="1" max="60" value={aggSec}
                     onChange={e => onAggSec(e.target.value)} disabled={isDemo} />
            </div>
          )}
        </div>

        {/* 조건식 buy/sell */}
        <div className="field-row">
          <div className="field">
            <label>매수 조건식 (신호 오버레이)</label>
            <select className="select" value={buy} onChange={e => onBuy(e.target.value)} disabled={isDemo}>
              <option value="">— 없음 —</option>
              {strategies.buy.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field">
            <label>매도 조건식</label>
            <select className="select" value={sell} onChange={e => onSell(e.target.value)} disabled={isDemo}>
              <option value="">— 없음 —</option>
              {strategies.sell.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>

        {/* 종목 멀티선택(최대 4, 등락순 + 검색) */}
        <div className="field">
          <label>
            종목 선택 (최대 {_SIM_MAX_CODES} · 등락순)
            <span className="mono" style={{ color: "var(--ink-3)", marginLeft: 8 }}>
              {selected.length}/{_SIM_MAX_CODES} 선택
            </span>
          </label>
          <input className="input" placeholder="코드/이름 검색…" value={stockQuery}
                 onChange={e => onStockQuery(e.target.value)} spellCheck={false}
                 disabled={isDemo || !date} style={{ marginBottom: 6 }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 2, maxHeight: 220, overflowY: "auto" }}>
            {isDemo ? (
              <div className="research-empty">데모 모드 — 백엔드 연결 시 종목 목록이 표시됩니다.</div>
            ) : !date ? (
              <div className="research-empty">날짜를 먼저 선택하세요.</div>
            ) : loadingStocks ? (
              <div className="research-empty">종목 로딩 중…</div>
            ) : filteredStocks.length === 0 ? (
              <div className="research-empty">{stockQuery ? "검색 결과 없음" : "종목이 없습니다"}</div>
            ) : filteredStocks.map(s => {
              const active = selected.includes(s.code);
              const disabled = !active && selected.length >= _SIM_MAX_CODES;
              return (
                <button key={s.code} onClick={() => onToggleStock(s.code)} disabled={disabled}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "5px 8px", borderRadius: 5,
                    border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
                    background: active ? "rgba(76,214,179,0.08)" : "var(--bg-0)",
                    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.4 : 1,
                    textAlign: "left",
                  }}>
                  <span className="mono" style={{ fontSize: 11, color: active ? "var(--teal)" : "var(--ink-1)", flexShrink: 0, width: 56 }}>
                    {s.code}
                  </span>
                  <span style={{ fontSize: 11.5, color: "var(--ink-1)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {s.name}
                  </span>
                  <span className={"mono " + (s.last_change_pct > 0 ? "num-pos" : s.last_change_pct < 0 ? "num-neg" : "")}
                        style={{ fontSize: 10.5, flexShrink: 0, width: 56, textAlign: "right" }}>
                    {s.last_change_pct > 0 ? "+" : ""}{(s.last_change_pct || 0).toFixed(2)}%
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// 1c. 원클릭 프리셋 바 — [최근 거래일]·[최대 상승일] 즉시 적용(서버 /sim/demo 추천).
//     클릭 시 추천 날짜·등락 1위 종목을 선택하고 자동 재생까지 트리거한다.
// ===========================================================================
function SimPresetBar({ isDemo, busy, onPreset }) {
  if (isDemo) return null;
  const presets = [
    { mode: "latest", label: "최근 거래일", hint: "마지막 거래일·등락 1위" },
    { mode: "top_gainer", label: "최대 상승일", hint: "최근 중 등락 최대일" },
  ];
  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "8px 10px" }}>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginRight: 2 }}>
          빠른 시작
        </span>
        {presets.map(p => (
          <button key={p.mode} className="btn sm" onClick={() => onPreset(p.mode)} disabled={busy}
                  title={p.hint}
                  style={{ fontSize: 11, padding: "4px 10px", opacity: busy ? 0.5 : 1 }}>
            ⚡ {p.label}
          </button>
        ))}
        {busy && <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>추천 조회 중…</span>}
      </div>
    </div>
  );
}

// ===========================================================================
// 1b. 시장 미니맵 — 그날 종목을 등락율 색상 타일 그리드로(상승 빨강/하락 파랑 농도).
//     타일 클릭 → 선택 토글(최대 4). 선택 타일 테두리 강조. 검색 필터와 공존.
// ===========================================================================
function SimMarketMinimap({ stocks, selected, onToggleStock, query, isDemo, date, loading }) {
  // 검색 필터와 공존 — 컨트롤바와 동일 규칙(코드/이름 부분일치).
  const tiles = useMemo_sim(() => {
    const q = (query || "").trim().toLowerCase();
    const base = stocks || [];
    if (!q) return base;
    return base.filter(s =>
      (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
  }, [stocks, query]);

  let body;
  if (isDemo) {
    body = <div className="research-empty">데모 모드 — 백엔드 연결 시 시장 미니맵이 표시됩니다.</div>;
  } else if (!date) {
    body = <div className="research-empty">날짜를 먼저 선택하세요.</div>;
  } else if (loading) {
    body = <div className="research-empty">미니맵 로딩 중…</div>;
  } else if (tiles.length === 0) {
    body = <div className="research-empty">{query ? "검색 결과 없음" : "종목이 없습니다"}</div>;
  } else {
    body = (
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(74px, 1fr))",
        gap: 4, maxHeight: 240, overflowY: "auto",
      }}>
        {tiles.map(s => {
          const active = selected.includes(s.code);
          const atCap = !active && selected.length >= _SIM_MAX_CODES;
          const pct = Number(s.last_change_pct) || 0;
          return (
            <button key={s.code} onClick={() => onToggleStock(s.code)} disabled={atCap}
              title={s.code + " · " + (s.name || "") + " · " + (pct > 0 ? "+" : "") + pct.toFixed(2) + "%"}
              style={{
                display: "flex", flexDirection: "column", gap: 1, padding: "5px 6px",
                borderRadius: 5, textAlign: "left", overflow: "hidden",
                border: "1.5px solid " + (active ? "var(--teal)" : "transparent"),
                background: _simTileColor(pct),
                cursor: atCap ? "not-allowed" : "pointer", opacity: atCap ? 0.45 : 1,
                boxShadow: active ? "0 0 0 1px var(--teal-dim) inset" : "none",
              }}>
              <span style={{
                fontSize: 10.5, color: "var(--ink-1)", fontWeight: active ? 600 : 400,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {s.name || s.code}
              </span>
              <span className="mono" style={{ fontSize: 10, color: pct >= 0 ? "#ffd2d6" : "#cfe0ff" }}>
                {pct > 0 ? "+" : ""}{pct.toFixed(2)}%
              </span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--red)" }}></span>
          시장 미니맵
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
          {selected.length}/{_SIM_MAX_CODES} 선택 · 등락순
        </span>
      </div>
      <div className="panel-bd" style={{ padding: "8px 10px" }}>{body}</div>
    </div>
  );
}

// ===========================================================================
// 2. 재생 컨트롤 — ▶/⏸/⏹, 배속, 진행 슬라이더(seek), 현재 시각.
// ===========================================================================
function SimPlaybackBar({
  status, onPlay, onPause, onResume, onStop,
  speed, onSpeed, cursor, total, curT, sessionRange, onSeek, canPlay,
}) {
  const playing = status === "playing";
  const paused = status === "paused";
  const pct = total > 0 ? Math.round((cursor / total) * 100) : 0;

  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {!playing && !paused && (
            <button className="btn primary" onClick={onPlay} disabled={!canPlay}>▶ 재생</button>
          )}
          {playing && <button className="btn" onClick={onPause}>⏸ 일시정지</button>}
          {paused && <button className="btn primary" onClick={onResume}>▶ 재개</button>}
          {(playing || paused) && <button className="btn danger" onClick={onStop}>⏹ 정지</button>}

          {/* 배속 */}
          <div style={{ display: "flex", gap: 3, marginLeft: 8 }}>
            {_SIM_SPEEDS.map(sp => (
              <button key={sp} onClick={() => onSpeed(sp)} className="mono"
                style={{
                  padding: "4px 8px", fontSize: 10.5, borderRadius: 4,
                  border: "1px solid " + (speed === sp ? "var(--teal-dim)" : "var(--line-1)"),
                  background: speed === sp ? "rgba(76,214,179,0.08)" : "transparent",
                  color: speed === sp ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                }}>
                {sp === 600 ? "초고속" : sp + "x"}
              </button>
            ))}
          </div>

          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", marginLeft: 6 }}
                title="1x = 실시간(1초봉 1초/1분봉 1분). 배속만큼 빠르게 흐릅니다.">
            ⏱ {speed === 1 ? "실시간" : speed + "x"} 페이싱
          </span>
          <span className="mono" style={{ fontSize: 13, color: "var(--teal)", marginLeft: "auto", letterSpacing: ".04em" }}>
            {curT != null ? window._simTimeLabel(curT) : "--:--:--"}
            <span style={{ color: "var(--ink-3)", fontSize: 11 }}> · {cursor}/{total}</span>
          </span>
        </div>

        {/* 진행 슬라이더(seek) */}
        <input type="range" min="0" max={Math.max(0, total - 1)} value={cursor}
               disabled={!total} onChange={e => onSeek(parseInt(e.target.value, 10))}
               style={{ width: "100%", accentColor: "var(--teal)", cursor: total ? "pointer" : "default" }} />
        <div className="progress-track">
          <div className={"progress-fill " + (playing ? "running" : "")} style={{ width: pct + "%" }}></div>
        </div>
      </div>
    </div>
  );
}

function SimEnginePopover({ onClose }) {
  const ref = useRef_sim(null);
  useEffect_sim(() => {
    // 바깥 클릭·Esc 로 닫기(접근성). 마운트 시 포커스해 키보드 사용자가 바로 닫게.
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDoc);
    if (ref.current) { try { ref.current.focus(); } catch (e) {} }
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDoc);
    };
  }, [onClose]);
  return (
    <div ref={ref} role="dialog" aria-label="엔진 설명" tabIndex={-1}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onClose(); }}
      style={{
        position: "absolute", top: "100%", left: 0, marginTop: 6, zIndex: 30,
        minWidth: 320, maxWidth: 420, padding: "10px 12px",
        background: "var(--bg-1)", border: "1px solid var(--line-1)",
        borderRadius: 8, boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
        color: "var(--ink-1)",
      }}>
      <div className="mono" style={{ fontSize: 11, fontWeight: 600, color: "var(--ink-1)", marginBottom: 6 }}>
        엔진별 역할(비대칭) — 같은 데이터, 다른 강점
      </div>
      <table className="mono" style={{ width: "100%", fontSize: 10.5, color: "var(--ink-1)", borderCollapse: "collapse" }}>
        <tbody>
          {_SIM_ENGINE_ROWS.map(([name, desc]) => (
            <tr key={name}>
              <td style={{ padding: "3px 8px 3px 0", color: "var(--teal)", whiteSpace: "nowrap", verticalAlign: "top" }}>{name}</td>
              <td style={{ padding: "3px 0", color: "var(--ink-1)" }}>{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 8, textAlign: "right" }}>
        <button className="btn ghost sm" onClick={onClose} style={{ fontSize: 10.5, padding: "2px 10px" }}>닫기</button>
      </div>
    </div>
  );
}

// ===========================================================================
// 보기 도구 바 — 엔진 모드(라이브/LWC/SVG) + 보조지표 토글(가격·모멘텀·흐름)
//   + 멀티차트 모드(분할/오버레이) + 분할 열(1~5)/행 캡 + 엔진 설명 ⓘ.
// ===========================================================================
function SimViewBar({ indicators, onToggleIndicator, chartMode, onChartMode,
                      splitCols, onSplitCols, splitRows, onSplitRows,
                      colCap, codeCount, multi, engineMode, onEngineMode }) {
  // 지표 그룹 — 가격(MA/EMA/VWAP/볼린저/VWAP밴드) | 모멘텀(RSI/MACD) | 흐름(체결강도/호가/오더플로우/거래량MA/체결강도MA).
  //   key 세트는 Track S 와의 교차파일 계약(_SIM_DEFAULT_INDICATORS 와 정확히 일치).
  const indGroups = [
    ["가격", [["ma", "MA"], ["ema", "EMA"], ["vwap", "VWAP"], ["boll", "볼린저"], ["vwapband", "VWAP밴드"]]],
    ["모멘텀", [["rsi", "RSI"], ["macd", "MACD"]]],
    ["흐름", [["strength", "체결강도"], ["imbalance", "호가"], ["orderflow", "오더플로우"], ["volma", "거래량MA"], ["strma", "체결강도MA"]]],
  ];
  const [engineInfoOpen, setEngineInfoOpen] = useState_sim(false);
  const tbtn = (active, label, onClick, key, title) => (
    <button key={key} onClick={onClick} className="mono" title={title}
      style={{
        padding: "3px 9px", fontSize: 10.5, borderRadius: 4,
        border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
        background: active ? "rgba(76,214,179,0.10)" : "transparent",
        color: active ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
      }}>
      {label}
    </button>
  );
  // 열 선택지(1~colCap) — 종목수/상한(5)으로 클램프된 colCap 까지만 노출.
  const colChoices = [];
  for (let c = 1; c <= Math.max(1, colCap || 1); c += 1) colChoices.push(c);
  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", padding: "7px 10px" }}>
        <span className="mono" style={{ ..._SIM_VIEWBAR_LABEL, display: "inline-flex", alignItems: "center", gap: 4, position: "relative" }}>
          엔진
          <button type="button" aria-label="엔진 설명" title="엔진별 역할 설명"
            onClick={() => setEngineInfoOpen(v => !v)}
            style={{
              width: 16, height: 16, lineHeight: "14px", padding: 0, borderRadius: "50%",
              border: "1px solid var(--line-1)", background: "transparent",
              color: "var(--ink-1)", cursor: "pointer", fontSize: 10, fontWeight: 700,
            }}>ⓘ</button>
          {engineInfoOpen && <SimEnginePopover onClose={() => setEngineInfoOpen(false)} />}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          {_SIM_ENGINE_MODES.map(([m, lbl]) =>
            tbtn(engineMode === m, lbl, () => onEngineMode(m), "e" + m,
                 m === "live" ? "Canvas 라이브 렌더(현재봉 성장·플래시·풀 오더플로우)"
                   : m === "lwc" ? "lightweight-charts(전문 줌/크로스헤어·체결강도 오버레이만)" : "순수 SVG 폴백(풀 오더플로우)"))}
        </div>
        {/* LWC 비대칭 명시(P4): LWC 선택 시 일부 서브패인 미표시가 '고장'이 아니라 의도된
            ASYMMETRIC PARITY 임을 토글 옆에 캡션으로 분명히 한다(ⓘ 팝오버 보강, 로직 변화 없음). */}
        {engineMode === "lwc" && (
          <span className="mono"
                title="LWC(lightweight-charts)는 캔들 가독성을 위해 일부 하단 서브패인을 싣지 않습니다(의도된 비대칭). 전체 오더플로우/모멘텀은 라이브·SVG 엔진에서 보세요."
                style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
            LWC 비대칭 — RSI·MACD·호가불균형·net-delta 미표시(라이브·SVG 전용)
          </span>
        )}
        <span className="mono" style={{ ..._SIM_VIEWBAR_LABEL, marginLeft: 6 }}>지표</span>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {indGroups.map(([grp, defs]) => (
            <div key={grp} style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>{grp}</span>
              {defs.map(([k, lbl]) => tbtn(!!indicators[k], lbl, () => onToggleIndicator(k), k))}
            </div>
          ))}
        </div>
        {multi && (
          <>
            <span className="mono" style={{ ..._SIM_VIEWBAR_LABEL, marginLeft: 6 }}>보기</span>
            <div style={{ display: "flex", gap: 4 }}>
              {_SIM_CHART_MODES.map(([m, lbl]) =>
                tbtn(chartMode === m, lbl, () => onChartMode(m), m,
                     m === "overlay" ? "정규화 한 차트 겹침" : "종목별 분할 그리드"))}
            </div>
            {chartMode === "split" && (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                  <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>열</span>
                  {colChoices.map(c =>
                    tbtn(splitCols === c, String(c), () => onSplitCols(c), "c" + c, c + "열로 분할"))}
                </div>
                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                  <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>행</span>
                  <button className="mono" title="자동 행수(종목수/열)"
                    onClick={() => onSplitRows(0)}
                    style={{
                      padding: "3px 9px", fontSize: 10.5, borderRadius: 4,
                      border: "1px solid " + ((splitRows || 0) === 0 ? "var(--teal-dim)" : "var(--line-1)"),
                      background: (splitRows || 0) === 0 ? "rgba(76,214,179,0.10)" : "transparent",
                      color: (splitRows || 0) === 0 ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                    }}>자동</button>
                  <button className="mono" aria-label="행 줄이기" title="보이는 행 줄이기"
                    onClick={() => onSplitRows(Math.max(1, (splitRows || 0) - 1))}
                    style={{ padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "1px solid var(--line-1)", background: "transparent", color: "var(--ink-2)", cursor: "pointer" }}>−</button>
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-1)", minWidth: 18, textAlign: "center" }}>
                    {(splitRows || 0) === 0 ? "—" : splitRows}
                  </span>
                  <button className="mono" aria-label="행 늘리기" title="보이는 행 늘리기"
                    onClick={() => onSplitRows(Math.min(_SIM_MAX_CODES, (splitRows || 0) + 1))}
                    style={{ padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "1px solid var(--line-1)", background: "transparent", color: "var(--ink-2)", cursor: "pointer" }}>＋</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { SimControlBar, SimPresetBar, SimMarketMinimap, SimPlaybackBar, SimEnginePopover, SimViewBar };
