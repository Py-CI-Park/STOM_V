/* research-next-steps.jsx — "그래서 다음에 무엇을 바꿔야 하나"에 답하는 카드.
 *
 *   대시보드는 지금까지 상태를 보여주는 데까지만 갔다. 정체를 감지해도(개선 추이 카드),
 *   손실 구간을 찾아도(부검), 가정이 빗나가도(가정 루프) 그 셋을 이어 붙여 "다음 수"로
 *   만드는 일은 사람이 머리로 했다. 이 카드는 이미 발행된 세 가지 근거만 엮는다.
 *
 *   새로 계산하는 값은 없다. 없는 근거는 없다고 말하고 제안하지 않는다.
 */
import { riImprovementSeries } from "./research-improvement.jsx";

const { useMemo: useMemo_ns } = React;

// 세대별 가정 중 '빗나감'으로 판정된 것을 문구 기준으로 묶는다.
//   같은 가정을 여러 번 시도해 계속 빗나갔다면 그것이 가장 강한 신호다.
function collectRejectedHypotheses(generations) {
  const bucket = new Map();
  for (const g of (Array.isArray(generations) ? generations : [])) {
    for (const h of (g && Array.isArray(g.hypotheses) ? g.hypotheses : [])) {
      if (!h || h.verdict !== "rejected") continue;
      const key = String(h.text || h.target_metric || "").trim();
      if (!key) continue;
      const prev = bucket.get(key) || { text: key, count: 0, gens: [], metric: h.target_metric, side: h.side };
      prev.count += 1;
      if (g.gen_no != null) prev.gens.push(g.gen_no);
      bucket.set(key, prev);
    }
  }
  return [...bucket.values()].sort((a, b) => b.count - a.count);
}

// 부검 세그먼트 중 평균 대비 가장 나빴던 구간.
function worstAutopsySegments(autopsy, limit = 2) {
  if (!autopsy || typeof autopsy !== "object" || autopsy.status === "missing" || autopsy.status === "pending") return [];
  const pool = []
    .concat(Array.isArray(autopsy.cross_segments) ? autopsy.cross_segments : [])
    .concat(Array.isArray(autopsy.time_segments) ? autopsy.time_segments : [])
    .concat(Array.isArray(autopsy.market_cap_segments) ? autopsy.market_cap_segments : [])
    .filter(r => r && typeof r === "object" && Number.isFinite(Number(r.return_diff)) && Number(r.return_diff) < 0);
  return pool.sort((a, b) => Number(a.return_diff) - Number(b.return_diff)).slice(0, limit);
}

// 근거 → 제안. 근거가 없으면 항목을 만들지 않는다(빈 제안 금지).
function buildNextSteps({ generations, autopsy }) {
  const steps = [];
  const series = riImprovementSeries(generations);

  // ① 정체 — 최고 기록 갱신 이후 경과 세대.
  let sinceRecord = null;
  for (let i = series.length - 1; i >= 0; i -= 1) {
    if (series[i].isRecord) { sinceRecord = series.length - 1 - i; break; }
  }
  if (sinceRecord != null && sinceRecord >= 5) {
    steps.push({
      tone: "warn",
      title: `${sinceRecord}세대째 최고 기록이 갱신되지 않았습니다`,
      detail: "지금 방향으로는 더 좋아지지 않고 있습니다. 같은 축을 미세 조정하기보다 시간대·종목군 같은 탐색 축 자체를 바꾸는 편이 낫습니다.",
      evidence: "세대별 개선 추이",
    });
  }

  // ② 게이트 — 통과 세대가 하나도 없으면 게이트가 실효 상한인지 먼저 확인해야 한다.
  const gatePassed = series.filter(p => p.gatePassed).length;
  if (series.length >= 5 && gatePassed === 0) {
    steps.push({
      tone: "warn",
      title: `${series.length}세대 중 게이트 통과가 0건입니다`,
      detail: "후보 품질 문제인지 게이트 기준이 현재 데이터에서 도달 불가한 값인지 구분해야 합니다. 거버넌스의 하드 게이트 값과 실제 분포를 나란히 보세요.",
      evidence: "세대 표 · 조건식 발굴 거버넌스",
    });
  }

  // ③ 부검 — 손실이 몰린 구간.
  for (const seg of worstAutopsySegments(autopsy)) {
    steps.push({
      tone: "danger",
      title: `손실이 몰린 구간: ${seg.label}`,
      detail: `전체 평균보다 ${Number(seg.return_diff).toFixed(2)}%p 나빴습니다(${seg.count ?? "?"}건). 이 구간을 제외하거나 진입 조건을 좁히는 가정을 먼저 시험하세요.`,
      evidence: "세그먼트 부검",
    });
  }

  // ④ 반복 실패한 가정 — 같은 시도를 또 하지 않도록.
  const rejected = collectRejectedHypotheses(generations).filter(r => r.count >= 2);
  for (const r of rejected.slice(0, 2)) {
    steps.push({
      tone: "info",
      title: `이미 ${r.count}번 빗나간 가정입니다`,
      detail: `"${r.text}" — 세대 ${r.gens.map(g => "g" + g).join(", ")} 에서 기대와 반대로 움직였습니다. 같은 방향을 다시 시도하기 전에 전제를 바꾸세요.`,
      evidence: "가정 루프",
    });
  }

  return steps;
}

function ResearchNextStepsCard({ state }) {
  const generations = state && state.generations;
  const autopsy = state && state.page_data && state.page_data.autopsy;
  const steps = useMemo_ns(() => buildNextSteps({ generations, autopsy }), [generations, autopsy]);
  const autopsyMissing = !autopsy || autopsy.status === "missing" || autopsy.status === "pending";

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          다음에 무엇을 바꿀까 · 근거 기반 제안
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>제안 {steps.length}건</span>
      </div>
      <div className="panel-bd">
        <p className="v59-section-intro" style={{ marginTop: 0 }}>
          이미 발행된 근거(개선 추이 · 게이트 · 부검 · 가정 판정)만 엮어 만든 제안입니다.
          <b> 새로 계산하거나 추정한 값은 없습니다.</b>
        </p>
        {steps.length === 0 ? (
          <div className="research-empty">
            아직 제안할 근거가 모이지 않았습니다. 세대가 더 쌓이거나 부검이 발행되면 여기에 표시됩니다.
          </div>
        ) : (
          <ol className="ns-list">
            {steps.map((s, i) => (
              <li key={i} className={"ns-item " + s.tone}>
                <b>{s.title}</b>
                <span>{s.detail}</span>
                <small>근거 · {s.evidence}</small>
              </li>
            ))}
          </ol>
        )}
        {autopsyMissing && (
          <p className="ns-gap mono" role="status">
            이번 run 은 세그먼트 부검이 발행되지 않아 구간 기반 제안은 만들 수 없습니다.
          </p>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ResearchNextStepsCard, buildNextSteps, collectRejectedHypotheses });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { ResearchNextStepsCard, buildNextSteps, collectRejectedHypotheses };
