/* Backtest workbench analysis charts — GUI 패리티 차트 묶음 (split from backtest-charts.jsx).
   B3 — STOM GUI PlotShow 2장 이미지 패리티 차트 6종.
   analysis.gui_parity = {mdd_random, daily, hourly, weekday, holding, trade_rolling}.
   순수 SVG(외부 라이브러리 금지)·기존 차트 컨벤션(chart-wrap·chart-axis-text·Mini·LegendDot·hover 툴팁).
*/
import { LegendDot, Mini, MetricHelpStrip } from "./chart.jsx";
import {
  useState_btc, useRef_btc, useMemo_btc,
  _btDateLabel, _gpMoney, _BtChartEmpty,
} from "./bt-chart-utils.jsx";
import { ChartFrame } from "./chart-frame.jsx";

function _btParityWithEvidence(Chart, describe) {
  return function EvidenceChart(props) {
    return <ChartFrame {...describe(props)}><Chart {...props} /></ChartFrame>;
  };
}

// 이미지1-(a) MDD 랜덤곡선 — 30개 셔플 누적곡선(회색) + 실제 누적곡선(주황). actual_mdd vs random.
// 셔플 선은 실제 거래 증거가 아닌 비교용 장식이며, 원본 표에는 실제 actual 행만 제공한다.
function _BtMddRandomChartContent({ data }) {
  const d = data || {};
  const curves = d.curves || [];
  const actual = d.actual || [];
  const W = 880, H = 320;
  const padL = 58, padR = 24, padT = 18, padB = 26;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // 전 곡선의 인덱스 길이는 다운샘플로 달라질 수 있어 각 곡선 자체 비율로 그린다.
  const allCum = [];
  for (const c of curves) for (const p of c) allCum.push(p.cum || 0);
  for (const p of actual) allCum.push(p.cum || 0);
  const lo = allCum.length ? Math.min(0, ...allCum) : 0;
  const hi = allCum.length ? Math.max(0, ...allCum) : 1;
  const range = (hi - lo) || 1;
  const y = (v) => padT + innerH - ((v - lo) / range) * innerH;
  const pathOf = (pts) => {
    const m = pts.length;
    if (m < 2) return "";
    return pts.map((p, i) =>
      `${i === 0 ? "M" : "L"} ${(padL + (i / (m - 1)) * innerW).toFixed(1)} ${y(p.cum || 0).toFixed(1)}`
    ).join(" ");
  };
  const rmdd = d.random_mdd_pct || { max: 0, min: 0, avg: 0 };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          MDD 랜덤 곡선 — 거래순서 무작위 30회 vs 실제
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="rgba(255,255,255,0.35)" label="셔플 누적" />
          <LegendDot color="var(--amber)" label="실제 누적" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "거래별 손익 순서를 무작위로 섞은 30개 누적곡선",
          "실제 곡선이 셔플 분포 안쪽이면 운(순서) 의존이 낮음",
          `실제 MDD ${(d.actual_mdd_pct || 0).toFixed(1)}% · 셔플 MDD 평균 ${rmdd.avg.toFixed(1)}%`,
        ]} />
        <div style={{ display: "flex", gap: 22, marginBottom: 10, flexWrap: "wrap" }}>
          <Mini label="실제 MDD" value={(d.actual_mdd_pct || 0).toFixed(1) + "%"} />
          <Mini label="셔플 MDD 최대" value={rmdd.max.toFixed(1) + "%"} color="var(--red)" />
          <Mini label="셔플 MDD 평균" value={rmdd.avg.toFixed(1) + "%"} />
          <Mini label="셔플 MDD 최소" value={rmdd.min.toFixed(1) + "%"} color="var(--teal)" />
        </div>
        <div className="chart-wrap" style={{ position: "relative" }}>
          {curves.length === 0 && <_BtChartEmpty message="거래가 누적되면 MDD 랜덤 곡선이 표시됩니다" />}
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            {/* 0 기준선 */}
            <line x1={padL} x2={W - padR} y1={y(0)} y2={y(0)} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={y(0) + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={y(hi) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(hi)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(lo) + 3} textAnchor="end" fill="var(--chart-loss)">{_gpMoney(lo)}</text>
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {curves.map((c, i) => (
              <path key={`mc${i}`} d={pathOf(c)} fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="0.6" />
            ))}
            {actual.length > 1 && <path d={pathOf(actual)} fill="none" stroke="var(--amber)" strokeWidth="2.2" />}
          </svg>
        </div>
      </div>
    </div>
  );
}

// 이미지1-(b) 일별 수익 막대 + 누적 라인. index_available=false 면 지수 미제공 안내.
function _BtDailyPnlChartContent({ data }) {
  const d = data || {};
  const series = d.series || [];
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);
  const W = 880, H = 320;
  const padL = 58, padR = 62, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = series.length;
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, Math.min(22, slot * 0.7));
  const xC = (i) => padL + slot * (i + 0.5);

  const pnls = series.map(s => s.pnl || 0);
  const pMax = Math.max(0, ...pnls), pMin = Math.min(0, ...pnls);
  const pRange = (pMax - pMin) || 1;
  const yP = (v) => padT + innerH - ((v - pMin) / pRange) * innerH;
  const cums = series.map(s => s.cum || 0);
  const cMax = Math.max(0, ...cums), cMin = Math.min(0, ...cums);
  const cRange = (cMax - cMin) || 1;
  const yC = (v) => padT + innerH - ((v - cMin) / cRange) * innerH;
  const cumPath = n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${xC(i).toFixed(1)} ${yC(s.cum || 0).toFixed(1)}`).join(" ");
  const zeroY = yP(0);

  const xTickIdx = useMemo_btc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idx = []; for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          일별 수익 · 누적
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="일이익 ₩" />
          <LegendDot color="var(--red)" label="일손실 ₩" />
          <LegendDot color="var(--amber)" label="누적 ₩" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "일별 실현손익(막대) + 그날까지 누적(라인)",
          d.index_available ? "시장지수 비교 포함" : "시장지수 비교는 per-trade CSV 에 데이터 없음 — 미표시",
          "크로스헤어로 일자별 값 확인",
        ]} />
        <div className="chart-wrap" style={{ position: "relative" }}>
          {n === 0 && <_BtChartEmpty message="거래가 누적되면 일별 수익이 표시됩니다" />}
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={yP(pMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(pMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={yP(pMin) + 3} textAnchor="end" fill="var(--chart-loss)">{_gpMoney(pMin)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yC(cMax) + 3} textAnchor="start" fill="var(--amber)">{_gpMoney(cMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yC(cMin) + 3} textAnchor="start" fill="var(--amber)">{_gpMoney(cMin)}</text>
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {series.map((s, i) => {
              const v = s.pnl || 0; const y0 = zeroY, y1 = yP(v);
              return <rect key={`d${i}`} x={xC(i) - barW / 2} y={Math.min(y0, y1)} width={barW} height={Math.max(1, Math.abs(y1 - y0))}
                           fill={v >= 0 ? "var(--teal)" : "var(--red)"} opacity={hover === i ? 1 : 0.55} />;
            })}
            {n > 1 && <path d={cumPath} fill="none" stroke="var(--amber)" strokeWidth="2" />}
            {xTickIdx.map((i) => (
              <text key={`dx${i}`} className="chart-axis-text" x={xC(i)} y={H - 10} textAnchor="middle">
                {series[i] ? _btDateLabel(series[i].date) : ""}
              </text>
            ))}
            {hover != null && series[hover] && (
              <line x1={xC(hover)} x2={xC(hover)} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>
          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16, background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 150,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>{_btDateLabel(series[hover].date)}</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>일손익</span>
                <span style={{ textAlign: "right", color: (series[hover].pnl || 0) >= 0 ? "var(--teal)" : "var(--red)" }}>{fmtMoney(series[hover].pnl)}</span>
                <span style={{ color: "var(--ink-2)" }}>누적</span>
                <span style={{ textAlign: "right", color: "var(--amber)" }}>{fmtMoney(series[hover].cum)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 이미지1-(c) 시간대별 손익 — 슬롯별 이익(위)/손실(아래) 부호 막대.
function _BtHourlyPnlChartContent({ data }) {
  const slots = (data && data.slots) || [];
  const [hover, setHover] = useState_btc(null);
  const W = 880, H = 320;
  const padL = 58, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = slots.length;
  const slotW = n > 0 ? innerW / n : innerW;
  const barW = Math.max(2, Math.min(30, slotW * 0.6));
  const xC = (i) => padL + slotW * (i + 0.5);
  const vals = [];
  for (const s of slots) { vals.push(s.profit || 0); vals.push(s.loss || 0); }
  const vMax = vals.length ? Math.max(0, ...vals) : 0;
  const vMin = vals.length ? Math.min(0, ...vals) : 0;
  const vRange = (vMax - vMin) || 1;
  const y = (v) => padT + innerH - ((v - vMin) / vRange) * innerH;
  const zeroY = y(0);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          시간대별 손익 (30분 슬롯)
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="이익 ₩" />
          <LegendDot color="var(--red)" label="손실 ₩" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={["매수시각 30분 슬롯별 이익/손실 분리 합", "위=이익 · 아래=손실", "강한 손실 시간대 회피 후보 진단"]} />
        <div className="chart-wrap" style={{ position: "relative" }}>
          {n === 0 && <_BtChartEmpty message="시간 정보가 있는 거래가 누적되면 표시됩니다" />}
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseLeave={() => setHover(null)}>
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(vMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMin) + 3} textAnchor="end" fill="var(--chart-loss)">{_gpMoney(vMin)}</text>
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {slots.map((s, i) => {
              const pTop = y(s.profit || 0), lBot = y(s.loss || 0);
              return (
                <g key={`h${i}`} onMouseEnter={() => setHover(i)}>
                  {(s.profit || 0) > 0 && <rect x={xC(i) - barW / 2} y={pTop} width={barW} height={Math.max(0.5, zeroY - pTop)} fill="var(--chart-profit)" opacity={hover === i ? 1 : 0.7} />}
                  {(s.loss || 0) < 0 && <rect x={xC(i) - barW / 2} y={zeroY} width={barW} height={Math.max(0.5, lBot - zeroY)} fill="var(--chart-loss)" opacity={hover === i ? 1 : 0.7} />}
                  <rect x={xC(i) - slotW / 2} y={padT} width={slotW} height={innerH} fill="transparent" />
                </g>
              );
            })}
            {slots.map((s, i) => (i % Math.max(1, Math.ceil(n / 12)) === 0 || i === n - 1) ? (
              <text key={`hx${i}`} className="chart-axis-text" x={xC(i)} y={H - 10} textAnchor="middle">{s.slot_label}</text>
            ) : null)}
          </svg>
          {hover != null && slots[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16, background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 150,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>{slots[hover].slot_label} 슬롯</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>이익</span><span style={{ textAlign: "right", color: "var(--teal)" }}>{fmtMoney(slots[hover].profit)}</span>
                <span style={{ color: "var(--ink-2)" }}>손실</span><span style={{ textAlign: "right", color: "var(--red)" }}>{fmtMoney(slots[hover].loss)}</span>
                <span style={{ color: "var(--ink-2)" }}>순손익</span><span style={{ textAlign: "right", color: (slots[hover].net || 0) >= 0 ? "var(--teal)" : "var(--red)" }}>{fmtMoney(slots[hover].net)}</span>
                <span style={{ color: "var(--ink-2)" }}>거래</span><span style={{ textAlign: "right" }}>{slots[hover].trades}건</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 이미지1-(d) 요일별 손익 — 요일별 이익/손실 부호 막대.
function _BtWeekdayPnlChartContent({ data }) {
  const days = (data && data.days) || [];
  const W = 560, H = 320;
  const padL = 58, padR = 24, padT = 18, padB = 28;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = days.length;
  const slotW = n > 0 ? innerW / n : innerW;
  const barW = Math.max(8, Math.min(56, slotW * 0.62));
  const xC = (i) => padL + slotW * (i + 0.5);
  const vals = [];
  for (const d of days) { vals.push(d.profit || 0); vals.push(d.loss || 0); }
  const vMax = vals.length ? Math.max(0, ...vals) : 0;
  const vMin = vals.length ? Math.min(0, ...vals) : 0;
  const vRange = (vMax - vMin) || 1;
  const y = (v) => padT + innerH - ((v - vMin) / vRange) * innerH;
  const zeroY = y(0);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          요일별 손익
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="이익 ₩" />
          <LegendDot color="var(--red)" label="손실 ₩" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={["요일별 이익/손실 분리 합(매수시각 기준)", "특정 요일 편향 진단", "막대 위 숫자 = 순손익"]} />
        <div className="chart-wrap" style={{ position: "relative" }}>
          {n === 0 && <_BtChartEmpty message="거래가 누적되면 요일별 손익이 표시됩니다" />}
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(vMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMin) + 3} textAnchor="end" fill="var(--chart-loss)">{_gpMoney(vMin)}</text>
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {days.map((d, i) => {
              const pTop = y(d.profit || 0), lBot = y(d.loss || 0);
              const netY = (d.net || 0) >= 0 ? pTop - 4 : lBot + 12;
              return (
                <g key={`w${i}`}>
                  {(d.profit || 0) > 0 && <rect x={xC(i) - barW / 2} y={pTop} width={barW} height={Math.max(0.5, zeroY - pTop)} fill="var(--chart-profit)" opacity="0.78" />}
                  {(d.loss || 0) < 0 && <rect x={xC(i) - barW / 2} y={zeroY} width={barW} height={Math.max(0.5, lBot - zeroY)} fill="var(--chart-loss)" opacity="0.78" />}
                  {d.trades > 0 && (
                    <text className="chart-axis-text" x={xC(i)} y={netY} textAnchor="middle"
                          fill={(d.net || 0) >= 0 ? "var(--teal)" : "var(--red)"} style={{ fontSize: 9.5 }}>
                      {_gpMoney(d.net)}
                    </text>
                  )}
                  <text className="chart-axis-text" x={xC(i)} y={H - 10} textAnchor="middle" style={{ fontSize: 12 }}>{d.label}</text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}

// 이미지2-(e) 보유금액 곡선 — 시점별 미청산 진입원금 합(holding_basis=entry_cost).
function _BtHoldingCurveChartContent({ data }) {
  const d = data || {};
  const series = d.series || [];
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);
  const W = 880, H = 320;
  const padL = 64, padR = 24, padT = 18, padB = 28;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = series.length;
  const x = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;
  const hMax = n ? Math.max(1, ...series.map(p => p.holding || 0)) : 1;
  const y = (v) => padT + innerH - (Math.max(0, v) / hMax) * innerH;
  const path = n < 2 ? "" : series.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.holding || 0).toFixed(1)}`).join(" ");
  const areaPath = n < 2 ? "" : `${path} L ${x(n - 1).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`;
  const peak = n ? Math.max(...series.map(p => p.holding || 0)) : 0;
  const partial = (d.covered || 0) < (d.total || 0);

  const _tLabel = (t) => { const s = String(t); return s.length >= 12 ? s.slice(4, 6) + "/" + s.slice(6, 8) + " " + s.slice(8, 10) + ":" + s.slice(10, 12) : s; };

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.round(Math.max(0, Math.min(1, (px - padL) / innerW)) * (n - 1));
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--green, #4cd6a0)" }}></span>
          보유금액 곡선
        </div>
        <Mini label="최대 보유" value={fmtMoney(peak)} />
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "진입 시 +매수금액 · 청산 시 -매수금액으로 재구성한 보유 원금 합",
          "GUI 보유금액의 정직 근사(평가손익·수수료 미반영, 진입원가 기준)",
          partial ? `매수금액 결측 거래 제외 — ${d.covered}/${d.total} 거래 반영` : `${d.total} 거래 전부 반영`,
        ]} />
        <div className="chart-wrap" style={{ position: "relative" }}>
          {n === 0 && <_BtChartEmpty message="매수금액 정보가 있는 거래가 누적되면 보유금액 곡선이 표시됩니다" />}
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            <text className="chart-axis-text" x={padL - 8} y={y(hMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(hMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(0) + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {n > 1 && <path d={areaPath} fill="rgba(76,214,160,0.14)" stroke="none" />}
            {n > 1 && <path d={path} fill="none" stroke="var(--chart-profit)" strokeWidth="2" />}
            {[0, Math.floor(n / 2), n - 1].filter((v, idx, a) => n > 0 && a.indexOf(v) === idx).map((i) => (
              <text key={`hcx${i}`} className="chart-axis-text" x={x(i)} y={H - 9} textAnchor="middle">
                {series[i] ? _tLabel(series[i].time) : ""}
              </text>
            ))}
            {hover != null && series[hover] && (
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>
          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16, background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 160,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>{_tLabel(series[hover].time)}</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>보유금액</span>
                <span style={{ textAlign: "right", color: "var(--teal)" }}>{fmtMoney(series[hover].holding)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 이미지2-(f) 거래별 손익 + 누적 + 롤링 평균(창 20/60/120/240/480).
function _BtTradeRollingChartContent({ data }) {
  const d = data || {};
  const series = d.series || [];
  const windows = d.windows || [20, 60, 120, 240, 480];
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);
  const W = 880, H = 320;
  const padL = 60, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = series.length;
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, Math.min(14, slot * 0.6));
  const xC = (i) => padL + slot * (i + 0.5);
  const xL = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;

  // 막대 스케일(거래별 손익) · 라인 스케일(누적·롤링) 공용 — 모두 같은 y축(원).
  const allVals = [];
  for (const s of series) {
    allVals.push(s.pnl || 0); allVals.push(s.cum || 0);
    for (const w of windows) { const v = s.roll && s.roll[String(w)]; if (v != null) allVals.push(v); }
  }
  const vMax = allVals.length ? Math.max(0, ...allVals) : 0;
  const vMin = allVals.length ? Math.min(0, ...allVals) : 0;
  const vRange = (vMax - vMin) || 1;
  const y = (v) => padT + innerH - ((v - vMin) / vRange) * innerH;
  const zeroY = y(0);

  const ROLL_COLORS = { "20": "var(--red)", "60": "var(--teal)", "120": "var(--blue)", "240": "var(--ink-3)", "480": "var(--ink-1)" };
  const cumPath = n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${xL(i).toFixed(1)} ${y(s.cum || 0).toFixed(1)}`).join(" ");
  const rollPath = (w) => {
    const key = String(w);
    let dStr = ""; let started = false;
    series.forEach((s, i) => {
      const v = s.roll && s.roll[key];
      if (v == null) { started = false; return; }
      dStr += `${started ? "L" : "M"} ${xL(i).toFixed(1)} ${y(v).toFixed(1)} `;
      started = true;
    });
    return dStr.trim();
  };

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          거래별 손익 · 롤링 평균
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <LegendDot color="var(--amber)" label="누적 ₩" />
          {windows.map(w => <LegendDot key={w} color={ROLL_COLORS[String(w)] || "var(--ink-2)"} label={`MA${w}`} />)}
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "거래별 실현손익(막대) + 누적손익(주황) + 누적손익 이동평균(창 20/60/120/240/480)",
          "롤링 라인이 우상향이면 누적 성장 가속",
          "창보다 거래가 적으면 해당 롤링선은 생략",
        ]} />
        <div className="chart-wrap" style={{ position: "relative" }}>
          {n === 0 && <_BtChartEmpty message="거래가 누적되면 거래별 손익·롤링이 표시됩니다" />}
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_gpMoney(vMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(vMin) + 3} textAnchor="end" fill="var(--chart-loss)">{_gpMoney(vMin)}</text>
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {series.map((s, i) => {
              const v = s.pnl || 0; const y0 = zeroY, y1 = y(v);
              return <rect key={`tr${i}`} x={xC(i) - barW / 2} y={Math.min(y0, y1)} width={barW} height={Math.max(0.5, Math.abs(y1 - y0))}
                           fill={v >= 0 ? "var(--teal)" : "var(--red)"} opacity={hover === i ? 0.95 : 0.45} />;
            })}
            {windows.map(w => {
              const p = rollPath(w);
              return p ? <path key={`rp${w}`} d={p} fill="none" stroke={ROLL_COLORS[String(w)] || "var(--ink-2)"} strokeWidth="1.3" opacity="0.9" /> : null;
            })}
            {n > 1 && <path d={cumPath} fill="none" stroke="var(--amber)" strokeWidth="2" />}
            {hover != null && series[hover] && (
              <line x1={xC(hover)} x2={xC(hover)} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>
          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16, background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 170,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>거래 #{series[hover].index + 1}</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>손익</span>
                <span style={{ textAlign: "right", color: (series[hover].pnl || 0) >= 0 ? "var(--teal)" : "var(--red)" }}>{fmtMoney(series[hover].pnl)}</span>
                <span style={{ color: "var(--ink-2)" }}>누적</span>
                <span style={{ textAlign: "right", color: "var(--amber)" }}>{fmtMoney(series[hover].cum)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// GUI 패리티 진단 — 원본 GUI 이미지의 근사이며, 결과 증거를 대체하지 않는다.
function BtGuiParitySection({ guiParity }) {
  const gp = guiParity || {};
  return (
    <>
      <BtMddRandomChart data={gp.mdd_random} />
      <BtHourlyPnlChart data={gp.hourly} />
      <BtWeekdayPnlChart data={gp.weekday} />
      <BtHoldingCurveChart data={gp.holding} />
    </>
  );
}

const BtMddRandomChart = _btParityWithEvidence(_BtMddRandomChartContent, ({ data }) => ({
  title: "MDD 랜덤 곡선", unit: "누적 손익 (원)", period: "거래 순서",
  sampleCount: Array.isArray(data && data.actual) ? data.actual.length : 0,
  freshness: "백테스트 분석 응답", threshold: "실제 대 셔플 MDD", source: "analysis.gui_parity.mdd_random.actual",
  rows: data && data.actual, columns: ["index", "cum"], rowKey: "index",
}));
const BtDailyPnlChart = _btParityWithEvidence(_BtDailyPnlChartContent, ({ data }) => ({
  title: "일별 수익", unit: "일별·누적 손익 (원)", period: "일자별",
  sampleCount: Array.isArray(data && data.series) ? data.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.gui_parity.daily.series",
  rows: data && data.series, columns: ["date", "pnl", "cum"], rowKey: "date",
}));
const BtHourlyPnlChart = _btParityWithEvidence(_BtHourlyPnlChartContent, ({ data }) => ({
  title: "시간대별 손익", unit: "손익 (원)", period: "30분 매수 시각 슬롯",
  sampleCount: Array.isArray(data && data.slots) ? data.slots.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.gui_parity.hourly.slots",
  rows: data && data.slots, columns: ["slot_label", "profit", "loss", "net", "trades"], rowKey: "slot_label",
}));
const BtWeekdayPnlChart = _btParityWithEvidence(_BtWeekdayPnlChartContent, ({ data }) => ({
  title: "요일별 손익", unit: "손익 (원)", period: "매수 요일별",
  sampleCount: Array.isArray(data && data.days) ? data.days.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.gui_parity.weekday.days",
  rows: data && data.days, columns: ["weekday", "profit", "loss", "net", "trades"], rowKey: "weekday",
}));
const BtHoldingCurveChart = _btParityWithEvidence(_BtHoldingCurveChartContent, ({ data }) => ({
  title: "보유금액 곡선", unit: "미청산 진입원금 (원)", period: "거래 시점별",
  sampleCount: Array.isArray(data && data.series) ? data.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "진입원가 기준", source: "analysis.gui_parity.holding.series",
  rows: data && data.series, columns: ["time", "holding"], rowKey: "time",
}));
const BtTradeRollingChart = _btParityWithEvidence(_BtTradeRollingChartContent, ({ data }) => ({
  title: "거래별 손익 · 누적 · 롤링", unit: "손익 (원)", period: "거래 순서",
  sampleCount: Array.isArray(data && data.series) ? data.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.gui_parity.trade_rolling.series",
  rows: data && data.series, columns: ["index", "pnl", "cum"], rowKey: "index",
}));

export {
  BtMddRandomChart, BtDailyPnlChart, BtHourlyPnlChart, BtWeekdayPnlChart,
  BtHoldingCurveChart, BtTradeRollingChart, BtGuiParitySection,
};
