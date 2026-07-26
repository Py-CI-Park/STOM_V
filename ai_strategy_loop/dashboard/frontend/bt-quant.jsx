/* bt-quant.jsx — v5.4 B1: 백테스트 퀀트 인사이트 패널(회귀·다차원 회귀·자기상관·요일 구조).
 *   목적: AI 분석에 도움이 되는 수치 + 사람에게 인사이트를 주는 시각화(순수 SVG, 외부 라이브러리 금지).
 *   입력은 /bt/result 의 analysis 페이로드만 사용(재계산 없음 — 표시용 통계 요약만 클라이언트 계산).
 *     - analysis.mae_mfe : [{mae, mfe, pnl_pct, hold_sec, code}]
 *     - analysis.equity.daily : [{date, pnl, ...}]
 */
const { useMemo: useMemo_btq } = React;

// ---- 통계 유틸(닫힌형 OLS — 표시용) ----
function _btqOls(xs, ys) {
  const n = Math.min(xs.length, ys.length);
  if (n < 3) return null;
  let sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
  for (let i = 0; i < n; i++) { const x = xs[i], y = ys[i]; sx += x; sy += y; sxx += x * x; sxy += x * y; syy += y * y; }
  const den = n * sxx - sx * sx;
  if (!den) return null;
  const b = (n * sxy - sx * sy) / den;
  const a = (sy - b * sx) / n;
  const my = sy / n;
  let ssTot = 0, ssRes = 0;
  for (let i = 0; i < n; i++) { const f = a + b * xs[i]; ssTot += (ys[i] - my) ** 2; ssRes += (ys[i] - f) ** 2; }
  const r2 = ssTot ? Math.max(0, 1 - ssRes / ssTot) : 0;
  return { a, b, r2, n };
}

// 표준화 다중회귀(가우스 소거, k<=3) — 계수는 표준화 베타(상대 기여 비교용).
function _btqMultiOls(X, y) {
  const n = y.length, k = X.length;
  if (n < k + 3) return null;
  const std = (arr) => {
    const m = arr.reduce((s, v) => s + v, 0) / arr.length;
    const sd = Math.sqrt(arr.reduce((s, v) => s + (v - m) ** 2, 0) / arr.length) || 1;
    return arr.map(v => (v - m) / sd);
  };
  const Z = X.map(std), yz = std(y);
  // normal equations: (Z'Z) beta = Z'y
  const A = [], B = [];
  for (let i = 0; i < k; i++) {
    A.push([]);
    for (let j = 0; j < k; j++) A[i].push(Z[i].reduce((s, v, t) => s + v * Z[j][t], 0));
    B.push(Z[i].reduce((s, v, t) => s + v * yz[t], 0));
  }
  // gaussian elimination
  for (let c = 0; c < k; c++) {
    let piv = c;
    for (let r = c + 1; r < k; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    if (Math.abs(A[piv][c]) < 1e-9) return null;
    [A[c], A[piv]] = [A[piv], A[c]]; [B[c], B[piv]] = [B[piv], B[c]];
    for (let r = 0; r < k; r++) {
      if (r === c) continue;
      const f = A[r][c] / A[c][c];
      for (let j = 0; j < k; j++) A[r][j] -= f * A[c][j];
      B[r] -= f * B[c];
    }
  }
  const beta = B.map((v, i) => v / A[i][i]);
  let ssRes = 0, ssTot = 0;
  for (let t = 0; t < n; t++) {
    let f = 0;
    for (let i = 0; i < k; i++) f += beta[i] * Z[i][t];
    ssRes += (yz[t] - f) ** 2; ssTot += yz[t] ** 2;
  }
  const r2 = ssTot ? Math.max(0, 1 - ssRes / ssTot) : 0;
  return { beta, r2, n };
}

function _btqParseDow(dateVal) {
  // date: "YYYYMMDD" | "YYYY-MM-DD" | epoch — 요일 0=일…6=토, 실패 시 null.
  if (dateVal == null) return null;
  let d = null;
  const s = String(dateVal);
  if (/^\d{8}$/.test(s)) d = new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8));
  else if (/^\d{4}-\d{2}-\d{2}/.test(s)) d = new Date(s.slice(0, 10));
  else if (Number.isFinite(Number(dateVal)) && Number(dateVal) > 1e9) d = new Date(Number(dateVal) * (Number(dateVal) > 1e12 ? 1 : 1000));
  return d && !isNaN(d.getTime()) ? d.getDay() : null;
}

// ---- 소형 SVG 산점도 + 회귀선 ----
function _BtqScatter({ pts, xLab, yLab, ols, colorFn }) {
  const W = 560, H = 260, padL = 46, padR = 14, padT = 12, padB = 30;
  const iw = W - padL - padR, ih = H - padT - padB;
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const xr = (xMax - xMin) || 1, yr = (yMax - yMin) || 1;
  const sx = v => padL + ((v - xMin) / xr) * iw;
  const sy = v => padT + ih - ((v - yMin) / yr) * ih;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }} role="img" aria-label={`${xLab} 대 ${yLab} 산점도`}>
      <line x1={padL} y1={padT + ih} x2={padL + iw} y2={padT + ih} stroke="var(--line)" />
      <line x1={padL} y1={padT} x2={padL} y2={padT + ih} stroke="var(--line)" />
      {yMin < 0 && yMax > 0 && <line x1={padL} y1={sy(0)} x2={padL + iw} y2={sy(0)} stroke="var(--line-2)" strokeDasharray="3 3" />}
      {pts.map((p, i) => (
        <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={2.6}
                fill={colorFn ? colorFn(p) : (p.y >= 0 ? "var(--teal)" : "var(--red)")} fillOpacity={0.65} />
      ))}
      {ols && (
        <line x1={sx(xMin)} y1={sy(ols.a + ols.b * xMin)} x2={sx(xMax)} y2={sy(ols.a + ols.b * xMax)}
              stroke="var(--violet)" strokeWidth={2} strokeDasharray="6 3" />
      )}
      <text x={padL + iw / 2} y={H - 6} textAnchor="middle" fontSize="10.5" fill="var(--ink-3)">{xLab}</text>
      <text x={12} y={padT + ih / 2} textAnchor="middle" fontSize="10.5" fill="var(--ink-3)"
            transform={`rotate(-90 12 ${padT + ih / 2})`}>{yLab}</text>
    </svg>
  );
}

const _BTQ_DOW = ["일", "월", "화", "수", "목", "금", "토"];

function BtQuantPanel({ analysis }) {
  const a = analysis || {};
  const trades = Array.isArray(a.mae_mfe) ? a.mae_mfe.filter(p => p && Number.isFinite(Number(p.pnl_pct))) : [];
  const daily = Array.isArray((a.equity || {}).daily) ? a.equity.daily : [];

  const model = useMemo_btq(() => {
    // ① 다차원 회귀: (MAE, MFE, 보유시간) → 수익률(표준화 베타)
    const ok = trades.filter(p => Number.isFinite(Number(p.mae)) && Number.isFinite(Number(p.mfe)));
    const multi = ok.length >= 8
      ? _btqMultiOls(
          [ok.map(p => Number(p.mae)), ok.map(p => Number(p.mfe)), ok.map(p => Number(p.hold_sec) || 0)],
          ok.map(p => Number(p.pnl_pct)))
      : null;
    // ② 보유시간 vs 수익 산점도 + 회귀
    const holdPts = ok.filter(p => Number(p.hold_sec) > 0)
      .map(p => ({ x: Number(p.hold_sec) / 60, y: Number(p.pnl_pct) }));
    const holdOls = holdPts.length >= 3 ? _btqOls(holdPts.map(p => p.x), holdPts.map(p => p.y)) : null;
    // ③ 일별 수익 자기상관(lag-1)
    const pnl = daily.map(d => Number(d.pnl) || 0);
    const lagPts = [];
    for (let i = 1; i < pnl.length; i++) lagPts.push({ x: pnl[i - 1], y: pnl[i] });
    const lagOls = lagPts.length >= 3 ? _btqOls(lagPts.map(p => p.x), lagPts.map(p => p.y)) : null;
    // ④ 요일 구조
    const dow = new Map();
    for (const d of daily) {
      const w = _btqParseDow(d.date != null ? d.date : d.dt);
      if (w == null) continue;
      const cur = dow.get(w) || { sum: 0, n: 0, win: 0 };
      const v = Number(d.pnl) || 0;
      cur.sum += v; cur.n += 1; if (v > 0) cur.win += 1;
      dow.set(w, cur);
    }
    return { multi, holdPts, holdOls, lagPts, lagOls, dow, nTrades: ok.length };
  }, [a]);

  const { multi, holdPts, holdOls, lagPts, lagOls, dow } = model;
  if (!trades.length && !daily.length) return null;

  const betaRows = multi ? [
    { k: "MAE(최대 역행)", v: multi.beta[0] },
    { k: "MFE(최대 순행)", v: multi.beta[1] },
    { k: "보유시간", v: multi.beta[2] },
  ] : [];
  const maxAbsBeta = betaRows.reduce((m, r) => Math.max(m, Math.abs(r.v)), 0) || 1;
  const lagWord = lagOls ? (lagOls.b > 0.15 ? "추세 지속(전일 수익이 다음날로 이어지는 경향)"
    : lagOls.b < -0.15 ? "평균 회귀(전일 수익이 다음날 반대로 움직이는 경향)" : "자기상관 미약(일별 수익 독립적)") : null;
  const dowRows = [1, 2, 3, 4, 5].map(w => ({ w, ...(dow.get(w) || { sum: 0, n: 0, win: 0 }) }));
  const dowMaxAbs = dowRows.reduce((m, r) => Math.max(m, Math.abs(r.n ? r.sum / r.n : 0)), 0) || 1;

  return (
    <>
      <section className="panel bt-equal-card bt-quant-card" aria-label="다차원 회귀">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--violet)" }}></span>다차원 회귀 · 수익률 설명력</div></div>
        <div className="panel-bd">
          {multi ? (
            <div>
              {betaRows.map(r => (
                <div key={r.k} className="v54-beta-row">
                  <span className="k">{r.k}</span>
                  <span className="bar">
                    <i className={r.v >= 0 ? "pos" : "neg"}
                       style={{ width: Math.max(4, Math.round(Math.abs(r.v) / maxAbsBeta * 100)) + "%" }}></i>
                  </span>
                  <span className="v mono">{r.v >= 0 ? "+" : ""}{r.v.toFixed(2)}</span>
                </div>
              ))}
              <p className="v54-quant-note">표준화 β(상대 기여). R² {(multi.r2 * 100).toFixed(0)}% · n={multi.n}.
                {Math.abs(multi.beta[0]) > Math.abs(multi.beta[1])
                  ? " 손실 통제(MAE)가 수익률을 더 크게 좌우 — 손절 규칙 개선이 우선순위."
                  : " 이익 실현(MFE) 포착이 수익률을 더 크게 좌우 — 청산 타이밍 개선이 우선순위."}</p>
            </div>
          ) : <p className="v54-quant-note">거래 표본 부족(8건 미만) — 다차원 회귀 생략.</p>}
        </div>
      </section>
      <section className="panel bt-equal-card bt-quant-card" aria-label="보유시간 수익률 회귀">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--blue)" }}></span>보유시간 → 수익률</div></div>
        <div className="panel-bd">
          {holdPts.length >= 3 ? (
            <div>
              <_BtqScatter pts={holdPts} xLab="보유시간(분)" yLab="수익률(%)" ols={holdOls} />
              {holdOls && <p className="v54-quant-note">기울기 {holdOls.b >= 0 ? "+" : ""}{holdOls.b.toFixed(3)}%/분 · R² {(holdOls.r2 * 100).toFixed(0)}% — {holdOls.b < 0 ? "오래 들고 있을수록 불리: 시간 손절 검토." : "보유 시간이 길수록 유리: 조기 청산 완화 검토."}</p>}
            </div>
          ) : <p className="v54-quant-note">보유시간 표본 부족.</p>}
        </div>
      </section>
      <section className="panel bt-equal-card bt-quant-card" aria-label="일별 수익 자기상관">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>일별 수익 자기상관 · lag-1</div></div>
        <div className="panel-bd">
          {lagPts.length >= 3 ? (
            <div>
              <_BtqScatter pts={lagPts} xLab="전일 수익(원)" yLab="당일 수익(원)" ols={lagOls} />
              {lagOls && <p className="v54-quant-note">β {lagOls.b >= 0 ? "+" : ""}{lagOls.b.toFixed(2)} · R² {(lagOls.r2 * 100).toFixed(0)}% — {lagWord}.</p>}
            </div>
          ) : <p className="v54-quant-note">일별 수익 표본 부족.</p>}
        </div>
      </section>
      <section className="panel bt-equal-card bt-quant-card" aria-label="요일별 평균 수익과 승일률">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>요일 구조 · 평균 수익·승일률</div></div>
        <div className="panel-bd">
          {dowRows.some(r => r.n > 0) ? (
            <div>
              {dowRows.map(r => {
                const avg = r.n ? r.sum / r.n : 0;
                return (
                  <div key={r.w} className="v54-beta-row">
                    <span className="k">{_BTQ_DOW[r.w]}</span>
                    <span className="bar">
                      <i className={avg >= 0 ? "pos" : "neg"}
                         style={{ width: Math.max(3, Math.round(Math.abs(avg) / dowMaxAbs * 100)) + "%" }}></i>
                    </span>
                    <span className="v mono">{r.n ? Math.round(avg).toLocaleString() + "원 · " + Math.round(r.win / r.n * 100) + "%" : "—"}</span>
                  </div>
                );
              })}
              <p className="v54-quant-note">요일별 평균 일수익과 수익일 비율. 특정 요일 열세가 뚜렷하면 요일 필터 가설로 환류.</p>
            </div>
          ) : <p className="v54-quant-note">날짜 정보가 없어 요일 구조 생략.</p>}
        </div>
      </section>
    </>
  );
}

Object.assign(window, { BtQuantPanel });
// dual-safe ESM export. KEEP on ONE physical line.
export { BtQuantPanel };
