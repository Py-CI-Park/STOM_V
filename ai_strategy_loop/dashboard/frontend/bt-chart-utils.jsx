/* Backtest workbench analysis charts — shared helpers (split from backtest-charts.jsx for the 800-line cap).
   순수 SVG 차트 묶음(/bt/result analysis)이 공유하는 포맷·축약·모션·미니 컴포넌트 헬퍼.
   chart.jsx 의 디자인 언어(chart-wrap·chart-grid-line·chart-axis-text·Mini·LegendDot)를 그대로 따른다.

   소비처: bt-equity-charts / bt-distribution-charts / bt-stat-panels / bt-gui-parity / bt-result-area /
           backtest-charts(배럴). 각 차트가 필요한 심볼만 골라 import 한다.
*/
const {
  useState: useState_btc, useRef: useRef_btc, useMemo: useMemo_btc,
  useEffect: useEffect_btc, useCallback: useCallback_btc,
} = React;

// 만/억 단위 축약(원). 그래프 축 라벨 가독성용.
function _btMoneyTick(v) {
  const a = Math.abs(v);
  if (a >= 1e8) return (v / 1e8).toFixed(1) + "억";
  if (a >= 1e4) return (v / 1e4).toFixed(0) + "만";
  return Math.round(v).toLocaleString("ko-KR");
}

// YYYYMMDD(int) → MM/DD 축약 라벨.
function _btDateLabel(d) {
  const s = String(d);
  if (s.length === 8) return s.slice(4, 6) + "/" + s.slice(6, 8);
  return s;
}

// 연도 정보를 보강한 x축 날짜 라벨. 직전 틱과 연도가 다르거나(=경계) 첫 틱이면
//   YYYY-MM-DD 로, 그 외에는 MM/DD 로 표기해 축에 연도 맥락을 남긴다(틱 과밀 방지).
function _btDateLabelY(d, prevD) {
  const s = String(d);
  if (s.length !== 8) return _btDateLabel(d);
  const ps = prevD != null ? String(prevD) : "";
  const sameYear = ps.length === 8 && ps.slice(0, 4) === s.slice(0, 4);
  if (sameYear) return s.slice(4, 6) + "/" + s.slice(6, 8);
  return s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
}

// 축 눈금 값 배열 — P3 de-dup: 구현은 빌드 번들(stom-ui.js, format.ts)이 window._axisTicks 로
//   제공한다(ESM 모듈이라 babel/app.js 보다 먼저 로드). chart.jsx 와 동일 패턴 — babel 스코프
//   별칭만 둬서 기존 bare 호출(_btAxisTicks(...))이 그대로 해소되게 한다(call site 무변경).
const _btAxisTicks = window._axisTicks;

// ───────────────────────────────────────────────────────────────────────────
// 결과 CSV 내보내기(P4) — 일별 수익곡선(날짜·일별손익·누적수익)을 클라이언트 Blob 으로
//   다운로드한다. 백엔드 없이 a[download] 클릭(엑셀 한글 호환 위해 utf-8 BOM 선행).
//   sim 체결로그 CSV(simulation-charts.jsx _simDownloadSignalLogCsv)와 동일 규약:
//   utf-8 BOM · \r\n 줄바꿈 · RFC4180 따옴표 이스케이프. 자급자족 HTML 리포트(/bt/report)
//   는 그대로 두고, 표 데이터(수익곡선)를 표계산 도구로 옮길 수 있게 보완하는 것이 목적.
function _btCsvCell(v) {
  if (v == null) return "";
  const s = String(v);
  // 쉼표/따옴표/개행 포함 시 큰따옴표로 감싸고 내부 따옴표는 2배(RFC4180).
  return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

// analysis.equity(daily/cumulative) → CSV 문자열. 컬럼: 날짜·일별손익(원)·누적수익(원).
//   daily[i]={date,pnl} 와 cumulative[i]={date,cum_profit} 는 같은 거래일 인덱스로 정렬돼 있다.
function _btAnalysisCsv(analysis) {
  const eq = (analysis && analysis.equity) || {};
  const daily = eq.daily || [];
  const cumulative = eq.cumulative || [];
  const header = ["날짜", "일별손익(원)", "누적수익(원)"];
  const lines = [header.map(_btCsvCell).join(",")];
  // daily/cumulative 는 같은 거래일 인덱스로 정렬돼 있다(BtEquityChart 와 동일 가정).
  //   길이가 어긋나도 더 긴 쪽까지 안전하게 순회(누락 인덱스는 빈 칸).
  const rowN = Math.max(daily.length, cumulative.length);
  for (let i = 0; i < rowN; i++) {
    const d = daily[i] || {};
    const c = cumulative[i] || {};
    lines.push([
      _btCsvCell(d.date),
      _btCsvCell(d.pnl != null ? Math.round(d.pnl) : ""),
      _btCsvCell(c.cum_profit != null ? Math.round(c.cum_profit) : ""),
    ].join(","));
  }
  return "﻿" + lines.join("\r\n");   // utf-8 BOM — 엑셀 한글 깨짐 방지.
}

// 클라이언트 Blob 다운로드 — 백엔드 없이 a[download] 클릭. 파일명 백테스트_YYYY-MM-DD.csv.
function _btDownloadAnalysisCsv(analysis) {
  const csv = _btAnalysisCsv(analysis);
  const d = new Date();
  const ymd = d.getFullYear() + "-"
    + String(d.getMonth() + 1).padStart(2, "0") + "-"
    + String(d.getDate()).padStart(2, "0");
  const fname = "백테스트_" + ymd + ".csv";
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

const _BT_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"];

// prefers-reduced-motion 존중 — 모션 비활성 시 즉시 최종값.
function _btReducedMotion() {
  try {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) { return false; }
}

// rAF 카운트업 훅 — target 으로 durMs 동안 부드럽게 증가(0.6s 기본). 모션 off 면 즉시.
function _useCountUp(target, durMs) {
  const [val, setVal] = useState_btc(typeof target === "number" ? target : 0);
  const fromRef = useRef_btc(0);
  const rafRef = useRef_btc(0);
  useEffect_btc(() => {
    const to = typeof target === "number" && isFinite(target) ? target : 0;
    if (_btReducedMotion()) { setVal(to); return; }
    const from = fromRef.current;
    const dur = durMs || 600;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);   // easeOutCubic.
      setVal(from + (to - from) * eased);
      if (p < 1) { rafRef.current = requestAnimationFrame(tick); }
      else { fromRef.current = to; }
    };
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, durMs]);
  return val;
}

// SVG 아크 게이지(승률·MDD) — 0~max 비율을 반원 호로. value/max 정규화.
function _BtArcGauge({ value, max, color, label, sub }) {
  const v = typeof value === "number" && isFinite(value) ? value : 0;
  const frac = Math.max(0, Math.min(1, max ? v / max : 0));
  const R = 22, CX = 26, CY = 26, sw = 6;
  const circ = Math.PI * R;   // 반원 둘레.
  const dash = circ * frac;
  // 반원 경로(좌→우, 위로 볼록).
  const arc = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;
  return (
    <div className="bt-gauge-wrap">
      <svg width="52" height="34" viewBox="0 0 52 34">
        <path d={arc} fill="none" stroke="var(--line-2)" strokeWidth={sw} strokeLinecap="round" />
        <path d={arc} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
              strokeDasharray={`${dash.toFixed(1)} ${circ.toFixed(1)}`} />
      </svg>
      <div className="bt-gauge-num">
        <span className="summary-val" style={{ fontSize: 15, color }}>{label}</span>
        {sub && <span className="summary-sub">{sub}</span>}
      </div>
    </div>
  );
}

// 일별손익 미니 스파크라인(바). values=일별 pnl 배열.
function _BtSparkline({ values, w, h }) {
  const vals = Array.isArray(values) ? values : [];
  const W = w || 120, H = h || 24;
  if (vals.length === 0) return <svg className="bt-spark" viewBox={`0 0 ${W} ${H}`} />;
  const maxAbs = Math.max(1, ...vals.map(v => Math.abs(v || 0)));
  const n = vals.length;
  const bw = Math.max(1, (W / n) * 0.8);
  const mid = H / 2;
  return (
    <svg className="bt-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <line x1="0" x2={W} y1={mid} y2={mid} stroke="var(--line-1)" strokeWidth="0.5" />
      {vals.map((v, i) => {
        const val = v || 0;
        const bh = (Math.abs(val) / maxAbs) * (mid - 1);
        const x = (W / n) * (i + 0.5) - bw / 2;
        const y = val >= 0 ? mid - bh : mid;
        return <rect key={i} x={x} y={y} width={bw} height={Math.max(0.5, bh)}
                     fill={val >= 0 ? "var(--teal)" : "var(--red)"} opacity="0.8" />;
      })}
    </svg>
  );
}

// 차트 공용 빈 상태 오버레이.
function _BtChartEmpty({ message }) {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
      textAlign: "center", padding: "0 16px",
    }}>
      {message || "분석 데이터가 없습니다"}
    </div>
  );
}

// 만/억 축약(원) — 셀/축 라벨 공용(이 모듈 _btMoneyTick 과 동일 의도, 음수 부호 보존).
//   GUI 패리티 차트(bt-gui-parity)에서 사용한다.
function _gpMoney(v) {
  const a = Math.abs(v || 0);
  if (a >= 1e8) return ((v || 0) / 1e8).toFixed(1) + "억";
  if (a >= 1e4) return Math.round((v || 0) / 1e4) + "만";
  return Math.round(v || 0).toLocaleString("ko-KR");
}

export {
  useState_btc, useRef_btc, useMemo_btc, useEffect_btc, useCallback_btc,
  _btMoneyTick, _btDateLabel, _btDateLabelY, _btAxisTicks,
  _btCsvCell, _btAnalysisCsv, _btDownloadAnalysisCsv,
  _BT_WEEKDAYS, _btReducedMotion, _useCountUp,
  _BtArcGauge, _BtSparkline, _BtChartEmpty, _gpMoney,
};
