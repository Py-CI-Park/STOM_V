/* Chart simulation — 멀티차트 오버레이 + 체결 로그 (split from simulation-charts.jsx for the 800-line cap).
   - SimOverlayChart : 선택 종목(≤4) 정규화(시작=100) 비교선 오버레이(순수 SVG).
   - SimSignalLog    : 신호(매수/매도) 시각·가격·수익률 목록 + CSV 내보내기(클라이언트 Blob).
   _sim CSV 헬퍼(_simCsvCell · _simCsvTime · _simSignalLogCsv · _simDownloadSignalLogCsv)는 본 파일 전용.

   소비처: simulation.jsx(SimOverlayChart · SimSignalLog import) · simulation-charts(배럴 재게시). */
import {
  useMemo_simc,
  _simTimeLabel, _simPriceTick,
  _SIM_OVERLAY_COLORS,
} from "./sim-chart-utils.jsx";

/* ─────────────── 멀티차트 오버레이 모드 (정규화 비교) ───────────────
   선택 종목들(≤4)을 한 차트에 정규화(각 종목 시작 종가=100) 라인으로 겹쳐 그린다.
   범례·색상 구분. 진행에 따라 함께 자라난다. 순수 SVG(라이브러리 불필요 — 비교 전용). */
function SimOverlayChart({ codes, barsByCode, nameByCode, curT }) {
  const series = useMemo_simc(() => {
    return (codes || []).map((code, idx) => {
      const arr = (barsByCode[code] || []);
      const base = arr.length ? (arr[0].c || 0) : 0;
      const pts = (base > 0)
        ? arr.map(b => ({ t: b.t, v: (b.c / base) * 100 }))
        : [];
      return { code, name: nameByCode[code] || code, color: _SIM_OVERLAY_COLORS[idx % 4], pts };
    });
  }, [codes.join(","), barsByCode]);

  const allVals = [];
  series.forEach(s => s.pts.forEach(p => allVals.push(p.v)));
  const hasData = allVals.length > 0;

  const W = 880, H = 360, padL = 48, padR = 16, padT = 16, padB = 26;
  const innerW = W - padL - padR, innerH = H - padT - padB;
  const vMax = hasData ? Math.max(100.5, ...allVals) : 105;
  const vMin = hasData ? Math.min(99.5, ...allVals) : 95;
  const vRange = (vMax - vMin) || 1;

  // 공통 시간축: 모든 종목 t 의 정렬 합집합 → x 위치(인덱스 기반 균등 — 비교 직관).
  const allT = useMemo_simc(() => {
    const set = new Set();
    series.forEach(s => s.pts.forEach(p => set.add(p.t)));
    return Array.from(set).sort((a, b) => a - b);
  }, [series]);
  const tIdx = useMemo_simc(() => {
    const m = new Map(); allT.forEach((t, i) => m.set(t, i)); return m;
  }, [allT]);
  const nT = allT.length;
  const xAt = (t) => {
    const i = tIdx.has(t) ? tIdx.get(t) : 0;
    return nT <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (nT - 1);
  };
  const yAt = (v) => padT + innerH - ((v - vMin) / vRange) * innerH;

  const linePath = (pts) => {
    if (pts.length < 2) return "";
    return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(p.t).toFixed(1)} ${yAt(p.v).toFixed(1)}`).join(" ");
  };

  return (
    <div className="panel" style={{ minWidth: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          <span className="mono" style={{ fontSize: 12.5 }}>정규화 오버레이 (시작=100)</span>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {series.map(s => {
            const last = s.pts.length ? s.pts[s.pts.length - 1].v : 100;
            return (
              <span key={s.code} className="mono" style={{ fontSize: 10, color: s.color, display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 9, height: 2, background: s.color, display: "inline-block" }}></span>
                {s.name} <span style={{ color: last >= 100 ? "var(--teal)" : "var(--red)" }}>{last.toFixed(1)}</span>
              </span>
            );
          })}
        </div>
      </div>
      <div className="panel-bd">
        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
            {/* 기준선 100 */}
            <line x1={padL} x2={W - padR} y1={yAt(100)} y2={yAt(100)}
                  stroke="rgba(255,255,255,0.15)" strokeWidth="1" strokeDasharray="3 3" />
            <text className="chart-axis-text" x={padL - 6} y={yAt(100) + 3} textAnchor="end" fill="var(--ink-3)">100</text>
            <text className="chart-axis-text" x={padL - 6} y={yAt(vMax) + 8} textAnchor="end" fill="var(--ink-2)">{vMax.toFixed(1)}</text>
            <text className="chart-axis-text" x={padL - 6} y={yAt(vMin)} textAnchor="end" fill="var(--ink-2)">{vMin.toFixed(1)}</text>
            {series.map(s => s.pts.length > 1 && (
              <path key={s.code} d={linePath(s.pts)} fill="none" stroke={s.color} strokeWidth="1.5" opacity="0.9" />
            ))}
            {/* 시간 라벨(시작·중간·끝) */}
            {nT > 0 && [0, Math.floor(nT / 2), nT - 1].map((i, k) => (
              <text key={k} className="chart-axis-text" x={xAt(allT[i])} y={H - 8} textAnchor="middle">
                {allT[i] != null ? _simTimeLabel(allT[i]) : ""}
              </text>
            ))}
            {!hasData && (
              <text x={W / 2} y={H / 2} textAnchor="middle" fill="var(--ink-3)" fontSize="12" className="mono">
                재생을 시작하면 정규화 비교선이 채워집니다
              </text>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}

/* CSV 셀 이스케이프 — 콤마/따옴표/줄바꿈 포함 시 큰따옴표 감싸기(따옴표는 2배).
   Phase13 리뷰 — 수식 인젝션 방어: =,+,-,@ 로 시작하면 앞에 ' 를 붙여 Excel/Sheets 가
   수식으로 평가하지 않게 한다(종목코드 등 비숫자 컬럼 안전 강화). */
function _simCsvCell(v) {
  let s = v == null ? "" : String(v);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

// buy_time/sell_time(YYYYMMDDHHMMSS) 우선 HH:MM:SS, 부재 시 hms(HHMMSS) 폴백.
function _simCsvTime(full, hms) {
  if (full != null && full !== "") {
    const s = String(full).padStart(14, "0");
    return s.slice(8, 10) + ":" + s.slice(10, 12) + ":" + s.slice(12, 14);
  }
  return _simTimeLabel(hms);
}

/* 체결 로그 → CSV 문자열(utf-8 BOM 포함). 컬럼: (종목코드)·매수시간·매도시간·매수가·매도가·수익률(%).
   종목코드는 어떤 행에라도 code 가 있을 때만 컬럼으로 포함한다(엑셀 한글 호환 위해 BOM 선행). */
function _simSignalLogCsv(rows) {
  const list = rows || [];
  const hasCode = list.some((r) => r && (r.code != null && r.code !== ""));
  const header = (hasCode ? ["종목코드"] : []).concat(["매수시간", "매도시간", "매수가", "매도가", "수익률(%)"]);
  const lines = [header.map(_simCsvCell).join(",")];
  for (let i = 0; i < list.length; i++) {
    const r = list[i] || {};
    const cells = hasCode ? [r.code != null ? r.code : ""] : [];
    cells.push(_simCsvTime(r.buy_time, r.buy_hms));
    cells.push(_simCsvTime(r.sell_time, r.sell_hms));
    cells.push(r.buy_price != null ? Math.round(r.buy_price) : "");
    cells.push(r.sell_price != null ? Math.round(r.sell_price) : "");
    cells.push((r.profit_pct || 0).toFixed(2));
    lines.push(cells.map(_simCsvCell).join(","));
  }
  return "﻿" + lines.join("\r\n");   // utf-8 BOM — 엑셀 한글 깨짐 방지.
}

// 클라이언트 Blob 다운로드 — 백엔드 없이 a[download] 클릭. 파일명 체결로그_YYYY-MM-DD.csv.
function _simDownloadSignalLogCsv(rows) {
  const csv = _simSignalLogCsv(rows);
  const d = new Date();
  const ymd = d.getFullYear() + "-"
    + String(d.getMonth() + 1).padStart(2, "0") + "-"
    + String(d.getDate()).padStart(2, "0");
  const fname = "체결로그_" + ymd + ".csv";
  try {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 0);
  } catch (e) { /* 브라우저 미지원/차단 시 조용히 무시. */ }
}

/* ② 체결 로그 — 신호(매수/매도) 목록. 현재 리플레이 시각(curT) 도달 행 하이라이트. */
function SimSignalLog({ signals, curT }) {
  const rows = signals || [];
  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          체결 로그
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
            {rows.length}건 · 엔진 신호
          </span>
          {rows.length > 0 && (
            <button className="btn ghost sm"
                    style={{ fontSize: 10, padding: "2px 8px" }}
                    onClick={() => _simDownloadSignalLogCsv(rows)}
                    title="체결 로그를 CSV 파일로 내보냅니다">
              CSV 내보내기
            </button>
          )}
        </div>
      </div>
      <div className="panel-bd" style={{ maxHeight: 420, overflowY: "auto", padding: "8px 10px" }}>
        {rows.length === 0 ? (
          <div className="research-empty">조건식을 선택하면 매매 신호가 표시됩니다.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {rows.map((s, i) => {
              const reached = curT != null && s.sell_hms <= curT;
              const buying = curT != null && s.buy_hms <= curT && s.sell_hms > curT;
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "5px 7px", borderRadius: 5,
                  border: "1px solid " + (buying ? "var(--amber)" : reached ? "var(--line-1)" : "var(--line-1)"),
                  background: buying ? "rgba(240,179,90,0.10)" : reached ? "var(--bg-0)" : "transparent",
                  opacity: reached || buying ? 1 : 0.5,
                }}>
                  <span className="mono" style={{ fontSize: 10, color: "var(--teal)", flexShrink: 0 }}>
                    ▲{_simTimeLabel(s.buy_hms)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--red)", flexShrink: 0 }}>
                    ▼{_simTimeLabel(s.sell_hms)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flex: 1, textAlign: "right", whiteSpace: "nowrap" }}>
                    {_simPriceTick(s.buy_price)}→{_simPriceTick(s.sell_price)}
                  </span>
                  <span className={"mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg")}
                        style={{ fontSize: 11, flexShrink: 0, width: 52, textAlign: "right" }}>
                    {s.profit_pct >= 0 ? "+" : ""}{(s.profit_pct || 0).toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export { SimOverlayChart, SimSignalLog };
