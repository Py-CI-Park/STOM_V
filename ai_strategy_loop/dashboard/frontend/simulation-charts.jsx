/* Chart simulation candles — PR3 + Upgrade Stage3 (차트 엔진 고도화).
   기본 엔진: TradingView lightweight-charts(standalone, vendor-lightweight-charts.js).
   window.LightweightCharts 전역이 있으면 캔들+거래량+마커(매수▲/매도▼)를 그 엔진으로
   그리고(줌/팬/크로스헤어 내장), 없으면(오프라인 등) 기존 순수 SVG 폴백을 쓴다 —
   SVG 폴백도 휠 줌·드래그 팬·크로스헤어를 직접 구현해 두 경로 모두 동작한다.

   체결강도 히트 스트립(SimHeatStrip)은 두 경로 공통으로 차트 하단에 시간축 정렬 색 밴드.
   backtest-charts.jsx 의 디자인 언어(chart-wrap·chart-axis-text·panel)를 따른다.

   window 전역으로 공유: index.html 에서 simulation.jsx 보다 먼저 로드된다.
   소비 컴포넌트(export):
     - SimCandleChart : 엔진 자동선택(LWC↔SVG) 캔들+거래량+신호 마커 래퍼.
     - SimHeatStrip   : 체결강도 히트 스트립(시간축 색 밴드).
     - SimSignalLog   : 신호(매수/매도) 시각·가격·수익률 목록. */
const {
  useState: useState_simc, useRef: useRef_simc, useMemo: useMemo_simc,
  useEffect: useEffect_simc,
} = React;

// 최근 N 캔들 윈도우(SVG 폴백 렌더 부하 상한). LWC 는 전체를 주고 내장 팬/줌에 맡긴다.
const _SIM_WINDOW = 400;
// LWC 에 넘기는 누적 캔들 상한(과대 입력 방지 — 일일 데이터는 통상 이 안).
const _SIM_LWC_MAX = 5000;

// 보조지표 기본 토글 — 차트 위 라인 오버레이로 렌더(LWC addLineSeries / SVG path 동일).
//   기존: ma(MA5/20/60), vwap(VWAP), boll(볼린저 20,2 상/중/하단).
//   Phase7 신규(CROSS-FILE CONTRACT — Track B 와 동일 키 집합):
//     · 클라이언트 계산(버퍼 위 순수 함수, 와이어 무변경): ema(EMA12/26), rsi(RSI14),
//       macd(MACD 12/26/9), volma(거래량 MA 5/20), strma(체결강도 MA 5).
//     · 서버 공급(vwap_up/vwap_low 프레임 필드): vwapband(VWAP 밴드 ±1σ).
//     · 뷰 토글(별도 데이터 없음 — 그리기만): strength(체결강도 그래프), imbalance(호가 불균형),
//       orderflow(net-delta strip).
//   heavy 한 것들은 기본 OFF. strength 는 SVG 가 이미 그리므로 기본 ON.
const _SIM_DEFAULT_INDICATORS = {
  ma: true, vwap: true, boll: false,
  ema: false, rsi: false, macd: false, volma: false, strma: false,
  vwapband: false, strength: true, imbalance: false, orderflow: false,
};

// 지표별 색/스타일(LWC·SVG 공통 팔레트). dashed 는 SVG strokeDasharray·LWC LineStyle 매핑.
const _SIM_IND_STYLE = {
  ma5:    { color: "#4cd6b3", width: 1, dashed: true,  label: "MA5" },
  ma20:   { color: "#f0b35a", width: 1.1, dashed: false, label: "MA20" },
  ma60:   { color: "#7c6cf0", width: 1.1, dashed: false, label: "MA60" },
  vwap:   { color: "#ffd24c", width: 1.4, dashed: false, label: "VWAP" },
  bb_up:  { color: "#5a93c8", width: 1, dashed: true,  label: "BB+" },
  bb_mid: { color: "#5a93c8", width: 0.9, dashed: true, label: "BB" },
  bb_low: { color: "#5a93c8", width: 1, dashed: true,  label: "BB-" },
  // Phase7 — 클라이언트 계산 라인(EMA/VWAP밴드).
  ema12:    { color: "#6fd6ff", width: 1, dashed: false, label: "EMA12" },
  ema26:    { color: "#b07cf0", width: 1, dashed: false, label: "EMA26" },
  vwap_up:  { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP+" },
  vwap_low: { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP-" },
};

/* ─────────────── Phase7 클라이언트 지표 헬퍼 (CROSS-FILE CONTRACT) ───────────────
   bar 버퍼 위 순수 함수 — 동일 입력 ⇒ 동일 출력(엔진 간 발산 없음). 입력은 모두
   이미 프레임에 실려 오는 값(OHLCV + strength)이라 와이어 변경/서버 헬퍼가 필요 없다.
   각 헬퍼는 bars 와 같은 길이의 배열을 돌려준다(윈도우 미충족 구간은 null → 끊어 그림). */

// 단순이동평균(period) over selector(b)→number. 윈도우 미충족 구간 null.
function _simSma(bars, period, sel) {
  const out = new Array(bars.length).fill(null);
  let sum = 0, cnt = 0;
  const q = [];
  for (let i = 0; i < bars.length; i++) {
    const v = sel(bars[i]);
    const x = (v != null && isFinite(v)) ? v : null;
    q.push(x);
    if (x != null) { sum += x; cnt++; }
    if (q.length > period) {
      const drop = q.shift();
      if (drop != null) { sum -= drop; cnt--; }
    }
    out[i] = (q.length >= period && cnt === period) ? sum / period : null;
  }
  return out;
}

// 지수이동평균(period) over close. 첫 유효 close 를 seed, 이후 EMA 점화식.
function _simEma(bars, period) {
  const out = new Array(bars.length).fill(null);
  const k = 2 / (period + 1);
  let ema = null;
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i].c;
    if (c == null || !isFinite(c)) { out[i] = ema; continue; }
    ema = (ema == null) ? c : c * k + ema * (1 - k);
    out[i] = ema;
  }
  return out;
}

// RSI(Wilder, 기본 14) over close. 윈도우 미충족 구간 null.
function _simRsi(bars, period) {
  const p = period || 14;
  const out = new Array(bars.length).fill(null);
  let avgGain = null, avgLoss = null, prev = null;
  let seedG = 0, seedL = 0, seedN = 0;
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i].c;
    if (c == null || !isFinite(c)) { out[i] = null; continue; }
    if (prev == null) { prev = c; out[i] = null; continue; }
    const ch = c - prev; prev = c;
    const gain = ch > 0 ? ch : 0, loss = ch < 0 ? -ch : 0;
    if (avgGain == null) {
      seedG += gain; seedL += loss; seedN++;
      if (seedN === p) { avgGain = seedG / p; avgLoss = seedL / p; }
      else { out[i] = null; continue; }
    } else {
      avgGain = (avgGain * (p - 1) + gain) / p;
      avgLoss = (avgLoss * (p - 1) + loss) / p;
    }
    const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + rs);
  }
  return out;
}

// MACD(12/26/9) over close → {macd[], signal[], hist[]} (각 bars 길이, null 패딩).
function _simMacd(bars) {
  const fast = _simEma(bars, 12);
  const slow = _simEma(bars, 26);
  const macd = bars.map((b, i) =>
    (fast[i] != null && slow[i] != null) ? fast[i] - slow[i] : null);
  // signal = MACD 의 9 EMA(유효 구간만 점화).
  const signal = new Array(bars.length).fill(null);
  const k = 2 / (9 + 1);
  let s = null;
  for (let i = 0; i < bars.length; i++) {
    const m = macd[i];
    if (m == null) { signal[i] = s; continue; }
    s = (s == null) ? m : m * k + s * (1 - k);
    signal[i] = s;
  }
  const hist = bars.map((b, i) =>
    (macd[i] != null && signal[i] != null) ? macd[i] - signal[i] : null);
  return { macd, signal, hist };
}

// 거래량 MA — periods(예 [5,20]) 각각의 SMA over b.vol → { ["vol_ma"+p]: number[] }.
function _simVolMa(bars, periods) {
  const ps = periods || [5, 20];
  const out = {};
  ps.forEach(p => { out["vol_ma" + p] = _simSma(bars, p, b => b.vol); });
  return out;
}

// 체결강도 MA — SMA(period=5) over b.strength. volMA 와 동일 계열의 클라이언트 계산.
function _simStrengthMa(bars, period) {
  return _simSma(bars, period || 5, b => b.strength);
}

// HHMMSS → HH:MM:SS · 가격 축약(원). P3 de-dup: 빌드 번들(stom-ui.js, format.ts)이
//   window._hmsTimeLabel/_priceTick 로 단일 출처 제공(ESM 모듈이라 babel/app.js 보다 먼저 로드).
//   babel 스코프 별칭만 둬서 기존 호출(_simTimeLabel/_simPriceTick)이 그대로 해소된다.
const _simTimeLabel = window._hmsTimeLabel;
const _simPriceTick = window._priceTick;

// HHMMSS(int) → 자정 기준 초(LWC time 축의 단조 증가 UTCTimestamp 로 사용).
function _hmsToSec(hms) {
  const s = String(hms).padStart(6, "0");
  return parseInt(s.slice(0, 2), 10) * 3600 + parseInt(s.slice(2, 4), 10) * 60 + parseInt(s.slice(4, 6), 10);
}

// 체결강도(0~200, 100=균형) → 색(낮음 파랑 → 100 중립 → 높음 빨강). 히트 스트립·밴드 공용.
function _strengthColor(v, alpha) {
  const a = alpha == null ? 1 : alpha;
  const s = Math.max(0, Math.min(200, v == null ? 100 : v));
  // 0→파랑(56,140,255), 100→회청(120,130,150), 200→빨강(240,80,80).
  let r, g, b;
  if (s <= 100) {
    const t = s / 100;
    r = Math.round(56 + (120 - 56) * t);
    g = Math.round(140 + (130 - 140) * t);
    b = Math.round(255 + (150 - 255) * t);
  } else {
    const t = (s - 100) / 100;
    r = Math.round(120 + (240 - 120) * t);
    g = Math.round(130 + (80 - 130) * t);
    b = Math.round(150 + (80 - 150) * t);
  }
  return `rgba(${r},${g},${b},${a})`;
}

function _lwcAvailable() {
  return typeof window !== "undefined" && window.LightweightCharts &&
    typeof window.LightweightCharts.createChart === "function";
}

/* ─────────────────────── 비주얼 추가 (Track C) ───────────────────────
   ① SimChangeGauge : 종목 등락율 반원 게이지(상승 빨강/하락 파랑, ±12% 포화).
   ② SimSessionRing : 세션 진행 링(09:00~15:30 대비 현재 시각 호 채움).
   ③ 신호 플래시    : 신호 도달 순간 차트 테두리 1회 플래시(SimChartShell 적용). */
const _SESSION_START_SEC = 9 * 3600;            // 09:00:00.
const _SESSION_END_SEC = 15 * 3600 + 30 * 60;   // 15:30:00.

// HHMMSS(int) 또는 None → 세션 진행률 0..1(09:00=0, 15:30=1, 범위 밖 클램프).
function _sessionProgress(hms) {
  if (hms == null) return 0;
  const sec = _hmsToSec(hms);
  const span = _SESSION_END_SEC - _SESSION_START_SEC;
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (sec - _SESSION_START_SEC) / span));
}

// 등락율(%) → 게이지 색. 상승 빨강(--red), 하락 파랑, 0=중립 회색. 농도는 |등락|/12.
function _changeColor(pct) {
  const v = Number(pct) || 0;
  const mag = Math.min(1, Math.abs(v) / 12);
  const a = (0.35 + mag * 0.6).toFixed(3);
  if (v > 0) return `rgba(255,93,108,${a})`;
  if (v < 0) return `rgba(56,140,255,${a})`;
  return "rgba(150,158,170,0.5)";
}

// 반원 게이지 — 등락율을 -12%(좌)~+12%(우) 반원 바늘로 표시. SVG 순수(라이브러리 없음).
function SimChangeGauge({ changePct, size }) {
  const S = size || 56;
  const v = Number(changePct) || 0;
  const clamped = Math.max(-12, Math.min(12, v));
  // -12%→180°(좌), 0%→90°(상), +12%→0°(우). 반원(180°→0°).
  const angle = 180 - ((clamped + 12) / 24) * 180;
  const rad = (angle * Math.PI) / 180;
  const r = S / 2 - 4;
  const cx = S / 2, cy = S / 2;
  const nx = cx + r * Math.cos(rad);
  const ny = cy - r * Math.sin(rad);
  const color = _changeColor(v);
  return (
    <svg width={S} height={S / 2 + 6} viewBox={`0 0 ${S} ${S / 2 + 6}`} aria-hidden="true">
      {/* 반원 트랙 */}
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="var(--line-2)" strokeWidth="3" strokeLinecap="round" />
      {/* 중앙 0% 틱 */}
      <line x1={cx} y1={cy - r} x2={cx} y2={cy - r + 4}
            stroke="var(--ink-3)" strokeWidth="1" />
      {/* 바늘 */}
      <line x1={cx} y1={cy} x2={nx.toFixed(2)} y2={ny.toFixed(2)}
            stroke={color} strokeWidth="2.4" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="2.6" fill={color} />
      {/* 등락 라벨 */}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize="10" className="mono"
            fill={color}>
        {v > 0 ? "+" : ""}{v.toFixed(2)}%
      </text>
    </svg>
  );
}

// 세션 진행 링 — 09:00~15:30 대비 현재 시각(curT) 호 채움 + 중앙 HH:MM.
function SimSessionRing({ curT, size }) {
  const S = size || 52;
  const r = S / 2 - 5;
  const cx = S / 2, cy = S / 2;
  const circ = 2 * Math.PI * r;
  const prog = _sessionProgress(curT);
  const dash = (circ * prog).toFixed(2);
  const label = curT != null ? _simTimeLabel(curT).slice(0, 5) : "--:--";
  return (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} aria-hidden="true">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--line-2)" strokeWidth="3" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--teal)" strokeWidth="3"
              strokeLinecap="round" strokeDasharray={`${dash} ${(circ - dash).toFixed(2)}`}
              transform={`rotate(-90 ${cx} ${cy})`} />
      <text x={cx} y={cy + 3.2} textAnchor="middle" fontSize="10" className="mono"
            fill="var(--ink-1)">{label}</text>
    </svg>
  );
}

/* ───────────────────────── 히트 스트립 (Part C) ─────────────────────────
   차트 하단 체결강도 색 밴드(시간축 정렬). 리플레이 진행에 따라 view 가 채워진다. */
function SimHeatStrip({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);
  const n = view.length;
  if (n === 0) return null;
  const H = compact ? 14 : 18;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--violet)", flexShrink: 0, width: 48 }}>
        체결강도
      </span>
      <div style={{ display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
        {view.map((b, i) => (
          <div key={i} title={_simTimeLabel(b.t) + " · " + (b.strength || 0).toFixed(0)}
               style={{ flex: 1, background: _strengthColor(b.strength, 0.85) }} />
        ))}
      </div>
    </div>
  );
}

/* ───────────────────── 호가 잔량 흐름 (Part C) ─────────────────────
   매수총잔량(위)·매도총잔량(아래) 미러형 영역 차트(시간축 동기). 캔들 아래 접이식 패널.
   데이터(buy_rest/sell_rest)가 전혀 없으면(컬럼 부재 등) 패널 자동 숨김(무예외). */
function SimRestFlow({ bars, compact }) {
  const [open, setOpen] = useState_simc(false);

  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  // 유효 잔량 데이터 유무 — 하나라도 숫자면 패널 노출. 전부 None/무값이면 숨김.
  const hasData = useMemo_simc(() =>
    view.some(b => (b.buy_rest != null && isFinite(b.buy_rest)) ||
                   (b.sell_rest != null && isFinite(b.sell_rest))),
    [view]);

  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const half = compact ? 28 : 38;          // 위/아래 각 영역 높이.
  const H = half * 2 + 18;                  // +중앙 라벨/축 여백.
  const padL = 56, padR = 16;
  const innerW = W - padL - padR;
  const mid = half + 4;                     // 중앙선 y.

  const buyVals = view.map(b => (b.buy_rest != null && isFinite(b.buy_rest)) ? b.buy_rest : 0);
  const sellVals = view.map(b => (b.sell_rest != null && isFinite(b.sell_rest)) ? b.sell_rest : 0);
  const maxRest = Math.max(1, ...buyVals, ...sellVals);

  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yBuy = (v) => mid - (Math.min(v, maxRest) / maxRest) * half;     // 위로.
  const ySell = (v) => mid + (Math.min(v, maxRest) / maxRest) * half;    // 아래로.

  const areaPath = (vals, yFn) => {
    if (n === 0) return "";
    let d = `M ${xAt(0).toFixed(1)} ${mid.toFixed(1)} `;
    for (let i = 0; i < n; i++) d += `L ${xAt(i).toFixed(1)} ${yFn(vals[i]).toFixed(1)} `;
    d += `L ${xAt(n - 1).toFixed(1)} ${mid.toFixed(1)} Z`;
    return d;
  };

  const last = view.length ? view[view.length - 1] : null;
  const lastBuy = last && last.buy_rest != null ? last.buy_rest : null;
  const lastSell = last && last.sell_rest != null ? last.sell_rest : null;

  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "4px 8px",
          background: "transparent", border: "1px solid var(--line-1)", borderRadius: 5,
          color: "var(--ink-2)", cursor: "pointer", fontSize: 10,
        }}>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▼" : "▶"}</span>
        호가 잔량 흐름
        {lastBuy != null && (
          <span style={{ marginLeft: "auto", color: "var(--teal)" }}>
            매수 {_simPriceTick(lastBuy)}
          </span>
        )}
        {lastSell != null && (
          <span style={{ color: "var(--red)" }}>매도 {_simPriceTick(lastSell)}</span>
        )}
      </button>
      {open && (
        <div style={{ marginTop: 4 }}>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
            {/* 중앙 기준선 */}
            <line x1={padL} x2={W - padR} y1={mid} y2={mid}
                  stroke="var(--line-2)" strokeWidth="1" />
            {/* 매수잔량(위, teal 영역) */}
            {n > 0 && <path d={areaPath(buyVals, yBuy)} fill="rgba(76,214,179,0.28)"
                            stroke="var(--teal)" strokeWidth="1" />}
            {/* 매도잔량(아래, red 영역) */}
            {n > 0 && <path d={areaPath(sellVals, ySell)} fill="rgba(255,93,108,0.26)"
                            stroke="var(--red)" strokeWidth="1" />}
            <text className="chart-axis-text" x={padL - 8} y={mid - half + 8} textAnchor="end" fill="var(--teal)">매수</text>
            <text className="chart-axis-text" x={padL - 8} y={mid + half} textAnchor="end" fill="var(--red)">매도</text>
            <text className="chart-axis-text" x={padL - 8} y={mid + 3} textAnchor="end" fill="var(--ink-3)">
              {_simPriceTick(maxRest)}
            </text>
          </svg>
        </div>
      )}
    </div>
  );
}

// bar t → 자정 기준 단조 증가 초 매핑(LWC setData 와 동일 규칙: 동일/역순 슬롯 +1 보정).
function _monotonicSecs(bars) {
  const out = [];
  let lastSec = -1;
  for (let i = 0; i < bars.length; i++) {
    let sec = _hmsToSec(bars[i].t);
    if (sec <= lastSec) sec = lastSec + 1;
    lastSec = sec;
    out.push(sec);
  }
  return out;
}

// 지표 라인 데이터 추출 — bar[key] 가 null 인 구간은 건너뛴다(끊어 그림 → LWC whitespace).
function _lineData(bars, secs, key) {
  const out = [];
  for (let i = 0; i < bars.length; i++) {
    const v = bars[i][key];
    if (v == null || !isFinite(v)) continue;
    out.push({ time: secs[i], value: v });
  }
  return out;
}

/* ─────────────── lightweight-charts 엔진 경로 (기본) ─────────────── */
/* ⚠ ASYMMETRIC PARITY (FINAL) — LWC stacking SPIKE 결론(Phase7 §7.3 STEP 0):
   lightweight-charts v4.2 에는 addPane API 가 없다. 서브-시리즈는 단일 캔들 페인 위에
   distinct priceScaleId + scaleMargins 로 쌓는 "오버레이 프라이스 스케일"뿐이다.
   compact H=240 에서 vol(scaleMargins top:0.82 → 18%) + strength + imbalance 를 3개
   오버레이 밴드로 쌓으면 각 밴드가 화면을 또 갉아먹어 캔들 본체 밴드가 가독 하한
   55% 아래(추정 ~45% 이하)로 떨어진다(vol 18% + strength~13% + imbalance~13% ≈ 44%
   소비 → 캔들 ≈ 56% 이지만 축 라벨/여백 차감 시 55% 하회). 따라서 비대칭 패리티를
   FINAL 로 못박는다: LWC 는 strength 오버레이 한 개만 싣는다(그 전문 강점은 줌/크로스헤어/
   네이티브 last-price 애니메이션이지 커스텀 서브패인이 아니다). 호가 불균형·net-delta 는
   live+svg 만 싣는다(SimCandleChartSVG·SimLiveChart). */
function SimCandleChartLWC({ bars, signals, curT, code, name, compact, indicators }) {
  const wrapRef = useRef_simc(null);
  const chartRef = useRef_simc(null);
  const candleRef = useRef_simc(null);
  const volRef = useRef_simc(null);
  const roRef = useRef_simc(null);
  const lineRef = useRef_simc({});   // key → LWC line series.
  const strRef = useRef_simc(null);  // 체결강도 오버레이 라인 시리즈(단 하나의 서브-시리즈).
  const strMaRef = useRef_simc(null); // 체결강도 MA 오버레이(strma 토글 시).
  const ind = indicators || _SIM_DEFAULT_INDICATORS;

  const H = compact ? 240 : 360;

  // 차트 1회 생성(언마운트 시 정리). ResizeObserver 로 폭 추종.
  useEffect_simc(() => {
    const LWC = window.LightweightCharts;
    const el = wrapRef.current;
    if (!LWC || !el) return;
    const chart = LWC.createChart(el, {
      width: el.clientWidth || 600,
      height: H,
      layout: { background: { color: "transparent" }, textColor: "rgba(200,205,215,0.7)", fontFamily: "var(--mono)" },
      grid: { vertLines: { color: "rgba(255,255,255,0.04)" }, horzLines: { color: "rgba(255,255,255,0.05)" } },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      timeScale: {
        borderColor: "rgba(255,255,255,0.1)",
        // 봉 수가 적은 리플레이 초반의 우측 압착/과확대 방지 — 고정 기본 간격.
        rightOffset: 4, barSpacing: 7, minBarSpacing: 2,
        timeVisible: true, secondsVisible: !compact,
        tickMarkFormatter: (t) => {
          const sec = ((t % 86400) + 86400) % 86400;
          const hh = String(Math.floor(sec / 3600)).padStart(2, "0");
          const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
          return hh + ":" + mm;
        },
      },
      crosshair: { mode: LWC.CrosshairMode ? LWC.CrosshairMode.Normal : 0 },
      handleScroll: true, handleScale: true,
    });
    const candle = chart.addCandlestickSeries({
      upColor: "#4cd6b3", downColor: "#ff5d6c",
      borderUpColor: "#4cd6b3", borderDownColor: "#ff5d6c",
      wickUpColor: "#4cd6b3", wickDownColor: "#ff5d6c",
    });
    const vol = chart.addHistogramSeries({
      priceFormat: { type: "volume" }, priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    chartRef.current = chart;
    candleRef.current = candle;
    volRef.current = vol;

    const ro = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(() => {
          if (chartRef.current && el.clientWidth) chartRef.current.applyOptions({ width: el.clientWidth });
        })
      : null;
    if (ro) { ro.observe(el); roRef.current = ro; }

    return () => {
      if (roRef.current) { try { roRef.current.disconnect(); } catch (e) {} roRef.current = null; }
      try { chart.remove(); } catch (e) {}
      chartRef.current = null; candleRef.current = null; volRef.current = null;
      lineRef.current = {};   // chart.remove() 가 모든 series 파괴 — 참조만 비운다.
      strRef.current = null; strMaRef.current = null;
    };
  }, [H, compact]);

  // bars 변경 시 데이터 갱신(시각=자정 기준 초로 단조 증가 보장, 중복 t 는 마지막 우선).
  useEffect_simc(() => {
    const candle = candleRef.current, vol = volRef.current;
    if (!candle || !vol) return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const cData = [];
    const vData = [];
    let lastSec = -1;
    for (let i = 0; i < src.length; i++) {
      const b = src[i];
      let sec = _hmsToSec(b.t);
      if (sec <= lastSec) sec = lastSec + 1;  // 동일/역순 슬롯 방지(LWC 단조 증가 요구).
      lastSec = sec;
      const up = (b.c || 0) >= (b.o || 0);
      cData.push({ time: sec, open: b.o || b.c || 0, high: b.h || b.c || 0, low: b.l || b.c || 0, close: b.c || 0 });
      vData.push({ time: sec, value: b.vol || 0, color: up ? "rgba(76,214,179,0.4)" : "rgba(255,93,108,0.4)" });
    }
    try { candle.setData(cData); vol.setData(vData); } catch (e) {}
  }, [bars]);

  // 보조지표 라인 오버레이(MA5/20/60·VWAP·볼린저) — 토글에 따라 생성/갱신/제거.
  useEffect_simc(() => {
    const chart = chartRef.current;
    if (!chart || typeof chart.addLineSeries !== "function") return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const secs = _monotonicSecs(src);
    const lines = lineRef.current;

    // 토글에 따라 켜질 지표 키 집합. 서버 라인(ma/vwap/boll/vwapband)은 bar 필드,
    //   클라이언트 라인(ema)은 _simEma 로 계산해 src 위에 매핑한다.
    const active = {};
    if (ind.ma) { active.ma5 = 1; active.ma20 = 1; active.ma60 = 1; }
    if (ind.vwap) active.vwap = 1;
    if (ind.boll) { active.bb_up = 1; active.bb_mid = 1; active.bb_low = 1; }
    if (ind.vwapband) { active.vwap_up = 1; active.vwap_low = 1; }   // 서버 공급 필드.
    if (ind.ema) { active.ema12 = 1; active.ema26 = 1; }             // 클라이언트 계산.

    // 클라이언트 계산 EMA(12/26) — bar 필드가 아니므로 별도 배열로 준비.
    const emaData = {};
    if (ind.ema) {
      const e12 = _simEma(src, 12), e26 = _simEma(src, 26);
      emaData.ema12 = []; emaData.ema26 = [];
      for (let i = 0; i < src.length; i++) {
        if (e12[i] != null && isFinite(e12[i])) emaData.ema12.push({ time: secs[i], value: e12[i] });
        if (e26[i] != null && isFinite(e26[i])) emaData.ema26.push({ time: secs[i], value: e26[i] });
      }
    }

    // 비활성 라인 제거.
    Object.keys(lines).forEach(key => {
      if (!active[key]) {
        try { chart.removeSeries(lines[key]); } catch (e) {}
        delete lines[key];
      }
    });
    // 활성 라인 생성·갱신.
    Object.keys(active).forEach(key => {
      const st = _SIM_IND_STYLE[key];
      if (!st) return;
      if (!lines[key]) {
        try {
          lines[key] = chart.addLineSeries({
            color: st.color, lineWidth: st.width,
            lineStyle: st.dashed && window.LightweightCharts && window.LightweightCharts.LineStyle
              ? window.LightweightCharts.LineStyle.Dashed : 0,
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { return; }
      }
      // ema12/ema26 는 클라이언트 계산 배열, 그 외는 bar 필드.
      const data = (key === "ema12" || key === "ema26") ? (emaData[key] || []) : _lineData(src, secs, key);
      try { lines[key].setData(data); } catch (e) {}
    });
  }, [bars, ind.ma, ind.vwap, ind.boll, ind.ema, ind.vwapband]);

  // 체결강도 오버레이 — LWC 가 싣는 단 하나의 서브-시리즈(비대칭 패리티). 자체 priceScaleId +
  //   scaleMargins 로 캔들 페인 하단에 얇은 밴드를 카빙(0~200 스케일). strma 토글 시 MA5 도 함께.
  useEffect_simc(() => {
    const chart = chartRef.current;
    if (!chart || typeof chart.addLineSeries !== "function") return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const secs = _monotonicSecs(src);

    const ensureScale = () => {
      try { chart.priceScale("strength").applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } }); } catch (e) {}
    };
    // 체결강도 라인.
    if (ind.strength) {
      if (!strRef.current) {
        try {
          strRef.current = chart.addLineSeries({
            color: "#7c6cf0", lineWidth: 1.2, priceScaleId: "strength",
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { strRef.current = null; }
        ensureScale();
      }
      if (strRef.current) {
        const data = [];
        for (let i = 0; i < src.length; i++) {
          const s = src[i].strength;
          if (s != null && isFinite(s)) data.push({ time: secs[i], value: s });
        }
        try { strRef.current.setData(data); } catch (e) {}
      }
    } else if (strRef.current) {
      try { chart.removeSeries(strRef.current); } catch (e) {}
      strRef.current = null;
    }
    // 체결강도 MA5(클라이언트 _simStrengthMa) — strength+strma 둘 다 켜질 때만.
    if (ind.strength && ind.strma) {
      if (!strMaRef.current) {
        try {
          strMaRef.current = chart.addLineSeries({
            color: "#f0b35a", lineWidth: 1, priceScaleId: "strength",
            lineStyle: window.LightweightCharts && window.LightweightCharts.LineStyle
              ? window.LightweightCharts.LineStyle.Dashed : 0,
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { strMaRef.current = null; }
        ensureScale();
      }
      if (strMaRef.current) {
        const ma = _simStrengthMa(src, 5);
        const data = [];
        for (let i = 0; i < src.length; i++) {
          if (ma[i] != null && isFinite(ma[i])) data.push({ time: secs[i], value: ma[i] });
        }
        try { strMaRef.current.setData(data); } catch (e) {}
      }
    } else if (strMaRef.current) {
      try { chart.removeSeries(strMaRef.current); } catch (e) {}
      strMaRef.current = null;
    }
  }, [bars, ind.strength, ind.strma]);

  // 신호 마커(매수▲/매도▼) — curT 이하 도달분만. nearest bar 시각에 스냅.
  useEffect_simc(() => {
    const candle = candleRef.current;
    if (!candle) return;
    const arr = bars || [];
    if (arr.length === 0) { try { candle.setMarkers([]); } catch (e) {} return; }
    // bar t → 단조 sec 매핑(setData 와 동일 규칙으로 재현).
    const secOf = [];
    let lastSec = -1;
    for (let i = 0; i < arr.length; i++) {
      let sec = _hmsToSec(arr[i].t);
      if (sec <= lastSec) sec = lastSec + 1;
      lastSec = sec; secOf.push(sec);
    }
    const nearestSec = (hms) => {
      let best = -1;
      for (let i = 0; i < arr.length; i++) { if (arr[i].t <= hms) best = i; else break; }
      return best >= 0 ? secOf[best] : null;
    };
    const markers = [];
    (signals || []).forEach((sig) => {
      if (curT == null || sig.buy_hms <= curT) {
        const s = nearestSec(sig.buy_hms);
        if (s != null) markers.push({ time: s, position: "belowBar", color: "#4cd6b3", shape: "arrowUp", text: "매수" });
      }
      if (curT == null || sig.sell_hms <= curT) {
        const s = nearestSec(sig.sell_hms);
        if (s != null) {
          const pct = (sig.profit_pct >= 0 ? "+" : "") + (sig.profit_pct || 0).toFixed(1) + "%";
          markers.push({ time: s, position: "aboveBar", color: "#ff5d6c", shape: "arrowDown", text: compact ? "" : pct });
        }
      }
    });
    markers.sort((a, b) => a.time - b.time);
    try { candle.setMarkers(markers); } catch (e) {}
  }, [signals, curT, bars, compact]);

  const lastBar = (bars && bars.length) ? bars[bars.length - 1] : null;
  return (
    <SimChartShell code={code} name={name} lastBar={lastBar} bars={bars}
                   signals={signals} curT={curT} compact={compact} engine="lwc"
                   indicators={ind}>
      <div ref={wrapRef} style={{ width: "100%", height: H }} />
    </SimChartShell>
  );
}

/* ─────────────── 순수 SVG 폴백 경로(줌/팬/크로스헤어 직접 구현) ─────────────── */
function SimCandleChartSVG({ bars, signals, curT, code, name, compact, indicators }) {
  const ind = indicators || _SIM_DEFAULT_INDICATORS;
  const [hover, setHover] = useState_simc(null);
  // 팬 오프셋(우측 끝에서 좌로 이동한 캔들 수) + 줌(보이는 캔들 수).
  const [zoom, setZoom] = useState_simc(0);     // 추가 확대 단계(0=기본 윈도우).
  const [pan, setPan] = useState_simc(0);       // 오른쪽 끝 기준 좌측 이동량.
  const dragRef = useRef_simc(null);
  const svgRef = useRef_simc(null);

  const allBars = bars || [];
  // 보이는 캔들 수: 기본 윈도우에서 zoom 단계만큼 축소(최소 20).
  const visCount = Math.max(20, Math.min(allBars.length || _SIM_WINDOW, _SIM_WINDOW - zoom * 40));
  // 윈도우 끝 인덱스(팬 적용). 최신이 우측.
  const endIdx = Math.max(visCount, allBars.length - pan);
  const startIdx = Math.max(0, endIdx - visCount);
  const view = useMemo_simc(() => allBars.slice(startIdx, endIdx), [bars, startIdx, endIdx]);

  const W = 880;
  const H = compact ? 220 : 340;
  const volH = compact ? 34 : 52;
  const strH = compact ? 24 : 34;
  const padL = 56, padR = 16, padT = 14;
  const gap = 8;
  const priceH = H - padT - volH - strH - gap * 2 - 22;
  const innerW = W - padL - padR;

  const n = view.length;
  const slot = n > 0 ? innerW / n : innerW;
  const candleW = Math.max(1, Math.min(14, slot * 0.66));
  const xCenter = (i) => padL + slot * (i + 0.5);

  const priceTop = padT;
  const priceBot = padT + priceH;
  const highs = view.map(b => b.h || b.c || 0);
  const lows = view.map(b => b.l || b.c || 0).filter(v => v > 0);
  const pMax = highs.length ? Math.max(...highs) : 1;
  const pMin = lows.length ? Math.min(...lows) : 0;
  const pRange = (pMax - pMin) || 1;
  const yPrice = (v) => priceBot - ((v - pMin) / pRange) * priceH;

  const volTop = priceBot + gap;
  const volBot = volTop + volH;
  const vMax = Math.max(1, ...view.map(b => b.vol || 0));
  const yVol = (v) => volBot - (v / vMax) * volH;

  const strTop = volBot + gap;
  const strBot = strTop + strH;
  const strVals = view.map(b => b.strength || 0);
  const sMax = Math.max(100, ...strVals);
  const yStr = (v) => strBot - (Math.min(v, sMax) / sMax) * strH;

  const tIndex = useMemo_simc(() => {
    const m = new Map();
    view.forEach((b, i) => m.set(b.t, i));
    return m;
  }, [view]);

  const nearestIdx = (hms) => {
    if (tIndex.has(hms)) return tIndex.get(hms);
    let best = -1;
    for (let i = 0; i < n; i++) { if (view[i].t <= hms) best = i; else break; }
    return best;
  };

  const strPath = useMemo_simc(() => {
    if (n < 2) return "";
    return view.map((b, i) =>
      `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yStr(b.strength || 0).toFixed(1)}`
    ).join(" ");
  }, [view, n, sMax]);

  // 클라이언트 계산 지표(EMA12/26, 체결강도 MA5, 거래량 MA5/20) — 순수 헬퍼로 버퍼 위 계산.
  //   토글 OFF 면 계산 자체를 생략(빈 배열)해 비용 0.
  const ema12 = useMemo_simc(() => ind.ema ? _simEma(view, 12) : [], [view, ind.ema]);
  const ema26 = useMemo_simc(() => ind.ema ? _simEma(view, 26) : [], [view, ind.ema]);
  const strMa = useMemo_simc(() => (ind.strength && ind.strma) ? _simStrengthMa(view, 5) : [], [view, ind.strength, ind.strma]);
  const volMa = useMemo_simc(() => ind.volma ? _simVolMa(view, [5, 20]) : {}, [view, ind.volma]);

  // 값 배열(bars 길이)→ y 매핑 path. null 구간 끊어 그림. yFn 으로 스케일 선택(가격/거래량/강도).
  const arrPath = (vals, yFn) => {
    if (!vals || n < 2) return "";
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) { started = false; continue; }
      d += `${started ? "L" : "M"} ${xCenter(i).toFixed(1)} ${yFn(v).toFixed(1)} `;
      started = true;
    }
    return d;
  };

  // MA 오버레이 path(MA5/20/60 — null 구간은 끊어 그린다).
  const maPath = (key) => {
    if (n < 2) return "";
    let d = "", started = false;
    view.forEach((b, i) => {
      const v = b[key];
      if (v == null) { started = false; return; }
      d += `${started ? "L" : "M"} ${xCenter(i).toFixed(1)} ${yPrice(v).toFixed(1)} `;
      started = true;
    });
    return d;
  };

  const xTickIdx = useMemo_simc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 7));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
    // 드래그 팬.
    if (dragRef.current != null) {
      const dxPx = (e.clientX - dragRef.current.x) * (W / rect.width);
      const dCandles = Math.round(dxPx / Math.max(1, slot));
      const next = Math.max(0, Math.min(allBars.length - visCount, dragRef.current.pan + dCandles));
      setPan(next);
    }
  };

  // 휠 줌(위로=확대). 기본 페이지 스크롤 막고 zoom 단계 조절.
  const onWheel = (e) => {
    e.preventDefault();
    setZoom(z => Math.max(0, Math.min(8, z + (e.deltaY < 0 ? 1 : -1))));
  };
  const onDown = (e) => { dragRef.current = { x: e.clientX, pan }; };
  const onUp = () => { dragRef.current = null; };

  const lastBar = (bars && bars.length) ? bars[bars.length - 1] : null;

  return (
    <SimChartShell code={code} name={name} lastBar={lastBar} bars={bars}
                   signals={signals} curT={curT} compact={compact} engine="svg"
                   indicators={ind}>
      <div className="chart-wrap">
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
             onMouseMove={onMove} onMouseLeave={() => { setHover(null); onUp(); }}
             onWheel={onWheel} onMouseDown={onDown} onMouseUp={onUp}
             style={{ cursor: dragRef.current ? "grabbing" : "crosshair" }}>
          <text className="chart-axis-text" x={padL - 8} y={priceTop + 8} textAnchor="end" fill="var(--ink-2)">
            {_simPriceTick(pMax)}
          </text>
          <text className="chart-axis-text" x={padL - 8} y={priceBot} textAnchor="end" fill="var(--ink-2)">
            {_simPriceTick(pMin)}
          </text>
          <line x1={padL} x2={W - padR} y1={priceBot} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />
          <line x1={padL} x2={padL} y1={priceTop} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />

          {/* MA 오버레이(5=teal점선, 20=amber, 60=violet) — 토글 ind.ma */}
          {n > 1 && ind.ma && <path d={maPath("ma5")} fill="none" stroke="var(--teal)" strokeWidth="1" opacity="0.5" strokeDasharray="3 2" />}
          {n > 1 && ind.ma && <path d={maPath("ma20")} fill="none" stroke="var(--amber)" strokeWidth="1.1" opacity="0.7" />}
          {n > 1 && ind.ma && <path d={maPath("ma60")} fill="none" stroke="var(--violet)" strokeWidth="1.1" opacity="0.6" />}
          {/* VWAP(금색 실선) — 토글 ind.vwap */}
          {n > 1 && ind.vwap && <path d={maPath("vwap")} fill="none" stroke="#ffd24c" strokeWidth="1.4" opacity="0.85" />}
          {/* VWAP 밴드(±1σ, 서버 vwap_up/vwap_low) — 토글 ind.vwapband */}
          {n > 1 && ind.vwapband && <path d={maPath("vwap_up")} fill="none" stroke="#ffd24c" strokeWidth="0.9" opacity="0.5" strokeDasharray="2 3" />}
          {n > 1 && ind.vwapband && <path d={maPath("vwap_low")} fill="none" stroke="#ffd24c" strokeWidth="0.9" opacity="0.5" strokeDasharray="2 3" />}
          {/* EMA12/26(클라이언트 _simEma) — 토글 ind.ema */}
          {n > 1 && ind.ema && <path d={arrPath(ema12, yPrice)} fill="none" stroke="#6fd6ff" strokeWidth="1" opacity="0.7" />}
          {n > 1 && ind.ema && <path d={arrPath(ema26, yPrice)} fill="none" stroke="#b07cf0" strokeWidth="1" opacity="0.7" />}
          {/* 볼린저(20,2) 상/중/하단(청색 점선) — 토글 ind.boll */}
          {n > 1 && ind.boll && <path d={maPath("bb_up")} fill="none" stroke="#5a93c8" strokeWidth="1" opacity="0.6" strokeDasharray="3 2" />}
          {n > 1 && ind.boll && <path d={maPath("bb_mid")} fill="none" stroke="#5a93c8" strokeWidth="0.9" opacity="0.45" strokeDasharray="2 3" />}
          {n > 1 && ind.boll && <path d={maPath("bb_low")} fill="none" stroke="#5a93c8" strokeWidth="1" opacity="0.6" strokeDasharray="3 2" />}

          {/* 캔들 */}
          {view.map((b, i) => {
            const up = (b.c || 0) >= (b.o || 0);
            const color = up ? "var(--teal)" : "var(--red)";
            const cx = xCenter(i);
            const yHigh = yPrice(b.h || b.c || 0);
            const yLow = yPrice(b.l || b.c || 0);
            const yO = yPrice(b.o || b.c || 0);
            const yC = yPrice(b.c || 0);
            const top = Math.min(yO, yC);
            const bodyH = Math.max(1, Math.abs(yC - yO));
            return (
              <g key={`k${i}`} opacity={hover === i ? 1 : 0.92}>
                <line x1={cx} x2={cx} y1={yHigh} y2={yLow} stroke={color} strokeWidth="1" />
                <rect x={cx - candleW / 2} y={top} width={candleW} height={bodyH} fill={color} />
              </g>
            );
          })}

          {/* 거래량 막대 */}
          {view.map((b, i) => {
            const up = (b.c || 0) >= (b.o || 0);
            const y = yVol(b.vol || 0);
            return <rect key={`v${i}`} x={xCenter(i) - candleW / 2} y={y}
                         width={candleW} height={Math.max(0, volBot - y)}
                         fill={up ? "var(--teal)" : "var(--red)"} opacity="0.4" />;
          })}
          {/* 거래량 MA5/20(클라이언트 _simVolMa) — 토글 ind.volma */}
          {n > 1 && ind.volma && <path d={arrPath(volMa.vol_ma5, yVol)} fill="none" stroke="#4cd6b3" strokeWidth="0.9" opacity="0.7" />}
          {n > 1 && ind.volma && <path d={arrPath(volMa.vol_ma20, yVol)} fill="none" stroke="#f0b35a" strokeWidth="0.9" opacity="0.6" />}
          <text className="chart-axis-text" x={padL - 8} y={volTop + 8} textAnchor="end" fill="var(--ink-3)">거래량</text>

          {/* 체결강도 서브라인(100 균형선) — 토글 ind.strength. strma 시 MA5 점선 오버레이. */}
          {ind.strength && <line x1={padL} x2={W - padR} y1={yStr(100)} y2={yStr(100)}
                stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />}
          {n > 1 && ind.strength && <path d={strPath} fill="none" stroke="var(--violet)" strokeWidth="1.3" opacity="0.85" />}
          {n > 1 && ind.strength && ind.strma && <path d={arrPath(strMa, yStr)} fill="none" stroke="#f0b35a" strokeWidth="1" opacity="0.7" strokeDasharray="3 2" />}
          {ind.strength && <text className="chart-axis-text" x={padL - 8} y={strTop + 8} textAnchor="end" fill="var(--violet)">체결강도</text>}

          {/* 신호 마커 */}
          {(signals || []).map((sig, si) => {
            const bi = nearestIdx(sig.buy_hms);
            const sj = nearestIdx(sig.sell_hms);
            const reached = curT != null && sig.sell_hms <= curT;
            const buyVisible = bi >= 0 && (curT == null || sig.buy_hms <= curT);
            const sellVisible = sj >= 0 && (curT == null || sig.sell_hms <= curT);
            return (
              <g key={`s${si}`}>
                {buyVisible && (
                  <text x={xCenter(bi)} y={yPrice(sig.buy_price) + 13} textAnchor="middle"
                        fontSize={compact ? 10 : 12} fill="var(--teal)" opacity={reached ? 1 : 0.85}>▲</text>
                )}
                {sellVisible && (
                  <g>
                    <text x={xCenter(sj)} y={yPrice(sig.sell_price) - 5} textAnchor="middle"
                          fontSize={compact ? 10 : 12} fill="var(--red)" opacity="1">▼</text>
                    {!compact && (
                      <text x={xCenter(sj)} y={yPrice(sig.sell_price) - 16} textAnchor="middle"
                            fontSize="9" className="mono"
                            fill={sig.profit_pct >= 0 ? "var(--teal)" : "var(--red)"}>
                        {sig.profit_pct >= 0 ? "+" : ""}{(sig.profit_pct || 0).toFixed(1)}%
                      </text>
                    )}
                  </g>
                )}
              </g>
            );
          })}

          {/* X 시간 라벨 */}
          {xTickIdx.map((i) => (
            <text key={`x${i}`} className="chart-axis-text" x={xCenter(i)} y={H - 6} textAnchor="middle">
              {view[i] ? _simTimeLabel(view[i].t) : ""}
            </text>
          ))}

          {/* 크로스헤어(수직+수평) */}
          {hover != null && view[hover] && (
            <g>
              <line x1={xCenter(hover)} x2={xCenter(hover)} y1={priceTop} y2={priceBot}
                    stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="3 3" />
              <line x1={padL} x2={W - padR} y1={yPrice(view[hover].c || 0)} y2={yPrice(view[hover].c || 0)}
                    stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
            </g>
          )}
        </svg>

        {hover != null && view[hover] && (
          <div style={{
            position: "absolute", top: 12, right: 12,
            background: "var(--bg-0)", border: "1px solid var(--line-2)",
            borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
            minWidth: 150, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
          }}>
            <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>
              {_simTimeLabel(view[hover].t)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
              <span style={{ color: "var(--ink-2)" }}>종가</span>
              <span style={{ textAlign: "right" }}>{_simPriceTick(view[hover].c)}</span>
              <span style={{ color: "var(--ink-2)" }}>등락</span>
              <span style={{ textAlign: "right" }} className={view[hover].change >= 0 ? "num-pos" : "num-neg"}>
                {(view[hover].change || 0).toFixed(2)}%
              </span>
              <span style={{ color: "var(--ink-2)" }}>체결강도</span>
              <span style={{ textAlign: "right" }}>{(view[hover].strength || 0).toFixed(0)}</span>
            </div>
          </div>
        )}

        {/* 줌/팬 힌트 + 리셋 */}
        {n > 0 && (zoom > 0 || pan > 0) && (
          <button className="btn ghost sm" onClick={() => { setZoom(0); setPan(0); }}
                  style={{ position: "absolute", top: 10, left: 10, fontSize: 10, padding: "2px 7px" }}>
            ⤢ 리셋
          </button>
        )}

        {n === 0 && (
          <div style={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center",
            justifyContent: "center", color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
          }}>
            재생을 시작하면 캔들이 실시간으로 채워집니다
          </div>
        )}
      </div>
    </SimChartShell>
  );
}

/* ─────────────── 호가 불균형 그래프 (Req 9, ASYMMETRIC: live+svg only) ───────────────
   b.imbalance(=매수총잔량/매도총잔량, 1.0=균형) 시계열 + 1.0 기준선. imbalance 부재 시
   buy_rest/sell_rest 로 정규화 폴백. 데이터 전무면 숨김(무예외). LWC 는 싣지 않는다. */
function SimImbalancePane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  // imbalance 값(직접 필드 우선, 없으면 buy_rest/sell_rest 비율). 둘 다 없으면 null.
  const vals = useMemo_simc(() => view.map(b => {
    if (b.imbalance != null && isFinite(b.imbalance)) return b.imbalance;
    const br = (b.buy_rest != null && isFinite(b.buy_rest)) ? b.buy_rest : null;
    const sr = (b.sell_rest != null && isFinite(b.sell_rest)) ? b.sell_rest : null;
    if (br != null && sr != null && sr > 0) return br / sr;
    return null;
  }), [view]);

  const hasData = useMemo_simc(() => vals.some(v => v != null), [vals]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 40;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  // 1.0 중심, 동적 상한(최대 비율, 최소 2.0). 0..vMax 선형, 1.0 균형선.
  const finite = vals.filter(v => v != null && isFinite(v));
  const vMax = Math.max(2.0, ...finite);
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => padT + innerH - (Math.min(v, vMax) / vMax) * innerH;

  let d = "", started = false;
  for (let i = 0; i < n; i++) {
    const v = vals[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
    started = true;
  }

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>호가 불균형(레벨1 총잔량비)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 1.0 균형선 */}
        <line x1={padL} x2={W - padR} y1={yAt(1.0)} y2={yAt(1.0)}
              stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="2 3" />
        <text className="chart-axis-text" x={padL - 6} y={yAt(1.0) + 3} textAnchor="end" fill="var(--ink-3)">1.0</text>
        {n > 1 && <path d={d} fill="none" stroke="var(--teal)" strokeWidth="1.2" opacity="0.85" />}
      </svg>
    </div>
  );
}

/* ─────────────── net-delta strip (Req 7 in-chart orderflow, ASYMMETRIC: live+svg only) ───────────────
   bar 별 순매수수량(net_qty)을 색 히스토그램(>0 teal / <0 red)으로 캔들 아래 띠에 그린다.
   SimOrderFlowTape(side panel)과 달리 차트-내부 오더플로우 표현. net_qty 전무면 숨김. LWC 제외. */
function SimNetDeltaStrip({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const hasData = useMemo_simc(() =>
    view.some(b => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
    [view]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 28 : 38;
  const padL = 56, padR = 16;
  const innerW = W - padL - padR;
  const mid = H / 2;
  const half = mid - 3;
  const maxAbs = Math.max(1, ...view.map(b => Math.abs(_simNq(b))));
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.7);

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>net-delta(순매수수량)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 0 기준선 */}
        <line x1={padL} x2={W - padR} y1={mid} y2={mid} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        {view.map((b, i) => {
          const nq = _simNq(b);
          const h = (Math.min(Math.abs(nq), maxAbs) / maxAbs) * half;
          const x = padL + slot * i + (slot - barW) / 2;
          const y = nq >= 0 ? mid - h : mid;
          const color = nq > 0 ? "var(--teal)" : nq < 0 ? "var(--red)" : "var(--ink-3)";
          return <rect key={i} x={x.toFixed(1)} y={y.toFixed(1)} width={barW.toFixed(1)}
                       height={Math.max(0.5, h).toFixed(1)} fill={color} opacity="0.7" />;
        })}
      </svg>
    </div>
  );
}

/* ─────────────── RSI 서브패인 (Req 2, ASYMMETRIC: live+svg only) ───────────────
   RSI(Wilder 14기간) 0–100 스케일 SVG. 30/50/70 가이드선 + 폴리라인.
   클라이언트 _simRsi(window 전역) 으로 계산. LWC 는 싣지 않는다(ASYMMETRIC PARITY). */
function SimRsiPane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const rsiVals = useMemo_simc(() =>
    (typeof _simRsi === "function") ? _simRsi(view, 14) : [],
    [view]);

  const hasData = useMemo_simc(() => rsiVals.some(v => v != null), [rsiVals]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 40;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => padT + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH;

  let d = "", started = false;
  for (let i = 0; i < n; i++) {
    const v = rsiVals[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
    started = true;
  }

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>RSI(14)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 30 / 50 / 70 가이드선 */}
        {[30, 50, 70].map(lv => (
          <line key={lv} x1={padL} x2={W - padR} y1={yAt(lv)} y2={yAt(lv)}
                stroke="rgba(255,255,255,0.10)" strokeWidth="1" strokeDasharray="2 3" />
        ))}
        <text className="chart-axis-text" x={padL - 6} y={yAt(70) + 3} textAnchor="end" fill="var(--ink-3)">70</text>
        <text className="chart-axis-text" x={padL - 6} y={yAt(30) + 3} textAnchor="end" fill="var(--ink-3)">30</text>
        {n > 1 && <path d={d} fill="none" stroke="var(--teal)" strokeWidth="1.2" opacity="0.85" />}
      </svg>
    </div>
  );
}

/* ─────────────── MACD 서브패인 (Req 2, ASYMMETRIC: live+svg only) ───────────────
   MACD(12/26/9) zero-centered SVG: 히스토그램(hist) + MACD 라인 + 시그널 라인.
   클라이언트 _simMacd(window 전역) 으로 계산. LWC 는 싣지 않는다(ASYMMETRIC PARITY). */
function SimMacdPane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const macdData = useMemo_simc(() =>
    (typeof _simMacd === "function") ? _simMacd(view) : { macd: [], signal: [], hist: [] },
    [view]);

  const hasData = useMemo_simc(() =>
    (macdData.macd || []).some(v => v != null),
    [macdData]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 42;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const mid = padT + innerH / 2;
  const half = innerH / 2 - 1;

  const hist = macdData.hist || [];
  const macdLine = macdData.macd || [];
  const signalLine = macdData.signal || [];

  let maxAbs = 1;
  for (let i = 0; i < n; i++) {
    const v = hist[i];
    if (v != null && isFinite(v)) maxAbs = Math.max(maxAbs, Math.abs(v));
  }
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => (v == null || !isFinite(v)) ? mid
    : mid - (Math.max(-maxAbs, Math.min(maxAbs, v)) / maxAbs) * half;

  const slot = n > 1 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.55);

  // MACD / 시그널 라인 path.
  const linePath = (vals) => {
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) { started = false; continue; }
      d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
      started = true;
    }
    return d;
  };

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>MACD(12,26,9)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 0 기준선 */}
        <line x1={padL} x2={W - padR} y1={mid} y2={mid} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        {/* 히스토그램 막대 */}
        {view.map((b, i) => {
          const v = hist[i];
          if (v == null || !isFinite(v)) return null;
          const bh = Math.abs(yAt(v) - mid);
          const x = xAt(i) - barW / 2;
          const y = v >= 0 ? mid - bh : mid;
          const color = v > 0 ? "var(--teal)" : "var(--red)";
          return <rect key={i} x={x.toFixed(1)} y={y.toFixed(1)}
                       width={barW.toFixed(1)} height={Math.max(0.5, bh).toFixed(1)}
                       fill={color} opacity="0.55" />;
        })}
        {/* MACD 라인(teal 실선) */}
        {n > 1 && <path d={linePath(macdLine)} fill="none" stroke="var(--teal)" strokeWidth="1.1" opacity="0.9" />}
        {/* 시그널 라인(amber 점선) */}
        {n > 1 && <path d={linePath(signalLine)} fill="none" stroke="var(--amber)" strokeWidth="1" opacity="0.8" strokeDasharray="3 2" />}
      </svg>
    </div>
  );
}

/* 공통 셸 — 헤더(종목·현재가·등락 게이지·세션 링) + 본문(차트) + 히트 스트립.
   신호(매수/매도) 도달 순간 패널 테두리를 1회 플래시한다(curT 가 신호 시각을 막 넘을 때).
   호가 불균형·net-delta·RSI·MACD 서브패인은 ASYMMETRIC — live+svg 만(engine !== "lwc") 토글 시 노출. */
function SimChartShell({ code, name, lastBar, bars, signals, curT, compact, engine, indicators, children }) {
  const ind = indicators || _SIM_DEFAULT_INDICATORS;
  // 신호 도달 플래시 — curT 가 새 신호 시각(buy/sell)을 넘는 순간 1회 깜빡. ref 로 도달분 추적.
  const seenRef = useRef_simc(new Set());
  const [flash, setFlash] = useState_simc(null);  // "buy"|"sell"|null.

  // 리플레이 재시작(curT 리셋) 시 도달 기록 초기화.
  useEffect_simc(() => {
    if (curT == null) seenRef.current = new Set();
  }, [curT]);

  useEffect_simc(() => {
    if (curT == null) return;
    const seen = seenRef.current;
    let kind = null;
    (signals || []).forEach((sig) => {
      const bk = code + "@b@" + sig.buy_hms;
      if (sig.buy_hms != null && sig.buy_hms <= curT && !seen.has(bk)) { seen.add(bk); kind = "buy"; }
      const sk = code + "@s@" + sig.sell_hms;
      if (sig.sell_hms != null && sig.sell_hms <= curT && !seen.has(sk)) { seen.add(sk); kind = "sell"; }
    });
    if (kind) {
      setFlash(kind);
      const id = setTimeout(() => setFlash(null), 650);
      return () => clearTimeout(id);
    }
  }, [curT, signals, code]);

  // 신호 도달 테두리 플래시 — 인라인 boxShadow + transition 으로 1회 점멸(styles.css 불가).
  //   매수=teal 글로우, 매도=red 글로우. 650ms 뒤 flash=null → transition 으로 부드럽게 소멸.
  const flashGlow = flash === "buy"
    ? "0 0 0 2px var(--teal), 0 0 16px 2px rgba(76,214,179,0.55)"
    : flash === "sell"
      ? "0 0 0 2px var(--red), 0 0 16px 2px rgba(255,93,108,0.55)"
      : "none";
  return (
    <div className="panel" style={{ minWidth: 0, boxShadow: flashGlow, transition: "box-shadow 0.45s ease-out" }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          <span className="mono" style={{ fontSize: compact ? 11 : 12.5 }}>
            {code}{name ? " · " + name : ""}
          </span>
          <span className="mono" style={{ fontSize: 9, color: "var(--ink-3)", marginLeft: 6 }}>
            {engine === "lwc" ? "LWC" : "SVG"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {lastBar && <SimChangeGauge changePct={lastBar.change} size={compact ? 48 : 56} />}
          <SimSessionRing curT={curT} size={compact ? 44 : 52} />
          {lastBar && (
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)" }}>
              {_simPriceTick(lastBar.c)}
            </span>
          )}
        </div>
      </div>
      <div className="panel-bd">
        {children}
        {/* 차트-내부 서브패인 — ASYMMETRIC: live+svg 만(LWC 제외). 토글별 노출. */}
        {engine !== "lwc" && ind.imbalance && <SimImbalancePane bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.orderflow && <SimNetDeltaStrip bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.rsi && <SimRsiPane bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.macd && <SimMacdPane bars={bars} compact={compact} />}
        <SimOrderBook lastBar={lastBar} compact={compact} />
        <SimOrderFlowTape bars={bars} compact={compact} />
        <SimFootprint bars={bars} compact={compact} />
        <SimHeatStrip bars={bars} compact={compact} />
        <SimRestFlow bars={bars} compact={compact} />
      </div>
    </div>
  );
}

/* ① 엔진 자동선택 래퍼 — LWC 가용 시 lightweight-charts, 아니면 SVG 폴백. */
function SimCandleChart(props) {
  const useLwc = useMemo_simc(() => _lwcAvailable(), []);
  return useLwc ? <SimCandleChartLWC {...props} /> : <SimCandleChartSVG {...props} />;
}

/* ─────────────── 오더플로우 테이프 (Part: 오더플로우) ───────────────
   최근 N bar 의 순매수수량(net_qty) 을 색 스트립으로(순매수>0 teal 농도 / 순매도<0 red 농도).
   net_qty 데이터 전무면 숨김. 진행에 따라 우측으로 자라난다(리플레이 체감 강화). */
function SimOrderFlowTape({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const hasData = useMemo_simc(() =>
    view.some(b => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
    [view]);
  if (!hasData) return null;

  const maxAbs = Math.max(1, ...view.map(b => Math.abs(_simNq(b))));
  const H = compact ? 14 : 18;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)", flexShrink: 0, width: 48 }}>
        오더플로우
      </span>
      <div style={{ display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
        {view.map((b, i) => {
          const nq = _simNq(b);
          const mag = Math.min(1, Math.abs(nq) / maxAbs);
          const a = (0.15 + mag * 0.75).toFixed(3);
          const bg = nq > 0 ? `rgba(76,214,179,${a})` : nq < 0 ? `rgba(255,93,108,${a})` : "rgba(150,158,170,0.12)";
          return (
            <div key={i} title={_simTimeLabel(b.t) + " · 순매수 " + _simPriceTick(nq)}
                 style={{ flex: 1, background: bg }} />
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────── footprint 오더플로우 (S3) ───────────────
   가격 레벨별 매수/매도 체결량을 누적해 footprint 차트처럼 그린다(가격 사다리 행).
   각 행: [매도체결량 막대 | 가격 | 매수체결량 막대] + 델타. 현재가 행 강조, 강도 히트 색.

   체결량 분리(매수 vs 매도) — 데이터 출처 정직성:
     • net_qty(=초/분당매수수량−매도수량) 가 있으면 **실데이터 정확 분리**:
         buy = (vol + net_qty)/2,  sell = (vol − net_qty)/2   (분당매수/매도수량 복원).
     • net_qty 가 없으면(구버전 DB) 체결강도 휴리스틱으로 근사:
         강도>100 → 매수 우세, <100 → 매도 우세. share = clamp(strength/200, 0..1).
       이 경우는 근사임을 행 상단 배지로 명시한다(허위 정밀 회피).
   가격 버킷: bar 종가를 틱 크기로 내림 정렬(추정 틱 = 가격대별 한국거래소 호가단위 근사). */
// Phase12-A — net_qty 유한값만(null=데이터없음·실제 0 모두 막대 없음, NaN 위험 제거).
function _simNq(b) { return (b && b.net_qty != null && isFinite(b.net_qty)) ? b.net_qty : 0; }

function _hoga_tick(price) {
  // 한국거래소 호가단위 근사(2023 개편 기준 단순화). 정확값 아님 — footprint 버킷팅용.
  const p = Math.abs(Number(price) || 0);
  if (p < 2000) return 1;
  if (p < 5000) return 5;
  if (p < 20000) return 10;
  if (p < 50000) return 50;
  if (p < 200000) return 100;
  if (p < 500000) return 500;
  return 1000;
}

function _bucketPrice(price, tick) {
  const t = tick || 1;
  return Math.round(Math.floor((Number(price) || 0) / t) * t);
}

// bar 한 개의 (buy, sell) 체결량 추정. real=net_qty 사용 여부.
function _barBuySell(bar) {
  const vol = (bar.vol != null && isFinite(bar.vol)) ? bar.vol : 0;
  const nq = bar.net_qty;
  if (nq != null && isFinite(nq)) {
    const buy = (vol + nq) / 2;
    const sell = (vol - nq) / 2;
    return { buy: Math.max(0, buy), sell: Math.max(0, sell), real: true };
  }
  // 휴리스틱 — 체결강도로 매수 점유율 근사(100=균형).
  const s = (bar.strength != null && isFinite(bar.strength)) ? bar.strength : 100;
  const buyShare = Math.max(0, Math.min(1, s / 200));
  return { buy: vol * buyShare, sell: vol * (1 - buyShare), real: false };
}

function SimFootprint({ bars, compact }) {
  const [open, setOpen] = useState_simc(false);

  // 가격 레벨별 누적 매수/매도 체결량 집계(최근 윈도우). real 플래그도 추적.
  const agg = useMemo_simc(() => {
    const arr = bars || [];
    const view = arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    if (view.length === 0) return { levels: [], real: true, curPrice: null, hasVol: false };
    const last = view[view.length - 1];
    const map = new Map();     // bucketPrice → {buy, sell}
    let real = true;
    let hasVol = false;
    for (let i = 0; i < view.length; i++) {
      const b = view[i];
      const bs = _barBuySell(b);
      if (!bs.real) real = false;
      if ((bs.buy + bs.sell) > 0) hasVol = true;
      // Phase12-A — 호가단위는 bar 자기 가격으로 산정(단일 last.c tick 으로 전 구간을
      //   버킷하면 KRX 호가단위 경계(예: 50,000 전후 50→100)를 가로지를 때 정렬이 어긋남).
      const key = _bucketPrice(b.c, _hoga_tick(b.c));
      const cur = map.get(key) || { buy: 0, sell: 0 };
      cur.buy += bs.buy; cur.sell += bs.sell;
      map.set(key, cur);
    }
    // 가격 내림차순(높은 가격이 위).
    const levels = Array.from(map.entries())
      .map(([price, v]) => ({ price, buy: v.buy, sell: v.sell, delta: v.buy - v.sell }))
      .sort((a, b) => b.price - a.price);
    return { levels, real, curPrice: _bucketPrice(last.c, _hoga_tick(last.c)), hasVol };
  }, [bars]);

  if (!agg.hasVol) return null;   // 체결량 데이터 전무 → 숨김(무예외).

  const maxSide = Math.max(1, ...agg.levels.map(l => Math.max(l.buy, l.sell)));
  const rowH = compact ? 14 : 17;
  const barW = compact ? 80 : 110;

  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "4px 8px",
          background: "transparent", border: "1px solid var(--line-1)", borderRadius: 5,
          color: "var(--ink-2)", cursor: "pointer", fontSize: 10,
        }}>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▼" : "▶"}</span>
        오더플로우 footprint
        <span style={{ marginLeft: "auto", color: agg.real ? "var(--teal)" : "var(--amber)" }}>
          {agg.real ? "실데이터" : "강도 근사"}
        </span>
      </button>
      {open && (
        <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 1 }}>
          {/* 헤더 */}
          <div className="mono" style={{ display: "flex", alignItems: "center", fontSize: 8.5, color: "var(--ink-3)", padding: "0 2px" }}>
            <span style={{ width: barW, textAlign: "left", color: "var(--red)" }}>매도체결</span>
            <span style={{ flex: 1, textAlign: "center" }}>가격</span>
            <span style={{ width: barW, textAlign: "right", color: "var(--teal)" }}>매수체결</span>
            <span style={{ width: compact ? 44 : 56, textAlign: "right" }}>델타</span>
          </div>
          {agg.levels.map(lv => {
            const isCur = lv.price === agg.curPrice;
            const sellW = (lv.sell / maxSide) * barW;
            const buyW = (lv.buy / maxSide) * barW;
            const sellInt = Math.min(1, lv.sell / maxSide);
            const buyInt = Math.min(1, lv.buy / maxSide);
            return (
              <div key={lv.price} className="mono"
                   style={{
                     display: "flex", alignItems: "center", height: rowH, fontSize: 9.5,
                     background: isCur ? "rgba(255,210,76,0.10)" : "transparent",
                     borderRadius: 3,
                     boxShadow: isCur ? "0 0 0 1px rgba(255,210,76,0.4) inset" : "none",
                   }}>
                {/* 매도 체결 막대(우측 정렬 — 가격 쪽으로 자람) */}
                <div style={{ width: barW, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 4 }}>
                  <span style={{ color: "var(--ink-3)", fontSize: 8.5 }}>
                    {lv.sell >= 1 ? _simPriceTick(lv.sell) : ""}
                  </span>
                  <div style={{ width: sellW, height: rowH - 5, background: `rgba(255,93,108,${(0.25 + sellInt * 0.6).toFixed(3)})`, borderRadius: 2 }} />
                </div>
                {/* 가격 */}
                <span style={{ flex: 1, textAlign: "center", color: isCur ? "var(--amber)" : "var(--ink-1)", fontWeight: isCur ? 600 : 400 }}>
                  {_simPriceTick(lv.price)}
                </span>
                {/* 매수 체결 막대(좌측 정렬 — 가격 쪽에서 자람) */}
                <div style={{ width: barW, display: "flex", justifyContent: "flex-start", alignItems: "center", gap: 4 }}>
                  <div style={{ width: buyW, height: rowH - 5, background: `rgba(76,214,179,${(0.25 + buyInt * 0.6).toFixed(3)})`, borderRadius: 2 }} />
                  <span style={{ color: "var(--ink-3)", fontSize: 8.5 }}>
                    {lv.buy >= 1 ? _simPriceTick(lv.buy) : ""}
                  </span>
                </div>
                {/* 델타 */}
                <span style={{ width: compact ? 44 : 56, textAlign: "right", color: lv.delta >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {lv.delta >= 0 ? "+" : ""}{_simPriceTick(lv.delta)}
                </span>
              </div>
            );
          })}
          {!agg.real && (
            <div style={{ fontSize: 8.5, color: "var(--ink-3)", marginTop: 3, lineHeight: 1.4 }}>
              순매수수량(net_qty) 부재로 체결강도 기반 근사 분리다(실 매수/매도 체결량 아님).
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─────────────── HTS형 호가창 (S5) ───────────────
   실제 거래화면 호가창처럼 현재가 중심 수직 사다리. 매도 호가(위·파랑 톤·HTS 관행)·
   매수 호가(아래·빨강 톤)·레벨별 가로 잔량 막대·총매도/총매수 잔량 footer·체결강도 배지.

   가용 실데이터 한계 정직 표기: 일일 DB 는 최우선호가(bid1/ask1)와 총잔량(buy_rest/
   sell_rest)만 제공한다(레벨 2~10 호가 없음). 따라서 레벨1 + 총잔량을 크게 보여주고
   "레벨1 호가 + 총잔량" 임을 명시한다(허위 다단 호가 생성 금지). */
function SimOrderBook({ lastBar, compact }) {
  // Phase7 — bid1/ask1 변동 플래시. prev 값 추적해 변할 때 짧은 배경 글로우(CSS transition).
  const prevRef = useRef_simc({ bid1: null, ask1: null });
  const [flash, setFlash] = useState_simc({ bid: false, ask: false });

  const bid1 = (lastBar && lastBar.bid1 != null && isFinite(lastBar.bid1)) ? lastBar.bid1 : null;
  const ask1 = (lastBar && lastBar.ask1 != null && isFinite(lastBar.ask1)) ? lastBar.ask1 : null;

  useEffect_simc(() => {
    const p = prevRef.current;
    const bidChg = p.bid1 != null && bid1 != null && bid1 !== p.bid1;
    const askChg = p.ask1 != null && ask1 != null && ask1 !== p.ask1;
    if (bidChg || askChg) {
      setFlash({ bid: bidChg, ask: askChg });
      const id = setTimeout(() => setFlash({ bid: false, ask: false }), 280);
      prevRef.current = { bid1, ask1 };
      return () => clearTimeout(id);
    }
    prevRef.current = { bid1, ask1 };
  }, [bid1, ask1]);

  if (!lastBar) return null;
  const buyRest = (lastBar.buy_rest != null && isFinite(lastBar.buy_rest)) ? lastBar.buy_rest : null;
  const sellRest = (lastBar.sell_rest != null && isFinite(lastBar.sell_rest)) ? lastBar.sell_rest : null;
  // 호가도 잔량도 전무하면 숨김(무예외).
  if (bid1 == null && ask1 == null && buyRest == null && sellRest == null) return null;

  const cur = (lastBar.c != null && isFinite(lastBar.c)) ? lastBar.c : null;
  const strength = (lastBar.strength != null && isFinite(lastBar.strength)) ? lastBar.strength : null;
  const maxRest = Math.max(1, buyRest || 0, sellRest || 0);
  const askW = sellRest != null ? (sellRest / maxRest) * 100 : 0;
  const bidW = buyRest != null ? (buyRest / maxRest) * 100 : 0;
  // 스프레드(ask1-bid1) + bps(중간가 기준 만분율). 둘 다 있을 때만.
  const spread = (bid1 != null && ask1 != null) ? (ask1 - bid1) : null;
  const mid = (bid1 != null && ask1 != null) ? (ask1 + bid1) / 2 : null;
  const spreadBps = (spread != null && mid && mid > 0) ? (spread / mid) * 10000 : null;
  // 잔량 점유율(buy_rest vs sell_rest 총합 대비) — true ratio depth.
  const totRest = (buyRest || 0) + (sellRest || 0);
  const buyShare = totRest > 0 ? (buyRest || 0) / totRest * 100 : null;
  const sellShare = totRest > 0 ? (sellRest || 0) / totRest * 100 : null;
  // 체결강도 색(100=균형). >100 매수 우세(teal), <100 매도 우세(red).
  const stColor = strength == null ? "var(--ink-2)" : strength >= 100 ? "var(--teal)" : "var(--red)";
  const rowH = compact ? 20 : 24;
  const askBg = flash.ask ? "rgba(56,140,255,0.22)" : "rgba(56,140,255,0.06)";
  const bidBg = flash.bid ? "rgba(255,93,108,0.22)" : "rgba(255,93,108,0.06)";

  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3, gap: 6 }}>
        <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}
              title="일일 DB는 최우선호가·총잔량만 제공(레벨2~10 없음)">호가창 (레벨1 + 총잔량)</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {spread != null && (
            <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-2)" }}>
              스프레드 {_simPriceTick(spread)}{spreadBps != null ? ` (${spreadBps.toFixed(1)}bp)` : ""}
            </span>
          )}
          {strength != null && (
            <span className="mono" style={{ fontSize: 9.5, color: stColor, padding: "1px 6px", borderRadius: 3, border: "1px solid " + (strength >= 100 ? "var(--teal-dim)" : "var(--line-1)") }}>
              체결강도 {strength.toFixed(0)}
            </span>
          )}
        </div>
      </div>
      {/* 매도호가1(위, HTS 파랑 톤) — bid/ask 변동 시 배경 플래시(CSS transition) */}
      <div style={{ display: "flex", alignItems: "center", height: rowH, background: askBg, borderRadius: 3, marginBottom: 1, transition: "background 0.28s ease-out" }}>
        <span className="mono" style={{ width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#5aa0ff", paddingRight: 8 }}>
          {ask1 != null ? _simPriceTick(ask1) : "—"}
        </span>
        <div style={{ flex: 1, height: rowH - 8, position: "relative", display: "flex", justifyContent: "flex-start" }}>
          <div style={{ width: askW + "%", height: "100%", background: "rgba(56,140,255,0.30)", borderRadius: 2, transition: "width 0.2s ease-out" }} />
        </div>
        <span className="mono" style={{ width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#5aa0ff", paddingRight: 4 }}>
          {sellRest != null ? _simPriceTick(sellRest) : "—"}
        </span>
      </div>
      {/* 현재가 구분선 */}
      <div className="mono" style={{ textAlign: "center", fontSize: 11, color: "var(--amber)", padding: "2px 0", letterSpacing: ".04em" }}>
        ▸ {cur != null ? _simPriceTick(cur) : "—"} ◂
      </div>
      {/* 매수호가1(아래, HTS 빨강 톤) */}
      <div style={{ display: "flex", alignItems: "center", height: rowH, background: bidBg, borderRadius: 3, marginTop: 1, transition: "background 0.28s ease-out" }}>
        <span className="mono" style={{ width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#ff8088", paddingRight: 8 }}>
          {bid1 != null ? _simPriceTick(bid1) : "—"}
        </span>
        <div style={{ flex: 1, height: rowH - 8, display: "flex", justifyContent: "flex-start" }}>
          <div style={{ width: bidW + "%", height: "100%", background: "rgba(255,93,108,0.28)", borderRadius: 2, transition: "width 0.2s ease-out" }} />
        </div>
        <span className="mono" style={{ width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#ff8088", paddingRight: 4 }}>
          {buyRest != null ? _simPriceTick(buyRest) : "—"}
        </span>
      </div>
      {/* 미니 불균형 게이지 — buy_rest vs sell_rest 점유율(% 라벨). 잔량 데이터 있을 때만. */}
      {buyShare != null && sellShare != null && (
        <div style={{ marginTop: 5 }}>
          <div style={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
            <div style={{ width: buyShare.toFixed(1) + "%", background: "var(--teal)", opacity: 0.7, transition: "width 0.25s ease-out" }} />
            <div style={{ width: sellShare.toFixed(1) + "%", background: "var(--red)", opacity: 0.7, transition: "width 0.25s ease-out" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2, fontSize: 9 }}>
            <span className="mono" style={{ color: "var(--teal)" }}>매수 {buyShare.toFixed(0)}%</span>
            <span className="mono" style={{ color: "var(--red)" }}>매도 {sellShare.toFixed(0)}%</span>
          </div>
        </div>
      )}
      {/* footer — 총매도/총매수 잔량 */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 9.5 }}>
        <span className="mono" style={{ color: "#5aa0ff" }}>총매도 {sellRest != null ? _simPriceTick(sellRest) : "—"}</span>
        <span className="mono" style={{ color: "#ff8088" }}>총매수 {buyRest != null ? _simPriceTick(buyRest) : "—"}</span>
      </div>
    </div>
  );
}

/* ─────────────── 멀티차트 오버레이 모드 (정규화 비교) ───────────────
   선택 종목들(≤4)을 한 차트에 정규화(각 종목 시작 종가=100) 라인으로 겹쳐 그린다.
   범례·색상 구분. 진행에 따라 함께 자라난다. 순수 SVG(라이브러리 불필요 — 비교 전용). */
const _SIM_OVERLAY_COLORS = ["#4cd6b3", "#ff5d6c", "#f0b35a", "#7c6cf0"];

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

Object.assign(window, {
  SimCandleChart, SimCandleChartLWC, SimCandleChartSVG,
  SimHeatStrip, SimRestFlow, SimSignalLog,
  SimChangeGauge, SimSessionRing,
  SimOrderFlowTape, SimFootprint, SimOrderBook, SimOverlayChart,
  SimImbalancePane, SimNetDeltaStrip, SimRsiPane, SimMacdPane,
  _simTimeLabel, _simPriceTick, _strengthColor, _sessionProgress, _changeColor,
  _simSma, _simEma, _simRsi, _simMacd, _simVolMa, _simStrengthMa,
  _SIM_DEFAULT_INDICATORS,
});

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { SimCandleChart, SimCandleChartLWC, SimCandleChartSVG, SimOverlayChart, SimSignalLog };
