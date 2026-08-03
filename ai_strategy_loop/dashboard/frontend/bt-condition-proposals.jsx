/* Evidence-first sell proposal cards. Drafts are never saved automatically. */
function BtConditionProposals({ proposals }) {
  const rows = (proposals && proposals.proposals) || [];
  if (!rows.length) return <div className="tp-empty">분석을 완료한 뒤 후보를 생성하세요. 근거가 부족하면 후보를 만들지 않습니다.</div>;
  const copy = code => { try { navigator.clipboard.writeText(code); } catch (error) {} };
  return (
    <div className="tp-proposal-grid">
      {rows.map(row => <article className="tp-proposal" key={row.proposal_id}>
        <header><div><b>{row.title}</b><small>{row.family || "연구군"} · {row.timeframe || "unknown"} 전용{row.intent_gate === "pass" ? " · intent gate ✓" : ""}</small><small>{row.intent}</small></div><span className="tp-authority advisory">자문</span></header>
        <pre>{row.stom_code}</pre>
        {(row.threshold_sources || []).length > 0 && <div className="tp-proposal-sources"><b>임계값 출처 · 분위수</b>{row.threshold_sources.map(source => <small key={source}>• {source}</small>)}</div>}
        {(row.param_family || []).length > 0 && <div className="tp-proposal-params"><b>구조 파라미터(스윕 대상)</b>{row.param_family.map(param => <small key={param}>• {param}</small>)}</div>}
        <dl><dt>근거</dt><dd>{row.evidence}</dd><dt>반증</dt><dd>{row.counterevidence}</dd><dt>위험</dt><dd>{row.risk}</dd></dl>
        <button className="btn ghost sm" onClick={() => copy(row.stom_code)}>초안 복사 · 자동 저장 안 함</button>
      </article>)}
    </div>
  );
}

Object.assign(window, { BtConditionProposals });
export { BtConditionProposals };
