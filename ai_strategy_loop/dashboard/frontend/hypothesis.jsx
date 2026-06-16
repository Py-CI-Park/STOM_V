/* P2b-2 — 가정(Hypothesis) 루프 가시화 패널.
   가정 루프(P2a)가 세운 가정과 채택/기각 판정을 대시보드에 노출한다. 데이터는
   generations.hypotheses_json(가정 추적 토글 ON일 때만 채워짐)에 영속되어 세대 행의
   state.generations[].hypotheses 로 실려 온다. 읽기 전용 가시화 — 새 백테/생성/평가 없음.

   각 가정 dict 필드(autopsy/hypothesis.py Hypothesis.to_dict):
     side(buy|sell|both) · text(NL 한 줄) · target_metric(mdd|profit|daily_avg_trades|graded) ·
     expected_direction(+1 증가기대 / -1 감소기대) · source · basis ·
     verdict(untested|accepted|rejected|inconclusive) · observed_delta(실측 델타 or null).

   하위호환: hypotheses가 빈 리스트(토글 OFF/구 상태/부모 없는 세대)면 패널 자체를 렌더하지
   않는다(null 반환). 패널 스타일은 기존 panel/panel-hd/panel-bd + pill + var(--...)을 재사용.
   QualityTrendChart(chart.jsx)·AutopsyPanel(panels.jsx) 패턴 참고. */

// verdict → pill 스타일/라벨 매핑. 색은 styles.css var 토큰만 사용한다.
const _VERDICT_META = {
  accepted:     { label: "채택", color: "var(--teal)",  tip: "실측 델타 부호가 기대 방향과 일치(가정이 맞았다)" },
  rejected:     { label: "기각", color: "var(--red)",   tip: "실측 델타 부호가 기대 방향과 반대(가정이 빗나갔다)" },
  inconclusive: { label: "판정불가", color: "var(--ink-3)", tip: "델타 없음(부모 없음/키 누락) 또는 움직임 미미" },
  untested:     { label: "미검증", color: "var(--ink-3)", tip: "아직 다음 세대 델타로 검증되지 않음" },
};

// side → 뱃지 라벨. 어느 측 전략을 고치려는 가정인가.
const _SIDE_LABEL = { buy: "매수", sell: "매도", both: "공통" };

// target_metric → 사람이 읽는 라벨(가정이 겨냥하는 지표).
const _METRIC_LABEL = {
  mdd: "MDD",
  profit: "총손익",
  daily_avg_trades: "일평균거래",
  graded: "graded",
};

function _VerdictPill({ verdict }) {
  const meta = _VERDICT_META[verdict] || _VERDICT_META.untested;
  return (
    <span className="pill" data-tip={meta.tip}
      style={{ color: meta.color, borderColor: meta.color, fontSize: 10 }}>
      {meta.label}
    </span>
  );
}

function HypothesisPanel({ state }) {
  // 가정이 있는 가장 최근 세대를 찾는다(gen_no 내림차순). 없으면 패널 미표시.
  const gens = state.generations || [];
  let target = null;
  for (const g of gens) {
    const hyps = g.hypotheses || [];
    if (hyps.length > 0 && (!target || g.gen_no > target.gen_no)) {
      target = g;
    }
  }

  // 판정된 가정을 가진 세대가 하나도 없으면 렌더하지 않는다(하위호환·노이즈 방지).
  if (!target) return null;

  const hyps = target.hypotheses || [];
  const genLabel = `gen_${String(target.gen_no).padStart(2, "0")}`;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          가정 루프 — Hypothesis ({genLabel})
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          실행→분석→가정→개선 과학적 방법 루프
        </span>
      </div>
      <div className="panel-bd">
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
          {hyps.map((h, i) => {
            const dir = (h.expected_direction || 0) > 0 ? "↑" : (h.expected_direction || 0) < 0 ? "↓" : "·";
            const metric = _METRIC_LABEL[h.target_metric] || h.target_metric || "—";
            const sideLabel = _SIDE_LABEL[h.side] || h.side || "—";
            const obs = h.observed_delta;
            return (
              <li key={i} style={{
                padding: "8px 10px",
                background: "var(--bg-1)",
                border: "1px solid var(--line-1)",
                borderRadius: 6,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
                  <span className="pill" style={{ fontSize: 10 }}>{sideLabel}</span>
                  <_VerdictPill verdict={h.verdict} />
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
                    {metric} {dir}
                  </span>
                  {typeof obs === "number" && (
                    <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", marginLeft: "auto" }}
                          data-tip="다음 세대 실측 델타(판정 근거)">
                      Δ {obs >= 0 ? "+" : ""}{obs.toFixed(4)}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: "var(--ink-0)", lineHeight: 1.5 }}>
                  {h.text || "—"}
                </div>
                {h.basis && (
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 }}>
                    근거: {h.basis}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

Object.assign(window, { HypothesisPanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { HypothesisPanel };
