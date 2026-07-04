/* v4-charts.jsx — V4 전용 대형 캔버스 차트 (강한 시각화, V2 무영향)
 *
 *   승인 프로토타입의 hero 차트를 실데이터 컴포넌트로 구현한다.
 *   V4HeroChart: state.generations 의 graded_score 곡선 — 그라디언트 area · gate 점선 ·
 *   best(보라, 흰 링) / 현재(앰버) 마커 · mono 축라벨. 테마 토큰을 그리는 시점에 읽고
 *   data-theme 변경·리사이즈에 재도장. devicePixelRatio 대응.
 *   jsdom(하네스)에는 canvas 2D 가 없으므로 ctx 부재 시 조용히 스킵(렌더는 유지).
 */
const { useEffect: useEffect_v4c, useRef: useRef_v4c } = React;

function _v4Tok(name) {
  try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  catch (e) { return ""; }
}
function _v4Alpha(hex, a) {
  const h = (hex || "#4cd6b3").replace("#", "");
  const f = h.length === 3 ? h.split("").map(c => c + c).join("") : h;
  const r = parseInt(f.substr(0, 2), 16) || 0, g = parseInt(f.substr(2, 2), 16) || 0, b = parseInt(f.substr(4, 2), 16) || 0;
  return `rgba(${r},${g},${b},${a})`;
}

// series: [{x라벨, v값}] — graded_score 곡선. target: gate 점선 값. bestIdx: 보라 마커 인덱스.
function _v4DrawHero(canvas, series, { target, bestIdx }) {
  if (!canvas || typeof canvas.getContext !== "function") return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return; // jsdom 등 canvas 미지원 호스트 — 조용히 스킵
  const wrap = canvas.parentElement;
  const cw = Math.max(320, (wrap && wrap.clientWidth) || 880);
  const ch = Math.max(220, (wrap && wrap.clientHeight) || 400);
  const dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
  canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);

  const ink2 = _v4Tok("--ink-2") || "#778496";
  const line1 = _v4Tok("--line-1") || "#1d2530";
  const teal = _v4Tok("--teal") || "#4cd6b3";
  const violet = _v4Tok("--violet") || "#a594ff";
  const amber = _v4Tok("--amber") || "#f0b35a";
  const bg1 = _v4Tok("--bg-1") || "#0c1014";
  const mono = (_v4Tok("--mono") || "IBM Plex Mono, monospace");

  const pl = 52, pr = 26, pt = 20, pb = 34;
  const vals = series.map(s => s.v);
  if (!vals.length) {
    ctx.fillStyle = ink2; ctx.font = "12px " + mono; ctx.textAlign = "center";
    ctx.fillText("연구 대기 — 세대 데이터가 도착하면 실시간으로 그려집니다", cw / 2, ch / 2);
    return;
  }
  let min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
  if (target != null) { min = Math.min(min, target); max = Math.max(max, target); }
  const pad = (max - min || 1) * 0.12; min -= pad; max += pad;
  const rng = max - min || 1;
  const px = i => series.length < 2 ? (pl + (cw - pl - pr) / 2) : pl + (cw - pl - pr) * i / (series.length - 1);
  const py = v => pt + (ch - pt - pb) * (1 - (v - min) / rng);

  // 그리드(점선) + y축 라벨
  ctx.strokeStyle = line1; ctx.lineWidth = 1; ctx.setLineDash([2, 6]);
  ctx.fillStyle = ink2; ctx.font = "11px " + mono; ctx.textAlign = "right";
  for (let g = 0; g <= 4; g++) {
    const yy = pt + (ch - pt - pb) * g / 4;
    ctx.beginPath(); ctx.moveTo(pl, yy); ctx.lineTo(cw - pr, yy); ctx.stroke();
    ctx.fillText((max - rng * g / 4).toFixed(2), pl - 8, yy + 4);
  }
  ctx.setLineDash([]);

  // gate 점선(보라)
  if (target != null) {
    const gy = py(target);
    ctx.strokeStyle = violet; ctx.setLineDash([7, 7]);
    ctx.beginPath(); ctx.moveTo(pl, gy); ctx.lineTo(cw - pr, gy); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = violet; ctx.textAlign = "left";
    ctx.fillText("gate " + Number(target).toFixed(2), pl + 6, gy - 6);
  }

  // 그라디언트 area + 라인
  const grad = ctx.createLinearGradient(0, pt, 0, ch - pb);
  grad.addColorStop(0, _v4Alpha(teal, 0.28)); grad.addColorStop(1, _v4Alpha(teal, 0));
  ctx.beginPath(); ctx.moveTo(px(0), py(vals[0]));
  for (let i = 1; i < vals.length; i++) ctx.lineTo(px(i), py(vals[i]));
  ctx.lineTo(px(vals.length - 1), ch - pb); ctx.lineTo(px(0), ch - pb); ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();
  ctx.beginPath(); ctx.moveTo(px(0), py(vals[0]));
  for (let j = 1; j < vals.length; j++) ctx.lineTo(px(j), py(vals[j]));
  ctx.strokeStyle = teal; ctx.lineWidth = 2.2; ctx.lineJoin = "round"; ctx.stroke();

  // 세대 점(옅게)
  ctx.fillStyle = _v4Alpha(teal, 0.8);
  for (let d = 0; d < vals.length; d++) { ctx.beginPath(); ctx.arc(px(d), py(vals[d]), 2.2, 0, 7); ctx.fill(); }

  // best 마커(보라 + 흰 링)
  if (bestIdx != null && bestIdx >= 0 && bestIdx < vals.length) {
    ctx.beginPath(); ctx.arc(px(bestIdx), py(vals[bestIdx]), 6, 0, 7);
    ctx.fillStyle = violet; ctx.fill();
    ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 1.5; ctx.stroke();
  }
  // 현재 점(앰버 + 배경 링)
  const li = vals.length - 1;
  ctx.beginPath(); ctx.arc(px(li), py(vals[li]), 7, 0, 7);
  ctx.fillStyle = amber; ctx.fill();
  ctx.strokeStyle = bg1; ctx.lineWidth = 3; ctx.stroke();

  // x축 라벨(처음/중간/끝)
  ctx.fillStyle = ink2; ctx.font = "11px " + mono; ctx.textAlign = "center";
  const marks = series.length >= 3 ? [0, Math.floor((series.length - 1) / 2), series.length - 1] : series.map((_, i) => i);
  for (const m of marks) ctx.fillText(String(series[m].x), px(m), ch - pb + 18);
}

// V4HeroChart — Research Live 주인공 차트. state.generations 기반, 컨테이너 크기로 스케일.
function V4HeroChart({ state, target }) {
  const ref = useRef_v4c(null);
  const gens = Array.isArray(state && state.generations) ? state.generations : [];
  const series = gens
    .filter(g => g && g.graded_score != null && isFinite(Number(g.graded_score)))
    .map(g => ({ x: "g" + g.gen_no, v: Number(g.graded_score) }));
  let bestIdx = null, bestV = -Infinity;
  for (let i = 0; i < series.length; i++) if (series[i].v > bestV) { bestV = series[i].v; bestIdx = i; }
  const key = series.map(s => s.v.toFixed(4)).join(",") + "|" + (target ?? "");

  useEffect_v4c(() => {
    const draw = () => _v4DrawHero(ref.current, series, { target, bestIdx });
    draw();
    let ro = null;
    if (typeof ResizeObserver === "function" && ref.current && ref.current.parentElement) {
      ro = new ResizeObserver(draw);
      ro.observe(ref.current.parentElement);
    }
    window.addEventListener("resize", draw);
    const mo = typeof MutationObserver === "function"
      ? new MutationObserver(draw) : null;
    if (mo) mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      window.removeEventListener("resize", draw);
      if (ro) ro.disconnect();
      if (mo) mo.disconnect();
    };
  }, [key]);

  return (
    <div className="v4-canvas-wrap v4-hero-canvas" role="img" aria-label="적합도 곡선(세대별 graded score)">
      <canvas ref={ref}></canvas>
    </div>
  );
}

Object.assign(window, { V4HeroChart });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4HeroChart };
